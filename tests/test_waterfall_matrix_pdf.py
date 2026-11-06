"""Tests for PDF export in preview-waterfall and preview-matrix commands."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PDF_MAGIC_BYTES = b"%PDF-"


def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "aspose_font.cli"] + list(args),
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )


class TestWaterfallMatrixPdfExport:
    """Test PDF export functionality for preview-waterfall and preview-matrix."""

    def test_cli_preview_waterfall_pdf_output(self, tmp_path: Path) -> None:
        """Test that preview-waterfall can export to PDF."""
        font_path = "testdata/Roboto-VariableFont_wdth,wght.ttf"
        output_path = tmp_path / "waterfall.pdf"

        result = _run_cli(
            "preview-waterfall",
            font_path,
            str(output_path),
            "--format",
            "pdf",
            "--all-named",
        )

        assert result.returncode == 0, f"CLI failed: {result.stderr}"
        assert output_path.exists(), "PDF file was not created"
        assert output_path.read_bytes().startswith(PDF_MAGIC_BYTES), "File is not a valid PDF"

    def test_cli_preview_matrix_pdf_output(self, tmp_path: Path) -> None:
        """Test that preview-matrix can export to PDF."""
        font_path = "testdata/Roboto-VariableFont_wdth,wght.ttf"
        output_path = tmp_path / "matrix.pdf"

        result = _run_cli(
            "preview-matrix",
            font_path,
            str(output_path),
            "--format",
            "pdf",
            "--all-named",
        )

        assert result.returncode == 0, f"CLI failed: {result.stderr}"
        assert output_path.exists(), "PDF file was not created"
        assert output_path.read_bytes().startswith(PDF_MAGIC_BYTES), "File is not a valid PDF"

    def test_cli_preview_waterfall_pdf_with_all_named(self, tmp_path: Path) -> None:
        """Test PDF export with --all-named flag."""
        font_path = "testdata/Roboto-VariableFont_wdth,wght.ttf"
        output_path = tmp_path / "waterfall-all.pdf"

        result = _run_cli(
            "preview-waterfall",
            font_path,
            str(output_path),
            "--format",
            "pdf",
            "--all-named",
        )

        assert result.returncode == 0, f"CLI failed: {result.stderr}"
        assert output_path.exists(), "PDF file was not created"
        assert output_path.read_bytes().startswith(PDF_MAGIC_BYTES), "File is not a valid PDF"

    def test_cli_preview_waterfall_default_png_still_works(self, tmp_path: Path) -> None:
        """Test that PNG export still works (regression test)."""
        font_path = "testdata/Roboto-VariableFont_wdth,wght.ttf"
        output_path = tmp_path / "waterfall.png"

        result = _run_cli(
            "preview-waterfall",
            font_path,
            str(output_path),
            "--all-named",
        )

        assert result.returncode == 0, f"CLI failed: {result.stderr}"
        assert output_path.exists(), "PNG file was not created"
        assert output_path.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n", "File is not a valid PNG"

    def test_cli_preview_waterfall_export_pptx_still_works(self, tmp_path: Path) -> None:
        """Test that PPTX export still works (regression test)."""
        font_path = "testdata/Roboto-VariableFont_wdth,wght.ttf"
        output_path = tmp_path / "waterfall.pptx"

        result = _run_cli(
            "preview-waterfall",
            font_path,
            str(output_path),
            "--format",
            "pptx",
            "--all-named",
        )

        assert result.returncode == 0, f"CLI failed: {result.stderr}"
        assert output_path.exists(), "PPTX file was not created"
        content = output_path.read_bytes()
        assert content[:4] == b"PK\x03\x04", "File is not a valid PPTX (ZIP)"

    def test_cli_preview_waterfall_missing_output_error(self) -> None:
        """Test that missing output path raises an error for PDF/PPTX."""
        font_path = "testdata/Roboto-VariableFont_wdth,wght.ttf"

        result = _run_cli(
            "preview-waterfall",
            font_path,
            "--format",
            "pdf",
            "--all-named",
        )

        assert result.returncode != 0, "CLI should have failed"
        assert "requires OUTPUT" in result.stderr or "requires" in result.stderr.lower()

    def test_cli_preview_matrix_default_png_still_works(self, tmp_path: Path) -> None:
        """Test that PNG export still works for matrix (regression test)."""
        font_path = "testdata/Roboto-VariableFont_wdth,wght.ttf"
        output_path = tmp_path / "matrix.png"

        result = _run_cli(
            "preview-matrix",
            font_path,
            str(output_path),
            "--all-named",
        )

        assert result.returncode == 0, f"CLI failed: {result.stderr}"
        assert output_path.exists(), "PNG file was not created"
        assert output_path.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n", "File is not a valid PNG"

    def test_cli_preview_matrix_export_pptx_still_works(self, tmp_path: Path) -> None:
        """Test that PPTX export still works for matrix (regression test)."""
        font_path = "testdata/Roboto-VariableFont_wdth,wght.ttf"
        output_path = tmp_path / "matrix.pptx"

        result = _run_cli(
            "preview-matrix",
            font_path,
            str(output_path),
            "--format",
            "pptx",
            "--all-named",
        )

        assert result.returncode == 0, f"CLI failed: {result.stderr}"
        assert output_path.exists(), "PPTX file was not created"
        content = output_path.read_bytes()
        assert content[:4] == b"PK\x03\x04", "File is not a valid PPTX (ZIP)"
