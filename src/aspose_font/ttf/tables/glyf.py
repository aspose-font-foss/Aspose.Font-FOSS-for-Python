"""TTF glyf table raw storage."""

from __future__ import annotations

from dataclasses import dataclass

from aspose_font._io import BinaryReader


@dataclass
class GlyfTable:
    _data: bytes

    @classmethod
    def from_reader(cls, r: BinaryReader, length: int) -> "GlyfTable":
        return cls(_data=r.read_bytes(length))

    def to_bytes(self) -> bytes:
        return self._data

    def get_glyph_bytes(self, offset: int, length: int) -> bytes:
        return self._data[offset : offset + length]
