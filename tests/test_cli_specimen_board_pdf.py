"""PDF output test for aspose_font.cli specimen-board command (FONT-384)."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROBOTO = str(Path(__file__).resolve().parents[1] / "testdata" / "Roboto-VariableFont_wdth,wght.ttf")
CLI = [sys.executable, "-m", "aspose_font.cli"]

def run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        CLI + list(args),
        capture_output=True,
        text=True,
    )

def test_specimen_board_pdf_output(tmp_path: Path) -> None:
    out = tmp_path / "specimen.pdf"
    result = run("specimen-board", ROBOTO, str(out), "--format", "pdf", "--text", "Specimen")
    assert result.returncode == 0
    assert out.exists()
    data = out.read_bytes()
    assert data.startswith(b"%PDF-")
    assert "Saved:" in result.stdout
