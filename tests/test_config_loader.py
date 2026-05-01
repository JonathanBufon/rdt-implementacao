from pathlib import Path

from backend.app.core.config_loader import load_topology


def test_load_topology_from_default_config() -> None:
    topology = load_topology(Path("backend/config"))

    assert len(topology.routers) == 5
    assert len(topology.links) == 6
    assert topology.adjacency[1][2] == 10
    assert topology.adjacency[2][1] == 10
    assert topology.adjacency[4][5] == 2


def test_topology_api_response_shape() -> None:
    response = load_topology(Path("backend/config")).to_api_response()

    assert response["routers"][0] == {"id": 1, "ip": "127.0.0.1", "port": 25001, "x": 0.5, "y": 0.5}
    assert response["links"][0] == {"source": 1, "target": 2, "cost": 10}
    assert response["layout"] == "spring"
    assert response["generated_by"] == "file"
    assert response["is_connected"] is True
