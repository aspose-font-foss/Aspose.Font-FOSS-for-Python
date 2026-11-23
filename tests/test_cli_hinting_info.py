"""Tests for hinting-info CLI command (FONT-538)."""
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


def test_hinting_info_command_prints_summary() -> None:
    """Test that hinting-info prints hinting table summary."""
    result = run("hinting-info", ROBOTO)
    assert result.returncode == 0
    out = result.stdout
    assert "hinting inspection" in out


def test_hinting_info_accepts_json_flag(tmp_path: Path) -> None:
    """Test that --json flag outputs valid JSON to stdout."""
    result = run("hinting-info", ROBOTO, "--json")
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert "cvt" in data
    assert "fpgm" in data
    assert "prep" in data
    assert "gasp" in data


def test_hinting_info_handles_font_without_hinting_exits_0(tmp_path: Path) -> None:
    """Test that fonts without hinting tables print notice and exit 0."""
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
    font_path = tmp_path / "no-hinting.ttf"
    font_path.write_bytes(minimal_ttf)

    result = run("hinting-info", str(font_path))
    assert result.returncode == 0
    assert "CVT table: Not present" in result.stdout
    assert "fpgm table: Not present" in result.stdout
    assert "prep table: Not present" in result.stdout
    assert "gasp table: Not present" in result.stdout


def test_hinting_info_non_ttf_font_exits_with_error() -> None:
    """Test that non-TTF fonts produce error."""
    pfb_path = str(Path(__file__).resolve().parents[1] / "testdata" / "OpenSans-Regular.pfb")
    result = run("hinting-info", pfb_path)
    assert result.returncode != 0
    combined_output = result.stdout + result.stderr
    assert "hinting-info inspection is only supported" in combined_output


def test_hinting_info_json_structure() -> None:
    """Test that JSON output has expected structure for all hinting tables."""
    result = run("hinting-info", ROBOTO, "--json")
    assert result.returncode == 0
    data = json.loads(result.stdout)

    assert isinstance(data["cvt"], (dict, type(None)))
    assert isinstance(data["fpgm"], (dict, type(None)))
    assert isinstance(data["prep"], (dict, type(None)))
    assert isinstance(data["gasp"], (dict, type(None)))

    if data["cvt"] is not None:
        assert "value_count" in data["cvt"]
        assert "byte_size" in data["cvt"]
        assert "value_range" in data["cvt"]

    if data["fpgm"] is not None:
        assert "byte_size" in data["fpgm"]
        assert "estimated_savings" in data["fpgm"]
        assert "estimated_savings_percent" in data["fpgm"]

    if data["prep"] is not None:
        assert "byte_size" in data["prep"]
        assert "estimated_savings" in data["prep"]
        assert "estimated_savings_percent" in data["prep"]

    if data["gasp"] is not None:
        assert "version" in data["gasp"]
        assert "range_count" in data["gasp"]
        assert "ranges" in data["gasp"]
        if data["gasp"]["ranges"]:
            range_item = data["gasp"]["ranges"][0]
            assert "max_ppem" in range_item
            assert "behavior_flags" in range_item
            assert "flags" in range_item


def test_hinting_info_cvt_table_details(tmp_path: Path) -> None:
    """Test that CVT table details are reported correctly when present."""
    cvt_data = bytes([0x00, 0x00, 0x00, 0x32, 0xFF, 0xFE])
    head = bytes(12) + (0x5F0F3CF5).to_bytes(4, "big") + bytes(54 - 16)
    maxp = (0x00010000).to_bytes(4, "big") + (1).to_bytes(2, "big") + bytes(26)
    loca = (0).to_bytes(4, "big") + (126).to_bytes(4, "big")
    glyf = bytes(100)
    num_tables = 5
    offset_table = (
        b"\x00\x01\x00\x00"
        + num_tables.to_bytes(2, "big")
        + (0).to_bytes(2, "big")
        + (0).to_bytes(2, "big")
        + (0).to_bytes(2, "big")
    )
    head_offset = 12 + num_tables * 16
    maxp_offset = head_offset + len(head)
    cvt_offset = maxp_offset + len(maxp)
    loca_offset = cvt_offset + len(cvt_data)
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
        + b"cvt "
        + (0).to_bytes(4, "big")
        + cvt_offset.to_bytes(4, "big")
        + len(cvt_data).to_bytes(4, "big")
        + b"loca"
        + (0).to_bytes(4, "big")
        + loca_offset.to_bytes(4, "big")
        + len(loca).to_bytes(4, "big")
        + b"glyf"
        + (0).to_bytes(4, "big")
        + glyf_offset.to_bytes(4, "big")
        + len(glyf).to_bytes(4, "big")
    )
    minimal_ttf = offset_table + directory + head + maxp + cvt_data + loca + glyf
    font_path = tmp_path / "with-cvt.ttf"
    font_path.write_bytes(minimal_ttf)

    result = run("hinting-info", str(font_path))
    assert result.returncode == 0
    assert "CVT table:" in result.stdout
    assert "2 control values" in result.stdout


def test_hinting_info_program_tables_details(tmp_path: Path) -> None:
    """Test that fpgm and prep program details are reported correctly."""
    fpgm_data = bytes([0x01, 0x02, 0x03, 0x04, 0x05])
    prep_data = bytes([0x10, 0x20, 0x30, 0x40])
    head = bytes(12) + (0x5F0F3CF5).to_bytes(4, "big") + bytes(54 - 16)
    maxp = (0x00010000).to_bytes(4, "big") + (1).to_bytes(2, "big") + bytes(26)
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
    fpgm_offset = maxp_offset + len(maxp)
    prep_offset = fpgm_offset + len(fpgm_data)
    directory = (
        b"head"
        + (0).to_bytes(4, "big")
        + head_offset.to_bytes(4, "big")
        + len(head).to_bytes(4, "big")
        + b"maxp"
        + (0).to_bytes(4, "big")
        + maxp_offset.to_bytes(4, "big")
        + len(maxp).to_bytes(4, "big")
        + b"fpgm"
        + (0).to_bytes(4, "big")
        + fpgm_offset.to_bytes(4, "big")
        + len(fpgm_data).to_bytes(4, "big")
        + b"prep"
        + (0).to_bytes(4, "big")
        + prep_offset.to_bytes(4, "big")
        + len(prep_data).to_bytes(4, "big")
    )
    tables_data = head + maxp + fpgm_data + prep_data
    minimal_ttf = offset_table + directory + tables_data
    font_path = tmp_path / "with-programs.ttf"
    font_path.write_bytes(minimal_ttf)

    result = run("hinting-info", str(font_path))
    assert result.returncode == 0
    assert "fpgm table:" in result.stdout
    assert "5 bytes" in result.stdout
    assert "prep table:" in result.stdout
    assert "4 bytes" in result.stdout


def test_hinting_info_json_output_to_file(tmp_path: Path) -> None:
    """Test that --json-output flag writes JSON report to file."""
    output_file = tmp_path / "hinting-report.json"
    result = run("hinting-info", ROBOTO, "--json-output", str(output_file))
    assert result.returncode == 0
    assert f"Saved: {output_file}" in result.stdout
    assert output_file.exists()
    data = json.loads(output_file.read_text())
    assert "cvt" in data
    assert "fpgm" in data
    assert "prep" in data
    assert "gasp" in data
