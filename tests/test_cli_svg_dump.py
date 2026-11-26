"""Tests for CLI SVG dump command (FONT-458)."""

from __future__ import annotations

import gzip
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


def _build_minimal_sfnt(version: bytes, svg_data: bytes | None = None) -> bytes:
    """Build a minimal SFNT font with optional SVG table."""
    head = bytes(12) + (0x5F0F3CF5).to_bytes(4, "big") + bytes(54 - 16)
    maxp = (0x00010000).to_bytes(4, "big") + (1).to_bytes(2, "big") + bytes(26)

    num_tables = 2 if svg_data is None else 3
    offset_table = (
        version
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

    if svg_data is not None:
        svg_offset = maxp_offset + len(maxp)
        directory += (
            b"SVG "
            + (0).to_bytes(4, "big")
            + svg_offset.to_bytes(4, "big")
            + len(svg_data).to_bytes(4, "big")
        )

    result = offset_table + directory + head + maxp
    if svg_data is not None:
        result += svg_data

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


def _build_svg_table_multi(records: list[tuple[int, int, bytes]]) -> bytes:
    """Build a minimal SVG table with multiple document records.

    Args:
        records: List of (start_glyph_id, end_glyph_id, svg_xml) tuples.
    """
    stream = bytes()
    stream += b"\x00\x01"  # version
    stream += b"\x00\x00\x00\x0A"  # offset to document list = 10
    stream += b"\x00\x00\x00\x00"  # reserved
    stream += len(records).to_bytes(2, "big")  # numEntries

    # Calculate offsets
    doc_list_start = 10
    current_offset = doc_list_start + len(records) * 16  # 16 bytes per record

    for start_gid, end_gid, svg_xml in records:
        stream += start_gid.to_bytes(2, "big")
        stream += end_gid.to_bytes(2, "big")
        stream += (current_offset - doc_list_start).to_bytes(4, "big")
        stream += len(svg_xml).to_bytes(4, "big")
        stream += b"\x00\x00\x00\x02"
        current_offset += len(svg_xml)

    for _, _, svg_xml in records:
        stream += svg_xml

    return stream


class TestSvgDumpCommand:
    """Tests for the svg-dump CLI command."""

    def test_svg_dump_multi_glyph_extraction(self, tmp_path: Path) -> None:
        """Test extracting multiple SVG glyphs from a font."""
        svg1 = b'<?xml version="1.0"?><svg id="glyph5"></svg>'
        svg2 = b'<?xml version="1.0"?><svg id="glyph6"></svg>'

        # Two separate records: glyph 5 and glyph 6
        svg_table = _build_svg_table_multi([
            (5, 5, svg1),
            (6, 6, svg2),
        ])
        font_data = _build_minimal_sfnt(b"\x00\x01\x00\x00", svg_table)

        font_path = tmp_path / "test.ttf"
        font_path.write_bytes(font_data)

        output_dir = tmp_path / "output"

        result = run("svg-dump", str(font_path), str(output_dir))

        assert result.returncode == 0
        assert (output_dir / "glyph_5.svg").exists()
        assert (output_dir / "glyph_6.svg").exists()
        assert (output_dir / "svg-manifest.json").exists()

        manifest = json.loads((output_dir / "svg-manifest.json").read_text())
        assert manifest["svg_table_version"] == 1
        assert len(manifest["documents"]) == 2

    def test_svg_dump_single_glyph_extraction(self, tmp_path: Path) -> None:
        """Test extracting a single SVG glyph using --glyph-id."""
        svg_xml = b'<?xml version="1.0"?><svg id="glyph5"></svg>'

        svg_table = _build_svg_table(svg_xml, glyph_id=5)
        font_data = _build_minimal_sfnt(b"\x00\x01\x00\x00", svg_table)

        font_path = tmp_path / "test.ttf"
        font_path.write_bytes(font_data)

        output_dir = tmp_path / "output"

        result = run("svg-dump", str(font_path), str(output_dir), "--glyph-id", "5")

        assert result.returncode == 0
        assert (output_dir / "glyph_5.svg").exists()
        assert not (output_dir / "glyph_6.svg").exists()

        svg_content = (output_dir / "glyph_5.svg").read_text()
        assert 'id="glyph5"' in svg_content

    def test_svg_dump_no_svg_table(self, tmp_path: Path) -> None:
        """Test handling of font without SVG table."""
        font_data = _build_minimal_sfnt(b"\x00\x01\x00\x00")

        font_path = tmp_path / "test.ttf"
        font_path.write_bytes(font_data)

        output_dir = tmp_path / "output"

        result = run("svg-dump", str(font_path), str(output_dir))

        assert result.returncode == 0
        assert "No SVG table found" in result.stdout
        assert not (output_dir / "svg-manifest.json").exists()

    def test_svg_dump_invalid_glyph_id(self, tmp_path: Path) -> None:
        """Test handling of non-existent glyph ID."""
        svg_xml = b'<?xml version="1.0"?><svg id="glyph5"></svg>'

        svg_table = _build_svg_table(svg_xml, glyph_id=5)
        font_data = _build_minimal_sfnt(b"\x00\x01\x00\x00", svg_table)

        font_path = tmp_path / "test.ttf"
        font_path.write_bytes(font_data)

        output_dir = tmp_path / "output"

        result = run("svg-dump", str(font_path), str(output_dir), "--glyph-id", "100")

        assert result.returncode == 0
        assert "No SVG document found for glyph ID 100" in result.stdout

    def test_svg_dump_gzip_compressed(self, tmp_path: Path) -> None:
        """Test extracting gzip-compressed SVG documents."""
        svg_xml = b'<?xml version="1.0"?><svg id="compressed"></svg>'
        compressed_svg = gzip.compress(svg_xml)

        stream = bytes()
        stream += b"\x00\x01"
        stream += b"\x00\x00\x00\x0A"
        stream += b"\x00\x00\x00\x00"
        stream += b"\x00\x01"

        stream += b"\x00\x05"
        stream += b"\x00\x05"
        stream += (18).to_bytes(4, "big")
        stream += len(compressed_svg).to_bytes(4, "big")
        stream += b"\x00\x00\x00\x01"

        stream += compressed_svg

        svg_table = stream
        font_data = _build_minimal_sfnt(b"\x00\x01\x00\x00", svg_table)

        font_path = tmp_path / "test.ttf"
        font_path.write_bytes(font_data)

        output_dir = tmp_path / "output"

        result = run("svg-dump", str(font_path), str(output_dir))

        assert result.returncode == 0
        assert (output_dir / "glyph_5.svg").exists()

        svg_content = (output_dir / "glyph_5.svg").read_text()
        assert 'id="compressed"' in svg_content

    def test_svg_dump_empty_table(self, tmp_path: Path) -> None:
        """Test handling of SVG table with no documents."""
        stream = bytes()
        stream += b"\x00\x01"
        stream += b"\x00\x00\x00\x0A"
        stream += b"\x00\x00\x00\x00"
        stream += b"\x00\x00"

        svg_table = stream
        font_data = _build_minimal_sfnt(b"\x00\x01\x00\x00", svg_table)

        font_path = tmp_path / "test.ttf"
        font_path.write_bytes(font_data)

        output_dir = tmp_path / "output"

        result = run("svg-dump", str(font_path), str(output_dir))

        assert result.returncode == 0
        assert (output_dir / "svg-manifest.json").exists()

        manifest = json.loads((output_dir / "svg-manifest.json").read_text())
        assert manifest["documents"] == []
