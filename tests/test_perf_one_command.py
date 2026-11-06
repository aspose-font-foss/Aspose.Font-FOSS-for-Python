"""CI performance regression tests for one-command web optimizer."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from aspose_font.perf.regression_one_command import run_one_command_regression

FIXTURE_ROOT = Path(__file__).resolve().parent.parent / "testdata"


def test_run_one_command_regression_returns_valid_report(tmp_path: Path) -> None:
    """Verify run_one_command_regression returns a valid report structure."""
    thresholds_path = tmp_path / "thresholds.yml"
    thresholds_path.write_text(
        "load_ms: 150.0\nsubset_ms: 200.0\nmanifest_ms: 100.0\n",
        encoding="utf-8",
    )

    font_path = FIXTURE_ROOT / "Roboto-VariableFont_wdth,wght.ttf"

    if not font_path.exists():
        pytest.skip(f"Fixture not found: {font_path}")

    report = run_one_command_regression(font_path, thresholds_path)

    assert "load_time_ms" in report
    assert "subset_time_ms" in report
    assert "manifest_time_ms" in report
    assert "total_time_ms" in report
    assert "passed" in report
    assert isinstance(report["passed"], bool)
    assert isinstance(report["load_time_ms"], float)
    assert isinstance(report["subset_time_ms"], float)
    assert isinstance(report["manifest_time_ms"], float)
    assert isinstance(report["total_time_ms"], float)


def test_one_command_regression_respects_thresholds(tmp_path: Path) -> None:
    """Verify all stages pass when thresholds are reasonable."""
    thresholds_path = tmp_path / "thresholds.yml"
    thresholds_path.write_text(
        "load_ms: 1000.0\nsubset_ms: 1000.0\nmanifest_ms: 1000.0\n",
        encoding="utf-8",
    )

    font_path = FIXTURE_ROOT / "Roboto-VariableFont_wdth,wght.ttf"

    if not font_path.exists():
        pytest.skip(f"Fixture not found: {font_path}")

    report = run_one_command_regression(font_path, thresholds_path)

    assert report["passed"] is True
    assert report["load_time_ms"] < 1000.0
    assert report["subset_time_ms"] < 1000.0
    assert report["manifest_time_ms"] < 1000.0


def test_one_command_regression_fails_with_tight_thresholds(tmp_path: Path) -> None:
    """Verify regression fails when thresholds are too tight."""
    thresholds_path = tmp_path / "thresholds.yml"
    thresholds_path.write_text(
        "load_ms: 0.1\nsubset_ms: 0.1\nmanifest_ms: 0.1\n",
        encoding="utf-8",
    )

    font_path = FIXTURE_ROOT / "Roboto-VariableFont_wdth,wght.ttf"

    if not font_path.exists():
        pytest.skip(f"Fixture not found: {font_path}")

    report = run_one_command_regression(font_path, thresholds_path)

    assert report["passed"] is False


def test_one_command_regression_cli_integration(tmp_path: Path) -> None:
    """Verify CLI command produces valid JSON output."""
    import subprocess

    thresholds_path = tmp_path / "thresholds.yml"
    thresholds_path.write_text(
        "load_ms: 1000.0\nsubset_ms: 1000.0\nmanifest_ms: 1000.0\n",
        encoding="utf-8",
    )

    report_path = tmp_path / "report_one_command.json"

    result = subprocess.run(
        [sys.executable, "-m", "aspose_font.cli", "one-command-regress", "--output", str(report_path)],
        capture_output=True,
        text=True,
        cwd=str(tmp_path),
    )

    assert result.returncode == 0
    assert report_path.exists()

    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert "passed" in report
    assert report["passed"] is True
