"""Tests for Block and mining."""

import unittest

from blockchain.block import Block
from blockchain.transaction import Transaction


class TestBlock(unittest.TestCase):
    def test_genesis(self):
        genesis = Block.genesis(difficulty=2)
        self.assertEqual(genesis.header.index, 0)
        self.assertTrue(genesis.hash.startswith("00"))
        self.assertTrue(genesis.verify_pow())

    def test_mine_and_verify(self):
        tx = Transaction(sender="alice", recipient="bob", amount=10)
        block = Block.new(
            index=1,
            previous_hash="0" * 64,
            transactions=[tx],
            difficulty=2,
        )
        block.mine()
        self.assertTrue(block.verify_pow())
        self.assertTrue(block.verify_merkle())

    def test_tampered_block_fails_pow(self):
        block = Block.genesis(difficulty=2)
        block.header.nonce += 1  # tamper
        self.assertFalse(block.verify_pow())

    def test_serialization_roundtrip(self):
        tx = Transaction(sender="alice", recipient="bob", amount=5)
        block = Block.new(index=1, previous_hash="a" * 64, transactions=[tx], difficulty=2)
        block.mine()
        d = block.to_dict()
        restored = Block.from_dict(d)
        self.assertEqual(restored.hash, block.hash)
        self.assertEqual(len(restored.transactions), 1)
        self.assertTrue(restored.verify_pow())


if __name__ == "__main__":
    unittest.main()
