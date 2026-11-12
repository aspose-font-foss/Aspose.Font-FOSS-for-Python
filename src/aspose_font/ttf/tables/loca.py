"""TTF loca table parser."""

from __future__ import annotations

from dataclasses import dataclass

from aspose_font._io import BinaryReader, BinaryWriter


@dataclass
class LocaTable:
    offsets: list[int]

    @classmethod
    def from_reader(
        cls,
        r: BinaryReader,
        num_glyphs: int,
        index_to_loc_format: int,
        table_length: int,
    ) -> "LocaTable":
        rr = BinaryReader(r.read_bytes(table_length))
        count = num_glyphs + 1
        offsets: list[int] = []
        if index_to_loc_format == 0:
            for _ in range(count):
                offsets.append(rr.read_u16() * 2)
        else:
            for _ in range(count):
                offsets.append(rr.read_u32())
        return cls(offsets=offsets)

    def to_bytes(self, index_to_loc_format: int) -> bytes:
        w = BinaryWriter()
        if index_to_loc_format == 0:
            for offset in self.offsets:
                w.write_u16(offset // 2)
        else:
            for offset in self.offsets:
                w.write_u32(offset)
        return w.to_bytes()

    def glyph_offset(self, gid: int) -> int:
        return self.offsets[gid]

    def glyph_length(self, gid: int) -> int:
        return self.offsets[gid + 1] - self.offsets[gid]
