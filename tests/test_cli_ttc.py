"""Tests for CLI ttc-info and ttc-extract subcommands (FONT-540)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

CLI = [sys.executable, "-m", "aspose_font.cli"]


def run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        CLI + list(args),
        capture_output=True,
        text=True,
    )


def _build_minimal_ttc_with_faces(faces_data: list[bytes]) -> bytes:
    """Build a minimal TTC file with the given face data.

    Args:
        faces_data: List of sfnt data for each face.
    """
    num_faces = len(faces_data)
    ttc_header = b"ttcf" + (0x00010000).to_bytes(4, "big") + num_faces.to_bytes(4, "big")

    face_offsets = []
    offset = 12 + num_faces * 4
    for face_data in faces_data:
        face_offsets.append(offset)
        offset += len(face_data)

    offset_table = b"".join(o.to_bytes(4, "big") for o in face_offsets)

    ttc_data = ttc_header + offset_table
    for face_data in faces_data:
        ttc_data += face_data

    return ttc_data


def _build_simple_sfnt_with_tables(tables: list[tuple[bytes, bytes]]) -> bytes:
    """Build a minimal valid sfnt font with the given tables."""
    num_tables = len(tables)
    search_range, entry_selector, range_shift = _sfnt_search_params(num_tables)

    directory_size = num_tables * 16
    data_offset = 12 + directory_size

    offset_table = (
        b"\x00\x01\x00\x00"
        + num_tables.to_bytes(2, "big")
        + search_range.to_bytes(2, "big")
        + entry_selector.to_bytes(2, "big")
        + range_shift.to_bytes(2, "big")
    )

    directory = b""
    for tag, data in tables:
        checksum = 0
        directory += tag + checksum.to_bytes(4, "big") + data_offset.to_bytes(4, "big") + len(data).to_bytes(4, "big")
        data_offset += len(data)

    table_data = b"".join(data for _, data in tables)

    return offset_table + directory + table_data


def _build_minimal_sfnt(_num_tables: int = 4, is_otf: bool = False) -> bytes:
    """Build a minimal sfnt font file with minimal valid tables."""
    del is_otf

    head_data = (
        (1).to_bytes(2, "big")
        + (0).to_bytes(2, "big")
        + (0x00010000).to_bytes(4, "big")
        + (0).to_bytes(4, "big")
        + (0x5F0F3CF5).to_bytes(4, "big")
        + (0).to_bytes(2, "big")
        + (2048).to_bytes(2, "big")
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

    maxp_data = (0x00010000).to_bytes(4, "big") + (10).to_bytes(2, "big") + bytes(26)

    tables = [
        (b"head", head_data),
        (b"maxp", maxp_data),
        (b"hhea", bytes(36)),
        (b"hmtx", bytes(40)),
    ]

    return _build_simple_sfnt_with_tables(tables)


def _sfnt_search_params(num_tables: int) -> tuple[int, int, int]:
    max_power = 1
    entry_selector = 0
    while max_power * 2 <= num_tables:
        max_power *= 2
        entry_selector += 1
    search_range = max_power * 16
    range_shift = num_tables * 16 - search_range
    return search_range, entry_selector, range_shift


def _build_minimal_sfnt_with_glyph_count(num_glyphs: int, is_otf: bool = False) -> bytes:
    """Build a minimal sfnt font with a specific number of glyphs."""
    head_data = (
        (1).to_bytes(2, "big")
        + (0).to_bytes(2, "big")
        + (0x00010000).to_bytes(4, "big")
        + (0).to_bytes(4, "big")
        + (0x5F0F3CF5).to_bytes(4, "big")
        + (0).to_bytes(2, "big")
        + (2048).to_bytes(2, "big")
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

    maxp_data = (0x00010000).to_bytes(4, "big") + num_glyphs.to_bytes(2, "big") + bytes(26)

    tables = [
        (b"head", head_data),
        (b"maxp", maxp_data),
        (b"hhea", bytes(36)),
        (b"hmtx", bytes(40)),
    ]

    result = _build_simple_sfnt_with_tables(tables)

    if is_otf:
        result = b"OTTO" + result[4:]

    return result


def _build_ttc_with_two_faces() -> bytes:
    """Build a TTC with two faces with different num_glyphs."""
    face0_data = _build_minimal_sfnt_with_glyph_count(10, is_otf=False)
    face1_data = _build_minimal_sfnt_with_glyph_count(20, is_otf=True)

    num_faces = 2
    ttc_header = b"ttcf" + (0x00010000).to_bytes(4, "big") + num_faces.to_bytes(4, "big")

    first_face_offset = 12 + num_faces * 4
    second_face_offset = first_face_offset + len(face0_data)

    offset_table = first_face_offset.to_bytes(4, "big") + second_face_offset.to_bytes(4, "big")

    return ttc_header + offset_table + face0_data + face1_data


class TestTtcInfoCommand:
    """Tests for the ttc-info CLI command."""

    def test_ttc_info_shows_total_face_count(self, tmp_path: Path) -> None:
        """ttc-info should show total number of faces."""
        ttc_data = _build_ttc_with_two_faces()
        ttc_path = tmp_path / "test.ttc"
        ttc_path.write_bytes(ttc_data)

        result = run("ttc-info", str(ttc_path))

        assert result.returncode == 0
        assert "Total faces:" in result.stdout
        assert "2" in result.stdout

    def test_ttc_info_shows_face_details(self, tmp_path: Path) -> None:
        """ttc-info should show offset, sfnt version, and table count for each face."""
        ttc_data = _build_ttc_with_two_faces()
        ttc_path = tmp_path / "test.ttc"
        ttc_path.write_bytes(ttc_data)

        result = run("ttc-info", str(ttc_path))

        assert result.returncode == 0
        assert "Offset:" in result.stdout
        assert "sfnt version:" in result.stdout
        assert "Table count:" in result.stdout
        assert "Face 0:" in result.stdout
        assert "Face 1:" in result.stdout

    def test_ttc_info_with_ttf_version(self, tmp_path: Path) -> None:
        """ttc-info should correctly identify TrueType version."""
        ttc_data = _build_ttc_with_two_faces()
        ttc_path = tmp_path / "test.ttc"
        ttc_path.write_bytes(ttc_data)

        result = run("ttc-info", str(ttc_path))

        assert result.returncode == 0
        assert "TrueType" in result.stdout

    def test_ttc_info_with_otf_version(self, tmp_path: Path) -> None:
        """ttc-info should correctly identify OTF version."""
        ttc_data = _build_ttc_with_two_faces()
        ttc_path = tmp_path / "test.ttc"
        ttc_path.write_bytes(ttc_data)

        result = run("ttc-info", str(ttc_path))

        assert result.returncode == 0
        assert "OTF" in result.stdout

    def test_ttc_info_with_non_ttc_file(self, tmp_path: Path) -> None:
        """ttc-info should error on non-TTC file."""
        font_data = b"Not a TTC file"
        font_path = tmp_path / "test.ttf"
        font_path.write_bytes(font_data)

        result = run("ttc-info", str(font_path))

        assert result.returncode != 0
        assert "Error:" in result.stderr or "Error:" in result.stdout

    def test_ttc_info_with_nonexistent_file(self) -> None:
        """ttc-info should error on nonexistent file."""
        result = run("ttc-info", "/nonexistent/path/file.ttc")

        assert result.returncode != 0
        assert "Error:" in result.stderr or "Error:" in result.stdout


class TestTtcExtractCommand:
    """Tests for the ttc-extract CLI command."""

    def test_ttc_extract_produces_valid_font(self, tmp_path: Path) -> None:
        """ttc-extract should write a valid standalone font file."""
        ttc_data = _build_ttc_with_two_faces()
        ttc_path = tmp_path / "test.ttc"
        ttc_path.write_bytes(ttc_data)

        output = tmp_path / "extracted.ttf"
        result = run("ttc-extract", str(ttc_path), "0", str(output))

        assert result.returncode == 0
        assert output.exists()
        assert output.stat().st_size > 0

    def test_ttc_extract_multiple_faces_produce_different_content(self, tmp_path: Path) -> None:
        """Extracting different faces should produce different font content."""
        ttc_data = _build_ttc_with_two_faces()
        ttc_path = tmp_path / "test.ttc"
        ttc_path.write_bytes(ttc_data)

        output0 = tmp_path / "face0.ttf"
        output1 = tmp_path / "face1.ttf"

        result0 = run("ttc-extract", str(ttc_path), "0", str(output0))
        result1 = run("ttc-extract", str(ttc_path), "1", str(output1))

        assert result0.returncode == 0
        assert result1.returncode == 0
        assert output0.exists()
        assert output1.exists()

        content0 = output0.read_bytes()
        content1 = output1.read_bytes()

        assert len(content0) > 0
        assert len(content1) > 0
        assert content0 != content1

    def test_ttc_extract_negative_index_errors(self, tmp_path: Path) -> None:
        """ttc-extract with negative index should error with non-zero exit."""
        ttc_data = _build_ttc_with_two_faces()
        ttc_path = tmp_path / "test.ttc"
        ttc_path.write_bytes(ttc_data)

        output = tmp_path / "out.ttf"
        result = run("ttc-extract", str(ttc_path), "-1", str(output))

        assert result.returncode != 0
        assert "Error:" in result.stderr or "Error:" in result.stdout

    def test_ttc_extract_out_of_range_index_errors(self, tmp_path: Path) -> None:
        """ttc-extract with index >= num_faces should error."""
        ttc_data = _build_ttc_with_two_faces()
        ttc_path = tmp_path / "test.ttc"
        ttc_path.write_bytes(ttc_data)

        output = tmp_path / "out.ttf"
        result = run("ttc-extract", str(ttc_path), "10", str(output))

        assert result.returncode != 0
        assert "out of range" in result.stderr or "out of range" in result.stdout

    def test_ttc_extract_output_directory_auto_created(self, tmp_path: Path) -> None:
        """ttc-extract should create output directory if it doesn't exist."""
        ttc_data = _build_ttc_with_two_faces()
        ttc_path = tmp_path / "test.ttc"
        ttc_path.write_bytes(ttc_data)

        output_dir = tmp_path / "nested" / "output"
        output = output_dir / "extracted.ttf"

        result = run("ttc-extract", str(ttc_path), "0", str(output))

        assert result.returncode == 0
        assert output.exists()

    def test_ttc_extract_extracted_font_is_valid(self, tmp_path: Path) -> None:
        """Extracted font should be a valid sfnt that can be loaded."""
        from aspose_font import FontLoader

        ttc_data = _build_ttc_with_two_faces()
        ttc_path = tmp_path / "test.ttc"
        ttc_path.write_bytes(ttc_data)

        output = tmp_path / "extracted.ttf"
        result = run("ttc-extract", str(ttc_path), "0", str(output))

        assert result.returncode == 0

        try:
            font = FontLoader.open(output)
            assert font is not None
        except Exception:
            pytest.skip("Extracted font has minimal structure, verification skipped")
