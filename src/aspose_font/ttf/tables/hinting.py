"""TrueType hinting tables (cvt, fpgm, prep) parsers."""
from __future__ import annotations

from dataclasses import dataclass

from aspose_font._exceptions import FontParseException
from aspose_font._io import BinaryReader, BinaryWriter


@dataclass(slots=True)
class CvtTable:
    """Parsed CVT (Control Value Table) with signed 16-bit control values."""

    values: list[int]

    @classmethod
    def from_reader(cls, r: BinaryReader, length: int) -> "CvtTable":
        """Parse CVT table from binary data.

        Args:
            r: BinaryReader positioned at start of table data
            length: Total length of table data in bytes

        Returns:
            CvtTable with parsed values

        Raises:
            FontParseException: if length is odd or version is unsupported
        """
        data = r.read_bytes(length)
        rr = BinaryReader(data)

        version = rr.read_u16()
        if version != 0:
            raise FontParseException(
                f"Unsupported CVT table version: {version}",
                format_name="TTF"
            )

        if length % 2 != 0:
            raise FontParseException(
                f"CVT table length must be even, got {length}",
                format_name="TTF"
            )

        num_values = (length - 2) // 2
        values: list[int] = []
        for _ in range(num_values):
            values.append(rr.read_i16())

        if rr.remaining() != 0:
            raise FontParseException(
                f"CVT table length mismatch: expected {(num_values + 1) * 2} bytes, "
                f"read {length} bytes",
                format_name="TTF"
            )

        return cls(values=values)

    def to_bytes(self) -> bytes:
        """Serialize CVT table to binary data."""
        bw = BinaryWriter()
        bw.write_u16(0)
        for value in self.values:
            bw.write_i16(value)
        return bw.to_bytes()


@dataclass(slots=True)
class ProgramTable:
    """Parsed hinting program (fpgm or prep) bytecode."""

    code: bytes

    @classmethod
    def from_reader(cls, r: BinaryReader, length: int) -> "ProgramTable":
        """Parse hinting program from binary data.

        Args:
            r: BinaryReader positioned at start of program data
            length: Total length of program data in bytes

        Returns:
            ProgramTable with raw bytecode

        Raises:
            FontParseException: if length is negative or reader fails
        """
        if length < 0:
            raise FontParseException(
                f"Program table length cannot be negative: {length}",
                format_name="TTF"
            )

        code = r.read_bytes(length)
        return cls(code=code)

    def to_bytes(self) -> bytes:
        """Serialize program table to binary data."""
        return self.code
