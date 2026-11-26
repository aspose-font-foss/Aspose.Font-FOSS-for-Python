"""CI performance regression test for variable font loading (FONT-351)."""

from __future__ import annotations

from pathlib import Path

from aspose_font import FontLoader
from aspose_font.performance import measure_load_time

FIXTURE_ROOT = Path(__file__).resolve().parent.parent / "testdata"


def test_variable_font_load_performance() -> None:
    """Verify FontLoader.open loads Roboto Variable within performance threshold (≤500ms).

    This test enforces a CI performance regression gate for raw font loading.
    The measurement is repeated 3 times and uses the maximum to account for CI variance.

    Threshold: 500ms (conservative CI regression gate for raw variable font load)
    Baseline: ~100-200ms on developer machines; CI runners may be slower
    Repeats: 3 measurements, taking the maximum for stability

    Reference font: Roboto-VariableFont_wdth,wght.ttf
    Reference: FONT-351, Phase 4: Reliability Matrix & CI Performance Regression.
    """
    font_path = FIXTURE_ROOT / "Roboto-VariableFont_wdth,wght.ttf"
    if not font_path.exists():
        font_path = FIXTURE_ROOT.parent / "Roboto-VariableFont_wdth,wght.ttf"
    if not font_path.exists():
        raise FileNotFoundError(f"Variable font not found at {font_path}")

    font = FontLoader.open(font_path)
    assert font.is_variable, "Test fixture must be a variable font"

    repeat_count = 3
    elapsed_list: list[float] = []

    for _ in range(repeat_count):
        load_time = measure_load_time(font_path)
        elapsed_list.append(load_time)

    max_elapsed_seconds = max(elapsed_list)
    max_elapsed_ms = max_elapsed_seconds * 1000

    threshold_seconds = 0.5

    assert max_elapsed_seconds <= threshold_seconds, (
        f"Variable font load took {max_elapsed_ms:.2f}ms (max of {repeat_count} runs), "
        f"exceeds CI regression threshold of {threshold_seconds * 1000}ms. "
        f"Individual runs: {[f'{e*1000:.2f}ms' for e in elapsed_list]}. "
        f"This indicates a performance regression in FontLoader.open for variable fonts."
    )
