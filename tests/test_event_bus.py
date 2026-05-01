from queue import Empty

from backend.app.core.event_bus import EventBus


def test_event_bus_keeps_recent_events_and_notifies_subscribers() -> None:
    event_bus = EventBus()
    subscriber = event_bus.subscribe()

    event = event_bus.emit("MESSAGE_SENT", seq=1, router_id=1, message="sent")

    assert event_bus.recent() == [event]
    assert subscriber.get_nowait() == event

    event_bus.unsubscribe(subscriber)
    event_bus.emit("MESSAGE_DELIVERED", seq=1, router_id=2, message="delivered")

    try:
        subscriber.get_nowait()
    except Empty:
        pass
    else:
        raise AssertionError("unsubscribed listener should not receive events")
