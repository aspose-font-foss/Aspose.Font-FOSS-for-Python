"""TrueType glyf outline parsing into GlyphPath."""

from __future__ import annotations

from dataclasses import dataclass

from aspose_font._exceptions import FontParseException, GlyphNotFoundException
from aspose_font._io import BinaryReader
from aspose_font._types import (
    ClosePath,
    CurveTo,
    Glyph,
    GlyphId,
    GlyphPath,
    LineTo,
    MoveTo,
    QuadraticTo,
)
from aspose_font.ttf.tables.glyf import GlyfTable
from aspose_font.ttf.tables.hmtx import HmtxTable
from aspose_font.ttf.tables.loca import LocaTable

_ON_CURVE_POINT = 0x01
_X_SHORT_VECTOR = 0x02
_Y_SHORT_VECTOR = 0x04
_REPEAT_FLAG = 0x08
_X_IS_SAME_OR_POSITIVE_X_SHORT_VECTOR = 0x10
_Y_IS_SAME_OR_POSITIVE_Y_SHORT_VECTOR = 0x20

_ARG_1_AND_2_ARE_WORDS = 0x0001
_ARGS_ARE_XY_VALUES = 0x0002
_WE_HAVE_A_SCALE = 0x0008
_MORE_COMPONENTS = 0x0020
_WE_HAVE_AN_X_AND_Y_SCALE = 0x0040
_WE_HAVE_A_TWO_BY_TWO = 0x0080


@dataclass(slots=True)
class _Point:
    x: float
    y: float
    on_curve: bool


