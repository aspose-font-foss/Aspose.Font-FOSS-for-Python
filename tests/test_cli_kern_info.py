"""Tests for kern-info CLI command (FONT-496)."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from aspose_font import FontLoader

ROBOTO = str(Path(__file__).resolve().parents[1] / "testdata" / "Roboto-VariableFont_wdth,wght.ttf")
CLI = [sys.executable, "-m", "aspose_font.cli"]


def run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        CLI + list(args),
        capture_output=True,
        text=True,
    )


def _create_font_with_kern_table(tmp_path: Path) -> Path:
    """Create a minimal TTF font with a kern table for testing."""
    head = bytes(12) + (0x5F0F3CF5).to_bytes(4, "big") + bytes(54 - 16)
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
    kern_offset = maxp_offset + len(maxp)
    directory = (
        b"head"
        + (0).to_bytes(4, "big")
        + head_offset.to_bytes(4, "big")
        + len(head).to_bytes(4, "big")
        + b"maxp"
        + (0).to_bytes(4, "big")
        + maxp_offset.to_bytes(4, "big")
        + len(maxp).to_bytes(4, "big")
        + b"kern"
        + (0).to_bytes(4, "big")
        + kern_offset.to_bytes(4, "big")
        + (30).to_bytes(4, "big")
    )
    # Simple kern table: version=0 (OpenType), nSubtables=1
    # Subtable: version=0, length=26, coverage=0x0000 (format 0, horizontal)
    # Followed by format 0 data: nPairs=2, then 2 pairs
    kern_data = (
        b"\x00\x00"  # main version (OpenType format)
        + b"\x00\x01"  # nSubtables = 1
        + b"\x00\x00"  # subtable version = 0
        + b"\x00\x1A"  # length = 26 bytes
        + b"\x00\x00"  # coverage = 0x0000 (format 0, horizontal)
        # format 0 data:
        + b"\x00\x02"  # nPairs = 2
        + b"\x00\x00"  # searchRange
        + b"\x00\x01"  # entrySelector
        + b"\x00\x00"  # rangeShift
        + b"\x00\x05"  # left glyph ID = 5
        + b"\x00\x0A"  # right glyph ID = 10
        + b"\xFF\xE7"  # value = -25
        + b"\x00\x0F"  # left glyph ID = 15
        + b"\x00\x14"  # right glyph ID = 20
        + b"\xFF\xE2"  # value = -30
    )
    minimal_ttf = offset_table + directory + head + maxp + kern_data
    font_path = tmp_path / "with-kern.ttf"
    font_path.write_bytes(minimal_ttf)
    return font_path


def test_kern_info_command_prints_subtables() -> None:
    """Test that kern-info prints subtables information for font with kern table."""
    font = FontLoader.open(ROBOTO)
    if font.ttf_tables.kern is None:
        pytest.skip("Roboto font in test suite does not have kern table")

    result = run("kern-info", ROBOTO)
    assert result.returncode == 0
    out = result.stdout
    assert "kern table:" in out
    assert "Subtables:" in out
    assert "Pairs:" in out
    assert "Total pairs:" in out


def test_kern_info_accepts_json_output_flag(tmp_path: Path) -> None:
    """Test that --json-output writes valid JSON report."""
    font = FontLoader.open(ROBOTO)
    if font.ttf_tables.kern is None:
        pytest.skip("Roboto font in test suite does not have kern table")

    json_path = tmp_path / "kern.json"
    result = run("kern-info", ROBOTO, "--json-output", str(json_path))
    assert result.returncode == 0
    assert json_path.exists()
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)
    assert "version" in data
    assert "subtables" in data
    assert "total_pairs" in data
    assert isinstance(data["version"], str)
    assert len(data["version"]) == 4


def test_kern_info_handles_font_without_kern_exits_0(tmp_path: Path) -> None:
    """Test that fonts without kern table print notice and exit 0."""
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
    minimal_ttf = offset_table + directory + head + maxp
    font_path = tmp_path / "no-kern.ttf"
    font_path.write_bytes(minimal_ttf)

    result = run("kern-info", str(font_path))
    assert result.returncode == 0
    assert "kern table: Not present" in result.stdout
    assert "Not present" in result.stdout


def test_kern_info_non_ttf_font_exits_with_error() -> None:
    """Test that non-TTF fonts produce error."""
    pfb_path = str(Path(__file__).resolve().parents[1] / "testdata" / "OpenSans-Regular.pfb")
    result = run("kern-info", pfb_path)
    assert result.returncode != 0
    assert "kern table inspection is only supported" in result.stdout or result.stderr


def test_kern_info_json_output_structure(tmp_path: Path) -> None:
    """Test that JSON output has correct structure with version, subtables, and pairs."""
    font = FontLoader.open(ROBOTO)
    if font.ttf_tables.kern is None:
        pytest.skip("Roboto font in test suite does not have kern table")

    json_path = tmp_path / "kern.json"
    result = run("kern-info", ROBOTO, "--json-output", str(json_path))
    assert result.returncode == 0
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)
    assert isinstance(data["version"], str)
    assert isinstance(data["subtables"], list)
    assert isinstance(data["total_pairs"], int)
    if data["subtables"]:
        first_subtable = data["subtables"][0]
        assert "format" in first_subtable
        assert "coverage_flags" in first_subtable
        assert "pairs" in first_subtable
        assert isinstance(first_subtable["format"], int)
        assert isinstance(first_subtable["coverage_flags"], int)
        assert isinstance(first_subtable["pairs"], list)
        if first_subtable["pairs"]:
            first_pair = first_subtable["pairs"][0]
            assert isinstance(first_pair["left"], int)
            assert isinstance(first_pair["right"], int)
            assert isinstance(first_pair["value"], int)


def test_kern_info_with_created_font(tmp_path: Path) -> None:
    """Test kern-info with a font we create that has a kern table."""
    font_path = _create_font_with_kern_table(tmp_path)
    result = run("kern-info", str(font_path))
    assert result.returncode == 0
    out = result.stdout
    assert "kern table:" in out
    assert "Subtables: 1" in out
    assert "Pairs:" in out
    assert "Total pairs: 2" in out


def test_kern_info_json_with_created_font(tmp_path: Path) -> None:
    """Test kern-info --json-output with a font we create that has a kern table."""
    font_path = _create_font_with_kern_table(tmp_path)
    json_path = tmp_path / "kern.json"
    result = run("kern-info", str(font_path), "--json-output", str(json_path))
    assert result.returncode == 0
    assert json_path.exists()
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)
    assert data["version"] == "0000"
    assert len(data["subtables"]) == 1
    assert data["total_pairs"] == 2
    subtable = data["subtables"][0]
    assert subtable["format"] == 0
    assert subtable["coverage_flags"] == 0
    assert len(subtable["pairs"]) == 2
    assert subtable["pairs"][0]["left"] == 5
    assert subtable["pairs"][0]["right"] == 10
    assert subtable["pairs"][0]["value"] == -25
