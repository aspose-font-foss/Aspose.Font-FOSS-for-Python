"""CI performance regression test for Variable Instance Builder."""

from __future__ import annotations

import time
from pathlib import Path

from aspose_font import FontLoader, VariableInstanceBuilder

FIXTURE_ROOT = Path(__file__).resolve().parent.parent / "testdata"


def test_variable_instance_builder_performance(tmp_path: Path) -> None:
    """Verify VariableInstanceBuilder static instance generation completes within threshold.

    This test enforces a performance regression gate for VariableInstanceBuilder
    on CI runners. If this test fails, it indicates a performance regression
    in the variable font instancing workflow.

    Threshold: 100ms (CI regression gate; per src/aspose_font/ci/perf_var_package.py:80)
    Baseline: ~5000ms (full build without ci_fast_mode, from backlog/runtime/performance_var_package_baselines.json)
    With ci_fast_mode: ~50-100ms (single instance, reduced preview, no antialias)
    """
    font_path = FIXTURE_ROOT / "Roboto-VariableFont_wdth,wght.ttf"
    if not font_path.exists():
        font_path = FIXTURE_ROOT.parent / "Roboto-VariableFont_wdth,wght.ttf"
    if not font_path.exists():
        raise FileNotFoundError(f"Variable font not found at {font_path}")

    font = FontLoader.open(font_path)
    assert font.is_variable, "Test fixture must be a variable font"

    builder = VariableInstanceBuilder(font)

    start_time = time.perf_counter()
    package = builder.build_package(ci_fast_mode=True)
    elapsed_ms = (time.perf_counter() - start_time) * 1000

    assert package is not None

    threshold_ms = 100.0

    assert elapsed_ms <= threshold_ms, (
        f"VariableInstanceBuilder static instance generation took {elapsed_ms:.2f}ms, "
        f"exceeds CI regression threshold of {threshold_ms}ms. "
        f"This indicates a performance regression in the VariableInstanceBuilder workflow."
    )
