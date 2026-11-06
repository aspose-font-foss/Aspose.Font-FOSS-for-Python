"""Font format conversion pipeline (SPEC-009 / ADR-010)."""

from __future__ import annotations

import logging
import math
from collections import deque
from dataclasses import dataclass

from aspose_font._exceptions import (
    FontConversionException,
    FontNotSupportedException,
    FontParseException,
)
from aspose_font._font_base import Font, FontType
from aspose_font._types import ClosePath, CurveTo, GlyphId, GlyphPath, LineTo, MoveTo, QuadraticTo
from aspose_font.cff.charset import CffCharset
from aspose_font.cff.dict_ import PrivateDict, TopDict
from aspose_font.cff.encoding import CffEncoding
from aspose_font.cff.font import CffFont
from aspose_font.cff.index import CffIndex
from aspose_font.eot.font import EotFont
from aspose_font.ttf.font import TtfFont
from aspose_font.ttf.tables import (
    GlyfTable,
    HeadTable,
    HheaTable,
    HmtxTable,
    LocaTable,
    MaxpTable,
    Os2Table,
    PostTable,
    TtfTableSet,
)
from aspose_font.ttf.tables.cmap import CmapSubtable, CmapTable
from aspose_font.ttf.tables.hmtx import HMetric
from aspose_font.ttf.tables.name import NameRecord, NameTable
from aspose_font.type1.font import Type1Font
from aspose_font.woff.woff1 import WoffFont
from aspose_font.woff.woff2 import Woff2Font

_LOG = logging.getLogger(__name__)

Point = tuple[float, float]
QuadSegment = tuple[Point, Point, Point]


_CONVERTERS: dict[tuple[FontType, FontType], str] = {
    (FontType.TTF, FontType.CFF): "_ttf_to_cff",
    (FontType.TTF, FontType.WOFF): "_wrap_to_woff",
    (FontType.TTF, FontType.WOFF2): "_wrap_to_woff2",
    (FontType.OTF, FontType.TTF): "_cff_otf_to_ttf",
    (FontType.OTF, FontType.WOFF): "_wrap_to_woff",
    (FontType.OTF, FontType.WOFF2): "_wrap_to_woff2",
    (FontType.CFF, FontType.TTF): "_cff_otf_to_ttf",
    (FontType.CFF, FontType.WOFF): "_wrap_to_woff",
    (FontType.CFF, FontType.WOFF2): "_wrap_to_woff2",
    (FontType.TYPE1, FontType.TTF): "_type1_to_ttf",
    (FontType.TYPE1, FontType.CFF): "_type1_to_cff",
    (FontType.TYPE1_PFA, FontType.TTF): "_type1_to_ttf",
    (FontType.TYPE1_PFA, FontType.CFF): "_type1_to_cff",
    (FontType.WOFF, FontType.TTF): "_unwrap_woff",
    (FontType.WOFF, FontType.WOFF2): "_woff_to_woff2",
    (FontType.WOFF2, FontType.TTF): "_unwrap_woff2",
    (FontType.WOFF2, FontType.WOFF): "_woff2_to_woff",
    (FontType.EOT, FontType.TTF): "_unwrap_eot",
    (FontType.EOT, FontType.OTF): "_eot_to_otf",
    (FontType.EOT, FontType.WOFF): "_eot_to_woff",
    (FontType.EOT, FontType.WOFF2): "_eot_to_woff2",
    (FontType.TTF, FontType.EOT): "_ttf_to_eot",
    (FontType.OTF, FontType.EOT): "_otf_to_eot",
}


