"""Tests for autonomous development helper (FONT-372)."""

from __future__ import annotations

from pathlib import Path

from aspose_font.autonomous import AutonomousWorkflowResult
from aspose_font.autonomous_dev import run_autonomous_development


def test_run_autonomous_development_basic(tmp_path: Path) -> None:
    """Basic sanity test for the autonomous development helper.

    Verifies that the function returns a result object, includes at least one
    generated artifact (the QA package), and reports a positive total time.
    """
    # Resolve a known test font
    font_path = (
        Path(__file__).resolve().parents[1]
        / "testdata"
        / "Roboto-VariableFont_wdth,wght.ttf"
    )

    # Execute the helper in a temporary output directory
    result = run_autonomous_development(str(font_path), output_dir=tmp_path, preset=["latin"])  # type: ignore[arg-type]

    # The result should be an AutonomousWorkflowResult instance
    assert isinstance(result, AutonomousWorkflowResult)

    # The summary must contain generated artifacts and include a QA package entry
    generated = result.summary.get("generated_artifacts", [])
    assert any(art.get("kind") == "qa_package" for art in generated), "QA package not found in artifacts"

    # Total time should be a positive integer
    total_time = result.metrics.get("total_time_ms")
    assert isinstance(total_time, int) and total_time > 0, "Total time should be a positive integer"
