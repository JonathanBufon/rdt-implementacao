from backend.app.network.packet import Packet
from backend.app.network.packet import checksum
from backend.app.network.packet import has_valid_checksum


def test_packet_roundtrip_json_bytes() -> None:
    packet = Packet(
        type="DATA",
        rdt_version="1.0",
        seq=1,
        source=1,
        destination=3,
        current_router=1,
        payload="Teste",
        checksum="abc123",
        path=[1, 2, 3],
    )

    decoded = Packet.from_bytes(packet.to_bytes())

    assert decoded == packet


def test_packet_checksum_validation() -> None:
    packet = Packet(
        type="DATA",
        rdt_version="2.0",
        seq=7,
        source=1,
        destination=2,
        current_router=1,
        payload="Mensagem",
        checksum=checksum(7, 1, 2, "Mensagem"),
        path=[1, 2],
    )

    assert has_valid_checksum(packet)
    assert not has_valid_checksum(packet.with_checksum("invalid"))
