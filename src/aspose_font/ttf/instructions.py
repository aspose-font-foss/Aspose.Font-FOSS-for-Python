"""TrueType bytecode disassembler."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class DisassembledInstruction:
    """Disassembled TrueType bytecode instruction."""

    opcode: int
    mnemonic: str
    args: list[int]
    offset: int


class InstructionDisassembler:
    """Disassembles TrueType bytecode into human-readable assembly."""

    PUSHB_FIRST = 0xB0
    PUSHB_LAST = 0xB7
    PUSHW_FIRST = 0xB8
    PUSHW_LAST = 0xBF
    NPUSHB = 0x40
    NPUSHW = 0x41

    OPCODE_NAMES: dict[int, str] = {
        0x00: "NOP",
        0x01: "SVTCA0",
        0x02: "SVTCA1",
        0x03: "SPVTCA0",
        0x04: "SPVTCA1",
        0x05: "SFVTCA0",
        0x06: "SFVTCA1",
        0x07: "SPVTL0",
        0x08: "SPVTL1",
        0x09: "SFVTL0",
        0x0A: "SFVTL1",
        0x0B: "SPVFS",
        0x0C: "SFVFS",
        0x0D: "GPV",
        0x0E: "GFV",
        0x0F: "SFVTPV",
        0x10: "ISECT",
        0x11: "SRP0",
        0x12: "SRP1",
        0x13: "SRP2",
        0x14: "SZP0",
        0x15: "SZP1",
        0x16: "SZP2",
        0x17: "SZPS",
        0x18: "SLOOP",
        0x19: "RTG",
        0x1A: "RTHG",
        0x1B: "SMD",
        0x1C: "SCVTCI",
        0x1D: "SSWCI",
        0x1E: "SSW",
        0x1F: "DUP",
        0x20: "POP",
        0x21: "CLEAR",
        0x22: "SWAP",
        0x23: "DEPTH",
        0x24: "CINDEX",
        0x25: "MINDEX",
        0x26: "ABS",
        0x27: "ADD",
        0x28: "SUB",
        0x29: "DIV",
        0x2A: "MUL",
        0x2B: "NEG",
        0x2C: "FLOOR",
        0x2D: "CEILING",
        0x2E: "ROUND0",
        0x2F: "ROUND1",
        0x30: "ROUND2",
        0x31: "ROUND3",
        0x32: "NROUND0",
        0x33: "NROUND1",
        0x34: "NROUND2",
        0x35: "NROUND3",
        0x36: "WCVTF",
        0x37: "MDAP0",
        0x38: "MDAP1",
        0x39: "IUP0",
        0x3A: "IUP1",
        0x3B: "SHP0",
        0x3C: "SHP1",
        0x3D: "SHC0",
        0x3E: "SHC1",
        0x3F: "SHZ0",
        0x40: "NPUSHB",
        0x41: "NPUSHW",
        0x42: "WS",
        0x43: "RS",
        0x44: "WCVTP",
        0x45: "RCVT",
        0x46: "GC0",
        0x47: "GC1",
        0x48: "SCFS",
        0x49: "MD0",
        0x4A: "MD1",
        0x4B: "MPPEM",
        0x4C: "MPS",
        0x4D: "FLIPOPN",
        0x4E: "SHP0",
        0x4F: "SHP1",
        0x50: "SHC0",
        0x51: "SHC1",
        0x52: "SHZ0",
        0x53: "SHZ1",
        0x54: "MDAP",
        0x55: "IUP",
        0x56: "SLOOP",
        0x57: "RTG",
        0x58: "RTHG",
        0x59: "SMD",
        0x5A: "SANGW",
        0x5B: "AA",
        0x5C: "FLIPPT",
        0x5D: "FLIPRGON",
        0x5E: "FLIPRGOFF",
        0x5F: "SCANCTRL",
        0x60: "SDPVTL0",
        0x61: "SDPVTL1",
        0x62: "GETINFO",
        0x63: "IDEF",
        0x64: "ROLL",
        0x65: "MAX",
        0x66: "MIN",
        0x67: "SCANTYPE",
        0x68: "INSTCTRL",
        0x69: "SLOOP",
        0x6A: "RTG",
        0x6B: "RTHG",
        0x6C: "SMD",
        0x6D: "SANGW",
        0x6E: "AA",
        0x6F: "FLIPPT",
        0x70: "FLIPRGON",
        0x71: "FLIPRGOFF",
        0x72: "SCANCTRL",
        0x73: "SDPVTL0",
        0x74: "SDPVTL1",
        0x75: "GETINFO",
        0x76: "IDEF",
        0x77: "ROLL",
        0x78: "MAX",
        0x79: "MIN",
        0x7A: "SCANTYPE",
        0x7B: "INSTCTRL",
        0x7C: "SLOOP",
        0x7D: "RTG",
        0x7E: "RTHG",
        0x7F: "SMD",
        0x80: "SANGW",
        0x81: "AA",
        0x82: "FLIPPT",
        0x83: "FLIPRGON",
        0x84: "FLIPRGOFF",
        0x85: "SCANCTRL",
        0x86: "SDPVTL0",
        0x87: "SDPVTL1",
        0x88: "GETINFO",
        0x89: "IDEF",
        0x8A: "ROLL",
        0x8B: "MAX",
        0x8C: "MIN",
        0x8D: "SCANTYPE",
        0x8E: "INSTCTRL",
        0x8F: "SLOOP",
        0x90: "RTG",
        0x91: "RTHG",
        0x92: "SMD",
        0x93: "SANGW",
        0x94: "AA",
        0x95: "FLIPPT",
        0x96: "FLIPRGON",
        0x97: "FLIPRGOFF",
        0x98: "SCANCTRL",
        0x99: "SDPVTL0",
        0x9A: "SDPVTL1",
        0x9B: "GETINFO",
        0x9C: "IDEF",
        0x9D: "ROLL",
        0x9E: "MAX",
        0x9F: "MIN",
        0xA0: "SCANTYPE",
        0xA1: "INSTCTRL",
        0xA2: "SLOOP",
        0xA3: "RTG",
        0xA4: "RTHG",
        0xA5: "SMD",
        0xA6: "SANGW",
        0xA7: "AA",
        0xA8: "FLIPPT",
        0xA9: "FLIPRGON",
        0xAA: "FLIPRGOFF",
        0xAB: "SCANCTRL",
        0xAC: "SDPVTL0",
        0xAD: "SDPVTL1",
        0xAE: "GETINFO",
        0xAF: "IDEF",
        0xB0: "PUSHB",
        0xB1: "PUSHB",
        0xB2: "PUSHB",
        0xB3: "PUSHB",
        0xB4: "PUSHB",
        0xB5: "PUSHB",
        0xB6: "PUSHB",
        0xB7: "PUSHB",
        0xB8: "PUSHW",
        0xB9: "PUSHW",
        0xBA: "PUSHW",
        0xBB: "PUSHW",
        0xBC: "PUSHW",
        0xBD: "PUSHW",
        0xBE: "PUSHW",
        0xBF: "PUSHW",
        0xC0: "MIRP",
        0xC1: "MIRP",
        0xC2: "MIRP",
        0xC3: "MIRP",
        0xC4: "MIRP",
        0xC5: "MIRP",
        0xC6: "MIRP",
        0xC7: "MIRP",
        0xC8: "MIRP",
        0xC9: "MIRP",
        0xCA: "MIRP",
        0xCB: "MIRP",
        0xCC: "MIRP",
        0xCD: "MIRP",
        0xCE: "MIRP",
        0xCF: "MIRP",
        0xD0: "MIRP",
        0xD1: "MIRP",
        0xD2: "MIRP",
        0xD3: "MIRP",
        0xD4: "MIRP",
        0xD5: "MIRP",
        0xD6: "MIRP",
        0xD7: "MIRP",
        0xD8: "MIRP",
        0xD9: "MIRP",
        0xDA: "MIRP",
        0xDB: "MIRP",
        0xDC: "MIRP",
        0xDD: "MIRP",
        0xDE: "MIRP",
        0xDF: "MIRP",
        0xE0: "MIRP",
        0xE1: "MIRP",
        0xE2: "MIRP",
        0xE3: "MIRP",
        0xE4: "MIRP",
        0xE5: "MIRP",
        0xE6: "MIRP",
        0xE7: "MIRP",
        0xE8: "MIRP",
        0xE9: "MIRP",
        0xEA: "MIRP",
        0xEB: "MIRP",
        0xEC: "MIRP",
        0xED: "MIRP",
        0xEE: "MIRP",
        0xEF: "MIRP",
        0xF0: "MIRP",
        0xF1: "MIRP",
        0xF2: "MIRP",
        0xF3: "MIRP",
        0xF4: "MIRP",
        0xF5: "MIRP",
        0xF6: "MIRP",
        0xF7: "MIRP",
        0xF8: "MIRP",
        0xF9: "MIRP",
        0xFA: "MIRP",
        0xFB: "MIRP",
        0xFC: "MIRP",
        0xFD: "MIRP",
        0xFE: "MIRP",
        0xFF: "MIRP",
    }

    def disassemble(self, bytecode: bytes) -> list[DisassembledInstruction]:
        """Disassemble TrueType bytecode into a list of instructions.

        Args:
            bytecode: Raw bytecode bytes to disassemble

        Returns:
            List of DisassembledInstruction objects
        """
        instructions: list[DisassembledInstruction] = []
        offset = 0
        bytecode_len = len(bytecode)

        while offset < bytecode_len:
            opcode = bytecode[offset]
            instr_offset = offset
            offset += 1

            mnemonic = self.OPCODE_NAMES.get(opcode, f"UNKNOWN_{opcode:02X}")

            if opcode == self.NPUSHB:
                if offset >= bytecode_len:
                    instructions.append(DisassembledInstruction(
                        opcode=opcode,
                        mnemonic=mnemonic,
                        args=[],
                        offset=instr_offset
                    ))
                    break
                count = bytecode[offset]
                offset += 1
                args: list[int] = []
                for _ in range(count):
                    if offset >= bytecode_len:
                        break
                    args.append(bytecode[offset])
                    offset += 1
                instructions.append(DisassembledInstruction(
                    opcode=opcode,
                    mnemonic="NPUSHB",
                    args=args,
                    offset=instr_offset
                ))
                continue

            if opcode == self.NPUSHW:
                if offset >= bytecode_len:
                    instructions.append(DisassembledInstruction(
                        opcode=opcode,
                        mnemonic=mnemonic,
                        args=[],
                        offset=instr_offset
                    ))
                    break
                count = bytecode[offset]
                offset += 1
                args = []
                for _ in range(count):
                    if offset + 1 >= bytecode_len:
                        if offset < bytecode_len:
                            args.append(bytecode[offset])
                            offset += 1
                        break
                    word = (bytecode[offset] << 8) | bytecode[offset + 1]
                    offset += 2
                    args.append(word)
                instructions.append(DisassembledInstruction(
                    opcode=opcode,
                    mnemonic="NPUSHW",
                    args=args,
                    offset=instr_offset
                ))
                continue

            if self.PUSHB_FIRST <= opcode <= self.PUSHB_LAST:
                count = opcode - self.PUSHB_FIRST + 1
                args = []
                for _ in range(count):
                    if offset >= bytecode_len:
                        break
                    args.append(bytecode[offset])
                    offset += 1
                instructions.append(DisassembledInstruction(
                    opcode=opcode,
                    mnemonic="PUSHB",
                    args=args,
                    offset=instr_offset
                ))
                continue

            if self.PUSHW_FIRST <= opcode <= self.PUSHW_LAST:
                count = opcode - self.PUSHW_FIRST + 1
                args = []
                for _ in range(count):
                    if offset + 1 >= bytecode_len:
                        if offset < bytecode_len:
                            args.append(bytecode[offset])
                            offset += 1
                        break
                    word = (bytecode[offset] << 8) | bytecode[offset + 1]
                    offset += 2
                    args.append(word)
                instructions.append(DisassembledInstruction(
                    opcode=opcode,
                    mnemonic="PUSHW",
                    args=args,
                    offset=instr_offset
                ))
                continue

            instructions.append(DisassembledInstruction(
                opcode=opcode,
                mnemonic=mnemonic,
                args=[],
                offset=instr_offset
            ))

        return instructions

    def format_listing(self, instructions: list[DisassembledInstruction]) -> str:
        """Format disassembled instructions as assembly listing.

        Args:
            instructions: List of DisassembledInstruction objects

        Returns:
            Formatted assembly output with one line per instruction
        """
        lines: list[str] = []
        for instr in instructions:
            if instr.args:
                args_str = ", ".join(f"{arg:02X}" for arg in instr.args)
                line = f"{instr.offset:04X}: {instr.mnemonic} [{args_str}]"
            else:
                line = f"{instr.offset:04X}: {instr.mnemonic}"
            lines.append(line)
        return "\n".join(lines)
