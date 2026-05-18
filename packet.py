import json


def make_data(seq, origin, destination, payload, path):
    return {
        "type": "DATA",
        "seq": seq,
        "origin": origin,
        "destination": destination,
        "payload": payload,
        "path": path,
    }


def make_ack(seq, origin, destination):
    return {
        "type": "ACK",
        "seq": seq,
        "origin": origin,
        "destination": destination,
    }


def serialize(packet):
    return json.dumps(packet).encode()


def deserialize(data):
    return json.loads(data.decode())
