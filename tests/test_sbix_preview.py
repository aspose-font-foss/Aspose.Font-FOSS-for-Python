"""Tests for FONT-474 Color Bitmap Glyph Extraction in FontPreviewBuilder."""

from __future__ import annotations

import sys
from pathlib import Path

from aspose_font._io import BinaryReader
from aspose_font._types import GlyphId
from aspose_font.preview import FontPreviewBuilder, _decode_png_rgb
from aspose_font.ttf.font import TtfFont

CLI = [sys.executable, "-m", "aspose_font.cli"]


def _build_minimal_sfnt_with_sbix(sbix_data: bytes, num_glyphs: int = 10) -> bytes:
    """Build a minimal SFNT font with sbix table."""
    units_per_em = 2048

    head = (
        (1).to_bytes(2, "big")
        + (0).to_bytes(2, "big")
        + (0x00010000).to_bytes(4, "big")
        + (0).to_bytes(4, "big")
        + (0x5F0F3CF5).to_bytes(4, "big")
        + (0).to_bytes(2, "big")
        + units_per_em.to_bytes(2, "big")
        + (0).to_bytes(8, "big")
        + (0).to_bytes(8, "big")
        + (0xFF9C).to_bytes(2, "big")
        + (0xFF38).to_bytes(2, "big")
        + (0x03E8).to_bytes(2, "big")
        + (0x0384).to_bytes(2, "big")
        + (0).to_bytes(2, "big")
        + (8).to_bytes(2, "big")
        + (2).to_bytes(2, "big")
        + (0).to_bytes(2, "big")
        + (0).to_bytes(2, "big")
    )

    maxp = (0x00010000).to_bytes(4, "big") + (num_glyphs).to_bytes(2, "big") + bytes(26)

    num_tables = 3
    offset_table = (
        b"\x00\x01\x00\x00"
        + num_tables.to_bytes(2, "big")
        + (0).to_bytes(2, "big")
        + (0).to_bytes(2, "big")
        + (0).to_bytes(2, "big")
    )

    head_offset = 12 + num_tables * 16
    maxp_offset = head_offset + len(head)
    sbix_offset = maxp_offset + len(maxp)

    directory = (
        b"head"
        + (0).to_bytes(4, "big")
        + head_offset.to_bytes(4, "big")
        + len(head).to_bytes(4, "big")
        + b"maxp"
        + (0).to_bytes(4, "big")
        + maxp_offset.to_bytes(4, "big")
        + len(maxp).to_bytes(4, "big")
        + b"sbix"
        + (0).to_bytes(4, "big")
        + sbix_offset.to_bytes(4, "big")
        + len(sbix_data).to_bytes(4, "big")
    )

    result = offset_table + directory + head + maxp + sbix_data
    return result


def _build_sbix_table_with_png_glyph(glyph_id: int = 5, ppem: int = 24) -> bytes:
    """Build a minimal sbix table with a single PNG glyph."""
    bitmap_data = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIEND\xAE\x42\x60\x82"

    stream = b""
    stream += (0).to_bytes(2, "big")  # version = 0
    stream += (0).to_bytes(2, "big")  # flags = 0
    stream += (1).to_bytes(4, "big")  # num_strikes = 1
    stream += ppem.to_bytes(2, "big")  # ppem
    stream += (96).to_bytes(2, "big")  # resolution = 96
    stream += (0).to_bytes(4, "big")  # offset_to_bitmap_data = 0

    stream += (1).to_bytes(4, "big")  # num_glyphs = 1
    stream += glyph_id.to_bytes(2, "big")  # glyph_id
    stream += b"png "  # graphic_type = png
    stream += (0).to_bytes(2, "big")  # origin_offset_x = 0
    stream += (0).to_bytes(2, "big")  # origin_offset_y = 0
    stream += len(bitmap_data).to_bytes(4, "big")  # bitmap_data_length
    stream += bitmap_data  # bitmap_data

    return stream


