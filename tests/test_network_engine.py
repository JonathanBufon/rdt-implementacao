import socket
import time
from pathlib import Path

import pytest

from backend.app.network.packet import Packet
from backend.app.network.packet import checksum
from backend.app.simulation.network_engine import NetworkEngine


def test_network_engine_sends_data_hop_by_hop(tmp_path: Path) -> None:
    ports = _free_udp_ports(3)
    config_dir = tmp_path / "config"
    logs_dir = tmp_path / "logs"
    config_dir.mkdir()

    (config_dir / "roteador.config").write_text(
        "\n".join(
            [
                f"1 {ports[0]} 127.0.0.1",
                f"2 {ports[1]} 127.0.0.1",
                f"3 {ports[2]} 127.0.0.1",
            ]
        ),
        encoding="utf-8",
    )
    (config_dir / "enlaces.config").write_text("1 2 1\n2 3 1\n", encoding="utf-8")

    engine = NetworkEngine(config_dir=config_dir, logs_dir=logs_dir)
    engine.start()
    try:
        response = engine.send_message(1, 3, "Teste UDP", "1.0")
        assert response["path"] == [1, 2, 3]

        _wait_for_log(logs_dir / "router_3.log", "DELIVERED")
        _wait_for_event(engine, "MESSAGE_DELIVERED")

        assert "SENT" in (logs_dir / "router_1.log").read_text(encoding="utf-8")
        assert "FORWARDED" in (logs_dir / "router_2.log").read_text(encoding="utf-8")
        assert "DELIVERED" in (logs_dir / "router_3.log").read_text(encoding="utf-8")
        assert [event["type"] for event in engine.recent_events()][-1] == "MESSAGE_DELIVERED"
    finally:
        engine.stop()


def test_network_engine_accepts_rdt_2_with_nak_retry_and_ack(tmp_path: Path) -> None:
    ports = _free_udp_ports(2)
    config_dir = tmp_path / "config"
    logs_dir = tmp_path / "logs"
    config_dir.mkdir()

    (config_dir / "roteador.config").write_text(
        f"1 {ports[0]} 127.0.0.1\n2 {ports[1]} 127.0.0.1\n",
        encoding="utf-8",
    )
    (config_dir / "enlaces.config").write_text("1 2 1\n", encoding="utf-8")

    engine = NetworkEngine(config_dir=config_dir, logs_dir=logs_dir, corruption_rate=1.0)
    engine.start()
    try:
        response = engine.send_message(1, 2, "Teste", "2.0")
        assert response["path"] == [1, 2]

        _wait_for_event(engine, "MESSAGE_DELIVERED")
        _wait_for_event(engine, "ACK_RECEIVED")

        events = [event["type"] for event in engine.recent_events()]
        assert "PACKET_CORRUPTED" in events
        assert "NAK_SENT" in events
        assert "NAK_RECEIVED" in events
        assert "MESSAGE_RETRY" in events
        assert "ACK_SENT" in events
        assert "ACK_RECEIVED" in events

        source_log = (logs_dir / "router_1.log").read_text(encoding="utf-8")
        destination_log = (logs_dir / "router_2.log").read_text(encoding="utf-8")
        assert "NAK_RECEIVED" in source_log
        assert "RETRY" in source_log
        assert "ACK_RECEIVED" in source_log
        assert "CORRUPTED" in destination_log
        assert "DELIVERED" in destination_log
    finally:
        engine.stop()


