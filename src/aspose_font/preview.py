"""High-level preview image generation helpers."""

from __future__ import annotations

import struct
import zlib
from dataclasses import dataclass
from pathlib import Path

from aspose_font._exceptions import FontNotSupportedException
from aspose_font._font_base import Font
from aspose_font._types import (
    ClosePath,
    CurveTo,
    GlyphId,
    GlyphPath,
    LineTo,
    MoveTo,
    QuadraticTo,
)
from aspose_font.rasterizer import Rasterizer
from aspose_font.text import TextRenderer
from aspose_font.ttf.font import TtfFont
from aspose_font.ttf.tables.colr import (
    PaintColrLayers,
    PaintGlyph,
    PaintLinearGradient,
    PaintRadialGradient,
    PaintRotate,
    PaintScale,
    PaintSkew,
    PaintSolid,
    PaintTransform,
    PaintTranslate,
)


class WebFontBundle:
    pass

_DEFAULT_PREVIEW_TEXT = "Hamburgefons 0123456789"
_BOARD_SURFACE = (248, 242, 232)
_BOARD_PANEL = (255, 250, 244)
_BOARD_BORDER = (203, 183, 156)
_BOARD_RULE = (226, 211, 189)
_BOARD_SHADOW = (238, 226, 209)
_BOARD_LABEL = (68, 60, 50)


@dataclass(slots=True, frozen=True)
class PreviewImage:
    filename: str
    media_type: str
    data: bytes

    def write_to(self, path: str | Path) -> Path:
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(self.data)
        return output_path


