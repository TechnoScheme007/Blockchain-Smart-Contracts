"""Tests for Blockchain: mining, validation, fork resolution."""

import unittest

from blockchain.chain import Blockchain
from blockchain.transaction import Transaction


class TestBlockchain(unittest.TestCase):
    def setUp(self):
        self.bc = Blockchain(difficulty=2)

    def test_genesis_exists(self):
        self.assertEqual(self.bc.height, 1)
        self.assertEqual(self.bc.chain[0].header.index, 0)

    def test_mine_block(self):
        block = self.bc.mine_block("miner1")
        self.assertEqual(self.bc.height, 2)
        self.assertTrue(block.verify_pow())
        self.assertEqual(block.header.previous_hash, self.bc.chain[0].hash)

    def test_balance_after_mining(self):
        self.bc.mine_block("miner1")
        self.assertGreater(self.bc.get_balance("miner1"), 0)

    def test_transaction_flow(self):
        self.bc.mine_block("alice")  # alice gets reward
        tx = Transaction(sender="alice", recipient="bob", amount=10)
        self.bc.add_transaction(tx)
        self.bc.mine_block("alice")
        self.assertEqual(self.bc.get_balance("bob"), 10)

    def test_validate_chain(self):
        self.bc.mine_block("m")
        self.bc.mine_block("m")
        self.assertTrue(self.bc.validate_chain(self.bc.chain))

    def test_fork_resolution_longest_wins(self):
        chain_a = Blockchain(difficulty=2)
        chain_b = Blockchain(difficulty=2)

        # Make chain_b longer
        chain_b.mine_block("b1")
        chain_b.mine_block("b2")
        chain_b.mine_block("b3")

        # chain_a is shorter - should accept chain_b
        replaced = chain_a.replace_chain(chain_b.chain)
        self.assertTrue(replaced)
        self.assertEqual(chain_a.height, chain_b.height)

    def test_fork_resolution_rejects_shorter(self):
        self.bc.mine_block("m")
        self.bc.mine_block("m")
        short_chain = Blockchain(difficulty=2)
        replaced = self.bc.replace_chain(short_chain.chain)
        self.assertFalse(replaced)


if __name__ == "__main__":
    unittest.main()