class TtfGlyphParser:
    def __init__(self, loca: LocaTable, glyf: GlyfTable, hmtx: HmtxTable) -> None:
        self._loca = loca
        self._glyf = glyf
        self._hmtx = hmtx

    def parse(self, gid: GlyphId) -> Glyph:
        return self._parse_gid(gid, depth=0)

    def _parse_gid(self, gid: GlyphId, depth: int) -> Glyph:
        idx = int(gid)
        if idx < 0 or idx + 1 >= len(self._loca.offsets):
            raise GlyphNotFoundException(idx)

        metric = self._hmtx.get_metric(idx)
        try:
            offset = self._loca.glyph_offset(idx)
            length = self._loca.glyph_length(idx)
            if length <= 0:
                return Glyph(glyph_id=gid, glyph_name=None, path=None, advance_width=metric.advance_width, lsb=metric.lsb)

            data = self._glyf.get_glyph_bytes(offset, length)
            r = BinaryReader(data)
            n_contours = r.read_i16()
            r.read_i16()  # xMin
            r.read_i16()  # yMin
            r.read_i16()  # xMax
            r.read_i16()  # yMax

            if n_contours == 0:
                path = None
            elif n_contours > 0:
                path = self._parse_simple(r, n_contours, idx)
            elif n_contours == -1:
                path = self._parse_composite(r, idx, depth)
            else:
                raise FontParseException(f"Invalid contour count for GID {idx}: {n_contours}", format_name="TTF")
            return Glyph(
                glyph_id=gid,
                glyph_name=None,
                path=path,
                advance_width=metric.advance_width,
                lsb=metric.lsb,
            )
        except FontParseException as exc:
            raise FontParseException(
                f"Corrupt glyph data for GID {idx}: {exc}",
                format_name="TTF",
            ) from exc

    def _parse_simple(self, r: BinaryReader, n_contours: int, gid: int) -> GlyphPath:
        contour_ends = [r.read_u16() for _ in range(n_contours)]
        if not contour_ends:
            raise FontParseException(f"Simple glyph with no contours for GID {gid}", format_name="TTF")
        if any(contour_ends[i] <= contour_ends[i - 1] for i in range(1, len(contour_ends))):
            raise FontParseException(f"Invalid contour end points for GID {gid}", format_name="TTF")

        n_points = contour_ends[-1] + 1
        instruction_len = r.read_u16()
        r.read_bytes(instruction_len)

        flags = self._decode_flags(r, n_points)
        xs = self._decode_coords(
            r,
            n_points=n_points,
            flags=flags,
            same_or_positive_bit=_X_IS_SAME_OR_POSITIVE_X_SHORT_VECTOR,
            short_bit=_X_SHORT_VECTOR,
        )
        ys = self._decode_coords(
            r,
            n_points=n_points,
            flags=flags,
            same_or_positive_bit=_Y_IS_SAME_OR_POSITIVE_Y_SHORT_VECTOR,
            short_bit=_Y_SHORT_VECTOR,
        )

        return self._flags_to_path(contour_ends, flags, xs, ys)

    def _parse_composite(self, r: BinaryReader, gid: int, depth: int) -> GlyphPath:
        if depth > 8:
            raise FontParseException(f"Composite glyph recursion limit at GID {gid}", format_name="TTF")

        out = GlyphPath()
        while True:
            flags = r.read_u16()
            component_gid = r.read_u16()

            if flags & _ARG_1_AND_2_ARE_WORDS:
                arg1 = r.read_i16()
                arg2 = r.read_i16()
            else:
                arg1 = r.read_i8()
                arg2 = r.read_i8()

            dx = float(arg1) if (flags & _ARGS_ARE_XY_VALUES) else 0.0
            dy = float(arg2) if (flags & _ARGS_ARE_XY_VALUES) else 0.0

            xx = 1.0
            yx = 0.0
            xy = 0.0
            yy = 1.0
            if flags & _WE_HAVE_A_SCALE:
                scale = r.read_f2dot14()
                xx = scale
                yy = scale
            elif flags & _WE_HAVE_AN_X_AND_Y_SCALE:
                xx = r.read_f2dot14()
                yy = r.read_f2dot14()
            elif flags & _WE_HAVE_A_TWO_BY_TWO:
                xx = r.read_f2dot14()
                yx = r.read_f2dot14()
                xy = r.read_f2dot14()
                yy = r.read_f2dot14()

            component = self._parse_gid(GlyphId(component_gid), depth + 1)
            if component.path is not None:
                transformed = self._apply_transform(component.path, xx, yx, xy, yy, dx, dy)
                out.extend(list(transformed))

            if not (flags & _MORE_COMPONENTS):
                break

        return out if len(out) > 0 else None

    def _decode_flags(self, r: BinaryReader, n_points: int) -> list[int]:
        flags: list[int] = []
        i = 0
        while i < n_points:
            f = r.read_u8()
            flags.append(f)
            if f & _REPEAT_FLAG:
                repeat_count = r.read_u8()
                flags.extend([f] * repeat_count)
                i += repeat_count + 1
            else:
                i += 1
        if len(flags) != n_points:
            raise FontParseException("Invalid flag expansion in simple glyph", format_name="TTF")
        return flags

    def _decode_coords(
        self,
        r: BinaryReader,
        n_points: int,
        flags: list[int],
        same_or_positive_bit: int,
        short_bit: int,
    ) -> list[int]:
        coords: list[int] = []
        acc = 0
        for i in range(n_points):
            flag = flags[i]
            if flag & short_bit:
                delta = r.read_u8()
                if not (flag & same_or_positive_bit):
                    delta = -delta
            elif flag & same_or_positive_bit:
                delta = 0
            else:
                delta = r.read_i16()
            acc += delta
            coords.append(acc)
        return coords

    def _flags_to_path(
        self,
        contour_ends: list[int],
        flags: list[int],
        xs: list[int],
        ys: list[int],
    ) -> GlyphPath:
        path = GlyphPath()
        contour_start = 0

        for contour_end in contour_ends:
            if contour_end < contour_start:
                raise FontParseException("Corrupt contour range", format_name="TTF")
            points = [
                _Point(float(xs[i]), float(ys[i]), bool(flags[i] & _ON_CURVE_POINT))
                for i in range(contour_start, contour_end + 1)
            ]
            contour_start = contour_end + 1
            if not points:
                continue

            first_on = next((i for i, p in enumerate(points) if p.on_curve), -1)
            if first_on >= 0:
                ordered = points[first_on:] + points[:first_on]
                start = ordered[0]
            else:
                mid_x = (points[-1].x + points[0].x) / 2.0
                mid_y = (points[-1].y + points[0].y) / 2.0
                start = _Point(mid_x, mid_y, True)
                ordered = [start] + points

            path.append(MoveTo(start.x, start.y))

            i = 1
            count = len(ordered)
            while i <= count:
                p = ordered[i % count]
                if p.on_curve:
                    if i < count:
                        path.append(LineTo(p.x, p.y))
                    i += 1
                    continue

                nxt = ordered[(i + 1) % count]
                if nxt.on_curve:
                    path.append(QuadraticTo(p.x, p.y, nxt.x, nxt.y))
                    i += 2
                else:
                    mid_x = (p.x + nxt.x) / 2.0
                    mid_y = (p.y + nxt.y) / 2.0
                    path.append(QuadraticTo(p.x, p.y, mid_x, mid_y))
                    i += 1

            path.append(ClosePath())

        return path

    def _apply_transform(
        self,
        path: GlyphPath,
        xx: float,
        yx: float,
        xy: float,
        yy: float,
        dx: float,
        dy: float,
    ) -> GlyphPath:
        out = GlyphPath()

        def tx(x: float, y: float) -> tuple[float, float]:
            return (x * xx + y * xy + dx, x * yx + y * yy + dy)

        for cmd in path:
            if isinstance(cmd, MoveTo):
                x, y = tx(cmd.x, cmd.y)
                out.append(MoveTo(x, y))
            elif isinstance(cmd, LineTo):
                x, y = tx(cmd.x, cmd.y)
                out.append(LineTo(x, y))
            elif isinstance(cmd, QuadraticTo):
                x1, y1 = tx(cmd.x1, cmd.y1)
                x, y = tx(cmd.x, cmd.y)
                out.append(QuadraticTo(x1, y1, x, y))
            elif isinstance(cmd, CurveTo):
                x1, y1 = tx(cmd.x1, cmd.y1)
                x2, y2 = tx(cmd.x2, cmd.y2)
                x, y = tx(cmd.x, cmd.y)
                out.append(CurveTo(x1, y1, x2, y2, x, y))
            elif isinstance(cmd, ClosePath):
                out.append(ClosePath())
        return out
