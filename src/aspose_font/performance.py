"""Performance benchmark utilities for core font workflows."""

from __future__ import annotations

import dataclasses
import json
import time
from pathlib import Path
from typing import Any

from aspose_font import FontLoader


@dataclasses.dataclass(frozen=True, slots=True)
class PerformanceBenchmark:
    """Performance baseline for a specific workflow."""

    workflow_name: str
    operation: str
    threshold_ms: int
    sample_count: int = 10
    confidence: float = 0.95


@dataclasses.dataclass(frozen=True, slots=True)
class PerformanceMeasurement:
    """Single measurement of a workflow performance."""

    workflow_name: str
    operation: str
    elapsed_ms: float
    font_size_bytes: int
    timestamp: str


@dataclasses.dataclass(frozen=True, slots=True)
class PerformanceBaselineReport:
    """Complete performance baseline report for a workflow."""

    workflow_name: str
    measurements: list[PerformanceMeasurement]
    statistics: dict[str, float]
    threshold_ms: int
    passing: bool
    deviation_percent: float
    root_causes: list[str]


@dataclasses.dataclass(frozen=True, slots=True)
class PerformanceRegressionPackage:
    """Self-contained performance regression package."""

    report: PerformanceBaselineReport
    baseline_path: Path | None
    reference_measurements: list[PerformanceMeasurement] | None
    remediation_notes: list[dict[str, str]]
    metadata: dict[str, Any]


# Backward compatibility aliases
PerformanceResult = PerformanceMeasurement
PerformanceReport = PerformanceBaselineReport


# Standard benchmarks (from PROJECT_CONTEXT.md)
BENCHMARKS: dict[str, PerformanceBenchmark] = {
    "web_optimizer_load": PerformanceBenchmark(
        workflow_name="Web Font Optimizer",
        operation="Load + Preview",
        threshold_ms=100,
    ),
    "web_optimizer_subset": PerformanceBenchmark(
        workflow_name="Web Font Optimizer",
        operation="Subset",
        threshold_ms=50,
    ),
    "qa_report_generation": PerformanceBenchmark(
        workflow_name="Font QA Report",
        operation="Full Generation",
        threshold_ms=200,
    ),
}


def measure_workflow_performance(
    font_path: Path,
    workflow: str,
    repetitions: int = 10,
    warmup: int = 2,
) -> list[PerformanceMeasurement]:
    """
    Measure performance of a specific workflow multiple times.

    Args:
        font_path: Path to test font
        workflow: One of "web_optimizer_load", "web_optimizer_subset", "qa_report_generation"
        repetitions: Number of measurements to take
        warmup: Number of initial runs to exclude from measurement

    Returns:
        List of PerformanceMeasurement objects
    """
    measurements: list[PerformanceMeasurement] = []
    benchmark = BENCHMARKS[workflow]

    for i in range(warmup + repetitions):
        is_warmup = i < warmup
        start = time.perf_counter()

        if workflow == "web_optimizer_load":
            _measure_web_optimizer_load(font_path)
        elif workflow == "web_optimizer_subset":
            _measure_web_optimizer_subset(font_path)
        elif workflow == "qa_report_generation":
            _measure_qa_report_generation(font_path)
        else:
            raise ValueError(f"Unknown workflow: {workflow}")

        elapsed_ms = (time.perf_counter() - start) * 1000

        if not is_warmup:
            measurements.append(
                PerformanceMeasurement(
                    workflow_name=benchmark.workflow_name,
                    operation=benchmark.operation,
                    elapsed_ms=elapsed_ms,
                    font_size_bytes=font_path.stat().st_size,
                    timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                )
            )

    return measurements


def _measure_web_optimizer_load(font_path: Path) -> None:
    """Measure Web Font Optimizer load + preview operation."""
    from aspose_font import WebFontOptimizer

    font = FontLoader.open(str(font_path))
    WebFontOptimizer.build(
        font,
        source_path=font_path,
        presets=("latin",),
        text="Aspose Web",
        include_woff=False,
    )


