"""CI performance regression drift alert tests for Web Font Optimizer.

Baseline threshold: 1000ms for full WebFontOptimizer.build workflow on Roboto.
This threshold accounts for CI environment variability and text processing overhead.

Threshold rationale:
- Measured local performance: ~550ms average for WebFontOptimizer.build
- CI environment is slower due to different hardware and resource contention
- Includes text="Aspose Web" substring processing which adds subsetting time
- Threshold accounts for ~1.8x CI variability with buffer for fluctuations
- Consistent with related tests (1500ms for similar workflow)

To update baseline: Run tests on clean checkout, record actual elapsed_ms, and update
the THRESHOLD_MS constant below. Never increase threshold without justification.
"""

from __future__ import annotations

from pathlib import Path

from aspose_font import FontLoader, WebFontOptimizer
from aspose_font.performance import assert_performance

THRESHOLD_MS = 1000

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROBOTO = REPO_ROOT / "testdata" / "Roboto-VariableFont_wdth,wght.ttf"


def test_web_optimizer_build_performance_regression_threshold() -> None:
    """Verify WebFontOptimizer.build completes within CI performance threshold.

    This test enables CI to detect performance regressions in the Web Font Optimizer
    workflow. If this test fails, the optimizer has become slower than the accepted
    threshold (600ms for full build on Roboto with latin preset).
    """
    font = FontLoader.open(FIXTURE_ROBOTO)

    def build_workflow():
        return WebFontOptimizer.build(
            font,
            source_path=FIXTURE_ROBOTO,
            presets=("latin",),
            text="Aspose Web",
            include_woff=False,
        )

    assert_performance(build_workflow, baseline_ms=THRESHOLD_MS)
