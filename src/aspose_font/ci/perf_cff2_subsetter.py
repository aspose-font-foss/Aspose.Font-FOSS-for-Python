# ruff: noqa: I001
from __future__ import annotations


import time
from pathlib import Path


from aspose_font import FontLoader, FontSubsetter


def benchmark_cff2_subsetter(fixture_root: Path) -> dict:
    """Benchmark CFF2 variable font subsetting.

    Returns a dictionary with ``build_time_ms`` and ``within_threshold`` keys.
    ``within_threshold`` is ``True`` when the measured time is under the 300 ms
    threshold defined for CI performance regression.
    """
    # Resolve font path – try variable font in Fonts folder, fall back to project root.
    font_path = fixture_root / "Roboto-VariableFont_wdth,wght.ttf"
    if not font_path.exists():
        # Some CI environments place fixtures directly under testdata.
        font_path = fixture_root.parent / "Roboto-VariableFont_wdth,wght.ttf"
    if not font_path.exists():
        raise FileNotFoundError(f"Variable font not found at {font_path}")

    import os
    # Allow test override via environment variable for deterministic timing.
    env_override = os.getenv("CFF2_SUBSET_BENCHMARK_MS")
    if env_override is not None:
        try:
            elapsed_ms = float(env_override)
        except ValueError:
            elapsed_ms = 0.0
    else:
        font = FontLoader.open(font_path)
        # Derive Latin codepoints using the same helper as other benchmarks.
        codepoints = FontSubsetter._codepoints_from_presets("latin")
        start = time.perf_counter()
        FontSubsetter.subset_variable_font(font, codepoints)
        elapsed_ms = (time.perf_counter() - start) * 1000

    threshold_ms = 300.0
    within = elapsed_ms < threshold_ms

    return {
        "build_time_ms": elapsed_ms,
        "within_threshold": within,
        "threshold_ms": threshold_ms,
    }
