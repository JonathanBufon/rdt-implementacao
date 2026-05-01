import socket
from threading import Event
from threading import Thread

from ..core.config_loader import RouterConfig
from ..core.routing import RoutingTable
from ..logging.router_logger import RouterLogger
from .packet import Packet


class UdpRouter:
    def __init__(
        self,
        config: RouterConfig,
        router_addresses: dict[int, tuple[str, int]],
        routing_table: RoutingTable,
        logger: RouterLogger,
    ) -> None:
        self.config = config
        self.router_addresses = router_addresses
        self.routing_table = routing_table
        self.logger = logger
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
        next_hop = self._next_hop(packet.destination)
        self._send(packet.at_router(self.config.id), next_hop)
        self.logger.write(
            self.config.id,
            "SENT",
            f'seq={packet.seq} destination={packet.destination} next_hop={next_hop} payload="{packet.payload}"',
        )

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
        self.logger.write(
            self.config.id,
            "RECEIVED",
            f"seq={packet.seq} source={packet.source} destination={packet.destination}",
        )

        if packet.type != "DATA":
            self.logger.write(self.config.id, "CORRUPTED", f"unsupported packet type={packet.type}")
            return

        if packet.destination == self.config.id:
            self.logger.write(
                self.config.id,
                "DELIVERED",
                f'seq={packet.seq} source={packet.source} payload="{packet.payload}"',
            )
            return

        next_hop = self._next_hop(packet.destination)
        self._send(packet, next_hop)
        self.logger.write(
            self.config.id,
            "FORWARDED",
            f"seq={packet.seq} destination={packet.destination} next_hop={next_hop}",
        )

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
