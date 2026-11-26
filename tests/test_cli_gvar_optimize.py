"""Tests for gvar-optimize CLI command (FONT-567)."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from aspose_font import TtfFont

ROBOTO = str(Path(__file__).resolve().parents[1] / "testdata" / "Roboto-VariableFont_wdth,wght.ttf")
CLI = [sys.executable, "-m", "aspose_font.cli"]


def run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        CLI + list(args),
        capture_output=True,
        text=True,
    )


def test_gvar_optimize_command_succeeds(tmp_path: Path) -> None:
    """Test that basic gvar compaction succeeds."""
    output_path = tmp_path / "output.ttf"
    result = run("gvar-optimize", ROBOTO, str(output_path))
    assert result.returncode == 0
    assert output_path.exists()
    assert "Saved:" in result.stdout
    assert "Size reduction:" in result.stdout


def test_gvar_optimize_reduces_or_maintains_size(tmp_path: Path) -> None:
    """Test that output size is reasonable - gvar compaction should not increase gvar size."""
    from aspose_font import FontLoader

    output_path = tmp_path / "output.ttf"

    result = run("gvar-optimize", ROBOTO, str(output_path))
    assert result.returncode == 0

    input_font = FontLoader.open(ROBOTO)
    gvar_table = input_font.get_gvar_table()
    if gvar_table is None:
        pytest.skip("Input font has no gvar table")

    original_gvar_size = len(gvar_table._raw)

    output_font = FontLoader.open(output_path)
    if not isinstance(output_font, TtfFont):
        pytest.skip("Output is not TTF font")

    output_gvar = output_font.get_gvar_table()
    if output_gvar is None:
        pytest.skip("Output font has no gvar table")

    output_gvar_size = len(output_gvar._raw)

    assert output_gvar_size <= original_gvar_size, f"gvar size should not increase: {output_gvar_size} > {original_gvar_size}"


def test_gvar_optimize_output_loads(tmp_path: Path) -> None:
    """Test that output font loads successfully."""
    from aspose_font import FontLoader

    output_path = tmp_path / "output.ttf"
    result = run("gvar-optimize", ROBOTO, str(output_path))
    assert result.returncode == 0

    font = FontLoader.open(output_path)
    assert font is not None
    assert isinstance(font, TtfFont)


def test_gvar_optimize_non_ttf_font_exits_with_error() -> None:
    """Test that non-TTF fonts produce error."""
    pfb_path = str(Path(__file__).resolve().parents[1] / "testdata" / "OpenSans-Regular.pfb")
    result = run("gvar-optimize", pfb_path, "out.ttf")
    assert result.returncode != 0
    combined_output = result.stdout + result.stderr
    assert "gvar-optimize is only supported for TTF/OTF fonts" in combined_output


def test_gvar_optimize_missing_gvar_exits_with_error(tmp_path: Path) -> None:
    """Test that fonts without gvar table produce error."""
    from aspose_font import FontLoader

    static_roboto = str(Path(__file__).resolve().parents[1] / "testdata" / "Fonts" / "Roboto-Regular.ttf")
    output_path = tmp_path / "output.ttf"

    font = FontLoader.open(static_roboto)
    if not isinstance(font, TtfFont):
        pytest.skip("Static Roboto is not TTF")
        return

    has_gvar = "gvar" in font.ttf_tables._raw
    if not has_gvar:
        result = run("gvar-optimize", static_roboto, str(output_path))
        assert result.returncode != 0
        combined_output = result.stdout + result.stderr
        assert "does not contain gvar table" in combined_output or "gvar table" in combined_output.lower()
    else:
        pytest.skip("Roboto-Regular has gvar table, skipping missing gvar test")


def test_gvar_optimize_json_output(tmp_path: Path) -> None:
    """Test that --json flag produces valid JSON."""
    result = run("gvar-optimize", "--json", ROBOTO, str(tmp_path / "output.ttf"))
    assert result.returncode == 0

    import json as json_module

    try:
        json_module.loads(result.stdout)
    except json_module.JSONDecodeError:
        pytest.fail("JSON output is not valid JSON")


def test_gvar_optimize_size_reduction_in_output(tmp_path: Path) -> None:
    """Test that output contains size reduction summary."""
    output_path = tmp_path / "output.ttf"
    result = run("gvar-optimize", ROBOTO, str(output_path))
    assert result.returncode == 0

    assert "Original gvar size:" in result.stdout
    assert "Optimized gvar size:" in result.stdout
    assert "Size reduction:" in result.stdout
    assert "Removed glyphs:" in result.stdout
    assert "Retained glyphs:" in result.stdout
