"""Tests for vorg-info CLI command (FONT-490)."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from aspose_font.ttf.tables.vorg import VertOriginYMetric, VorgTable

CLI = [sys.executable, "-m", "aspose_font.cli"]


def run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        CLI + list(args),
        capture_output=True,
        text=True,
    )


def create_font_with_vorg(tmp_path: Path, vorg: VorgTable) -> Path:
    """Create a minimal TTF font with a VORG table."""
    head = bytes(12) + (0x5F0F3CF5).to_bytes(4, "big") + bytes(54 - 16)
    maxp = (0x00010000).to_bytes(4, "big") + (1).to_bytes(2, "big") + bytes(26)
    vorg_bytes = vorg.to_bytes()

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
    vorg_offset = maxp_offset + len(maxp)
    directory = (
        b"head"
        + (0).to_bytes(4, "big")
        + head_offset.to_bytes(4, "big")
        + len(head).to_bytes(4, "big")
        + b"maxp"
        + (0).to_bytes(4, "big")
        + maxp_offset.to_bytes(4, "big")
        + len(maxp).to_bytes(4, "big")
        + b"VORG"
        + (0).to_bytes(4, "big")
        + vorg_offset.to_bytes(4, "big")
        + len(vorg_bytes).to_bytes(4, "big")
    )
    minimal_ttf = offset_table + directory + head + maxp + vorg_bytes
    font_path = tmp_path / "vorg-font.ttf"
    font_path.write_bytes(minimal_ttf)
    return font_path


def test_vorg_info_command_prints_summary(tmp_path: Path) -> None:
    """Test that vorg-info prints VORG table summary for font with VORG table."""
    vorg = VorgTable(
        major_version=1,
        minor_version=0,
        default_vert_origin_y=800,
        vert_origin_y_metrics=[
            VertOriginYMetric(glyph_id=1, vert_origin_y=750),
            VertOriginYMetric(glyph_id=2, vert_origin_y=760),
        ]
    )
    font_path = create_font_with_vorg(tmp_path, vorg)
    result = run("vorg-info", str(font_path))
    assert result.returncode == 0
    out = result.stdout
    assert "VORG table:" in out
    assert "Default vertical origin Y:" in out
    assert "Glyph-specific vertical origins:" in out


def test_vorg_info_accepts_json_output_flag(tmp_path: Path) -> None:
    """Test that --json-output writes valid JSON report for font with VORG table."""
    vorg = VorgTable(
        major_version=1,
        minor_version=0,
        default_vert_origin_y=800,
        vert_origin_y_metrics=[
            VertOriginYMetric(glyph_id=1, vert_origin_y=750),
            VertOriginYMetric(glyph_id=2, vert_origin_y=760),
        ]
    )
    font_path = create_font_with_vorg(tmp_path, vorg)
    json_path = tmp_path / "vorg.json"
    result = run("vorg-info", str(font_path), "--json-output", str(json_path))
    assert result.returncode == 0
    assert json_path.exists()
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)
    assert "version" in data
    assert data["version"] == "1.0"
    assert "default_vert_origin_y" in data
    assert isinstance(data["default_vert_origin_y"], int)
    assert "glyph_specific_metrics_count" in data
    assert isinstance(data["glyph_specific_metrics_count"], int)
    assert "glyph_metrics" in data
    assert isinstance(data["glyph_metrics"], list)


def test_vorg_info_handles_font_without_vorg_exits_0(tmp_path: Path) -> None:
    """Test that fonts without VORG table print notice and exit 0."""
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
    font_path = tmp_path / "no-vorg.ttf"
    font_path.write_bytes(minimal_ttf)

    result = run("vorg-info", str(font_path))
    assert result.returncode == 0
    assert "VORG table: Not present" in result.stdout
    assert "Note:" in result.stdout


def test_vorg_info_non_ttf_font_exits_with_error() -> None:
    """Test that non-TTF fonts produce error."""
    pfb_path = str(Path(__file__).resolve().parents[1] / "testdata" / "OpenSans-Regular.pfb")
    result = run("vorg-info", pfb_path)
    assert result.returncode != 0
    combined_output = result.stdout + result.stderr
    assert "VORG table inspection is only supported" in combined_output


def test_vorg_info_json_output_contains_expected_structure(tmp_path: Path) -> None:
    """Test that JSON output has expected structure for font with VORG table."""
    vorg = VorgTable(
        major_version=1,
        minor_version=0,
        default_vert_origin_y=800,
        vert_origin_y_metrics=[
            VertOriginYMetric(glyph_id=1, vert_origin_y=750),
            VertOriginYMetric(glyph_id=2, vert_origin_y=760),
        ]
    )
    font_path = create_font_with_vorg(tmp_path, vorg)
    json_path = tmp_path / "vorg.json"
    result = run("vorg-info", str(font_path), "--json-output", str(json_path))
    assert result.returncode == 0
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)
    assert isinstance(data["version"], str)
    assert data["version"] == "1.0"
    assert isinstance(data["default_vert_origin_y"], int)
    assert isinstance(data["glyph_specific_metrics_count"], int)
    assert isinstance(data["glyph_metrics"], list)
    if len(data["glyph_metrics"]) > 0:
        first = data["glyph_metrics"][0]
        assert "glyph_id" in first
        assert "vert_origin_y" in first
        assert isinstance(first["glyph_id"], int)
        assert isinstance(first["vert_origin_y"], int)
