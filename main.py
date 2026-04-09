#!/usr/bin/env python3
"""Blockchain node CLI - mine blocks, send transactions, deploy smart contracts."""

from __future__ import annotations

import argparse
import cmd
import logging
import sys
import time

from blockchain.block import Block
from blockchain.chain import Blockchain
from blockchain.network.node import Node
from blockchain.transaction import Transaction, TxType
from blockchain.vm.assembler import assemble, disassemble
from blockchain.vm.vm import VM

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("main")


class BlockchainCLI(cmd.Cmd):
    """Interactive blockchain node shell."""

    intro = (
        "\n"
        "====================================\n"
        "  Proof-of-Work Blockchain Node\n"
        "====================================\n"
        "Type 'help' for available commands.\n"
    )
    prompt = "blockchain> "

    def __init__(self, node: Node, miner_address: str):
        super().__init__()
        self.node = node
        self.miner_address = miner_address

    # -- Mining --

    def do_mine(self, arg):
        """Mine a new block. Usage: mine [num_blocks]"""
        count = int(arg) if arg.strip() else 1
        for i in range(count):
            block = self.node.blockchain.mine_block(self.miner_address)
            self.node.broadcast_block(block)
            print(f"  Block #{block.header.index} mined | hash: {block.hash[:20]}... | nonce: {block.header.nonce}")

    # -- Transactions --

    def do_send(self, arg):
        """Send coins. Usage: send <recipient> <amount>"""
        parts = arg.split()
        if len(parts) != 2:
            print("Usage: send <recipient> <amount>")
            return
        recipient, amount = parts[0], float(parts[1])
        tx = Transaction(
            sender=self.miner_address,
            recipient=recipient,
            amount=amount,
        )
        self.node.blockchain.add_transaction(tx)
        self.node.broadcast_transaction(tx)
        print(f"  Transaction {tx.tx_hash[:16]}... added to pending pool")

    def do_pending(self, arg):
        """Show pending transactions."""
        txs = self.node.blockchain.pending_transactions
        if not txs:
            print("  No pending transactions")
            return
        for tx in txs:
            print(f"  {tx.tx_hash[:16]}... | {tx.sender[:8]}.. -> {tx.recipient[:8]}.. | {tx.amount}")

    # -- Chain info --

    def do_chain(self, arg):
        """Show the blockchain. Usage: chain [last_n]"""
        n = int(arg) if arg.strip() else len(self.node.blockchain.chain)
        blocks = self.node.blockchain.chain[-n:]
        for block in blocks:
            txcount = len(block.transactions)
            print(
                f"  #{block.header.index:>4} | {block.hash[:20]}... | "
                f"txs: {txcount} | nonce: {block.header.nonce} | "
                f"diff: {block.header.difficulty}"
            )

    def do_block(self, arg):
        """Show block details. Usage: block <index>"""
        if not arg.strip():
            print("Usage: block <index>")
            return
        idx = int(arg)
        if idx < 0 or idx >= len(self.node.blockchain.chain):
            print(f"  Block #{idx} not found")
            return
        block = self.node.blockchain.chain[idx]
        print(f"  Block #{block.header.index}")
        print(f"  Hash:       {block.hash}")
        print(f"  Prev Hash:  {block.header.previous_hash}")
        print(f"  Merkle:     {block.header.merkle_root}")
        print(f"  Timestamp:  {block.header.timestamp}")
        print(f"  Difficulty: {block.header.difficulty}")
        print(f"  Nonce:      {block.header.nonce}")
        print(f"  Transactions ({len(block.transactions)}):")
        for tx in block.transactions:
            print(f"    {tx.tx_hash[:16]}... {tx.tx_type.value} | {tx.sender[:8]}.. -> {tx.recipient[:8]}.. | {tx.amount}")

    def do_balance(self, arg):
        """Check balance. Usage: balance [address] (default: your address)"""
        addr = arg.strip() if arg.strip() else self.miner_address
        bal = self.node.blockchain.get_balance(addr)
        print(f"  {addr[:16]}... balance: {bal}")

    def do_height(self, arg):
        """Show current chain height."""
        print(f"  Chain height: {self.node.blockchain.height}")

    def do_difficulty(self, arg):
        """Show or set difficulty. Usage: difficulty [new_value]"""
        if arg.strip():
            self.node.blockchain.difficulty = int(arg)
            print(f"  Difficulty set to {self.node.blockchain.difficulty}")
        else:
            print(f"  Current difficulty: {self.node.blockchain.difficulty}")

    # -- Networking --

    def do_peers(self, arg):
        """List connected peers."""
        if not self.node.peers:
            print("  No connected peers")
            return
        for p in self.node.peers:
            print(f"  {p.address}")

    def do_connect(self, arg):
        """Connect to a peer. Usage: connect <host:port>"""
        if not arg.strip():
            print("Usage: connect <host:port>")
            return
        host, port = arg.strip().split(":")
        self.node.connect_to_peer(host, int(port))
        print(f"  Connected to {arg}")

    # -- Smart Contracts --

    def do_deploy(self, arg):
        """Deploy a smart contract from assembly file. Usage: deploy <filename>"""
        if not arg.strip():
            print("Usage: deploy <filename>")
            print("  Or type assembly interactively: deploy -i")
            return
        if arg.strip() == "-i":
            print("  Enter assembly (empty line to finish):")
            lines = []
            while True:
                line = input("  ... ")
                if not line:
                    break
                lines.append(line)
            source = "\n".join(lines)
        else:
            with open(arg.strip()) as f:
                source = f.read()

        bytecode = assemble(source)
        print(f"  Bytecode ({len(bytecode)} bytes): {bytecode.hex()}")

        tx = Transaction(
            sender=self.miner_address,
            recipient="",
            amount=0,
            tx_type=TxType.CONTRACT_DEPLOY,
            data=bytecode,
        )
        self.node.blockchain.add_transaction(tx)
        contract_addr = tx.tx_hash[:40]
        print(f"  Contract will deploy at: {contract_addr}")
        print("  Mine a block to execute deployment.")

    def do_call(self, arg):
        """Call a deployed contract. Usage: call <contract_addr> <asm_file_or_-i>"""
        parts = arg.split(None, 1)
        if len(parts) < 2:
            print("Usage: call <contract_addr> <filename|-i>")
            return
        contract_addr = parts[0]
        if parts[1].strip() == "-i":
            print("  Enter assembly (empty line to finish):")
            lines = []
            while True:
                line = input("  ... ")
                if not line:
                    break
                lines.append(line)
            source = "\n".join(lines)
        else:
            with open(parts[1].strip()) as f:
                source = f.read()

        bytecode = assemble(source)
        tx = Transaction(
            sender=self.miner_address,
            recipient=contract_addr,
            amount=0,
            tx_type=TxType.CONTRACT_CALL,
            data=bytecode,
        )
        self.node.blockchain.add_transaction(tx)
        print(f"  Call transaction {tx.tx_hash[:16]}... queued")
        print("  Mine a block to execute.")

    def do_storage(self, arg):
        """View contract storage. Usage: storage <contract_addr>"""
        if not arg.strip():
            print("Usage: storage <contract_addr>")
            print("  Known contracts:")
            for addr in self.node.blockchain.contract_storage:
                print(f"    {addr}")
            return
        addr = arg.strip()
        if addr not in self.node.blockchain.contract_storage:
            print(f"  Contract {addr} not found")
            return
        storage = self.node.blockchain.contract_storage[addr]
        if not storage:
            print("  (empty)")
        for k, v in storage.items():
            print(f"  [{k}] = {v}")

    def do_asm(self, arg):
        """Assemble a file and show bytecode. Usage: asm <filename>"""
        if not arg.strip():
            print("Usage: asm <filename>")
            return
        with open(arg.strip()) as f:
            source = f.read()
        bytecode = assemble(source)
        print(f"  Bytecode ({len(bytecode)} bytes): {bytecode.hex()}")
        print(f"  Disassembly:")
        print(disassemble(bytecode))

    def do_vm(self, arg):
        """Execute bytecode directly (hex). Usage: vm <hex_bytecode>"""
        if not arg.strip():
            print("Usage: vm <hex_bytecode>")
            return
        bytecode = bytes.fromhex(arg.strip())
        vm = VM()
        result = vm.execute(bytecode)
        print(f"  Stack: {result}")
        if vm.logs:
            print(f"  Logs:  {vm.logs}")
        if vm.storage:
            print(f"  Storage: {vm.storage}")

    # -- Misc --

    def do_status(self, arg):
        """Show node status."""
        bc = self.node.blockchain
        print(f"  Node:       {self.node.address}")
        print(f"  Address:    {self.miner_address}")
        print(f"  Height:     {bc.height}")
        print(f"  Difficulty: {bc.difficulty}")
        print(f"  Peers:      {len(self.node.peers)}")
        print(f"  Pending TX: {len(bc.pending_transactions)}")
        print(f"  Contracts:  {len(bc.contract_storage)}")
        print(f"  Last block: {bc.last_block.hash[:20]}...")

    def do_quit(self, arg):
        """Exit the node."""
        print("Shutting down...")
        self.node.stop()
        return True

    do_exit = do_quit
    do_EOF = do_quit


