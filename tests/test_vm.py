"""Tests for the stack-based VM and assembler."""

import unittest

from blockchain.vm.assembler import assemble, disassemble
from blockchain.vm.opcodes import OpCode
from blockchain.vm.vm import VM, VMError


class TestVM(unittest.TestCase):
    def test_push_and_add(self):
        code = assemble("PUSH 10\nPUSH 20\nADD\nHALT")
        vm = VM()
        result = vm.execute(code)
        self.assertEqual(result, [30])

    def test_arithmetic(self):
        code = assemble("PUSH 100\nPUSH 7\nMOD\nHALT")
        vm = VM()
        result = vm.execute(code)
        self.assertEqual(result, [2])

    def test_comparison(self):
        code = assemble("PUSH 5\nPUSH 10\nLT\nHALT")
        vm = VM()
        result = vm.execute(code)
        self.assertEqual(result, [1])

    def test_storage(self):
        code = assemble("PUSH 42\nPUSH 99\nSSTORE\nPUSH 42\nSLOAD\nHALT")
        vm = VM()
        result = vm.execute(code)
        self.assertEqual(result, [99])
        self.assertEqual(vm.storage["42"], 99)

    def test_conditional_jump(self):
        # JUMPI pops: condition, then address
        # PUSH 999 is at bytecode offset 17 (0x11)
        source = """
            PUSH 17
            PUSH 1
            JUMPI
            PUSH 111
            HALT
            PUSH 999
            LOG
            HALT
        """
        code = assemble(source)
        vm = VM()
        vm.execute(code)
        # If jump worked, 999 should be in logs, not 111
        self.assertIn(999, vm.logs)
        self.assertNotIn(111, [v for v in vm.logs])

    def test_stack_overflow(self):
        # Push 1025 items (limit is 1024)
        lines = ["PUSH 1\n" for _ in range(1025)]
        code = assemble("".join(lines) + "HALT")
        vm = VM()
        with self.assertRaises(VMError):
            vm.execute(code)

    def test_division_by_zero(self):
        code = assemble("PUSH 10\nPUSH 0\nDIV\nHALT")
        vm = VM()
        with self.assertRaises(VMError):
            vm.execute(code)

    def test_dup_and_swap(self):
        code = assemble("PUSH 1\nPUSH 2\nSWAP\nHALT")
        vm = VM()
        result = vm.execute(code)
        self.assertEqual(result, [2, 1])

    def test_log(self):
        code = assemble("PUSH 42\nLOG\nHALT")
        vm = VM()
        vm.execute(code)
        self.assertEqual(vm.logs, [42])

    def test_not(self):
        code = assemble("PUSH 0\nNOT\nHALT")
        vm = VM()
        result = vm.execute(code)
        self.assertEqual(result, [1])

    def test_bitwise(self):
        code = assemble("PUSH 0xFF\nPUSH 0x0F\nAND\nHALT")
        vm = VM()
        result = vm.execute(code)
        self.assertEqual(result, [0x0F])


class TestAssembler(unittest.TestCase):
    def test_roundtrip(self):
        source = "PUSH 42\nADD\nHALT"
        bytecode = assemble(source)
        text = disassemble(bytecode)
        self.assertIn("PUSH 42", text)
        self.assertIn("ADD", text)
        self.assertIn("HALT", text)

    def test_comments_ignored(self):
        source = "# comment\nPUSH 1\n; another comment\nHALT"
        bytecode = assemble(source)
        vm = VM()
        result = vm.execute(bytecode)
        self.assertEqual(result, [1])

    def test_hex_values(self):
        source = "PUSH 0xFF\nHALT"
        bytecode = assemble(source)
        vm = VM()
        result = vm.execute(bytecode)
        self.assertEqual(result, [255])


if __name__ == "__main__":
    unittest.main()
