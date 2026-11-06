"""TTF post table parser."""

from __future__ import annotations

from dataclasses import dataclass

from aspose_font._io import BinaryReader

_STANDARD_NAMES = tuple(f"glyph{i}" for i in range(258))


@dataclass
class PostTable:
    version: int
    italic_angle: float
    underline_position: int
    underline_thickness: int
    is_fixed_pitch: int
    glyph_names: list[str] | None
    _raw: bytes

    @classmethod
    def from_reader(cls, r: BinaryReader, table_length: int) -> "PostTable":
        raw = r.read_bytes(table_length)
        rr = BinaryReader(raw)
        version = rr.read_u32()
        italic_angle = rr.read_fixed()
        underline_position = rr.read_i16()
        underline_thickness = rr.read_i16()
        is_fixed_pitch = rr.read_u32()
        rr.read_u32()
        rr.read_u32()
        rr.read_u32()
        rr.read_u32()

        glyph_names: list[str] | None = None
        if version == 0x00020000 and rr.remaining() >= 2:
            count = rr.read_u16()
            name_indexes = [rr.read_u16() for _ in range(count)]
            custom: list[str] = []
            while rr.remaining() > 0:
                length = rr.read_u8()
                custom.append(rr.read_bytes(length).decode("latin-1", errors="replace"))

            glyph_names = []
            for idx in name_indexes:
                if idx < len(_STANDARD_NAMES):
                    glyph_names.append(_STANDARD_NAMES[idx])
                else:
                    cidx = idx - 258
                    glyph_names.append(custom[cidx] if cidx < len(custom) else "")

        return cls(
            version=version,
            italic_angle=italic_angle,
            underline_position=underline_position,
            underline_thickness=underline_thickness,
            is_fixed_pitch=is_fixed_pitch,
            glyph_names=glyph_names,
            _raw=raw,
        )

    def to_bytes(self) -> bytes:
        return self._raw

    def glyph_name(self, gid: int) -> str | None:
        if self.glyph_names is None:
            return None
        if 0 <= gid < len(self.glyph_names):
            return self.glyph_names[gid]
        return None
