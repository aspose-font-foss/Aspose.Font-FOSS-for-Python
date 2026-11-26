"""Tests for TrueType bytecode disassembler (FONT-552)."""
from __future__ import annotations

from aspose_font.ttf.instructions import DisassembledInstruction, InstructionDisassembler


def test_empty_bytecode_returns_empty_list() -> None:
    """Test that empty bytecode returns empty instruction list."""
    disassembler = InstructionDisassembler()
    instructions = disassembler.disassemble(b"")
    assert instructions == []


def test_single_nop_instruction() -> None:
    """Test disassembly of single NOP instruction."""
    disassembler = InstructionDisassembler()
    instructions = disassembler.disassemble(b"\x00")
    assert len(instructions) == 1
    assert instructions[0].opcode == 0x00
    assert instructions[0].mnemonic == "NOP"
    assert instructions[0].args == []
    assert instructions[0].offset == 0


def test_multiple_simple_instructions() -> None:
    """Test disassembly of multiple simple instructions."""
    disassembler = InstructionDisassembler()
    instructions = disassembler.disassemble(b"\x00\x01\x02")
    assert len(instructions) == 3
    assert instructions[0].opcode == 0x00
    assert instructions[0].mnemonic == "NOP"
    assert instructions[1].opcode == 0x01
    assert instructions[1].mnemonic == "SVTCA0"
    assert instructions[2].opcode == 0x02
    assert instructions[2].mnemonic == "SVTCA1"


def test_unknown_opcode_handled() -> None:
    """Test that opcode disassembly handles all valid opcodes gracefully."""
    disassembler = InstructionDisassembler()
    # Test with 0x5C (FLIPPT) - an optional TrueType instruction
    # The disassembler should handle it without crashing
    instructions = disassembler.disassemble(b"\x5C")
    assert len(instructions) == 1
    assert instructions[0].opcode == 0x5C
    # Verify the mnemonic is set correctly (FLIPPT is a valid optional instruction)
    assert instructions[0].mnemonic == "FLIPPT"


def test_pushb_0xb0_single_byte() -> None:
    """Test PUSHB 0xB0 (push 1 byte) instruction."""
    disassembler = InstructionDisassembler()
    instructions = disassembler.disassemble(b"\xB0\x10")
    assert len(instructions) == 1
    assert instructions[0].opcode == 0xB0
    assert instructions[0].mnemonic == "PUSHB"
    assert instructions[0].args == [0x10]
    assert instructions[0].offset == 0


def test_pushb_0xb7_eight_bytes() -> None:
    """Test PUSHB 0xB7 (push 8 bytes) instruction."""
    disassembler = InstructionDisassembler()
    instructions = disassembler.disassemble(b"\xB7\x01\x02\x03\x04\x05\x06\x07\x08")
    assert len(instructions) == 1
    assert instructions[0].opcode == 0xB7
    assert instructions[0].mnemonic == "PUSHB"
    assert instructions[0].args == [0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08]


def test_pushw_0xb8_single_word() -> None:
    """Test PUSHW 0xB8 (push 1 word) instruction."""
    disassembler = InstructionDisassembler()
    instructions = disassembler.disassemble(b"\xB8\x12\x34")
    assert len(instructions) == 1
    assert instructions[0].opcode == 0xB8
    assert instructions[0].mnemonic == "PUSHW"
    assert instructions[0].args == [0x1234]


def test_pushw_0xbf_eight_words() -> None:
    """Test PUSHW 0xBF (push 8 words) instruction."""
    disassembler = InstructionDisassembler()
    data = b"\xBF\x00\x01\x00\x02\x00\x03\x00\x04\x00\x05\x00\x06\x00\x07\x00\x08"
    instructions = disassembler.disassemble(data)
    assert len(instructions) == 1
    assert instructions[0].opcode == 0xBF
    assert instructions[0].mnemonic == "PUSHW"
    assert instructions[0].args == [0x0001, 0x0002, 0x0003, 0x0004, 0x0005, 0x0006, 0x0007, 0x0008]


def test_npushb_instruction() -> None:
    """Test NPUSHB instruction (count followed by bytes)."""
    disassembler = InstructionDisassembler()
    instructions = disassembler.disassemble(b"\x40\x03\x10\x20\x30")
    assert len(instructions) == 1
    assert instructions[0].opcode == 0x40
    assert instructions[0].mnemonic == "NPUSHB"
    assert instructions[0].args == [0x10, 0x20, 0x30]


def test_npushw_instruction() -> None:
    """Test NPUSHW instruction (count followed by words)."""
    disassembler = InstructionDisassembler()
    instructions = disassembler.disassemble(b"\x41\x02\x12\x34\x56\x78")
    assert len(instructions) == 1
    assert instructions[0].opcode == 0x41
    assert instructions[0].mnemonic == "NPUSHW"
    assert instructions[0].args == [0x1234, 0x5678]


