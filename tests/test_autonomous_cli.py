"""Tests for autonomous CLI command (FONT-335)."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

CLI = [sys.executable, "-m", "aspose_font.cli"]
ROBOTO = str(Path(__file__).resolve().parents[1] / "testdata" / "Roboto-VariableFont_wdth,wght.ttf")


def test_autonomous_cli_command_exists():
    """Verify autonomous command is registered."""
    result = subprocess.run(CLI + ["--help"], capture_output=True, text=True)
    assert result.returncode == 0
    assert "autonomous" in result.stdout


def test_autonomous_cli_basic_execution(tmp_path: Path):
    """Test basic autonomous workflow execution."""
    output_dir = tmp_path / "autonomous_output"
    output_dir.mkdir()

    result = subprocess.run(
        CLI + ["autonomous", ROBOTO, str(output_dir), "--preset", "latin"],
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


def test_autonomous_cli_verbose_outputs_decision_report(tmp_path: Path):
    """Test verbose flag outputs decision report."""
    output_dir = tmp_path / "autonomous_verbose"
    output_dir.mkdir()

    result = subprocess.run(
        CLI + ["autonomous", ROBOTO, str(output_dir), "--preset", "latin", "--verbose"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, f"CLI failed: {result.stderr}"

    assert "Autonomous workflow decision:" in result.stdout
    assert "Reason:" in result.stdout
    assert "Confidence:" in result.stdout


def test_autonomous_cli_without_verbose(tmp_path: Path):
    """Test that decision report is included by default (without verbose)."""
    output_dir = tmp_path / "autonomous_no_verbose"
    output_dir.mkdir()

    result = subprocess.run(
        CLI + ["autonomous", ROBOTO, str(output_dir), "--preset", "latin"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, f"CLI failed: {result.stderr}"

    assert (output_dir / "optimizer-manifest.json").exists()
    manifest = json.loads((output_dir / "optimizer-manifest.json").read_text(encoding="utf-8"))
    assert "export_mode" in manifest or "export_note" in manifest
    assert manifest.get("auto_instanced_default") is not None or manifest.get("export_mode") is not None


def test_autonomous_cli_skip_instances(tmp_path: Path):
    """Test --no-instances flag skips instance generation."""
    output_dir = tmp_path / "autonomous_no_instances"
    output_dir.mkdir()

    result = subprocess.run(
        CLI + ["autonomous", ROBOTO, str(output_dir), "--preset", "latin", "--no-instances"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, f"CLI failed: {result.stderr}"

    assert (output_dir / "roboto-instance-regular.woff2").exists()
    assert (output_dir / "qa-report.json").exists()


def test_autonomous_cli_skip_qa(tmp_path: Path):
    """Test --no-qa flag skips QA report generation."""
    output_dir = tmp_path / "autonomous_no_qa"
    output_dir.mkdir()

    result = subprocess.run(
        CLI + ["autonomous", ROBOTO, str(output_dir), "--preset", "latin", "--no-qa"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, f"CLI failed: {result.stderr}"

    assert (output_dir / "roboto-instance-regular.woff2").exists()
    assert not (output_dir / "qa-report.json").exists()


def test_autonomous_cli_json_summary(tmp_path: Path):
    """Test --json-summary writes summary file."""
    output_dir = tmp_path / "autonomous_json"
    output_dir.mkdir()

    json_summary = output_dir / "summary.json"

    result = subprocess.run(
        CLI + ["autonomous", ROBOTO, str(output_dir), "--preset", "latin", "--json-summary", str(json_summary)],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, f"CLI failed: {result.stderr}"

    assert json_summary.exists()
    summary_data = json.loads(json_summary.read_text(encoding="utf-8"))
    assert "kind" in summary_data
    assert summary_data["kind"] == "autonomous_workflow_result"
    assert "decision" in summary_data
    assert "workflow" in summary_data["decision"]


def test_autonomous_cli_no_decision_report_flag(tmp_path: Path):
    """Test --no-decision-report flag suppresses decision output."""
    output_dir = tmp_path / "autonomous_no_decision"
    output_dir.mkdir()

    result = subprocess.run(
        CLI + ["autonomous", ROBOTO, str(output_dir), "--preset", "latin", "--no-decision-report"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, f"CLI failed: {result.stderr}"

    assert "Autonomous workflow decision:" not in result.stdout
    assert (output_dir / "optimizer-manifest.json").exists()
