import random
from pathlib import Path
from threading import Lock

from ..core.config_loader import TopologyConfig
from ..core.config_loader import load_topology
from ..core.event_bus import EventBus
from ..core.routing import compute_all_routing_tables
from ..logging.router_logger import RouterLogger
from ..network.packet import Packet
from ..network.packet import checksum
from ..network.router import UdpRouter
from ..rdt.base import ReliableDataTransferProtocol
from ..rdt.rdt_1 import Rdt1Protocol
from ..rdt.rdt_2 import Rdt2Protocol
from ..rdt.rdt_3 import Rdt3Protocol
from .fault_simulator import FaultSimulator

SUPPORTED_RDT_VERSIONS = {"1.0", "2.0", "3.0"}


class NetworkEngine:
    def __init__(
        self,
        config_dir: Path,
        logs_dir: Path,
        corruption_rate: float = 0.10,
        loss_rate: float = 0.10,
        timeout_seconds: float = 2,
        max_retries: int = 5,
        rng: random.Random | None = None,
    ) -> None:
        self.config_dir = config_dir
        self.logger = RouterLogger(logs_dir)
        self.event_bus = EventBus()
        self.fault_simulator = FaultSimulator(
            corruption_rate=corruption_rate,
            loss_rate=loss_rate,
            rng=rng,
        )
        self._protocols: dict[str, ReliableDataTransferProtocol] = {
            Rdt1Protocol.version: Rdt1Protocol(),
            Rdt2Protocol.version: Rdt2Protocol(),
            Rdt3Protocol.version: Rdt3Protocol(
                timeout_seconds=timeout_seconds,
                max_retries=max_retries,
            ),
        }
        self._lock = Lock()
        self._seq = 0
        self._topology: TopologyConfig | None = None
        self._routers: dict[int, UdpRouter] = {}

    def start(self) -> None:
        if self._routers:
            return

        topology = load_topology(self.config_dir)
        routing_tables = compute_all_routing_tables(topology)
        addresses = {router.id: (router.ip, router.port) for router in topology.routers}

        routers = {
            router.id: UdpRouter(
                config=router,
                router_addresses=addresses,
                routing_table=routing_tables[router.id],
                logger=self.logger,
                event_bus=self.event_bus,
                fault_simulator=self.fault_simulator,
            )
            for router in topology.routers
        }

        for router in routers.values():
            router.start()

        self._topology = topology
        self._routers = routers
        self.event_bus.emit(
            "NETWORK_STARTED",
            router_count=len(topology.routers),
            link_count=len(topology.links),
            message="Rede UDP inicializada",
        )
        self.event_bus.emit(
            "ROUTES_COMPUTED",
            router_count=len(routing_tables),
            message="Tabelas de roteamento calculadas com Dijkstra",
        )

    def stop(self) -> None:
        for router in self._routers.values():
            router.stop()
        self._routers = {}
        self._topology = None

    def topology(self) -> TopologyConfig:
        if self._topology is None:
            return load_topology(self.config_dir)
        return self._topology

    def send_message(
        self,
        source: int,
        destination: int,
        message: str,
        rdt_version: str,
    ) -> dict[str, int | str | list[int]]:
        topology = self.topology()
        router_ids = {router.id for router in topology.routers}

        if source not in router_ids:
            raise ValueError(f"source router {source} is not configured")
        if destination not in router_ids:
            raise ValueError(f"destination router {destination} is not configured")
        if source == destination:
            raise ValueError("source and destination must be different")
        if not message:
            raise ValueError("message must not be empty")
        if len(message) > 100:
            raise ValueError("message must have at most 100 characters")
        if rdt_version not in SUPPORTED_RDT_VERSIONS:
            raise ValueError("rdt_version must be 1.0, 2.0 or 3.0")

        if source not in self._routers:
            raise RuntimeError("network engine is not running")

        routing_table = compute_all_routing_tables(topology)[source]
        route = routing_table.routes.get(destination)
        if route is None:
            raise ValueError(f"no route from {source} to {destination}")

        seq = self._next_seq()
        packet = Packet(
            type="DATA",
            rdt_version=rdt_version,
            seq=seq,
            source=source,
            destination=destination,
            current_router=source,
            payload=message,
            checksum=checksum(seq, source, destination, message),
            path=route.path,
            attempt=1,
        )

        self.event_bus.emit(
            "MESSAGE_CREATED",
            seq=seq,
            router_id=source,
            source=source,
            destination=destination,
            path=route.path,
            message=f"Mensagem DATA seq={seq} criada com RDT {rdt_version}",
        )
        self._protocols[rdt_version].send(self._routers[source], packet)

        return {
            "status": "queued",
            "seq": seq,
            "source": source,
            "destination": destination,
            "path": route.path,
        }

    def read_logs(self, router_id: int) -> list[str]:
        return self.logger.read(router_id)

    def recent_events(self) -> list[dict[str, object]]:
        return self.event_bus.recent()

    def _next_seq(self) -> int:
        with self._lock:
            self._seq += 1
            return self._seq
