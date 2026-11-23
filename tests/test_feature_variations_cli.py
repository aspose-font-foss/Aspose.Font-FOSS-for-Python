"""Unit tests for the feature-variations CLI command."""

from __future__ import annotations

from pathlib import Path

import pytest

from aspose_font import FontLoader

FIXTURE_PATH = Path(__file__).resolve().parents[1] / "testdata" / "FeatureVarFont.ttf"


def test_feature_variations_command_registers():
    """Test that the feature-variations subcommand is registered."""
    import subprocess
    import sys

    result = subprocess.run(
        [sys.executable, "-m", "aspose_font.cli", "--help"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "feature-variations" in result.stdout


def test_feature_variations_command_runs_successfully():
    """Test that feature-variations command runs without error."""
    import subprocess
    import sys

    if not FIXTURE_PATH.exists():
        pytest.skip("FeatureVarFont.ttf fixture not found")

    result = subprocess.run(
        [sys.executable, "-m", "aspose_font.cli", "feature-variations", str(FIXTURE_PATH)],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "Error" not in result.stderr


def test_feature_variations_command_output_format():
    """Test that feature-variations outputs tags, one per line."""
    import subprocess
    import sys

    if not FIXTURE_PATH.exists():
        pytest.skip("FeatureVarFont.ttf fixture not found")

    result = subprocess.run(
        [sys.executable, "-m", "aspose_font.cli", "feature-variations", str(FIXTURE_PATH)],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0

    lines = result.stdout.strip().split("\n")
    lines = [line for line in lines if line]

    assert len(lines) > 0

    for line in lines:
        assert len(line) == 4, f"Expected 4-character tag, got: {line!r}"
        assert line.isupper(), f"Expected uppercase tag, got: {line}"


def test_feature_variations_api_consistency():
    """Test that CLI output matches feature_variations_list() API."""
    import subprocess
    import sys

    if not FIXTURE_PATH.exists():
        pytest.skip("FeatureVarFont.ttf fixture not found")

    loaded = FontLoader.open(FIXTURE_PATH)
    font = loaded.font

    expected_tags = font.feature_variations_list()

    if expected_tags is None:
        result = subprocess.run(
            [sys.executable, "-m", "aspose_font.cli", "feature-variations", str(FIXTURE_PATH)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "No feature variations" in result.stdout
        return

    result = subprocess.run(
        [sys.executable, "-m", "aspose_font.cli", "feature-variations", str(FIXTURE_PATH)],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0

    cli_tags = result.stdout.strip().split("\n")
    cli_tags = [t for t in cli_tags if t]

    assert len(cli_tags) == len(expected_tags)
    assert set(cli_tags) == set(expected_tags)


def test_feature_variations_no_feature_variations():
    """Test command on font without FeatureVariations table."""
    import subprocess
    import sys

    from aspose_font import FontLoader

    roboto_path = Path(__file__).resolve().parents[1] / "testdata" / "Roboto-VariableFont_wdth,wght.ttf"

    try:
        loaded = FontLoader.open(roboto_path)
        if loaded.ttf_tables.feature_variations is None:
            pass
        else:
            pytest.skip("Roboto fixture has feature variations - unexpected")
    except Exception:
        pytest.skip("Unable to load Roboto fixture")

    result = subprocess.run(
        [sys.executable, "-m", "aspose_font.cli", "feature-variations", str(roboto_path)],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "No feature variations" in result.stdout or len(result.stdout.strip()) == 0
