"""Tests for CLI ttc-build subcommand (FONT-542)."""

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


def _get_test_font_paths() -> list[Path]:
    testdata_dir = Path(__file__).resolve().parents[1] / "testdata"
    return [
        testdata_dir / "Fonts" / "Roboto-Regular.ttf",
        testdata_dir / "Fonts" / "Roboto-Medium.ttf",
    ]


def _build_minimal_sfnt_with_tables(tables: list[tuple[bytes, bytes]]) -> bytes:
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

    return _build_minimal_sfnt_with_tables(tables)


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

    result = _build_minimal_sfnt_with_tables(tables)

    if is_otf:
        result = b"OTTO" + result[4:]

    return result


def _sfnt_search_params(num_tables: int) -> tuple[int, int, int]:
    max_power = 1
    entry_selector = 0
    while max_power * 2 <= num_tables:
        max_power *= 2
        entry_selector += 1
    search_range = max_power * 16
    range_shift = num_tables * 16 - search_range
    return search_range, entry_selector, range_shift


def _build_minimal_ttc_with_faces(faces_data: list[bytes]) -> bytes:
    """Build a minimal TTC file with the given face data."""
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


class TestTtcBuildCommand:
    """Tests for the ttc-build CLI command."""

    def test_cli_ttc_build_creates_valid_ttc(self, tmp_path: Path) -> None:
        """ttc-build should create a valid TTC from two font files."""
        font_paths = _get_test_font_paths()

        if not font_paths[0].exists() or not font_paths[1].exists():
            pytest.skip("Test font files not available")

        ttc_path = tmp_path / "output.ttc"

        result = run("ttc-build", str(font_paths[0]), str(font_paths[1]), "-o", str(ttc_path))

        assert result.returncode == 0
        assert ttc_path.exists()
        assert ttc_path.stat().st_size > 0

        ttc_data = ttc_path.read_bytes()
        assert ttc_data[:4] == b"ttcf"

    def test_cli_ttc_build_no_dedup_flag(self, tmp_path: Path) -> None:
        """ttc-build should work with --no-dedup flag."""
        font_paths = _get_test_font_paths()

        if not font_paths[0].exists() or not font_paths[1].exists():
            pytest.skip("Test font files not available")

        ttc_path = tmp_path / "output_no_dedup.ttc"

        result = run("ttc-build", str(font_paths[0]), str(font_paths[1]), "-o", str(ttc_path), "--no-dedup")

        assert result.returncode == 0
        assert ttc_path.exists()

        ttc_data = ttc_path.read_bytes()
        assert ttc_data[:4] == b"ttcf"

    def test_cli_ttc_build_prints_summary(self, tmp_path: Path) -> None:
        """ttc-build should print summary with merged count and dedup status."""
        font_paths = _get_test_font_paths()

        if not font_paths[0].exists() or not font_paths[1].exists():
            pytest.skip("Test font files not available")

        ttc_path = tmp_path / "output.ttc"

        result = run("ttc-build", str(font_paths[0]), str(font_paths[1]), "-o", str(ttc_path))

        assert result.returncode == 0
        assert "Merged 2 font(s) into:" in result.stdout
        assert "Table deduplication: enabled" in result.stdout
        assert "(Summary: shared tables reduce file size)" in result.stdout

    def test_cli_ttc_build_no_dedup_prints_summary(self, tmp_path: Path) -> None:
        """ttc-build with --no-dedup should print dedup disabled."""
        font_paths = _get_test_font_paths()

        if not font_paths[0].exists() or not font_paths[1].exists():
            pytest.skip("Test font files not available")

        ttc_path = tmp_path / "output_no_dedup.ttc"

        result = run("ttc-build", str(font_paths[0]), str(font_paths[1]), "-o", str(ttc_path), "--no-dedup")

        assert result.returncode == 0
        assert "Merged 2 font(s) into:" in result.stdout
        assert "Table deduplication: enabled" not in result.stdout

    def test_cli_ttc_build_minimal_fonts(self, tmp_path: Path) -> None:
        """ttc-build should work with exactly 2 valid font files."""
        font_paths = _get_test_font_paths()

        if not font_paths[0].exists() or not font_paths[1].exists():
            pytest.skip("Test font files not available")

        ttc_path = tmp_path / "output.ttc"

        result = run("ttc-build", str(font_paths[0]), str(font_paths[1]), "-o", str(ttc_path))

        assert result.returncode == 0
        assert ttc_path.exists()

        ttc_data = ttc_path.read_bytes()
        assert ttc_data[:4] == b"ttcf"

    def test_cli_ttc_build_invalid_inputs(self, tmp_path: Path) -> None:
        """ttc-build should error on non-existent font paths."""
        ttc_path = tmp_path / "output.ttc"

        result = run("ttc-build", "/nonexistent/font.ttf", "-o", str(ttc_path))

        assert result.returncode != 0
        assert "Error:" in result.stderr or "Error:" in result.stdout

    def test_cli_ttc_build_single_font_errors(self, tmp_path: Path) -> None:
        """ttc-build should error when only one font is provided."""
        font_paths = _get_test_font_paths()

        if not font_paths[0].exists():
            pytest.skip("Test font files not available")

        ttc_path = tmp_path / "output.ttc"

        result = run("ttc-build", str(font_paths[0]), "-o", str(ttc_path))

        assert result.returncode != 0
        assert "Error:" in result.stderr or "Error:" in result.stdout

    def test_cli_ttc_build_output_directory_auto_created(self, tmp_path: Path) -> None:
        """ttc-build should create output directory if it doesn't exist."""
        font_paths = _get_test_font_paths()

        if not font_paths[0].exists() or not font_paths[1].exists():
            pytest.skip("Test font files not available")

        output_dir = tmp_path / "nested" / "output"
        ttc_path = output_dir / "output.ttc"

        result = run("ttc-build", str(font_paths[0]), str(font_paths[1]), "-o", str(ttc_path))

        assert result.returncode == 0
        assert ttc_path.exists()
