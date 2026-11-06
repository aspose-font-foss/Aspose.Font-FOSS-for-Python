"""Tests for aspose_font.cli specimen-playground command (FONT-407)."""
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


def test_specimen_playground_basic(tmp_path: Path) -> None:
    out_dir = tmp_path / "output"
    result = run("specimen-playground", ROBOTO, str(out_dir))
    assert result.returncode == 0
    assert (out_dir / "playground.html").exists()
    assert (out_dir / "playground-manifest.json").exists()
    html = (out_dir / "playground.html").read_text(encoding="utf-8")
    assert "<html" in html.lower() or "<!DOCTYPE" in html
    assert "fontVariationSettings" in html
    assert "Written:" in result.stdout


def test_specimen_playground_dark_mode(tmp_path: Path) -> None:
    out_dir = tmp_path / "output"
    result = run("specimen-playground", ROBOTO, str(out_dir), "--dark-mode")
    assert result.returncode == 0
    html = (out_dir / "playground.html").read_text(encoding="utf-8")
    assert "dark" in html.lower()


def test_specimen_playground_sample_text(tmp_path: Path) -> None:
    out_dir = tmp_path / "output"
    custom_text = "The quick brown fox"
    result = run("specimen-playground", ROBOTO, str(out_dir), "--sample-text", custom_text)
    assert result.returncode == 0
    html = (out_dir / "playground.html").read_text(encoding="utf-8")
    assert custom_text in html


def test_specimen_playground_help() -> None:
    result = run("specimen-playground", "-h")
    assert result.returncode == 0
    assert "specimen-playground" in result.stdout
    assert "--dark-mode" in result.stdout
    assert "--sample-text" in result.stdout


def test_specimen_playground_various_templates(tmp_path: Path) -> None:
    for template in ("classic", "editorial", "lab"):
        out_dir = tmp_path / f"output_{template}"
        result = run("specimen-playground", ROBOTO, str(out_dir), "--template", template)
        assert result.returncode == 0
        html = (out_dir / "playground.html").read_text(encoding="utf-8")
        assert f"specimen-template-{template}" in html


def test_specimen_playground_static_font(tmp_path: Path) -> None:
    static_font = tmp_path / "static.ttf"
    static_font.write_bytes(b"fake")
    out_dir = tmp_path / "output"
    result = run("specimen-playground", str(static_font), str(out_dir))
    assert result.returncode == 1
    assert result.stderr.strip() != ""
