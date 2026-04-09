"""Tests for Merkle tree."""

import unittest

from blockchain.merkle import MerkleTree, sha256


class TestMerkleTree(unittest.TestCase):
    def test_single_leaf(self):
        h = sha256(b"hello")
        tree = MerkleTree([h])
        self.assertEqual(tree.root_hash, h)

    def test_two_leaves(self):
        h1 = sha256(b"a")
        h2 = sha256(b"b")
        tree = MerkleTree([h1, h2])
        expected = sha256(bytes.fromhex(h1) + bytes.fromhex(h2))
        self.assertEqual(tree.root_hash, expected)

    def test_odd_leaves(self):
        leaves = [sha256(str(i).encode()) for i in range(3)]
        tree = MerkleTree(leaves)
        self.assertIsNotNone(tree.root_hash)
        self.assertEqual(len(tree.root_hash), 64)

    def test_empty(self):
        tree = MerkleTree([])
        self.assertEqual(len(tree.root_hash), 64)

    def test_proof_verification(self):
        leaves = [sha256(str(i).encode()) for i in range(4)]
        tree = MerkleTree(leaves)
        for i in range(4):
            proof = tree.get_proof(i, len(leaves))
            self.assertTrue(
                MerkleTree.verify_proof(leaves[i], proof, tree.root_hash),
                f"Proof failed for leaf {i}",
            )

    def test_deterministic(self):
        leaves = [sha256(str(i).encode()) for i in range(5)]
        t1 = MerkleTree(leaves)
        t2 = MerkleTree(leaves)
        self.assertEqual(t1.root_hash, t2.root_hash)


if __name__ == "__main__":
    unittest.main()
