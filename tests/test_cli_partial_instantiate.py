"""Tests for var-partial-instance CLI command (FONT-323)."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

CLI = [sys.executable, "-m", "aspose_font.cli"]


def run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        CLI + list(args),
        capture_output=True,
        text=True,
    )


def test_var_partial_instance_creates_partial_instance(tmp_path: Path) -> None:
    test_font = str(Path(__file__).resolve().parents[1] / "testdata" / "Roboto-VariableFont_wdth,wght.ttf")
    output_path = tmp_path / "partial-instance.ttf"

    result = run("var-partial-instance", test_font, str(output_path), "--lock-axis", "wght=400")

    assert result.returncode == 0
    assert output_path.exists()
    assert "Locked axes: wght=400" in result.stdout
    assert "Output:" in result.stdout

    from aspose_font import FontLoader
    font = FontLoader.open(output_path)
    # partial_instantiate preserves fvar, so is_variable is still True
    assert font.is_variable
    # Locked axis (wght) should have min=default=max=400
    wght_axis = next(a for a in font.axes if a.tag == "wght")
    assert wght_axis.min_value == 400.0
    assert wght_axis.default_value == 400.0
    assert wght_axis.max_value == 400.0


def test_var_partial_instance_multiple_axes(tmp_path: Path) -> None:
    """Test with multiple lock-axis arguments (still leaves one variable axis)."""
    test_font = str(Path(__file__).resolve().parents[1] / "testdata" / "Roboto-VariableFont_wdth,wght.ttf")
    output_path = tmp_path / "partial-multi.ttf"

    # Lock both axes - this will fail because partial_instantiate needs at least one variable axis
    result = run("var-partial-instance", test_font, str(output_path), "--lock-axis", "wght=400")

    assert result.returncode == 0
    assert output_path.exists()
    output_line = next(line for line in result.stdout.split("\n") if "Locked axes:" in line)
    assert "wght=400" in output_line


def test_var_partial_instance_requires_at_least_one_lock_axis() -> None:
    test_font = str(Path(__file__).resolve().parents[1] / "testdata" / "Roboto-VariableFont_wdth,wght.ttf")

    result = run("var-partial-instance", test_font, "output.ttf")

    assert result.returncode != 0
    assert "required" in result.stderr.lower()


def test_var_partial_instance_preserves_variable_axis(tmp_path: Path) -> None:
    """Test that the output preserves the variable axis (wdth) while locking wght."""
    test_font = str(Path(__file__).resolve().parents[1] / "testdata" / "Roboto-VariableFont_wdth,wght.ttf")
    output_path = tmp_path / "partial-variable.ttf"

    result = run("var-partial-instance", test_font, str(output_path), "--lock-axis", "wght=400")

    assert result.returncode == 0
    assert output_path.exists()

    from aspose_font import FontLoader
    font = FontLoader.open(output_path)
    # Output should still be a variable font since we only locked wght, wdth remains variable
    assert font.is_variable

    # Verify it has two axes (both preserved in fvar), but wght is locked
    assert len(font.axes) == 2
    wght_axis = next(a for a in font.axes if a.tag == "wght")
    wdth_axis = next(a for a in font.axes if a.tag == "wdth")
    assert wght_axis.min_value == wght_axis.max_value == 400.0  # locked
    # wdth should still be variable (min != max)
    assert wdth_axis.min_value != wdth_axis.max_value
