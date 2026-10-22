"""Performance benchmark tests for core font workflows."""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from aspose_font import FontLoader
from aspose_font._performance import (
    PerformanceBenchmark,
    PerformanceRegressionError,
    PerformanceRegressionResult,
    assert_no_regression,
    compare_performance,
    load_baselines,
    measure_workflow,
    run_performance_suite,
    save_baselines,
)
from aspose_font.ci.perf import run_ci_benchmarks
from aspose_font.performance import measure_load_time

MARKER = pytest.mark.performance

FIXTURE_ROOT = Path(__file__).resolve().parent.parent / "testdata" / "Fonts"
FIXTURE_ROBOTOGVAR = Path(__file__).resolve().parent.parent / "testdata" / "Roboto-VariableFont_wdth,wght.ttf"
FIXTURE_ROBOTO = FIXTURE_ROOT / "Roboto-Regular.ttf"
BASELINE_PATH = Path(__file__).resolve().parent.parent / "backlog" / "runtime" / "performance_baselines.json"


@MARKER
def test_ci_benchmarks_executes_successfully() -> None:
    """Verify CI benchmarks run and return valid results."""
    report = run_ci_benchmarks(FIXTURE_ROOT)
    assert report is not None
    assert len(report.results) == 5
    assert report.summary["total_metrics"] == 5


@MARKER
def test_ci_benchmarks_respect_thresholds() -> None:
    """Verify all metrics meet their threshold contracts."""
    report = run_ci_benchmarks(FIXTURE_ROOT)
    for metric in report.results:
        assert metric.elapsed_ms < metric.threshold_ms, (
            f"{metric.name} took {metric.elapsed_ms:.2f}ms, exceeds threshold {metric.threshold_ms}ms"
        )
        assert metric.passed is True


@pytest.fixture
def temp_baseline_path(tmp_path: Path) -> Path:
    """Provide a temporary path for baseline testing."""
    return tmp_path / "performance_baselines.json"


