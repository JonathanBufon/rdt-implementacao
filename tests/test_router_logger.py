from pathlib import Path

from backend.app.core.event_bus import EventBus
from backend.app.logging.router_logger import RouterLogger


def test_router_logger_writes_file_and_emits_log_created(tmp_path: Path) -> None:
    event_bus = EventBus()
    logger = RouterLogger(tmp_path, event_bus=event_bus)

    logger.write(1, "SENT", "seq=1 destination=2")

    assert logger.read(1)[0].endswith("SENT seq=1 destination=2")

    event = event_bus.recent()[0]
    assert event["type"] == "LOG_CREATED"
    assert event["router_id"] == 1
    assert event["log_event"] == "SENT"
