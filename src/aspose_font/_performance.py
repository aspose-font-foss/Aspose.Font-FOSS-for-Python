"""Private module for performance regression infrastructure."""

from __future__ import annotations

import dataclasses
import json
import sys
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Union


@dataclasses.dataclass(frozen=True)
class PerformanceBenchmark:
    """Immutable performance benchmark record."""

    workflow_name: str
    fixture_path: str
    fixture_size_bytes: int
    duration_ms: float
    timestamp: str
    python_version: str
    platform: str


@dataclasses.dataclass(frozen=True)
class PerformanceRegressionResult:
    """Result of performance regression comparison."""

    workflow_name: str
    fixture_path: str
    baseline_duration_ms: float
    current_duration_ms: float
    regression_ratio: float
    threshold_ms: float
    passed: bool
    delta_ms: float
    delta_percent: float


class PerformanceRegressionError(Exception):
    """Raised when performance regression exceeds threshold."""

    def __init__(self, message: str, results: List[PerformanceRegressionResult]) -> None:
        super().__init__(message)
        self.results = results


def measure_workflow(
    name: str,
    fixture_path: Union[str, Path],
    runner: Callable[[], None],
    iterations: int = 3,
    warmup: int = 1,
) -> PerformanceBenchmark:
    """Measure workflow performance and return benchmark record.

    Args:
        name: Workflow name for identification
        fixture_path: Path to the font fixture being tested
        runner: Callable that executes the workflow to measure
        iterations: Number of timed measurements to take
        warmup: Number of initial runs to exclude from measurement

    Returns:
        PerformanceBenchmark record with timing data
    """
    fixture_path = Path(fixture_path)
    fixture_size = fixture_path.stat().st_size

    for i in range(warmup + iterations):
        if i < warmup:
            runner()
        else:
            start_time = time.perf_counter()
            runner()
            duration_ms = (time.perf_counter() - start_time) * 1000

    return PerformanceBenchmark(
        workflow_name=name,
        fixture_path=str(fixture_path),
        fixture_size_bytes=fixture_size,
        duration_ms=duration_ms,
        timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        python_version=sys.version,
        platform=sys.platform,
    )


def load_baselines(baseline_path: Path) -> Dict[str, List[PerformanceBenchmark]]:
    """Load baseline benchmarks from JSON file.

    Args:
        baseline_path: Path to JSON file containing baseline data

    Returns:
        Dictionary mapping workflow names to lists of benchmark records
    """
    if not baseline_path.exists():
        return {}

    try:
        data = json.loads(baseline_path.read_text(encoding="utf-8"))
        result: Dict[str, List[PerformanceBenchmark]] = {}
        for workflow_name, records in data.items():
            result[workflow_name] = [
                PerformanceBenchmark(
                    workflow_name=record["workflow_name"],
                    fixture_path=record["fixture_path"],
                    fixture_size_bytes=record["fixture_size_bytes"],
                    duration_ms=record["duration_ms"],
                    timestamp=record["timestamp"],
                    python_version=record["python_version"],
                    platform=record["platform"],
                )
                for record in records
            ]
        return result
    except (json.JSONDecodeError, KeyError, OSError):
        return {}


