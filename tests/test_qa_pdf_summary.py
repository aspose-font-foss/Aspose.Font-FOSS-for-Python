"""Tests for PDF summary generation in Font QA Report."""

from __future__ import annotations

import sys
from pathlib import Path

from aspose_font.ttf.font import TtfFont

ROBOTO = str(Path(__file__).resolve().parents[1] / "testdata" / "Roboto-VariableFont_wdth,wght.ttf")


def test_font_qa_report_write_pdf(roboto: TtfFont, tmp_path: Path) -> None:
    """Verify FontQaReport.write_pdf() creates valid PDF."""
    from aspose_font import FontQaReporter

    report = FontQaReporter.build(roboto, presets=("latin",), text="QA")

    pdf_path = report.write_pdf(tmp_path / "qa-report.pdf")

    assert pdf_path.exists()
    assert pdf_path.stat().st_size > 0
    assert pdf_path.read_bytes()[:4] == b"%PDF"


def test_qa_pdf_summary_cli(tmp_path: Path) -> None:
    """Verify CLI --pdf-summary flag creates non-empty PDF file."""
    from subprocess import run as _run

    pdf_output = tmp_path / "qa-report.pdf"
    json_output = tmp_path / "qa.json"
    result = _run(
        [
            sys.executable,
            "-m",
            "aspose_font.cli",
            "qa-report",
            ROBOTO,
            "--preset",
            "latin",
            "--text",
            "QA",
            "--json-output",
            str(json_output),
            "--pdf-summary",
            str(pdf_output),
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, f"CLI failed: {result.stderr}"
    assert pdf_output.exists()
    assert pdf_output.stat().st_size > 0
    assert pdf_output.read_bytes()[:4] == b"%PDF"
