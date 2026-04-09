"""Blockchain: chain management, validation, difficulty adjustment, fork resolution."""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field

from .block import Block
from .transaction import Transaction, TxType

logger = logging.getLogger(__name__)

BLOCK_REWARD = 50.0
DIFFICULTY_ADJUSTMENT_INTERVAL = 10  # blocks
TARGET_BLOCK_TIME = 10.0  # seconds


@dataclass
class Blockchain:
    difficulty: int = 4
    chain: list[Block] = field(default_factory=list)
    pending_transactions: list[Transaction] = field(default_factory=list)
    contract_storage: dict[str, dict[str, int]] = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def __post_init__(self):
        if not self.chain:
            genesis = Block.genesis(self.difficulty)
            self.chain.append(genesis)
            logger.info("Genesis block created: %s", genesis.hash[:16])

    @property
    def last_block(self) -> Block:
        return self.chain[-1]

    @property
    def height(self) -> int:
        return len(self.chain)

    def add_transaction(self, tx: Transaction) -> bool:
        if tx.tx_type != TxType.COINBASE and tx.sender == "0" * 64:
            return False
        with self._lock:
            self.pending_transactions.append(tx)
        return True

    def mine_block(self, miner_address: str) -> Block:
        coinbase = Transaction.coinbase(miner_address, BLOCK_REWARD)
        with self._lock:
            transactions = [coinbase] + list(self.pending_transactions)
            self.pending_transactions.clear()

        block = Block.new(
            index=self.height,
            previous_hash=self.last_block.hash,
            transactions=transactions,
            difficulty=self.difficulty,
        )
        logger.info("Mining block #%d (difficulty=%d)...", block.header.index, self.difficulty)
        block.mine()
        logger.info("Block #%d mined: %s", block.header.index, block.hash[:16])

        with self._lock:
            self.chain.append(block)
            self._maybe_adjust_difficulty()
            self._execute_contracts(block)

        return block

    def _maybe_adjust_difficulty(self):
        if self.height % DIFFICULTY_ADJUSTMENT_INTERVAL != 0:
            return
        if self.height < DIFFICULTY_ADJUSTMENT_INTERVAL:
            return

        recent = self.chain[-DIFFICULTY_ADJUSTMENT_INTERVAL:]
        elapsed = recent[-1].header.timestamp - recent[0].header.timestamp
        expected = TARGET_BLOCK_TIME * DIFFICULTY_ADJUSTMENT_INTERVAL

        if elapsed < expected / 2:
            self.difficulty += 1
            logger.info("Difficulty increased to %d", self.difficulty)
        elif elapsed > expected * 2:
            self.difficulty = max(1, self.difficulty - 1)
            logger.info("Difficulty decreased to %d", self.difficulty)

    def _execute_contracts(self, block: Block):
        from .vm.vm import VM

        for tx in block.transactions:
            if tx.tx_type == TxType.CONTRACT_DEPLOY:
                contract_addr = tx.tx_hash[:40]
                self.contract_storage[contract_addr] = {}
                vm = VM(storage=self.contract_storage[contract_addr])
                vm.execute(tx.data)
                logger.info("Contract deployed at %s", contract_addr)
            elif tx.tx_type == TxType.CONTRACT_CALL:
                contract_addr = tx.recipient
                if contract_addr in self.contract_storage:
                    vm = VM(storage=self.contract_storage[contract_addr])
                    vm.execute(tx.data)

    def validate_block(self, block: Block) -> bool:
        if not block.verify_pow():
            logger.warning("Block #%d failed PoW verification", block.header.index)
            return False
        if not block.verify_merkle():
            logger.warning("Block #%d failed Merkle verification", block.header.index)
            return False
        if block.header.index > 0:
            if block.header.index != self.last_block.header.index + 1:
                return False
            if block.header.previous_hash != self.last_block.hash:
                return False
        return True

    def validate_chain(self, chain: list[Block]) -> bool:
        if not chain:
            return False
        for i in range(1, len(chain)):
            block = chain[i]
            prev = chain[i - 1]
            if not block.verify_pow() or not block.verify_merkle():
                return False
            if block.header.previous_hash != prev.hash:
                return False
            if block.header.index != prev.header.index + 1:
                return False
        return True

    def replace_chain(self, new_chain: list[Block]) -> bool:
        """Fork resolution: longest valid chain wins."""
        with self._lock:
            if len(new_chain) <= len(self.chain):
                logger.info("Received chain not longer than current, rejecting")
                return False
            if not self.validate_chain(new_chain):
                logger.warning("Received chain is invalid, rejecting")
                return False
            logger.info(
                "Replacing chain: height %d -> %d",
                len(self.chain),
                len(new_chain),
            )
            self.chain = new_chain
            return True

    def add_block(self, block: Block) -> bool:
        with self._lock:
            if not self.validate_block(block):
                return False
            self.chain.append(block)
            self._execute_contracts(block)
            return True

    def get_balance(self, address: str) -> float:
        balance = 0.0
        for block in self.chain:
            for tx in block.transactions:
                if tx.recipient == address:
                    balance += tx.amount
                if tx.sender == address:
                    balance -= tx.amount
        return balance

    def to_dict_list(self) -> list[dict]:
        return [b.to_dict() for b in self.chain]

    @classmethod
    def from_dict_list(cls, data: list[dict], difficulty: int = 4) -> Blockchain:
        chain = [Block.from_dict(d) for d in data]
        bc = cls.__new__(cls)
        bc.difficulty = difficulty
        bc.chain = chain
        bc.pending_transactions = []
        bc.contract_storage = {}
        bc._lock = threading.Lock()
        return bc
