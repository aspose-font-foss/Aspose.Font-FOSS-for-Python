"""Tests for gpos-info CLI command (FONT-448)."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from aspose_font import FontLoader

ROBOTO = str(Path(__file__).resolve().parents[1] / "testdata" / "Roboto-VariableFont_wdth,wght.ttf")
CLI = [sys.executable, "-m", "aspose_font.cli"]


def run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        CLI + list(args),
        capture_output=True,
        text=True,
    )


def test_gpos_info_command_prints_scripts_and_features() -> None:
    """Test that gpos-info prints available scripts and features for font with GPOS."""
    font = FontLoader.open(ROBOTO)
    if font.ttf_tables.gpos is None:
        pytest.skip("Roboto font in test suite does not have GPOS table")

    result = run("gpos-info", ROBOTO)
    assert result.returncode == 0
    out = result.stdout
    assert "GPOS table:" in out
    assert "Scripts:" in out


def test_gpos_info_accepts_json_output_flag(tmp_path: Path) -> None:
    """Test that --json-output writes valid JSON report."""
    font = FontLoader.open(ROBOTO)
    if font.ttf_tables.gpos is None:
        pytest.skip("Roboto font in test suite does not have GPOS table")

    json_path = tmp_path / "gpos.json"
    result = run("gpos-info", ROBOTO, "--json-output", str(json_path))
    assert result.returncode == 0
    assert json_path.exists()
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)
    assert "version" in data
    assert "scripts" in data
    assert "features" in data


def test_gpos_info_handles_font_without_gpos_exits_0(tmp_path: Path) -> None:
    """Test that fonts without GPOS table print notice and exit 0."""
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
    font_path = tmp_path / "no-gpos.ttf"
    font_path.write_bytes(minimal_ttf)

    result = run("gpos-info", str(font_path))
    assert result.returncode == 0
    assert "GPOS table: Not present" in result.stdout
    assert "Not present" in result.stdout


def test_gpos_info_accepts_script_filter() -> None:
    """Test that --script flag filters output to one script."""
    font = FontLoader.open(ROBOTO)
    if font.ttf_tables.gpos is None:
        pytest.skip("Roboto font in test suite does not have GPOS table")

    result = run("gpos-info", ROBOTO, "--script", "latn")
    assert result.returncode == 0
    assert "latn" in result.stdout


def test_gpos_info_accepts_feature_filter() -> None:
    """Test that --feature flag filters output to one feature (e.g., 'kern')."""
    font = FontLoader.open(ROBOTO)
    if font.ttf_tables.gpos is None:
        pytest.skip("Roboto font in test suite does not have GPOS table")

    result = run("gpos-info", ROBOTO, "--feature", "kern")
    assert result.returncode == 0
    assert "kern" in result.stdout


def test_gpos_info_json_output_contains_expected_structure(tmp_path: Path) -> None:
    """Test that JSON output has version, scripts, and features fields."""
    font = FontLoader.open(ROBOTO)
    if font.ttf_tables.gpos is None:
        pytest.skip("Roboto font in test suite does not have GPOS table")

    json_path = tmp_path / "gpos.json"
    result = run("gpos-info", ROBOTO, "--json-output", str(json_path))
    assert result.returncode == 0
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)
    assert isinstance(data["version"], int)
    assert isinstance(data["scripts"], list)
    assert isinstance(data["features"], list)


def test_gpos_info_non_ttf_font_exits_with_error() -> None:
    """Test that non-TTF fonts produce error."""
    pfb_path = str(Path(__file__).resolve().parents[1] / "testdata" / "OpenSans-Regular.pfb")
    result = run("gpos-info", pfb_path)
    assert result.returncode != 0
    assert "GPOS table inspection is only supported" in result.stdout or result.stderr
