"""Tests for ltag-info CLI command (FONT-505)."""
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


def _create_font_with_ltag_table(tmp_path: Path) -> Path:
    """Create a minimal TTF font with ltag table for testing."""
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
    ltag_offset = maxp_offset + len(maxp)

    # ltag: version=1.0, count=2, offsets, then null-terminated tags
    # The ltag table layout is:
    # Bytes 0-1: major_version (0x0001)
    # Bytes 2-3: minor_version (0x0000)
    # Bytes 4-5: count (0x0002)
    # Bytes 6-7: offset to tag 0 ("en\x00")
    # Bytes 8-9: offset to tag 1 ("fr\x00")
    # Bytes 10-12: "en\x00" (3 bytes)
    # Bytes 13-15: "fr\x00" (3 bytes)
    # So offset 0 = 10 (absolute) and offset 1 = 13 (absolute)
    ltag_data = (
        b"\x00\x01"  # major version (2 bytes)
        + b"\x00\x00"  # minor version (2 bytes)
        + b"\x00\x02"  # count=2 (2 bytes)
        + b"\x00\x0A"  # offset 0: tag 0 starts at byte 10 from table start (2 bytes)
        + b"\x00\x0D"  # offset 1: tag 1 starts at byte 13 from table start (2 bytes)
        + b"en\x00"    # tag 0 (3 bytes): "en" + null
        + b"fr\x00"    # tag 1 (3 bytes): "fr" + null
    )

    directory = (
        b"head"
        + (0).to_bytes(4, "big")
        + head_offset.to_bytes(4, "big")
        + len(head).to_bytes(4, "big")
        + b"maxp"
        + (0).to_bytes(4, "big")
        + maxp_offset.to_bytes(4, "big")
        + len(maxp).to_bytes(4, "big")
        + b"ltag"
        + (0).to_bytes(4, "big")
        + ltag_offset.to_bytes(4, "big")
        + len(ltag_data).to_bytes(4, "big")
    )

    minimal_ttf = offset_table + directory + head + maxp + ltag_data
    font_path = tmp_path / "with-ltag.ttf"
    font_path.write_bytes(minimal_ttf)
    return font_path


def test_ltag_info_command_prints_tags() -> None:
    """Test that ltag-info prints tags for font with ltag table."""
    font = FontLoader.open(ROBOTO)
    if font.ttf_tables.ltag is None:
        pytest.skip("Roboto font in test suite does not have ltag table")

    result = run("ltag-info", ROBOTO)
    assert result.returncode == 0
    out = result.stdout
    assert "ltag table:" in out
    assert "Language tags:" in out
    assert "[" in out and "]" in out


def test_ltag_info_handles_font_without_ltag_exits_0(tmp_path: Path) -> None:
    """Test that fonts without ltag table print notice and exit 0."""
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
    font_path = tmp_path / "no-ltag.ttf"
    font_path.write_bytes(minimal_ttf)

    result = run("ltag-info", str(font_path))
    assert result.returncode == 0
    assert "ltag table: Not present" in result.stdout


def test_ltag_info_accepts_json_output_flag(tmp_path: Path) -> None:
    """Test that --json-output writes valid JSON report."""
    font = FontLoader.open(ROBOTO)
    if font.ttf_tables.ltag is None:
        pytest.skip("Roboto font in test suite does not have ltag table")

    json_path = tmp_path / "ltag.json"
    result = run("ltag-info", ROBOTO, "--json-output", str(json_path))
    assert result.returncode == 0
    assert json_path.exists()
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)
    assert "version" in data
    assert "tag_count" in data
    assert isinstance(data["version"], str)
    assert isinstance(data["tag_count"], int)


def test_ltag_info_non_ttf_font_exits_with_error() -> None:
    """Test that non-TTF fonts produce error."""
    pfb_path = str(Path(__file__).resolve().parents[1] / "testdata" / "OpenSans-Regular.pfb")
    result = run("ltag-info", pfb_path)
    assert result.returncode != 0
    assert "ltag table inspection is only supported" in result.stdout or result.stderr


def test_ltag_info_cross_references_name_records(tmp_path: Path) -> None:
    """Test that ltag-info cross-references name table records."""
    font_path = _create_font_with_ltag_table(tmp_path)
    result = run("ltag-info", str(font_path))
    assert result.returncode == 0
    out = result.stdout
    assert "ltag table:" in out
    assert "Language tags:" in out
    assert "[0]" in out or "[1]" in out


def test_ltag_info_json_structure(tmp_path: Path) -> None:
    """Test that JSON output has correct structure with version, tag_count, tags."""
    font = FontLoader.open(ROBOTO)
    if font.ttf_tables.ltag is None:
        pytest.skip("Roboto font in test suite does not have ltag table")

    result = run("ltag-info", ROBOTO, "--json-output", str(tmp_path / "ltag.json"))
    assert result.returncode == 0
    with open(tmp_path / "ltag.json", encoding="utf-8") as f:
        data = json.load(f)
    assert isinstance(data["version"], str)
    assert isinstance(data["tag_count"], int)
    assert isinstance(data["tags"], list)
    if data["tags"]:
        first_tag = data["tags"][0]
        assert "index" in first_tag
        assert "tag" in first_tag
        assert "name_records" in first_tag


def test_ltag_info_with_created_font(tmp_path: Path) -> None:
    """Test ltag-info with a font we create that has an ltag table."""
    font_path = _create_font_with_ltag_table(tmp_path)
    result = run("ltag-info", str(font_path))
    assert result.returncode == 0
    out = result.stdout
    assert "ltag table: version 1.0" in out
    assert "Language tags: 2" in out
    assert "[0] en" in out
    assert "[1] fr" in out


def test_ltag_info_json_with_created_font(tmp_path: Path) -> None:
    """Test ltag-info --json-output with a font we create that has an ltag table."""
    font_path = _create_font_with_ltag_table(tmp_path)
    json_path = tmp_path / "ltag.json"
    result = run("ltag-info", str(font_path), "--json-output", str(json_path))
    assert result.returncode == 0
    assert json_path.exists()
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)
    assert data["version"] == "1.0"
    assert data["tag_count"] == 2
    assert len(data["tags"]) == 2
    assert data["tags"][0]["tag"] == "en"
    assert data["tags"][1]["tag"] == "fr"
