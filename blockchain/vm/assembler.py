"""Simple assembler: converts human-readable mnemonics to bytecode."""

from __future__ import annotations

import struct

from .opcodes import OpCode


def assemble(source: str) -> bytes:
    """Assemble a program from text mnemonics.

    Example source:
        PUSH 10
        PUSH 20
        ADD
        LOG
        HALT
    """
    bytecode = bytearray()
    lines = source.strip().split("\n")

    for line_num, raw_line in enumerate(lines, 1):
        line = raw_line.strip()
        if not line or line.startswith("#") or line.startswith(";"):
            continue

        parts = line.split(None, 1)
        mnemonic = parts[0].upper()

        try:
            op = OpCode[mnemonic]
        except KeyError:
            raise ValueError(f"Line {line_num}: unknown instruction '{mnemonic}'")

        bytecode.append(op.value)

        if op == OpCode.PUSH:
            if len(parts) < 2:
                raise ValueError(f"Line {line_num}: PUSH requires an operand")
            try:
                value = int(parts[1], 0)  # supports hex (0x...) and decimal
            except ValueError:
                raise ValueError(f"Line {line_num}: invalid integer '{parts[1]}'")
            bytecode.extend(struct.pack(">i", value))

    return bytes(bytecode)


def disassemble(bytecode: bytes) -> str:
    """Disassemble bytecode back to human-readable mnemonics."""
    lines: list[str] = []
    pc = 0

    while pc < len(bytecode):
        addr = pc
        raw_op = bytecode[pc]
        pc += 1

        try:
            op = OpCode(raw_op)
        except ValueError:
            lines.append(f"{addr:04x}: ??? 0x{raw_op:02x}")
            continue

        if op == OpCode.PUSH:
            if pc + 4 > len(bytecode):
                lines.append(f"{addr:04x}: PUSH <truncated>")
                break
            value = struct.unpack(">i", bytecode[pc : pc + 4])[0]
            lines.append(f"{addr:04x}: PUSH {value}")
            pc += 4
        else:
            lines.append(f"{addr:04x}: {op.name}")

    return "\n".join(lines)
