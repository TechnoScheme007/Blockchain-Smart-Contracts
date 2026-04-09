"""Merkle tree for transaction integrity verification."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@dataclass
class MerkleNode:
    hash: str
    left: MerkleNode | None = None
    right: MerkleNode | None = None


class MerkleTree:
    """Binary Merkle tree built from a list of data hashes."""

    def __init__(self, leaves: list[str]):
        if not leaves:
            self.root = MerkleNode(hash=sha256(b""))
            return
        nodes = [MerkleNode(hash=h) for h in leaves]
        self.root = self._build(nodes)

    @staticmethod
    def _hash_pair(a: str, b: str) -> str:
        combined = bytes.fromhex(a) + bytes.fromhex(b)
        return sha256(combined)

    def _build(self, nodes: list[MerkleNode]) -> MerkleNode:
        while len(nodes) > 1:
            next_level: list[MerkleNode] = []
            for i in range(0, len(nodes), 2):
                left = nodes[i]
                right = nodes[i + 1] if i + 1 < len(nodes) else left
                parent_hash = self._hash_pair(left.hash, right.hash)
                next_level.append(MerkleNode(hash=parent_hash, left=left, right=right))
            nodes = next_level
        return nodes[0]

    @property
    def root_hash(self) -> str:
        return self.root.hash

    def get_proof(self, index: int, total: int) -> list[tuple[str, str]]:
        """Return Merkle proof as list of (hash, direction) pairs."""
        proof: list[tuple[str, str]] = []
        self._collect_proof(self.root, index, total, proof)
        return proof

    def _collect_proof(
        self,
        node: MerkleNode | None,
        index: int,
        total: int,
        proof: list[tuple[str, str]],
    ) -> bool:
        if node is None:
            return False
        if node.left is None and node.right is None:
            return True

        mid = (total + 1) // 2
        if index < mid:
            if self._collect_proof(node.left, index, mid, proof):
                if node.right:
                    proof.append((node.right.hash, "right"))
                return True
        else:
            if self._collect_proof(node.right, index - mid, total - mid, proof):
                if node.left:
                    proof.append((node.left.hash, "left"))
                return True
        return False

    @staticmethod
    def verify_proof(leaf_hash: str, proof: list[tuple[str, str]], root_hash: str) -> bool:
        current = leaf_hash
        for sibling_hash, direction in proof:
            if direction == "right":
                combined = bytes.fromhex(current) + bytes.fromhex(sibling_hash)
            else:
                combined = bytes.fromhex(sibling_hash) + bytes.fromhex(current)
            current = sha256(combined)
        return current == root_hash
