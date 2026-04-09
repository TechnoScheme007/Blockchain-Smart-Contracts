"""Tests for P2P networking and chain synchronization."""

import time
import unittest

from blockchain.chain import Blockchain
from blockchain.network.node import Node
from blockchain.network.protocol import (
    MessageType,
    decode_message,
    encode_message,
    read_message_from_buffer,
)


class TestProtocol(unittest.TestCase):
    def test_encode_decode(self):
        msg = encode_message(MessageType.HELLO, {"port": 6000})
        buf = bytearray(msg)
        raw, remaining = read_message_from_buffer(buf)
        self.assertIsNotNone(raw)
        msg_type, payload = decode_message(raw)
        self.assertEqual(msg_type, MessageType.HELLO)
        self.assertEqual(payload["port"], 6000)

    def test_incomplete_buffer(self):
        msg = encode_message(MessageType.HELLO, {"port": 6000})
        partial = bytearray(msg[:5])
        raw, buf = read_message_from_buffer(partial)
        self.assertIsNone(raw)

    def test_multiple_messages_in_buffer(self):
        m1 = encode_message(MessageType.HELLO, {"a": 1})
        m2 = encode_message(MessageType.GET_CHAIN)
        buf = bytearray(m1 + m2)
        raw1, buf = read_message_from_buffer(buf)
        raw2, buf = read_message_from_buffer(buf)
        self.assertIsNotNone(raw1)
        self.assertIsNotNone(raw2)
        self.assertEqual(decode_message(raw1)[0], MessageType.HELLO)
        self.assertEqual(decode_message(raw2)[0], MessageType.GET_CHAIN)


class TestNodeSync(unittest.TestCase):
    def test_two_nodes_sync(self):
        bc1 = Blockchain(difficulty=2)
        bc1.mine_block("node1")
        bc1.mine_block("node1")

        node1 = Node("127.0.0.1", 7001, bc1)
        node2 = Node("127.0.0.1", 7002, Blockchain(difficulty=2))

        node1.start()
        node2.start()
        time.sleep(0.5)

        node2.connect_to_peer("127.0.0.1", 7001)
        time.sleep(2)  # allow sync

        # node2 should have synced to node1's chain
        self.assertGreaterEqual(node2.blockchain.height, bc1.height)

        node1.stop()
        node2.stop()

    def test_fork_resolution_via_network(self):
        bc1 = Blockchain(difficulty=2)
        bc2 = Blockchain(difficulty=2)

        # bc1 has a longer chain
        bc1.mine_block("n1")
        bc1.mine_block("n1")
        bc1.mine_block("n1")

        node1 = Node("127.0.0.1", 7003, bc1)
        node2 = Node("127.0.0.1", 7004, bc2)

        node1.start()
        node2.start()
        time.sleep(0.5)

        node2.connect_to_peer("127.0.0.1", 7003)
        time.sleep(2)

        self.assertEqual(node2.blockchain.height, bc1.height)

        node1.stop()
        node2.stop()


if __name__ == "__main__":
    unittest.main()
