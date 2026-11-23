"""Minimal avar table parser for variable-font instancing."""

from __future__ import annotations

from dataclasses import dataclass, field

from aspose_font._exceptions import FontParseException
from aspose_font._io import BinaryReader


@dataclass(slots=True)
class AvarAxisMap:
    mapping: list[tuple[float, float]]


@dataclass
class AvarTable:
    axis_maps: list[AvarAxisMap]
    axis_tags: list[str] = field(default_factory=list)

    def __post_init__(self):
        if self.axis_tags and len(self.axis_maps) != len(self.axis_tags):
            raise FontParseException(
                f"avar table has {len(self.axis_maps)} axis maps but {len(self.axis_tags)} axis tags",
                format_name="TTF"
            )

    @classmethod
    def from_reader(cls, r: BinaryReader, length: int, axis_tags: list[str] | None = None) -> "AvarTable":
        rr = BinaryReader(r.read_bytes(length))
        major = rr.read_u16()
        minor = rr.read_u16()
        if (major, minor) != (1, 0):
            raise FontParseException("Invalid avar table", format_name="TTF")
        rr.read_u16()  # reserved
        axis_count = rr.read_u16()
        if axis_tags is not None and len(axis_tags) != axis_count:
            raise FontParseException(
                f"avar table axis count ({axis_count}) doesn't match provided axis_tags ({len(axis_tags)})",
                format_name="TTF"
            )
        axis_maps: list[AvarAxisMap] = []
        for _ in range(axis_count):
            segment_count = rr.read_u16()
            mapping = [(rr.read_f2dot14(), rr.read_f2dot14()) for _ in range(segment_count)]
            axis_maps.append(AvarAxisMap(mapping=mapping))
        if axis_tags is None:
            axis_tags = []
        return cls(axis_maps=axis_maps, axis_tags=axis_tags)

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

    def map_normalized_by_tag(self, axis_tag: str, value: float) -> float:
        try:
            axis_index = self.axis_tags.index(axis_tag)
        except ValueError:
            return value
        return self.map_normalized(axis_index, value)