class FontConverter:
    @staticmethod
    def convert(font: Font, target: FontType) -> Font:
        if font.font_type == target:
            return font

        key = (font.font_type, target)
        method_name = _CONVERTERS.get(key)
        if method_name is None:
            raise FontConversionException(
                f"No conversion path from {font.font_type.value} to {target.value}"
            )

        method = getattr(FontConverter, method_name)
        return method(font)

    @staticmethod
    def _ttf_to_cff(font: TtfFont) -> CffFont:
        if not isinstance(font, TtfFont):
            raise FontConversionException("TTF -> CFF expects TtfFont input")

        head = font.ttf_tables.head
        bbox = (
            int(head.x_min) if head is not None else 0,
            int(head.y_min) if head is not None else 0,
            int(head.x_max) if head is not None else 0,
            int(head.y_max) if head is not None else 0,
        )
        upm = max(1, int(font.metrics.units_per_em))
        scale = 1.0 / float(upm)

        glyph_names: list[str] = []
        charstrings: list[bytes] = []
        for gid in range(font.num_glyphs):
            glyph = font.glyph_accessor.get_glyph_by_id(GlyphId(gid))
            name = glyph.glyph_name
            if not name:
                name = ".notdef" if gid == 0 else f"glyph{gid}"
            glyph_names.append(name)
            path = glyph.path if glyph.path is not None else GlyphPath()
            cubic_path = CurveAdapter.convert_path_quad_to_cubic(path)
            charstrings.append(_path_to_type2(cubic_path, glyph.advance_width, nominal_width_x=0))

        if glyph_names and glyph_names[0] != ".notdef":
            glyph_names[0] = ".notdef"

        top_dict = TopDict(
            full_name=font.font_name or font.font_family or "ConvertedFont",
            family_name=font.font_family or font.font_name or "Converted",
            weight=font.font_style or "Regular",
            font_bbox=bbox,
            charstring_type=2,
            font_matrix=(scale, 0.0, 0.0, scale, 0.0, 0.0),
        )
        private_dict = PrivateDict(default_width_x=0, nominal_width_x=0)

        charset = CffCharset(glyph_names if glyph_names else [".notdef"])
        encoding = CffEncoding(_collect_encoding_map(font))

        return CffFont(
            data=b"",
            top_dict=top_dict,
            private_dict=private_dict,
            charset=charset,
            encoding=encoding,
            charstrings=CffIndex(charstrings if charstrings else [bytes([14])]),
            global_subrs=CffIndex([]),
            local_subrs=CffIndex([]),
            string_index=CffIndex([]),
        )

    @staticmethod
    def _cff_otf_to_ttf(font: CffFont | TtfFont) -> TtfFont:
        cff = font
        if isinstance(font, TtfFont):
            if font.cff_font is None:
                raise FontConversionException("OTF -> TTF requires embedded CFF data")
            cff = font.cff_font
        if not isinstance(cff, CffFont):
            raise FontConversionException("CFF/OTF -> TTF expects CffFont or CFF-backed TtfFont")
        return _build_ttf_from_outline_font(cff)

    @staticmethod
    def _type1_to_ttf(font: Type1Font) -> TtfFont:
        if not isinstance(font, Type1Font):
            raise FontConversionException("Type1 -> TTF expects Type1Font input")
        return _build_ttf_from_outline_font(font)

    @staticmethod
    def _type1_to_cff(font: Type1Font) -> CffFont:
        if not isinstance(font, Type1Font):
            raise FontConversionException("Type1 -> CFF expects Type1Font input")

        glyph_names: list[str] = []
        charstrings: list[bytes] = []
        for gid in range(font.num_glyphs):
            try:
                glyph = font.glyph_accessor.get_glyph_by_id(GlyphId(gid))
                name = glyph.glyph_name
                path = glyph.path if glyph.path is not None else GlyphPath()
                aw = glyph.advance_width
            except (FontNotSupportedException, FontParseException) as exc:
                _LOG.warning("Skipping glyph %d (unsupported feature: %s)", gid, exc)
                name = ""
                path = GlyphPath()
                aw = 0
            if not name:
                name = ".notdef" if gid == 0 else f"glyph{gid}"
            glyph_names.append(name)
            charstrings.append(_path_to_type2(path, aw, nominal_width_x=0))

        if glyph_names and glyph_names[0] != ".notdef":
            glyph_names[0] = ".notdef"

        metrics = font.metrics
        top_dict = TopDict(
            full_name=font.font_name or font.font_family or "ConvertedFont",
            family_name=font.font_family or font.font_name or "Converted",
            weight=font.font_style or "Regular",
            font_bbox=(0, metrics.descender, max(metrics.advance_width_max, 0), metrics.ascender),
            charstring_type=2,
            font_matrix=(0.001, 0.0, 0.0, 0.001, 0.0, 0.0),
        )
        private_dict = PrivateDict(
            default_width_x=0,
            nominal_width_x=0,
            std_hw=getattr(font._font_data, "std_hw", 0.0),
            std_vw=getattr(font._font_data, "std_vw", 0.0),
        )

        return CffFont(
            data=b"",
            top_dict=top_dict,
            private_dict=private_dict,
            charset=CffCharset(glyph_names if glyph_names else [".notdef"]),
            encoding=CffEncoding(_collect_encoding_map(font)),
            charstrings=CffIndex(charstrings if charstrings else [bytes([14])]),
            global_subrs=CffIndex([]),
            local_subrs=CffIndex([]),
            string_index=CffIndex([]),
        )

    @staticmethod
    def _wrap_to_woff(font: Font) -> WoffFont:
        inner = _ensure_ttf_inner_font(font)
        return WoffFont(inner=inner)

    @staticmethod
    def _wrap_to_woff2(font: Font) -> Woff2Font:
        inner = _ensure_ttf_inner_font(font)
        return Woff2Font(inner=inner)

    @staticmethod
    def _unwrap_woff(font: WoffFont) -> TtfFont:
        if not isinstance(font, WoffFont):
            raise FontConversionException("WOFF -> TTF expects WoffFont input")
        inner = _clone_ttf_font(font.inner_font)
        if inner.font_type == FontType.OTF:
            return FontConverter._cff_otf_to_ttf(inner)
        return inner

    @staticmethod
    def _unwrap_woff2(font: Woff2Font) -> TtfFont:
        if not isinstance(font, Woff2Font):
            raise FontConversionException("WOFF2 -> TTF expects Woff2Font input")
        inner = _clone_ttf_font(font.inner_font)
        if inner.font_type == FontType.OTF:
            return FontConverter._cff_otf_to_ttf(inner)
        return inner

    @staticmethod
    def _woff_to_woff2(font: WoffFont) -> Woff2Font:
        return FontConverter._wrap_to_woff2(FontConverter._unwrap_woff(font))

    @staticmethod
    def _woff2_to_woff(font: Woff2Font) -> WoffFont:
        return FontConverter._wrap_to_woff(FontConverter._unwrap_woff2(font))

    @staticmethod
    def _ttf_to_eot(font: TtfFont) -> EotFont:
        if not isinstance(font, TtfFont) or font.font_type != FontType.TTF:
            raise FontConversionException("TTF -> EOT expects TrueType-backed TtfFont input")
        return EotFont(inner=font)

    @staticmethod
    def _otf_to_eot(font: TtfFont) -> EotFont:
        if not isinstance(font, TtfFont) or font.font_type != FontType.OTF:
            raise FontConversionException("OTF -> EOT expects OTF-backed TtfFont input")
        return EotFont(inner=font)

    @staticmethod
    def _unwrap_eot(font: EotFont) -> TtfFont:
        if not isinstance(font, EotFont):
            raise FontConversionException("EOT -> TTF expects EotFont input")
        inner = font.inner_font
        if inner.font_type == FontType.OTF:
            return FontConverter._cff_otf_to_ttf(inner)
        return inner

    @staticmethod
    def _eot_to_otf(font: EotFont) -> TtfFont:
        if not isinstance(font, EotFont):
            raise FontConversionException("EOT -> OTF expects EotFont input")
        inner = font.inner_font
        if inner.font_type != FontType.OTF:
            raise FontConversionException("EOT font does not contain OTF payload")
        return inner

    @staticmethod
    def _eot_to_woff(font: EotFont) -> WoffFont:
        if not isinstance(font, EotFont):
            raise FontConversionException("EOT -> WOFF expects EotFont input")
        return FontConverter._wrap_to_woff(FontConverter._unwrap_eot(font))

    @staticmethod
    def _eot_to_woff2(font: EotFont) -> Woff2Font:
        if not isinstance(font, EotFont):
            raise FontConversionException("EOT -> WOFF2 expects EotFont input")
        return FontConverter._wrap_to_woff2(FontConverter._unwrap_eot(font))


