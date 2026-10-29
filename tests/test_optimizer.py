"""Tests for FONT-255 Autonomous Web Font Optimizer (optimizer.py module)."""

from __future__ import annotations

from pathlib import Path

from aspose_font import (
    TtfFont,
    WebFontOptimizerDecision,
    WebFontOptimizerPackageWithDecision,
    analyze_font_for_web_optimization,
    build_web_optimizer_package,
)
from aspose_font.cff.font import CffFont


def test_analyze_font_for_web_optimization_variable(roboto: TtfFont) -> None:
    """Test that variable fonts are correctly identified for live export."""
    decision = analyze_font_for_web_optimization(roboto)

    assert decision.mode == "live"
    assert decision.confidence == 0.95
    assert len(decision.affected_axes) > 1
    assert "wght" in decision.affected_axes
    assert "wdth" in decision.affected_axes
    assert "variable" in decision.reason.lower()
    assert len(decision.recommended_presets) > 0


def test_analyze_font_for_web_optimization_static(opensans_cff: CffFont) -> None:
    """Test that static fonts are correctly identified for static export."""
    decision = analyze_font_for_web_optimization(opensans_cff)

    assert decision.mode == "static"
    assert decision.confidence == 1.0
    assert len(decision.affected_axes) == 0
    assert "static" in decision.reason.lower()
    assert "not variable" in decision.reason.lower()
    assert len(decision.recommended_presets) > 0


def test_analyze_font_for_web_optimization_variable_single_axis() -> None:
    """Test variable font with minimal axes gets static-fallback."""
    from aspose_font import FontLoader

    single_axis_font_path = (
        Path(__file__).resolve().parents[1] / "testdata" / "Roboto-VariableFont_wdth,wght.ttf"
    )
    font = FontLoader.open(str(single_axis_font_path))

    decision = analyze_font_for_web_optimization(font)

    assert decision.mode == "live"
    assert decision.confidence == 0.95


def test_build_web_optimizer_package_decision_logging(roboto: TtfFont, tmp_path: Path) -> None:
    """Test that build_web_optimizer_package includes decision metadata."""
    package = build_web_optimizer_package(
        roboto,
        source_path=Path("testdata/Roboto-VariableFont_wdth,wght.ttf"),
        file_stem="roboto-test",
        include_woff=False,
        variable_mode="auto",
    )

    assert isinstance(package, WebFontOptimizerPackageWithDecision)
    assert isinstance(package.decision, WebFontOptimizerDecision)
    assert package.decision.mode == "live"
    assert package.decision.confidence == 0.95
    assert len(package.decision.affected_axes) > 0

    assert package.size_summary.get("source_bytes") is not None
    assert package.size_summary.get("total_web_font_bytes") > 0
    assert len(package.notes) > 0

    manifest = package.manifest
    assert "decision" in manifest
    assert manifest["decision"] == "live"
    assert "decision_metadata" in manifest
    assert manifest["decision_metadata"]["confidence"] == 0.95


def test_build_web_optimizer_package_with_explicit_decision(roboto: TtfFont) -> None:
    """Test that pre-computed decisions can be passed to build_web_optimizer_package."""
    from aspose_font.optimizer import build_web_optimizer_package_with_plan

    explicit_decision = WebFontOptimizerDecision(
        mode="static",
        reason="Explicit static mode requested",
        confidence=1.0,
        affected_axes=[],
        recommended_presets=["latin"],
    )

    package = build_web_optimizer_package_with_plan(
        roboto,
        decision=explicit_decision,
        variable_mode="static",
    )

    assert isinstance(package, WebFontOptimizerPackageWithDecision)
    assert package.decision.mode == "static"
    assert package.decision.reason == "Explicit static mode requested"


