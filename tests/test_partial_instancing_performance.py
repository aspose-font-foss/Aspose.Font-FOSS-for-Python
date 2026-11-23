"""CI performance regression test for partial instancing (FONT-373)."""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from aspose_font import FontLoader
from aspose_font.instancing import SmartInstancer

FIXTURE_ROOT = Path(__file__).resolve().parent.parent / "testdata"


@pytest.mark.performance
def test_partial_instancing_performance() -> None:
    """Verify SmartInstancer.partial_instantiate completes within 1000 ms.

    Threshold: 1000 ms (CI regression gate for partial instancing).
    The measurement is performed three times; the maximum is used to allow for CI variance.
    """
    font_path = FIXTURE_ROOT / "Roboto-VariableFont_wdth,wght.ttf"
    if not font_path.exists():
        font_path = FIXTURE_ROOT.parent / "Roboto-VariableFont_wdth,wght.ttf"
    if not font_path.exists():
        raise FileNotFoundError(f"Variable font not found at {font_path}")

    font = FontLoader.open(font_path)
    assert font.is_variable, "Test fixture must be a variable font"

    instancer = SmartInstancer(font)
    repeat_count = 3
    elapsed_times: list[float] = []

    for _ in range(repeat_count):
        start = time.perf_counter()
        result_font = instancer.partial_instantiate(lock_axes={"wght": 700.0})
        elapsed = time.perf_counter() - start
        elapsed_times.append(elapsed)
        assert result_font is not None
        # Ensure the result is static (wght locked) or still variable depending on implementation
        # At least, the operation succeeded without error.

    max_elapsed = max(elapsed_times)
    threshold_seconds = 1.0
    assert max_elapsed <= threshold_seconds, (
        f"Partial instancing took {max_elapsed*1000:.2f} ms (max of {repeat_count} runs), "
        f"exceeds CI regression threshold of {threshold_seconds*1000:.0f} ms."
    )
