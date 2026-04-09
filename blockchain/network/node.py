"""P2P node: TCP server, peer discovery, chain synchronization."""

from __future__ import annotations

import json
import logging
import socket
import struct
import threading
import time
from dataclasses import dataclass, field

from ..block import Block
from ..chain import Blockchain
from ..transaction import Transaction
from .protocol import MessageType, decode_message, encode_message, read_message_from_buffer

logger = logging.getLogger(__name__)


@dataclass
class Peer:
    host: str
    port: int

    @property
    def address(self) -> str:
        return f"{self.host}:{self.port}"

    def __hash__(self):
        return hash(self.address)

    def __eq__(self, other):
        if isinstance(other, Peer):
            return self.address == other.address
        return False


class Node:
    """A blockchain P2P node that listens on TCP and connects to peers."""

    def __init__(self, host: str, port: int, blockchain: Blockchain | None = None):
        self.host = host
        self.port = port
        self.blockchain = blockchain or Blockchain()
        self.peers: set[Peer] = set()
        self.known_blocks: set[str] = set()
        self.known_txs: set[str] = set()
        self._server_socket: socket.socket | None = None
        self._running = False
        self._threads: list[threading.Thread] = []

    @property
    def address(self) -> str:
        return f"{self.host}:{self.port}"

    def start(self):
        self._running = True
        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server_socket.settimeout(1.0)
        self._server_socket.bind((self.host, self.port))
        self._server_socket.listen(50)

        t = threading.Thread(target=self._accept_loop, daemon=True)
        t.start()
        self._threads.append(t)

        logger.info("Node listening on %s:%d", self.host, self.port)

    def stop(self):
        self._running = False
        if self._server_socket:
            self._server_socket.close()
        for t in self._threads:
            t.join(timeout=3)
        logger.info("Node stopped")

    def connect_to_peer(self, host: str, port: int):
        peer = Peer(host, port)
        if peer in self.peers or peer.address == self.address:
            return
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5.0)
            sock.connect((host, port))
            self.peers.add(peer)
            logger.info("Connected to peer %s", peer.address)

            # Send hello
            hello = encode_message(MessageType.HELLO, {
                "host": self.host,
                "port": self.port,
                "height": self.blockchain.height,
            })
            sock.sendall(hello)

            # Handle peer in background
            t = threading.Thread(target=self._handle_connection, args=(sock, peer), daemon=True)
            t.start()
            self._threads.append(t)

            # Request chain if peer is ahead
            self._request_chain(sock)
            # Request peers
            sock.sendall(encode_message(MessageType.GET_PEERS))
        except (ConnectionRefusedError, TimeoutError, OSError) as e:
            logger.warning("Failed to connect to %s: %s", peer.address, e)

    def connect_to_seeds(self, seeds: list[tuple[str, int]]):
        for host, port in seeds:
            self.connect_to_peer(host, port)

    def broadcast_block(self, block: Block):
        self.known_blocks.add(block.hash)
        msg = encode_message(MessageType.NEW_BLOCK, block.to_dict())
        self._broadcast(msg)

    def broadcast_transaction(self, tx: Transaction):
        self.known_txs.add(tx.tx_hash)
        msg = encode_message(MessageType.NEW_TX, tx.to_dict())
        self._broadcast(msg)

    def _broadcast(self, msg: bytes):
        for peer in list(self.peers):
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(3.0)
                sock.connect((peer.host, peer.port))
                sock.sendall(msg)
                sock.close()
            except OSError:
                logger.debug("Failed to broadcast to %s", peer.address)

    def _accept_loop(self):
        while self._running:
            try:
                conn, addr = self._server_socket.accept()
                peer = Peer(addr[0], addr[1])
                logger.debug("Incoming connection from %s", peer.address)
                t = threading.Thread(
                    target=self._handle_connection, args=(conn, peer), daemon=True
                )
                t.start()
                self._threads.append(t)
            except socket.timeout:
                continue
            except OSError:
                break

    def _handle_connection(self, sock: socket.socket, peer: Peer):
        buf = bytearray()
        sock.settimeout(30.0)
        try:
            while self._running:
                try:
                    data = sock.recv(4096)
                    if not data:
                        break
                    buf.extend(data)

                    while True:
                        msg_bytes, buf = read_message_from_buffer(buf)
                        if msg_bytes is None:
                            break
                        self._handle_message(sock, peer, msg_bytes)
                except socket.timeout:
                    continue
                except (ConnectionResetError, BrokenPipeError):
                    break
        finally:
            sock.close()
            self.peers.discard(peer)

    def _handle_message(self, sock: socket.socket, peer: Peer, raw: bytes):
        msg_type, payload = decode_message(raw)

        if msg_type == MessageType.HELLO:
            remote_peer = Peer(payload["host"], payload["port"])
            self.peers.add(remote_peer)
            logger.info("Hello from %s (height=%d)", remote_peer.address, payload["height"])
            if payload["height"] > self.blockchain.height:
                self._request_chain(sock)

        elif msg_type == MessageType.GET_PEERS:
            peer_list = [{"host": p.host, "port": p.port} for p in self.peers]
            sock.sendall(encode_message(MessageType.PEERS, peer_list))

        elif msg_type == MessageType.PEERS:
            for p in payload:
                new_peer = Peer(p["host"], p["port"])
                if new_peer.address != self.address and new_peer not in self.peers:
                    self.connect_to_peer(p["host"], p["port"])

        elif msg_type == MessageType.GET_CHAIN:
            chain_data = self.blockchain.to_dict_list()
            sock.sendall(encode_message(MessageType.CHAIN, chain_data))

        elif msg_type == MessageType.CHAIN:
            chain = [Block.from_dict(b) for b in payload]
            if self.blockchain.replace_chain(chain):
                logger.info("Chain synchronized to height %d", len(chain))

        elif msg_type == MessageType.NEW_BLOCK:
            block = Block.from_dict(payload)
            if block.hash not in self.known_blocks:
                self.known_blocks.add(block.hash)
                if self.blockchain.add_block(block):
                    logger.info("Accepted new block #%d from peer", block.header.index)
                    self._broadcast(encode_message(MessageType.NEW_BLOCK, payload))
                else:
                    # Block doesn't fit; maybe we're behind - request full chain
                    self._request_chain(sock)

        elif msg_type == MessageType.NEW_TX:
            tx = Transaction.from_dict(payload)
            if tx.tx_hash not in self.known_txs:
                self.known_txs.add(tx.tx_hash)
                self.blockchain.add_transaction(tx)
                self._broadcast(encode_message(MessageType.NEW_TX, payload))

    def _request_chain(self, sock: socket.socket):
        try:
            sock.sendall(encode_message(MessageType.GET_CHAIN))
        except OSError:
            pass