def test_build_web_optimizer_package_writes_decision_to_dir(
    roboto: TtfFont, tmp_path: Path
) -> None:
    """Test that decision metadata is written to output directory."""
    package = build_web_optimizer_package(
        roboto,
        source_path=Path("testdata/Roboto-VariableFont_wdth,wght.ttf"),
        file_stem="roboto-decision",
        include_woff=False,
        variable_mode="auto",
    )

    package.write_to(tmp_path)

    decision_path = tmp_path / "decision_report.json"
    assert decision_path.exists()

    decision_data = decision_path.read_text(encoding="utf-8")
    import json

    decision_json = json.loads(decision_data)

    assert decision_json["mode"] == "live"
    assert decision_json["confidence"] == 0.95
    assert len(decision_json["affected_axes"]) > 0


def test_decision_report_contains_reasons(roboto: TtfFont, tmp_path: Path) -> None:
    """Test that decision report contains detailed reasons."""
    package = build_web_optimizer_package(
        roboto,
        source_path=Path("testdata/Roboto-VariableFont_wdth,wght.ttf"),
        include_woff=False,
        variable_mode="auto",
    )

    decision_report = package.manifest.get("decision_report")
    assert decision_report is not None
    assert "reasons" in decision_report
    assert len(decision_report["reasons"]) > 0

    reasons = decision_report["reasons"]
    assert any("Variable font" in r or "variable" in r.lower() for r in reasons)


def test_optimizer_interactive_playground_basic(roboto: TtfFont) -> None:
    """Test that optimizer WebFontOptimizer.build_interactive_playground works."""
    from aspose_font.optimizer import WebFontOptimizer

    html = WebFontOptimizer.build_interactive_playground(
        font=roboto,
        family="Roboto",
        style="Regular",
        preview_text="Hello World",
        specimen_template="classic",
        export_mode="live",
        export_note=None,
    )

    assert isinstance(html, str)
    assert len(html) > 0
    assert "<!doctype html>" in html
    assert "<html" in html.lower()
    assert "</html>" in html.lower()
    assert "fontVariationSettings" in html


def test_optimizer_interactive_playground_axis_sliders(roboto: TtfFont) -> None:
    """Test that optimizer playground has axis sliders for variable fonts."""
    from aspose_font.optimizer import WebFontOptimizer

    html = WebFontOptimizer.build_interactive_playground(
        font=roboto,
        family="Roboto",
        style="Regular",
        preview_text="Test",
        specimen_template="classic",
        export_mode="live",
        export_note=None,
    )

    assert 'class="axis-control"' in html
    assert 'data-axis="wght"' in html
    assert 'data-axis="wdth"' in html


def test_optimizer_interactive_playground_font_controls(roboto: TtfFont) -> None:
    """Test that optimizer playground has font size and line height controls."""
    from aspose_font.optimizer import WebFontOptimizer

    html = WebFontOptimizer.build_interactive_playground(
        font=roboto,
        family="Roboto",
        style="Regular",
        preview_text="Test",
        specimen_template="classic",
        export_mode="live",
        export_note=None,
    )

    assert 'id="font-size"' in html
    assert 'id="line-height"' in html
    assert 'id="specimen-text"' in html


def test_optimizer_interactive_playground_dark_mode(roboto: TtfFont) -> None:
    """Test that optimizer playground supports dark mode."""
    from aspose_font.optimizer import WebFontOptimizer

    html = WebFontOptimizer.build_interactive_playground(
        font=roboto,
        family="Roboto",
        style="Regular",
        preview_text="Test",
        specimen_template="classic",
        export_mode="live",
        export_note=None,
        dark_mode=True,
    )

    assert "dark" in html.lower()


def test_optimizer_interactive_playground_css_snippet(roboto: TtfFont) -> None:
    """Test that optimizer playground includes copyable CSS snippet."""
    from aspose_font.optimizer import WebFontOptimizer

    html = WebFontOptimizer.build_interactive_playground(
        font=roboto,
        family="Roboto",
        style="Regular",
        preview_text="Test",
        specimen_template="classic",
        export_mode="live",
        export_note=None,
    )

    assert "@font-face" in html
    assert "url('./fonts.css')" in html
    assert "woff2" in html