class CurveAdapter:
    @staticmethod
    def quad_to_cubic(p0: Point, q: Point, p3: Point) -> tuple[Point, Point, Point, Point]:
        c1x = p0[0] + (2.0 / 3.0) * (q[0] - p0[0])
        c1y = p0[1] + (2.0 / 3.0) * (q[1] - p0[1])
        c2x = p3[0] + (2.0 / 3.0) * (q[0] - p3[0])
        c2y = p3[1] + (2.0 / 3.0) * (q[1] - p3[1])
        return p0, (c1x, c1y), (c2x, c2y), p3

    @staticmethod
    def cubic_to_quads(
        p0: Point,
        c1: Point,
        c2: Point,
        p3: Point,
        tolerance: float = 0.5,
    ) -> list[QuadSegment]:
        if tolerance <= 0:
            raise FontConversionException("cubic_to_quads tolerance must be > 0")

        queue: deque[tuple[Point, Point, Point, Point, int]] = deque([(p0, c1, c2, p3, 0)])
        out: list[QuadSegment] = []
        subdivisions = 0

        while queue:
            s0, s1, s2, s3, depth = queue.popleft()
            err = CurveAdapter._cubic_midpoint_error(s0, s1, s2, s3)
            if err <= tolerance:
                qx = (s1[0] + s2[0]) / 2.0
                qy = (s1[1] + s2[1]) / 2.0
                out.append((s0, (qx, qy), s3))
                continue

            if depth >= 32:
                _LOG.warning(
                    "cubic_to_quads reached max subdivision depth (%d); accepting approximation",
                    depth,
                )
                qx = (s1[0] + s2[0]) / 2.0
                qy = (s1[1] + s2[1]) / 2.0
                out.append((s0, (qx, qy), s3))
                continue

            left0, left1, left2, left3, right0, right1, right2, right3 = CurveAdapter._subdivide_cubic(
                s0, s1, s2, s3
            )
            queue.appendleft((right0, right1, right2, right3, depth + 1))
            queue.appendleft((left0, left1, left2, left3, depth + 1))
            subdivisions += 1

        _LOG.debug("cubic_to_quads subdivided %d times (tolerance=%s)", subdivisions, tolerance)
        return out

    @staticmethod
    def _cubic_midpoint_error(p0: Point, c1: Point, c2: Point, p3: Point) -> float:
        cx = (p0[0] + 3.0 * c1[0] + 3.0 * c2[0] + p3[0]) / 8.0
        cy = (p0[1] + 3.0 * c1[1] + 3.0 * c2[1] + p3[1]) / 8.0

        qx = (c1[0] + c2[0]) / 2.0
        qy = (c1[1] + c2[1]) / 2.0
        mx = (p0[0] + 2.0 * qx + p3[0]) / 4.0
        my = (p0[1] + 2.0 * qy + p3[1]) / 4.0
        return math.hypot(cx - mx, cy - my)

    @staticmethod
    def _subdivide_cubic(
        p0: Point,
        c1: Point,
        c2: Point,
        p3: Point,
    ) -> tuple[Point, Point, Point, Point, Point, Point, Point, Point]:
        p01 = _lerp(p0, c1)
        p12 = _lerp(c1, c2)
        p23 = _lerp(c2, p3)
        p012 = _lerp(p01, p12)
        p123 = _lerp(p12, p23)
        pm = _lerp(p012, p123)
        return p0, p01, p012, pm, pm, p123, p23, p3

    @staticmethod
    def convert_path_quad_to_cubic(path: GlyphPath) -> GlyphPath:
        out = GlyphPath()
        current: Point | None = None
        subpath_start: Point | None = None

        for cmd in path:
            if isinstance(cmd, MoveTo):
                out.append(MoveTo(cmd.x, cmd.y))
                current = (cmd.x, cmd.y)
                subpath_start = current
            elif isinstance(cmd, LineTo):
                out.append(LineTo(cmd.x, cmd.y))
                current = (cmd.x, cmd.y)
            elif isinstance(cmd, QuadraticTo):
                if current is None:
                    raise FontConversionException("QuadraticTo encountered before MoveTo")
                _, c1, c2, p3 = CurveAdapter.quad_to_cubic(
                    current,
                    (cmd.x1, cmd.y1),
                    (cmd.x, cmd.y),
                )
                out.append(CurveTo(c1[0], c1[1], c2[0], c2[1], p3[0], p3[1]))
                current = p3
            elif isinstance(cmd, CurveTo):
                out.append(CurveTo(cmd.x1, cmd.y1, cmd.x2, cmd.y2, cmd.x, cmd.y))
                current = (cmd.x, cmd.y)
            elif isinstance(cmd, ClosePath):
                out.append(ClosePath())
                current = subpath_start
        return out

    @staticmethod
    def convert_path_cubic_to_quad(path: GlyphPath, tolerance: float = 0.5) -> GlyphPath:
        out = GlyphPath()
        current: Point | None = None
        subpath_start: Point | None = None

        for cmd in path:
            if isinstance(cmd, MoveTo):
                out.append(MoveTo(cmd.x, cmd.y))
                current = (cmd.x, cmd.y)
                subpath_start = current
            elif isinstance(cmd, LineTo):
                out.append(LineTo(cmd.x, cmd.y))
                current = (cmd.x, cmd.y)
            elif isinstance(cmd, CurveTo):
                if current is None:
                    raise FontConversionException("CurveTo encountered before MoveTo")
                quads = CurveAdapter.cubic_to_quads(
                    current,
                    (cmd.x1, cmd.y1),
                    (cmd.x2, cmd.y2),
                    (cmd.x, cmd.y),
                    tolerance=tolerance,
                )
                for _, q, p3 in quads:
                    out.append(QuadraticTo(q[0], q[1], p3[0], p3[1]))
                current = (cmd.x, cmd.y)
            elif isinstance(cmd, QuadraticTo):
                out.append(QuadraticTo(cmd.x1, cmd.y1, cmd.x, cmd.y))
                current = (cmd.x, cmd.y)
            elif isinstance(cmd, ClosePath):
                out.append(ClosePath())
                current = subpath_start

        return out