class TestPerformanceInfrastructure:
    """Tests for the _performance module infrastructure."""

    def test_performance_benchmark_dataclass(self) -> None:
        """Verify PerformanceBenchmark dataclass has expected fields."""
        benchmark = PerformanceBenchmark(
            workflow_name="test_workflow",
            fixture_path="/test/font.ttf",
            fixture_size_bytes=1024,
            duration_ms=50.0,
            timestamp="2026-09-29T12:00:00Z",
            python_version="3.10.0",
            platform="win32",
        )
        assert benchmark.workflow_name == "test_workflow"
        assert benchmark.duration_ms == 50.0
        assert benchmark.fixture_size_bytes == 1024

    def test_performance_regression_result_dataclass(self) -> None:
        """Verify PerformanceRegressionResult dataclass has expected fields."""
        result = PerformanceRegressionResult(
            workflow_name="test_workflow",
            fixture_path="/test/font.ttf",
            baseline_duration_ms=50.0,
            current_duration_ms=70.0,
            regression_ratio=1.4,
            threshold_ms=20.0,
            passed=False,
            delta_ms=20.0,
            delta_percent=40.0,
        )
        assert result.current_duration_ms > result.baseline_duration_ms
        assert result.delta_percent == 40.0

    def test_measure_workflow_returns_benchmark(self, tmp_path: Path) -> None:
        """Verify measure_workflow returns a PerformanceBenchmark."""
        FontLoader.open(FIXTURE_ROBOTO)

        def workflow() -> None:
            FontLoader.open(FIXTURE_ROBOTO)

        benchmark = measure_workflow(
            name="font_load",
            fixture_path=FIXTURE_ROBOTO,
            runner=workflow,
            iterations=2,
        )

        assert isinstance(benchmark, PerformanceBenchmark)
        assert benchmark.workflow_name == "font_load"
        assert benchmark.duration_ms > 0
        assert benchmark.fixture_size_bytes > 0

    def test_measure_workflow_excludes_warmup(self, tmp_path: Path) -> None:
        """Verify measure_workflow excludes warmup runs from timing."""
        FontLoader.open(FIXTURE_ROBOTO)
        call_count = 0

        def counting_workflow() -> None:
            nonlocal call_count
            call_count += 1
            time.sleep(0.001)

        benchmark = measure_workflow(
            name="counting_workflow",
            fixture_path=FIXTURE_ROBOTO,
            runner=counting_workflow,
            iterations=2,
            warmup=1,
        )

        assert call_count == 3
        assert benchmark.duration_ms > 0

    def test_load_baselines_empty_when_file_not_found(self, tmp_path: Path) -> None:
        """Verify load_baselines returns empty dict when file doesn't exist."""
        nonexistent_path = tmp_path / "nonexistent.json"
        baselines = load_baselines(nonexistent_path)
        assert baselines == {}

    def test_save_and_load_baselines_roundtrip(self, temp_baseline_path: Path) -> None:
        """Verify save_baselines and load_baselines work as roundtrip."""
        benchmark = PerformanceBenchmark(
            workflow_name="test_workflow",
            fixture_path="/test/font.ttf",
            fixture_size_bytes=1024,
            duration_ms=50.0,
            timestamp="2026-09-29T12:00:00Z",
            python_version="3.10.0",
            platform="win32",
        )

        save_baselines({"test_workflow": [benchmark]}, temp_baseline_path)

        loaded = load_baselines(temp_baseline_path)
        assert "test_workflow" in loaded
        assert len(loaded["test_workflow"]) == 1
        assert loaded["test_workflow"][0].duration_ms == 50.0

    def test_compare_performance_with_no_baselines(self) -> None:
        """Verify compare_performance returns passed result when no baselines."""
        current = PerformanceBenchmark(
            workflow_name="test_workflow",
            fixture_path="/test/font.ttf",
            fixture_size_bytes=1024,
            duration_ms=50.0,
            timestamp="2026-09-29T12:00:00Z",
            python_version="3.10.0",
            platform="win32",
        )

        result = compare_performance(
            current=current,
            baselines=[],
            threshold_ms=20.0,
        )

        assert result.passed is True
        assert result.baseline_duration_ms == 0.0

    def test_compare_performance_detects_regression(self) -> None:
        """Verify compare_performance detects performance regression."""
        current = PerformanceBenchmark(
            workflow_name="test_workflow",
            fixture_path="/test/font.ttf",
            fixture_size_bytes=1024,
            duration_ms=100.0,
            timestamp="2026-09-29T12:00:00Z",
            python_version="3.10.0",
            platform="win32",
        )

        baseline = PerformanceBenchmark(
            workflow_name="test_workflow",
            fixture_path="/test/font.ttf",
            fixture_size_bytes=1024,
            duration_ms=50.0,
            timestamp="2026-09-29T12:00:00Z",
            python_version="3.10.0",
            platform="win32",
        )

        result = compare_performance(
            current=current,
            baselines=[baseline],
            threshold_ms=10.0,
        )

        assert result.passed is False
        assert result.delta_ms == 50.0
        assert result.delta_percent == 100.0

    def test_compare_performance_within_threshold(self) -> None:
        """Verify compare_performance passes when within threshold."""
        current = PerformanceBenchmark(
            workflow_name="test_workflow",
            fixture_path="/test/font.ttf",
            fixture_size_bytes=1024,
            duration_ms=60.0,
            timestamp="2026-09-29T12:00:00Z",
            python_version="3.10.0",
            platform="win32",
        )

        baseline = PerformanceBenchmark(
            workflow_name="test_workflow",
            fixture_path="/test/font.ttf",
            fixture_size_bytes=1024,
            duration_ms=50.0,
            timestamp="2026-09-29T12:00:00Z",
            python_version="3.10.0",
            platform="win32",
        )

        result = compare_performance(
            current=current,
            baselines=[baseline],
            threshold_ms=20.0,
        )

        assert result.passed is True

    def test_assert_no_regression_passes(self) -> None:
        """Verify assert_no_regression doesn't raise on passing result."""
        result = PerformanceRegressionResult(
            workflow_name="test_workflow",
            fixture_path="/test/font.ttf",
            baseline_duration_ms=50.0,
            current_duration_ms=60.0,
            regression_ratio=1.2,
            threshold_ms=20.0,
            passed=True,
            delta_ms=10.0,
            delta_percent=20.0,
        )

        assert assert_no_regression(result, raise_on_regression=True) is True

    def test_assert_no_regression_raises(self) -> None:
        """Verify assert_no_regression raises PerformanceRegressionError on failure."""
        result = PerformanceRegressionResult(
            workflow_name="test_workflow",
            fixture_path="/test/font.ttf",
            baseline_duration_ms=50.0,
            current_duration_ms=80.0,
            regression_ratio=1.6,
            threshold_ms=20.0,
            passed=False,
            delta_ms=30.0,
            delta_percent=60.0,
        )

        with pytest.raises(PerformanceRegressionError) as exc_info:
            assert_no_regression(result, raise_on_regression=True)

        assert "test_workflow" in str(exc_info.value)
        assert "30.0" in str(exc_info.value)

    def test_assert_no_regression_returns_false_when_not_raising(self) -> None:
        """Verify assert_no_regression returns False when not raising."""
        result = PerformanceRegressionResult(
            workflow_name="test_workflow",
            fixture_path="/test/font.ttf",
            baseline_duration_ms=50.0,
            current_duration_ms=80.0,
            regression_ratio=1.6,
            threshold_ms=20.0,
            passed=False,
            delta_ms=30.0,
            delta_percent=60.0,
        )

        assert assert_no_regression(result, raise_on_regression=False) is False

    def test_run_performance_suite_executes(self, temp_baseline_path: Path) -> None:
        """Verify run_performance_suite executes workflows and returns results."""
        FontLoader.open(FIXTURE_ROBOTO)

        def load_workflow() -> None:
            FontLoader.open(FIXTURE_ROBOTO)

        results = run_performance_suite(
            benchmarks=[
                {
                    "name": "font_load",
                    "fixture_path": str(FIXTURE_ROBOTO),
                    "runner": load_workflow,
                    "iterations": 2,
                    "warmup": 1,
                }
            ],
            baseline_path=temp_baseline_path,
            threshold_ms=1000.0,
        )

        assert len(results) == 1
        assert isinstance(results[0], PerformanceRegressionResult)
        assert results[0].workflow_name == "font_load"

    def test_run_performance_suite_saves_baselines(self, temp_baseline_path: Path) -> None:
        """Verify run_performance_suite saves baselines after runs."""
        FontLoader.open(FIXTURE_ROBOTO)

        def load_workflow() -> None:
            FontLoader.open(FIXTURE_ROBOTO)

        run_performance_suite(
            benchmarks=[
                {
                    "name": "font_load",
                    "fixture_path": str(FIXTURE_ROBOTO),
                    "runner": load_workflow,
                    "iterations": 2,
                }
            ],
            baseline_path=temp_baseline_path,
            threshold_ms=1000.0,
        )

        assert temp_baseline_path.exists()
        baselines = load_baselines(temp_baseline_path)
        assert "font_load" in baselines


