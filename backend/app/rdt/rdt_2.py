from ..network.packet import Packet
from ..network.router import UdpRouter
from .base import ReliableDataTransferProtocol


class Rdt2Protocol(ReliableDataTransferProtocol):
    version = "2.0"

    def send(self, router: UdpRouter, packet: Packet) -> None:
        router.send_initial(packet)
