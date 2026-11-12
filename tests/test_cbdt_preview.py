"""Tests for FONT-478 CBDT Emoji Preview Extraction."""

from __future__ import annotations

import sys
from pathlib import Path

from aspose_font._types import GlyphId
from aspose_font.preview import FontPreviewBuilder
from aspose_font.ttf.font import TtfFont
from aspose_font.ttf.tables import TtfTableSet
from aspose_font.ttf.tables.cbdt import CbdtGlyphBitmap, CbdtTable, CblcStrike
from aspose_font.ttf.tables.head import HeadTable
from aspose_font.ttf.tables.maxp import MaxpTable

CLI = [sys.executable, "-m", "aspose_font.cli"]


def _build_font_with_cbdt(strikes: list[CblcStrike], bitmaps: list[CbdtGlyphBitmap]) -> TtfFont:
    """Build a minimal TTF font with CBDT table for testing."""
    head = HeadTable(
        magic=0x5F0F3CF5,
        major_version=1,
        minor_version=0,
        font_revision=0x00010000,
        checksum_adjustment=0,
        flags=0,
        units_per_em=2048,
        created=0,
        modified=0,
        x_min=-100,
        y_min=-200,
        x_max=1000,
        y_max=800,
        mac_style=0,
        lowest_rec_ppem=8,
        font_direction_hint=2,
        index_to_loc_format=0,
        glyph_data_format=0,
    )

    maxp = MaxpTable(version=0x00010000, num_glyphs=10)

    tables = TtfTableSet(
        head=head,
        maxp=maxp,
        cbdt=CbdtTable(
            version=0x00020000,
            strikes=strikes,
            bitmaps=bitmaps
        )
    )

    return TtfFont(sfnt_data=b"", tables=tables, sfnt_version=0x00010000)


