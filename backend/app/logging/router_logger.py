from datetime import datetime
from pathlib import Path
from threading import Lock

from ..core.event_bus import EventBus


class RouterLogger:
    def __init__(self, logs_dir: Path, event_bus: EventBus | None = None) -> None:
        self.logs_dir = logs_dir
        self.event_bus = event_bus
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()

    def write(self, router_id: int, event: str, message: str) -> None:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_path = self.logs_dir / f"router_{router_id}.log"
        line = f"[{timestamp}] {event} {message}\n"

        with self._lock:
            with log_path.open("a", encoding="utf-8") as log_file:
                log_file.write(line)
        if self.event_bus is not None:
            self.event_bus.emit(
                "LOG_CREATED",
                router_id=router_id,
                log_event=event,
                line=line.rstrip(),
                message=f"Log {event} criado para Roteador {router_id}",
            )

    def read(self, router_id: int) -> list[str]:
        log_path = self.logs_dir / f"router_{router_id}.log"
        if not log_path.exists():
            return []

        with self._lock:
            return log_path.read_text(encoding="utf-8").splitlines()