# Standalone utilities required by SPEC-009 FR-6.
def quad_to_cubic(p0: Point, q: Point, p3: Point) -> tuple[Point, Point, Point, Point]:
    return CurveAdapter.quad_to_cubic(p0, q, p3)


def cubic_to_quads(
    p0: Point,
    c1: Point,
    c2: Point,
    p3: Point,
    tolerance: float = 0.5,
) -> list[QuadSegment]:
    return CurveAdapter.cubic_to_quads(p0, c1, c2, p3, tolerance=tolerance)


@dataclass(slots=True)
class _TtfGlyphPoint:
    x: int
    y: int
    on_curve: bool


def _ensure_ttf_inner_font(font: Font) -> TtfFont:
    if isinstance(font, TtfFont):
        return font
    if isinstance(font, WoffFont):
        return FontConverter._unwrap_woff(font)
    if isinstance(font, Woff2Font):
        return FontConverter._unwrap_woff2(font)
    if isinstance(font, (CffFont, Type1Font)):
        return FontConverter.convert(font, FontType.TTF)
    raise FontConversionException(f"Cannot wrap font type {font.font_type.value} to WOFF/WOFF2")


def _clone_ttf_font(font: TtfFont) -> TtfFont:
    if not isinstance(font, TtfFont):
        raise FontConversionException("Expected TtfFont while cloning wrapped inner font")
    from aspose_font.loader import FontLoader

    copied = FontLoader.open(font.to_bytes(), font_type=font.font_type)
    if not isinstance(copied, TtfFont):
        raise FontConversionException("Failed to reparse wrapped inner sfnt payload")
    return copied


