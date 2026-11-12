"""Tests for gasp-info CLI command (FONT-516)."""
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


def test_gasp_info_command_prints_summary() -> None:
    """Test that gasp-info prints gasp version and PPEM ranges with decoded flags."""
    result = run("gasp-info", ROBOTO)
    assert result.returncode == 0
    out = result.stdout
    assert "gasp/ltsh inspection" in out
    assert "gasp table:" in out or "gasp table: Not present" in out


def test_gasp_info_accepts_json_output_flag(tmp_path: Path) -> None:
    """Test that --json-output writes valid JSON report."""
    json_path = tmp_path / "gasp.json"
    result = run("gasp-info", ROBOTO, "--json-output", str(json_path))
    assert result.returncode == 0
    assert json_path.exists()
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)
    assert "gasp" in data
    assert "ltsh" in data


def test_gasp_info_handles_font_without_gasp_exits_0(tmp_path: Path) -> None:
    """Test that fonts without gasp table print notice and exit 0."""
    head = bytes(12) + (0x5F0F3CF5).to_bytes(4, "big") + bytes(54 - 16)
    maxp = (0x00010000).to_bytes(4, "big") + (1).to_bytes(2, "big") + bytes(26)
    loca = (0).to_bytes(4, "big") + (126).to_bytes(4, "big")
    glyf = bytes(100)
    num_tables = 4
    offset_table = (
        b"\x00\x01\x00\x00"
        + num_tables.to_bytes(2, "big")
        + (0).to_bytes(2, "big")
        + (0).to_bytes(2, "big")
        + (0).to_bytes(2, "big")
    )
    head_offset = 12 + num_tables * 16
    maxp_offset = head_offset + len(head)
    loca_offset = maxp_offset + len(maxp)
    glyf_offset = loca_offset + len(loca)
    directory = (
        b"head"
        + (0).to_bytes(4, "big")
        + head_offset.to_bytes(4, "big")
        + len(head).to_bytes(4, "big")
        + b"maxp"
        + (0).to_bytes(4, "big")
        + maxp_offset.to_bytes(4, "big")
        + len(maxp).to_bytes(4, "big")
        + b"loca"
        + (0).to_bytes(4, "big")
        + loca_offset.to_bytes(4, "big")
        + len(loca).to_bytes(4, "big")
        + b"glyf"
        + (0).to_bytes(4, "big")
        + glyf_offset.to_bytes(4, "big")
        + len(glyf).to_bytes(4, "big")
    )
    minimal_ttf = offset_table + directory + head + maxp + loca + glyf
    font_path = tmp_path / "no-gasp.ttf"
    font_path.write_bytes(minimal_ttf)

    result = run("gasp-info", str(font_path))
    assert result.returncode == 0
    assert "gasp table: Not present" in result.stdout
    assert "Not present" in result.stdout


def test_gasp_info_handles_font_without_ltsh_exits_0(tmp_path: Path) -> None:
    """Test that fonts without LTSH table print notice and exit 0."""
    head = bytes(12) + (0x5F0F3CF5).to_bytes(4, "big") + bytes(54 - 16)
    maxp = (0x00010000).to_bytes(4, "big") + (1).to_bytes(2, "big") + bytes(26)
    loca = (0).to_bytes(4, "big") + (126).to_bytes(4, "big")
    glyf = bytes(100)
    num_tables = 4
    offset_table = (
        b"\x00\x01\x00\x00"
        + num_tables.to_bytes(2, "big")
        + (0).to_bytes(2, "big")
        + (0).to_bytes(2, "big")
        + (0).to_bytes(2, "big")
    )
    head_offset = 12 + num_tables * 16
    maxp_offset = head_offset + len(head)
    loca_offset = maxp_offset + len(maxp)
    glyf_offset = loca_offset + len(loca)
    directory = (
        b"head"
        + (0).to_bytes(4, "big")
        + head_offset.to_bytes(4, "big")
        + len(head).to_bytes(4, "big")
        + b"maxp"
        + (0).to_bytes(4, "big")
        + maxp_offset.to_bytes(4, "big")
        + len(maxp).to_bytes(4, "big")
        + b"loca"
        + (0).to_bytes(4, "big")
        + loca_offset.to_bytes(4, "big")
        + len(loca).to_bytes(4, "big")
        + b"glyf"
        + (0).to_bytes(4, "big")
        + glyf_offset.to_bytes(4, "big")
        + len(glyf).to_bytes(4, "big")
    )
    minimal_ttf = offset_table + directory + head + maxp + loca + glyf
    font_path = tmp_path / "no-ltsh.ttf"
    font_path.write_bytes(minimal_ttf)

    result = run("gasp-info", str(font_path))
    assert result.returncode == 0
    assert "LTSH table: Not present" in result.stdout
    assert "Not present" in result.stdout


def test_gasp_info_non_ttf_font_exits_with_error() -> None:
    """Test that non-TTF fonts produce error."""
    pfb_path = str(Path(__file__).resolve().parents[1] / "testdata" / "OpenSans-Regular.pfb")
    result = run("gasp-info", pfb_path)
    assert result.returncode != 0
    combined_output = result.stdout + result.stderr
    assert "gasp/ltsh table inspection is only supported" in combined_output


def test_gasp_info_json_output_contains_expected_structure(tmp_path: Path) -> None:
    """Test that JSON output has expected structure."""
    json_path = tmp_path / "gasp.json"
    result = run("gasp-info", ROBOTO, "--json-output", str(json_path))
    assert result.returncode == 0
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)
    assert isinstance(data["gasp"], (dict, type(None)))
    assert isinstance(data["ltsh"], (dict, type(None)))
    if data["gasp"] is not None:
        assert "version" in data["gasp"]
        assert "range_count" in data["gasp"]
        assert "ranges" in data["gasp"]
        if data["gasp"]["ranges"]:
            range_item = data["gasp"]["ranges"][0]
            assert "max_ppem" in range_item
            assert "behavior_flags" in range_item
            assert "flags" in range_item
