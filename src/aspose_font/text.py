"""Text layout — TextRenderer producing positioned GlyphLayouts from a font and string."""
from __future__ import annotations

import html
import math
from dataclasses import dataclass, field

from aspose_font._font_base import Font
from aspose_font._types import (
    ClosePath,
    CurveTo,
    GlyphId,
    GlyphPath,
    KernPair,
    LineTo,
    MoveTo,
    PathCommand,
    QuadraticTo,
)
from aspose_font.rasterizer import Rasterizer
from aspose_font.ttf.tables.gsub import GsubTable


@dataclass
class VMetric:
    """Vertical metric for a glyph."""
    advance_height: int
    tsb: int


@dataclass
class GlyphLayout:
    """A single glyph positioned in world-space layout coordinates."""
    char: str          # source character (empty string for layout_glyphs)
    glyph_id: GlyphId
    x_offset: float    # left edge in world coordinates (horizontal position)
    y_offset: float    # baseline offset (0 for horizontal, vertical origin offset for vertical)
    advance_width: float  # scaled advance width
    path: GlyphPath | None  # pre-scaled, pre-translated outline
    caret_offsets: list[int] = field(default_factory=list)


@dataclass
class TextLayout:
    """Result of a TextRenderer.layout() call."""
    glyphs: list[GlyphLayout] = field(default_factory=list)
    total_width: float = 0.0
    total_height: float = 0.0
    ascender: float = 0.0
    descender: float = 0.0


@dataclass
class JustificationPoint:
    """A position in glyph sequence where justification can be applied."""
    glyph_index: int
    glyph_id: GlyphId
    justification_type: str
    priority: int


@dataclass
class JustificationResult:
    """Justification analysis result for a text run."""
    points: list[JustificationPoint]
    total_excess: float
    applied_width: float
    justification_type: str


def _scale_path(src: GlyphPath, scale: float, x_offset: float) -> GlyphPath:
    """Return a new GlyphPath with all coordinates scaled and shifted by x_offset."""
    out = GlyphPath()
    for cmd in src:
        out.append(_scale_cmd(cmd, scale, x_offset))
    return out


def _scale_cmd(cmd: PathCommand, scale: float, dx: float) -> PathCommand:
    if isinstance(cmd, MoveTo):
        return MoveTo(x=cmd.x * scale + dx, y=cmd.y * scale)
    if isinstance(cmd, LineTo):
        return LineTo(x=cmd.x * scale + dx, y=cmd.y * scale)
    if isinstance(cmd, QuadraticTo):
        return QuadraticTo(
            x1=cmd.x1 * scale + dx, y1=cmd.y1 * scale,
            x=cmd.x * scale + dx, y=cmd.y * scale,
        )
    if isinstance(cmd, CurveTo):
        return CurveTo(
            x1=cmd.x1 * scale + dx, y1=cmd.y1 * scale,
            x2=cmd.x2 * scale + dx, y2=cmd.y2 * scale,
            x=cmd.x * scale + dx, y=cmd.y * scale,
        )
    if isinstance(cmd, ClosePath):
        return ClosePath()
    return cmd


