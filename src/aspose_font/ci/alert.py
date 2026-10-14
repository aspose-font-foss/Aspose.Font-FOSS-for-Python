from __future__ import annotations

import json
from pathlib import Path


def check_drift(report_path: str) -> dict:
    """Check performance regression drift from a JSON report.

    Reads a performance JSON report and compares build_time_ms against threshold_ms.

    Args:
        report_path: Path to the JSON report file.

    Returns:
        Dict with keys:
        - drift (bool): True if build_time_ms > threshold_ms
        - message (str): Human-readable message
        - build_time_ms (float): Actual build time
        - threshold_ms (float): Threshold value
        - within_threshold (bool): Inverse of drift
    """
    path = Path(report_path)
    if not path.exists():
        raise FileNotFoundError(f"Report not found: {report_path}")

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {report_path}: {exc}") from exc

    build_time_ms = data.get("build_time_ms")
    threshold_ms = data.get("threshold_ms")

    if build_time_ms is None:
        raise ValueError(f"Missing 'build_time_ms' in {report_path}")
    if threshold_ms is None:
        raise ValueError(f"Missing 'threshold_ms' in {report_path}")

    drift = build_time_ms > threshold_ms
    within_threshold = not drift

    if drift:
        message = (
            f"Performance drift detected: build took {build_time_ms:.2f}ms "
            f"(threshold: {threshold_ms:.2f}ms)"
        )
    else:
        message = (
            f"Performance within threshold: build took {build_time_ms:.2f}ms "
            f"(threshold: {threshold_ms:.2f}ms)"
        )

    return {
        "drift": drift,
        "message": message,
        "build_time_ms": build_time_ms,
        "threshold_ms": threshold_ms,
        "within_threshold": within_threshold,
    }
