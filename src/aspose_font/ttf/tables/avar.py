"""Minimal avar table parser for variable-font instancing."""

from __future__ import annotations

from dataclasses import dataclass

from aspose_font._exceptions import FontParseException
from aspose_font._io import BinaryReader


@dataclass(slots=True)
class AvarAxisMap:
    mapping: list[tuple[float, float]]


@dataclass
class AvarTable:
    axis_maps: list[AvarAxisMap]

    @classmethod
    def from_reader(cls, r: BinaryReader, length: int) -> "AvarTable":
        rr = BinaryReader(r.read_bytes(length))
        major = rr.read_u16()
        minor = rr.read_u16()
        if (major, minor) != (1, 0):
            raise FontParseException("Invalid avar table", format_name="TTF")
        rr.read_u16()  # reserved
        axis_count = rr.read_u16()
        axis_maps: list[AvarAxisMap] = []
        for _ in range(axis_count):
            segment_count = rr.read_u16()
            mapping = [(rr.read_f2dot14(), rr.read_f2dot14()) for _ in range(segment_count)]
            axis_maps.append(AvarAxisMap(mapping=mapping))
        return cls(axis_maps=axis_maps)

    def map_normalized(self, axis_index: int, value: float) -> float:
        if axis_index < 0 or axis_index >= len(self.axis_maps):
            return value
        mapping = self.axis_maps[axis_index].mapping
        if not mapping:
            return value
        if value <= mapping[0][0]:
            return mapping[0][1]
        for (x0, y0), (x1, y1) in zip(mapping, mapping[1:]):
            if value == x0:
                return y0
            if value <= x1:
                if x1 == x0:
                    return y1
                t = (value - x0) / (x1 - x0)
                return y0 + (y1 - y0) * t
        return mapping[-1][1]
