"""TTF head table parser."""

from __future__ import annotations

from dataclasses import dataclass

from aspose_font._io import BinaryReader, BinaryWriter


@dataclass
class HeadTable:
    magic: int
    major_version: int
    minor_version: int
    font_revision: float
    checksum_adjustment: int
    flags: int
    units_per_em: int
    created: int
    modified: int
    x_min: int
    y_min: int
    x_max: int
    y_max: int
    mac_style: int
    lowest_rec_ppem: int
    font_direction_hint: int
    index_to_loc_format: int
    glyph_data_format: int

    @classmethod
    def from_reader(cls, r: BinaryReader) -> "HeadTable":
        major_version = r.read_u16()
        minor_version = r.read_u16()
        font_revision = r.read_fixed()
        checksum_adjustment = r.read_u32()
        magic = r.read_u32()
        flags = r.read_u16()
        units_per_em = r.read_u16()
        created = r.read_u64()
        modified = r.read_u64()
        x_min = r.read_i16()
        y_min = r.read_i16()
        x_max = r.read_i16()
        y_max = r.read_i16()
        mac_style = r.read_u16()
        lowest_rec_ppem = r.read_u16()
        font_direction_hint = r.read_i16()
        index_to_loc_format = r.read_i16()
        glyph_data_format = r.read_i16()
        return cls(
            magic=magic,
            major_version=major_version,
            minor_version=minor_version,
            font_revision=font_revision,
            checksum_adjustment=checksum_adjustment,
            flags=flags,
            units_per_em=units_per_em,
            created=created,
            modified=modified,
            x_min=x_min,
            y_min=y_min,
            x_max=x_max,
            y_max=y_max,
            mac_style=mac_style,
            lowest_rec_ppem=lowest_rec_ppem,
            font_direction_hint=font_direction_hint,
            index_to_loc_format=index_to_loc_format,
            glyph_data_format=glyph_data_format,
        )

    def to_bytes(self) -> bytes:
        w = BinaryWriter()
        w.write_u16(self.major_version)
        w.write_u16(self.minor_version)
        w.write_fixed(self.font_revision)
        w.write_u32(self.checksum_adjustment)
        w.write_u32(self.magic)
        w.write_u16(self.flags)
        w.write_u16(self.units_per_em)
        w.write_u64(self.created)
        w.write_u64(self.modified)
        w.write_i16(self.x_min)
        w.write_i16(self.y_min)
        w.write_i16(self.x_max)
        w.write_i16(self.y_max)
        w.write_u16(self.mac_style)
        w.write_u16(self.lowest_rec_ppem)
        w.write_i16(self.font_direction_hint)
        w.write_i16(self.index_to_loc_format)
        w.write_i16(self.glyph_data_format)
        return w.to_bytes()
