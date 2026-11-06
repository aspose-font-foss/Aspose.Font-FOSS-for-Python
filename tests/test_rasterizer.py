"""Tests for rasterization and PNG rendering (SPEC-015 / ADR-015 / FONT-16)."""

from __future__ import annotations

import struct
import zlib

from aspose_font import TtfFont
from aspose_font._types import ClosePath, GlyphPath, LineTo, MoveTo
from aspose_font.rasterizer import Rasterizer
from aspose_font.text import TextRenderer


def _png_dimensions(data: bytes) -> tuple[int, int]:
    return (
        struct.unpack_from(">I", data, 16)[0],
        struct.unpack_from(">I", data, 20)[0],
    )


def _png_pixels(data: bytes) -> tuple[int, int, bytes]:
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError("not a PNG signature")

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
            raise ValueError(f"unsupported PNG filter: {filter_type}")
        pixels[wp:wp + stride] = raw[rp:rp + stride]
        rp += stride
        wp += stride
    return width, height, bytes(pixels)


def _make_triangle() -> GlyphPath:
    path = GlyphPath()
    path.append(MoveTo(10.0, 10.0))
    path.append(LineTo(90.0, 10.0))
    path.append(LineTo(50.0, 90.0))
    path.append(ClosePath())
    return path


def test_render_png_magic_bytes(roboto: TtfFont) -> None:
    data = TextRenderer.render_png(roboto, "A", size=64)
    assert data.startswith(b"\x89PNG")


def test_render_png_dimensions(roboto: TtfFont) -> None:
    data = TextRenderer.render_png(roboto, "A", size=64)
    w, h = _png_dimensions(data)
    assert w > 0
    assert h > 0


def test_render_empty_string(roboto: TtfFont) -> None:
    data = TextRenderer.render_png(roboto, "", size=64)
    assert data.startswith(b"\x89PNG")
    w, h = _png_dimensions(data)
    assert w > 0
    assert h > 0


def test_rasterizer_triangle() -> None:
    raster = Rasterizer(100, 100)
    raster.draw_path(_make_triangle(), color=(0, 0, 0))
    data = raster.to_png()
    assert data.startswith(b"\x89PNG")


def test_rasterizer_to_png_roundtrip() -> None:
    raster = Rasterizer(12, 7)
    data = raster.to_png()
    assert _png_dimensions(data) == (12, 7)


def test_antialias_vs_no_antialias(roboto: TtfFont) -> None:
    data_aa = TextRenderer.render_png(roboto, "A", size=64, antialias=True)
    data_noaa = TextRenderer.render_png(roboto, "A", size=64, antialias=False)

    _, _, px_aa = _png_pixels(data_aa)
    _, _, px_noaa = _png_pixels(data_noaa)

    has_mid_tone_aa = any(ch not in (0, 255) for ch in px_aa)
    has_mid_tone_noaa = any(ch not in (0, 255) for ch in px_noaa)

    assert has_mid_tone_aa
    assert not has_mid_tone_noaa
