import socket
import time
from pathlib import Path

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

        assert "SENT" in (logs_dir / "router_1.log").read_text(encoding="utf-8")
        assert "FORWARDED" in (logs_dir / "router_2.log").read_text(encoding="utf-8")
        assert "DELIVERED" in (logs_dir / "router_3.log").read_text(encoding="utf-8")
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