def _build_ttf_from_outline_font(font: Font) -> TtfFont:
    num_glyphs = font.num_glyphs
    glyph_records: list[bytes] = []
    metrics: list[HMetric] = []
    glyph_names: list[str] = []

    global_x_min = 0
    global_y_min = 0
    global_x_max = 0
    global_y_max = 0
    have_bounds = False

    for gid in range(num_glyphs):
        try:
            glyph = font.glyph_accessor.get_glyph_by_id(GlyphId(gid))
            glyph_name = glyph.glyph_name or (".notdef" if gid == 0 else f"glyph{gid}")
            quad_path = GlyphPath()
            if glyph.path is not None:
                quad_path = CurveAdapter.convert_path_cubic_to_quad(glyph.path)
            aw = int(round(glyph.advance_width))
            lsb = int(round(glyph.lsb))
        except (FontNotSupportedException, FontParseException) as exc:
            _LOG.warning("Skipping glyph %d (unsupported feature: %s)", gid, exc)
            glyph_name = ".notdef" if gid == 0 else f"glyph{gid}"
            quad_path = GlyphPath()
            aw = 0
            lsb = 0

        glyph_names.append(glyph_name)
        raw = _path_to_glyf(quad_path)
        glyph_records.append(raw)
        metrics.append(HMetric(advance_width=max(0, aw), lsb=lsb))

        bounds = _path_bounds(quad_path)
        if bounds is not None:
            x_min, y_min, x_max, y_max = bounds
            if not have_bounds:
                global_x_min, global_y_min, global_x_max, global_y_max = bounds
                have_bounds = True
            else:
                global_x_min = min(global_x_min, x_min)
                global_y_min = min(global_y_min, y_min)
                global_x_max = max(global_x_max, x_max)
                global_y_max = max(global_y_max, y_max)

    if glyph_names and glyph_names[0] != ".notdef":
        glyph_names[0] = ".notdef"

    offsets = [0]
    glyf_chunks: list[bytes] = []
    cursor = 0
    for raw in glyph_records:
        glyf_chunks.append(raw)
        cursor += len(raw)
        pad = (4 - (cursor % 4)) % 4
        if pad:
            glyf_chunks.append(b"\x00" * pad)
            cursor += pad
        offsets.append(cursor)
    glyf_data = b"".join(glyf_chunks)

    source_metrics = font.metrics
    units_per_em = max(16, int(source_metrics.units_per_em))
    ascender = int(source_metrics.ascender)
    descender = int(source_metrics.descender)
    line_gap = int(source_metrics.line_gap)

    if not have_bounds:
        global_x_min = 0
        global_y_min = 0
        global_x_max = 0
        global_y_max = 0

    advance_width_max = max((m.advance_width for m in metrics), default=0)
    min_lsb = min((m.lsb for m in metrics), default=0)
    cmap_mapping = _collect_bmp_gid_mapping(font)

    tables = TtfTableSet()
    tables.head = HeadTable(
        magic=0x5F0F3CF5,
        major_version=1,
        minor_version=0,
        font_revision=1.0,
        checksum_adjustment=0,
        flags=0x000B,
        units_per_em=units_per_em,
        created=0,
        modified=0,
        x_min=global_x_min,
        y_min=global_y_min,
        x_max=global_x_max,
        y_max=global_y_max,
        mac_style=0,
        lowest_rec_ppem=8,
        font_direction_hint=2,
        index_to_loc_format=1,
        glyph_data_format=0,
    )
    tables.hhea = HheaTable(
        major_version=1,
        minor_version=0,
        ascender=ascender,
        descender=descender,
        line_gap=line_gap,
        advance_width_max=advance_width_max,
        min_lsb=min_lsb,
        min_rsb=0,
        x_max_extent=global_x_max,
        caret_slope_rise=1,
        caret_slope_run=0,
        caret_offset=0,
        metric_data_format=0,
        number_of_hmetrics=max(1, num_glyphs),
    )
    tables.maxp = MaxpTable(version=0x00010000, num_glyphs=num_glyphs)
    tables.os2 = _build_os2_table(
        ascender=ascender,
        descender=descender,
        line_gap=line_gap,
        metrics=metrics,
        cmap_mapping=cmap_mapping,
    )
    tables.name = _build_name_table(font)
    tables.post = _build_post_table(source_metrics.underline_position, source_metrics.underline_thickness, glyph_names)
    tables.cmap = _build_cmap_table_from_mapping(cmap_mapping)
    tables.loca = LocaTable(offsets=offsets)
    tables.hmtx = HmtxTable(metrics=metrics)
    tables.glyf = GlyfTable(_data=glyf_data)

    return TtfFont(sfnt_data=b"", tables=tables, sfnt_version=0x00010000)


