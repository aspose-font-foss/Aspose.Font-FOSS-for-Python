"""OpenType VORG (Vertical Origin) table parser."""
from __future__ import annotations

from dataclasses import dataclass

from aspose_font._exceptions import FontParseException
from aspose_font._io import BinaryReader, BinaryWriter


@dataclass(slots=True, frozen=True)
class VertOriginYMetric:
    """Per-glyph vertical origin Y offset."""
    glyph_id: int
    vert_origin_y: int


@dataclass(slots=True)
class VorgTable:
    """OpenType VORG (Vertical Origin) table parser."""
    major_version: int
    minor_version: int
    default_vert_origin_y: int
    vert_origin_y_metrics: list[VertOriginYMetric]

    @classmethod
    def from_reader(cls, r: BinaryReader, length: int) -> "VorgTable":
        """Parse VORG table from binary reader."""
        rr = BinaryReader(r.read_bytes(length))

        major_version = rr.read_u16()
        minor_version = rr.read_u16()

        if (major_version, minor_version) != (1, 0):
            raise FontParseException(
                f"Unsupported VORG table version: {major_version}.{minor_version}",
                format_name="TTF"
            )

        default_vert_origin_y = rr.read_i16()
        num_records = rr.read_u16()

        vert_origin_y_metrics: list[VertOriginYMetric] = []
        for _ in range(num_records):
            glyph_id = rr.read_u16()
            vert_origin_y = rr.read_i16()
            vert_origin_y_metrics.append(VertOriginYMetric(
                glyph_id=glyph_id,
                vert_origin_y=vert_origin_y
            ))

        return cls(
            major_version=major_version,
            minor_version=minor_version,
            default_vert_origin_y=default_vert_origin_y,
            vert_origin_y_metrics=vert_origin_y_metrics
        )

    def to_bytes(self) -> bytes:
        """Serialize VORG table to binary data."""
        bw = BinaryWriter()
        bw.write_u16(self.major_version)
        bw.write_u16(self.minor_version)
        bw.write_i16(self.default_vert_origin_y)
        bw.write_u16(len(self.vert_origin_y_metrics))
        for metric in self.vert_origin_y_metrics:
            bw.write_u16(metric.glyph_id)
            bw.write_i16(metric.vert_origin_y)
        return bw.to_bytes()

    def get_vert_origin_y(self, glyph_id: int) -> int:
        """Return glyph-specific vertOriginY or the default value."""
        for metric in self.vert_origin_y_metrics:
            if metric.glyph_id == glyph_id:
                return metric.vert_origin_y
        return self.default_vert_origin_y