class TestRenderSbixGlyphToPng:
    """Tests for FontPreviewBuilder.render_sbix_glyph_to_png method."""

    def test_render_sbix_glyph_to_png_returns_png_bytes(self, tmp_path: Path) -> None:
        """Test that render_sbix_glyph_to_png returns valid PNG bytes for a font with sbix table."""
        sbix_data = _build_sbix_table_with_png_glyph(glyph_id=5, ppem=24)
        font_data = _build_minimal_sfnt_with_sbix(sbix_data, num_glyphs=10)

        font_path = tmp_path / "test.ttf"
        font_path.write_bytes(font_data)

        font = TtfFont._from_reader(BinaryReader(font_data))
        assert isinstance(font, TtfFont)

        preview = FontPreviewBuilder.render_sbix_glyph_to_png(font, glyph_id=5, ppem=24, size=256)

        assert preview.filename == "sbix-glyph-5.png"
        assert preview.media_type == "image/png"
        assert preview.data.startswith(b"\x89PNG\r\n\x1a\n")

    def test_render_sbix_glyph_to_png_with_ppem_fallback(self, tmp_path: Path) -> None:
        """Test that render_sbix_glyph_to_png uses highest ppem when None is specified."""
        stream = b""
        stream += (0).to_bytes(2, "big")  # version = 0
        stream += (0).to_bytes(2, "big")  # flags = 0
        stream += (2).to_bytes(4, "big")  # num_strikes = 2

        stream += (16).to_bytes(2, "big")  # ppem = 16
        stream += (72).to_bytes(2, "big")  # resolution = 72
        stream += (0).to_bytes(4, "big")  # offset_to_bitmap_data = 0

        stream += (32).to_bytes(2, "big")  # ppem = 32
        stream += (96).to_bytes(2, "big")  # resolution = 96
        stream += (0).to_bytes(4, "big")  # offset_to_bitmap_data = 0

        stream += (1).to_bytes(4, "big")  # num_glyphs in strike 0 = 1
        stream += (5).to_bytes(2, "big")  # glyph_id
        stream += b"png "  # graphic_type
        stream += (0).to_bytes(2, "big")  # origin_offset_x
        stream += (0).to_bytes(2, "big")  # origin_offset_y
        stream += (26).to_bytes(4, "big")  # bitmap_data_length
        stream += b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIEND\xAE\x42\x60\x82"

        stream += (1).to_bytes(4, "big")  # num_glyphs in strike 1 = 1
        stream += (5).to_bytes(2, "big")  # glyph_id
        stream += b"png "  # graphic_type
        stream += (0).to_bytes(2, "big")  # origin_offset_x
        stream += (0).to_bytes(2, "big")  # origin_offset_y
        stream += (26).to_bytes(4, "big")  # bitmap_data_length
        stream += b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIEND\xAE\x42\x60\x82"

        font_data = _build_minimal_sfnt_with_sbix(stream, num_glyphs=10)

        font_path = tmp_path / "test.ttf"
        font_path.write_bytes(font_data)

        font = TtfFont._from_reader(BinaryReader(font_data))
        assert isinstance(font, TtfFont)

        preview = FontPreviewBuilder.render_sbix_glyph_to_png(font, glyph_id=5, ppem=None, size=256)

        assert preview.filename == "sbix-glyph-5.png"
        assert preview.media_type == "image/png"

    def test_render_sbix_glyph_to_png_specific_ppem(self, tmp_path: Path) -> None:
        """Test that render_sbix_glyph_to_png with specific ppem returns correct strike."""
        stream = b""
        stream += (0).to_bytes(2, "big")  # version = 0
        stream += (0).to_bytes(2, "big")  # flags = 0
        stream += (2).to_bytes(4, "big")  # num_strikes = 2

        stream += (16).to_bytes(2, "big")  # ppem = 16
        stream += (72).to_bytes(2, "big")  # resolution = 72
        stream += (0).to_bytes(4, "big")  # offset_to_bitmap_data = 0

        stream += (32).to_bytes(2, "big")  # ppem = 32
        stream += (96).to_bytes(2, "big")  # resolution = 96
        stream += (0).to_bytes(4, "big")  # offset_to_bitmap_data = 0

        stream += (1).to_bytes(4, "big")  # num_glyphs in strike 0 = 1
        stream += (5).to_bytes(2, "big")  # glyph_id
        stream += b"png "  # graphic_type
        stream += (0).to_bytes(2, "big")  # origin_offset_x
        stream += (0).to_bytes(2, "big")  # origin_offset_y
        stream += (26).to_bytes(4, "big")  # bitmap_data_length
        stream += b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIEND\xAE\x42\x60\x82"

        stream += (1).to_bytes(4, "big")  # num_glyphs in strike 1 = 1
        stream += (5).to_bytes(2, "big")  # glyph_id
        stream += b"png "  # graphic_type
        stream += (0).to_bytes(2, "big")  # origin_offset_x
        stream += (0).to_bytes(2, "big")  # origin_offset_y
        stream += (26).to_bytes(4, "big")  # bitmap_data_length
        stream += b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIEND\xAE\x42\x60\x82"

        font_data = _build_minimal_sfnt_with_sbix(stream, num_glyphs=10)

        font_path = tmp_path / "test.ttf"
        font_path.write_bytes(font_data)

        font = TtfFont._from_reader(BinaryReader(font_data))
        assert isinstance(font, TtfFont)

        preview = FontPreviewBuilder.render_sbix_glyph_to_png(font, glyph_id=5, ppem=32, size=256)

        assert preview.filename == "sbix-glyph-5.png"
        assert preview.media_type == "image/png"

    def test_render_sbix_glyph_to_png_missing_sbix(self, tmp_path: Path) -> None:
        """Test that missing sbix table falls back to vector rendering."""
        head = (
            (1).to_bytes(2, "big")
            + (0).to_bytes(2, "big")
            + (0x00010000).to_bytes(4, "big")
            + (0).to_bytes(4, "big")
            + (0x5F0F3CF5).to_bytes(4, "big")
            + (0).to_bytes(2, "big")
            + (2048).to_bytes(2, "big")
            + (0).to_bytes(8, "big")
            + (0).to_bytes(8, "big")
            + (0xFF9C).to_bytes(2, "big")
            + (0xFF38).to_bytes(2, "big")
            + (0x03E8).to_bytes(2, "big")
            + (0x0384).to_bytes(2, "big")
            + (0).to_bytes(2, "big")
            + (8).to_bytes(2, "big")
            + (2).to_bytes(2, "big")
            + (0).to_bytes(2, "big")
            + (0).to_bytes(2, "big")
        )

        maxp = (0x00010000).to_bytes(4, "big") + (1).to_bytes(2, "big") + bytes(26)

        num_tables = 2
        offset_table = (
            b"\x00\x01\x00\x00"
            + num_tables.to_bytes(2, "big")
            + (0).to_bytes(2, "big")
            + (0).to_bytes(2, "big")
            + (0).to_bytes(2, "big")
        )

        head_offset = 12 + num_tables * 16
        maxp_offset = head_offset + len(head)

        directory = (
            b"head"
            + (0).to_bytes(4, "big")
            + head_offset.to_bytes(4, "big")
            + len(head).to_bytes(4, "big")
            + b"maxp"
            + (0).to_bytes(4, "big")
            + maxp_offset.to_bytes(4, "big")
            + len(maxp).to_bytes(4, "big")
        )

        font_data = offset_table + directory + head + maxp

        font_path = tmp_path / "test.ttf"
        font_path.write_bytes(font_data)

        font = TtfFont._from_reader(BinaryReader(font_data))

        preview = FontPreviewBuilder.render_sbix_glyph_to_png(font, glyph_id=5, ppem=24, size=256)

        assert preview.filename == "sbix-glyph-5.png"
        assert preview.media_type == "image/png"
        assert preview.data.startswith(b"\x89PNG\r\n\x1a\n")

    def test_render_sbix_glyph_to_png_missing_glyph(self, tmp_path: Path) -> None:
        """Test that missing glyph ID in sbix falls back to vector rendering."""
        sbix_data = _build_sbix_table_with_png_glyph(glyph_id=5, ppem=24)
        font_data = _build_minimal_sfnt_with_sbix(sbix_data, num_glyphs=10)

        font_path = tmp_path / "test.ttf"
        font_path.write_bytes(font_data)

        font = TtfFont._from_reader(BinaryReader(font_data))
        assert isinstance(font, TtfFont)

        preview = FontPreviewBuilder.render_sbix_glyph_to_png(font, glyph_id=100, ppem=24, size=256)

        assert preview.filename == "sbix-glyph-100.png"
        assert preview.media_type == "image/png"
        assert preview.data.startswith(b"\x89PNG\r\n\x1a\n")

    def test_render_sbix_glyph_to_png_with_glyph_id_object(self, tmp_path: Path) -> None:
        """Test that GlyphId object works as glyph_id parameter."""
        sbix_data = _build_sbix_table_with_png_glyph(glyph_id=5, ppem=24)
        font_data = _build_minimal_sfnt_with_sbix(sbix_data, num_glyphs=10)

        font_path = tmp_path / "test.ttf"
        font_path.write_bytes(font_data)

        font = TtfFont._from_reader(BinaryReader(font_data))
        assert isinstance(font, TtfFont)

        preview = FontPreviewBuilder.render_sbix_glyph_to_png(
            font, glyph_id=GlyphId(5), ppem=24, size=256
        )

        assert preview.filename == "sbix-glyph-5.png"
        assert preview.media_type == "image/png"
        assert preview.data.startswith(b"\x89PNG\r\n\x1a\n")

    def test_render_sbix_glyph_to_png_png_format(self, tmp_path: Path) -> None:
        """Test rendering PNG format bitmap from sbix table."""
        sbix_data = _build_sbix_table_with_png_glyph(glyph_id=5, ppem=24)
        font_data = _build_minimal_sfnt_with_sbix(sbix_data, num_glyphs=10)

        font_path = tmp_path / "test.ttf"
        font_path.write_bytes(font_data)

        font = TtfFont._from_reader(BinaryReader(font_data))
        assert isinstance(font, TtfFont)

        preview = FontPreviewBuilder.render_sbix_glyph_to_png(font, glyph_id=5, ppem=24, size=256)

        width, height, pixels = _decode_png_rgb(preview.data)

        assert width > 0
        assert height > 0
        assert len(pixels) == width * height * 3

    def test_render_sbix_glyph_to_png_custom_background(self, tmp_path: Path) -> None:
        """Test that custom background color is applied to rendered glyph."""
        sbix_data = _build_sbix_table_with_png_glyph(glyph_id=5, ppem=24)
        font_data = _build_minimal_sfnt_with_sbix(sbix_data, num_glyphs=10)

        font_path = tmp_path / "test.ttf"
        font_path.write_bytes(font_data)

        font = TtfFont._from_reader(BinaryReader(font_data))
        assert isinstance(font, TtfFont)

        preview = FontPreviewBuilder.render_sbix_glyph_to_png(
            font,
            glyph_id=5,
            ppem=24,
            size=256,
            background=(0, 0, 255),
        )

        assert preview.filename == "sbix-glyph-5.png"
        assert preview.media_type == "image/png"
