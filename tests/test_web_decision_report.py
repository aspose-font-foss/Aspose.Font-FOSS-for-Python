"""Tests for WebFontOptimizer decision report generation."""

import json
from pathlib import Path

from aspose_font import FontLoader, WebFontOptimizer


def test_decision_report_generated(tmp_path: Path) -> None:
    font_path = Path(__file__).resolve().parents[1] / "testdata" / "Roboto-VariableFont_wdth,wght.ttf"
    if not font_path.exists():
        return
    font = FontLoader.open(font_path)

    output_dir = tmp_path / "output"
    output_dir.mkdir()

    package = WebFontOptimizer.build(font, decision_report=True)
    package.write_to(output_dir)

    decision_path = output_dir / "decision_report.json"
    assert decision_path.exists(), "decision_report.json not created"

    decision_data = json.loads(decision_path.read_text(encoding="utf-8"))
    assert "mode" in decision_data, "decision_report.json missing 'mode' field"
    assert "reason" in decision_data, "decision_report.json missing 'reason' field"
    assert isinstance(decision_data["reason"], str), "'reason' must be a string"
    assert len(decision_data["reason"]) > 0, "'reason' must not be empty"
    assert decision_data["mode"] in ("live", "static", "static_fallback"), f"Invalid mode: {decision_data['mode']}"


def test_decision_report_not_generated_by_default(tmp_path: Path) -> None:
    font_path = Path(__file__).resolve().parents[1] / "testdata" / "Roboto-VariableFont_wdth,wght.ttf"
    if not font_path.exists():
        return
    font = FontLoader.open(font_path)

    output_dir = tmp_path / "output"
    output_dir.mkdir()

    package = WebFontOptimizer.build(font, decision_report=False)
    package.write_to(output_dir)

    decision_path = output_dir / "decision_report.json"
    assert not decision_path.exists(), "decision_report.json should not be created when flag is False"
