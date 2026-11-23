from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_ci_drift_alert_passing(tmp_path: Path) -> None:
    """Test passing scenario: build time within threshold."""
    report_path = tmp_path / "performance-passing.json"
    report_data = {
        "build_time_ms": 5000.0,
        "threshold_ms": 10000.0,
        "within_threshold": True,
        "status": "pass",
    }
    report_path.write_text(json.dumps(report_data, indent=2), encoding="utf-8")

    result = subprocess.run(
        [sys.executable, "-m", "aspose_font.cli", "ci-drift-alert", "--report", str(report_path)],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "within threshold" in result.stdout.lower()
    assert "5000.00ms" in result.stdout


def test_ci_drift_alert_failing(tmp_path: Path) -> None:
    """Test failing scenario: build time exceeds threshold."""
    report_path = tmp_path / "performance-failing.json"
    report_data = {
        "build_time_ms": 15000.0,
        "threshold_ms": 10000.0,
        "within_threshold": False,
        "status": "fail",
    }
    report_path.write_text(json.dumps(report_data, indent=2), encoding="utf-8")

    result = subprocess.run(
        [sys.executable, "-m", "aspose_font.cli", "ci-drift-alert", "--report", str(report_path)],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "drift detected" in result.stdout.lower()
    assert "15000.00ms" in result.stdout
    assert "threshold: 10000.00ms" in result.stdout


def test_ci_drift_alert_missing_fields(tmp_path: Path) -> None:
    """Test error handling for missing required fields."""
    report_path = tmp_path / "performance-incomplete.json"
    report_data = {
        "build_time_ms": 5000.0,
        # Missing threshold_ms
    }
    report_path.write_text(json.dumps(report_data, indent=2), encoding="utf-8")

    result = subprocess.run(
        [sys.executable, "-m", "aspose_font.cli", "ci-drift-alert", "--report", str(report_path)],
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "threshold_ms" in result.stderr


def test_ci_drift_alert_invalid_json(tmp_path: Path) -> None:
    """Test error handling for invalid JSON."""
    report_path = tmp_path / "performance-invalid.json"
    report_path.write_text("{ invalid json }", encoding="utf-8")

    result = subprocess.run(
        [sys.executable, "-m", "aspose_font.cli", "ci-drift-alert", "--report", str(report_path)],
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "Invalid JSON" in result.stderr


def test_ci_drift_alert_file_not_found() -> None:
    """Test error handling for non-existent file."""
    result = subprocess.run(
        [sys.executable, "-m", "aspose_font.cli", "ci-drift-alert", "--report", "/nonexistent/path.json"],
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "not found" in result.stderr.lower() or "not found" in result.stdout.lower()
