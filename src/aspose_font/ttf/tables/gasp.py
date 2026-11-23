"""OpenType gasp (Grid-fitting and Scan conversion) table parser."""
from __future__ import annotations

from dataclasses import dataclass

from aspose_font._exceptions import FontParseException
from aspose_font._io import BinaryReader


@dataclass(slots=True, frozen=True)
class GaspRange:
    """Grid-fitting behavior recommendation for a PPEM range."""
    range_max_ppem: int
    range_gasp_behavior: int


@dataclass(slots=True)
class GaspTable:
    """OpenType gasp table parser."""
    gasp_version: int
    ranges: list[GaspRange]

    @classmethod
    def from_reader(cls, r: BinaryReader, length: int) -> "GaspTable":
        """Parse gasp table from binary reader."""
        rr = BinaryReader(r.read_bytes(length))

        gasp_version = rr.read_u16()
        num_ranges = rr.read_u16()

        if gasp_version not in (0, 1):
            raise FontParseException(
                f"Unsupported gasp table version: {gasp_version}",
                format_name="TTF"
            )

        ranges: list[GaspRange] = []
        for _ in range(num_ranges):
            range_max_ppem = rr.read_u16()
            range_gasp_behavior = rr.read_u16()
            ranges.append(GaspRange(
                range_max_ppem=range_max_ppem,
                range_gasp_behavior=range_gasp_behavior
            ))

        return cls(gasp_version=gasp_version, ranges=ranges)

    def to_bytes(self) -> bytes:
        """Serialize gasp table to binary data."""
        from aspose_font._io import BinaryWriter
        bw = BinaryWriter()
        bw.write_u16(self.gasp_version)
        bw.write_u16(len(self.ranges))
        for range_record in self.ranges:
            bw.write_u16(range_record.range_max_ppem)
            bw.write_u16(range_record.range_gasp_behavior)
        return bw.to_bytes()
