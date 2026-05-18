import threading


class StopAndWait:
    def __init__(self):
        self.pending_seq = None
        self.lock = threading.Lock()
        self.ack_event = threading.Event()

    def set_pending(self, seq):
        with self.lock:
            self.pending_seq = seq
            self.ack_event.clear()

    def on_ack(self, seq):
        with self.lock:
            if self.pending_seq == seq:
                self.pending_seq = None
                self.ack_event.set()
                return True
        return False

    def wait_for_ack(self, timeout=3):
        return self.ack_event.wait(timeout=timeout)
