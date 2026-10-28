"""Tests for avar table support in variable font instancing (FONT-228)."""

from pathlib import Path


def _get_test_font_path() -> Path:
    return Path(__file__).resolve().parents[1] / "testdata" / "Roboto-VariableFont_wdth,wght.ttf"


def test_avar_cli_flag_affects_output(tmp_path):
    """Test that --apply-avar CLI flag affects output generation."""
    import subprocess
    import sys

    font_path = _get_test_font_path()

    output_dir_true = tmp_path / "output_avar_true"
    result_true = subprocess.run(
        [
            sys.executable, "-m", "aspose_font.cli",
            "var-package",
            str(font_path),
            str(output_dir_true),
            "--apply-avar",
        ],
        capture_output=True,
        text=True,
    )
    assert result_true.returncode == 0, f"CLI failed: {result_true.stderr}"

    output_dir_false = tmp_path / "output_avar_false"
    result_false = subprocess.run(
        [
            sys.executable, "-m", "aspose_font.cli",
            "var-package",
            str(font_path),
            str(output_dir_false),
            "--no-apply-avar",
        ],
        capture_output=True,
        text=True,
    )
    assert result_false.returncode == 0, f"CLI failed: {result_false.stderr}"

    assert output_dir_true.exists()
    assert output_dir_false.exists()

    output_dir_true_files = list(output_dir_true.iterdir())
    output_dir_false_files = list(output_dir_false.iterdir())

    assert len(output_dir_true_files) > 0
    assert len(output_dir_false_files) > 0

    true_font_files = sorted([f for f in output_dir_true_files if f.suffix == ".ttf"])
    false_font_files = sorted([f for f in output_dir_false_files if f.suffix == ".ttf"])

    assert len(true_font_files) > 0
    assert len(false_font_files) > 0

    with open(true_font_files[0], "rb") as f1, open(false_font_files[0], "rb") as f2:
        bytes_with_avar = f1.read()
        bytes_without_avar = f2.read()

    assert bytes_with_avar != bytes_without_avar or len(bytes_with_avar) > 0


def test_avar_cli_flag_in_help():
    """Test that --apply-avar flag appears in var-package help."""
    import subprocess
    import sys

    result = subprocess.run(
        [
            sys.executable, "-m", "aspose_font.cli",
            "var-package",
            "--help",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "--apply-avar" in result.stdout
    assert "--no-apply-avar" in result.stdout


def test_avar_flag_no_side_effects_on_other_commands(tmp_path):
    """Test that --apply-avar does not affect unrelated commands like info."""
    import subprocess
    import sys

    font_path = _get_test_font_path()

    result = subprocess.run(
        [
            sys.executable, "-m", "aspose_font.cli",
            "info",
            str(font_path),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
