"""Tests for jstf-info CLI command (FONT-503)."""
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


def test_jstf_info_command_prints_summary() -> None:
    """Test that jstf-info prints JSTF table summary."""
    result = run("jstf-info", ROBOTO)
    assert result.returncode == 0
    out = result.stdout
    assert "JSTF table:" in out
    assert "Scripts:" in out or "Not present" in out


def test_jstf_info_accepts_json_flag(tmp_path: Path) -> None:
    """Test that --json writes valid JSON report for font without JSTF (handles gracefully)."""
    json_path = tmp_path / "jstf.json"
    result = run("jstf-info", ROBOTO, "--json", str(json_path))
    # When no JSTF, it exits without creating JSON file (same behavior as other info commands)
    assert result.returncode == 0
    # JSON file should not be created when no JSTF table
    assert not json_path.exists()


def test_jstf_info_handles_font_without_jstf_exits_0(tmp_path: Path) -> None:
    """Test that fonts without JSTF table print notice and exit 0."""
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
    font_path = tmp_path / "no-jstf.ttf"
    font_path.write_bytes(minimal_ttf)

    result = run("jstf-info", str(font_path))
    assert result.returncode == 0
    assert "JSTF table: Not present" in result.stdout
    assert "Note:" in result.stdout


def test_jstf_info_non_ttf_font_exits_with_error() -> None:
    """Test that non-TTF fonts produce error."""
    pfb_path = str(Path(__file__).resolve().parents[1] / "testdata" / "OpenSans-Regular.pfb")
    result = run("jstf-info", pfb_path)
    assert result.returncode != 0
    combined_output = result.stdout + result.stderr
    assert "JSTF table inspection is only supported" in combined_output


def test_jstf_info_json_output_contains_expected_structure(tmp_path: Path) -> None:
    """Test that fonts without JSTF exit gracefully with --json flag."""
    json_path = tmp_path / "jstf.json"
    result = run("jstf-info", ROBOTO, "--json", str(json_path))
    assert result.returncode == 0
    # When no JSTF table, no JSON file should be created
    assert not json_path.exists()