class FontPreviewBuilder:
    _SUPPORTED_OUTPUT_FORMATS = {"png", "svg"}

    @classmethod
    def build(
        cls,
        font: Font,
        *,
        text: str = _DEFAULT_PREVIEW_TEXT,
        size: float = 72.0,
        color: tuple[int, int, int] = (17, 17, 17),
        background: tuple[int, int, int] = (255, 253, 248),
        padding: int = 12,
        antialias: bool = True,
        file_stem: str | None = None,
        instance_coordinates: dict[str, float] | None = None,
        instance_name: str | None = None,
        output_format: str = "png",
    ) -> PreviewImage:
        prepared = cls._prepare_font(
            font,
            instance_coordinates=instance_coordinates,
            instance_name=instance_name,
        )
        stem = file_stem or cls._default_stem(prepared, text)
        normalized_format = cls._normalize_output_format(output_format)
        if normalized_format == "png":
            data = TextRenderer.render_png(
                prepared,
                text,
                size=size,
                color=color,
                background=background,
                padding=padding,
                antialias=antialias,
            )
            media_type = "image/png"
        else:
            data = TextRenderer.render_svg(
                prepared,
                text,
                size=size,
                color=color,
                background=background,
                padding=padding,
            )
            media_type = "image/svg+xml"
        return PreviewImage(
            filename=f"{stem}.{normalized_format}",
            media_type=media_type,
            data=data,
        )

    @staticmethod
    def compose_sheet(
        previews: list[PreviewImage],
        *,
        columns: int,
        gap: int = 16,
        background: tuple[int, int, int] = (255, 253, 248),
        title: str | None = None,
        column_headers: list[str] | None = None,
        row_headers: list[str] | None = None,
        labels: list[str] | None = None,
        footer_lines: list[str] | None = None,
        label_color: tuple[int, int, int] = _BOARD_LABEL,
        file_stem: str = "preview-sheet",
    ) -> PreviewImage:
        if not previews:
            raise ValueError("Preview sheet requires at least one preview")
        if columns < 1:
            raise ValueError("Preview sheet requires columns >= 1")
        if labels is not None and len(labels) != len(previews):
            raise ValueError("Preview sheet labels must match preview count")

        decoded = [_decode_png_rgb(preview.data) for preview in previews]
        max_width = max(width for width, _height, _pixels in decoded)
        max_height = max(height for _width, height, _pixels in decoded)
        label_height = _sheet_label_height(labels) if labels else 0
        rows = (len(decoded) + columns - 1) // columns
        if column_headers is not None and len(column_headers) != columns:
            raise ValueError("Preview sheet column headers must match column count")
        if row_headers is not None and len(row_headers) != rows:
            raise ValueError("Preview sheet row headers must match row count")

        title_height = _text_block_height([title], max_chars=40) if title else 0
        column_header_height = (
            _text_block_height(column_headers, max_chars=18) if column_headers else 0
        )
        row_header_width = (
            _text_block_width(row_headers, max_chars=18) + 8 if row_headers else 0
        )
        footer_height = (
            _text_block_height(footer_lines, max_chars=48) + 12 if footer_lines else 0
        )
        cell_total_height = max_height + label_height
        content_left = gap + row_header_width
        content_top = gap + title_height + column_header_height
        canvas_width = row_header_width + max_width * columns + gap * (columns + 1)
        canvas_height = (
            title_height
            + column_header_height
            + cell_total_height * rows
            + footer_height
            + gap * (rows + 2)
        )
        r, g, b = background
        pixels = bytearray([r, g, b] * canvas_width * canvas_height)
        _fill_rect(
            pixels,
            canvas_width,
            gap // 2,
            gap // 2,
            canvas_width - gap,
            canvas_height - gap,
            _BOARD_SURFACE,
        )
        _draw_rect_outline(
            pixels,
            canvas_width,
            gap // 2,
            gap // 2,
            canvas_width - gap,
            canvas_height - gap,
            color=_BOARD_BORDER,
        )

        if title:
            _fill_rect(
                pixels,
                canvas_width,
                gap,
                gap,
                canvas_width - gap * 2,
                title_height,
                _BOARD_PANEL,
            )
            _draw_rect_outline(
                pixels,
                canvas_width,
                gap,
                gap,
                canvas_width - gap * 2,
                title_height,
                color=_BOARD_BORDER,
            )
            _draw_centered_text_block(
                pixels,
                canvas_width,
                gap,
                gap,
                canvas_width - gap * 2,
                title_height,
                title,
                color=label_color,
                max_chars=40,
            )
            _draw_horizontal_rule(
                pixels,
                canvas_width,
                gap + 8,
                canvas_width - gap - 8,
                gap + title_height + max(4, gap // 2),
                color=_BOARD_RULE,
            )
        if column_headers:
            for col, header in enumerate(column_headers):
                left = content_left + gap + col * (max_width + gap)
                _fill_rect(
                    pixels,
                    canvas_width,
                    left,
                    gap + title_height,
                    max_width,
                    column_header_height,
                    _BOARD_PANEL,
                )
                _draw_rect_outline(
                    pixels,
                    canvas_width,
                    left,
                    gap + title_height,
                    max_width,
                    column_header_height,
                    color=_BOARD_BORDER,
                )
                _draw_centered_text_block(
                    pixels,
                    canvas_width,
                    left,
                    gap + title_height,
                    max_width,
                    column_header_height,
                    header,
                    color=label_color,
                    max_chars=18,
                )
        if row_headers:
            for row, header in enumerate(row_headers):
                top = content_top + gap + row * (cell_total_height + gap)
                _fill_rect(
                    pixels,
                    canvas_width,
                    gap,
                    top,
                    row_header_width,
                    cell_total_height,
                    _BOARD_PANEL,
                )
                _draw_rect_outline(
                    pixels,
                    canvas_width,
                    gap,
                    top,
                    row_header_width,
                    cell_total_height,
                    color=_BOARD_BORDER,
                )
                _draw_centered_text_block(
                    pixels,
                    canvas_width,
                    gap,
                    top,
                    row_header_width,
                    cell_total_height,
                    header,
                    color=label_color,
                    max_chars=18,
                )

        for index, (width, height, src_pixels) in enumerate(decoded):
            row = index // columns
            col = index % columns
            left = content_left + gap + col * (max_width + gap)
            top = content_top + gap + row * (cell_total_height + gap)
            _fill_rect(
                pixels,
                canvas_width,
                left + 2,
                top + 2,
                max_width,
                cell_total_height,
                _BOARD_SHADOW,
            )
            _fill_rect(
                pixels,
                canvas_width,
                left,
                top,
                max_width,
                cell_total_height,
                _BOARD_PANEL,
            )
            _draw_rect_outline(
                pixels,
                canvas_width,
                left,
                top,
                max_width,
                cell_total_height,
                color=_BOARD_BORDER,
            )
            if labels:
                _draw_sheet_label(
                    pixels,
                    canvas_width,
                    left,
                    top,
                    max_width,
                    label_height,
                    labels[index],
                    color=label_color,
                )
            image_top = top + label_height
            for y in range(height):
                src_start = y * width * 3
                dst_start = ((image_top + y) * canvas_width + left) * 3
                pixels[dst_start:dst_start + width * 3] = src_pixels[src_start:src_start + width * 3]
            if label_height:
                _draw_horizontal_rule(
                    pixels,
                    canvas_width,
                    left + 8,
                    left + max_width - 8,
                    image_top - 3,
                    color=_BOARD_RULE,
                )
        if footer_lines:
            footer_top = content_top + gap + rows * (cell_total_height + gap)
            footer_left = gap
            footer_width = canvas_width - gap * 2
            _fill_rect(
                pixels,
                canvas_width,
                footer_left,
                footer_top,
                footer_width,
                footer_height,
                _BOARD_PANEL,
            )
            _draw_rect_outline(
                pixels,
                canvas_width,
                footer_left,
                footer_top,
                footer_width,
                footer_height,
                color=_BOARD_BORDER,
            )
            _draw_text_block(
                pixels,
                canvas_width,
                footer_left + 10,
                footer_top + 8,
                footer_width - 20,
                footer_height - 16,
                footer_lines,
                color=label_color,
                max_chars=48,
            )

        return PreviewImage(
            filename=f"{file_stem}.png",
            media_type="image/png",
            data=_encode_png_rgb(canvas_width, canvas_height, bytes(pixels)),
        )

    @staticmethod
    def compose_difference_preview(
        before: PreviewImage,
        after: PreviewImage,
        *,
        file_stem: str = "preview-diff",
        background: tuple[int, int, int] = (255, 253, 248),
        before_color: tuple[int, int, int] = (198, 109, 42),
        after_color: tuple[int, int, int] = (71, 126, 199),
        overlap_color: tuple[int, int, int] = (126, 94, 156),
        threshold: int = 8,
    ) -> PreviewImage:
        canvas_width, canvas_height, before_pixels, after_pixels = _normalized_preview_pair(
            before.data,
            after.data,
            background=background,
        )

        diff_pixels = bytearray(canvas_width * canvas_height * 3)
        background_luma = _rgb_luma(background)
        for index in range(0, len(diff_pixels), 3):
            before_rgb = (
                before_pixels[index],
                before_pixels[index + 1],
                before_pixels[index + 2],
            )
            after_rgb = (
                after_pixels[index],
                after_pixels[index + 1],
                after_pixels[index + 2],
            )
            before_ink = max(0, background_luma - _rgb_luma(before_rgb))
            after_ink = max(0, background_luma - _rgb_luma(after_rgb))
            if before_ink <= threshold and after_ink <= threshold:
                color = background
            elif abs(before_ink - after_ink) <= threshold and before_ink > threshold:
                color = overlap_color
            elif before_ink > after_ink:
                color = before_color
            else:
                color = after_color
            diff_pixels[index:index + 3] = bytes(color)

        return PreviewImage(
            filename=f"{file_stem}.png",
            media_type="image/png",
            data=_encode_png_rgb(canvas_width, canvas_height, bytes(diff_pixels)),
        )

    @staticmethod
    def compose_overlay_preview(
        before: PreviewImage,
        after: PreviewImage,
        *,
        file_stem: str = "preview-overlay",
        background: tuple[int, int, int] = (255, 253, 248),
        before_color: tuple[int, int, int] = (198, 109, 42),
        after_color: tuple[int, int, int] = (71, 126, 199),
        overlap_color: tuple[int, int, int] = (126, 94, 156),
        threshold: int = 8,
    ) -> PreviewImage:
        canvas_width, canvas_height, before_pixels, after_pixels = _normalized_preview_pair(
            before.data,
            after.data,
            background=background,
        )

        overlay_pixels = bytearray(canvas_width * canvas_height * 3)
        background_luma = _rgb_luma(background)
        for index in range(0, len(overlay_pixels), 3):
            before_rgb = (
                before_pixels[index],
                before_pixels[index + 1],
                before_pixels[index + 2],
            )
            after_rgb = (
                after_pixels[index],
                after_pixels[index + 1],
                after_pixels[index + 2],
            )
            before_ink = max(0, background_luma - _rgb_luma(before_rgb))
            after_ink = max(0, background_luma - _rgb_luma(after_rgb))
            before_active = before_ink > threshold
            after_active = after_ink > threshold
            if before_active and after_active:
                color = overlap_color
            elif before_active:
                color = before_color
            elif after_active:
                color = after_color
            else:
                color = background
            overlay_pixels[index:index + 3] = bytes(color)

        return PreviewImage(
            filename=f"{file_stem}.png",
            media_type="image/png",
            data=_encode_png_rgb(canvas_width, canvas_height, bytes(overlay_pixels)),
        )

    @classmethod
    def render_color_glyph(
        cls,
        font: Font,
        glyph_id: int | GlyphId,
        *,
        size: float = 72.0,
        palette_index: int = 0,
        background: tuple[int, int, int] = (255, 255, 255),
        padding: int = 12,
        antialias: bool = True,
    ) -> PreviewImage:
        if not isinstance(font, TtfFont):
            raise FontNotSupportedException("render_color_glyph requires a TTF font")

        if not font.ttf_tables.colr or not font.ttf_tables.cpal:
            return cls._render_color_glyph_fallback(
                font,
                glyph_id,
                size=size,
                background=background,
                padding=padding,
                antialias=antialias,
            )

        if font.ttf_tables.colr.version != 1:
            return cls._render_color_glyph_fallback(
                font,
                glyph_id,
                size=size,
                background=background,
                padding=padding,
                antialias=antialias,
            )

        gid = int(glyph_id)
        width, height, rgb_bytes = _render_color_glyph_to_rgb(
            font,
            gid,
            size=size,
            palette_index=palette_index,
            background=background,
            padding=padding,
            antialias=antialias,
        )

        png_data = _encode_png_rgb(width, height, rgb_bytes)

        return PreviewImage(
            filename=f"color-glyph-{gid}.png",
            media_type="image/png",
            data=png_data,
        )

    @staticmethod
    def _render_color_glyph_fallback(
        font: Font,
        glyph_id: int | GlyphId,
        *,
        size: float = 72.0,
        background: tuple[int, int, int] = (255, 255, 255),
        padding: int = 12,
        antialias: bool = True,
    ) -> PreviewImage:
        gid = int(glyph_id)

        text = "H"

        png_data = TextRenderer.render_png(
            font,
            text,
            size=size,
            color=(0, 0, 0),
            background=background,
            padding=padding,
            antialias=antialias,
        )

        return PreviewImage(
            filename=f"color-glyph-{gid}.png",
            media_type="image/png",
            data=png_data,
        )

    @classmethod
    def render_svg_glyph_to_png(
        cls,
        font: Font,
        glyph_id: int | GlyphId,
        *,
        size: int = 256,
        background: tuple[int, int, int] = (255, 255, 255),
    ) -> PreviewImage:
        if not isinstance(font, TtfFont):
            raise FontNotSupportedException("render_svg_glyph_to_png requires a TTF font")

        svg_table = font.ttf_tables.svg
        if svg_table is None:
            return cls._render_svg_glyph_fallback(
                font,
                glyph_id,
                size=size,
                background=background,
            )

        gid = int(glyph_id)
        svg_content = svg_table.get_svg(gid)
        if svg_content is None:
            return cls._render_svg_glyph_fallback(
                font,
                glyph_id,
                size=size,
                background=background,
            )

        try:
            path = _parse_svg_to_path(svg_content)
        except Exception:
            return cls._render_svg_glyph_fallback(
                font,
                glyph_id,
                size=size,
                background=background,
            )

        if path is None or len(path) == 0:
            return cls._render_svg_glyph_fallback(
                font,
                glyph_id,
                size=size,
                background=background,
            )

        width, height, rgb_bytes = _render_path_to_rgb(
            font,
            path,
            size=size,
            background=background,
            padding=0,
        )

        png_data = _encode_png_rgb(width, height, rgb_bytes)

        return PreviewImage(
            filename=f"svg-glyph-{gid}.png",
            media_type="image/png",
            data=png_data,
        )

    @staticmethod
    def _render_svg_glyph_fallback(
        font: Font,
        glyph_id: int | GlyphId,
        *,
        size: float = 72.0,
        background: tuple[int, int, int] = (255, 255, 255),
    ) -> PreviewImage:
        gid = int(glyph_id)

        text = "H"

        png_data = TextRenderer.render_png(
            font,
            text,
            size=size,
            color=(0, 0, 0),
            background=background,
            padding=12,
            antialias=True,
        )

        return PreviewImage(
            filename=f"svg-glyph-{gid}.png",
            media_type="image/png",
            data=png_data,
        )

    @staticmethod
    def _prepare_font(
        font: Font,
        *,
        instance_coordinates: dict[str, float] | None,
        instance_name: str | None,
    ) -> Font:
        if instance_coordinates is None and instance_name is None:
            return font
        if not isinstance(font, TtfFont) or not font.is_variable:
            raise FontNotSupportedException(
                "preview instance selection is only supported for variable TTF fonts"
            )
        return font.smart_instancer.instantiate(
            instance_coordinates,
            instance_name=instance_name,
        )

    @staticmethod
    def _default_stem(font: Font, text: str) -> str:
        del text
        family = (font.font_family or font.font_name or "preview").strip()
        style = (font.font_style or "").strip()
        return _slugify_filename(" ".join(part for part in (family, style) if part))

    @classmethod
    def _normalize_output_format(cls, output_format: str) -> str:
        normalized = output_format.lower().strip()
        if normalized not in cls._SUPPORTED_OUTPUT_FORMATS:
            supported = ", ".join(sorted(cls._SUPPORTED_OUTPUT_FORMATS))
            raise ValueError(f"Unsupported preview output format: {output_format!r}. Supported: {supported}")
        return normalized


def _parse_svg_to_path(svg_content: str) -> GlyphPath | None:
    import re

    path = GlyphPath()

    match = re.search(r'<path\s+[^>]*d=["\']([^"\']*)["\']', svg_content, re.IGNORECASE)
    if match is None:
        return None

    d = match.group(1).strip()

    commands = re.findall(r'[MmLlQqCcZzHhVv][^MmLlQqCcZzHhVv]*', d)

    if not commands:
        return None

    current_x, current_y = 0.0, 0.0

    for cmd_str in commands:
        cmd_str = cmd_str.strip()
        if not cmd_str:
            continue

        cmd_char = cmd_str[0].upper()
        rest = cmd_str[1:].strip()

        values = re.findall(r'[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?', rest)

        if not values:
            continue

        nums = [float(v) for v in values]
        idx = 0

        if cmd_char == 'M':
            while idx < len(nums):
                x, y = nums[idx], nums[idx + 1]
                path.append(MoveTo(x=x, y=y))
                current_x, current_y = x, y
                idx += 2

        elif cmd_char == 'L':
            while idx < len(nums):
                x, y = nums[idx], nums[idx + 1]
                path.append(LineTo(x=x, y=y))
                current_x, current_y = x, y
                idx += 2

        elif cmd_char == 'H':
            while idx < len(nums):
                x = nums[idx]
                path.append(LineTo(x=x, y=current_y))
                current_x = x
                idx += 1

        elif cmd_char == 'V':
            while idx < len(nums):
                y = nums[idx]
                path.append(LineTo(x=current_x, y=y))
                current_y = y
                idx += 1

        elif cmd_char == 'Q':
            while idx < len(nums):
                x1, y1 = nums[idx], nums[idx + 1]
                x, y = nums[idx + 2], nums[idx + 3]
                path.append(QuadraticTo(x=x, y=y, x1=x1, y1=y1))
                current_x, current_y = x, y
                idx += 4

        elif cmd_char == 'C':
            while idx < len(nums):
                x1, y1 = nums[idx], nums[idx + 1]
                x2, y2 = nums[idx + 2], nums[idx + 3]
                x, y = nums[idx + 4], nums[idx + 5]
                path.append(CurveTo(x=x, y=y, x1=x1, y1=y1, x2=x2, y2=y2))
                current_x, current_y = x, y
                idx += 6

        elif cmd_char == 'Z' or cmd_char == 'S':
            path.append(ClosePath())
            current_x, current_y = 0.0, 0.0

        elif cmd_char == 'm':
            while idx < len(nums):
                dx, dy = nums[idx], nums[idx + 1]
                x, y = current_x + dx, current_y + dy
                path.append(MoveTo(x=x, y=y))
                current_x, current_y = x, y
                idx += 2

        elif cmd_char == 'l':
            while idx < len(nums):
                dx, dy = nums[idx], nums[idx + 1]
                x, y = current_x + dx, current_y + dy
                path.append(LineTo(x=x, y=y))
                current_x, current_y = x, y
                idx += 2

        elif cmd_char == 'h':
            while idx < len(nums):
                dx = nums[idx]
                x = current_x + dx
                path.append(LineTo(x=x, y=current_y))
                current_x = x
                idx += 1

        elif cmd_char == 'v':
            while idx < len(nums):
                dy = nums[idx]
                y = current_y + dy
                path.append(LineTo(x=current_x, y=y))
                current_y = y
                idx += 1

        elif cmd_char == 'q':
            while idx < len(nums):
                dx1, dy1 = nums[idx], nums[idx + 1]
                dx, dy = nums[idx + 2], nums[idx + 3]
                x1, y1 = current_x + dx1, current_y + dy1
                x, y = current_x + dx, current_y + dy
                path.append(QuadraticTo(x=x, y=y, x1=x1, y1=y1))
                current_x, current_y = x, y
                idx += 4

        elif cmd_char == 'c':
            while idx < len(nums):
                dx1, dy1 = nums[idx], nums[idx + 1]
                dx2, dy2 = nums[idx + 2], nums[idx + 3]
                dx, dy = nums[idx + 4], nums[idx + 5]
                x1, y1 = current_x + dx1, current_y + dy1
                x2, y2 = current_x + dx2, current_y + dy2
                x, y = current_x + dx, current_y + dy
                path.append(CurveTo(x=x, y=y, x1=x1, y1=y1, x2=x2, y2=y2))
                current_x, current_y = x, y
                idx += 6

    return path


def _render_path_to_rgb(
    font: TtfFont,
    path: GlyphPath,
    *,
    size: int = 256,
    background: tuple[int, int, int] = (255, 255, 255),
    padding: int = 0,
) -> tuple[int, int, bytes]:
    bounds = _path_bounds(path)
    if bounds is None:
        bounds = (0, 0, size, size)

    min_x, min_y, max_x, max_y = bounds

    glyph_width = max_x - min_x
    glyph_height = max_y - min_y

    canvas_width = max(1, int(glyph_width) + padding * 2)
    canvas_height = max(1, int(glyph_height) + padding * 2)

    scale_factor = 4
    sf = float(scale_factor)

    raster = Rasterizer(canvas_width * scale_factor, canvas_height * scale_factor, background)

    transform = (
        sf,
        0.0,
        0.0,
        -sf,
        sf * (padding - min_x),
        sf * (canvas_height - padding - max_y),
    )

    raster.draw_path(path, color=(0, 0, 0), transform=transform)

    out = Rasterizer(canvas_width, canvas_height, background)
    for y in range(out.height):
        for x in range(out.width):
            r = 0
            g = 0
            b = 0
            base_y = y * 4
            base_x = x * 4
            for dy in range(4):
                for dx in range(4):
                    px = (base_y + dy) * raster.width + (base_x + dx)
                    idx = px * 3
                    r += raster._buf[idx]
                    g += raster._buf[idx + 1]
                    b += raster._buf[idx + 2]
            r //= 16
            g //= 16
            b //= 16
            dst_idx = (y * out.width + x) * 3
            out._buf[dst_idx] = r
            out._buf[dst_idx + 1] = g
            out._buf[dst_idx + 2] = b

    return canvas_width, canvas_height, bytes(out._buf)


def _slugify_filename(value: str) -> str:
    chars: list[str] = []
    previous_dash = False
    for ch in value.lower():
        if ch.isalnum():
            chars.append(ch)
            previous_dash = False
        else:
            if not previous_dash:
                chars.append("-")
                previous_dash = True
    slug = "".join(chars).strip("-")
    return slug or "preview"


def _decode_png_rgb(data: bytes) -> tuple[int, int, bytes]:
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError("Preview sheet composition requires PNG inputs")

    pos = 8
    width = 0
    height = 0
    idat_parts: list[bytes] = []
    while pos + 8 <= len(data):
        length = struct.unpack_from(">I", data, pos)[0]
        ctype = data[pos + 4:pos + 8]
        chunk_data = data[pos + 8:pos + 8 + length]
        pos += 12 + length
        if ctype == b"IHDR":
            width, height = struct.unpack_from(">II", chunk_data, 0)
        elif ctype == b"IDAT":
            idat_parts.append(chunk_data)
        elif ctype == b"IEND":
            break

    raw = zlib.decompress(b"".join(idat_parts))
    stride = width * 3
    pixels = bytearray(width * height * 3)
    rp = 0
    wp = 0
    for _ in range(height):
        filter_type = raw[rp]
        rp += 1
        if filter_type != 0:
            raise ValueError(f"Unsupported PNG filter: {filter_type}")
        pixels[wp:wp + stride] = raw[rp:rp + stride]
        rp += stride
        wp += stride
    return width, height, bytes(pixels)


def _encode_png_rgb(width: int, height: int, pixels: bytes) -> bytes:
    png_sig = b"\x89PNG\r\n\x1a\n"

    def _chunk(tag: bytes, payload: bytes) -> bytes:
        c = tag + payload
        return (
            struct.pack(">I", len(payload))
            + c
            + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)
        )

    ihdr = _chunk(
        b"IHDR",
        struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0),
    )
    raw = bytearray()
    stride = width * 3
    for y in range(height):
        raw.append(0)
        start = y * stride
        raw.extend(pixels[start:start + stride])
    idat = _chunk(b"IDAT", zlib.compress(bytes(raw), 6))
    iend = _chunk(b"IEND", b"")
    return png_sig + ihdr + idat + iend


