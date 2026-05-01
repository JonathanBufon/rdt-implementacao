from abc import ABC
from abc import abstractmethod

from ..network.packet import Packet
from ..network.router import UdpRouter


class ReliableDataTransferProtocol(ABC):
    version: str

    @abstractmethod
    def send(self, router: UdpRouter, packet: Packet) -> None:
        """Send a packet using the concrete RDT protocol."""
