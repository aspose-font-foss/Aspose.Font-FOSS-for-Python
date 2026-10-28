"""Tests for FONT-413 Color Glyph Rasterization Preview Support."""

from __future__ import annotations

import sys
from pathlib import Path

from aspose_font import FontLoader
from aspose_font._exceptions import FontNotSupportedException
from aspose_font._types import GlyphId
from aspose_font.preview import FontPreviewBuilder, _decode_png_rgb

ROBOTO_REGULAR = str(Path(__file__).resolve().parents[1] / "testdata" / "Fonts" / "Roboto-Regular.ttf")
ROBOTO_VARIABLE = str(Path(__file__).resolve().parents[1] / "testdata" / "Roboto-VariableFont_wdth,wght.ttf")

CLI = [sys.executable, "-m", "aspose_font.cli"]


def test_render_color_glyph_png_magic_bytes():
    """Verify PNG signature bytes in rendered output."""
    font_loader = FontLoader.load(ROBOTO_REGULAR)
    font = font_loader.font

    result = FontPreviewBuilder.render_color_glyph(
        font,
        glyph_id=9,
        size=72.0,
        palette_index=0,
        background=(255, 255, 255),
        padding=12,
        antialias=True,
    )

    assert result.filename == "color-glyph-9.png"
    assert result.media_type == "image/png"
    assert result.data.startswith(b"\x89PNG\r\n\x1a\n")


def test_render_color_glyph_png_dimensions():
    """Confirm non-zero width/height for rendered glyph."""
    font_loader = FontLoader.load(ROBOTO_REGULAR)
    font = font_loader.font

    result = FontPreviewBuilder.render_color_glyph(
        font,
        glyph_id=9,
        size=72.0,
        palette_index=0,
        background=(255, 255, 255),
        padding=12,
        antialias=True,
    )

    width, height, pixels = _decode_png_rgb(result.data)

    assert width > 0
    assert height > 0
    assert len(pixels) == width * height * 3


def test_render_color_glyph_palette_index_0():
    """Validate color presence in PNG (ensure not all pixels match background)."""
    font_loader = FontLoader.load(ROBOTO_REGULAR)
    font = font_loader.font

    result = FontPreviewBuilder.render_color_glyph(
        font,
        glyph_id=9,
        size=72.0,
        palette_index=0,
        background=(255, 255, 255),
        padding=12,
        antialias=True,
    )

    width, height, pixels = _decode_png_rgb(result.data)

    bg_color = (255, 255, 255)
    ink_pixels = 0

    for i in range(0, len(pixels), 3):
        r, g, b = pixels[i], pixels[i + 1], pixels[i + 2]
        if (r, g, b) != bg_color:
            ink_pixels += 1

    assert ink_pixels > 0, "No ink pixels found - glyph may not have rendered"


def test_render_color_glyph_fallback_to_monochrome():
    """Confirm monochrome output when COLRv1 not available (Roboto-Regular has no COLR)."""
    font_loader = FontLoader.load(ROBOTO_REGULAR)
    font = font_loader.font

    result = FontPreviewBuilder.render_color_glyph(
        font,
        glyph_id=9,
        size=72.0,
        palette_index=0,
        background=(255, 255, 255),
        padding=12,
        antialias=True,
    )

    assert result.media_type == "image/png"
    assert result.data.startswith(b"\x89PNG\r\n\x1a\n")

    width, height, pixels = _decode_png_rgb(result.data)

    assert width > 0
    assert height > 0

    has_ink = False
    for i in range(0, len(pixels), 3):
        r, g, b = pixels[i], pixels[i + 1], pixels[i + 2]
        if (r, g, b) != (255, 255, 255):
            has_ink = True
            break

    assert has_ink, "Expected ink in rendered monochrome glyph"


def test_render_color_glyph_non_ttf_font():
    """Verify FontNotSupportedException for non-TTF fonts."""
    try:
        font_loader = FontLoader.load(ROBOTO_REGULAR)
        font = font_loader

        FontPreviewBuilder.render_color_glyph(
            font,
            glyph_id=3,
            size=72.0,
            palette_index=0,
            background=(255, 255, 255),
            padding=12,
            antialias=True,
        )

        assert False, "Expected FontNotSupportedException for non-TTF font"
    except FontNotSupportedException as e:
        assert "TTF" in str(e).upper() or "ttf" in str(e)


def test_render_color_glyph_with_glyph_id_object():
    """Test that GlyphId objects work as glyph_id parameter."""
    font_loader = FontLoader.load(ROBOTO_REGULAR)
    font = font_loader.font

    result = FontPreviewBuilder.render_color_glyph(
        font,
        glyph_id=GlyphId(9),
        size=72.0,
        palette_index=0,
        background=(255, 255, 255),
        padding=12,
        antialias=True,
    )

    assert result.filename == "color-glyph-9.png"
    assert result.media_type == "image/png"
    assert result.data.startswith(b"\x89PNG\r\n\x1a\n")