def _normalized_preview_pair(
    before_data: bytes,
    after_data: bytes,
    *,
    background: tuple[int, int, int],
) -> tuple[int, int, bytes, bytes]:
    before_width, before_height, before_pixels = _decode_png_rgb(before_data)
    after_width, after_height, after_pixels = _decode_png_rgb(after_data)
    canvas_width = max(before_width, after_width)
    canvas_height = max(before_height, after_height)
    if before_width == after_width and before_height == after_height:
        return canvas_width, canvas_height, before_pixels, after_pixels
    return (
        canvas_width,
        canvas_height,
        _expand_rgb_canvas(before_pixels, before_width, before_height, canvas_width, canvas_height, background),
        _expand_rgb_canvas(after_pixels, after_width, after_height, canvas_width, canvas_height, background),
    )


def _expand_rgb_canvas(
    pixels: bytes,
    width: int,
    height: int,
    canvas_width: int,
    canvas_height: int,
    background: tuple[int, int, int],
) -> bytes:
    if width == canvas_width and height == canvas_height:
        return pixels
    expanded = bytearray(bytes(background) * canvas_width * canvas_height)
    row_len = width * 3
    canvas_row_len = canvas_width * 3
    for y in range(height):
        source_start = y * row_len
        target_start = y * canvas_row_len
        expanded[target_start:target_start + row_len] = pixels[source_start:source_start + row_len]
    return bytes(expanded)


