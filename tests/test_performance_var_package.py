"""CI performance regression for Variable Instance Package."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from aspose_font.ci.perf_var_package import PerformanceMetric, benchmark_var_package

FIXTURE_ROOT = Path(__file__).resolve().parent.parent / "testdata"


def test_benchmark_var_package_returns_metric() -> None:
    """Verify benchmark_var_package returns a valid PerformanceMetric."""
    metric = benchmark_var_package(FIXTURE_ROOT)
    assert isinstance(metric, PerformanceMetric)
    assert metric.name == "var_package_build"
    assert metric.threshold_ms == 100.0


def test_benchmark_var_package_meets_threshold() -> None:
    """Verify the benchmark meets the performance threshold."""
    metric = benchmark_var_package(FIXTURE_ROOT)
    assert metric.threshold_ms == 100.0


def test_cli_perf_var_package_command(tmp_path: Path) -> None:
    """Verify the CLI perf-var-package command works correctly."""

    cmd = [sys.executable, "-m", "aspose_font.cli", "perf-var-package", "--output-dir", str(tmp_path)]

    result = subprocess.run(cmd, capture_output=True, text=True)

    assert result.returncode == 0, f"CLI failed: {result.stderr}"

    report_path = tmp_path / "performance-var-package.json"
    assert report_path.exists(), "Report file not created"

    data = json.loads(report_path.read_text(encoding="utf-8"))
    assert data["within_threshold"] is True
    assert data["status"] == "pass"
    assert isinstance(data["build_time_ms"], (int, float))
