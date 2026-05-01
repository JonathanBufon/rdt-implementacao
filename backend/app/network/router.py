import socket
from threading import Event
from threading import Lock
from threading import Thread

from ..core.config_loader import RouterConfig
from ..core.event_bus import EventBus
from ..core.routing import RoutingTable
from ..logging.router_logger import RouterLogger
from .packet import Packet
from .packet import checksum
from .packet import has_valid_checksum


class UdpRouter:
    def __init__(
        self,
        config: RouterConfig,
        router_addresses: dict[int, tuple[str, int]],
        routing_table: RoutingTable,
        logger: RouterLogger,
        event_bus: EventBus,
        fault_simulator: object | None = None,
    ) -> None:
        self.config = config
        self.router_addresses = router_addresses
        self.routing_table = routing_table
        self.logger = logger
        self.event_bus = event_bus
        self.fault_simulator = fault_simulator
        self._sent_packets: dict[int, Packet] = {}
        self._ack_events: dict[int, Event] = {}
        self._state_lock = Lock()
        self._stop_event = Event()
        self._thread: Thread | None = None
        self._socket: socket.socket | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return

        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._socket.bind((self.config.ip, self.config.port))
        self._socket.settimeout(0.2)
        self._stop_event.clear()
        self._thread = Thread(target=self._serve, name=f"udp-router-{self.config.id}", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._socket:
            self._socket.close()
            self._socket = None
        if self._thread:
            self._thread.join(timeout=1)
            self._thread = None

    def send_initial(self, packet: Packet) -> None:
        with self._state_lock:
            self._sent_packets[packet.seq] = packet
        next_hop = self._next_hop(packet.destination)
        self._send(packet.at_router(self.config.id), next_hop)
        self.logger.write(
            self.config.id,
            "SENT",
            f'seq={packet.seq} destination={packet.destination} next_hop={next_hop} payload="{packet.payload}"',
        )
        self.event_bus.emit(
            "MESSAGE_SENT",
            seq=packet.seq,
            router_id=self.config.id,
            source=packet.source,
            destination=packet.destination,
            next_hop=next_hop,
            message=f"Roteador {self.config.id} enviou DATA seq={packet.seq} para Roteador {next_hop}",
        )

    def send_stop_and_wait(
        self,
        packet: Packet,
        timeout_seconds: float,
        max_retries: int,
    ) -> bool:
        ack_event = Event()
        with self._state_lock:
            self._ack_events[packet.seq] = ack_event

        try:
            current_packet = packet
            for attempt in range(1, max_retries + 1):
                current_packet = packet.with_attempt(attempt)
                if attempt > 1:
                    self.logger.write(
                        self.config.id,
                        "RETRY",
                        f"seq={packet.seq} attempt={attempt} destination={packet.destination}",
                    )
                    self.event_bus.emit(
                        "MESSAGE_RETRY",
                        seq=packet.seq,
                        router_id=self.config.id,
                        source=packet.source,
                        destination=packet.destination,
                        attempt=attempt,
                        message=f"Roteador {self.config.id} retransmitiu DATA seq={packet.seq}",
                    )

                self.send_initial(current_packet)
                if ack_event.wait(timeout_seconds):
                    return True

                self.logger.write(
                    self.config.id,
                    "TIMEOUT",
                    f"seq={packet.seq} destination={packet.destination} attempt={attempt}",
                )
                self.event_bus.emit(
                    "TIMEOUT",
                    seq=packet.seq,
                    router_id=self.config.id,
                    source=packet.source,
                    destination=packet.destination,
                    attempt=attempt,
                    message=f"Roteador {self.config.id} entrou em timeout aguardando ACK seq={packet.seq}",
                )

            self.logger.write(
                self.config.id,
                "FAILED",
                f"seq={packet.seq} destination={packet.destination} attempts={max_retries}",
            )
            self.event_bus.emit(
                "MESSAGE_FAILED",
                seq=packet.seq,
                router_id=self.config.id,
                source=packet.source,
                destination=packet.destination,
                attempt=current_packet.attempt,
                message=f"Mensagem DATA seq={packet.seq} falhou após {max_retries} tentativas",
            )
            return False
        finally:
            with self._state_lock:
                self._ack_events.pop(packet.seq, None)

    def _serve(self) -> None:
        while not self._stop_event.is_set():
            try:
                assert self._socket is not None
                data, _address = self._socket.recvfrom(65535)
            except TimeoutError:
                continue
            except OSError:
                break

            try:
                packet = Packet.from_bytes(data).at_router(self.config.id)
            except (KeyError, ValueError):
                self.logger.write(self.config.id, "CORRUPTED", "invalid UDP packet")
                continue

            self._handle_packet(packet)

    def _handle_packet(self, packet: Packet) -> None:
        if packet.type in {"ACK", "NAK"}:
            self._handle_control_packet(packet)
            return

        self.logger.write(
            self.config.id,
            "RECEIVED",
            f"seq={packet.seq} source={packet.source} destination={packet.destination}",
        )
        self.event_bus.emit(
            "MESSAGE_RECEIVED",
            seq=packet.seq,
            router_id=self.config.id,
            source=packet.source,
            destination=packet.destination,
            message=f"Roteador {self.config.id} recebeu DATA seq={packet.seq}",
        )

        if packet.type != "DATA":
            self.logger.write(self.config.id, "CORRUPTED", f"unsupported packet type={packet.type}")
            self.event_bus.emit(
                "PACKET_CORRUPTED",
                seq=packet.seq,
                router_id=self.config.id,
                source=packet.source,
                destination=packet.destination,
                message=f"Roteador {self.config.id} recebeu tipo de pacote inválido",
            )
            return

        if self._should_drop(packet):
            self.logger.write(
                self.config.id,
                "DROPPED",
                f"seq={packet.seq} source={packet.source} destination={packet.destination}",
            )
            self.event_bus.emit(
                "PACKET_DROPPED",
                seq=packet.seq,
                router_id=self.config.id,
                source=packet.source,
                destination=packet.destination,
                message=f"Roteador {self.config.id} descartou DATA seq={packet.seq}",
            )
            return

        packet = self._maybe_corrupt(packet)
        if packet.rdt_version == "2.0" and not has_valid_checksum(packet):
            self.logger.write(
                self.config.id,
                "CORRUPTED",
                f"seq={packet.seq} source={packet.source} destination={packet.destination}",
            )
            self.event_bus.emit(
                "PACKET_CORRUPTED",
                seq=packet.seq,
                router_id=self.config.id,
                source=packet.source,
                destination=packet.destination,
                message=f"Roteador {self.config.id} detectou corrupção no DATA seq={packet.seq}",
            )
            self._send_control("NAK", packet)
            return

        if packet.destination == self.config.id:
            self.logger.write(
                self.config.id,
                "DELIVERED",
                f'seq={packet.seq} source={packet.source} payload="{packet.payload}"',
            )
            self.event_bus.emit(
                "MESSAGE_DELIVERED",
                seq=packet.seq,
                router_id=self.config.id,
                source=packet.source,
                destination=packet.destination,
                message=f"Mensagem DATA seq={packet.seq} entregue no Roteador {self.config.id}",
            )
            if packet.rdt_version in {"2.0", "3.0"}:
                self._send_control("ACK", packet)
            return

        next_hop = self._next_hop(packet.destination)
        self._send(packet, next_hop)
        self.logger.write(
            self.config.id,
            "FORWARDED",
            f"seq={packet.seq} destination={packet.destination} next_hop={next_hop}",
        )
        self.event_bus.emit(
            "MESSAGE_FORWARDED",
            seq=packet.seq,
            router_id=self.config.id,
            source=packet.source,
            destination=packet.destination,
            next_hop=next_hop,
            message=f"Roteador {self.config.id} encaminhou DATA seq={packet.seq} para Roteador {next_hop}",
        )

    def _handle_control_packet(self, packet: Packet) -> None:
        event_name = "ACK_RECEIVED" if packet.type == "ACK" else "NAK_RECEIVED"
        if packet.destination != self.config.id:
            next_hop = self._next_hop(packet.destination)
            self._send(packet.at_router(self.config.id), next_hop)
            self.logger.write(
                self.config.id,
                "FORWARDED",
                f"type={packet.type} seq={packet.seq} destination={packet.destination} next_hop={next_hop}",
            )
            self.event_bus.emit(
                f"{packet.type}_FORWARDED",
                seq=packet.seq,
                router_id=self.config.id,
                source=packet.source,
                destination=packet.destination,
                next_hop=next_hop,
                message=f"Roteador {self.config.id} encaminhou {packet.type} seq={packet.seq} para Roteador {next_hop}",
            )
            return

        self.logger.write(
            self.config.id,
            event_name,
            f"seq={packet.seq} from={packet.source}",
        )
        self.event_bus.emit(
            event_name,
            seq=packet.seq,
            router_id=self.config.id,
            source=packet.source,
            destination=packet.destination,
            message=f"Roteador {self.config.id} recebeu {packet.type} seq={packet.seq}",
        )

        if packet.destination == self.config.id:
            if packet.type == "ACK":
                with self._state_lock:
                    ack_event = self._ack_events.get(packet.seq)
                if ack_event is not None:
                    ack_event.set()
            if packet.type == "NAK":
                self._retry(packet.seq)

    def _retry(self, seq: int) -> None:
        with self._state_lock:
            packet = self._sent_packets.get(seq)
        if packet is None:
            self.logger.write(self.config.id, "FAILED", f"seq={seq} retry packet not found")
            return

        retry_packet = packet.with_attempt(packet.attempt + 1)
        self.logger.write(
            self.config.id,
            "RETRY",
            f"seq={seq} attempt={retry_packet.attempt} destination={retry_packet.destination}",
        )
        self.event_bus.emit(
            "MESSAGE_RETRY",
            seq=seq,
            router_id=self.config.id,
            source=retry_packet.source,
            destination=retry_packet.destination,
            attempt=retry_packet.attempt,
            message=f"Roteador {self.config.id} retransmitiu DATA seq={seq}",
        )
        self.send_initial(retry_packet)

    def _send_control(self, packet_type: str, packet: Packet) -> None:
        route = self.routing_table.routes.get(packet.source)
        if route is None:
            self.logger.write(self.config.id, "FAILED", f"seq={packet.seq} no route to {packet.source}")
            return

        control_packet = Packet(
            type=packet_type,  # type: ignore[arg-type]
            rdt_version=packet.rdt_version,
            seq=packet.seq,
            source=self.config.id,
            destination=packet.source,
            current_router=self.config.id,
            payload="",
            checksum=checksum(packet.seq, self.config.id, packet.source, ""),
            path=route.path,
            attempt=packet.attempt,
        )
        next_hop = route.next_hop
        self._send(control_packet, next_hop)

        event_name = "ACK_SENT" if packet_type == "ACK" else "NAK_SENT"
        self.logger.write(
            self.config.id,
            event_name,
            f"seq={packet.seq} destination={packet.source} next_hop={next_hop}",
        )
        self.event_bus.emit(
            event_name,
            seq=packet.seq,
            router_id=self.config.id,
            source=self.config.id,
            destination=packet.source,
            next_hop=next_hop,
            message=f"Roteador {self.config.id} enviou {packet_type} seq={packet.seq}",
        )

    def _maybe_corrupt(self, packet: Packet) -> Packet:
        should_corrupt = False
        if self.fault_simulator is not None:
            should_corrupt = bool(self.fault_simulator.should_corrupt(packet))  # type: ignore[attr-defined]
        if not should_corrupt:
            return packet
        return packet.with_checksum(f"corrupted-{packet.checksum}")

    def _should_drop(self, packet: Packet) -> bool:
        if self.fault_simulator is None:
            return False
        return bool(self.fault_simulator.should_drop(packet))  # type: ignore[attr-defined]

    def _next_hop(self, destination: int) -> int:
        route = self.routing_table.routes.get(destination)
        if route is None:
            raise ValueError(f"router {self.config.id} has no route to {destination}")
        return route.next_hop

    def _send(self, packet: Packet, next_hop: int) -> None:
        if self._socket is None:
            raise RuntimeError(f"router {self.config.id} is not running")

        address = self.router_addresses[next_hop]
        self._socket.sendto(packet.to_bytes(), address)
