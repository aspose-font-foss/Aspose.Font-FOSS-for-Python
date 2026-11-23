"""Tests for CLI sbix dump command (FONT-475)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

CLI = [sys.executable, "-m", "aspose_font.cli"]


def run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        CLI + list(args),
        capture_output=True,
        text=True,
    )


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


def _build_sbix_table_png(glyph_id: int = 5, ppem: int = 24) -> bytes:
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


def _build_sbix_table_multi(glyphs: list[tuple[int, int, bytes]]) -> bytes:
    """Build a minimal sbix table with multiple glyphs.

    Args:
        glyphs: List of (glyph_id, ppem, bitmap_data) tuples.
    """
    strikes: dict[int, list[tuple[int, bytes]]] = {}
    for glyph_id, ppem, bitmap_data in glyphs:
        if ppem not in strikes:
            strikes[ppem] = []
        strikes[ppem].append((glyph_id, bitmap_data))

    stream = b""
    stream += (0).to_bytes(2, "big")  # version = 0
    stream += (0).to_bytes(2, "big")  # flags = 0
    stream += len(strikes).to_bytes(4, "big")

    current_data_offset = 0
    for ppem in sorted(strikes.keys()):
        records = strikes[ppem]
        stream += ppem.to_bytes(2, "big")
        stream += (96).to_bytes(2, "big")
        stream += current_data_offset.to_bytes(4, "big")

        strike_size = 4  # num_glyphs (u32)
        for glyph_id, bitmap_data in records:
            strike_size += 2 + 4 + 2 + 2 + 4 + len(bitmap_data)  # glyph_id + graphic_type + offsets + bitmap_length + bitmap_data
        current_data_offset += strike_size

    for ppem in sorted(strikes.keys()):
        records = strikes[ppem]
        stream += len(records).to_bytes(4, "big")
        for glyph_id, bitmap_data in records:
            stream += glyph_id.to_bytes(2, "big")
            stream += b"png "
            stream += (0).to_bytes(2, "big")
            stream += (0).to_bytes(2, "big")
            stream += len(bitmap_data).to_bytes(4, "big")
            stream += bitmap_data

    return stream


def _build_sbix_table_jpeg(glyph_id: int = 5, ppem: int = 24) -> bytes:
    """Build a minimal sbix table with a JPEG glyph."""
    jpeg_data = b"\xFF\xD8\xFF\xE0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"

    stream = b""
    stream += (0).to_bytes(2, "big")  # version = 0
    stream += (0).to_bytes(2, "big")  # flags = 0
    stream += (1).to_bytes(4, "big")  # num_strikes = 1
    stream += ppem.to_bytes(2, "big")  # ppem
    stream += (96).to_bytes(2, "big")  # resolution = 96
    stream += (0).to_bytes(4, "big")  # offset_to_bitmap_data = 0

    stream += (1).to_bytes(4, "big")  # num_glyphs = 1
    stream += glyph_id.to_bytes(2, "big")  # glyph_id
    stream += b"jpg "  # graphic_type = jpg
    stream += (0).to_bytes(2, "big")  # origin_offset_x = 0
    stream += (0).to_bytes(2, "big")  # origin_offset_y = 0
    stream += len(jpeg_data).to_bytes(4, "big")  # bitmap_data_length
    stream += jpeg_data  # bitmap_data

    return stream


def _build_sbix_table_tiff(glyph_id: int = 5, ppem: int = 24) -> bytes:
    """Build a minimal sbix table with a TIFF glyph."""
    tiff_data = b"\x49\x49\x2A\x00\x08\x00\x00\x00"

    stream = b""
    stream += (0).to_bytes(2, "big")  # version = 0
    stream += (0).to_bytes(2, "big")  # flags = 0
    stream += (1).to_bytes(4, "big")  # num_strikes = 1
    stream += ppem.to_bytes(2, "big")  # ppem
    stream += (96).to_bytes(2, "big")  # resolution = 96
    stream += (0).to_bytes(4, "big")  # offset_to_bitmap_data = 0

    stream += (1).to_bytes(4, "big")  # num_glyphs = 1
    stream += glyph_id.to_bytes(2, "big")  # glyph_id
    stream += b"tiff"  # graphic_type = tiff
    stream += (0).to_bytes(2, "big")  # origin_offset_x = 0
    stream += (0).to_bytes(2, "big")  # origin_offset_y = 0
    stream += len(tiff_data).to_bytes(4, "big")  # bitmap_data_length
    stream += tiff_data  # bitmap_data

    return stream


class TestSbixDumpCommand:
    """Tests for the sbix-dump CLI command."""

    def test_sbix_dump_multi_glyph_extraction(self, tmp_path: Path) -> None:
        """Test extracting multiple PNG glyphs from a font."""
        glyphs = [
            (5, 24, b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIEND\xAE\x42\x60\x82"),
            (7, 24, b"\x89PNG\r\n\x1a\n\x00\x00\x00\x89IDATx\x9c\x62\x60\x60\x60\x60\x00\x00\x00\x04\x00\x01\xF5\xFF\x65\x82"),
        ]
        sbix_data = _build_sbix_table_multi(glyphs)
        font_data = _build_minimal_sfnt_with_sbix(sbix_data)

        font_path = tmp_path / "test.ttf"
        font_path.write_bytes(font_data)

        output_dir = tmp_path / "output"

        result = run("sbix-dump", str(font_path), str(output_dir))

        assert result.returncode == 0
        assert (output_dir / "glyph_5.png").exists()
        assert (output_dir / "glyph_7.png").exists()
        assert (output_dir / "sbix-manifest.json").exists()

        manifest = json.loads((output_dir / "sbix-manifest.json").read_text())
        assert manifest["sbix_version"] == 0
        assert len(manifest["bitmaps"]) == 2
        assert manifest["selected_ppem"] == 24

    def test_sbix_dump_single_glyph_extraction(self, tmp_path: Path) -> None:
        """Test extracting a single glyph using --glyph-id."""
        glyphs = [
            (5, 24, b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIEND\xAE\x42\x60\x82"),
            (7, 24, b"\x89PNG\r\n\x1a\n\x00\x00\x00\x89"),
        ]
        sbix_data = _build_sbix_table_multi(glyphs)
        font_data = _build_minimal_sfnt_with_sbix(sbix_data)

        font_path = tmp_path / "test.ttf"
        font_path.write_bytes(font_data)

        output_dir = tmp_path / "output"

        result = run("sbix-dump", str(font_path), str(output_dir), "--glyph-id", "5")

        assert result.returncode == 0
        assert (output_dir / "glyph_5.png").exists()
        assert not (output_dir / "glyph_7.png").exists()

    def test_sbix_dump_ppem_selection(self, tmp_path: Path) -> None:
        """Test extracting glyphs at specific ppem."""
        glyphs = [
            (5, 16, b"\x89PNG\r\n\x1a\n\x00\x00\x00\rLOW"),
            (5, 24, b"\x89PNG\r\n\x1a\n\x00\x00\x00\rHIGH"),
        ]
        sbix_data = _build_sbix_table_multi(glyphs)
        font_data = _build_minimal_sfnt_with_sbix(sbix_data)

        font_path = tmp_path / "test.ttf"
        font_path.write_bytes(font_data)

        output_dir = tmp_path / "output"

        result = run("sbix-dump", str(font_path), str(output_dir), "--ppem", "16")

        assert result.returncode == 0
        manifest = json.loads((output_dir / "sbix-manifest.json").read_text())
        assert manifest["selected_ppem"] == 16

    def test_sbix_dump_no_sbix_table(self, tmp_path: Path) -> None:
        """Test handling of font without sbix table."""
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

        output_dir = tmp_path / "output"

        result = run("sbix-dump", str(font_path), str(output_dir))

        assert result.returncode == 0
        assert "No sbix table found" in result.stdout

    def test_sbix_dump_invalid_glyph_id(self, tmp_path: Path) -> None:
        """Test handling of non-existent glyph ID."""
        sbix_data = _build_sbix_table_png(glyph_id=5, ppem=24)
        font_data = _build_minimal_sfnt_with_sbix(sbix_data)

        font_path = tmp_path / "test.ttf"
        font_path.write_bytes(font_data)

        output_dir = tmp_path / "output"

        result = run("sbix-dump", str(font_path), str(output_dir), "--glyph-id", "100")

        assert result.returncode == 0
        assert "No sbix bitmap found for glyph ID 100" in result.stdout

    def test_sbix_dump_png_format(self, tmp_path: Path) -> None:
        """Test extracting PNG glyphs."""
        sbix_data = _build_sbix_table_png(glyph_id=5, ppem=24)
        font_data = _build_minimal_sfnt_with_sbix(sbix_data)

        font_path = tmp_path / "test.ttf"
        font_path.write_bytes(font_data)

        output_dir = tmp_path / "output"

        result = run("sbix-dump", str(font_path), str(output_dir))

        assert result.returncode == 0
        assert (output_dir / "glyph_5.png").exists()

    def test_sbix_dump_jpeg_format(self, tmp_path: Path) -> None:
        """Test extracting JPEG glyphs."""
        sbix_data = _build_sbix_table_jpeg(glyph_id=5, ppem=24)
        font_data = _build_minimal_sfnt_with_sbix(sbix_data)

        font_path = tmp_path / "test.ttf"
        font_path.write_bytes(font_data)

        output_dir = tmp_path / "output"

        result = run("sbix-dump", str(font_path), str(output_dir))

        assert result.returncode == 0
        assert (output_dir / "glyph_5.jpg").exists()

    def test_sbix_dump_tiff_format(self, tmp_path: Path) -> None:
        """Test extracting TIFF glyphs."""
        sbix_data = _build_sbix_table_tiff(glyph_id=5, ppem=24)
        font_data = _build_minimal_sfnt_with_sbix(sbix_data)

        font_path = tmp_path / "test.ttf"
        font_path.write_bytes(font_data)

        output_dir = tmp_path / "output"

        result = run("sbix-dump", str(font_path), str(output_dir))

        assert result.returncode == 0
        assert (output_dir / "glyph_5.tif").exists()

    def test_sbix_dump_manifest_content(self, tmp_path: Path) -> None:
        """Test manifest JSON contains correct metadata."""
        sbix_data = _build_sbix_table_png(glyph_id=5, ppem=24)
        font_data = _build_minimal_sfnt_with_sbix(sbix_data)

        font_path = tmp_path / "test.ttf"
        font_path.write_bytes(font_data)

        output_dir = tmp_path / "output"

        result = run("sbix-dump", str(font_path), str(output_dir))

        assert result.returncode == 0

        manifest = json.loads((output_dir / "sbix-manifest.json").read_text())
        assert "font" in manifest
        assert manifest["sbix_version"] == 0
        assert manifest["selected_ppem"] == 24
        assert "available_strikes" in manifest
        assert len(manifest["bitmaps"]) == 1
        assert manifest["bitmaps"][0]["glyph_id"] == 5
        assert manifest["bitmaps"][0]["ppem"] == 24
        assert manifest["bitmaps"][0]["filename"] == "glyph_5.png"

    def test_sbix_dump_auto_create_output_dir(self, tmp_path: Path) -> None:
        """Test output directory is auto-created."""
        sbix_data = _build_sbix_table_png(glyph_id=5, ppem=24)
        font_data = _build_minimal_sfnt_with_sbix(sbix_data)

        font_path = tmp_path / "test.ttf"
        font_path.write_bytes(font_data)

        output_dir = tmp_path / "nested" / "output" / "dir"

        result = run("sbix-dump", str(font_path), str(output_dir))

        assert result.returncode == 0
        assert output_dir.exists()
        assert (output_dir / "glyph_5.png").exists()
        assert (output_dir / "sbix-manifest.json").exists()
