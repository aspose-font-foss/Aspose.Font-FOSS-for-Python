"""Tests for autonomous workflow decision analysis (FONT-331)."""

from pathlib import Path

from aspose_font import FontLoader
from aspose_font.autonomous import analyze_font_for_autonomous_workflow


def test_decision_variable_font_with_named_instances(tmp_path: Path) -> None:
    """Variable font with named instances should return web_optimize workflow."""
    font_path = Path(__file__).resolve().parents[1] / "testdata" / "Roboto-VariableFont_wdth,wght.ttf"
    if not font_path.exists():
        return

    font = FontLoader.open(font_path)
    decision = analyze_font_for_autonomous_workflow(font)

    assert decision.workflow == "web_optimize"
    assert decision.detected_font_type == "variable"
    assert "variable_axes" in decision.detected_capabilities
    assert "qa_verification" in decision.detected_capabilities

    action_actions = [a.get("action") for a in decision.recommended_actions]
    assert "quality_assurance" in action_actions
    assert "named_instance_package" not in action_actions

    assert isinstance(decision.confidence, float)
    assert 0.0 <= decision.confidence <= 1.0
    assert isinstance(decision.reason, str)
    assert len(decision.reason) > 0


def test_decision_static_font(tmp_path: Path) -> None:
    """Static font should return web_optimize workflow only."""
    font_path = Path(__file__).resolve().parents[1] / "testdata" / "OpenSans-Regular.cff"
    if not font_path.exists():
        return

    font = FontLoader.open(font_path)
    decision = analyze_font_for_autonomous_workflow(font)

    assert decision.workflow == "web_optimize"
    assert decision.detected_font_type == "static"
    assert "qa_verification" in decision.detected_capabilities

    action_actions = [a.get("action") for a in decision.recommended_actions]
    assert "quality_assurance" in action_actions
    assert "variable_instancing" not in action_actions

    assert isinstance(decision.confidence, float)
    assert 0.0 <= decision.confidence <= 1.0
    assert isinstance(decision.reason, str)
    assert len(decision.reason) > 0
