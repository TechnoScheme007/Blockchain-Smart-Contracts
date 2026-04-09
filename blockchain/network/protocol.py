"""Wire protocol for P2P communication over TCP.

Messages are length-prefixed JSON:
    [4 bytes big-endian length][JSON payload]

Message types:
    - HELLO: initial handshake with node info
    - PEERS: exchange known peer addresses
    - GET_CHAIN: request full chain
    - CHAIN: full chain response
    - NEW_BLOCK: broadcast a newly mined block
    - NEW_TX: broadcast a new transaction
"""

from __future__ import annotations

import json
import struct
from enum import Enum
from typing import Any


class MessageType(Enum):
    HELLO = "hello"
    PEERS = "peers"
    GET_PEERS = "get_peers"
    GET_CHAIN = "get_chain"
    CHAIN = "chain"
    NEW_BLOCK = "new_block"
    NEW_TX = "new_tx"


def encode_message(msg_type: MessageType, payload: Any = None) -> bytes:
    data = json.dumps({"type": msg_type.value, "payload": payload}).encode()
    return struct.pack(">I", len(data)) + data


def decode_message(data: bytes) -> tuple[MessageType, Any]:
    obj = json.loads(data.decode())
    return MessageType(obj["type"]), obj.get("payload")


def read_message_from_buffer(buf: bytearray) -> tuple[bytes | None, bytearray]:
    """Try to extract one complete message from buffer.

    Returns (message_bytes, remaining_buffer) or (None, buffer) if incomplete.
    """
    if len(buf) < 4:
        return None, buf
    msg_len = struct.unpack(">I", buf[:4])[0]
    if msg_len > 10 * 1024 * 1024:  # 10MB sanity limit
        raise ValueError(f"Message too large: {msg_len}")
    total = 4 + msg_len
    if len(buf) < total:
        return None, buf
    message = bytes(buf[4:total])
    return message, bytearray(buf[total:])