def test_network_engine_rdt_3_retries_after_timeout(tmp_path: Path) -> None:
    ports = _free_udp_ports(2)
    config_dir = tmp_path / "config"
    logs_dir = tmp_path / "logs"
    config_dir.mkdir()

    (config_dir / "roteador.config").write_text(
        f"1 {ports[0]} 127.0.0.1\n2 {ports[1]} 127.0.0.1\n",
        encoding="utf-8",
    )
    (config_dir / "enlaces.config").write_text("1 2 1\n", encoding="utf-8")

    engine = NetworkEngine(
        config_dir=config_dir,
        logs_dir=logs_dir,
        loss_rate=0.50,
        timeout_seconds=0.05,
        max_retries=3,
        rng=SequenceRandom([0.0, 1.0]),
    )
    engine.start()
    try:
        response = engine.send_message(1, 2, "Teste RDT 3", "3.0")
        assert response["path"] == [1, 2]

        _wait_for_event(engine, "MESSAGE_DELIVERED")
        _wait_for_event(engine, "ACK_RECEIVED")

        events = [event["type"] for event in engine.recent_events()]
        assert "PACKET_DROPPED" in events
        assert "TIMEOUT" in events
        assert "MESSAGE_RETRY" in events
        assert "ACK_SENT" in events
        assert "ACK_RECEIVED" in events

        source_log = (logs_dir / "router_1.log").read_text(encoding="utf-8")
        destination_log = (logs_dir / "router_2.log").read_text(encoding="utf-8")
        assert "TIMEOUT" in source_log
        assert "RETRY" in source_log
        assert "ACK_RECEIVED" in source_log
        assert "DROPPED" in destination_log
        assert "DELIVERED" in destination_log
    finally:
        engine.stop()


def test_network_engine_updates_simulation_settings(tmp_path: Path) -> None:
    config_dir = tmp_path / "config"
    logs_dir = tmp_path / "logs"
    config_dir.mkdir()
    logs_dir.mkdir()

    (config_dir / "roteador.config").write_text("1 25001 127.0.0.1\n2 25002 127.0.0.1\n", encoding="utf-8")
    (config_dir / "enlaces.config").write_text("1 2 1\n", encoding="utf-8")

    engine = NetworkEngine(config_dir=config_dir, logs_dir=logs_dir)
    settings = engine.update_simulation_settings(
        loss_rate=1.0,
        corruption_rate=0.0,
        timeout_seconds=0.5,
        max_retries=2,
    )

    assert settings == {
        "loss_rate": 1.0,
        "corruption_rate": 0.0,
        "timeout_seconds": 0.5,
        "max_retries": 2,
    }
    assert engine.fault_simulator.should_drop(_packet("3.0")) is True
    assert engine.fault_simulator.should_corrupt(_packet("2.0")) is False
    assert engine.recent_events()[-1]["type"] == "SIMULATION_SETTINGS_UPDATED"


def test_network_engine_updates_link_cost_and_recomputes_routes(tmp_path: Path) -> None:
    config_dir = tmp_path / "config"
    logs_dir = tmp_path / "logs"
    config_dir.mkdir()
    logs_dir.mkdir()

    (config_dir / "roteador.config").write_text(
        "1 25001 127.0.0.1\n2 25002 127.0.0.1\n3 25003 127.0.0.1\n",
        encoding="utf-8",
    )
    (config_dir / "enlaces.config").write_text("1 2 1\n2 3 1\n1 3 10\n", encoding="utf-8")

    engine = NetworkEngine(config_dir=config_dir, logs_dir=logs_dir)
    assert engine.routing_table(1).routes[3].path == [1, 2, 3]

    topology = engine.update_link_cost(1, 3, 1)

    assert {"source": 1, "target": 3, "cost": 1} in topology["links"]
    assert engine.routing_table(1).routes[3].path == [1, 3]
    assert [event["type"] for event in engine.recent_events()][-3:] == [
        "LINK_COST_UPDATED",
        "ROUTES_RECOMPUTED",
        "TOPOLOGY_UPDATED",
    ]


def test_network_engine_generates_random_topology_with_networkx(tmp_path: Path) -> None:
    config_dir = tmp_path / "config"
    logs_dir = tmp_path / "logs"
    config_dir.mkdir()
    logs_dir.mkdir()

    (config_dir / "roteador.config").write_text(
        "\n".join(
            [
                "1 25001 127.0.0.1",
                "2 25002 127.0.0.1",
                "3 25003 127.0.0.1",
                "4 25004 127.0.0.1",
                "5 25005 127.0.0.1",
            ]
        ),
        encoding="utf-8",
    )
    (config_dir / "enlaces.config").write_text("1 2 1\n2 3 1\n3 4 1\n4 5 1\n", encoding="utf-8")

    engine = NetworkEngine(config_dir=config_dir, logs_dir=logs_dir)
    topology = engine.generate_random_topology(
        nodes=5,
        edges=6,
        min_cost=1,
        max_cost=20,
        layout="random",
        connected=True,
    )

    assert topology["generated_by"] == "random"
    assert topology["layout"] == "random"
    assert topology["is_connected"] is True
    assert len(topology["routers"]) == 5
    assert len(topology["links"]) == 6
    assert all(0 <= router["x"] <= 1 and 0 <= router["y"] <= 1 for router in topology["routers"])
    assert [event["type"] for event in engine.recent_events()][-3:] == [
        "TOPOLOGY_RANDOM_GENERATED",
        "TOPOLOGY_UPDATED",
        "ROUTES_RECOMPUTED",
    ]