def _rgb_luma(color: tuple[int, int, int]) -> int:
    return int(round(color[0] * 0.299 + color[1] * 0.587 + color[2] * 0.114))


def _sheet_label_height(labels: list[str]) -> int:
    return _text_block_height(labels, max_chars=22)


def _fill_rect(
    pixels: bytearray,
    canvas_width: int,
    left: int,
    top: int,
    width: int,
    height: int,
    color: tuple[int, int, int],
) -> None:
    if width <= 0 or height <= 0:
        return
    fill = bytes(color) * width
    for y in range(max(0, top), top + height):
        if y < 0:
            continue
        start_x = max(0, left)
        end_x = min(canvas_width, left + width)
        if end_x <= start_x:
            continue
        idx = (y * canvas_width + start_x) * 3
        row_fill = fill[(start_x - left) * 3:(end_x - left) * 3]
        pixels[idx:idx + len(row_fill)] = row_fill


def _draw_rect_outline(
    pixels: bytearray,
    canvas_width: int,
    left: int,
    top: int,
    width: int,
    height: int,
    *,
    color: tuple[int, int, int],
) -> None:
    if width <= 1 or height <= 1:
        return
    _draw_horizontal_rule(pixels, canvas_width, left, left + width, top, color=color)
    _draw_horizontal_rule(
        pixels,
        canvas_width,
        left,
        left + width,
        top + height - 1,
        color=color,
    )
    _draw_vertical_rule(pixels, canvas_width, left, top, top + height, color=color)
    _draw_vertical_rule(
        pixels,
        canvas_width,
        left + width - 1,
        top,
        top + height,
        color=color,
    )


def _draw_horizontal_rule(
    pixels: bytearray,
    canvas_width: int,
    left: int,
    right: int,
    y: int,
    *,
    color: tuple[int, int, int],
) -> None:
    if y < 0 or canvas_width <= 0:
        return
    start_x = max(0, left)
    end_x = min(canvas_width, right)
    if end_x <= start_x:
        return
    idx = (y * canvas_width + start_x) * 3
    pixels[idx:idx + (end_x - start_x) * 3] = bytes(color) * (end_x - start_x)


def _draw_vertical_rule(
    pixels: bytearray,
    canvas_width: int,
    x: int,
    top: int,
    bottom: int,
    *,
    color: tuple[int, int, int],
) -> None:
    if x < 0 or x >= canvas_width:
        return
    for y in range(max(0, top), bottom):
        idx = (y * canvas_width + x) * 3
        if 0 <= idx <= len(pixels) - 3:
            pixels[idx] = color[0]
            pixels[idx + 1] = color[1]
            pixels[idx + 2] = color[2]


def _text_block_height(labels: list[str | None], *, max_chars: int) -> int:
    max_lines = 1
    for label in labels:
        if label is None:
            continue
        max_lines = max(max_lines, len(_wrap_label(label, max_chars=max_chars)))
    return max_lines * 10 + 6


def _text_block_width(labels: list[str], *, max_chars: int) -> int:
    max_width = 0
    for label in labels:
        for line in _wrap_label(label, max_chars=max_chars):
            if line:
                max_width = max(max_width, len(line) * 6 - 1)
    return max_width


def _draw_sheet_label(
    pixels: bytearray,
    canvas_width: int,
    left: int,
    top: int,
    width: int,
    height: int,
    label: str,
    *,
    color: tuple[int, int, int],
) -> None:
    _draw_centered_text_block(
        pixels,
        canvas_width,
        left,
        top,
        width,
        height,
        label,
        color=color,
        max_chars=22,
    )


