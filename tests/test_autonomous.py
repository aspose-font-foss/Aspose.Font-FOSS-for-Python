"""Tests for FONT-327 autonomous font processing workflow."""

from __future__ import annotations

import json
from pathlib import Path

from aspose_font import TtfFont
from aspose_font.autonomous import (
    AutonomousWorkflowDecision,
    AutonomousWorkflowResult,
    analyze_font_for_autonomous_workflow,
    run_autonomous_workflow,
    run_autonomous_workflow_from_path,
)


def test_analyze_font_for_autonomous_workflow_variable(roboto: TtfFont):
    """Test decision analysis for variable font."""
    decision = analyze_font_for_autonomous_workflow(roboto)

    assert isinstance(decision, AutonomousWorkflowDecision)
    assert decision.detected_font_type == "variable"
    assert "variable_axes" in decision.detected_capabilities
    assert "qa_verification" in decision.detected_capabilities
    assert decision.confidence > 0.8
    assert decision.workflow in ("combined", "web_optimize")
    assert len(decision.recommended_actions) > 0


def test_analyze_font_for_autonomous_workflow_static(opensans_cff: TtfFont):
    """Test decision analysis for static font."""
    decision = analyze_font_for_autonomous_workflow(opensans_cff)

    assert isinstance(decision, AutonomousWorkflowDecision)
    assert decision.detected_font_type == "static"
    assert decision.workflow == "web_optimize"
    assert decision.confidence > 0.7


def test_run_autonomous_workflow_full(roboto: TtfFont, tmp_path: Path):
    """Test full autonomous workflow with all components."""
    result = run_autonomous_workflow(
        roboto,
        input_path=str(Path("testdata") / "Roboto-VariableFont_wdth,wght.ttf"),
        output_dir=tmp_path,
        include_qa=True,
        include_instances=True,
        preset=["latin"],
    )

    assert isinstance(result, AutonomousWorkflowResult)
    assert isinstance(result.decision, AutonomousWorkflowDecision)

    assert result.web_package is not None
    assert result.qa_package is not None
    assert result.instance_package is not None
    assert "kind" in result.summary
    assert result.summary["kind"] == "autonomous_workflow_result"
    assert "generated_artifacts" in result.summary
    assert len(result.summary["generated_artifacts"]) > 0

    assert "total_time_ms" in result.metrics
    assert result.metrics["total_time_ms"] > 0


def test_run_autonomous_workflow_qa_only(roboto: TtfFont, tmp_path: Path):
    """Test autonomous workflow with QA only (no instances)."""
    result = run_autonomous_workflow(
        roboto,
        input_path=str(Path("testdata") / "Roboto-VariableFont_wdth,wght.ttf"),
        output_dir=tmp_path,
        include_qa=True,
        include_instances=False,
        preset=["latin"],
    )

    assert isinstance(result, AutonomousWorkflowResult)
    assert result.web_package is not None
    assert result.qa_package is not None
    assert result.instance_package is None

    artifact_kinds = [a["kind"] for a in result.summary["generated_artifacts"]]
    assert "web_bundle" in artifact_kinds
    assert "qa_package" in artifact_kinds


def test_run_autonomous_workflow_web_only(roboto: TtfFont, tmp_path: Path):
    """Test autonomous workflow with web only (no QA, no instances)."""
    result = run_autonomous_workflow(
        roboto,
        input_path=str(Path("testdata") / "Roboto-VariableFont_wdth,wght.ttf"),
        output_dir=tmp_path,
        include_qa=False,
        include_instances=False,
        preset=["latin"],
    )

    assert isinstance(result, AutonomousWorkflowResult)
    assert result.web_package is not None
    assert result.qa_package is None
    assert result.instance_package is None

    artifact_kinds = [a["kind"] for a in result.summary["generated_artifacts"]]
    assert "web_bundle" in artifact_kinds
    assert "qa_package" not in artifact_kinds


def test_run_autonomous_workflow_from_path(roboto_path: Path, tmp_path: Path):
    """Test convenience wrapper that loads font from path."""
    result = run_autonomous_workflow_from_path(
        str(roboto_path),
        output_dir=tmp_path,
        preset=["latin"],
    )

    assert isinstance(result, AutonomousWorkflowResult)
    assert result.web_package is not None
    assert result.qa_package is not None


def test_autonomous_cli_output_structure(roboto_path: Path, tmp_path: Path):
    """Test CLI output structure for autonomous command."""
    import subprocess
    import sys

    output_dir = tmp_path / "autonomous_output"
    output_dir.mkdir()

    json_summary = output_dir / "summary.json"

    result = subprocess.run(
        [sys.executable, "-m", "aspose_font.cli", "autonomous",
         str(roboto_path), str(output_dir),
         "--preset", "latin",
         "--no-instances",
         "--json-summary", str(json_summary)],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, f"CLI failed: {result.stderr}"

    assert (output_dir / "roboto-instance-regular.woff2").exists()
    assert (output_dir / "roboto-instance-regular.css").exists()
    assert (output_dir / "roboto-instance-regular.html").exists()
    assert (output_dir / "web-manifest.json").exists()
    assert (output_dir / "optimizer-manifest.json").exists()
    assert (output_dir / "qa-report.json").exists()
    assert (output_dir / "qa-report.html").exists()
    assert (output_dir / "autonomous-metrics.json").exists()
    assert (output_dir / "autonomous-summary.json").exists()

    summary_data = json.loads(json_summary.read_text(encoding="utf-8"))
    assert "kind" in summary_data
    assert summary_data["kind"] == "autonomous_workflow_result"
    assert "decision" in summary_data
    assert "workflow" in summary_data["decision"]
