"""Tests for math-info CLI command (FONT-487)."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROBOTO = str(Path(__file__).resolve().parents[1] / "testdata" / "Roboto-VariableFont_wdth,wght.ttf")
CLI = [sys.executable, "-m", "aspose_font.cli"]


def run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        CLI + list(args),
        capture_output=True,
        text=True,
    )


def test_math_info_command_prints_summary() -> None:
    """Test that math-info prints MATH table summary."""
    result = run("math-info", ROBOTO)
    assert result.returncode == 0
    out = result.stdout
    assert "MATH table:" in out
    assert "Constants:" in out or "Glyph info:" in out or "Variant glyphs:" in out or "Not present" in out


def test_math_info_accepts_json_output_flag(tmp_path: Path) -> None:
    """Test that --json-output writes valid JSON report for font with MATH table."""
    # Note: Roboto font doesn't have MATH table, so this test requires a font with MATH
    # For now, we'll skip this test until a font with MATH table is available in testdata
    pytest.skip("Requires a font with MATH table in testdata (e.g., Cambria Math or Latin Modern Math)")


def test_math_info_handles_font_without_math_exits_0(tmp_path: Path) -> None:
    """Test that fonts without MATH table print notice and exit 0."""
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
    font_path = tmp_path / "no-math.ttf"
    font_path.write_bytes(minimal_ttf)

    result = run("math-info", str(font_path))
    assert result.returncode == 0
    assert "MATH table: Not present" in result.stdout
    assert "Note:" in result.stdout


def test_math_info_non_ttf_font_exits_with_error() -> None:
    """Test that non-TTF fonts produce error."""
    pfb_path = str(Path(__file__).resolve().parents[1] / "testdata" / "OpenSans-Regular.pfb")
    result = run("math-info", pfb_path)
    assert result.returncode != 0
    combined_output = result.stdout + result.stderr
    assert "MATH table inspection is only supported" in combined_output


def test_math_info_json_output_contains_expected_structure(tmp_path: Path) -> None:
    """Test that JSON output has expected structure for font with MATH table."""
    # Note: Roboto font doesn't have MATH table, so this test requires a font with MATH
    # For now, we'll skip this test until a font with MATH table is available in testdata
    pytest.skip("Requires a font with MATH table in testdata (e.g., Cambria Math or Latin Modern Math)")
