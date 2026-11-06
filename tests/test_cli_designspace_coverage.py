"""Tests for aspose_font.cli designspace-coverage command (FONT-238)."""
from __future__ import annotations

import json
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


def test_designspace_coverage_generates_valid_json(tmp_path: Path):
    """Test that designspace-coverage command runs successfully and produces valid JSON."""
    json_output = tmp_path / "coverage.json"
    result = run(
        "designspace-coverage",
        ROBOTO,
        "--preset",
        "latin",
        "--output",
        str(json_output),
    )

    assert result.returncode == 0
    assert json_output.exists()

    payload = json.loads(json_output.read_text(encoding="utf-8"))
    assert payload["preset"] == "latin"
    assert "total_codepoints" in payload
    assert "covered_codepoints" in payload
    assert "missing_codepoints" in payload
    assert isinstance(payload["missing_codepoints"], list)
    assert all(isinstance(cp, int) for cp in payload["missing_codepoints"])


def test_designspace_coverage_missing_codepoints_are_sorted(tmp_path: Path):
    """Test that missing_codepoints in the output are sorted."""
    json_output = tmp_path / "coverage.json"
    result = run(
        "designspace-coverage",
        ROBOTO,
        "--preset",
        "latin",
        "--output",
        str(json_output),
    )

    assert result.returncode == 0

    payload = json.loads(json_output.read_text(encoding="utf-8"))
    missing = payload["missing_codepoints"]
    assert missing == sorted(missing)


def test_designspace_coverage_unknown_preset_exits_1():
    """Test that unknown preset causes non-zero exit."""
    result = run(
        "designspace-coverage",
        ROBOTO,
        "--preset",
        "nonexistent",
        "--output",
        "/tmp/coverage.json",
    )

    assert result.returncode == 1
    assert "Unknown preset" in result.stderr


def test_designspace_coverage_stdout_shows_coverage_summary(tmp_path: Path):
    """Test that the command prints a coverage summary to stdout."""
    json_output = tmp_path / "coverage.json"
    result = run(
        "designspace-coverage",
        ROBOTO,
        "--preset",
        "latin",
        "--output",
        str(json_output),
    )

    assert result.returncode == 0
    assert "Coverage:" in result.stdout
    assert "codepoints covered" in result.stdout
    assert "Written:" in result.stdout


def test_designspace_coverage_cyrillic_preset(tmp_path: Path):
    """Test designspace-coverage with cyrillic preset."""
    json_output = tmp_path / "coverage.json"
    result = run(
        "designspace-coverage",
        ROBOTO,
        "--preset",
        "cyrillic",
        "--output",
        str(json_output),
    )

    assert result.returncode == 0

    payload = json.loads(json_output.read_text(encoding="utf-8"))
    assert payload["preset"] == "cyrillic"
    assert payload["total_codepoints"] > 0
    assert payload["covered_codepoints"] >= 0
    assert isinstance(payload["missing_codepoints"], list)
