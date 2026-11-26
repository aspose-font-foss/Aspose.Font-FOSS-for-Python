"""Tests for SVG to PNG preview feature (FONT-462)."""

from __future__ import annotations

import gzip
import subprocess
import sys
from pathlib import Path

from aspose_font import CffFont
from aspose_font._types import GlyphId
from aspose_font.loader import FontLoader
from aspose_font.preview import FontPreviewBuilder, PreviewImage
from aspose_font.ttf.font import TtfFont

CLI = [sys.executable, "-m", "aspose_font.cli"]


def run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        CLI + list(args),
        capture_output=True,
        text=True,
    )


def _build_minimal_sfnt_with_svg(svg_data: bytes, units_per_em: int = 2048) -> bytes:
    """Build a minimal SFNT font with SVG table."""
    # Build head table with proper values
    head = (
        (1).to_bytes(2, "big")  # major_version
        + (0).to_bytes(2, "big")  # minor_version
        + (0x00010000).to_bytes(4, "big")  # font_revision
        + (0).to_bytes(4, "big")  # checksum_adjustment
        + (0x5F0F3CF5).to_bytes(4, "big")  # magic number
        + (0).to_bytes(2, "big")  # flags
        + units_per_em.to_bytes(2, "big")  # units_per_em
        + (0).to_bytes(8, "big")  # created
        + (0).to_bytes(8, "big")  # modified
        + (0xFF9C).to_bytes(2, "big")  # x_min = -100 as signed 16-bit
        + (0xFF38).to_bytes(2, "big")  # y_min = -200 as signed 16-bit
        + (0x03E8).to_bytes(2, "big")  # x_max = 1000 as unsigned 16-bit
        + (0x0384).to_bytes(2, "big")  # y_max = 900 as unsigned 16-bit
        + (0).to_bytes(2, "big")  # mac_style
        + (8).to_bytes(2, "big")  # lowest_rec_ppem
        + (2).to_bytes(2, "big")  # font_direction_hint
        + (0).to_bytes(2, "big")  # index_to_loc_format
        + (0).to_bytes(2, "big")  # glyph_data_format
    )

    maxp = (0x00010000).to_bytes(4, "big") + (1).to_bytes(2, "big") + bytes(26)

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

    directory = (
        b"head"
        + (0).to_bytes(4, "big")
        + head_offset.to_bytes(4, "big")
        + len(head).to_bytes(4, "big")
        + b"maxp"
        + (0).to_bytes(4, "big")
        + maxp_offset.to_bytes(4, "big")
        + len(maxp).to_bytes(4, "big")
        + b"SVG "
        + (0).to_bytes(4, "big")
        + (maxp_offset + len(maxp)).to_bytes(4, "big")
        + len(svg_data).to_bytes(4, "big")
    )

    result = offset_table + directory + head + maxp + svg_data
    return result


def _build_svg_table(svg_xml: bytes, glyph_id: int = 5) -> bytes:
    """Build a minimal SVG table with a single document."""
    stream = bytes()
    stream += b"\x00\x01"
    stream += b"\x00\x00\x00\x0A"
    stream += b"\x00\x00\x00\x00"
    stream += b"\x00\x01"

    stream += glyph_id.to_bytes(2, "big")
    stream += glyph_id.to_bytes(2, "big")
    stream += (18).to_bytes(4, "big")
    stream += len(svg_xml).to_bytes(4, "big")
    stream += b"\x00\x00\x00\x02"

    stream += svg_xml

    return stream


def _build_svg_table_gzip(svg_xml: bytes, glyph_id: int = 5) -> bytes:
    """Build a minimal SVG table with gzip-compressed document."""
    stream = bytes()
    stream += b"\x00\x01"
    stream += b"\x00\x00\x00\x0A"
    stream += b"\x00\x00\x00\x00"
    stream += b"\x00\x01"

    compressed = gzip.compress(svg_xml)

    stream += glyph_id.to_bytes(2, "big")
    stream += glyph_id.to_bytes(2, "big")
    stream += (18).to_bytes(4, "big")
    stream += len(compressed).to_bytes(4, "big")
    stream += b"\x00\x00\x00\x01"

    stream += compressed

    return stream


