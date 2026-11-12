"""OpenType LTSH (Linear Threshold) table parser."""
from __future__ import annotations

from dataclasses import dataclass

from aspose_font._exceptions import FontParseException
from aspose_font._io import BinaryReader, BinaryWriter


@dataclass(slots=True)
class LtshTable:
    """OpenType LTSH (Linear Threshold) table parser."""
    version: int
    values: list[int]

    @classmethod
    def from_reader(cls, r: BinaryReader, length: int) -> "LtshTable":
        """Parse LTSH table from binary reader."""
        rr = BinaryReader(r.read_bytes(length))

        version = rr.read_u16()
        num_glyphs = rr.read_u16()

        if version != 0:
            raise FontParseException(
                f"Unsupported LTSH table version: {version}",
                format_name="TTF"
            )

        values: list[int] = []
        for _ in range(num_glyphs):
            y_pixels = rr.read_u8()
            values.append(y_pixels)

        return cls(version=version, values=values)

    def to_bytes(self) -> bytes:
        """Serialize LTSH table to binary data."""
        bw = BinaryWriter()
        bw.write_u16(self.version)
        bw.write_u16(len(self.values))
        for value in self.values:
            bw.write_u8(value)
        return bw.to_bytes()
