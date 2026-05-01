import random
from dataclasses import dataclass
from pathlib import Path
from threading import Lock

from ..core.config_loader import TopologyConfig
from ..core.event_bus import EventBus
from ..core.networkx_graph_service import NetworkXGraphService
from ..core.routing import compute_all_routing_tables
from ..core.routing import compute_routing_table
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


@dataclass(frozen=True)
class SimulationSettings:
    loss_rate: float = 0.10
    corruption_rate: float = 0.10
    timeout_seconds: float = 2
    max_retries: int = 5

    def to_api_response(self) -> dict[str, float | int]:
        return {
            "loss_rate": self.loss_rate,
            "corruption_rate": self.corruption_rate,
            "timeout_seconds": self.timeout_seconds,
            "max_retries": self.max_retries,
        }


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
        self.settings = SimulationSettings(
            loss_rate=loss_rate,
            corruption_rate=corruption_rate,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
        )
        self.event_bus = EventBus()
        self.logger = RouterLogger(logs_dir, event_bus=self.event_bus)
        self.fault_simulator = FaultSimulator(
            corruption_rate=self.settings.corruption_rate,
            loss_rate=self.settings.loss_rate,
            rng=rng,
        )
        self._rdt3_protocol = Rdt3Protocol(
            timeout_seconds=self.settings.timeout_seconds,
            max_retries=self.settings.max_retries,
        )
        self._protocols: dict[str, ReliableDataTransferProtocol] = {
            Rdt1Protocol.version: Rdt1Protocol(),
            Rdt2Protocol.version: Rdt2Protocol(),
            Rdt3Protocol.version: self._rdt3_protocol,
        }
        self._lock = Lock()
        self._graph_rng = random.Random()
        self._seq = 0
        self._topology: TopologyConfig | None = None
        self._graph_service: NetworkXGraphService | None = None
        self._routing_tables = {}
        self._routers: dict[int, UdpRouter] = {}

    def start(self) -> None:
        if self._routers:
            return

        self._graph_service = NetworkXGraphService.from_config(self.config_dir, rng=self._graph_rng)
        topology = self._graph_service.to_topology_config()
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
        self._routing_tables = routing_tables
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
        self._graph_service = None
        self._routing_tables = {}

    def topology(self) -> TopologyConfig:
        if self._topology is None:
            if self._graph_service is None:
                self._graph_service = NetworkXGraphService.from_config(self.config_dir, rng=self._graph_rng)
            self._topology = self._graph_service.to_topology_config()
        return self._topology

    def routing_table(self, router_id: int):
        if self._topology is None:
            return compute_routing_table(self.topology(), router_id)
        return compute_routing_table(self._topology, router_id)

    def simulation_settings(self) -> dict[str, float | int]:
        return self.settings.to_api_response()

    def update_simulation_settings(
        self,
        loss_rate: float | None = None,
        corruption_rate: float | None = None,
        timeout_seconds: float | None = None,
        max_retries: int | None = None,
    ) -> dict[str, float | int]:
        updated = SimulationSettings(
            loss_rate=self.settings.loss_rate if loss_rate is None else loss_rate,
            corruption_rate=self.settings.corruption_rate if corruption_rate is None else corruption_rate,
            timeout_seconds=self.settings.timeout_seconds if timeout_seconds is None else timeout_seconds,
            max_retries=self.settings.max_retries if max_retries is None else max_retries,
        )
        self.settings = updated
        self.fault_simulator.update_rates(
            loss_rate=updated.loss_rate,
            corruption_rate=updated.corruption_rate,
        )
        self._rdt3_protocol.timeout_seconds = updated.timeout_seconds
        self._rdt3_protocol.max_retries = updated.max_retries
        payload = updated.to_api_response()
        self.event_bus.emit(
            "SIMULATION_SETTINGS_UPDATED",
            **payload,
            message="Configurações da simulação atualizadas",
        )
        return payload

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

        routing_table = self.routing_table(source)
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
            packet_type="DATA",
            seq=seq,
            router_id=source,
            current_router=source,
            source=source,
            destination=destination,
            next_hop=route.next_hop,
            path=route.path,
            attempt=1,
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

    def update_link_cost(self, source: int, target: int, cost: int) -> dict[str, object]:
        self._validate_router_ids(source, target)
        if cost <= 0:
            raise ValueError("cost must be a positive integer")

        topology = self.topology()
        link_index = self._find_link_index(source, target)
        if link_index is None:
            raise ValueError(f"link {source}-{target} is not configured")

        old_link = topology.links[link_index]
        self._apply_topology(self._graph().update_link_cost(source, target, cost))
        self.event_bus.emit(
            "LINK_COST_UPDATED",
            source=old_link.source,
            target=old_link.target,
            old_cost=old_link.cost,
            new_cost=cost,
            message=f"Custo do enlace {old_link.source} ↔ {old_link.target} alterado de {old_link.cost} para {cost}",
        )
        self._emit_routes_recomputed()
        return self._emit_topology_updated()

    def create_link(self, source: int, target: int, cost: int) -> dict[str, object]:
        self._validate_router_ids(source, target)
        if source == target:
            raise ValueError("source and target must be different")
        if cost <= 0:
            raise ValueError("cost must be a positive integer")
        if self._find_link_index(source, target) is not None:
            raise ValueError(f"link {source}-{target} already exists")

        self._apply_topology(self._graph().create_link(source, target, cost))
        self.event_bus.emit(
            "LINK_CREATED",
            source=source,
            target=target,
            cost=cost,
            message=f"Enlace {source} ↔ {target} criado com custo {cost}",
        )
        self._emit_routes_recomputed()
        return self._emit_topology_updated()

    def remove_link(self, source: int, target: int) -> dict[str, object]:
        self._validate_router_ids(source, target)
        link_index = self._find_link_index(source, target)
        if link_index is None:
            raise ValueError(f"link {source}-{target} is not configured")

        topology = self.topology()
        removed_link = topology.links[link_index]
        self._apply_topology(self._graph().remove_link(source, target))
        self.event_bus.emit(
            "LINK_REMOVED",
            source=removed_link.source,
            target=removed_link.target,
            message=f"Enlace {removed_link.source} ↔ {removed_link.target} removido",
        )
        self._emit_routes_recomputed()
        return self._emit_topology_updated()

    def apply_layout(self, layout: str) -> dict[str, object]:
        self._apply_topology(self._graph().apply_layout(layout))
        self.event_bus.emit(
            "TOPOLOGY_LAYOUT_UPDATED",
            layout=layout,
            message=f"Layout da topologia atualizado para {layout}",
        )
        return self._emit_topology_updated()

    def generate_random_topology(
        self,
        nodes: int,
        edges: int,
        min_cost: int,
        max_cost: int,
        layout: str,
        connected: bool,
    ) -> dict[str, object]:
        topology = self._graph().generate_random(
            nodes=nodes,
            edges=edges,
            min_cost=min_cost,
            max_cost=max_cost,
            layout=layout,
            connected=connected,
        )
        self._apply_topology(topology)
        self._sync_udp_routers()
        self.event_bus.emit(
            "TOPOLOGY_RANDOM_GENERATED",
            nodes=nodes,
            edges=edges,
            layout=layout,
            message="Grafo random gerado com NetworkX",
        )
        topology_response = self._emit_topology_updated()
        self._emit_routes_recomputed()
        return topology_response

    def recent_events(self) -> list[dict[str, object]]:
        return self.event_bus.recent()

    def subscribe_events(self):
        return self.event_bus.subscribe()

    def unsubscribe_events(self, subscriber) -> None:
        self.event_bus.unsubscribe(subscriber)

    def _next_seq(self) -> int:
        with self._lock:
            self._seq += 1
            return self._seq

    def _validate_router_ids(self, source: int, target: int) -> None:
        router_ids = {router.id for router in self.topology().routers}
        if source not in router_ids:
            raise ValueError(f"source router {source} is not configured")
        if target not in router_ids:
            raise ValueError(f"target router {target} is not configured")

    def _find_link_index(self, source: int, target: int) -> int | None:
        for index, link in enumerate(self.topology().links):
            if {link.source, link.target} == {source, target}:
                return index
        return None

    def _graph(self) -> NetworkXGraphService:
        if self._graph_service is None:
            self._graph_service = NetworkXGraphService.from_config(self.config_dir, rng=self._graph_rng)
        return self._graph_service

    def _apply_topology(self, updated_topology: TopologyConfig) -> None:
        routing_tables = compute_all_routing_tables(updated_topology)
        self._topology = updated_topology
        self._routing_tables = routing_tables
        for router_id, router in self._routers.items():
            if router_id in routing_tables:
                router.routing_table = routing_tables[router_id]

    def _sync_router_addresses(self) -> None:
        addresses = {router.id: (router.ip, router.port) for router in self.topology().routers}
        for router in self._routers.values():
            router.router_addresses = addresses

    def _sync_udp_routers(self) -> None:
        if not self._routers:
            return

        topology = self.topology()
        addresses = {router.id: (router.ip, router.port) for router in topology.routers}
        configured_router_ids = set(addresses)

        for router_id in list(self._routers):
            if router_id not in configured_router_ids:
                self._routers[router_id].stop()
                del self._routers[router_id]

        for router_config in topology.routers:
            router = self._routers.get(router_config.id)
            if router is None:
                router = UdpRouter(
                    config=router_config,
                    router_addresses=addresses,
                    routing_table=self._routing_tables[router_config.id],
                    logger=self.logger,
                    event_bus=self.event_bus,
                    fault_simulator=self.fault_simulator,
                )
                router.start()
                self._routers[router_config.id] = router
                continue

            router.router_addresses = addresses
            router.routing_table = self._routing_tables[router_config.id]

    def _emit_routes_recomputed(self) -> None:
        self.event_bus.emit(
            "ROUTES_RECOMPUTED",
            message="Rotas recalculadas com Dijkstra após mudança no grafo",
        )

    def _emit_topology_updated(self) -> dict[str, object]:
        topology_response = self.topology().to_api_response()
        self.event_bus.emit(
            "TOPOLOGY_UPDATED",
            topology=topology_response,
            message="Topologia atualizada",
        )
        return topology_response
