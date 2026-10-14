"""TTF maxp table parser."""

from __future__ import annotations

from dataclasses import dataclass

from aspose_font._io import BinaryReader, BinaryWriter


@dataclass
class MaxpTable:
    version: int
    num_glyphs: int
    extras: tuple[int, ...] = ()

    @classmethod
    def from_reader(cls, r: BinaryReader, table_length: int) -> "MaxpTable":
        version = r.read_u32()
        num_glyphs = r.read_u16()
        extras: list[int] = []
        remaining_words = max((table_length - 6) // 2, 0)
        for _ in range(remaining_words):
            extras.append(r.read_u16())
        return cls(version=version, num_glyphs=num_glyphs, extras=tuple(extras))

    def to_bytes(self) -> bytes:
        w = BinaryWriter()
        w.write_u32(self.version)
        w.write_u16(self.num_glyphs)
        for value in self.extras:
            w.write_u16(value)
        return w.to_bytes()
