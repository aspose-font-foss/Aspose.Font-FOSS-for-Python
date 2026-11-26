"""Tests for axis-clamp CLI command (FONT-573)."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from aspose_font import FontLoader, TtfFont

ROBOTO = str(Path(__file__).resolve().parents[1] / "testdata" / "Roboto-VariableFont_wdth,wght.ttf")
CLI = [sys.executable, "-m", "aspose_font.cli"]


def run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        CLI + list(args),
        capture_output=True,
        text=True,
    )


def test_axis_clamp_single_axis_success(tmp_path: Path) -> None:
    """Test that basic axis clamping works for a single axis."""
    output_path = tmp_path / "output.ttf"
    result = run("axis-clamp", ROBOTO, str(output_path), "--axis", "wght=300:700")
    assert result.returncode == 0
    assert output_path.exists()
    assert "Output:" in result.stdout


def test_axis_clamp_multiple_axes(tmp_path: Path) -> None:
    """Test that multiple axes can be clamped in one command."""
    output_path = tmp_path / "output.ttf"
    result = run(
        "axis-clamp",
        ROBOTO,
        str(output_path),
        "--axis",
        "wght=300:700",
        "--axis",
        "wdth=80:120",
    )
    assert result.returncode == 0
    assert output_path.exists()


def test_axis_clamp_json_output(tmp_path: Path) -> None:
    """Test that --json flag produces valid JSON output."""
    result = run("axis-clamp", ROBOTO, str(tmp_path / "output.ttf"), "--axis", "wght=300:700", "--json")
    assert result.returncode == 0

    import json

    stdout_data = json.loads(result.stdout)
    assert "clamped_axes" in stdout_data
    assert len(stdout_data["clamped_axes"]) == 1
    assert stdout_data["clamped_axes"][0]["tag"] == "wght"
    assert stdout_data["clamped_axes"][0]["min_value"] == 300.0
    assert stdout_data["clamped_axes"][0]["max_value"] == 700.0


def test_axis_clamp_output_font_valid(tmp_path: Path) -> None:
    """Test that output font is valid and has correct axis values."""
    output_path = tmp_path / "output.ttf"
    result = run("axis-clamp", ROBOTO, str(output_path), "--axis", "wght=400:600")
    assert result.returncode == 0

    font = FontLoader.open(output_path)
    assert isinstance(font, TtfFont)
    assert font.is_variable

    axes = {ax.tag: ax for ax in font.axes}
    assert axes["wght"].min_value == 400.0
    assert axes["wght"].max_value == 600.0


def test_axis_clamp_non_variable_font_exits_error() -> None:
    """Test that non-variable fonts produce error."""
    static_roboto = str(Path(__file__).resolve().parents[1] / "testdata" / "Fonts" / "Roboto-Regular.ttf")
    result = run("axis-clamp", static_roboto, "out.ttf", "--axis", "wght=300:700")
    assert result.returncode != 0
    combined_output = result.stdout + result.stderr
    assert "Font is not variable" in combined_output or "FVAR" in combined_output


def test_axis_clamp_non_ttf_font_exits_error() -> None:
    """Test that non-TTF fonts produce error."""
    pfb_path = str(Path(__file__).resolve().parents[1] / "testdata" / "OpenSans-Regular.pfb")
    result = run("axis-clamp", pfb_path, "out.ttf", "--axis", "wght=300:700")
    assert result.returncode != 0
    combined_output = result.stdout + result.stderr
    assert "axis-clamp is only supported for TTF/OTF fonts" in combined_output


def test_axis_clamp_invalid_axis_format_exits_error() -> None:
    """Test that invalid --axis format produces error."""
    result = run("axis-clamp", ROBOTO, "out.ttf", "--axis", "wght300:700")
    assert result.returncode != 0
    combined_output = result.stdout + result.stderr
    assert "Invalid" in combined_output or "Expected" in combined_output


def test_axis_clamp_nonexistent_axis_exits_error() -> None:
    """Test that non-existent axis tag produces error."""
    result = run("axis-clamp", ROBOTO, "out.ttf", "--axis", "XXXX=100:900")
    assert result.returncode != 0
    combined_output = result.stdout + result.stderr
    assert "not found" in combined_output or "XXXX" in combined_output


def test_axis_clamp_min_greater_than_max_exits_error() -> None:
    """Test that min > max raises error."""
    result = run("axis-clamp", ROBOTO, "out.ttf", "--axis", "wght=900:100")
    assert result.returncode != 0
    combined_output = result.stdout + result.stderr
    assert "min" in combined_output.lower() and "max" in combined_output.lower()


def test_axis_clamp_missing_axis_argument_exits_error() -> None:
    """Test that missing --axis argument produces error."""
    result = run("axis-clamp", ROBOTO, "out.ttf")
    assert result.returncode != 0
    combined_output = result.stdout + result.stderr
    assert "required" in combined_output.lower() or "axis" in combined_output.lower()


def test_axis_clamp_output_verify_multiple_axes(tmp_path: Path) -> None:
    """Test that output font has correct values when clamping multiple axes."""
    output_path = tmp_path / "output.ttf"
    result = run(
        "axis-clamp",
        ROBOTO,
        str(output_path),
        "--axis",
        "wght=300:800",
        "--axis",
        "wdth=85:115",
    )
    assert result.returncode == 0

    font = FontLoader.open(output_path)
    assert isinstance(font, TtfFont)

    axes = {ax.tag: ax for ax in font.axes}
    assert axes["wght"].min_value == 300.0
    assert axes["wght"].max_value == 800.0
    assert axes["wdth"].min_value == 85.0
    assert axes["wdth"].max_value == 115.0