def save_baselines(baselines: Dict[str, List[PerformanceBenchmark]], baseline_path: Path) -> None:
    """Save baseline benchmarks to JSON file.

    Args:
        baselines: Dictionary mapping workflow names to benchmark records
        baseline_path: Path to output JSON file
    """
    data: Dict[str, List[Dict[str, Any]]] = {}
    for workflow_name, benchmarks in baselines.items():
        data[workflow_name] = [
            {
                "workflow_name": b.workflow_name,
                "fixture_path": b.fixture_path,
                "fixture_size_bytes": b.fixture_size_bytes,
                "duration_ms": b.duration_ms,
                "timestamp": b.timestamp,
                "python_version": b.python_version,
                "platform": b.platform,
            }
            for b in benchmarks
        ]

    baseline_path.parent.mkdir(parents=True, exist_ok=True)
    baseline_path.write_text(
        json.dumps(data, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def compare_performance(
    current: PerformanceBenchmark,
    baselines: List[PerformanceBenchmark],
    threshold_ms: float = 20.0,
    threshold_percent: float = 20.0,
) -> PerformanceRegressionResult:
    """Compare current performance against baselines.

    Args:
        current: Current benchmark run
        baselines: List of baseline benchmarks for comparison
        threshold_ms: Absolute threshold for regression detection
        threshold_percent: Percentage threshold for regression detection

    Returns:
        PerformanceRegressionResult with comparison data
    """
    if not baselines:
        return PerformanceRegressionResult(
            workflow_name=current.workflow_name,
            fixture_path=current.fixture_path,
            baseline_duration_ms=0.0,
            current_duration_ms=current.duration_ms,
            regression_ratio=1.0,
            threshold_ms=threshold_ms,
            passed=True,
            delta_ms=0.0,
            delta_percent=0.0,
        )

    avg_baseline = sum(b.duration_ms for b in baselines) / len(baselines)
    current_ms = current.duration_ms
    delta_ms = current_ms - avg_baseline
    delta_percent = (delta_ms / avg_baseline * 100) if avg_baseline > 0 else 0.0
    regression_ratio = current_ms / avg_baseline if avg_baseline > 0 else 1.0

    passed = delta_ms <= threshold_ms and delta_percent <= threshold_percent

    return PerformanceRegressionResult(
        workflow_name=current.workflow_name,
        fixture_path=current.fixture_path,
        baseline_duration_ms=avg_baseline,
        current_duration_ms=current_ms,
        regression_ratio=regression_ratio,
        threshold_ms=threshold_ms,
        passed=passed,
        delta_ms=delta_ms,
        delta_percent=delta_percent,
    )


def assert_no_regression(
    result: PerformanceRegressionResult,
    raise_on_regression: bool = True,
) -> bool:
    """Assert performance did not regress.

    Args:
        result: Regression comparison result
        raise_on_regression: If True, raise exception when regression detected

    Returns:
        True if no regression, False otherwise

    Raises:
        PerformanceRegressionError: If regression detected and raise_on_regression=True
    """
    if result.passed:
        return True

    error_msg = (
        f"Performance regression detected in {result.workflow_name}: "
        f"+{result.delta_ms:.2f}ms ({result.delta_percent:.1f}% increase). "
        f"Threshold: {result.threshold_ms:.2f}ms"
    )
    if raise_on_regression:
        raise PerformanceRegressionError(error_msg, [result])
    return False


def run_performance_suite(
    benchmarks: List[Dict[str, Any]],
    baseline_path: Path,
    threshold_ms: float = 20.0,
    threshold_percent: float = 20.0,
) -> List[PerformanceRegressionResult]:
    """Run complete performance suite against baselines.

    Args:
        benchmarks: List of benchmark configurations with 'name', 'fixture_path', and 'runner' keys
        baseline_path: Path to baseline JSON file
        threshold_ms: Absolute threshold for regression detection
        threshold_percent: Percentage threshold for regression detection

    Returns:
        List of regression results for each benchmark
    """
    results: List[PerformanceRegressionResult] = []
    baselines = load_baselines(baseline_path)

    for benchmark_config in benchmarks:
        name = benchmark_config["name"]
        fixture_path = Path(benchmark_config["fixture_path"])
        runner = benchmark_config["runner"]

        current_benchmark = measure_workflow(
            name=name,
            fixture_path=fixture_path,
            runner=runner,
            iterations=benchmark_config.get("iterations", 3),
            warmup=benchmark_config.get("warmup", 1),
        )

        baseline_list = baselines.get(name, [])
        result = compare_performance(
            current=current_benchmark,
            baselines=baseline_list,
            threshold_ms=threshold_ms,
            threshold_percent=threshold_percent,
        )
        results.append(result)

        baselines[name] = baseline_list + [current_benchmark]

    save_baselines(baselines, baseline_path)

    return results