def _draw_centered_text_block(
    pixels: bytearray,
    canvas_width: int,
    left: int,
    top: int,
    width: int,
    height: int,
    label: str,
    *,
    color: tuple[int, int, int],
    max_chars: int,
) -> None:
    lines = _wrap_label(label, max_chars=max_chars)
    block_height = len(lines) * 10 - 3
    text_y = top + max(3, (height - block_height) // 2)
    for line in lines:
        text_width = len(line) * 6 - 1 if line else 0
        text_x = left + max(0, (width - text_width) // 2)
        _draw_bitmap_text(pixels, canvas_width, text_x, text_y, line, color=color)
        text_y += 10
        if text_y >= top + height:
            break


def _draw_text_block(
    pixels: bytearray,
    canvas_width: int,
    left: int,
    top: int,
    width: int,
    height: int,
    labels: list[str],
    *,
    color: tuple[int, int, int],
    max_chars: int,
) -> None:
    text_y = top
    for label in labels:
        for line in _wrap_label(label, max_chars=max_chars):
            _draw_bitmap_text(pixels, canvas_width, left, text_y, line, color=color)
            text_y += 10
            if text_y >= top + height:
                return


def _wrap_label(label: str, max_chars: int = 22) -> list[str]:
    normalized = " ".join(label.upper().split())
    if len(normalized) <= max_chars:
        return [normalized]
    words = normalized.split(" ")
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = word if not current else f"{current} {word}"
        if len(candidate) <= max_chars:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines or [normalized[:max_chars]]


def _draw_bitmap_text(
    pixels: bytearray,
    canvas_width: int,
    x: int,
    y: int,
    text: str,
    *,
    color: tuple[int, int, int],
) -> None:
    cursor_x = x
    for ch in text:
        glyph = _BITMAP_FONT.get(ch)
        if glyph is None:
            cursor_x += 6
            continue
        for row_index, row in enumerate(glyph):
            for col_index, bit in enumerate(row):
                if bit == "1":
                    px = cursor_x + col_index
                    py = y + row_index
                    idx = (py * canvas_width + px) * 3
                    if 0 <= idx <= len(pixels) - 3:
                        pixels[idx] = color[0]
                        pixels[idx + 1] = color[1]
                        pixels[idx + 2] = color[2]
        cursor_x += 6


_BITMAP_FONT = {
    " ": ["00000"] * 7,
    ".": ["00000", "00000", "00000", "00000", "00000", "01100", "01100"],
    "-": ["00000", "00000", "00000", "11111", "00000", "00000", "00000"],
    "=": ["00000", "11111", "00000", "11111", "00000", "00000", "00000"],
    ":": ["00000", "01100", "01100", "00000", "01100", "01100", "00000"],
    "0": ["01110", "10001", "10011", "10101", "11001", "10001", "01110"],
    "1": ["00100", "01100", "00100", "00100", "00100", "00100", "01110"],
    "2": ["01110", "10001", "00001", "00010", "00100", "01000", "11111"],
    "3": ["11110", "00001", "00001", "01110", "00001", "00001", "11110"],
    "4": ["00010", "00110", "01010", "10010", "11111", "00010", "00010"],
    "5": ["11111", "10000", "10000", "11110", "00001", "00001", "11110"],
    "6": ["01110", "10000", "10000", "11110", "10001", "10001", "01110"],
    "7": ["11111", "00001", "00010", "00100", "01000", "01000", "01000"],
    "8": ["01110", "10001", "10001", "01110", "10001", "10001", "01110"],
    "9": ["01110", "10001", "10001", "01111", "00001", "00001", "01110"],
    "A": ["01110", "10001", "10001", "11111", "10001", "10001", "10001"],
    "B": ["11110", "10001", "10001", "11110", "10001", "10001", "11110"],
    "C": ["01110", "10001", "10000", "10000", "10000", "10001", "01110"],
    "D": ["11100", "10010", "10001", "10001", "10001", "10010", "11100"],
    "E": ["11111", "10000", "10000", "11110", "10000", "10000", "11111"],
    "F": ["11111", "10000", "10000", "11110", "10000", "10000", "10000"],
    "G": ["01110", "10001", "10000", "10111", "10001", "10001", "01110"],
    "H": ["10001", "10001", "10001", "11111", "10001", "10001", "10001"],
    "I": ["01110", "00100", "00100", "00100", "00100", "00100", "01110"],
    "J": ["00001", "00001", "00001", "00001", "10001", "10001", "01110"],
    "K": ["10001", "10010", "10100", "11000", "10100", "10010", "10001"],
    "L": ["10000", "10000", "10000", "10000", "10000", "10000", "11111"],
    "M": ["10001", "11011", "10101", "10101", "10001", "10001", "10001"],
    "N": ["10001", "11001", "10101", "10011", "10001", "10001", "10001"],
    "O": ["01110", "10001", "10001", "10001", "10001", "10001", "01110"],
    "P": ["11110", "10001", "10001", "11110", "10000", "10000", "10000"],
    "Q": ["01110", "10001", "10001", "10001", "10101", "10010", "01101"],
    "R": ["11110", "10001", "10001", "11110", "10100", "10010", "10001"],
    "S": ["01111", "10000", "10000", "01110", "00001", "00001", "11110"],
    "T": ["11111", "00100", "00100", "00100", "00100", "00100", "00100"],
    "U": ["10001", "10001", "10001", "10001", "10001", "10001", "01110"],
    "V": ["10001", "10001", "10001", "10001", "10001", "01010", "00100"],
    "W": ["10001", "10001", "10001", "10101", "10101", "10101", "01010"],
    "X": ["10001", "10001", "01010", "00100", "01010", "10001", "10001"],
    "Y": ["10001", "10001", "01010", "00100", "00100", "00100", "00100"],
    "Z": ["11111", "00001", "00010", "00100", "01000", "10000", "11111"],
}


def generate_designspace_diff_overlay(
    font: Font,
    axis1: str,
    axis2: str,
    output_path: Path | None = None,
    *,
    size: float = 72.0,
    corner_colors: tuple[tuple[int, int, int], ...] = (
        (180, 50, 50),
        (50, 180, 50),
        (50, 50, 180),
        (180, 50, 180),
    ),
    overlap_color: tuple[int, int, int] = (100, 80, 140),
    background: tuple[int, int, int] = (255, 255, 255),
    padding: int = 12,
    cell_size: int = 300,
    legend_height: int = 60,
    antialias: bool = True,
) -> bytes | None:
    """Generate a PNG overlay visualizing four corner instances of a two-axis designspace.

    The function automatically determines the four corners of the designspace defined by
    axis1 and axis2, renders each corner with a distinct color, and combines them into
    a 2x2 grid with a legend showing axis value ranges.

    Args:
        font: The variable font to visualize.
        axis1: Name of the first axis (e.g., 'wght', 'wdth').
        axis2: Name of the second axis (e.g., 'wght', 'wdth').
        output_path: Path to write the output PNG file.
        size: Font size in points.
        corner_colors: RGB colors for the four corners (min/min, min/max, max/min, max/max).
        overlap_color: RGB color for overlapping ink areas (default: purple).
        background: RGB background color (default: white).
        padding: Padding in pixels around each cell.
        cell_size: Size of each corner cell in pixels.
        legend_height: Height of the legend area in pixels.
        antialias: Enable 4x supersampling antialiasing.

    Raises:
        FontNotSupportedException: If font is not a variable TTF font.
        ValueError: If axis1 or axis2 is not found in the font.
    """
    if not isinstance(font, TtfFont):
        raise FontNotSupportedException(
            "designspace diff overlay requires a TTF font"
        )
    if not font.is_variable:
        raise FontNotSupportedException(
            "designspace diff overlay requires a variable font"
        )

    axis1_lower = axis1.lower()
    axis2_lower = axis2.lower()

    axes = {axis.tag.lower(): axis for axis in font.variable_axes}
    if axis1_lower not in axes:
        raise ValueError(f"Font does not contain axis '{axis1}'. Available axes: {list(axes.keys())}")
    if axis2_lower not in axes:
        raise ValueError(f"Font does not contain axis '{axis2}'. Available axes: {list(axes.keys())}")

    axis1_obj = axes[axis1_lower]
    axis2_obj = axes[axis2_lower]

    min1, max1 = axis1_obj.min_value, axis1_obj.max_value
    min2, max2 = axis2_obj.min_value, axis2_obj.max_value

    corners = [
        (axis1_obj.normalize(min1), axis2_obj.normalize(min2)),
        (axis1_obj.normalize(min1), axis2_obj.normalize(max2)),
        (axis1_obj.normalize(max1), axis2_obj.normalize(min2)),
        (axis1_obj.normalize(max1), axis2_obj.normalize(max2)),
    ]

    instances = []
    normalized_values = []
    for norm1, norm2 in corners:
        coord = {axis1: axis1_obj.denormalize(norm1), axis2: axis2_obj.denormalize(norm2)}
        instance = font.smart_instancer.instantiate(coord)
        instances.append(instance)
        normalized_values.append((norm1, norm2))

    cell_total_size = cell_size + padding * 2
    canvas_width = cell_total_size * 2
    canvas_height = cell_total_size * 2 + legend_height

    canvas_pixels = bytearray(canvas_width * canvas_height * 3)

    # Fill canvas with background color
    bg_color = bytes(background)
    for y in range(canvas_height):
        start = y * canvas_width * 3
        end = start + canvas_width * 3
        canvas_pixels[start:end] = bg_color * canvas_width

    for idx, (instance, (norm1, norm2)) in enumerate(zip(instances, normalized_values)):
        col = idx % 2
        row = idx // 2

        left = col * cell_total_size + padding
        top = row * cell_total_size + padding

        _, _, instance_pixels = TextRenderer.render_rgb(
            instance,
            "Hamburgefons",
            size=size,
            color=(0, 0, 0),
            background=background,
            padding=0,
            antialias=antialias,
            _fixed_canvas=(cell_size, cell_size),
        )

        color = corner_colors[idx]
        instance_rgba = _apply_color_tint(instance_pixels, background, color)

        _paste_cell(canvas_pixels, canvas_width, instance_rgba, left, top, cell_size)

    axis1_label = f"{axis1}: {min1:.0f} → {max1:.0f}"
    axis2_label = f"{axis2}: {min2:.0f} → {max2:.0f}"

    corner_labels = [
        f"{axis1}: {min1:.0f} | {axis2}: {min2:.0f}",
        f"{axis1}: {min1:.0f} | {axis2}: {max2:.0f}",
        f"{axis1}: {max1:.0f} | {axis2}: {min2:.0f}",
        f"{axis1}: {max1:.0f} | {axis2}: {max2:.0f}",
    ]

    _draw_legend(
        canvas_pixels,
        canvas_width,
        canvas_height,
        legend_height,
        axis1_label,
        axis2_label,
        corner_labels,
        corner_colors,
    )

    png_data = _encode_png_rgb(canvas_width, canvas_height, bytes(canvas_pixels))
    if output_path is not None:
        Path(output_path).write_bytes(png_data)
        return None
    else:
        return png_data


def _render_color_glyph_to_rgb(
    font: TtfFont,
    glyph_id: int,
    *,
    size: float = 72.0,
    palette_index: int = 0,
    background: tuple[int, int, int] = (255, 255, 255),
    padding: int = 4,
    antialias: bool = True,
) -> tuple[int, int, bytes]:

    cpal = font.ttf_tables.cpal
    colr = font.ttf_tables.colr

    if not cpal or not colr or colr.version != 1:
        raise ValueError("COLR v1 table not available")

    base_glyph_records = colr.base_glyph_v1_records
    if not base_glyph_records:
        raise ValueError("No COLR v1 base glyph records found")

    record = None
    for rec in base_glyph_records:
        if rec.glyph_id == glyph_id:
            record = rec
            break

    if record is None:
        raise ValueError(f"Glyph ID {glyph_id} not found in COLR v1 table")

    start_layer_index = record.start_layer_index
    num_layers = record.num_layers

    layer_v1_records = colr.layer_v1_records
    paints = colr.paints

    if layer_v1_records is None or paints is None:
        raise ValueError("COLR v1 layer records or paints not available")

    layers = layer_v1_records[start_layer_index:start_layer_index + num_layers]

    palette = cpal.palettes[palette_index % len(cpal.palettes)]

    paths_with_colors: list[tuple[GlyphPath, tuple[int, int, int]]] = []

    for layer in layers:
        layer_gid = layer.glyph_id
        paint_offset = layer.paint_offset

        paint = paints.get(paint_offset)

        if paint is None:
            continue

        final_paint = _resolve_paint_tree(paint, paints)

        if isinstance(final_paint, PaintSolid):
            color_rgba = palette[final_paint.palette_index]
            r, g, b, _ = color_rgba
            color_rgb = (r, g, b)
        else:
            continue

        layer_glyph = font.glyph_accessor.get_glyph_by_id(layer_gid)
        if layer_glyph.path is None or len(layer_glyph.path) == 0:
            continue

        path = layer_glyph.path
        paths_with_colors.append((path, color_rgb))

    if not paths_with_colors:
        return _render_monochrome_glyph(
            font,
            glyph_id,
            size=size,
            background=background,
            padding=padding,
            antialias=antialias,
        )

    path_list = [p for p, _ in paths_with_colors]
    all_bounds = [_path_bounds(p) for p in path_list]
    all_bounds = [b for b in all_bounds if b is not None]

    if not all_bounds:
        return _render_monochrome_glyph(
            font,
            glyph_id,
            size=size,
            background=background,
            padding=padding,
            antialias=antialias,
        )

    min_x = min(b[0] for b in all_bounds)
    min_y = min(b[1] for b in all_bounds)
    max_x = max(b[2] for b in all_bounds)
    max_y = max(b[3] for b in all_bounds)

    glyph_width = max_x - min_x
    glyph_height = max_y - min_y

    canvas_width = max(1, int(glyph_width) + padding * 2)
    canvas_height = max(1, int(glyph_height) + padding * 2)

    scale_factor = 4 if antialias else 1
    sf = float(scale_factor)

    raster = Rasterizer(canvas_width * scale_factor, canvas_height * scale_factor, background)

    transform = (
        sf,
        0.0,
        0.0,
        -sf,
        sf * (padding - min_x),
        sf * (canvas_height - padding - max_y),
    )

    for path, color in paths_with_colors:
        raster.draw_path(path, color=color, transform=transform)

    if antialias:
        out = Rasterizer(canvas_width, canvas_height, background)
        for y in range(out.height):
            for x in range(out.width):
                r = 0
                g = 0
                b = 0
                base_y = y * 4
                base_x = x * 4
                for dy in range(4):
                    for dx in range(4):
                        px = (base_y + dy) * raster.width + (base_x + dx)
                        idx = px * 3
                        r += raster._buf[idx]
                        g += raster._buf[idx + 1]
                        b += raster._buf[idx + 2]
                r //= 16
                g //= 16
                b //= 16
                dst_idx = (y * out.width + x) * 3
                out._buf[dst_idx] = r
                out._buf[dst_idx + 1] = g
                out._buf[dst_idx + 2] = b
        return canvas_width, canvas_height, bytes(out._buf)

    return canvas_width, canvas_height, bytes(raster._buf)


def _resolve_paint_tree(paint: object, paints: dict[int, object]) -> object:
    if isinstance(paint, PaintSolid):
        return paint
    elif isinstance(paint, PaintGlyph):
        return _resolve_paint_tree(paint.paint, paints)
    elif isinstance(paint, PaintColrLayers):
        if paint.num_layers > 0 and paint.start_layer_index >= 0:
            first_layer_paint_offset = paint.start_layer_index
            return _resolve_paint_tree(paints.get(first_layer_paint_offset), paints)
        return paint
    elif isinstance(paint, PaintTransform):
        return _resolve_paint_tree(paint.paint, paints)
    elif isinstance(paint, PaintTranslate):
        return _resolve_paint_tree(paint.paint, paints)
    elif isinstance(paint, PaintScale):
        return _resolve_paint_tree(paint.paint, paints)
    elif isinstance(paint, PaintRotate):
        return _resolve_paint_tree(paint.paint, paints)
    elif isinstance(paint, PaintSkew):
        return _resolve_paint_tree(paint.paint, paints)
    elif isinstance(paint, PaintLinearGradient):
        return paint
    elif isinstance(paint, PaintRadialGradient):
        return paint
    return paint


def _render_monochrome_glyph(
    font: TtfFont,
    glyph_id: int,
    *,
    size: float = 72.0,
    background: tuple[int, int, int] = (255, 255, 255),
    padding: int = 4,
    antialias: bool = True,
) -> tuple[int, int, bytes]:
    text = "H"

    width, height, rgb_bytes = TextRenderer.render_rgb(
        font,
        text,
        size=size,
        color=(0, 0, 0),
        background=background,
        padding=padding,
        antialias=antialias,
        _fixed_canvas=None,
        _fixed_baseline=None,
    )

    return width, height, rgb_bytes


def _path_bounds(path: GlyphPath) -> tuple[int, int, int, int] | None:
    min_x = float('inf')
    min_y = float('inf')
    max_x = float('-inf')
    max_y = float('-inf')

    has_points = False

    for cmd in path:
        x, y = 0.0, 0.0
        if isinstance(cmd, MoveTo):
            x, y = cmd.x, cmd.y
            has_points = True
        elif isinstance(cmd, LineTo):
            x, y = cmd.x, cmd.y
            has_points = True
        elif isinstance(cmd, QuadraticTo):
            x, y = cmd.x, cmd.y
            has_points = True
        elif isinstance(cmd, CurveTo):
            x, y = cmd.x, cmd.y
            has_points = True

        if has_points:
            min_x = min(min_x, x)
            min_y = min(min_y, y)
            max_x = max(max_x, x)
            max_y = max(max_y, y)

    if not has_points:
        return None

    return (int(min_x), int(min_y), int(max_x), int(max_y))


def _apply_color_tint(
    pixels: bytes,
    background: tuple[int, int, int],
    tint_color: tuple[int, int, int],
) -> bytes:
    result = bytearray(len(pixels))
    bg_luma = _rgb_luma(background)
    threshold = 8
    for i in range(0, len(pixels), 3):
        r, g, b = pixels[i], pixels[i + 1], pixels[i + 2]
        luma = bg_luma - _rgb_luma((r, g, b))
        ink = max(0, luma)
        if ink > threshold:
            result[i] = tint_color[0]
            result[i + 1] = tint_color[1]
            result[i + 2] = tint_color[2]
        else:
            result[i:i + 3] = bytes((r, g, b))
    return bytes(result)


def _paste_cell(
    canvas: bytearray,
    canvas_width: int,
    cell_pixels: bytes,
    left: int,
    top: int,
    cell_size: int,
) -> None:
    cell_width = cell_size
    cell_height = cell_size
    for y in range(cell_height):
        src_start = y * cell_width * 3
        dst_start = ((top + y) * canvas_width + left) * 3
        canvas[dst_start:dst_start + cell_width * 3] = cell_pixels[src_start:src_start + cell_width * 3]


def _draw_legend(
    pixels: bytearray,
    canvas_width: int,
    canvas_height: int,
    legend_height: int,
    axis1_label: str,
    axis2_label: str,
    corner_labels: list[str],
    corner_colors: tuple[tuple[int, int, int], ...],
) -> None:
    bg = (255, 255, 255)
    border = (100, 100, 100)
    text_color = (50, 50, 50)

    legend_top = canvas_height - legend_height
    canvas_width_int = canvas_width

    _fill_rect(pixels, canvas_width_int, 0, legend_top, canvas_width_int, legend_height, bg)
    _draw_rect_outline(pixels, canvas_width_int, 0, legend_top, canvas_width_int, legend_height, color=border)

    _draw_centered_text_block(
        pixels, canvas_width_int, 0, legend_top + 8, canvas_width_int, 20,
        axis1_label, color=text_color, max_chars=60
    )
    _draw_centered_text_block(
        pixels, canvas_width_int, 0, legend_top + 30, canvas_width_int, 20,
        axis2_label, color=text_color, max_chars=60
    )

    for idx, label in enumerate(corner_labels):
        col = idx % 2
        left = col * 324 + 12
        top = legend_top + 10
        _draw_centered_text_block(
            pixels, canvas_width_int, left, top, 300, 30,
            label, color=corner_colors[idx], max_chars=40
        )


__all__ = [
    "PreviewImage",
    "FontPreviewBuilder",
    "generate_waterfall_matrix",
    "generate_designspace_diff_overlay",
]


def generate_waterfall_matrix(
    bundles: list["WebFontBundle"],
    *,
    preview_text: str = _DEFAULT_PREVIEW_TEXT,
    file_stem: str = "waterfall-matrix",
    output_format: str = "png",
) -> "PreviewImage":
    from aspose_font.web import WebFontBuilder

    if not bundles:
        raise ValueError("Waterfall & matrix export requires at least one web font bundle")

    normalized_format = output_format.lower()
    if normalized_format not in ("png", "pdf", "pptx"):
        raise ValueError(f"Unsupported output format: {output_format!r}. Supported: png, pdf, pptx")

    waterfall = WebFontBuilder.build_family_waterfall_preview(
        bundles, preview_text=preview_text, file_stem="waterfall"
    )
    matrix = WebFontBuilder.build_family_matrix_preview(
        bundles, preview_text=preview_text, file_stem="matrix"
    )

    waterfall_png = _decode_png_rgb(waterfall.data)
    matrix_png = _decode_png_rgb(matrix.data)

    gap = 16
    canvas_width = waterfall_png[0] + matrix_png[0] + gap
    canvas_height = max(waterfall_png[1], matrix_png[1])

    title_lines = [_sheet_title_for_waterfall_matrix(bundles)]
    footer_lines = [
        f"Preview text: {preview_text}",
        f"Styles: {', '.join(bundle.style for bundle in bundles)}",
    ]

    title_height = _text_block_height(title_lines, max_chars=60)
    footer_height = _text_block_height(footer_lines, max_chars=48) + 12

    total_height = canvas_height + title_height + footer_height + gap * 3
    total_width = canvas_width + gap * 2

    pixels = _create_rgb_canvas(total_width, total_height, _BOARD_PANEL)

    title_top = gap
    _draw_centered_text_block(
        pixels, total_width, gap, title_top, total_width - gap * 2,
        title_height, title_lines[0], color=_BOARD_LABEL, max_chars=60
    )

    rule_y = title_top + title_height + 4
    _draw_horizontal_rule(pixels, total_width, gap, total_width - gap, rule_y, color=_BOARD_RULE)

    content_top = rule_y + gap
    waterfall_left = gap
    matrix_left = waterfall_left + waterfall_png[0] + gap

    _draw_image_at(pixels, total_width, waterfall_png, waterfall_left, content_top)
    _draw_image_at(pixels, total_width, matrix_png, matrix_left, content_top)

    footer_top = content_top + canvas_height + gap
    _draw_text_block(
        pixels, total_width, gap + 8, footer_top,
        total_width - gap * 16, footer_height, footer_lines,
        color=_BOARD_LABEL, max_chars=48
    )

    data = _encode_png_rgb(total_width, total_height, bytes(pixels))

    if normalized_format == "pdf":
        data = _convert_png_to_pdf(data)
    elif normalized_format == "pptx":
        data = _convert_png_to_pptx(total_width, total_height, bytes(pixels))

    return PreviewImage(
        filename=f"{file_stem}.{'pptx' if normalized_format == 'pptx' else ('pdf' if normalized_format == 'pdf' else 'png')}",
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation" if normalized_format == "pptx" else ("application/pdf" if normalized_format == "pdf" else "image/png"),
        data=data,
    )


def _sheet_title_for_waterfall_matrix(bundles: list[WebFontBundle]) -> str:
    family_name = bundles[0].family if bundles else "Fonts"
    return f"{family_name} Review - Waterfall & Matrix"


def _convert_png_to_emf(width: int, height: int, png_data: bytes) -> bytes:
    import struct

    row_size = (width * 3 + 3) & ~3
    pixel_data_size = row_size * height

    emf_data = bytearray()

    emf_data.extend(struct.pack('<I', 1))
    emf_data.extend(struct.pack('<I', 100))
    emf_data.extend(struct.pack('<II', width * 100, height * 100))
    emf_data.extend(struct.pack('<I', 0x20000))
    emf_data.extend(struct.pack('<I', 1))
    emf_data.extend(struct.pack('<II', width, height))
    emf_data.extend(struct.pack('<II', width * 2540 // 100, height * 2540 // 100))
    emf_data.extend(struct.pack('<I', 0))
    emf_data.extend(struct.pack('<I', 24))
    emf_data.extend(struct.pack('<I', 1))
    emf_data.extend(struct.pack('<I', 0))
    emf_data.extend(struct.pack('<I', 0))
    emf_data.extend(struct.pack('<I', 0))
    emf_data.extend(struct.pack('<I', 0))
    emf_data.extend(struct.pack('<I', 0))
    emf_data.extend(struct.pack('<I', 0))
    emf_data.extend(b'\x00' * 44)

    header_record = bytearray()
    header_record.extend(struct.pack('<I', 96))
    header_record.extend(struct.pack('<I', 0x20000))
    header_record.extend(struct.pack('<I', 1))
    header_record.extend(struct.pack('<I', 0))
    header_record.extend(struct.pack('<I', 0))
    header_record.extend(struct.pack('<h', 0))
    header_record.extend(struct.pack('<II', 0, 0))
    header_record.extend(struct.pack('<II', width, height))
    header_record.extend(struct.pack('<I', 0))
    header_record.extend(struct.pack('<I', 1))
    header_record.extend(struct.pack('<II', 0, 0))
    header_record.extend(struct.pack('<II', 0, 0))
    header_record.extend(b'\x00' * 24)

    bmi_header = struct.pack('<IIIHHIIIIII',
        40,
        width,
        height,
        1,
        24,
        0,
        pixel_data_size,
        0, 0,
        0, 0
    )

    flipped_pixels = bytearray()
    for y in range(height - 1, -1, -1):
        start = y * width * 3
        flipped_pixels.extend(png_data[start:start + width * 3])

    padded_pixels = bytearray()
    for y in range(height):
        start = y * width * 3
        row = flipped_pixels[start:start + width * 3]
        padded_pixels.extend(row)
        padding = row_size - len(row)
        if padding > 0:
            padded_pixels.extend(b'\x00' * padding)

    emf = bytes(emf_data) + bytes(header_record) + bmi_header + bytes(padded_pixels)
    return emf


def _convert_png_to_pptx(width: int, height: int, png_data: bytes) -> bytes:
    import io
    import zipfile

    emf_data = _convert_png_to_emf(width, height, png_data)

    output = io.BytesIO()

    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(
            '_rels/.rels',
            b'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            b'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            b'<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
            b'Target="ppt/presentation.xml"/></Relationships>'
        )

        slide_id = 256
        presentation_xml = (
            b'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            b'<p:presentation xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" '
            b'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
            b'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
            b'removePersonalInformationOnSave="false" comments="false" conjugate="false" mirror="false">'
            b'<p:sldMasterIdLst><p:sldMasterId id="2147483648" r:id="rId1"/></p:sldMasterIdLst>'
            b'<p:sldIdLst><p:sldId id="%d" r:id="rId2"/></p:sldIdLst>'
            b'<p:sldLayoutIdLst><p:sldLayoutId id="2147483649" r:id="rId3"/></p:sldLayoutIdLst>'
            b'<p:notesMasterIdLst><p:notesMasterId id="2147483650" r:id="rId4"/></p:notesMasterIdLst>'
            b'<p:handoutMasterIdLst><p:handoutMasterId id="2147483651" r:id="rId5"/></p:handoutMasterIdLst>'
            b'<p:version>1600</p:version></p:presentation>'
        ) % slide_id
        zf.writestr('ppt/presentation.xml', presentation_xml)

        zf.writestr(
            'ppt/_rels/presentation.xml.rels',
            b'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            b'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            b'<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" '
            b'Target="slideMasters/slideMaster1.xml"/>'
            b'<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" '
            b'Target="slides/slide1.xml"/>'
            b'<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" '
            b'Target="slideLayouts/slideLayout1.xml"/>'
            b'<Relationship Id="rId4" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/notesMaster" '
            b'Target="notesMasters/notesMaster1.xml"/>'
            b'<Relationship Id="rId5" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/handoutMaster" '
            b'Target="handoutMasters/handoutMaster1.xml"/></Relationships>'
        )

        zf.writestr(
            'ppt/slideMasters/slideMaster1.xml',
            b'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            b'<p:sldMaster xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" '
            b'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" id="2147483648">'
            b'<p:cSld name="Custom Master 1"><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/></p:nvGrpSpPr><p:grpSpPr/></p:spTree></p:cSld>'
            b'<p:txStyle><p:level1Style><a:defRPr LANG="en-US"/></p:level1Style></p:txStyle></p:sldMaster>'
        )

        zf.writestr(
            'ppt/slideLayouts/slideLayout1.xml',
            b'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            b'<p:sldLayout xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" '
            b'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
            b'name="Title and Content" type="titleslide" preserve="1"><p:cSld><p:spTree>'
            b'<p:nvGrpSpPr><p:cNvPr id="1" name=""/></p:nvGrpSpPr><p:grpSpPr/></p:spTree></p:cSld>'
            b'<p:txStyles><p:level1Style><a:defRPr LANG="en-US"/></p:level1Style></p:txStyles></p:sldLayout>'
        )

        zf.writestr(
            'ppt/notesMasters/notesMaster1.xml',
            b'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            b'<p:notesMaster xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" '
            b'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" id="2147483650">'
            b'<p:cSld><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/></p:nvGrpSpPr><p:grpSpPr/></p:spTree></p:cSld></p:notesMaster>'
        )

        zf.writestr(
            'ppt/handoutMasters/handoutMaster1.xml',
            b'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            b'<p:handoutMaster xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" '
            b'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" id="2147483651">'
            b'<p:cSld><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/></p:nvGrpSpPr><p:grpSpPr/></p:spTree></p:cSld></p:handoutMaster>'
        )

        cx = width * 9525
        cy = height * 9525
        slide_xml = (
            b'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            b'<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" '
            b'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            b'<p:cSld><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/></p:nvGrpSpPr><p:grpSpPr/></p:nvGrpSpPr><p:grpSpPr>'
            b'<a:grpSpPr><a:extLst><a:ext uri="{BBA9A655-996E-4F28-9625-3A3A2B2B2B2B}"><a14:useLocalDpi xmlns:a14="http://schemas.microsoft.com/office/drawing/2010/main" val="0"/></a:ext></a:extLst></a:grpSpPr>'
            b'</p:grpSpPr><p:sp><p:nvSpPr><p:cNvPr id="2" name="Image 1"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr><p:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="%d" cy="%d"/></a:xfrm></p:spPr><p:txBody><a:bodyPr rtlCol="0" anchor="ctr"/><a:lstStyle/><a:p algn="l"><a:endParaRPr lang="en-US"/></a:p></p:txBody></p:sp>'
            b'<p:pic><p:nvPicPr><p:cNvPr id="3" name="Picture 1"/><p:cNvPicPr><a:picLocks noChangeAspect="1"/></p:cNvPicPr><p:nvPr/></p:nvPicPr><p:blipFill><a:blip r:embed="rId1" cstate="print"/><a:stretch><a:fillRect/></a:stretch></p:blipFill><p:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="%d" cy="%d"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></p:spPr></p:pic></p:spTree></p:cSld></p:sld>'
        ) % (cx, cy, cx, cy)
        zf.writestr('ppt/slides/slide1.xml', slide_xml)

        zf.writestr(
            'ppt/slides/_rels/slide1.xml.rels',
            b'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            b'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            b'<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" '
            b'Target="media/image1.emf"/></Relationships>'
        )

        zf.writestr('ppt/media/image1.emf', emf_data)

    return output.getvalue()


def _create_rgb_canvas(width: int, height: int, color: tuple[int, int, int]) -> bytearray:
    pixels = bytearray(width * height * 3)
    fill = bytes(color)
    for y in range(height):
        start = y * width * 3
        end = start + width * 3
        pixels[start:end] = fill * width
    return pixels


def _draw_image_at(
    pixels: bytearray,
    canvas_width: int,
    image_tuple: tuple[int, int, bytes],
    left: int,
    top: int,
) -> None:
    width, height, src_pixels = image_tuple

    for y in range(height):
        src_start = y * width * 3
        dst_start = ((top + y) * canvas_width + left) * 3
        pixels[dst_start:dst_start + width * 3] = src_pixels[src_start:src_start + width * 3]


def _convert_png_to_pdf(png_data: bytes) -> bytes:
    import zlib

    png_sig = b"\x89PNG\r\n\x1a\n"
    if not png_data.startswith(png_sig):
        raise ValueError("PNG data required for PDF conversion")

    pos = 8
    width = 0
    height = 0
    idat_parts: list[bytes] = []
    while pos + 8 <= len(png_data):
        length = struct.unpack_from(">I", png_data, pos)[0]
        ctype = png_data[pos + 4:pos + 8]
        chunk_data = png_data[pos + 8:pos + 8 + length]
        pos += 12 + length
        if ctype == b"IHDR":
            width, height = struct.unpack_from(">II", chunk_data, 0)
        elif ctype == b"IDAT":
            idat_parts.append(chunk_data)
        elif ctype == b"IEND":
            break

    raw = zlib.decompress(b"".join(idat_parts))

    pdf_header = b"%PDF-1.4\n"

    xref_obj_num = 5
    objects: list[bytes] = []

    obj1 = b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
    objects.append(obj1)

    image_width_pts = width / 4
    image_height_pts = height / 4

    obj2 = (
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
    )
    objects.append(obj2)

    obj3 = (
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 "
        + str(image_width_pts).encode()
        + b" "
        + str(image_height_pts).encode()
        + b"] /Contents 4 0 R >>\nendobj\n"
    )
    objects.append(obj3)

    compressed_data = zlib.compress(raw, 9)
    obj4 = (
        b"4 0 obj\n<< /Filter /FlateDecode /Length "
        + str(len(compressed_data)).encode()
        + b" >>\nstream\n"
        + compressed_data
        + b"\nendstream\nendobj\n"
    )
    objects.append(obj4)

    xref_start = len(pdf_header) + sum(len(obj) for obj in objects)
    xref_lines = [b"xref\n0 " + str(xref_obj_num + 1).encode() + b"\n"]
    xref_lines.append(b"0000000000 65535 f \n")
    offset = len(pdf_header)
    for obj in objects:
        xref_lines.append(f"{offset:010d} 00000 n \n".encode())
        offset += len(obj)

    trailer = (
        b"trailer\n<< /Size "
        + str(xref_obj_num + 1).encode()
        + b" /Root 1 0 R >>\nstartxref\n"
        + str(xref_start).encode()
        + b"\n%%EOF\n"
    )

    return pdf_header + b"".join(objects) + b"".join(xref_lines) + trailer


def _convert_html_to_png(html_str: str) -> bytes:
    """Convert HTML string to PNG bytes by rendering with a simple font preview.

    This function creates a minimal PNG with the HTML content rendered as text.
    """
    from aspose_font.text import TextRenderer

    width = 800
    height = 600
    background = (255, 255, 255)

    pixels = bytearray(width * height * 3)
    for i in range(len(pixels)):
        pixels[i] = background[i % 3]

    lines = html_str.replace("<br/>", "\n").replace("<br>", "\n").replace("</p>", "\n").split("\n")
    y_offset = 20

    for line in lines:
        clean_line = (
            line.replace("<h1>", "").replace("</h1>", "")
            .replace("<h2>", "").replace("</h2>", "")
            .replace("<strong>", "").replace("</strong>", "")
            .replace("<p>", "").replace("</p>", "")
            .replace("<ul>", "").replace("</ul>", "")
            .replace("<li>", "").replace("</li>", "  - ")
            .replace("<!doctype html>", "")
            .replace("<html lang=\"en\">", "")
            .replace("</html>", "")
            .replace("<head>", "").replace("</head>", "")
            .replace("<body>", "").replace("</body>", "")
            .replace("</title>", "")
            .replace("<style>body{font-family:system-ui,sans-serif;line-height:1.45;margin:2rem;max-width:900px}", "")
            .replace("<table{border-collapse:collapse;width:100%;margin:1rem 0}td,th{border:1px solid #ddd;padding:.45rem;text-align:left}", "")
            .replace("<code{background:#f5f5f5;padding:.1rem .25rem}", "")
            .replace("<.readiness-badge{display:inline-block;padding:.25rem .75rem;border-radius:.375rem;color:#fff;font-weight:600}", "")
        )
        if clean_line.strip():
            try:
                width_out, height_out, rgb_bytes = TextRenderer.render_rgb(
                    _get_default_font(),
                    clean_line.strip(),
                    size=14,
                    color=(17, 17, 17),
                    background=background,
                    padding=4,
                )
                if width_out > 0 and height_out > 0:
                    x = 20
                    for py in range(height_out):
                        if 0 <= y_offset + py < height:
                            src_row = py * width_out * 3
                            dst_row = (y_offset + py) * width * 3 + x * 3
                            pixels[dst_row:dst_row + width_out * 3] = rgb_bytes[src_row:src_row + width_out * 3]
                    y_offset += height_out + 8
            except Exception:
                pass

    return _encode_png_rgb(width, height, bytes(pixels))


def _get_default_font() -> Font:
    """Get a default fallback font for rendering HTML content."""

    try:
        from pathlib import Path
        roboto_path = Path(__file__).resolve().parents[1] / "testdata" / "Roboto-VariableFont_wdth,wght.ttf"
        if roboto_path.exists():
            from aspose_font import FontLoader
            return FontLoader.open(roboto_path)
    except Exception:
        pass

    class _FallbackFont:
        font_type = None
        font_name = "Fallback"
        font_family = "Fallback"
        font_style = "Regular"
        num_glyphs = 1
        metrics = type("Metrics", (), {"units_per_em": 1000, "ascender": 800, "descender": -200, "line_gap": 0})()

        @property
        def is_variable(self):
            return False

        @property
        def variable_axes(self):
            return []

        @property
        def variable_instances(self):
            return []

        class _FakeEncoding:
            def unicode_to_gid(self, codepoint):
                return 0

        class _FakeGlyphAccessor:
            def get_glyph_by_id(self, gid):
                class _FakeGlyph:
                    advance_width = 500
                    path = None
                return _FakeGlyph()

            def get_all_glyph_ids(self):
                return [0]

        encoding = _FakeEncoding()
        glyph_accessor = _FakeGlyphAccessor()

    return _FallbackFont()


class _WebFontBundle:
    pass