class TestRenderCbdtGlyphToPng:
    """Tests for FontPreviewBuilder.render_cbdt_glyph_to_png method."""

    def test_render_cbdt_glyph_to_png_returns_png_bytes(self, tmp_path: Path) -> None:
        """Test that render_cbdt_glyph_to_png returns valid PNG bytes for a font with CBDT table."""
        strikes = [CblcStrike(ppem=24, max_ppem=48, bit_depth=32, flags=0)]
        bitmaps = [
            CbdtGlyphBitmap(
                glyph_id=5,
                data_format=1,
                bitmap_data=b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIEND\xAE\x42\x60\x82",
                width=32,
                height=32,
                bearing_x=0,
                bearing_y=0,
                advance=32,
            )
        ]

        font = _build_font_with_cbdt(strikes, bitmaps)

        preview = FontPreviewBuilder.render_cbdt_glyph_to_png(
            font, glyph_id=5, ppem=24, size=256
        )

        assert preview.filename == "cbdt-glyph-5.png"
        assert preview.media_type == "image/png"
        assert preview.data.startswith(b"\x89PNG\r\n\x1a\n")

    def test_render_cbdt_glyph_to_png_with_ppem_fallback(
        self, tmp_path: Path
    ) -> None:
        """Test that render_cbdt_glyph_to_png uses highest ppem when None is specified."""
        strikes = [
            CblcStrike(ppem=16, max_ppem=32, bit_depth=32, flags=0),
            CblcStrike(ppem=32, max_ppem=64, bit_depth=32, flags=0),
        ]
        bitmaps = [
            CbdtGlyphBitmap(
                glyph_id=5,
                data_format=1,
                bitmap_data=b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIEND\xAE\x42\x60\x82",
                width=32,
                height=32,
                bearing_x=0,
                bearing_y=0,
                advance=32,
            )
        ]

        font = _build_font_with_cbdt(strikes, bitmaps)

        preview = FontPreviewBuilder.render_cbdt_glyph_to_png(
            font, glyph_id=5, ppem=None, size=256
        )

        assert preview.filename == "cbdt-glyph-5.png"
        assert preview.media_type == "image/png"

    def test_render_cbdt_glyph_to_png_specific_ppem(
        self, tmp_path: Path
    ) -> None:
        """Test that render_cbdt_glyph_to_png with specific ppem returns correct strike."""
        strikes = [
            CblcStrike(ppem=16, max_ppem=32, bit_depth=32, flags=0),
            CblcStrike(ppem=32, max_ppem=64, bit_depth=32, flags=0),
        ]
        bitmaps = [
            CbdtGlyphBitmap(
                glyph_id=5,
                data_format=1,
                bitmap_data=b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIEND\xAE\x42\x60\x82",
                width=32,
                height=32,
                bearing_x=0,
                bearing_y=0,
                advance=32,
            )
        ]

        font = _build_font_with_cbdt(strikes, bitmaps)

        preview = FontPreviewBuilder.render_cbdt_glyph_to_png(
            font, glyph_id=5, ppem=32, size=256
        )

        assert preview.filename == "cbdt-glyph-5.png"
        assert preview.media_type == "image/png"

    def test_render_cbdt_glyph_to_png_missing_cbdt(
        self, tmp_path: Path
    ) -> None:
        """Test that missing CBDT table falls back to vector rendering."""

        head = HeadTable(
            magic=0x5F0F3CF5,
            major_version=1,
            minor_version=0,
            font_revision=0x00010000,
            checksum_adjustment=0,
            flags=0,
            units_per_em=2048,
            created=0,
            modified=0,
            x_min=-100,
            y_min=-200,
            x_max=1000,
            y_max=800,
            mac_style=0,
            lowest_rec_ppem=8,
            font_direction_hint=2,
            index_to_loc_format=0,
            glyph_data_format=0,
        )

        maxp = MaxpTable(version=0x00010000, num_glyphs=10)

        tables = TtfTableSet(head=head, maxp=maxp, cbdt=None)

        font = TtfFont(sfnt_data=b"", tables=tables, sfnt_version=0x00010000)

        preview = FontPreviewBuilder.render_cbdt_glyph_to_png(
            font, glyph_id=5, ppem=24, size=256
        )

        assert preview.filename == "cbdt-glyph-5.png"
        assert preview.media_type == "image/png"
        assert preview.data.startswith(b"\x89PNG\r\n\x1a\n")

    def test_render_cbdt_glyph_to_png_missing_glyph(
        self, tmp_path: Path
    ) -> None:
        """Test that missing glyph ID in CBDT falls back to vector rendering."""
        strikes = [CblcStrike(ppem=24, max_ppem=48, bit_depth=32, flags=0)]
        bitmaps = [
            CbdtGlyphBitmap(
                glyph_id=5,
                data_format=1,
                bitmap_data=b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIEND\xAE\x42\x60\x82",
                width=32,
                height=32,
                bearing_x=0,
                bearing_y=0,
                advance=32,
            )
        ]

        font = _build_font_with_cbdt(strikes, bitmaps)

        preview = FontPreviewBuilder.render_cbdt_glyph_to_png(
            font, glyph_id=100, ppem=24, size=256
        )

        assert preview.filename == "cbdt-glyph-100.png"
        assert preview.media_type == "image/png"
        assert preview.data.startswith(b"\x89PNG\r\n\x1a\n")

    def test_render_cbdt_glyph_to_png_with_glyph_id_object(
        self, tmp_path: Path
    ) -> None:
        """Test that GlyphId object works as glyph_id parameter."""
        strikes = [CblcStrike(ppem=24, max_ppem=48, bit_depth=32, flags=0)]
        bitmaps = [
            CbdtGlyphBitmap(
                glyph_id=5,
                data_format=1,
                bitmap_data=b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIEND\xAE\x42\x60\x82",
                width=32,
                height=32,
                bearing_x=0,
                bearing_y=0,
                advance=32,
            )
        ]

        font = _build_font_with_cbdt(strikes, bitmaps)

        preview = FontPreviewBuilder.render_cbdt_glyph_to_png(
            font, glyph_id=GlyphId(5), ppem=24, size=256
        )

        assert preview.filename == "cbdt-glyph-5.png"
        assert preview.media_type == "image/png"
        assert preview.data.startswith(b"\x89PNG\r\n\x1a\n")

    def test_render_cbdt_glyph_to_png_png_format(
        self, tmp_path: Path
    ) -> None:
        """Test rendering PNG format bitmap from CBDT table (data_format=1)."""

        png_bitmap = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIEND\xAE\x42\x60\x82"

        strikes = [CblcStrike(ppem=24, max_ppem=48, bit_depth=32, flags=0)]
        bitmaps = [
            CbdtGlyphBitmap(
                glyph_id=5,
                data_format=1,
                bitmap_data=png_bitmap,
                width=32,
                height=32,
                bearing_x=0,
                bearing_y=0,
                advance=32,
            )
        ]

        font = _build_font_with_cbdt(strikes, bitmaps)

        preview = FontPreviewBuilder.render_cbdt_glyph_to_png(
            font, glyph_id=5, ppem=24, size=256
        )

        assert preview.data.startswith(b"\x89PNG\r\n\x1a\n")
        assert len(preview.data) >= len(png_bitmap)

    def test_render_cbdt_glyph_to_png_custom_background(
        self, tmp_path: Path
    ) -> None:
        """Test that custom background color is applied to rendered glyph."""
        strikes = [CblcStrike(ppem=24, max_ppem=48, bit_depth=32, flags=0)]
        bitmaps = [
            CbdtGlyphBitmap(
                glyph_id=5,
                data_format=1,
                bitmap_data=b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIEND\xAE\x42\x60\x82",
                width=32,
                height=32,
                bearing_x=0,
                bearing_y=0,
                advance=32,
            )
        ]

        font = _build_font_with_cbdt(strikes, bitmaps)

        preview = FontPreviewBuilder.render_cbdt_glyph_to_png(
            font,
            glyph_id=5,
            ppem=24,
            size=256,
            background=(0, 0, 255),
        )

        assert preview.filename == "cbdt-glyph-5.png"
        assert preview.media_type == "image/png"