def _build_name_table(font: Font) -> NameTable:
    family = (font.font_family or "Converted").strip() or "Converted"
    style = (font.font_style or "Regular").strip() or "Regular"
    full_name = (font.font_name or f"{family} {style}").strip() or f"{family} {style}"
    version = "Version 1.0"
    ps_name = _sanitize_postscript_name(full_name)

    records = [
        NameRecord(3, 1, 0x0409, 1, family),
        NameRecord(3, 1, 0x0409, 2, style),
        NameRecord(3, 1, 0x0409, 4, full_name),
        NameRecord(3, 1, 0x0409, 5, version),
        NameRecord(3, 1, 0x0409, 6, ps_name),
        NameRecord(1, 0, 0, 1, family),
        NameRecord(1, 0, 0, 2, style),
        NameRecord(1, 0, 0, 4, full_name),
        NameRecord(1, 0, 0, 5, version),
        NameRecord(1, 0, 0, 6, ps_name),
    ]
    return NameTable(records=records, _raw=b"")


def _build_post_table(underline_position: int, underline_thickness: int, glyph_names: list[str]) -> PostTable:
    raw = bytearray()
    raw.extend((0x00030000).to_bytes(4, "big"))
    raw.extend((0).to_bytes(4, "big", signed=True))
    raw.extend(int(underline_position).to_bytes(2, "big", signed=True))
    raw.extend(int(underline_thickness).to_bytes(2, "big", signed=True))
    raw.extend((0).to_bytes(4, "big"))
    raw.extend((0).to_bytes(4, "big"))
    raw.extend((0).to_bytes(4, "big"))
    raw.extend((0).to_bytes(4, "big"))
    raw.extend((0).to_bytes(4, "big"))
    return PostTable(
        version=0x00030000,
        italic_angle=0.0,
        underline_position=int(underline_position),
        underline_thickness=int(underline_thickness),
        is_fixed_pitch=0,
        glyph_names=glyph_names,
        _raw=bytes(raw),
    )


def _build_cmap_table(font: Font) -> CmapTable:
    mapping = _collect_bmp_gid_mapping(font)
    return _build_cmap_table_from_mapping(mapping)


def _build_cmap_table_from_mapping(mapping: dict[int, int]) -> CmapTable:
    subtable = CmapSubtable(platform_id=3, encoding_id=1, format=4, _mapping=mapping)
    return CmapTable(subtables=[subtable], _raw=b"")


def _collect_encoding_map(font: Font) -> dict[int, int]:
    mapping: dict[int, int] = {}
    for codepoint in font.encoding.get_all_codepoints():
        if codepoint < 0 or codepoint > 255:
            continue
        try:
            mapping[codepoint] = int(font.encoding.unicode_to_gid(codepoint))
        except Exception:
            continue
    return mapping


def _collect_bmp_gid_mapping(font: Font) -> dict[int, int]:
    mapping: dict[int, int] = {}
    for codepoint in font.encoding.get_all_codepoints():
        if codepoint < 0 or codepoint > 0xFFFF:
            continue
        try:
            mapping[codepoint] = int(font.encoding.unicode_to_gid(codepoint))
        except Exception:
            continue
    return mapping


