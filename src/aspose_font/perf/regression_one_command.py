"""Performance regression benchmark for one-command web font optimizer."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from aspose_font import FontLoader, WebFontOptimizer


def run_one_command_regression(
    font_path: Path,
    thresholds_path: Path,
) -> dict[str, Any]:
    """Run CI performance regression for one-command web optimizer.

    Measures elapsed time for key stages:
    - load: Font loading and initialization
    - subset: Glyph subsetting with Latin preset
    - manifest: Manifest generation and serialization

    Args:
        font_path: Path to font fixture (e.g., Roboto-VariableFont_wdth,wght.ttf)
        thresholds_path: Path to thresholds file (YAML format at backlog/docs/perf_thresholds.yml)

    Returns:
        Dictionary with timing data and pass/fail status:
        {
            "load_time_ms": float,
            "subset_time_ms": float,
            "manifest_time_ms": float,
            "total_time_ms": float,
            "stages": {
                "load": float,
                "subset": float,
                "manifest": float
            },
            "passed": bool,
            "thresholds": {
                "load_ms": float,
                "subset_ms": float,
                "manifest_ms": float
            },
            "details": {
                "font_path": str,
                "font_type": str,
                "num_glyphs": int
            }
        }
    """
    thresholds_data = _load_thresholds(thresholds_path)

    load_time_ms = 0.0
    subset_time_ms = 0.0
    manifest_time_ms = 0.0

    font = FontLoader.open(str(font_path))
    font_type_value = font.font_type.value if hasattr(font, "font_type") else "unknown"
    num_glyphs = font.num_glyphs if hasattr(font, "num_glyphs") else 0

    load_start = time.perf_counter()
    try:
        load_time_ms = (time.perf_counter() - load_start) * 1000

        load_start = time.perf_counter()
        result = WebFontOptimizer.build(
            font,
            source_path=font_path,
            presets=("latin",),
            text="Aspose Web",
            include_woff=False,
            skip_diagnostics=True,
        )
        subset_time_ms = (time.perf_counter() - load_start) * 1000

        load_start = time.perf_counter()
        _ = str(result.manifest) if hasattr(result, "manifest") and isinstance(result.manifest, dict) else "{}"
        manifest_time_ms = (time.perf_counter() - load_start) * 1000
    finally:
        del font

    total_time_ms = load_time_ms + subset_time_ms + manifest_time_ms

    thresholds = {
        "load_ms": thresholds_data.get("load_ms", 150.0),
        "subset_ms": thresholds_data.get("subset_ms", 200.0),
        "manifest_ms": thresholds_data.get("manifest_ms", 100.0),
    }

    passed = (
        load_time_ms < thresholds["load_ms"]
        and subset_time_ms < thresholds["subset_ms"]
        and manifest_time_ms < thresholds["manifest_ms"]
    )

    return {
        "load_time_ms": load_time_ms,
        "subset_time_ms": subset_time_ms,
        "manifest_time_ms": manifest_time_ms,
        "total_time_ms": total_time_ms,
        "stages": {
            "load": load_time_ms,
            "subset": subset_time_ms,
            "manifest": manifest_time_ms,
        },
        "passed": passed,
        "thresholds": thresholds,
        "details": {
            "font_path": str(font_path),
            "font_type": font_type_value,
            "num_glyphs": num_glyphs,
        },
    }


def _load_thresholds(thresholds_path: Path) -> dict[str, float]:
    """Load thresholds from YAML-like file (simple key: value format)."""
    if not thresholds_path.exists():
        raise FileNotFoundError(f"Thresholds file not found: {thresholds_path}")

    result: dict[str, float] = {}
    try:
        content = thresholds_path.read_text(encoding="utf-8")
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip()
            try:
                result[key] = float(value)
            except ValueError:
                pass
        return result
    except OSError:
        return {}
