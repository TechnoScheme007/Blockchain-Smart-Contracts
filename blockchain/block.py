"""Block structure with SHA-256 proof-of-work mining."""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field

from .merkle import MerkleTree
from .transaction import Transaction


@dataclass
class BlockHeader:
    index: int
    previous_hash: str
    merkle_root: str
    timestamp: float
    difficulty: int
    nonce: int = 0

    def compute_hash(self) -> str:
        header_bytes = json.dumps(
            {
                "index": self.index,
                "previous_hash": self.previous_hash,
                "merkle_root": self.merkle_root,
                "timestamp": self.timestamp,
                "difficulty": self.difficulty,
                "nonce": self.nonce,
            },
            sort_keys=True,
        ).encode()
        return hashlib.sha256(header_bytes).hexdigest()


@dataclass
class Block:
    header: BlockHeader
    transactions: list[Transaction] = field(default_factory=list)
    hash: str = ""

    @classmethod
    def new(
        cls,
        index: int,
        previous_hash: str,
        transactions: list[Transaction],
        difficulty: int,
    ) -> Block:
        tx_hashes = [tx.tx_hash for tx in transactions]
        merkle = MerkleTree(tx_hashes)
        header = BlockHeader(
            index=index,
            previous_hash=previous_hash,
            merkle_root=merkle.root_hash,
            timestamp=time.time(),
            difficulty=difficulty,
        )
        return cls(header=header, transactions=transactions)

    def mine(self) -> str:
        """Perform proof-of-work: find nonce such that hash has `difficulty` leading zeros."""
        target = "0" * self.header.difficulty
        while True:
            h = self.header.compute_hash()
            if h.startswith(target):
                self.hash = h
                return h
            self.header.nonce += 1

    def verify_pow(self) -> bool:
        target = "0" * self.header.difficulty
        return (
            self.hash == self.header.compute_hash()
            and self.hash.startswith(target)
        )

    def verify_merkle(self) -> bool:
        tx_hashes = [tx.tx_hash for tx in self.transactions]
        merkle = MerkleTree(tx_hashes)
        return merkle.root_hash == self.header.merkle_root

    def to_dict(self) -> dict:
        return {
            "header": {
                "index": self.header.index,
                "previous_hash": self.header.previous_hash,
                "merkle_root": self.header.merkle_root,
                "timestamp": self.header.timestamp,
                "difficulty": self.header.difficulty,
                "nonce": self.header.nonce,
            },
            "transactions": [tx.to_dict() for tx in self.transactions],
            "hash": self.hash,
        }

    @classmethod
    def from_dict(cls, d: dict) -> Block:
        h = d["header"]
        header = BlockHeader(
            index=h["index"],
            previous_hash=h["previous_hash"],
            merkle_root=h["merkle_root"],
            timestamp=h["timestamp"],
            difficulty=h["difficulty"],
            nonce=h["nonce"],
        )
        transactions = [Transaction.from_dict(tx) for tx in d["transactions"]]
        return cls(header=header, transactions=transactions, hash=d["hash"])

    @classmethod
    def genesis(cls, difficulty: int = 4) -> Block:
        block = cls.new(
            index=0,
            previous_hash="0" * 64,
            transactions=[],
            difficulty=difficulty,
        )
        block.mine()
        return block
