from ..network.packet import Packet
from ..network.router import UdpRouter
from .base import ReliableDataTransferProtocol

TIMEOUT_SECONDS = 2
MAX_RETRIES = 5


class Rdt3Protocol(ReliableDataTransferProtocol):
    version = "3.0"

    def __init__(
        self,
        timeout_seconds: float = TIMEOUT_SECONDS,
        max_retries: int = MAX_RETRIES,
    ) -> None:
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries

    def send(self, router: UdpRouter, packet: Packet) -> None:
        router.send_stop_and_wait(
            packet=packet,
            timeout_seconds=self.timeout_seconds,
            max_retries=self.max_retries,
        )
