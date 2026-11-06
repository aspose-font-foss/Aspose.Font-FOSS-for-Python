"""Performance regression test for Web Font Optimizer load time (FONT-328)."""

from __future__ import annotations

import time
from pathlib import Path

from aspose_font import WebFontOptimizer
from aspose_font.ttf.font import TtfFont


def test_web_optimizer_load_performance(roboto: TtfFont) -> None:
    """Verify WebFontOptimizer.build total elapsed time meets performance regression threshold (<=1500ms).

    This test enforces a performance regression gate for the Web Font Optimizer workflow
    on CI runners. The test measures the full build time from font load through optimization
    and output generation.

    Threshold: 1500ms (measured ~550ms locally; accounts for slower CI runners; full build includes load, subset, compress, write)

    Reference font: Roboto-VariableFont_wdth,wght.ttf
    Reference: FONT-328, Phase 4: Reliability Matrix & CI Performance Regression.
    """
    start_time = time.perf_counter()
    WebFontOptimizer.build(
        roboto,
        source_path=Path("testdata/Roboto-VariableFont_wdth,wght.ttf"),
        presets=("latin",),
        include_woff=False,
    )
    elapsed_ms = (time.perf_counter() - start_time) * 1000

    assert elapsed_ms <= 1500, (
        f"WebFontOptimizer.build took {elapsed_ms:.2f}ms, exceeds 1500ms CI regression threshold"
    )
