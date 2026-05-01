from backend.app.network.packet import Packet


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