class TestRenderSvgGlyphToPng:
    """Tests for FontPreviewBuilder.render_svg_glyph_to_png method."""

    def test_render_svg_glyph_to_png_returns_png_bytes(self, tmp_path: Path) -> None:
        """Test that render_svg_glyph_to_png returns valid PNG bytes for a font with SVG table."""
        svg_xml = b'<?xml version="1.0"?><svg><path d="M100 100 L200 200 Z"/></svg>'
        svg_table = _build_svg_table(svg_xml, glyph_id=5)
        font_data = _build_minimal_sfnt_with_svg(svg_table)

        font_path = tmp_path / "test.ttf"
        font_path.write_bytes(font_data)

        font = FontLoader.open(font_path)
        assert isinstance(font, TtfFont)

        preview = FontPreviewBuilder.render_svg_glyph_to_png(font, glyph_id=5, size=256)

        assert isinstance(preview, PreviewImage)
        assert preview.filename == "svg-glyph-5.png"
        assert preview.media_type == "image/png"
        assert preview.data.startswith(b"\x89PNG\r\n\x1a\n")

    def test_render_svg_glyph_to_png_handles_missing_svg_table(
        self, tmp_path: Path
    ) -> None:
        """Test that missing SVG table returns fallback preview."""
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

        font = FontLoader.open(font_path)

        preview = FontPreviewBuilder.render_svg_glyph_to_png(font, glyph_id=5, size=256)

        assert isinstance(preview, PreviewImage)
        assert preview.filename == "svg-glyph-5.png"
        assert preview.media_type == "image/png"
        assert preview.data.startswith(b"\x89PNG\r\n\x1a\n")

    def test_render_svg_glyph_to_png_handles_missing_glyph(self, tmp_path: Path) -> None:
        """Test that missing glyph ID returns fallback preview."""
        svg_xml = b'<?xml version="1.0"?><svg><path d="M100 100 L200 200 Z"/></svg>'
        svg_table = _build_svg_table(svg_xml, glyph_id=5)
        font_data = _build_minimal_sfnt_with_svg(svg_table, units_per_em=2048)

        font_path = tmp_path / "test.ttf"
        font_path.write_bytes(font_data)

        font = FontLoader.open(font_path)
        assert isinstance(font, TtfFont)

        preview = FontPreviewBuilder.render_svg_glyph_to_png(font, glyph_id=100, size=256)

        assert isinstance(preview, PreviewImage)
        assert preview.filename == "svg-glyph-100.png"

    def test_render_svg_glyph_to_png_with_various_sizes(self, tmp_path: Path) -> None:
        """Test rendering with different size parameters."""
        svg_xml = b'<?xml version="1.0"?><svg><path d="M100 100 L200 200 Z"/></svg>'
        svg_table = _build_svg_table(svg_xml, glyph_id=5)
        font_data = _build_minimal_sfnt_with_svg(svg_table, units_per_em=2048)

        font_path = tmp_path / "test.ttf"
        font_path.write_bytes(font_data)

        font = FontLoader.open(font_path)
        assert isinstance(font, TtfFont)

        for size in [128, 256, 512]:
            preview = FontPreviewBuilder.render_svg_glyph_to_png(
                font, glyph_id=5, size=size
            )
            assert isinstance(preview, PreviewImage)
            assert preview.filename == "svg-glyph-5.png"

    def test_render_svg_glyph_to_png_gzip_compressed(self, tmp_path: Path) -> None:
        """Test rendering with gzip-compressed SVG format."""
        svg_xml = b'<?xml version="1.0"?><svg><path d="M100 100 L200 200 Z"/></svg>'
        svg_table = _build_svg_table_gzip(svg_xml, glyph_id=5)
        font_data = _build_minimal_sfnt_with_svg(svg_table, units_per_em=2048)

        font_path = tmp_path / "test.ttf"
        font_path.write_bytes(font_data)

        font = FontLoader.open(font_path)
        assert isinstance(font, TtfFont)

        preview = FontPreviewBuilder.render_svg_glyph_to_png(font, glyph_id=5, size=256)

        assert isinstance(preview, PreviewImage)
        assert preview.filename == "svg-glyph-5.png"
        assert preview.media_type == "image/png"
        assert preview.data.startswith(b"\x89PNG\r\n\x1a\n")

    def test_render_svg_glyph_to_png_with_glyph_id_object(
        self, tmp_path: Path
    ) -> None:
        """Test that GlyphId object works as glyph_id parameter."""
        svg_xml = b'<?xml version="1.0"?><svg><path d="M100 100 L200 200 Z"/></svg>'
        svg_table = _build_svg_table(svg_xml, glyph_id=5)
        font_data = _build_minimal_sfnt_with_svg(svg_table, units_per_em=2048)

        font_path = tmp_path / "test.ttf"
        font_path.write_bytes(font_data)

        font = FontLoader.open(font_path)
        assert isinstance(font, TtfFont)

        preview = FontPreviewBuilder.render_svg_glyph_to_png(
            font, glyph_id=GlyphId(5), size=256
        )

        assert isinstance(preview, PreviewImage)
        assert preview.filename == "svg-glyph-5.png"

    def test_render_svg_glyph_to_png_non_ttf_font(
        self, tmp_path: Path, opensans_cff: CffFont
    ) -> None:
        """Test that non-TTF font raises FontNotSupportedException."""
        from aspose_font._exceptions import FontNotSupportedException

        try:
            FontPreviewBuilder.render_svg_glyph_to_png(opensans_cff, glyph_id=5, size=256)
            assert False, "Expected FontNotSupportedException"
        except FontNotSupportedException as exc:
            assert "TTF font" in str(exc)