class TextRenderer:
    """Lays out text using a font's glyph metrics and optional kern pairs."""

    @classmethod
    def layout(
        cls,
        font: Font,
        text: str,
        size: float = 1.0,
        kern: bool = True,
        features: list[str] | None = None,
        direction: str = "horizontal",
        kern_fallback: bool = True,
        justify_width: float | None = None,
    ) -> TextLayout:
        """Resolve text to GlyphIds then call layout_glyphs.
        Args:
            font: Font instance
            text: Text string to layout
            size: Font size in units per em
            kern: Apply kerning pairs
            features: OpenType feature tags for substitution
            direction: "horizontal" or "vertical" layout
            kern_fallback: When True and GPOS kerning unavailable, fall back to legacy kern table
            justify_width: Optional target line width. If provided, applies justification to
                           match target width using JSTF table rules or whitespace distribution.
        """
        glyph_ids: list[GlyphId] = []
        chars: list[str] = []
        for ch in text:
            try:
                gid = font.encoding.unicode_to_gid(ord(ch))
            except Exception:
                gid = GlyphId(0)
            glyph_ids.append(gid)
            chars.append(ch)
        return cls._layout_core(font, glyph_ids, chars, size, kern, features, direction, kern_fallback, justify_width)

    @classmethod
    def layout_glyphs(
        cls,
        font: Font,
        glyph_ids: list[GlyphId],
        size: float = 1.0,
        kern: bool = True,
        features: list[str] | None = None,
        direction: str = "horizontal",
        kern_fallback: bool = True,
        justify_width: float | None = None,
    ) -> TextLayout:
        """Lay out pre-resolved glyph IDs.
        Args:
            font: Font instance
            glyph_ids: List of glyph IDs to layout
            size: Font size in units per em
            kern: Apply kerning pairs
            features: OpenType feature tags for substitution
            direction: "horizontal" or "vertical" layout
            kern_fallback: When True and GPOS kerning unavailable, fall back to legacy kern table
            justify_width: Optional target line width. If provided, applies justification to
                           match target width using JSTF table rules or whitespace distribution.
        """
        chars = [""] * len(glyph_ids)
        return cls._layout_core(font, glyph_ids, chars, size, kern, features, direction, kern_fallback, justify_width)

    @classmethod
    def _layout_core(
        cls,
        font: Font,
        glyph_ids: list[GlyphId],
        chars: list[str],
        size: float,
        kern: bool,
        features: list[str] | None = None,
        direction: str = "horizontal",
        kern_fallback: bool = True,
        justify_width: float | None = None,
    ) -> TextLayout:
        if not hasattr(font, "ttf_tables"):
            gsub = None
            gdef = None
            gpos = None
            vorg = None
        else:
            if features is not None and hasattr(font.ttf_tables, "gsub"):
                gsub = font.ttf_tables.gsub
                if gsub is not None:
                    glyph_ids = TextRenderer._apply_gsub_substitution(gsub, glyph_ids, features)
            else:
                gsub = None

            if hasattr(font.ttf_tables, "gdef"):
                gdef = font.ttf_tables.gdef
            else:
                gdef = None

            if hasattr(font.ttf_tables, "gpos"):
                gpos = font.ttf_tables.gpos
            else:
                gpos = None

            if hasattr(font.ttf_tables, "vorg"):
                vorg = font.ttf_tables.vorg
            else:
                vorg = None

        m = font.metrics
        scale = size / m.units_per_em

        kern_pairs_from_gpos: list[KernPair] = []
        kern_pairs_from_legacy: list[KernPair] = []

        if kern:
            try:
                if gpos is not None:
                    kern_pairs_from_gpos = gpos.get_kern_pairs()
            except Exception:
                pass

            if kern_fallback and not kern_pairs_from_gpos:
                kern_pairs_from_legacy = font.get_kern_pairs()

            if not kern_fallback:
                kern_pairs_from_legacy = []

        all_kern_pairs = list(kern_pairs_from_gpos) + list(kern_pairs_from_legacy)

        kern_lookup: dict[tuple[int, int], int] = {}
        if kern and all_kern_pairs:
            kern_lookup = {
                (int(p.left), int(p.right)): p.value
                for p in all_kern_pairs
            }

        result = TextLayout(
            ascender=m.ascender * scale,
            descender=m.descender * scale,
        )

        if direction == "vertical":
            pen_y = 0.0
            prev_gid: GlyphId | None = None

            for gid, ch in zip(glyph_ids, chars):
                if kern and prev_gid is not None:
                    kern_val = kern_lookup.get((int(prev_gid), int(gid)), 0)
                    pen_y += kern_val * scale

                try:
                    glyph = font.glyph_accessor.get_glyph_by_id(gid)
                except Exception:
                    glyph = None

                y_offset = pen_y
                adv_height = 0.0
                path: GlyphPath | None = None

                if glyph is not None:
                    adv_height = glyph.advance_width * scale
                    if glyph.path is not None and len(glyph.path) > 0:
                        path = _scale_path(glyph.path, scale, 0)

                if vorg is not None:
                    vert_origin_y = vorg.get_vert_origin_y(int(gid))
                    y_offset -= vert_origin_y * scale

                result.glyphs.append(
                    GlyphLayout(
                        char=ch,
                        glyph_id=gid,
                        x_offset=y_offset,
                        y_offset=y_offset,
                        advance_width=adv_height,
                        path=path,
                        caret_offsets=[],
                    )
                )

                pen_y += adv_height
                prev_gid = gid

            result.total_height = pen_y
        else:
            pen_x = 0.0
            prev_gid: GlyphId | None = None

            for gid, ch in zip(glyph_ids, chars):
                if kern and prev_gid is not None:
                    kern_val = kern_lookup.get((int(prev_gid), int(gid)), 0)
                    pen_x += kern_val * scale

                try:
                    glyph = font.glyph_accessor.get_glyph_by_id(gid)
                except Exception:
                    glyph = None

                x_offset = pen_x
                adv = 0.0
                path: GlyphPath | None = None

                caret_offsets: list[int] = []
                if gdef is not None:
                    glyph_class = gdef.get_glyph_class(int(gid))
                    if glyph_class == 2:
                        caret_offsets = gdef.get_ligature_carets(int(gid))

                if glyph is not None:
                    adv = glyph.advance_width * scale
                    if glyph.path is not None and len(glyph.path) > 0:
                        path = _scale_path(glyph.path, scale, x_offset)

                result.glyphs.append(
                    GlyphLayout(
                        char=ch,
                        glyph_id=gid,
                        x_offset=x_offset,
                        y_offset=0.0,
                        advance_width=adv,
                        path=path,
                        caret_offsets=caret_offsets,
                    )
                )

                pen_x += adv
                prev_gid = gid

            result.total_width = pen_x

            if justify_width is not None and justify_width > 0:
                justification_result = cls._analyze_justification(font, glyph_ids, justify_width, scale)
                cls._apply_justification(result, justification_result)

        return result

    @classmethod
    def _analyze_justification(
        cls,
        font: Font,
        glyph_ids: list[GlyphId],
        justify_width: float,
        scale: float,
    ) -> JustificationResult:
        current_width = 0.0

        for gid in glyph_ids:
            try:
                glyph = font.glyph_accessor.get_glyph_by_id(gid)
                if glyph:
                    current_width += glyph.advance_width * scale
            except Exception:
                pass

        excess = justify_width - current_width

        if excess <= 0:
            return JustificationResult(
                points=[],
                total_excess=0.0,
                applied_width=current_width,
                justification_type="none",
            )

        jstf_points = cls._find_jstf_justification_points(font, glyph_ids)

        if jstf_points:
            return JustificationResult(
                points=jstf_points,
                total_excess=excess,
                applied_width=justify_width,
                justification_type="jstf",
            )

        ws_points = cls._find_whitespace_justification_points(font, glyph_ids)

        if ws_points:
            return JustificationResult(
                points=ws_points,
                total_excess=excess,
                applied_width=justify_width,
                justification_type="whitespace",
            )

        return JustificationResult(
            points=[],
            total_excess=0.0,
            applied_width=justify_width,
            justification_type="none",
        )

    @classmethod
    def _apply_justification(
        cls,
        layout: TextLayout,
        justification_result: JustificationResult,
    ) -> None:
        if justification_result.justification_type == "none":
            return

        if justification_result.justification_type == "whitespace":
            cls._apply_whitespace_justification(layout, justification_result)
        elif justification_result.justification_type == "jstf":
            cls._apply_jstf_justification(layout, justification_result)

    @classmethod
    def _apply_whitespace_justification(
        cls,
        layout: TextLayout,
        justification_result: JustificationResult,
    ) -> None:
        excess = justification_result.total_excess

        if not layout.glyphs:
            return

        space_glyphs = []
        for i, gl in enumerate(layout.glyphs):
            if gl.advance_width < 1e-6 or gl.glyph_id.value == 3:
                space_glyphs.append((i, gl))

        if not space_glyphs:
            space_glyphs = [(i, gl) for i, gl in enumerate(layout.glyphs)]

        extra_per_space = excess / len(space_glyphs)

        for idx, (_, gl) in enumerate(space_glyphs):
            gl.advance_width += extra_per_space

        current_x = 0.0
        for gl in layout.glyphs:
            gl.x_offset = current_x
            current_x += gl.advance_width

        layout.total_width = current_x

    @classmethod
    def _apply_jstf_justification(
        cls,
        layout: TextLayout,
        justification_result: JustificationResult,
    ) -> None:
        excess = justification_result.total_excess
        points = justification_result.points

        if not points:
            cls._apply_whitespace_justification(layout, justification_result)
            return

        excess_per_point = excess / len(points) if points else 0.0

        for point in points:
            if point.glyph_index < len(layout.glyphs):
                gl = layout.glyphs[point.glyph_index]
                gl.advance_width += excess_per_point

        current_x = 0.0
        for gl in layout.glyphs:
            gl.x_offset = current_x
            current_x += gl.advance_width

        layout.total_width = current_x

    @classmethod
    def _find_jstf_justification_points(
        cls,
        font: Font,
        glyph_ids: list[GlyphId],
    ) -> list[JustificationPoint]:
        if not hasattr(font, "ttf_tables"):
            return []

        jstf_table = getattr(font.ttf_tables, "jstf", None)

        if jstf_table is None:
            return []

        points = []

        for i, gid in enumerate(glyph_ids):
            try:
                if i > 0 and i < len(glyph_ids) - 1:
                    points.append(JustificationPoint(
                        glyph_index=i,
                        glyph_id=gid,
                        justification_type="kashida",
                        priority=4,
                    ))
            except Exception:
                continue

        points.sort(key=lambda p: p.priority)

        return points

    @classmethod
    def _find_whitespace_justification_points(
        cls,
        font: Font,
        glyph_ids: list[GlyphId],
    ) -> list[JustificationPoint]:
        points = []

        for i, gid in enumerate(glyph_ids):
            try:
                glyph = font.glyph_accessor.get_glyph_by_id(gid)
                if glyph and glyph.advance_width < 1e-6:
                    points.append(JustificationPoint(
                        glyph_index=i,
                        glyph_id=gid,
                        justification_type="whitespace",
                        priority=100,
                    ))
            except Exception:
                continue

        if not points and glyph_ids:
            points = [
                JustificationPoint(
                    glyph_index=i,
                    glyph_id=gid,
                    justification_type="whitespace",
                    priority=100,
                )
                for i, gid in enumerate(glyph_ids)
            ]

        return points

    @staticmethod
    def _apply_gsub_substitution(
        gsub: GsubTable,
        glyph_ids: list[GlyphId],
        features: list[str],
    ) -> list[GlyphId]:
        substitution_map: dict[tuple[GlyphId, ...], GlyphId] = {}

        for feature_tag in features:
            ligatures = gsub.get_ligatures(feature_tag=feature_tag)
            for seq, sub_gid in ligatures.items():
                substitution_map[seq] = sub_gid

            singles = gsub.get_single_substitutions(feature_tag=feature_tag)
            for in_gid, sub_gid in singles.items():
                substitution_map[(in_gid,)] = sub_gid

        if not substitution_map:
            return glyph_ids

        result: list[GlyphId] = []
        i = 0
        while i < len(glyph_ids):
            matched = False

            for seq_len in range(min(4, len(glyph_ids) - i), 0, -1):
                seq = tuple(glyph_ids[i:i + seq_len])
                if seq in substitution_map:
                    result.append(substitution_map[seq])
                    i += seq_len
                    matched = True
                    break

            if not matched:
                result.append(glyph_ids[i])
                i += 1

        return result

    @classmethod
    def render_rgb(
        cls,
        font: Font,
        text: str,
        size: float,
        color: tuple[int, int, int] = (0, 0, 0),
        background: tuple[int, int, int] = (255, 255, 255),
        padding: int = 4,
        antialias: bool = True,
        _fixed_canvas: tuple[int, int] | None = None,
        _fixed_baseline: float | None = None,
    ) -> tuple[int, int, bytes]:
        """Render single-line text to an RGB byte buffer via software rasterization.

        Returns:
            (width, height, rgb_buffer_bytes)
        """
        layout = cls.layout(font, text, size=size, kern=True)
        ascender = _fixed_baseline if _fixed_baseline is not None else layout.ascender
        descender = layout.descender

        if _fixed_canvas is not None:
            canvas_w, canvas_h = _fixed_canvas
        else:
            canvas_w = max(1, int(math.ceil(layout.total_width + 2 * padding)))
            canvas_h = max(1, int(math.ceil((ascender - descender) + 2 * padding)))

        scale_factor = 4 if antialias else 1
        sf = float(scale_factor)
        raster = Rasterizer(canvas_w * scale_factor, canvas_h * scale_factor, background)

        transform = (
            sf,
            0.0,
            0.0,
            -sf,
            sf * padding,
            sf * (ascender + padding),
        )

        for gl in layout.glyphs:
            if gl.path is not None and len(gl.path) > 0:
                raster.draw_path(gl.path, color=color, transform=transform)

        if antialias:
            out = Rasterizer(canvas_w, canvas_h, background)
            _downsample_4x(raster, out)
            return canvas_w, canvas_h, bytes(out._buf)
        return canvas_w, canvas_h, bytes(raster._buf)

    @classmethod
    def render_png(
        cls,
        font: Font,
        text: str,
        size: float,
        color: tuple[int, int, int] = (0, 0, 0),
        background: tuple[int, int, int] = (255, 255, 255),
        padding: int = 4,
        antialias: bool = True,
    ) -> bytes:
        """Render single-line text to PNG bytes via software rasterization."""
        width, height, rgb_bytes = cls.render_rgb(
            font, text, size, color, background, padding, antialias
        )
        # Re-wrap in a Rasterizer to easily use to_png
        out = Rasterizer(width, height, background)
        out._buf = bytearray(rgb_bytes)
        return out.to_png()

    @classmethod
    def render_svg(
        cls,
        font: Font,
        text: str,
        size: float,
        color: tuple[int, int, int] = (0, 0, 0),
        background: tuple[int, int, int] = (255, 255, 255),
        padding: int = 4,
    ) -> bytes:
        """Render single-line text to SVG bytes using vector outlines."""
        layout = cls.layout(font, text, size=size, kern=True)
        ascender = layout.ascender
        descender = layout.descender

        canvas_w = max(1, int(math.ceil(layout.total_width + 2 * padding)))
        canvas_h = max(1, int(math.ceil((ascender - descender) + 2 * padding)))
        transform = f"translate({padding:g} {ascender + padding:g}) scale(1 -1)"

        path_elements: list[str] = []
        for glyph_layout in layout.glyphs:
            if glyph_layout.path is None or len(glyph_layout.path) == 0:
                continue
            path_data = _path_to_svg_d(glyph_layout.path)
            if not path_data:
                continue
            path_elements.append(f'    <path d="{path_data}"/>')

        svg = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            (
                f'<svg xmlns="http://www.w3.org/2000/svg" width="{canvas_w}" '
                f'height="{canvas_h}" viewBox="0 0 {canvas_w} {canvas_h}" role="img">'
            ),
            f'  <title>{html.escape(text)}</title>',
            (
                f'  <rect width="{canvas_w}" height="{canvas_h}" '
                f'fill="{_svg_color(background)}"/>'
            ),
        ]
        if path_elements:
            svg.append(f'  <g fill="{_svg_color(color)}" transform="{transform}">')
            svg.extend(path_elements)
            svg.append("  </g>")
        return "\n".join(svg + ["</svg>"]).encode("utf-8")


