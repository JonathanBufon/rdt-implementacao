from dataclasses import dataclass
from heapq import heappop
from heapq import heappush
from math import inf

from .config_loader import TopologyConfig


@dataclass(frozen=True)
class RouteEntry:
    destination: int
    path: list[int]
    next_hop: int
    cost: int


@dataclass(frozen=True)
class RoutingTable:
    router_id: int
    routes: dict[int, RouteEntry]

    def to_api_response(self) -> dict[str, int | dict[str, dict[str, int | list[int]]]]:
        return {
            "router_id": self.router_id,
            "routes": {
                str(destination): {
                    "path": route.path,
                    "next_hop": route.next_hop,
                    "cost": route.cost,
                }
                for destination, route in sorted(self.routes.items())
            },
        }


def compute_routing_table(topology: TopologyConfig, router_id: int) -> RoutingTable:
    if router_id not in topology.adjacency:
        raise ValueError(f"router {router_id} is not configured")

    distances, previous = dijkstra(topology.adjacency, router_id)
    routes: dict[int, RouteEntry] = {}

    for destination in sorted(topology.adjacency):
        if destination == router_id or distances[destination] == inf:
            continue

        path = _build_path(previous, router_id, destination)
        if len(path) < 2:
            continue

        routes[destination] = RouteEntry(
            destination=destination,
            path=path,
            next_hop=path[1],
            cost=int(distances[destination]),
        )

    return RoutingTable(router_id=router_id, routes=routes)


def compute_all_routing_tables(topology: TopologyConfig) -> dict[int, RoutingTable]:
    return {
        router.id: compute_routing_table(topology, router.id)
        for router in sorted(topology.routers, key=lambda router: router.id)
    }


def dijkstra(
    adjacency: dict[int, dict[int, int]],
    source: int,
) -> tuple[dict[int, float], dict[int, int | None]]:
    distances: dict[int, float] = {router_id: inf for router_id in adjacency}
    previous: dict[int, int | None] = {router_id: None for router_id in adjacency}
    distances[source] = 0

    queue: list[tuple[float, int]] = [(0, source)]
    visited: set[int] = set()

    while queue:
        current_distance, current_router = heappop(queue)
        if current_router in visited:
            continue

        visited.add(current_router)

        for neighbor, cost in adjacency[current_router].items():
            candidate_distance = current_distance + cost
            if candidate_distance < distances[neighbor]:
                distances[neighbor] = candidate_distance
                previous[neighbor] = current_router
                heappush(queue, (candidate_distance, neighbor))

    return distances, previous


def _build_path(
    previous: dict[int, int | None],
    source: int,
    destination: int,
) -> list[int]:
    path: list[int] = []
    current: int | None = destination

    while current is not None:
        path.append(current)
        if current == source:
            break
        current = previous[current]

    path.reverse()

    if not path or path[0] != source:
        return []

    return path
