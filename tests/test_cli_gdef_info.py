"""Tests for gdef-info CLI command (FONT-472)."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROBOTO = str(Path(__file__).resolve().parents[1] / "testdata" / "Roboto-VariableFont_wdth,wght.ttf")
CLI = [sys.executable, "-m", "aspose_font.cli"]


def run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        CLI + list(args),
        capture_output=True,
        text=True,
    )


def test_gdef_info_command_prints_glyph_classes() -> None:
    """Test that gdef-info prints glyph class counts for font with GDEF."""
    result = run("gdef-info", ROBOTO)
    assert result.returncode == 0
    out = result.stdout
    assert "GDEF table:" in out
    assert "Glyph classes:" in out
    assert "Base (class 1):" in out


def test_gdef_info_accepts_json_output_flag(tmp_path: Path) -> None:
    """Test that --json-output writes valid JSON report."""
    json_path = tmp_path / "gdef.json"
    result = run("gdef-info", ROBOTO, "--json-output", str(json_path))
    assert result.returncode == 0
    assert json_path.exists()
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)
    assert "version" in data
    assert "glyph_classes" in data
    assert "ligature_carets" in data
    assert "mark_attachment_classes" in data


def test_gdef_info_handles_font_without_gdef_exits_0(tmp_path: Path) -> None:
    """Test that fonts without GDEF table print notice and exit 0."""
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
    font_path = tmp_path / "no-gdef.ttf"
    font_path.write_bytes(minimal_ttf)

    result = run("gdef-info", str(font_path))
    assert result.returncode == 0
    assert "GDEF table: Not present" in result.stdout
    assert "Note:" in result.stdout


def test_gdef_info_non_ttf_font_exits_with_error() -> None:
    """Test that non-TTF fonts produce error."""
    pfb_path = str(Path(__file__).resolve().parents[1] / "testdata" / "OpenSans-Regular.pfb")
    result = run("gdef-info", pfb_path)
    assert result.returncode != 0
    combined_output = result.stdout + result.stderr
    assert "GDEF table inspection is only supported" in combined_output


def test_gdef_info_json_output_contains_expected_structure(tmp_path: Path) -> None:
    """Test that JSON output has expected structure."""
    json_path = tmp_path / "gdef.json"
    result = run("gdef-info", ROBOTO, "--json-output", str(json_path))
    assert result.returncode == 0
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)
    assert isinstance(data["version"], (int, float))
    assert isinstance(data["glyph_classes"], dict)
    assert "base" in data["glyph_classes"]
    assert "ligature" in data["glyph_classes"]
    assert "mark" in data["glyph_classes"]
    assert "component" in data["glyph_classes"]
    assert isinstance(data["ligature_carets"], dict)
    assert "total" in data["ligature_carets"]
    assert "with_carets" in data["ligature_carets"]
    assert isinstance(data["mark_attachment_classes"], dict)
    assert "defined" in data["mark_attachment_classes"]
    assert "classes" in data["mark_attachment_classes"]
