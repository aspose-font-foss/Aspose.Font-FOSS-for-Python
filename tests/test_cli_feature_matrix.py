"""Tests for feature-matrix CLI command (FONT-484)."""
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


def test_feature_matrix_command_registers() -> None:
    """Test that feature-matrix subcommand is registered and shows help."""
    result = run("feature-matrix", "--help")
    assert result.returncode == 0
    assert "feature-matrix" in result.stdout
    assert "OpenType feature discovery matrix" in result.stdout


def test_feature_matrix_command_runs_successfully() -> None:
    """Test that feature-matrix executes without error on valid font."""
    result = run("feature-matrix", ROBOTO)
    assert result.returncode == 0
    assert "Font Feature Discovery Matrix" in result.stdout
    assert "GSUB:" in result.stdout
    assert "GPOS:" in result.stdout


def test_feature_matrix_ascii_output_format() -> None:
    """Test that ASCII output has expected table format."""
    result = run("feature-matrix", ROBOTO)
    assert result.returncode == 0
    out = result.stdout

    assert "Font Feature Discovery Matrix" in out
    assert "=" * 40 in out
    assert "\nGSUB:" in out
    assert "\nGPOS:" in out
    assert "\nSTAT:" in out
    assert "\nCOLR:" in out
    assert "\nSVG:" in out
    assert "\nSBIX:" in out


def test_feature_matrix_json_output(tmp_path: Path) -> None:
    """Test that --json-output produces valid JSON with correct keys."""
    json_path = tmp_path / "feature_matrix.json"
    result = run("feature-matrix", ROBOTO, "--json-output", str(json_path))
    assert result.returncode == 0
    assert "Saved:" in result.stdout
    assert json_path.exists()

    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)

    assert isinstance(data, dict)
    assert set(data.keys()) == {"GSUB", "GPOS", "STAT", "COLR", "SVG", "SBIX"}
    assert all(isinstance(v, list) for v in data.values())


def test_feature_matrix_script_filter() -> None:
    """Test that --script filter works correctly."""
    result = run("feature-matrix", ROBOTO, "--script", "latn")
    assert result.returncode == 0
    assert "Font Feature Discovery Matrix" in result.stdout


def test_feature_matrix_non_ttf_font(tmp_path: Path) -> None:
    """Test graceful handling of non-TTF fonts (CFF)."""
    cff_path = str(Path(__file__).resolve().parents[1] / "testdata" / "OpenSans-Regular.cff")
    result = run("feature-matrix", cff_path)
    assert result.returncode == 0
    out = result.stdout
    assert "Font Feature Discovery Matrix" in out
    for table in ["GSUB", "GPOS", "STAT", "COLR", "SVG", "SBIX"]:
        assert f"{table}:" in out


def test_feature_matrix_missing_file(tmp_path: Path) -> None:
    """Test proper error on non-existent file."""
    missing_file = tmp_path / "nonexistent.ttf"
    result = run("feature-matrix", str(missing_file))
    assert result.returncode != 0
    assert "Error:" in result.stdout or "Error:" in result.stderr


def test_feature_matrix_json_output_structure(tmp_path: Path) -> None:
    """Test that JSON output has expected structure with lists."""
    json_path = tmp_path / "feature_matrix.json"
    result = run("feature-matrix", ROBOTO, "--json-output", str(json_path))
    assert result.returncode == 0

    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)

    assert isinstance(data["GSUB"], list)
    assert isinstance(data["GPOS"], list)
    assert isinstance(data["STAT"], list)
    assert isinstance(data["COLR"], list)
    assert isinstance(data["SVG"], list)
    assert isinstance(data["SBIX"], list)


def test_feature_matrix_cff_font_output(tmp_path: Path) -> None:
    """Test feature-matrix on CFF font produces empty feature lists."""
    cff_path = str(Path(__file__).resolve().parents[1] / "testdata" / "OpenSans-Regular.cff")
    json_path = tmp_path / "cff_matrix.json"
    result = run("feature-matrix", cff_path, "--json-output", str(json_path))
    assert result.returncode == 0
    assert json_path.exists()

    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)

    assert data["GSUB"] == []
    assert data["GPOS"] == []
    assert data["STAT"] == []
    assert data["COLR"] == []
    assert data["SVG"] == []
    assert data["SBIX"] == []


def test_feature_matrix_json_flag_stdout() -> None:
    """Test feature-matrix with --json flag outputs to stdout."""
    result = run("feature-matrix", ROBOTO, "--json")
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert set(data.keys()) == {"GSUB", "GPOS", "STAT", "COLR", "SVG", "SBIX"}
    assert isinstance(data["GSUB"], list)
