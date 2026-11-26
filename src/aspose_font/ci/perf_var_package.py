from __future__ import annotations

import dataclasses
import json
import time
from pathlib import Path
from typing import Any

from aspose_font import FontLoader, VariableInstanceBuilder


def _find_baselines_path() -> Path:
    script_dir = Path(__file__).resolve()

    def _find_baselines_root() -> Path | None:
        for parents_level in range(1, 6):
            candidate = script_dir.parents[parents_level]
            baseline_file = candidate / "backlog" / "runtime" / "performance_var_package_baselines.json"
            if baseline_file.exists():
                return candidate
        return None

    root = _find_baselines_root()
    if root is None:
        root = script_dir.parents[3]

    return root / "backlog" / "runtime" / "performance_var_package_baselines.json"


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


def benchmark_var_package(fixture_root: Path) -> PerformanceMetric:
    """Benchmark VariableInstanceBuilder.build_package workflow.

    Measures the time to build a variable instance package from Roboto-VariableFont_wdth,wght.ttf
    using ci_fast_mode for performance regression testing.

    Baselines are loaded from backlog/runtime/performance_var_package_baselines.json and used to
    calculate variance percentage against the current build time.

    Threshold (100ms) represents the CI regression upper bound for acceptable performance
    with ci_fast_mode enabled (single instance, reduced preview size, no antialias).
    """
    baseline_store = _load_baselines()

    font_path = fixture_root / "Roboto-VariableFont_wdth,wght.ttf"
    if not font_path.exists():
        font_path = fixture_root.parent / "Roboto-VariableFont_wdth,wght.ttf"
    if not font_path.exists():
        raise FileNotFoundError(f"Variable font not found at {font_path}")

    font = FontLoader.open(font_path)

    if not font.is_variable:
        raise ValueError(f"Font at {font_path} is not a variable font")

    builder = VariableInstanceBuilder(font)

    start = time.perf_counter()
    builder.build_package(ci_fast_mode=True)
    elapsed_ms = (time.perf_counter() - start) * 1000

    threshold_ms = 100.0

    baseline_ms = baseline_store.get("var_package_build")

    variance_percent: float | None = None
    if baseline_ms is not None and baseline_ms > 0:
        variance_percent = ((elapsed_ms - baseline_ms) / baseline_ms) * 100

    passed = elapsed_ms < threshold_ms

    metric = PerformanceMetric(
        name="var_package_build",
        elapsed_ms=elapsed_ms,
        threshold_ms=threshold_ms,
        passed=passed,
        baseline_ms=baseline_ms,
        variance_percent=variance_percent,
    )

    if passed and baseline_ms is None:
        _save_baselines({"var_package_build": elapsed_ms})

    return metric


def _get_baselines_path() -> Path:
    return _find_baselines_path()


def _load_baselines() -> dict[str, float]:
    """Load persisted baselines from backlog/runtime/performance_var_package_baselines.json."""
    baseline_path = _get_baselines_path()
    if not baseline_path.exists():
        return {}

    try:
        data = json.loads(baseline_path.read_text(encoding="utf-8"))
        return {str(k): float(v) for k, v in data.items()}
    except (json.JSONDecodeError, OSError):
        return {}


def _save_baselines(baselines: dict[str, float]) -> None:
    """Persist updated baselines to disk."""
    baseline_path = _get_baselines_path()
    baseline_path.parent.mkdir(parents=True, exist_ok=True)
    baseline_path.write_text(
        json.dumps(baselines, indent=2, sort_keys=True),
        encoding="utf-8",
    )
