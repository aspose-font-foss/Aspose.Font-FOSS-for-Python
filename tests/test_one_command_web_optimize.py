"""Tests for one-command web font optimizer CLI (FONT-265)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

CLI = [sys.executable, "-m", "aspose_font.cli"]
ROBOTO = str(Path(__file__).resolve().parents[1] / "testdata" / "Roboto-VariableFont_wdth,wght.ttf")


def run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        CLI + list(args),
        capture_output=True,
        text=True,
    )


def test_web_optimize_produces_decision_report_json(tmp_path: Path):
    out_dir = tmp_path / "optimized-web"
    result = run(
        "web-optimize",
        ROBOTO,
        str(out_dir),
    )

    assert result.returncode == 0
    woff2_files = list(out_dir.glob("*.woff2"))
    woff_files = list(out_dir.glob("*.woff"))
    assert len(woff2_files) == 1
    assert len(woff_files) == 1
    css_files = list(out_dir.glob("*.css"))
    assert len(css_files) == 1
    html_files = list(out_dir.glob("*.html"))
    assert len(html_files) == 1
    assert (out_dir / "optimizer-manifest.json").exists()
    assert (out_dir / "decision-report.json").exists()

    decision = json.loads((out_dir / "decision-report.json").read_text(encoding="utf-8"))
    assert "decision" in decision
    assert "reasons" in decision
    assert "export_mode" in decision
    assert "font_path" in decision


def test_web_optimize_decision_report_contains_mode(tmp_path: Path):
    out_dir = tmp_path / "optimized-web"
    result = run(
        "web-optimize",
        ROBOTO,
        str(out_dir),
    )

    assert result.returncode == 0
    decision = json.loads((out_dir / "decision-report.json").read_text(encoding="utf-8"))
    assert decision["decision"] in ("live", "static", "static_fallback")
    assert isinstance(decision["reasons"], list)


def test_web_optimize_summary_displays_recommended_mode(tmp_path: Path):
    out_dir = tmp_path / "optimized-web"
    result = run(
        "web-optimize",
        ROBOTO,
        str(out_dir),
    )

    assert result.returncode == 0
    assert "Export mode:" in result.stdout


def test_web_optimize_decisions_when_subset_requested(tmp_path: Path):
    out_dir = tmp_path / "optimized-web"
    result = run(
        "web-optimize",
        ROBOTO,
        str(out_dir),
        "--preset",
        "latin",
        "--text",
        "Aspose Web",
    )

    assert result.returncode == 0
    decision = json.loads((out_dir / "decision-report.json").read_text(encoding="utf-8"))
    assert decision["decision"] == "static"
    assert any("subset" in reason.lower() for reason in decision["reasons"])


def test_web_optimize_live_mode_for_variable_font(tmp_path: Path):
    out_dir = tmp_path / "optimized-web"
    result = run(
        "web-optimize",
        ROBOTO,
        str(out_dir),
        "--variable-mode",
        "live",
    )

    assert result.returncode == 0
    decision = json.loads((out_dir / "decision-report.json").read_text(encoding="utf-8"))
    assert decision["decision"] == "live"


def test_web_optimize_custom_json_decision_path(tmp_path: Path):
    out_dir = tmp_path / "optimized-web"
    custom_path = tmp_path / "custom-decision.json"
    result = run(
        "web-optimize",
        ROBOTO,
        str(out_dir),
        "--decision-report",
        str(custom_path),
    )
    assert result.returncode == 0
    # When custom decision report path is specified, only custom path should be written
    assert custom_path.exists()
    # Default path should not exist when custom path is specified
    assert not (out_dir / "decision-report.json").exists()
