import json
from dataclasses import asdict
from dataclasses import dataclass
from hashlib import sha256
from typing import Literal


PacketType = Literal["DATA", "ACK", "NAK"]


@dataclass(frozen=True)
class Packet:
    type: PacketType
    rdt_version: str
    seq: int
    source: int
    destination: int
    current_router: int
    payload: str
    checksum: str
    path: list[int]
    attempt: int = 1

    def to_bytes(self) -> bytes:
        return json.dumps(asdict(self), ensure_ascii=False).encode("utf-8")

    @classmethod
    def from_bytes(cls, data: bytes) -> "Packet":
        payload = json.loads(data.decode("utf-8"))
        return cls(
            type=payload["type"],
            rdt_version=payload["rdt_version"],
            seq=int(payload["seq"]),
            source=int(payload["source"]),
            destination=int(payload["destination"]),
            current_router=int(payload["current_router"]),
            payload=payload["payload"],
            checksum=payload["checksum"],
            path=[int(router_id) for router_id in payload["path"]],
            attempt=int(payload.get("attempt", 1)),
        )

    def at_router(self, router_id: int) -> "Packet":
        return Packet(
            type=self.type,
            rdt_version=self.rdt_version,
            seq=self.seq,
            source=self.source,
            destination=self.destination,
            current_router=router_id,
            payload=self.payload,
            checksum=self.checksum,
            path=self.path,
            attempt=self.attempt,
        )

    def with_checksum(self, checksum: str) -> "Packet":
        return Packet(
            type=self.type,
            rdt_version=self.rdt_version,
            seq=self.seq,
            source=self.source,
            destination=self.destination,
            current_router=self.current_router,
            payload=self.payload,
            checksum=checksum,
            path=self.path,
            attempt=self.attempt,
        )

    def with_attempt(self, attempt: int) -> "Packet":
        return Packet(
            type=self.type,
            rdt_version=self.rdt_version,
            seq=self.seq,
            source=self.source,
            destination=self.destination,
            current_router=self.current_router,
            payload=self.payload,
            checksum=self.checksum,
            path=self.path,
            attempt=attempt,
        )


def checksum(seq: int, source: int, destination: int, payload: str) -> str:
    content = f"{seq}:{source}:{destination}:{payload}".encode("utf-8")
    return sha256(content).hexdigest()


def has_valid_checksum(packet: Packet) -> bool:
    return packet.checksum == checksum(
        seq=packet.seq,
        source=packet.source,
        destination=packet.destination,
        payload=packet.payload,
    )
