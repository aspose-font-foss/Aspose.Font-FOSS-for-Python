"""Performance regression test for animation export workflow (FONT-343)."""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from aspose_font import FontLoader
from aspose_font.animation import AnimationPreviewBuilder
from aspose_font.ttf.font import TtfFont


@pytest.fixture(scope="module")
def roboto_variable(testdata_dir: Path) -> TtfFont:
    """Load Roboto variable font for animation export testing."""
    font_path = testdata_dir / "Roboto-VariableFont_wdth,wght.ttf"
    font = FontLoader.open(str(font_path))
    assert isinstance(font, TtfFont)
    return font


def test_animation_export_performance(roboto_variable: TtfFont, tmp_path: Path) -> None:
    """Verify AnimationPreviewBuilder.build_export_package completes within CI threshold.

    This test enables CI to detect performance regressions in the animation export
    workflow. If this test fails, the animation export has become slower than the
    accepted threshold (1500ms for full export on Roboto with standard preset).

    Threshold rationale:
    - CI runners are slower than developer machines
    - Full workflow includes: axis sweep rendering + APNG encoding + manifest generation
    - Measured performance: ~1095ms on local machine
    - CI buffer: ~400ms to accommodate variability

    Acceptance Criteria:
    1. Test measures elapsed time for full animation export
    2. Test asserts time is ≤ 1500ms (calibrated against actual ~1100ms baseline)
    3. Test passes on CI and local pytest runs
    4. Lint passes for the new file
    """
    start = time.perf_counter()

    package = AnimationPreviewBuilder.build_export_package(
        roboto_variable,
        axis_tag="wdth",
        start_val=75.0,
        end_val=100.0,
        frames=3,
        fps=10,
        text="Test",
        preset="standard",
    )

    output_dir = package.write_to(tmp_path)

    elapsed_ms = (time.perf_counter() - start) * 1000

    assert output_dir.is_dir()
    assert (output_dir / package.animation.filename).exists()
    assert (output_dir / package.manifest_name).exists()

    # Performance gate: must complete within 1500ms on CI runners
    # Threshold calibrated against measured performance (~1100ms) with CI buffer
    assert elapsed_ms <= 1500.0, (
        f"Animation export performance degraded: {elapsed_ms:.1f}ms exceeds 1500ms threshold"
    )
