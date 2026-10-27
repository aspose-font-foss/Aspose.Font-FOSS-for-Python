"""Tests for CLI --decision-report-pdf flag (FONT-338)."""

import json
import subprocess
import sys
from pathlib import Path

_TESTDATA_DIR = Path(__file__).resolve().parents[1] / "testdata"


class TestWebOptimizeDecisionReportPDF:
    """Tests for CLI PDF decision report generation."""

    def test_cli_decision_report_pdf_flag_creates_file(self, tmp_path: Path) -> None:
        """CLI --decision-report-pdf should create PDF decision report file."""
        font_path = _TESTDATA_DIR / "Roboto-VariableFont_wdth,wght.ttf"
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        pdf_path = output_dir / "decision-report.pdf"

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "aspose_font.cli",
                "web-optimize",
                str(font_path),
                str(output_dir),
                "--decision-report-pdf",
                str(pdf_path.relative_to(output_dir)),
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert pdf_path.exists()
        assert pdf_path.stat().st_size > 0
        assert pdf_path.read_bytes().startswith(b"%PDF-")

    def test_cli_decision_report_pdf_with_json_decision_key(self, tmp_path: Path) -> None:
        """PDF decision report should be accompanied by JSON with 'decision' key."""
        font_path = _TESTDATA_DIR / "Roboto-VariableFont_wdth,wght.ttf"
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        pdf_path = output_dir / "decision-report.pdf"

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "aspose_font.cli",
                "web-optimize",
                str(font_path),
                str(output_dir),
                "--decision-report-pdf",
                str(pdf_path.relative_to(output_dir)),
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0

        json_path = output_dir / "decision_report.json"
        assert json_path.exists()

        data = json.loads(json_path.read_text(encoding="utf-8"))
        assert "decision" in data
        assert "mode" in data
