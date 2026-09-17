"""High-level preview image generation helpers."""

from __future__ import annotations

import struct
import zlib
from dataclasses import dataclass
from pathlib import Path

from aspose_font._exceptions import FontNotSupportedException
from aspose_font._font_base import Font
from aspose_font.text import TextRenderer
from aspose_font.ttf.font import TtfFont

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


__all__ = ["PreviewImage", "FontPreviewBuilder"]
