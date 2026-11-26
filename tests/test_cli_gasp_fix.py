"""Tests for gasp-fix CLI command (FONT-545)."""
from __future__ import annotations

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


def test_gasp_fix_command_succeeds(tmp_path: Path) -> None:
    """Test that basic gasp synthesis with default strategy succeeds."""
    output_path = tmp_path / "output.ttf"
    result = run("gasp-fix", ROBOTO, str(output_path))
    assert result.returncode == 0
    assert output_path.exists()
    assert "Saved:" in result.stdout


def test_gasp_fix_accepts_strategy_standard(tmp_path: Path) -> None:
    """Test that explicit --strategy standard works."""
    output_path = tmp_path / "output.ttf"
    result = run("gasp-fix", ROBOTO, str(output_path), "--strategy", "standard")
    assert result.returncode == 0
    assert output_path.exists()


def test_gasp_fix_accepts_strategy_grayscale(tmp_path: Path) -> None:
    """Test that --strategy grayscale works."""
    output_path = tmp_path / "output.ttf"
    result = run("gasp-fix", ROBOTO, str(output_path), "--strategy", "grayscale")
    assert result.returncode == 0
    assert output_path.exists()


def test_gasp_fix_accepts_strategy_cleartype(tmp_path: Path) -> None:
    """Test that --strategy cleartype works."""
    output_path = tmp_path / "output.ttf"
    result = run("gasp-fix", ROBOTO, str(output_path), "--strategy", "cleartype")
    assert result.returncode == 0
    assert output_path.exists()


def test_gasp_fix_replaces_existing_gasp(tmp_path: Path) -> None:
    """Test that gasp-fix overwrites existing gasp table."""
    output_path = tmp_path / "output.ttf"
    result = run("gasp-fix", ROBOTO, str(output_path))
    assert result.returncode == 0
    assert output_path.exists()


def test_gasp_fix_non_ttf_font_exits_with_error() -> None:
    """Test that non-TTF fonts produce error."""
    pfb_path = str(Path(__file__).resolve().parents[1] / "testdata" / "OpenSans-Regular.pfb")
    result = run("gasp-fix", pfb_path, "out.ttf")
    assert result.returncode != 0
    combined_output = result.stdout + result.stderr
    assert "gasp-fix is only supported for TTF/OTF fonts" in combined_output


def test_gasp_fix_invalid_strategy_exits_with_error(tmp_path: Path) -> None:
    """Test that unknown strategy names produce error."""
    output_path = tmp_path / "output.ttf"
    result = run("gasp-fix", ROBOTO, str(output_path), "--strategy", "invalid")
    assert result.returncode != 0
    combined_output = result.stdout + result.stderr
    assert "strategy" in combined_output.lower() or "invalid" in combined_output.lower()


def test_gasp_fix_outputs_valid_font(tmp_path: Path) -> None:
    """Test that output font loads successfully."""
    from aspose_font import FontLoader

    output_path = tmp_path / "output.ttf"
    result = run("gasp-fix", ROBOTO, str(output_path))
    assert result.returncode == 0

    font = FontLoader.open(output_path)
    assert font.ttf_tables.gasp is not None
