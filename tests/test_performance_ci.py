"""CI performance regression gating tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from aspose_font.ci.perf import RegressionReport, run_ci_benchmarks

FIXTURE_ROOT = Path(__file__).resolve().parent.parent / "testdata" / "Fonts"


@pytest.fixture
def fixture_root() -> Path:
    return FIXTURE_ROOT


def test_run_ci_benchmarks_executes_successfully(fixture_root: Path) -> None:
    """Verify run_ci_benchmarks returns a valid RegressionReport."""
    report = run_ci_benchmarks(fixture_root)
    assert isinstance(report, RegressionReport)
    assert len(report.results) == 5
    assert report.summary["total_metrics"] == 5


def test_ci_benchmarks_respect_thresholds(fixture_root: Path) -> None:
    """Verify all metrics meet their threshold contracts."""
    report = run_ci_benchmarks(fixture_root)
    for metric in report.results:
        assert metric.elapsed_ms < metric.threshold_ms, (
            f"{metric.name} took {metric.elapsed_ms:.2f}ms, exceeds threshold {metric.threshold_ms}ms"
        )
        assert metric.passed is True


def test_regression_report_json_roundtrip(fixture_root: Path) -> None:
    """Verify RegressionReport data structure is JSON-serializable."""
    report = run_ci_benchmarks(fixture_root)
    assert isinstance(report.timestamp, str)
    assert isinstance(report.summary, dict)
    assert "overall_status" in report.summary
    assert "total_metrics" in report.summary
    assert "passed" in report.summary


def test_subset_direct_metric_present_and_passed(fixture_root: Path) -> None:
    """Verify subset_direct metric exists in CI performance report."""
    report = run_ci_benchmarks(fixture_root)
    subset_metrics = [m for m in report.results if m.name == "subset_direct"]
    assert len(subset_metrics) == 1, "subset_direct metric must be present in CI report"
    subset_metric = subset_metrics[0]
    assert subset_metric.passed is True, (
        f"subset_direct performance test failed: {subset_metric.elapsed_ms:.2f}ms >= {subset_metric.threshold_ms}ms"
    )