def main():
    parser = argparse.ArgumentParser(description="Blockchain Node")
    parser.add_argument("--host", default="127.0.0.1", help="Listen host (default: 127.0.0.1)")
    parser.add_argument("--port", "-p", type=int, default=6000, help="Listen port (default: 6000)")
    parser.add_argument("--difficulty", "-d", type=int, default=4, help="Initial mining difficulty (default: 4)")
    parser.add_argument("--miner", "-m", default="miner_01", help="Miner address/name")
    parser.add_argument("--connect", "-c", nargs="*", default=[], help="Seed peers as host:port")
    parser.add_argument("--mine-only", type=int, metavar="N", help="Mine N blocks and exit (non-interactive)")
    args = parser.parse_args()

    blockchain = Blockchain(difficulty=args.difficulty)
    node = Node(args.host, args.port, blockchain)
    node.start()

    # Connect to seed peers
    seeds = []
    for peer_str in args.connect:
        h, p = peer_str.split(":")
        seeds.append((h, int(p)))
    if seeds:
        node.connect_to_seeds(seeds)
        time.sleep(1)  # allow chain sync

    if args.mine_only:
        for i in range(args.mine_only):
            block = blockchain.mine_block(args.miner)
            node.broadcast_block(block)
            print(f"Block #{block.header.index} mined: {block.hash[:20]}...")
        node.stop()
    else:
        try:
            cli = BlockchainCLI(node, args.miner)
            cli.cmdloop()
        except KeyboardInterrupt:
            print("\nShutting down...")
            node.stop()


if __name__ == "__main__":
    main()
