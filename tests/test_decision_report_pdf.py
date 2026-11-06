"""Tests for PDF decision report generation (FONT-337)."""

import subprocess
import sys
from pathlib import Path

from aspose_font import FontLoader
from aspose_font.web import DecisionReport, WebFontOptimizer

_TESTDATA_DIR = Path(__file__).resolve().parents[1] / "testdata"


class TestDecisionReportPDF:
    """Tests for PDF decision report generation."""

    def test_decision_report_pdf_generation(self) -> None:
        """PDF decision report should be generated when requested."""
        font = FontLoader.open(_TESTDATA_DIR / "Roboto-VariableFont_wdth,wght.ttf")
        result = WebFontOptimizer.decide_output(font, variable_mode="live")

        report = DecisionReport(
            mode=result.get("decision", "unknown"),
            reasons=result.get("reasons", []),
            summary=result.get("summary", ""),
            remediation=result.get("remediation", []),
        )

        pdf_data = DecisionReport.build_decision_pdf(report)
        assert isinstance(pdf_data, bytes)
        assert len(pdf_data) > 100
        assert pdf_data.startswith(b"%PDF-")

    def test_decision_report_pdf_contains_expected_fields(self) -> None:
        """PDF should contain mode, summary, reasons, remediation."""
        import zlib

        font = FontLoader.open(_TESTDATA_DIR / "Roboto-VariableFont_wdth,wght.ttf")
        result = WebFontOptimizer.decide_output(font, variable_mode="live")

        report = DecisionReport(
            mode=result.get("decision", "unknown"),
            reasons=result.get("reasons", []),
            summary=result.get("summary", ""),
            remediation=result.get("remediation", []),
        )

        pdf_data = DecisionReport.build_decision_pdf(report)

        pdf_text = pdf_data.decode("latin-1", errors="replace")

        stream_start = pdf_text.find("stream\n")
        stream_end = pdf_text.find("endstream")
        if stream_start != -1 and stream_end != -1:
            compressed_content = pdf_data[stream_start + 7 : stream_end]
            try:
                decompressed = zlib.decompress(compressed_content)
                decompressed_text = decompressed.decode("latin-1", errors="replace")
                assert "Mode:" in decompressed_text
                assert "Summary:" in decompressed_text
                assert "Reasons:" in decompressed_text
                assert "Remediation:" in decompressed_text
            except Exception:
                assert False, "PDF content should be decompressible and contain expected fields"
        else:
            assert False, "PDF stream not found"

    def test_decision_report_pdf_roundtrip(self, tmp_path: Path) -> None:
        """PDF decision report should be writeable and readable."""
        font = FontLoader.open(_TESTDATA_DIR / "Roboto-VariableFont_wdth,wght.ttf")
        result = WebFontOptimizer.decide_output(font, variable_mode="live")

        report = DecisionReport(
            mode=result.get("decision", "unknown"),
            reasons=result.get("reasons", []),
            summary=result.get("summary", ""),
            remediation=result.get("remediation", []),
        )

        pdf_path = tmp_path / "decision-report.pdf"
        pdf_data = DecisionReport.build_decision_pdf(report)
        pdf_path.write_bytes(pdf_data)

        assert pdf_path.exists()
        assert pdf_path.stat().st_size > 0
        assert pdf_path.read_bytes().startswith(b"%PDF-")

    def test_cli_pdf_report_generates_file(self, tmp_path: Path) -> None:
        """CLI --pdf-report should create PDF file."""
        font_path = _TESTDATA_DIR / "Roboto-VariableFont_wdth,wght.ttf"
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        pdf_path = output_dir / "custom-decision.pdf"

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "aspose_font.cli",
                "web-optimize",
                str(font_path),
                str(output_dir),
                "--preset",
                "latin",
                "--pdf-report",
                str(pdf_path.relative_to(output_dir)),
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert pdf_path.exists()
        assert pdf_path.stat().st_size > 0

        pdf_content = pdf_path.read_bytes()
        assert pdf_content.startswith(b"%PDF-")

    def test_cli_pdf_report_with_custom_absolute_path(self, tmp_path: Path) -> None:
        """CLI --pdf-report with absolute path should create PDF at that location."""
        font_path = _TESTDATA_DIR / "Roboto-VariableFont_wdth,wght.ttf"
        pdf_path = tmp_path / "absolute" / "custom-decision.pdf"

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "aspose_font.cli",
                "web-optimize",
                str(font_path),
                str(tmp_path / "output"),
                "--preset",
                "latin",
                "--pdf-report",
                str(pdf_path),
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert pdf_path.exists()
        assert pdf_path.stat().st_size > 0
        assert pdf_path.read_bytes().startswith(b"%PDF-")

    def test_decision_report_pdf_with_static_font(self) -> None:
        """PDF generation should work with static fonts."""
        font = FontLoader.open(_TESTDATA_DIR / "Arial.pfa")
        result = WebFontOptimizer.decide_output(font)

        report = DecisionReport(
            mode=result.get("decision", "unknown"),
            reasons=result.get("reasons", []),
            summary=result.get("summary", ""),
            remediation=result.get("remediation", []),
        )

        pdf_data = DecisionReport.build_decision_pdf(report)
        assert isinstance(pdf_data, bytes)
        assert len(pdf_data) > 100
        assert pdf_data.startswith(b"%PDF-")
