"""Bytecode opcodes for the stack-based virtual machine."""

from enum import IntEnum


class OpCode(IntEnum):
    # Stack operations
    PUSH = 0x01       # Push next byte(s) as value onto stack
    POP = 0x02        # Pop top of stack
    DUP = 0x03        # Duplicate top of stack
    SWAP = 0x04       # Swap top two stack items

    # Arithmetic
    ADD = 0x10        # a + b
    SUB = 0x11        # a - b
    MUL = 0x12        # a * b
    DIV = 0x13        # a / b (integer)
    MOD = 0x14        # a % b

    # Comparison
    EQ = 0x20         # a == b -> 1 or 0
    LT = 0x21         # a < b -> 1 or 0
    GT = 0x22         # a > b -> 1 or 0
    NOT = 0x23        # !a -> 1 or 0

    # Bitwise
    AND = 0x30        # a & b
    OR = 0x31         # a | b
    XOR = 0x32        # a ^ b

    # Control flow
    JUMP = 0x40       # Unconditional jump to address on stack
    JUMPI = 0x41      # Conditional jump: if top != 0, jump to address
    HALT = 0x42       # Stop execution
    NOP = 0x43        # No operation

    # Storage
    SSTORE = 0x50     # Store: key, value -> storage[key] = value
    SLOAD = 0x51      # Load: key -> push storage[key]

    # Environment
    CALLER = 0x60     # Push caller address (as int)
    CALLVALUE = 0x61  # Push transaction value

    # Logging / debug
    LOG = 0x70        # Pop and log top of stack


# How many extra bytes each opcode consumes as immediate data
IMMEDIATE_SIZE: dict[OpCode, int] = {
    OpCode.PUSH: 4,  # 4 bytes = 32-bit integer
}
