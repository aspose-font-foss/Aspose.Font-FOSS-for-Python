'''CI performance regression test for CFF2 variable font subsetting (ID: 4c82011d8d3e4599bc424816fe308c23).'''

from __future__ import annotations

from pathlib import Path

import pytest

from aspose_font.ci.perf import run_ci_benchmarks


@pytest.fixture
def fixture_root() -> Path:
    # Reuse same fixture root as other CI performance tests
    from tests.test_performance_ci import FIXTURE_ROOT
    return FIXTURE_ROOT


def test_cff2_variable_subsetting_metric_present_and_passed(fixture_root: Path) -> None:
    """Verify CFF2 variable subsetting metric exists and passes its threshold."""
    report = run_ci_benchmarks(fixture_root)
    subset_metrics = [m for m in report.results if m.name == "subset_variable"]
    assert len(subset_metrics) == 1, "subset_variable metric must be present in CI report"
    metric = subset_metrics[0]
    assert metric.passed is True, (
        f"subset_variable performance test failed: {metric.elapsed_ms:.2f}ms >= {metric.threshold_ms:.2f}ms"
    )