def _measure_web_optimizer_subset(font_path: Path) -> None:
    """Measure Web Font Optimizer subset operation."""
    from aspose_font import WebFontOptimizer

    font = FontLoader.open(str(font_path))
    WebFontOptimizer.build(
        font,
        source_path=font_path,
        presets=("latin",),
        text="Aspose Web",
        include_woff=False,
    )


def _measure_qa_report_generation(font_path: Path) -> None:
    """Measure Font QA Report generation operation."""
    from aspose_font import FontQaReporter

    font = FontLoader.open(str(font_path))
    FontQaReporter.build(
        font,
        source_label=str(font_path),
        presets=("latin",),
        text="QA Test String",
    )


def calculate_statistics(measurements: list[PerformanceMeasurement]) -> dict[str, float]:
    """
    Calculate statistical summary from measurements.

    Returns:
        Dict with keys: mean, std, min, max, p95, p99
    """
    if not measurements:
        return {
            "mean": 0.0,
            "std": 0.0,
            "min": 0.0,
            "max": 0.0,
            "p95": 0.0,
            "p99": 0.0,
        }

    values = [m.elapsed_ms for m in measurements]
    n = len(values)

    mean = sum(values) / n
    variance = sum((x - mean) ** 2 for x in values) / n
    std = variance**0.5
    min_val = min(values)
    max_val = max(values)

    sorted_values = sorted(values)
    p95_idx = int(0.95 * (n - 1))
    p99_idx = int(0.99 * (n - 1))
    p95 = sorted_values[p95_idx]
    p99 = sorted_values[p99_idx]

    return {
        "mean": mean,
        "std": std,
        "min": min_val,
        "max": max_val,
        "p95": p95,
        "p99": p99,
    }


def build_baseline_report(
    measurements: list[PerformanceMeasurement],
    benchmark: PerformanceBenchmark,
) -> PerformanceBaselineReport:
    """
    Build comprehensive performance baseline report.

    Returns:
        PerformanceBaselineReport with statistics and pass/fail status
    """
    statistics = calculate_statistics(measurements)

    threshold_ms = benchmark.threshold_ms
    mean_ms = statistics["mean"]
    passing = mean_ms < threshold_ms
    deviation_percent = ((mean_ms - threshold_ms) / threshold_ms) * 100 if threshold_ms > 0 else 0.0

    root_causes: list[str] = []
    if not passing:
        if statistics["max"] >= threshold_ms:
            root_causes.append("Maximum latency exceeds threshold")
        if statistics["std"] > threshold_ms * 0.1:
            root_causes.append("High variance in latency measurements")
        if statistics["p95"] >= threshold_ms:
            root_causes.append("95th percentile latency exceeds threshold")

    return PerformanceBaselineReport(
        workflow_name=benchmark.workflow_name,
        measurements=measurements,
        statistics=statistics,
        threshold_ms=threshold_ms,
        passing=passing,
        deviation_percent=deviation_percent,
        root_causes=root_causes,
    )


def generate_remediation_notes(report: PerformanceBaselineReport) -> list[dict[str, str]]:
    """
    Generate actionable remediation guidance for failing benchmarks.

    Returns:
        List of diagnostic notes with severity and recommended action
    """
    notes: list[dict[str, str]] = []

    if report.passing:
        return notes

    for cause in report.root_causes:
        if "Maximum latency" in cause:
            notes.append({
                "severity": "warning",
                "message": "Maximum latency exceeds threshold. Consider caching or lazy loading.",
            })
        elif "variance" in cause:
            notes.append({
                "severity": "warning",
                "message": "High variance detected. Consider running on dedicated hardware.",
            })
        elif "95th percentile" in cause:
            notes.append({
                "severity": "critical",
                "message": "95th percentile latency exceeds threshold. Optimize slow paths.",
            })

    notes.append({
        "severity": "info",
        "message": f"Mean latency: {report.statistics['mean']:.2f}ms, Threshold: {report.threshold_ms}ms",
    })

    return notes


