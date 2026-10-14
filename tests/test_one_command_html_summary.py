"""Tests for HTML summary generation in one-command Web Font Optimizer (FONT-336)."""

from __future__ import annotations

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


def test_cli_html_summary_creates_file(tmp_path: Path) -> None:
    """CLI with --html-summary creates decision-report.html alongside decision-report.json."""
    out_dir = tmp_path / "optimized-web"
    result = run(
        "web-optimize",
        ROBOTO,
        str(out_dir),
        "--html-summary",
    )

    assert result.returncode == 0
    assert (out_dir / "decision-report.json").exists()
    assert (out_dir / "decision-report.html").exists()

    json_content = (out_dir / "decision-report.json").read_text(encoding="utf-8")
    html_content = (out_dir / "decision-report.html").read_text(encoding="utf-8")

    assert "decision" in json_content.lower()
    assert "<html" in html_content.lower()
    assert "<title>Decision Report</title>" in html_content


def test_cli_html_summary_contains_required_fields(tmp_path: Path) -> None:
    """HTML summary contains mode, reason, summary, remediation fields."""
    out_dir = tmp_path / "optimized-web"
    result = run(
        "web-optimize",
        ROBOTO,
        str(out_dir),
        "--html-summary",
    )

    assert result.returncode == 0

    html_content = (out_dir / "decision-report.html").read_text(encoding="utf-8")

    assert 'id="mode"' in html_content
    assert 'id="reason"' in html_content
    assert 'id="summary"' in html_content
    assert 'id="remediation"' in html_content

    assert "<table>" in html_content
    assert "</table>" in html_content


def test_cli_html_summary_with_static_mode(tmp_path: Path) -> None:
    """HTML summary shows static mode when subsetting a variable font."""
    out_dir = tmp_path / "optimized-web"
    result = run(
        "web-optimize",
        ROBOTO,
        str(out_dir),
        "--html-summary",
        "--preset",
        "latin",
        "--text",
        "Aspose Web",
    )

    assert result.returncode == 0
    assert (out_dir / "decision-report.html").exists()

    html_content = (out_dir / "decision-report.html").read_text(encoding="utf-8")

    assert "Export Mode" in html_content
    assert "Primary Reason" in html_content
