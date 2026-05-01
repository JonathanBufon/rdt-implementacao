from collections import deque
from datetime import datetime
from queue import Queue
from threading import Lock
from typing import Any


class EventBus:
    def __init__(self, max_events: int = 200) -> None:
        self._events: deque[dict[str, Any]] = deque(maxlen=max_events)
        self._subscribers: set[Queue[dict[str, Any]]] = set()
        self._lock = Lock()

    def emit(self, event_type: str, **payload: Any) -> dict[str, Any]:
        event = {
            "type": event_type,
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            **payload,
        }
        with self._lock:
            self._events.append(event)
            subscribers = list(self._subscribers)
        for subscriber in subscribers:
            subscriber.put(event)
        return event

    def recent(self) -> list[dict[str, Any]]:
        with self._lock:
            return list(self._events)

    def subscribe(self) -> Queue[dict[str, Any]]:
        subscriber: Queue[dict[str, Any]] = Queue()
        with self._lock:
            self._subscribers.add(subscriber)
        return subscriber

    def unsubscribe(self, subscriber: Queue[dict[str, Any]]) -> None:
        with self._lock:
            self._subscribers.discard(subscriber)