def _build_os2_table(
    *,
    ascender: int,
    descender: int,
    line_gap: int,
    metrics: list[HMetric],
    cmap_mapping: dict[int, int],
) -> Os2Table:
    first_char = min(cmap_mapping.keys(), default=0)
    last_char = max(cmap_mapping.keys(), default=0)
    non_zero_advances = [m.advance_width for m in metrics if m.advance_width > 0]
    avg_char_width = (
        int(round(sum(non_zero_advances) / len(non_zero_advances))) if non_zero_advances else 0
    )
    us_win_ascent = max(0, ascender)
    us_win_descent = max(0, -descender)

    raw = bytearray()
    raw.extend((0).to_bytes(2, "big"))  # version
    raw.extend(int(avg_char_width).to_bytes(2, "big", signed=True))
    raw.extend((400).to_bytes(2, "big"))  # usWeightClass: Regular
    raw.extend((5).to_bytes(2, "big"))  # usWidthClass: Medium (normal)
    raw.extend((0).to_bytes(2, "big"))  # fsType
    for _ in range(11):
        raw.extend((0).to_bytes(2, "big", signed=True))
    raw.extend(b"\x00" * 10)  # panose
    raw.extend((0).to_bytes(4, "big"))  # ulUnicodeRange1
    raw.extend((0).to_bytes(4, "big"))  # ulUnicodeRange2
    raw.extend((0).to_bytes(4, "big"))  # ulUnicodeRange3
    raw.extend((0).to_bytes(4, "big"))  # ulUnicodeRange4
    raw.extend(b"PfEd")  # achVendID
    raw.extend((0x0040).to_bytes(2, "big"))  # fsSelection: regular
    raw.extend(first_char.to_bytes(2, "big"))
    raw.extend(last_char.to_bytes(2, "big"))
    raw.extend(int(ascender).to_bytes(2, "big", signed=True))
    raw.extend(int(descender).to_bytes(2, "big", signed=True))
    raw.extend(int(line_gap).to_bytes(2, "big", signed=True))
    raw.extend(int(us_win_ascent).to_bytes(2, "big"))
    raw.extend(int(us_win_descent).to_bytes(2, "big"))
    data = bytes(raw)

    return Os2Table(
        version=0,
        fs_type=0,
        s_typo_ascender=int(ascender),
        s_typo_descender=int(descender),
        s_typo_line_gap=int(line_gap),
        us_win_ascent=us_win_ascent,
        us_win_descent=us_win_descent,
        fs_selection=0x0040,
        panose=b"\x00" * 10,
        ach_vend_id="PfEd",
        _raw=data,
    )


def _sanitize_postscript_name(name: str) -> str:
    out = []
    for ch in name:
        if ch.isalnum() or ch in ".-_":
            out.append(ch)
        elif ch.isspace():
            out.append("-")
    clean = "".join(out).strip("-")
    return clean or "ConvertedFont"


