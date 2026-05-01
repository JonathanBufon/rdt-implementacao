from pathlib import Path

import pytest

from backend.app.core.config_loader import load_topology
from backend.app.core.routing import compute_all_routing_tables
from backend.app.core.routing import compute_routing_table


def test_compute_shortest_route_from_router_1_to_5() -> None:
    topology = load_topology(Path("backend/config"))

    table = compute_routing_table(topology, 1)
    route = table.routes[5]

    assert route.path == [1, 2, 4, 5]
    assert route.next_hop == 2
    assert route.cost == 17


def test_compute_all_routing_tables() -> None:
    topology = load_topology(Path("backend/config"))

    tables = compute_all_routing_tables(topology)

    assert set(tables) == {1, 2, 3, 4, 5}
    assert tables[5].routes[1].path == [5, 4, 2, 1]
    assert tables[5].routes[1].next_hop == 4
    assert tables[5].routes[1].cost == 17


def test_routing_table_api_response_shape() -> None:
    topology = load_topology(Path("backend/config"))

    response = compute_routing_table(topology, 1).to_api_response()

    assert response["router_id"] == 1
    assert response["routes"]["5"] == {
        "path": [1, 2, 4, 5],
        "next_hop": 2,
        "cost": 17,
    }


def test_unknown_router_fails() -> None:
    topology = load_topology(Path("backend/config"))

    with pytest.raises(ValueError, match="router 99 is not configured"):
        compute_routing_table(topology, 99)