class TestPerformanceWorkflows:
    """Tests for specific workflow performance measurements."""

    @MARKER
    def test_webfontoptimizer_build_timing(self) -> None:
        """Verify WebFontOptimizer.build timing meets threshold (<100ms for load)."""
        from aspose_font import WebFontOptimizer

        font = FontLoader.open(FIXTURE_ROBOTO)
        start_time = time.perf_counter()
        result = WebFontOptimizer.build(
            font,
            source_path=FIXTURE_ROBOTO,
            presets=("latin",),
            text="Aspose Web",
            include_woff=False,
        )
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        assert elapsed_ms < 100.0, f"WebFontOptimizer.build took {elapsed_ms:.2f}ms, exceeds 100ms threshold"
        assert result is not None

    @MARKER
    def test_variableinstancebuilder_build_package_timing(self) -> None:
        """Verify VariableInstanceBuilder.build_package timing completes."""
        from aspose_font import VariableInstanceBuilder

        font = FontLoader.open(FIXTURE_ROBOTOGVAR)
        builder = VariableInstanceBuilder(font)
        start_time = time.perf_counter()
        result = builder.build_package(
            names=["Regular"],
            naming_strategy="instance-family",
        )
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        assert elapsed_ms < 5000.0, f"VariableInstanceBuilder.build_package took {elapsed_ms:.2f}ms"
        assert result is not None

    @MARKER
    def test_fontqareporter_build_timing(self) -> None:
        """Verify FontQaReporter.build timing meets threshold (<200ms for full pipeline)."""
        from aspose_font import FontQaReporter

        font = FontLoader.open(FIXTURE_ROBOTO)
        start_time = time.perf_counter()
        _ = FontQaReporter.build(
            font,
            source_label=str(FIXTURE_ROBOTO),
            presets=("latin",),
            text="QA Test String",
        )
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        assert elapsed_ms < 200.0, f"FontQaReporter.build took {elapsed_ms:.2f}ms, exceeds 200ms threshold"


def test_variable_font_load_performance() -> None:
    """Verify FontLoader.open loads Roboto Variable within performance threshold (<=150ms).

    This test enforces a CI performance regression gate for raw font loading.
    The measurement is repeated 3 times and uses the maximum to account for CI variance.

    Threshold: 150ms (CI regression gate for raw variable font load)
    Baseline: ~4ms on developer machines; CI runners may be slower
    Repeats: 3 measurements, taking the maximum for stability

    Reference font: Roboto-VariableFont_wdth,wght.ttf
    Reference: FONT-351, Phase 4: Reliability Matrix & CI Performance Regression.
    """
    font_path = FIXTURE_ROOT / "Roboto-VariableFont_wdth,wght.ttf"
    if not font_path.exists():
        font_path = FIXTURE_ROOT.parent / "Roboto-VariableFont_wdth,wght.ttf"
    if not font_path.exists():
        raise FileNotFoundError(f"Variable font not found at {font_path}")

    font = FontLoader.open(font_path)
    assert font.is_variable, "Test fixture must be a variable font"

    repeat_count = 3
    elapsed_list: list[float] = []

    for _ in range(repeat_count):
        load_time = measure_load_time(font_path)
        elapsed_list.append(load_time)

    max_elapsed_seconds = max(elapsed_list)
    max_elapsed_ms = max_elapsed_seconds * 1000

    threshold_seconds = 0.15

    assert max_elapsed_seconds <= threshold_seconds, (
        f"Variable font load took {max_elapsed_ms:.2f}ms (max of {repeat_count} runs), "
        f"exceeds CI regression threshold of {threshold_seconds * 1000}ms. "
        f"Individual runs: {[f'{e*1000:.2f}ms' for e in elapsed_list]}. "
        f"This indicates a performance regression in FontLoader.open for variable fonts."
    )
