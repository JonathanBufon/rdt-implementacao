import random

from ..network.packet import Packet


class FaultSimulator:
    def __init__(
        self,
        corruption_rate: float = 0.10,
        rng: random.Random | None = None,
    ) -> None:
        self.corruption_rate = corruption_rate
        self.rng = rng or random.Random()
        self._corrupted_once: set[int] = set()

    def should_corrupt(self, packet: Packet) -> bool:
        if packet.rdt_version != "2.0" or packet.type != "DATA":
            return False

        if packet.seq in self._corrupted_once:
            return False

        should_corrupt = self.rng.random() < self.corruption_rate
        if should_corrupt:
            self._corrupted_once.add(packet.seq)
        return should_corrupt
