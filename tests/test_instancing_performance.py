"""CI performance regression test for Variable Instancing Build workflow."""

from __future__ import annotations

from pathlib import Path

from aspose_font import FontLoader, VariableInstanceBuilder

FIXTURE_ROOT = Path(__file__).resolve().parent.parent / "testdata"


def test_variable_instancing_build_performance() -> None:
    """Verify VariableInstanceBuilder.build_package ci_fast_mode completes within 100ms.

    This test enforces a CI performance regression gate for the Variable Instancing
    Build workflow (ci_fast_mode path). If this test fails, it indicates a performance
    regression in the variable font instancing or package generation workflow.

    Threshold: 100ms (CI regression gate; aligned with src/aspose_font/ci/perf_var_package.py:80)
    Baseline: ~5000ms (from backlog/runtime/performance_var_package_baselines.json)
    ci_fast_mode reduces build time by 50x through single instance, no avar, reduced preview.

    The 100ms threshold is the realistic CI upper bound for the optimized ci_fast_mode
    workflow, as documented in perf_var_package.py and verified in existing tests.
    """
    font_path = FIXTURE_ROOT / "Roboto-VariableFont_wdth,wght.ttf"
    if not font_path.exists():
        font_path = FIXTURE_ROOT.parent / "Roboto-VariableFont_wdth,wght.ttf"
    if not font_path.exists():
        raise FileNotFoundError(f"Variable font not found at {font_path}")

    font = FontLoader.open(font_path)
    assert font.is_variable, "Test fixture must be a variable font"

    builder = VariableInstanceBuilder(font)
    package = builder.build_package(ci_fast_mode=True)

    assert package is not None
    assert package.build_time_ms > 0, "VariableInstancePackage.build_time_ms should be recorded"

    threshold_ms = 100.0

    assert package.build_time_ms <= threshold_ms, (
        f"Variable Instancing Build (ci_fast_mode) took {package.build_time_ms:.2f}ms, "
        f"exceeds CI regression threshold of {threshold_ms}ms. "
        f"This indicates a performance regression in the VariableInstanceBuilder workflow."
    )
