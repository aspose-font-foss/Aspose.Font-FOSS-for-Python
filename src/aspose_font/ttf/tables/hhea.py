"""TTF hhea table parser."""

from __future__ import annotations

from dataclasses import dataclass

from aspose_font._io import BinaryReader, BinaryWriter


@dataclass
class HheaTable:
    major_version: int
    minor_version: int
    ascender: int
    descender: int
    line_gap: int
    advance_width_max: int
    min_lsb: int
    min_rsb: int
    x_max_extent: int
    caret_slope_rise: int
    caret_slope_run: int
    caret_offset: int
    metric_data_format: int
    number_of_hmetrics: int

    @classmethod
    def from_reader(cls, r: BinaryReader) -> "HheaTable":
        major_version = r.read_u16()
        minor_version = r.read_u16()
        ascender = r.read_i16()
        descender = r.read_i16()
        line_gap = r.read_i16()
        advance_width_max = r.read_u16()
        min_lsb = r.read_i16()
        min_rsb = r.read_i16()
        x_max_extent = r.read_i16()
        caret_slope_rise = r.read_i16()
        caret_slope_run = r.read_i16()
        caret_offset = r.read_i16()
        r.read_i16()
        r.read_i16()
        r.read_i16()
        r.read_i16()
        metric_data_format = r.read_i16()
        number_of_hmetrics = r.read_u16()
        return cls(
            major_version=major_version,
            minor_version=minor_version,
            ascender=ascender,
            descender=descender,
            line_gap=line_gap,
            advance_width_max=advance_width_max,
            min_lsb=min_lsb,
            min_rsb=min_rsb,
            x_max_extent=x_max_extent,
            caret_slope_rise=caret_slope_rise,
            caret_slope_run=caret_slope_run,
            caret_offset=caret_offset,
            metric_data_format=metric_data_format,
            number_of_hmetrics=number_of_hmetrics,
        )

    def to_bytes(self) -> bytes:
        w = BinaryWriter()
        w.write_u16(self.major_version)
        w.write_u16(self.minor_version)
        w.write_i16(self.ascender)
        w.write_i16(self.descender)
        w.write_i16(self.line_gap)
        w.write_u16(self.advance_width_max)
        w.write_i16(self.min_lsb)
        w.write_i16(self.min_rsb)
        w.write_i16(self.x_max_extent)
        w.write_i16(self.caret_slope_rise)
        w.write_i16(self.caret_slope_run)
        w.write_i16(self.caret_offset)
        w.write_i16(0)
        w.write_i16(0)
        w.write_i16(0)
        w.write_i16(0)
        w.write_i16(self.metric_data_format)
        w.write_u16(self.number_of_hmetrics)
        return w.to_bytes()