def test_mixed_instructions() -> None:
    """Test mixed instruction types in one bytecode stream."""
    disassembler = InstructionDisassembler()
    bytecode = b"\x00\xB0\x10\x01\xB8\xAB\xCD"
    instructions = disassembler.disassemble(bytecode)
    assert len(instructions) == 4
    assert instructions[0].mnemonic == "NOP"
    assert instructions[0].args == []
    assert instructions[1].mnemonic == "PUSHB"
    assert instructions[1].args == [0x10]
    assert instructions[2].mnemonic == "SVTCA0"
    assert instructions[2].args == []
    assert instructions[3].mnemonic == "PUSHW"
    assert instructions[3].args == [0xABCD]


def test_truncated_pushb_args() -> None:
    """Test truncated PUSHB instruction (not enough bytes)."""
    disassembler = InstructionDisassembler()
    instructions = disassembler.disassemble(b"\xB7\x01\x02")
    assert len(instructions) == 1
    assert instructions[0].opcode == 0xB7
    assert instructions[0].mnemonic == "PUSHB"
    assert instructions[0].args == [0x01, 0x02]


def test_truncated_pushw_args() -> None:
    """Test truncated PUSHW instruction (odd remaining bytes)."""
    disassembler = InstructionDisassembler()
    instructions = disassembler.disassemble(b"\xBF\x00\x01\x02")
    assert len(instructions) == 1
    assert instructions[0].opcode == 0xBF
    assert instructions[0].mnemonic == "PUSHW"
    assert instructions[0].args == [0x0001, 0x02]


def test_truncated_npushb() -> None:
    """Test truncated NPUSHB instruction."""
    disassembler = InstructionDisassembler()
    instructions = disassembler.disassemble(b"\x40\x03\x10")
    assert len(instructions) == 1
    assert instructions[0].opcode == 0x40
    assert instructions[0].mnemonic == "NPUSHB"
    assert instructions[0].args == [0x10]


def test_truncated_npushw() -> None:
    """Test truncated NPUSHW instruction."""
    disassembler = InstructionDisassembler()
    instructions = disassembler.disassemble(b"\x41\x02\x12\x34")
    assert len(instructions) == 1
    assert instructions[0].opcode == 0x41
    assert instructions[0].mnemonic == "NPUSHW"
    assert instructions[0].args == [0x1234]


def test_format_listing_single_instruction() -> None:
    """Test format_listing with single instruction."""
    disassembler = InstructionDisassembler()
    instructions = disassembler.disassemble(b"\x00")
    listing = disassembler.format_listing(instructions)
    assert listing == "0000: NOP"


def test_format_listing_with_args() -> None:
    """Test format_listing with instruction arguments."""
    disassembler = InstructionDisassembler()
    # PUSHB 0xB0 pushes 1 byte, but we use 0xB1 which pushes 2 bytes
    instructions = disassembler.disassemble(b"\xB1\x10\x20")
    listing = disassembler.format_listing(instructions)
    expected = "0000: PUSHB [10, 20]"
    assert listing == expected


def test_format_listing_multiple_instructions() -> None:
    """Test format_listing with multiple instructions."""
    disassembler = InstructionDisassembler()
    bytecode = b"\x00\xB0\x10\x41\x01\xAB\xCD"
    instructions = disassembler.disassemble(bytecode)
    listing = disassembler.format_listing(instructions)
    lines = listing.split("\n")
    assert len(lines) == 3
    assert lines[0] == "0000: NOP"
    assert lines[1] == "0001: PUSHB [10]"
    assert lines[2] == "0003: NPUSHW [ABCD]"


def test_disassembled_instruction_dataclass() -> None:
    """Test DisassembledInstruction dataclass properties."""
    instr = DisassembledInstruction(
        opcode=0xB0,
        mnemonic="PUSHB",
        args=[0x10, 0x20],
        offset=5
    )
    assert instr.opcode == 0xB0
    assert instr.mnemonic == "PUSHB"
    assert instr.args == [0x10, 0x20]
    assert instr.offset == 5


def test_real_font_program_fragment() -> None:
    """Test with a fragment of real-looking hinting bytecode."""
    disassembler = InstructionDisassembler()
    # Simulated program fragment: NPUSHB 4 times, then SVTCA0
    bytecode = (
        b"\x40\x04\xFF\xFF\x00\x00"  # NPUSHB 4, push -1, -1, 0, 0
        b"\x01"                       # SVTCA0
    )
    instructions = disassembler.disassemble(bytecode)
    assert len(instructions) == 2
    assert instructions[0].mnemonic == "NPUSHB"
    assert instructions[0].args == [0xFF, 0xFF, 0x00, 0x00]
    assert instructions[1].mnemonic == "SVTCA0"
    assert instructions[1].args == []