class TestSvgPreviewCommand:
    """Tests for the svg-preview CLI command."""

    def test_cli_svg_preview_writes_png_file(self, tmp_path: Path) -> None:
        """Test that svg-preview CLI command writes PNG file."""
        svg_xml = b'<?xml version="1.0"?><svg><path d="M100 100 L200 200 Z"/></svg>'
        svg_table = _build_svg_table(svg_xml, glyph_id=5)
        font_data = _build_minimal_sfnt_with_svg(svg_table, units_per_em=2048)

        font_path = tmp_path / "test.ttf"
        font_path.write_bytes(font_data)

        import os
        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            result = run("svg-preview", str(font_path), "5")

            assert result.returncode == 0
            output_file = tmp_path / "glyph_5.png"
            assert output_file.exists()
        finally:
            os.chdir(original_cwd)
        assert output_file.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")

    def test_cli_svg_preview_no_svg_table(self, tmp_path: Path) -> None:
        """Test handling of font without SVG table."""
        head = bytes(12) + (0x5F0F3CF5).to_bytes(4, "big") + bytes(54 - 16)
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

        result = run("svg-preview", str(font_path), "5")

        assert result.returncode == 0
        assert "No SVG table found" in result.stdout

    def test_cli_svg_preview_invalid_glyph(self, tmp_path: Path) -> None:
        """Test handling of non-existent glyph ID."""
        svg_xml = b'<?xml version="1.0"?><svg><path d="M100 100 L200 200 Z"/></svg>'
        svg_table = _build_svg_table(svg_xml, glyph_id=5)
        font_data = _build_minimal_sfnt_with_svg(svg_table, units_per_em=2048)

        font_path = tmp_path / "test.ttf"
        font_path.write_bytes(font_data)

        result = run("svg-preview", str(font_path), "100")

        assert result.returncode == 0
        assert "No SVG document found for glyph ID 100" in result.stdout

    def test_cli_svg_preview_custom_size(self, tmp_path: Path) -> None:
        """Test svg-preview with custom --size parameter."""
        svg_xml = b'<?xml version="1.0"?><svg><path d="M100 100 L200 200 Z"/></svg>'
        svg_table = _build_svg_table(svg_xml, glyph_id=5)
        font_data = _build_minimal_sfnt_with_svg(svg_table, units_per_em=2048)

        font_path = tmp_path / "test.ttf"
        font_path.write_bytes(font_data)

        import os
        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            result = run("svg-preview", str(font_path), "5", "--size", "512")

            assert result.returncode == 0
            output_file = tmp_path / "glyph_5.png"
            assert output_file.exists()
        finally:
            os.chdir(original_cwd)

    def test_cli_svg_preview_invalid_font_type(self, tmp_path: Path) -> None:
        """Test svg-preview with invalid font file."""
        font_path = tmp_path / "invalid.ttf"
        font_path.write_bytes(b"invalid font data")

        result = run("svg-preview", str(font_path), "5")

        assert result.returncode != 0
