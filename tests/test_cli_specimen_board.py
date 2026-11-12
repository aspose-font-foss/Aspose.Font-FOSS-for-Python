"""Tests for aspose_font.cli specimen-board command (FONT-330)."""
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


def test_specimen_board_png_output(tmp_path: Path) -> None:
    out = tmp_path / "specimen.png"
    result = run("specimen-board", ROBOTO, str(out), "--text", "Specimen")
    assert result.returncode == 0
    assert out.exists()
    data = out.read_bytes()
    assert data.startswith(b"\x89PNG\r\n\x1a\n")
    assert "Saved:" in result.stdout


def test_specimen_board_html_output(tmp_path: Path) -> None:
    out = tmp_path / "specimen.html"
    result = run("specimen-board", ROBOTO, str(out), "--format", "html", "--text", "Specimen")
    assert result.returncode == 0
    assert out.exists()
    html = out.read_text(encoding="utf-8")
    assert "<html" in html.lower() or "<!DOCTYPE" in html
    assert "Saved:" in result.stdout


def test_specimen_board_requires_variable_font(tmp_path: Path) -> None:
    static_font = tmp_path / "static.ttf"
    static_font.write_bytes(b"fake")
    out = tmp_path / "specimen.png"
    result = run("specimen-board", str(static_font), str(out))
    assert result.returncode == 1
    assert result.stderr.strip() != ""


def test_specimen_board_help() -> None:
    result = run("specimen-board", "-h")
    assert result.returncode == 0
    assert "specimen-board" in result.stdout
    assert "--format" in result.stdout
    assert "--instance-name" in result.stdout

