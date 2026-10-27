"""Tests for gsub-info CLI command (FONT-445)."""
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


def test_gsub_info_command_prints_scripts_and_features() -> None:
    """Test that gsub-info prints available scripts and features for font with GSUB."""
    result = run("gsub-info", ROBOTO)
    assert result.returncode == 0
    out = result.stdout
    assert "GSUB table:" in out
    assert "Scripts:" in out
    assert "latn" in out or "DFLT" in out


def test_gsub_info_accepts_json_output_flag(tmp_path: Path) -> None:
    """Test that --json-output writes valid JSON report."""
    json_path = tmp_path / "gsub.json"
    result = run("gsub-info", ROBOTO, "--json-output", str(json_path))
    assert result.returncode == 0
    assert json_path.exists()
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)
    assert "version" in data
    assert "scripts" in data
    assert "features" in data


def test_gsub_info_handles_font_without_gsub_exits_0(tmp_path: Path) -> None:
    """Test that fonts without GSUB table print notice and exit 0."""
    # Create a minimal TTF font without GSUB table
    head = bytes(12) + (0x5F0F3CF5).to_bytes(4, "big") + bytes(54 - 16)
    maxp = (0x00010000).to_bytes(4, "big") + (1).to_bytes(2, "big") + bytes(26)
    num_tables = 2
    offset_table = (
        b"\x00\x01\x00\x00"
        + num_tables.to_bytes(2, "big")
        + (0).to_bytes(2, "big")
        + (0).to_bytes(2, "big")
        + (0).to_bytes(2, "big")
    )
    head_offset = 12 + num_tables * 16
    maxp_offset = head_offset + len(head)
    directory = (
        b"head"
        + (0).to_bytes(4, "big")
        + head_offset.to_bytes(4, "big")
        + len(head).to_bytes(4, "big")
        + b"maxp"
        + (0).to_bytes(4, "big")
        + maxp_offset.to_bytes(4, "big")
        + len(maxp).to_bytes(4, "big")
    )
    minimal_ttf = offset_table + directory + head + maxp
    font_path = tmp_path / "no-gsub.ttf"
    font_path.write_bytes(minimal_ttf)

    result = run("gsub-info", str(font_path))
    assert result.returncode == 0
    assert "GSUB table: Not present" in result.stdout
    assert "Not present" in result.stdout


def test_gsub_info_accepts_script_filter() -> None:
    """Test that --script flag filters output to one script."""
    result = run("gsub-info", ROBOTO, "--script", "latn")
    assert result.returncode == 0
    # Should contain latn and its features
    assert "latn" in result.stdout


def test_gsub_info_accepts_feature_filter() -> None:
    """Test that --feature flag filters output to one feature."""
    result = run("gsub-info", ROBOTO, "--feature", "liga")
    assert result.returncode == 0
    # Should contain liga
    assert "liga" in result.stdout


def test_gsub_info_json_output_contains_expected_structure(tmp_path: Path) -> None:
    """Test that JSON output has version, scripts, and features fields."""
    json_path = tmp_path / "gsub.json"
    result = run("gsub-info", ROBOTO, "--json-output", str(json_path))
    assert result.returncode == 0
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)
    assert isinstance(data["version"], int)
    assert isinstance(data["scripts"], list)
    assert isinstance(data["features"], list)


def test_gsub_info_non_ttf_font_exits_with_error() -> None:
    """Test that non-TTF fonts produce error."""
    # Use a Type1 font (PFB) which doesn't support GSUB
    pfb_path = str(Path(__file__).resolve().parents[1] / "testdata" / "OpenSans-Regular.pfb")
    result = run("gsub-info", pfb_path)
    assert result.returncode != 0
    assert "GSUB table inspection is only supported" in result.stdout or result.stderr


def test_gsub_info_script_and_feature_filter_combined(tmp_path: Path) -> None:
    """Test that --script and --feature filters work together."""
    json_path = tmp_path / "gsub_combined.json"
    result = run("gsub-info", ROBOTO, "--script", "latn", "--feature", "liga", "--json-output", str(json_path))
    assert result.returncode == 0
    assert json_path.exists()
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)
    assert "version" in data
    assert "scripts" in data
    assert len(data["scripts"]) == 1
    assert data["scripts"][0]["tag"] == "latn"
    assert "liga" in data["scripts"][0]["features"]
    assert "liga" in data["features"]


def test_gsub_info_invalid_script_tag_exits_with_error() -> None:
    """Test that non-existent script tag produces error."""
    result = run("gsub-info", ROBOTO, "--script", "XXXX")
    assert result.returncode != 0
    combined_output = result.stdout + result.stderr
    assert "not found" in combined_output
