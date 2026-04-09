"""Transaction model for the blockchain."""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from enum import Enum


class TxType(Enum):
    TRANSFER = "transfer"
    CONTRACT_DEPLOY = "contract_deploy"
    CONTRACT_CALL = "contract_call"
    COINBASE = "coinbase"


@dataclass
class Transaction:
    sender: str
    recipient: str
    amount: float
    tx_type: TxType = TxType.TRANSFER
    data: bytes = field(default_factory=bytes)  # bytecode for contracts
    timestamp: float = field(default_factory=time.time)
    nonce: int = 0

    @property
    def tx_hash(self) -> str:
        payload = json.dumps(
            {
                "sender": self.sender,
                "recipient": self.recipient,
                "amount": self.amount,
                "tx_type": self.tx_type.value,
                "data": self.data.hex(),
                "timestamp": self.timestamp,
                "nonce": self.nonce,
            },
            sort_keys=True,
        ).encode()
        return hashlib.sha256(payload).hexdigest()

    def to_dict(self) -> dict:
        return {
            "sender": self.sender,
            "recipient": self.recipient,
            "amount": self.amount,
            "tx_type": self.tx_type.value,
            "data": self.data.hex(),
            "timestamp": self.timestamp,
            "nonce": self.nonce,
            "tx_hash": self.tx_hash,
        }

    @classmethod
    def from_dict(cls, d: dict) -> Transaction:
        return cls(
            sender=d["sender"],
            recipient=d["recipient"],
            amount=d["amount"],
            tx_type=TxType(d["tx_type"]),
            data=bytes.fromhex(d["data"]),
            timestamp=d["timestamp"],
            nonce=d["nonce"],
        )

    @classmethod
    def coinbase(cls, recipient: str, reward: float) -> Transaction:
        return cls(
            sender="0" * 64,
            recipient=recipient,
            amount=reward,
            tx_type=TxType.COINBASE,
        )
