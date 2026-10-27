"""Tests for the CI CFF2 subsetting performance benchmark command.

The benchmark function is patched to simulate fast and slow execution paths,
allowing verification of CLI integration, JSON report generation, and exit
codes without performing an actual subsetting operation.
"""

# ruff: noqa: I001
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest




@pytest.fixture
def cli_args(tmp_path: Path) -> list[str]:
    return [sys.executable, "-m", "aspose_font.cli", "ci-cff2-subset-performance", "--output-dir", str(tmp_path)]


def test_cli_success_fast(monkeypatch, cli_args, tmp_path: Path):
    """Fast benchmark should exit with code 0 and report within_threshold=True."""

    def fast_stub(_: Path) -> dict:
        return {"build_time_ms": 100.0, "threshold_ms": 300.0, "within_threshold": True}

    # Use environment variable to control benchmark timing for fast case.
    result = subprocess.run(cli_args, capture_output=True, text=True, env={**os.environ, "CFF2_SUBSET_BENCHMARK_MS": "100"})
    assert result.returncode == 0, result.stderr

    report_path = tmp_path / "performance-cff2-subset.json"
    assert report_path.exists()
    data = json.loads(report_path.read_text(encoding="utf-8"))
    assert data["within_threshold"] is True
    assert data["build_time_ms"] == 100.0


def test_cli_failure_slow(cli_args, tmp_path: Path):
    """Slow benchmark should exit with code 1 and report within_threshold=False."""

    # Use environment variable to simulate slow benchmark.
    result = subprocess.run(
        cli_args,
        capture_output=True,
        text=True,
        env={**os.environ, "CFF2_SUBSET_BENCHMARK_MS": "400"},
    )
    assert result.returncode == 1, result.stderr

    report_path = tmp_path / "performance-cff2-subset.json"
    assert report_path.exists()
    data = json.loads(report_path.read_text(encoding="utf-8"))
    assert data["within_threshold"] is False
    assert data["build_time_ms"] == 400.0
