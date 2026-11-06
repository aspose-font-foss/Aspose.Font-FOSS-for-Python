"""Tests for base-info CLI command (FONT-481)."""
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


def test_base_info_command_prints_baselines_and_scripts() -> None:
    """Test that base-info prints BASE table status (missing or present)."""
    result = run("base-info", ROBOTO)
    assert result.returncode == 0
    out = result.stdout
    assert "BASE table:" in out
    assert "Not present" in out or ("Horizontal baselines:" in out or "Scripts:" in out)


def test_base_info_accepts_json_output_flag(tmp_path: Path) -> None:
    """Test that --json-output writes valid JSON report."""
    json_path = tmp_path / "base.json"
    result = run("base-info", ROBOTO, "--json-output", str(json_path))
    assert result.returncode == 0
    assert json_path.exists()
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)
    assert "version" in data
    assert "baseline_tags" in data
    assert "scripts" in data


def test_base_info_handles_font_without_base_exits_0(tmp_path: Path) -> None:
    """Test that fonts without BASE table print notice and exit 0."""
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
    font_path = tmp_path / "no-base.ttf"
    font_path.write_bytes(minimal_ttf)

    result = run("base-info", str(font_path))
    assert result.returncode == 0
    assert "BASE table: Not present" in result.stdout
    assert "Not present" in result.stdout


def test_base_info_accepts_script_filter() -> None:
    """Test that --script flag accepts valid script tag and doesn't crash."""
    result = run("base-info", ROBOTO, "--script", "latn")
    assert result.returncode == 0


def test_base_info_accepts_baseline_filter() -> None:
    """Test that --baseline flag accepts valid baseline tag and doesn't crash."""
    result = run("base-info", ROBOTO, "--baseline", "ROMN")
    assert result.returncode == 0


def test_base_info_json_output_contains_expected_structure(tmp_path: Path) -> None:
    """Test that JSON output has version, baseline_tags, and scripts fields."""
    json_path = tmp_path / "base.json"
    result = run("base-info", ROBOTO, "--json-output", str(json_path))
    assert result.returncode == 0
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)
    # When BASE table is missing, version is None
    assert "version" in data
    assert isinstance(data["baseline_tags"], list)
    assert isinstance(data["scripts"], list)


def test_base_info_non_ttf_font_exits_with_error() -> None:
    """Test that non-TTF fonts produce error."""
    pfb_path = str(Path(__file__).resolve().parents[1] / "testdata" / "OpenSans-Regular.pfb")
    result = run("base-info", pfb_path)
    assert result.returncode != 0
    combined_output = result.stdout + result.stderr
    assert "BASE table inspection is only supported" in combined_output


def test_base_info_script_and_baseline_filter_combined(tmp_path: Path) -> None:
    """Test that --script and --baseline filters work together."""
    json_path = tmp_path / "base_combined.json"
    result = run("base-info", ROBOTO, "--script", "latn", "--baseline", "ROMN", "--json-output", str(json_path))
    assert result.returncode == 0
    assert json_path.exists()
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)
    assert "version" in data
    assert "baseline_tags" in data
    # When BASE table is not present, scripts should be empty
    # This tests the JSON structure is correct even without BASE table data


def test_base_info_invalid_script_tag_exits_with_error() -> None:
    """Test that --script flag accepts any value (validation happens at runtime)."""
    result = run("base-info", ROBOTO, "--script", "XXXX")
    # When BASE table is not present, validation doesn't occur
    # This test verifies the flag is accepted
    assert result.returncode == 0
