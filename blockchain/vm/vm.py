"""Stack-based virtual machine for executing smart contract bytecode."""

from __future__ import annotations

import logging
import struct
from dataclasses import dataclass, field

from .opcodes import IMMEDIATE_SIZE, OpCode

logger = logging.getLogger(__name__)

MAX_STACK_SIZE = 1024
MAX_STEPS = 10_000  # gas-like execution limit


class VMError(Exception):
    pass


@dataclass
class VM:
    storage: dict[str, int] = field(default_factory=dict)
    stack: list[int] = field(default_factory=list)
    logs: list[int] = field(default_factory=list)
    caller: int = 0
    callvalue: int = 0
    halted: bool = False

    def execute(self, bytecode: bytes) -> list[int]:
        pc = 0
        steps = 0
        self.halted = False

        while pc < len(bytecode) and not self.halted:
            steps += 1
            if steps > MAX_STEPS:
                raise VMError(f"Execution exceeded {MAX_STEPS} steps (out of gas)")

            raw_op = bytecode[pc]
            try:
                op = OpCode(raw_op)
            except ValueError:
                raise VMError(f"Unknown opcode 0x{raw_op:02x} at pc={pc}")

            pc += 1

            if op == OpCode.PUSH:
                if pc + 4 > len(bytecode):
                    raise VMError("PUSH: not enough data")
                value = struct.unpack(">i", bytecode[pc : pc + 4])[0]
                self._push(value)
                pc += 4

            elif op == OpCode.POP:
                self._pop()

            elif op == OpCode.DUP:
                val = self._peek()
                self._push(val)

            elif op == OpCode.SWAP:
                if len(self.stack) < 2:
                    raise VMError("SWAP: stack underflow")
                self.stack[-1], self.stack[-2] = self.stack[-2], self.stack[-1]

            elif op == OpCode.ADD:
                b, a = self._pop(), self._pop()
                self._push(a + b)

            elif op == OpCode.SUB:
                b, a = self._pop(), self._pop()
                self._push(a - b)

            elif op == OpCode.MUL:
                b, a = self._pop(), self._pop()
                self._push(a * b)

            elif op == OpCode.DIV:
                b, a = self._pop(), self._pop()
                if b == 0:
                    raise VMError("Division by zero")
                self._push(a // b)

            elif op == OpCode.MOD:
                b, a = self._pop(), self._pop()
                if b == 0:
                    raise VMError("Modulo by zero")
                self._push(a % b)

            elif op == OpCode.EQ:
                b, a = self._pop(), self._pop()
                self._push(1 if a == b else 0)

            elif op == OpCode.LT:
                b, a = self._pop(), self._pop()
                self._push(1 if a < b else 0)

            elif op == OpCode.GT:
                b, a = self._pop(), self._pop()
                self._push(1 if a > b else 0)

            elif op == OpCode.NOT:
                a = self._pop()
                self._push(1 if a == 0 else 0)

            elif op == OpCode.AND:
                b, a = self._pop(), self._pop()
                self._push(a & b)

            elif op == OpCode.OR:
                b, a = self._pop(), self._pop()
                self._push(a | b)

            elif op == OpCode.XOR:
                b, a = self._pop(), self._pop()
                self._push(a ^ b)

            elif op == OpCode.JUMP:
                addr = self._pop()
                if addr < 0 or addr >= len(bytecode):
                    raise VMError(f"JUMP to invalid address {addr}")
                pc = addr

            elif op == OpCode.JUMPI:
                cond = self._pop()
                addr = self._pop()
                if cond != 0:
                    if addr < 0 or addr >= len(bytecode):
                        raise VMError(f"JUMPI to invalid address {addr}")
                    pc = addr

            elif op == OpCode.HALT:
                self.halted = True

            elif op == OpCode.NOP:
                pass

            elif op == OpCode.SSTORE:
                value = self._pop()
                key = self._pop()
                self.storage[str(key)] = value
                logger.debug("SSTORE: storage[%s] = %d", key, value)

            elif op == OpCode.SLOAD:
                key = self._pop()
                value = self.storage.get(str(key), 0)
                self._push(value)
                logger.debug("SLOAD: storage[%s] -> %d", key, value)

            elif op == OpCode.CALLER:
                self._push(self.caller)

            elif op == OpCode.CALLVALUE:
                self._push(self.callvalue)

            elif op == OpCode.LOG:
                val = self._pop()
                self.logs.append(val)
                logger.debug("LOG: %d", val)

        return list(self.stack)

    def _push(self, value: int):
        if len(self.stack) >= MAX_STACK_SIZE:
            raise VMError("Stack overflow")
        self.stack.append(value)

    def _pop(self) -> int:
        if not self.stack:
            raise VMError("Stack underflow")
        return self.stack.pop()

    def _peek(self) -> int:
        if not self.stack:
            raise VMError("Stack underflow (peek)")
        return self.stack[-1]
