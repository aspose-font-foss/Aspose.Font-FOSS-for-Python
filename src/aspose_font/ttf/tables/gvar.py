"""Minimal gvar table parser for variable-font instancing."""

from __future__ import annotations

from dataclasses import dataclass

from aspose_font._exceptions import FontParseException
from aspose_font._io import BinaryReader

_EMBEDDED_PEAK_TUPLE = 0x8000
_INTERMEDIATE_REGION = 0x4000
_PRIVATE_POINT_NUMBERS = 0x2000
_TUPLE_INDEX_MASK = 0x0FFF


@dataclass(slots=True)
class TupleVariation:
    peak_coords: dict[str, float]
    start_coords: dict[str, float] | None
    end_coords: dict[str, float] | None
    points: list[int] | None
    deltas: list[tuple[int, int]]


@dataclass(slots=True)
class _TupleHeader:
    variation_data_size: int
    peak: tuple[float, ...]
    start: tuple[float, ...] | None
    end: tuple[float, ...] | None
    private_points: bool


@dataclass
class GvarTable:
    axis_count: int
    shared_tuples: list[tuple[float, ...]]
    glyph_offsets: list[int]
    data_offset: int
    _raw: bytes
    _axis_tags: list[str]

    @classmethod
    def from_reader(cls, r: BinaryReader, length: int, axis_tags: list[str]) -> "GvarTable":
        raw = r.read_bytes(length)
        rr = BinaryReader(raw)
        major = rr.read_u16()
        minor = rr.read_u16()
        if (major, minor) != (1, 0):
            raise FontParseException("Invalid gvar table", format_name="TTF")
        axis_count = rr.read_u16()
        shared_tuple_count = rr.read_u16()
        offset_to_shared_tuples = rr.read_u32()
        glyph_count = rr.read_u16()
        flags = rr.read_u16()
        offset_to_glyph_data = rr.read_u32()

        long_offsets = bool(flags & 0x0001)
        glyph_offsets = [rr.read_u32() if long_offsets else rr.read_u16() * 2 for _ in range(glyph_count + 1)]

        shared_reader = BinaryReader(raw[offset_to_shared_tuples:offset_to_glyph_data])
        shared_tuples = [
            tuple(shared_reader.read_f2dot14() for _ in range(axis_count))
            for _ in range(shared_tuple_count)
        ]
        return cls(
            axis_count=axis_count,
            shared_tuples=shared_tuples,
            glyph_offsets=glyph_offsets,
            data_offset=offset_to_glyph_data,
            _raw=raw,
            _axis_tags=list(axis_tags),
        )

    def glyph_variations(self, gid: int, point_count: int) -> list[TupleVariation]:
        if gid < 0 or gid + 1 >= len(self.glyph_offsets):
            return []
        start = self.glyph_offsets[gid]
        end = self.glyph_offsets[gid + 1]
        if start == end:
            return []

        data = self._raw[self.data_offset + start : self.data_offset + end]
        rr = BinaryReader(data)
        tuple_count_word = rr.read_u16()
        data_offset = rr.read_u16()
        tuple_count = tuple_count_word & _TUPLE_INDEX_MASK
        has_shared_points = bool(tuple_count_word & 0x8000)

        headers: list[_TupleHeader] = []
        for _ in range(tuple_count):
            variation_data_size = rr.read_u16()
            tuple_index = rr.read_u16()
            tuple_number = tuple_index & _TUPLE_INDEX_MASK
            if tuple_number >= len(self.shared_tuples):
                raise FontParseException("Invalid gvar table", format_name="TTF")
            peak = self.shared_tuples[tuple_number]
            start_coords = None
            end_coords = None
            if tuple_index & _EMBEDDED_PEAK_TUPLE:
                peak = tuple(rr.read_f2dot14() for _ in range(self.axis_count))
            if tuple_index & _INTERMEDIATE_REGION:
                start_coords = tuple(rr.read_f2dot14() for _ in range(self.axis_count))
                end_coords = tuple(rr.read_f2dot14() for _ in range(self.axis_count))
            headers.append(
                _TupleHeader(
                    variation_data_size=variation_data_size,
                    peak=peak,
                    start=start_coords,
                    end=end_coords,
                    private_points=bool(tuple_index & _PRIVATE_POINT_NUMBERS),
                )
            )

        if rr.tell() != data_offset:
            rr.seek(data_offset)
        shared_points: list[int] | None = None
        if has_shared_points:
            shared_points = self._decode_packed_points(rr)

        variations: list[TupleVariation] = []
        all_points_count = point_count + 4
        for header in headers:
            tuple_reader = BinaryReader(rr.read_bytes(header.variation_data_size))
            points = shared_points
            if header.private_points:
                points = self._decode_packed_points(tuple_reader)
            point_total = all_points_count if points is None else len(points)
            x_deltas = self._decode_packed_deltas(tuple_reader, point_total)
            y_deltas = self._decode_packed_deltas(tuple_reader, point_total)
            deltas = list(zip(x_deltas, y_deltas))
            variations.append(
                TupleVariation(
                    peak_coords=dict(zip(self._axis_tags, header.peak)),
                    start_coords=None if header.start is None else dict(zip(self._axis_tags, header.start)),
                    end_coords=None if header.end is None else dict(zip(self._axis_tags, header.end)),
                    points=points,
                    deltas=deltas,
                )
            )
        return variations

    @staticmethod
    def _decode_packed_points(r: BinaryReader) -> list[int] | None:
        count = r.read_u8()
        if count & 0x80:
            count = ((count & 0x7F) << 8) | r.read_u8()
        if count == 0:
            return None

        points: list[int] = []
        current = 0
        while len(points) < count:
            header = r.read_u8()
            run_count = (header & 0x7F) + 1
            wide = bool(header & 0x80)
            for _ in range(run_count):
                delta = r.read_u16() if wide else r.read_u8()
                current += delta
                points.append(current)
        return points

    @staticmethod
    def _decode_packed_deltas(r: BinaryReader, count: int) -> list[int]:
        deltas: list[int] = []
        while len(deltas) < count:
            header = r.read_u8()
            run_count = (header & 0x3F) + 1
            if header & 0x80:
                deltas.extend([0] * run_count)
            elif header & 0x40:
                deltas.extend(r.read_i16() for _ in range(run_count))
            else:
                deltas.extend(r.read_i8() for _ in range(run_count))
        return deltas[:count]
