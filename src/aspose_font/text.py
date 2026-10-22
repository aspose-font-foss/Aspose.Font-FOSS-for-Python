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
    LineTo,
    MoveTo,
    PathCommand,
    QuadraticTo,
)
from aspose_font.rasterizer import Rasterizer


@dataclass
class GlyphLayout:
    """A single glyph positioned in world-space layout coordinates."""
    char: str          # source character (empty string for layout_glyphs)
    glyph_id: GlyphId
    x_offset: float    # left edge in scaled world coordinates
    y_offset: float    # baseline offset (always 0 for horizontal layout)
    advance_width: float  # scaled advance width
    path: GlyphPath | None  # pre-scaled, pre-translated outline


@dataclass
class TextLayout:
    """Result of a TextRenderer.layout() call."""
    glyphs: list[GlyphLayout] = field(default_factory=list)
    total_width: float = 0.0
    ascender: float = 0.0
    descender: float = 0.0


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
    ) -> TextLayout:
        """Resolve text to GlyphIds then call layout_glyphs."""
        glyph_ids: list[GlyphId] = []
        chars: list[str] = []
        for ch in text:
            try:
                gid = font.encoding.unicode_to_gid(ord(ch))
            except Exception:
                gid = GlyphId(0)
            glyph_ids.append(gid)
            chars.append(ch)
        return cls._layout_core(font, glyph_ids, chars, size, kern)

    @classmethod
    def layout_glyphs(
        cls,
        font: Font,
        glyph_ids: list[GlyphId],
        size: float = 1.0,
        kern: bool = True,
    ) -> TextLayout:
        """Lay out pre-resolved glyph IDs."""
        chars = [""] * len(glyph_ids)
        return cls._layout_core(font, glyph_ids, chars, size, kern)

    @classmethod
    def _layout_core(
        cls,
        font: Font,
        glyph_ids: list[GlyphId],
        chars: list[str],
        size: float,
        kern: bool,
    ) -> TextLayout:
        m = font.metrics
        scale = size / m.units_per_em

        kern_lookup: dict[tuple[int, int], int] = {}
        if kern:
            kern_lookup = {
                (int(p.left), int(p.right)): p.value
                for p in font.get_kern_pairs()
            }

        result = TextLayout(
            ascender=m.ascender * scale,
            descender=m.descender * scale,
        )

        pen_x = 0.0
        prev_gid: GlyphId | None = None

        for gid, ch in zip(glyph_ids, chars):
            # Apply kern between previous and current glyph
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
                )
            )

            pen_x += adv
            prev_gid = gid

        result.total_width = pen_x
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