def run_performance_regression_check(
    font_path: Path,
    benchmarks: dict[str, PerformanceBenchmark] | None = None,
    baseline_path: Path | None = None,
) -> PerformanceRegressionPackage:
    """
    Run complete performance regression validation.

    This function:
    1. Measures performance for all configured benchmarks
    2. Builds baseline reports for each workflow
    3. Compares against thresholds
    4. Generates remediation guidance if failing

    Returns:
        PerformanceRegressionPackage with full report and diagnostics
    """
    if benchmarks is None:
        benchmarks = BENCHMARKS

    workflow_measurements: dict[str, list[PerformanceMeasurement]] = {}
    workflow_reports: dict[str, PerformanceBaselineReport] = {}

    for workflow_name, benchmark in benchmarks.items():
        measurements = measure_workflow_performance(
            font_path=font_path,
            workflow=workflow_name,
            repetitions=benchmark.sample_count,
            warmup=2,
        )
        workflow_measurements[workflow_name] = measurements

        report = build_baseline_report(measurements, benchmark)
        workflow_reports[workflow_name] = report

    main_report = next(iter(workflow_reports.values()))

    all_passing = all(r.passing for r in workflow_reports.values())
    if not all_passing:
        overall_report = next(r for r in workflow_reports.values() if not r.passing)
    else:
        overall_report = main_report

    remediation_notes: list[dict[str, str]] = []
    for report in workflow_reports.values():
        if not report.passing:
            remediation_notes.extend(generate_remediation_notes(report))

    reference_measurements: list[PerformanceMeasurement] | None = None
    if baseline_path and baseline_path.exists():
        try:
            data = json.loads(baseline_path.read_text(encoding="utf-8"))
            reference_measurements = [
                PerformanceMeasurement(
                    workflow_name=item["workflow_name"],
                    operation=item["operation"],
                    elapsed_ms=item["elapsed_ms"],
                    font_size_bytes=item["font_size_bytes"],
                    timestamp=item["timestamp"],
                )
                for item in data.get("measurements", [])
            ]
        except (json.JSONDecodeError, KeyError, OSError):
            pass

    return PerformanceRegressionPackage(
        report=overall_report,
        baseline_path=baseline_path,
        reference_measurements=reference_measurements,
        remediation_notes=remediation_notes,
        metadata={
            "workflow_count": len(benchmarks),
            "all_passing": all_passing,
            "reports": {name: report.passing for name, report in workflow_reports.items()},
        },
    )


def assert_performance(callable_: Any, *args: Any, baseline_ms: int) -> Any:
    """Assert that a callable's execution time does not exceed the baseline threshold.

    Measures wall-clock duration using time.perf_counter() and raises AssertionError
    if execution exceeds baseline_ms.

    Args:
        callable_: The function/method to measure
        *args: Arguments to pass to the callable
        baseline_ms: Maximum allowed execution time in milliseconds

    Raises:
        AssertionError: If execution time exceeds baseline_ms

    Returns:
        The result of the callable

    Example:
        >>> def my_workflow(): return expensive_operation()
        >>> assert_performance(my_workflow, baseline_ms=100)
    """
    start_time = time.perf_counter()
    result = callable_(*args)
    elapsed_ms = (time.perf_counter() - start_time) * 1000

    if elapsed_ms > baseline_ms:
        raise AssertionError(
            f"Performance regression detected: {callable_.__name__}() took "
            f"{elapsed_ms:.2f}ms, exceeds {baseline_ms}ms threshold"
        )

    return result


def measure_load_time(font_path: Path) -> float:
    """Measure time to load a font file using FontLoader.open.

    Args:
        font_path: Path to font file (TTF, OTF, WOFF, WOFF2, etc.)

    Returns:
        Load time in seconds (float)
    """
    start_time = time.perf_counter()
    FontLoader.open(str(font_path))
    elapsed_seconds = time.perf_counter() - start_time
    return elapsed_seconds
