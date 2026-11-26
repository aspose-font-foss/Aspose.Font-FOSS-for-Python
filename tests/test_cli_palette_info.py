"""Tests for palette-info CLI command (FONT-532)."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from aspose_font import TtfFont

ROBOTO = str(Path(__file__).resolve().parents[1] / "testdata" / "Roboto-VariableFont_wdth,wght.ttf")
CLI = [sys.executable, "-m", "aspose_font.cli"]


def run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        CLI + list(args),
        capture_output=True,
        text=True,
    )


def test_palette_info_command_prints_summary() -> None:
    """Test that palette-info prints CPAL summary for font with palettes."""
    result = run("palette-info", ROBOTO)
    assert result.returncode == 0
    out = result.stdout
    assert "CPAL table inspection:" in out
    assert "No color palette data" in out or "Version:" in out


def test_palette_info_handles_font_without_cpal_exits_0() -> None:
    """Test that fonts without CPAL print notice and exit 0."""
    result = run("palette-info", ROBOTO)
    assert result.returncode == 0
    assert "CPAL table inspection:" in result.stdout
    assert "Not present" in result.stdout or "No color palette data" in result.stdout


def test_palette_info_with_cpal_font_prints_colors(cpal_v1_font: TtfFont, tmp_path: Path) -> None:
    """Test that CPAL fonts print palette colors."""
    font_path = tmp_path / "cpal-test.ttf"
    font_path.write_bytes(cpal_v1_font.to_bytes())

    result = run("palette-info", str(font_path))
    assert result.returncode == 0
    out = result.stdout
    assert "CPAL table inspection:" in out
    assert "Version: 1" in out
    assert "Palettes: 2" in out
    assert "Color records: 4" in out
    assert "Palette 0:" in out
    assert "Palette 1:" in out
    assert "rgba" in out.lower() or "#" in out


def test_palette_info_css_flag_generates_valid_css(cpal_v1_font: TtfFont, tmp_path: Path) -> None:
    """Test that --css flag generates valid @font-palette-values CSS."""
    font_path = tmp_path / "cpal-test.ttf"
    font_path.write_bytes(cpal_v1_font.to_bytes())

    result = run("palette-info", str(font_path), "--css")
    assert result.returncode == 0
    out = result.stdout
    assert "@font-palette-values" in out
    assert "palette-0" in out
    assert "palette-1" in out
    assert "rgba(" in out or "rgb(" in out


def test_palette_info_json_output_structure(tmp_path: Path) -> None:
    """Test that --json-output produces valid JSON report."""
    json_path = tmp_path / "report.json"
    result = run("palette-info", ROBOTO, "--json-output", str(json_path))
    assert result.returncode == 0
    assert json_path.exists()

    data = json.loads(json_path.read_text())
    assert "table" in data
    assert "font" in data or data.get("note") is not None


def test_palette_info_json_output_with_cpal(cpal_v1_font: TtfFont, tmp_path: Path) -> None:
    """Test that JSON output contains expected structure for font with CPAL."""
    font_path = tmp_path / "cpal-test.ttf"
    font_path.write_bytes(cpal_v1_font.to_bytes())

    json_path = tmp_path / "report.json"
    result = run("palette-info", str(font_path), "--json-output", str(json_path))
    assert result.returncode == 0
    assert json_path.exists()

    data = json.loads(json_path.read_text())
    assert data["table"] is not None
    assert data["table"]["version"] == 1
    assert data["table"]["palette_count"] == 2
    assert data["table"]["color_record_count"] == 4
    assert "palettes" in data["table"]
    assert len(data["table"]["palettes"]) == 2
    assert "colors" in data["table"]["palettes"][0]
    assert len(data["table"]["palettes"][0]["colors"]) == 2
    assert len(data["table"]["palettes"][1]["colors"]) == 2


def test_palette_info_non_ttf_font_exits_with_error() -> None:
    """Test that non-TTF fonts produce error."""
    pfb_path = str(Path(__file__).resolve().parents[1] / "testdata" / "OpenSans-Regular.pfb")
    result = run("palette-info", pfb_path)
    assert result.returncode != 0
    combined_output = result.stdout + result.stderr
    assert "TTF/OTF fonts" in combined_output


def test_palette_info_css_without_cpal_exits_with_error() -> None:
    """Test that --css on font without CPAL exits with error."""
    result = run("palette-info", ROBOTO, "--css")
    assert result.returncode != 0
    assert "CPAL" in result.stdout or "CPAL" in result.stderr


def test_palette_info_color_with_alpha(cpal_v1_font_with_alpha: TtfFont, tmp_path: Path) -> None:
    """Test that palette-info correctly displays colors with alpha values."""
    font_path = tmp_path / "cpal-alpha-test.ttf"
    font_path.write_bytes(cpal_v1_font_with_alpha.to_bytes())

    result = run("palette-info", str(font_path))
    assert result.returncode == 0
    out = result.stdout
    assert "alpha:" in out.lower() or "(alpha:" in out.lower()


def test_palette_info_table_absence_message() -> None:
    """Test that fonts without CPAL show helpful message."""
    result = run("palette-info", ROBOTO)
    assert result.returncode == 0
    assert "CPAL table inspection:" in result.stdout
    assert "Note:" in result.stdout
    assert "OpenType CPAL" in result.stdout