def test_network_engine_applies_networkx_layout(tmp_path: Path) -> None:
    config_dir = tmp_path / "config"
    logs_dir = tmp_path / "logs"
    config_dir.mkdir()
    logs_dir.mkdir()

    (config_dir / "roteador.config").write_text(
        "1 25001 127.0.0.1\n2 25002 127.0.0.1\n3 25003 127.0.0.1\n4 25004 127.0.0.1\n5 25005 127.0.0.1\n",
        encoding="utf-8",
    )
    (config_dir / "enlaces.config").write_text("1 2 1\n2 3 1\n3 4 1\n4 5 1\n", encoding="utf-8")

    engine = NetworkEngine(config_dir=config_dir, logs_dir=logs_dir)
    topology = engine.apply_layout("circular")

    assert topology["layout"] == "circular"
    assert all(0 <= router["x"] <= 1 and 0 <= router["y"] <= 1 for router in topology["routers"])
    assert engine.recent_events()[-2]["type"] == "TOPOLOGY_LAYOUT_UPDATED"
    assert engine.recent_events()[-1]["type"] == "TOPOLOGY_UPDATED"


def test_network_engine_creates_and_removes_links(tmp_path: Path) -> None:
    ports = _free_udp_ports(3)
    config_dir = tmp_path / "config"
    logs_dir = tmp_path / "logs"
    config_dir.mkdir()

    (config_dir / "roteador.config").write_text(
        f"1 {ports[0]} 127.0.0.1\n2 {ports[1]} 127.0.0.1\n3 {ports[2]} 127.0.0.1\n",
        encoding="utf-8",
    )
    (config_dir / "enlaces.config").write_text("1 2 1\n", encoding="utf-8")

    engine = NetworkEngine(config_dir=config_dir, logs_dir=logs_dir)
    engine.start()
    try:
        engine.create_link(2, 3, 1)
        assert engine.routing_table(1).routes[3].path == [1, 2, 3]

        engine.remove_link(2, 3)
        assert 3 not in engine.routing_table(1).routes
        with pytest.raises(ValueError, match="no route from 1 to 3"):
            engine.send_message(1, 3, "sem rota", "1.0")
    finally:
        engine.stop()


def _free_udp_ports(count: int) -> list[int]:
    sockets = []
    try:
        for _ in range(count):
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.bind(("127.0.0.1", 0))
            sockets.append(sock)
        return [sock.getsockname()[1] for sock in sockets]
    finally:
        for sock in sockets:
            sock.close()


def _wait_for_log(path: Path, text: str) -> None:
    deadline = time.time() + 2
    while time.time() < deadline:
        if path.exists() and text in path.read_text(encoding="utf-8"):
            return
        time.sleep(0.05)
    raise AssertionError(f"{text!r} not found in {path}")


def _wait_for_event(engine: NetworkEngine, event_type: str) -> None:
    deadline = time.time() + 2
    while time.time() < deadline:
        if any(event["type"] == event_type for event in engine.recent_events()):
            return
        time.sleep(0.05)
    raise AssertionError(f"{event_type!r} event not emitted")


class SequenceRandom:
    def __init__(self, values: list[float]) -> None:
        self.values = values
        self.index = 0

    def random(self) -> float:
        if self.index >= len(self.values):
            return self.values[-1]

        value = self.values[self.index]
        self.index += 1
        return value


def _packet(rdt_version: str) -> Packet:
    return Packet(
        type="DATA",
        rdt_version=rdt_version,
        seq=1,
        source=1,
        destination=2,
        current_router=1,
        payload="teste",
        checksum=checksum(1, 1, 2, "teste"),
        path=[1, 2],
        attempt=1,
    )