def _downsample_4x(src: Rasterizer, dst: Rasterizer) -> None:
    """Average 4x4 supersampled RGB blocks into the destination buffer."""
    for y in range(dst.height):
        for x in range(dst.width):
            r = 0
            g = 0
            b = 0
            base_y = y * 4
            base_x = x * 4
            for dy in range(4):
                row = (base_y + dy) * src.width
                for dx in range(4):
                    idx = (row + base_x + dx) * 3
                    r += src._buf[idx]
                    g += src._buf[idx + 1]
                    b += src._buf[idx + 2]
            dst._set_pixel(x, y, r // 16, g // 16, b // 16)


def _path_to_svg_d(path: GlyphPath) -> str:
    commands: list[str] = []
    for cmd in path:
        if isinstance(cmd, MoveTo):
            commands.append(f"M {_svg_number(cmd.x)} {_svg_number(cmd.y)}")
        elif isinstance(cmd, LineTo):
            commands.append(f"L {_svg_number(cmd.x)} {_svg_number(cmd.y)}")
        elif isinstance(cmd, QuadraticTo):
            commands.append(
                "Q "
                f"{_svg_number(cmd.x1)} {_svg_number(cmd.y1)} "
                f"{_svg_number(cmd.x)} {_svg_number(cmd.y)}"
            )
        elif isinstance(cmd, CurveTo):
            commands.append(
                "C "
                f"{_svg_number(cmd.x1)} {_svg_number(cmd.y1)} "
                f"{_svg_number(cmd.x2)} {_svg_number(cmd.y2)} "
                f"{_svg_number(cmd.x)} {_svg_number(cmd.y)}"
            )
        elif isinstance(cmd, ClosePath):
            commands.append("Z")
    return " ".join(commands)


def _svg_number(value: float) -> str:
    if float(value).is_integer():
        return str(int(value))
    return f"{value:.4f}".rstrip("0").rstrip(".")


def _svg_color(color: tuple[int, int, int]) -> str:
    return f"rgb({color[0]},{color[1]},{color[2]})"


def get_math_variants(
    font: Font,
    glyph_id: int,
    target_size: float,
    direction: str = "vertical",
) -> list[tuple[GlyphId, float]]:
    """Select math glyph variants or assembly parts for a target size.

    Args:
        font: Font instance (expected to be TtfFont with MATH table)
        glyph_id: Source glyph ID (e.g., open parenthesis U+0028)
        target_size: Target glyph advance measurement in font units
        direction: "vertical" or "horizontal" for variant selection

    Returns:
        List of (GlyphId, advance_measurement) tuples representing:
        - Single variant glyphs (if a single glyph meets or exceeds target_size)
        - Component assembly instructions (top, middle, bottom parts) for stretchy glyphs
    """
    if not hasattr(font, "ttf_tables"):
        return [(GlyphId(glyph_id), 0.0)]

    math_table = getattr(font.ttf_tables, "math", None)
    if math_table is None:
        return [(GlyphId(glyph_id), 0.0)]

    variants = math_table.get_glyph_variants(glyph_id, direction)

    if not variants:
        return [(GlyphId(glyph_id), 0.0)]

    target_size_int = int(target_size)

    for variant in variants:
        if variant.advance_measurement >= target_size_int:
            return [(GlyphId(variant.variant_glyph), float(variant.advance_measurement))]

    assembly = math_table.get_glyph_assembly(glyph_id, direction)
    if assembly is not None:
        result = []
        for part in assembly.parts:
            advance = (
                part.full_advance_height
                if direction == "vertical"
                else part.full_advance_width
            )
            result.append((GlyphId(part.glyph_id), float(advance)))
        return result

    if variants:
        largest = variants[-1]
        return [(GlyphId(largest.variant_glyph), float(largest.advance_measurement))]

    return [(GlyphId(glyph_id), 0.0)]
