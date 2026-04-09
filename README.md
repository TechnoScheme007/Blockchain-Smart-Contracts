# Proof-of-Work Blockchain with Smart Contract VM

A from-scratch blockchain implementation in Python featuring SHA-256 mining, Merkle trees, P2P networking, and a stack-based virtual machine for smart contracts.

## Features

- **Proof-of-Work Mining** — SHA-256 hashing with adjustable difficulty and automatic difficulty adjustment
- **Merkle Trees** — Transaction integrity verification with proof generation and verification
- **P2P Networking** — TCP-based node discovery, peer exchange, and message protocol
- **Chain Synchronization** — Full chain sync with fork resolution (longest valid chain wins)
- **Stack-based VM** — Bytecode execution engine with arithmetic, logic, storage, and control flow
- **Smart Contracts** — Deploy and call contracts stored as bytecode in transactions
- **Interactive CLI** — Mine, transact, deploy contracts, and manage peers from a shell

## Project Structure

```
blockchain/
├── main.py                      # CLI entry point
├── blockchain/
│   ├── block.py                 # Block + BlockHeader with PoW mining
│   ├── chain.py                 # Blockchain, validation, fork resolution
│   ├── merkle.py                # Merkle tree with proof generation
│   ├── transaction.py           # Transaction model (transfer, coinbase, contracts)
│   ├── network/
│   │   ├── node.py              # P2P TCP node, peer management, chain sync
│   │   └── protocol.py          # Length-prefixed JSON wire protocol
│   └── vm/
│       ├── opcodes.py           # Bytecode instruction set
│       ├── vm.py                # Stack-based execution engine
│       └── assembler.py         # Human-readable assembly <-> bytecode
├── examples/
│   ├── counter.asm              # Counter contract (increments on each call)
│   ├── calculator.asm           # Arithmetic example
│   └── fibonacci.asm            # Fibonacci computation using storage
└── tests/
    ├── test_merkle.py
    ├── test_block.py
    ├── test_chain.py
    ├── test_vm.py
    └── test_network.py
```

## Quick Start

**Requirements:** Python 3.10+ (no external dependencies)

### Run a single node

```bash
python main.py --port 6000 --miner alice --difficulty 4
```

### Run a multi-node network

Terminal 1:
```bash
python main.py --port 6000 --miner alice
```

Terminal 2:
```bash
python main.py --port 6001 --miner bob --connect 127.0.0.1:6000
```

Terminal 3:
```bash
python main.py --port 6002 --miner charlie --connect 127.0.0.1:6000
```

### Non-interactive mining

```bash
python main.py --port 6000 --miner alice --mine-only 10
```

## CLI Commands

| Command | Description |
|---------|-------------|
| `mine [n]` | Mine n blocks (default: 1) |
| `send <addr> <amount>` | Send coins to an address |
| `balance [addr]` | Check balance |
| `chain [n]` | Show last n blocks |
| `block <index>` | Show block details |
| `height` | Current chain height |
| `difficulty [n]` | Show or set mining difficulty |
| `pending` | Show pending transactions |
| `peers` | List connected peers |
| `connect <host:port>` | Connect to a peer |
| `deploy <file\|-i>` | Deploy a smart contract |
| `call <addr> <file\|-i>` | Call a deployed contract |
| `storage [addr]` | View contract storage |
| `asm <file>` | Assemble and show bytecode |
| `vm <hex>` | Execute raw bytecode |
| `status` | Node status summary |
| `quit` | Exit |

## Smart Contract VM

The VM is a stack-based bytecode interpreter with 24 opcodes:

### Instruction Set

| Category | Opcodes |
|----------|---------|
| **Stack** | `PUSH`, `POP`, `DUP`, `SWAP` |
| **Arithmetic** | `ADD`, `SUB`, `MUL`, `DIV`, `MOD` |
| **Comparison** | `EQ`, `LT`, `GT`, `NOT` |
| **Bitwise** | `AND`, `OR`, `XOR` |
| **Control** | `JUMP`, `JUMPI`, `HALT`, `NOP` |
| **Storage** | `SSTORE`, `SLOAD` |
| **Environment** | `CALLER`, `CALLVALUE` |
| **Debug** | `LOG` |

### Example: Deploy a counter contract

```bash
blockchain> deploy examples/counter.asm
  Bytecode (37 bytes): 01000000000051010000000110010000000004010000000099005001000000005170042
  Contract will deploy at: a1b2c3d4...
  Mine a block to execute deployment.

blockchain> mine
  Block #1 mined | hash: 0000a3f2...

blockchain> storage a1b2c3d4...
  [0] = 1

blockchain> call a1b2c3d4... examples/counter.asm
blockchain> mine
blockchain> storage a1b2c3d4...
  [0] = 2
```

### Write assembly

```asm
# Compute 10 + 20, store in slot 0
PUSH 10
PUSH 20
ADD
PUSH 0        ; storage key
SWAP
SSTORE        ; storage[0] = 30
HALT
```

## Architecture

### Mining & Difficulty

- Blocks require SHA-256 hashes with `difficulty` leading zeros
- Difficulty auto-adjusts every 10 blocks toward a 10-second target block time
- Coinbase transaction rewards the miner 50 coins per block

### Merkle Tree

- Binary tree built from transaction hashes
- Odd leaf count: last leaf is duplicated
- Supports proof generation and verification for SPV-style validation

### P2P Protocol

Length-prefixed JSON over TCP:

```
[4 bytes: message length][JSON payload]
```

Message types: `HELLO`, `GET_PEERS`, `PEERS`, `GET_CHAIN`, `CHAIN`, `NEW_BLOCK`, `NEW_TX`

### Fork Resolution

When a node receives a longer valid chain, it replaces its own (longest chain wins). On receiving a block that doesn't fit, the node requests the full chain from that peer.

## Tests

```bash
python -m pytest tests/ -v -p no:recording
```

36 tests covering Merkle trees, block mining, chain validation, fork resolution, VM execution, assembler, and P2P networking.
