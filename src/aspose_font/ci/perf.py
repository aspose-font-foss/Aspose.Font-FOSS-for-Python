from __future__ import annotations

import dataclasses
import json
import time
from pathlib import Path
from typing import Any

from aspose_font import FontLoader, FontQaReporter, WebFontOptimizer
from aspose_font.subsetter import FontSubsetter

_BASELINES_PATH = Path(__file__).resolve().parent.parent.parent / "backlog" / "runtime" / "performance_baselines_ci.json"


class PerformanceRegressionError(Exception):
    """Raised when a performance benchmark exceeds its allowed threshold."""

    def __init__(self, message: str, metrics: list[PerformanceMetric]) -> None:
        super().__init__(message)
        self.metrics = metrics

    def __str__(self) -> str:
        lines = [super().__str__()]
        for metric in self.metrics:
            lines.append(f"  {metric.name}: {metric.elapsed_ms:.2f}ms (threshold: {metric.threshold_ms:.2f}ms)")
        return "\n".join(lines)


@dataclasses.dataclass(frozen=True, slots=True)
class PerformanceMetric:
    """Single benchmark measurement."""
    name: str
    elapsed_ms: float
    threshold_ms: float
    passed: bool
    baseline_ms: float | None
    variance_percent: float | None


@dataclasses.dataclass(frozen=True, slots=True)
class RegressionReport:
    """Full regression analysis report."""
    timestamp: str
    results: tuple[PerformanceMetric, ...]
    summary: dict[str, Any]


def run_ci_benchmarks(
    fixture_root: Path, *, baseline_margin_percent: float = 5.0
) -> RegressionReport:
    """Run CI performance tests and return regression report.

    Measured workflows:
    1. WebFontOptimizer.load (font + preview generation)
    2. WebFontOptimizer.subset (glyph subsetting on Roboto)
    3. FontSubsetter.subset (direct subsetting on Roboto)
    4. FontQaReporter.build (full QA report generation)
    """
    timestamps: dict[str, float] = {}
    metrics: list[PerformanceMetric] = []

    baseline_store = _load_baselines()

    roboto_path = fixture_root / "Roboto-Regular.ttf"
    if not roboto_path.exists():
        raise FileNotFoundError(f"Roboto font not found at {roboto_path}")

    font = FontLoader.open(roboto_path)

    # Benchmark 1: WebFontOptimizer.load (with diagnostics)
    load_start = time.perf_counter()
    WebFontOptimizer.build(
        font,
        source_path=roboto_path,
        presets=("latin",),
        text="Aspose Web",
        include_woff=False,
        skip_diagnostics=False,
    )
    load_elapsed_ms = (time.perf_counter() - load_start) * 1000
    timestamps["web_optimizer_load"] = load_elapsed_ms

    # Benchmark 2: WebFontOptimizer.subset (fast path without diagnostics)
    subset_start = time.perf_counter()
    WebFontOptimizer.build(
        font,
        source_path=roboto_path,
        presets=("latin",),
        text="Aspose Web",
        include_woff=False,
        skip_diagnostics=True,
    )
    subset_elapsed_ms = (time.perf_counter() - subset_start) * 1000
    timestamps["web_optimizer_subset"] = subset_elapsed_ms

    # Benchmark 3: FontSubsetter.subset (direct subsetting)
    codepoints = FontSubsetter._codepoints_from_presets("latin")
    subsetting_start = time.perf_counter()
    FontSubsetter.benchmark_subsetting(font, codepoints, runs=1)
    subsetting_elapsed_ms = (time.perf_counter() - subsetting_start) * 1000
    timestamps["subset_direct"] = subsetting_elapsed_ms

    # Benchmark 4: FontQaReporter.build
    qa_start = time.perf_counter()
    FontQaReporter.build(
        font,
        source_label=str(roboto_path),
        presets=("latin",),
        text="QA Test String",
    )
    qa_elapsed_ms = (time.perf_counter() - qa_start) * 1000
    timestamps["qa_report"] = qa_elapsed_ms

    thresholds: dict[str, float] = {
        "web_optimizer_load": 100.0,
        "web_optimizer_subset": 50.0,
        "subset_direct": 50.0,
        "qa_report": 200.0,
    }

    failed_metrics: list[PerformanceMetric] = []

    for name, elapsed_ms in timestamps.items():
        threshold_ms = thresholds[name]
        baseline_ms = baseline_store.get(name)

        variance_percent: float | None = None
        if baseline_ms is not None and baseline_ms > 0:
            variance_percent = ((elapsed_ms - baseline_ms) / baseline_ms) * 100

        if baseline_ms is not None:
            effective_threshold = threshold_ms * (1 + baseline_margin_percent / 100)
            baseline_threshold = baseline_ms * (1 + baseline_margin_percent / 100)
            effective_threshold = max(threshold_ms, baseline_threshold)
        else:
            effective_threshold = threshold_ms

        passed = elapsed_ms < effective_threshold

        metric = PerformanceMetric(
            name=name,
            elapsed_ms=elapsed_ms,
            threshold_ms=threshold_ms,
            passed=passed,
            baseline_ms=baseline_ms,
            variance_percent=variance_percent,
        )
        metrics.append(metric)

        if not passed:
            failed_metrics.append(metric)

    passed_count = sum(1 for m in metrics if m.passed)
    total_count = len(metrics)
    overall_status = "PASS" if passed_count == total_count else "FAIL"

    if failed_metrics:
        raise PerformanceRegressionError(
            f"{len(failed_metrics)} performance benchmarks exceeded their allowed thresholds",
            failed_metrics,
        )

    summary: dict[str, Any] = {
        "total_metrics": total_count,
        "passed": passed_count,
        "failed": total_count - passed_count,
        "overall_status": overall_status,
    }

    if baseline_store:
        summary["baseline_diffs"] = {
            m.name: {
                "current_ms": m.elapsed_ms,
                "baseline_ms": m.baseline_ms,
                "variance_percent": m.variance_percent,
            }
            for m in metrics
            if m.baseline_ms is not None
        }

    return RegressionReport(
        timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        results=tuple(metrics),
        summary=summary,
    )


def _load_baselines() -> dict[str, float]:
    """Load persisted baselines from backlog/runtime/performance_baselines_ci.json."""
    if not _BASELINES_PATH.exists():
        return {}

    try:
        data = json.loads(_BASELINES_PATH.read_text(encoding="utf-8"))
        return {str(k): float(v) for k, v in data.items()}
    except (json.JSONDecodeError, OSError):
        return {}


def _save_baselines(baselines: dict[str, float]) -> None:
    """Persist updated baselines to disk."""
    _BASELINES_PATH.parent.mkdir(parents=True, exist_ok=True)
    _BASELINES_PATH.write_text(
        json.dumps(baselines, indent=2, sort_keys=True),
        encoding="utf-8",
    )