def _lerp(a: Point, b: Point) -> Point:
    return ((a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0)


def _encode_type2_number(v: float | int) -> bytes:
    n = int(round(v))
    if -107 <= n <= 107:
        return bytes([n + 139])
    if 108 <= n <= 1131:
        n2 = n - 108
        return bytes([(n2 // 256) + 247, n2 % 256])
    if -1131 <= n <= -108:
        n2 = -n - 108
        return bytes([(n2 // 256) + 251, n2 % 256])
    if -32768 <= n <= 32767:
        return bytes([28]) + n.to_bytes(2, "big", signed=True)
    return bytes([29]) + n.to_bytes(4, "big", signed=True)


def _path_to_type2(path: GlyphPath, advance_width: int, nominal_width_x: int) -> bytes:
    out = bytearray()
    current_x = 0.0
    current_y = 0.0
    first_moveto = True

    for cmd in path:
        if isinstance(cmd, MoveTo):
            dx = cmd.x - current_x
            dy = cmd.y - current_y
            if first_moveto and int(advance_width) != int(nominal_width_x):
                out.extend(_encode_type2_number(int(advance_width) - int(nominal_width_x)))
            out.extend(_encode_type2_number(dx))
            out.extend(_encode_type2_number(dy))
            out.append(21)  # rmoveto
            current_x = cmd.x
            current_y = cmd.y
            first_moveto = False
        elif isinstance(cmd, LineTo):
            dx = cmd.x - current_x
            dy = cmd.y - current_y
            out.extend(_encode_type2_number(dx))
            out.extend(_encode_type2_number(dy))
            out.append(5)  # rlineto
            current_x = cmd.x
            current_y = cmd.y
        elif isinstance(cmd, CurveTo):
            dx1 = cmd.x1 - current_x
            dy1 = cmd.y1 - current_y
            dx2 = cmd.x2 - cmd.x1
            dy2 = cmd.y2 - cmd.y1
            dx3 = cmd.x - cmd.x2
            dy3 = cmd.y - cmd.y2
            out.extend(_encode_type2_number(dx1))
            out.extend(_encode_type2_number(dy1))
            out.extend(_encode_type2_number(dx2))
            out.extend(_encode_type2_number(dy2))
            out.extend(_encode_type2_number(dx3))
            out.extend(_encode_type2_number(dy3))
            out.append(8)  # rrcurveto
            current_x = cmd.x
            current_y = cmd.y
        elif isinstance(cmd, QuadraticTo):
            raise FontConversionException("Type2 compilation requires cubic paths; found QuadraticTo")
        elif isinstance(cmd, ClosePath):
            continue

    if first_moveto and int(advance_width) != int(nominal_width_x):
        out.extend(_encode_type2_number(int(advance_width) - int(nominal_width_x)))
    out.append(14)  # endchar
    return bytes(out)


def _path_bounds(path: GlyphPath) -> tuple[int, int, int, int] | None:
    pts: list[tuple[float, float]] = []
    for cmd in path:
        if isinstance(cmd, MoveTo):
            pts.append((cmd.x, cmd.y))
        elif isinstance(cmd, LineTo):
            pts.append((cmd.x, cmd.y))
        elif isinstance(cmd, QuadraticTo):
            pts.append((cmd.x1, cmd.y1))
            pts.append((cmd.x, cmd.y))
        elif isinstance(cmd, CurveTo):
            pts.append((cmd.x1, cmd.y1))
            pts.append((cmd.x2, cmd.y2))
            pts.append((cmd.x, cmd.y))

    if not pts:
        return None

    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return (
        int(math.floor(min(xs))),
        int(math.floor(min(ys))),
        int(math.ceil(max(xs))),
        int(math.ceil(max(ys))),
    )


def _path_to_glyf(path: GlyphPath) -> bytes:
    contours: list[list[_TtfGlyphPoint]] = []
    current: list[_TtfGlyphPoint] | None = None

    def close_current() -> None:
        nonlocal current
        if current is not None and len(current) > 0:
            contours.append(current)
        current = None

    for cmd in path:
        if isinstance(cmd, MoveTo):
            close_current()
            current = [_TtfGlyphPoint(int(round(cmd.x)), int(round(cmd.y)), True)]
        elif isinstance(cmd, LineTo):
            if current is None:
                current = [_TtfGlyphPoint(0, 0, True)]
            current.append(_TtfGlyphPoint(int(round(cmd.x)), int(round(cmd.y)), True))
        elif isinstance(cmd, QuadraticTo):
            if current is None:
                current = [_TtfGlyphPoint(0, 0, True)]
            current.append(_TtfGlyphPoint(int(round(cmd.x1)), int(round(cmd.y1)), False))
            current.append(_TtfGlyphPoint(int(round(cmd.x)), int(round(cmd.y)), True))
        elif isinstance(cmd, CurveTo):
            raise FontConversionException("glyf compilation requires quadratic paths; found CurveTo")
        elif isinstance(cmd, ClosePath):
            close_current()

    close_current()
    contours = [c for c in contours if c]
    if not contours:
        return b""

    all_points = [p for contour in contours for p in contour]
    x_min = min(p.x for p in all_points)
    y_min = min(p.y for p in all_points)
    x_max = max(p.x for p in all_points)
    y_max = max(p.y for p in all_points)

    end_pts: list[int] = []
    last = -1
    for contour in contours:
        last += len(contour)
        end_pts.append(last)

    flags = bytearray()
    x_bytes = bytearray()
    y_bytes = bytearray()

    prev_x = 0
    prev_y = 0
    for point in all_points:
        flag = 0x01 if point.on_curve else 0

        dx = point.x - prev_x
        if dx == 0:
            flag |= 0x10
        elif -255 <= dx <= 255:
            flag |= 0x02
            if dx > 0:
                flag |= 0x10
                x_bytes.append(dx)
            else:
                x_bytes.append(-dx)
        else:
            x_bytes.extend(int(dx).to_bytes(2, "big", signed=True))

        dy = point.y - prev_y
        if dy == 0:
            flag |= 0x20
        elif -255 <= dy <= 255:
            flag |= 0x04
            if dy > 0:
                flag |= 0x20
                y_bytes.append(dy)
            else:
                y_bytes.append(-dy)
        else:
            y_bytes.extend(int(dy).to_bytes(2, "big", signed=True))

        flags.append(flag)
        prev_x = point.x
        prev_y = point.y

    out = bytearray()
    out.extend(int(len(contours)).to_bytes(2, "big", signed=True))
    out.extend(int(x_min).to_bytes(2, "big", signed=True))
    out.extend(int(y_min).to_bytes(2, "big", signed=True))
    out.extend(int(x_max).to_bytes(2, "big", signed=True))
    out.extend(int(y_max).to_bytes(2, "big", signed=True))
    for end in end_pts:
        out.extend(int(end).to_bytes(2, "big"))
    out.extend((0).to_bytes(2, "big"))
    out.extend(flags)
    out.extend(x_bytes)
    out.extend(y_bytes)
    return bytes(out)


__all__ = [
    "FontConverter",
    "CurveAdapter",
    "quad_to_cubic",
    "cubic_to_quads",
]
