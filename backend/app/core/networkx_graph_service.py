import random
from itertools import combinations
from pathlib import Path

import networkx as nx

from .config_loader import LinkConfig
from .config_loader import RouterConfig
from .config_loader import TopologyConfig
from .config_loader import build_adjacency
from .config_loader import load_topology

SUPPORTED_LAYOUTS = {"spring", "random", "circular", "shell"}


class NetworkXGraphService:
    def __init__(
        self,
        topology: TopologyConfig,
        layout: str = "spring",
        generated_by: str = "file",
        rng: random.Random | None = None,
    ) -> None:
        self.rng = rng or random.Random()
        self.layout = self._validate_layout(layout)
        self.generated_by = generated_by
        self.routers = sorted(topology.routers, key=lambda router: router.id)
        self.graph = nx.Graph()
        self.graph.add_nodes_from(router.id for router in self.routers)
        for link in topology.links:
            self.graph.add_edge(link.source, link.target, weight=link.cost)
        self.positions = self._calculate_layout(self.layout)

    @classmethod
    def from_config(
        cls,
        config_dir: Path,
        layout: str = "spring",
        rng: random.Random | None = None,
    ) -> "NetworkXGraphService":
        return cls(load_topology(config_dir), layout=layout, generated_by="file", rng=rng)

    def to_topology_config(self) -> TopologyConfig:
        links = [
            LinkConfig(source=int(source), target=int(target), cost=int(data["weight"]))
            for source, target, data in sorted(self.graph.edges(data=True))
        ]
        return TopologyConfig(
            routers=self.routers,
            links=links,
            adjacency=build_adjacency(self.routers, links),
            router_positions=self.positions,
            layout=self.layout,
            generated_by=self.generated_by,
            is_connected=nx.is_connected(self.graph) if self.graph.number_of_nodes() else False,
        )

    def apply_layout(self, layout: str) -> TopologyConfig:
        self.layout = self._validate_layout(layout)
        self.positions = self._calculate_layout(self.layout)
        return self.to_topology_config()

    def update_link_cost(self, source: int, target: int, cost: int) -> TopologyConfig:
        if not self.graph.has_edge(source, target):
            raise ValueError(f"link {source}-{target} is not configured")
        self.graph[source][target]["weight"] = cost
        return self.to_topology_config()

    def create_link(self, source: int, target: int, cost: int) -> TopologyConfig:
        if source == target:
            raise ValueError("source and target must be different")
        if self.graph.has_edge(source, target):
            raise ValueError(f"link {source}-{target} already exists")
        self.graph.add_edge(source, target, weight=cost)
        return self.to_topology_config()

    def remove_link(self, source: int, target: int) -> TopologyConfig:
        if not self.graph.has_edge(source, target):
            raise ValueError(f"link {source}-{target} is not configured")
        self.graph.remove_edge(source, target)
        return self.to_topology_config()

    def generate_random(
        self,
        nodes: int,
        edges: int,
        min_cost: int,
        max_cost: int,
        layout: str = "spring",
        connected: bool = True,
    ) -> TopologyConfig:
        self._validate_random_request(nodes, edges, min_cost, max_cost, connected)
        self.layout = self._validate_layout(layout)
        self.routers = self._routers_for_node_count(nodes)
        node_ids = [router.id for router in self.routers]

        graph = nx.Graph()
        graph.add_nodes_from(node_ids)
        if connected:
            shuffled = list(node_ids)
            self.rng.shuffle(shuffled)
            for index in range(1, len(shuffled)):
                target_index = self.rng.randrange(0, index)
                graph.add_edge(shuffled[index], shuffled[target_index])

        available_edges = [
            edge for edge in combinations(node_ids, 2)
            if not graph.has_edge(edge[0], edge[1])
        ]
        self.rng.shuffle(available_edges)
        for source, target in available_edges[: edges - graph.number_of_edges()]:
            graph.add_edge(source, target)

        for source, target in graph.edges:
            graph[source][target]["weight"] = self.rng.randint(min_cost, max_cost)

        self.graph = graph
        self.generated_by = "random"
        self.positions = self._calculate_layout(self.layout)
        return self.to_topology_config()

    def _routers_for_node_count(self, nodes: int) -> list[RouterConfig]:
        routers_by_id = {router.id: router for router in self.routers}
        routers: list[RouterConfig] = []
        for router_id in range(1, nodes + 1):
            router = routers_by_id.get(router_id)
            if router is None:
                router = RouterConfig(id=router_id, port=25000 + router_id, ip="127.0.0.1")
            routers.append(router)
        return routers

    def _calculate_layout(self, layout: str) -> dict[int, tuple[float, float]]:
        if self.graph.number_of_nodes() == 0:
            return {}
        seed = self.rng.randint(1, 1_000_000)
        if layout == "spring":
            raw_positions = nx.spring_layout(self.graph, weight="weight", seed=seed)
        elif layout == "random":
            raw_positions = nx.random_layout(self.graph, seed=seed)
        elif layout == "circular":
            raw_positions = nx.circular_layout(self.graph)
        elif layout == "shell":
            raw_positions = nx.shell_layout(self.graph)
        else:
            raise ValueError(f"unsupported layout {layout}")
        return self._normalize_positions(raw_positions)

    def _normalize_positions(self, positions: dict[int, object]) -> dict[int, tuple[float, float]]:
        xs = [float(position[0]) for position in positions.values()]
        ys = [float(position[1]) for position in positions.values()]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        span_x = max(max_x - min_x, 0.000001)
        span_y = max(max_y - min_y, 0.000001)
        padding = 0.08
        scale = 1 - padding * 2

        return {
            int(router_id): (
                round(padding + ((float(position[0]) - min_x) / span_x) * scale, 4),
                round(padding + ((float(position[1]) - min_y) / span_y) * scale, 4),
            )
            for router_id, position in positions.items()
        }

    def _validate_layout(self, layout: str) -> str:
        if layout not in SUPPORTED_LAYOUTS:
            raise ValueError(f"layout must be one of: {', '.join(sorted(SUPPORTED_LAYOUTS))}")
        return layout

    def _validate_random_request(
        self,
        nodes: int,
        edges: int,
        min_cost: int,
        max_cost: int,
        connected: bool,
    ) -> None:
        if nodes < 5:
            raise ValueError("nodes must be at least 5")
        max_edges = nodes * (nodes - 1) // 2
        if edges > max_edges:
            raise ValueError(f"edges must be at most {max_edges} for {nodes} nodes")
        if connected and edges < nodes - 1:
            raise ValueError("edges must be at least nodes - 1 when connected is true")
        if min_cost < 1:
            raise ValueError("min_cost must be at least 1")
        if max_cost < min_cost:
            raise ValueError("max_cost must be greater than or equal to min_cost")
