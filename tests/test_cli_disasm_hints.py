"""Tests for disasm-hints CLI command (FONT-553)."""
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


def test_disasm_hints_command_prints_summary() -> None:
    """Test that disasm-hints prints font program instructions."""
    result = run("disasm-hints", ROBOTO, "--table", "fpgm")
    assert result.returncode == 0
    out = result.stdout
    assert "fpgm" in out.lower() or "font program" in out.lower()


def test_disasm_hints_prep_table() -> None:
    """Test that --table prep works."""
    result = run("disasm-hints", ROBOTO, "--table", "prep")
    assert result.returncode == 0
    out = result.stdout
    assert "prep" in out.lower() or "pre-program" in out.lower()


def test_disasm_hints_with_glyph_id() -> None:
    """Test that --glyph option works with a glyph ID."""
    result = run("disasm-hints", ROBOTO, "--glyph", "0")
    assert result.returncode == 0
    out = result.stdout
    assert "glyf" in out.lower() or "glyph" in out.lower()


def test_disasm_hints_json_flag() -> None:
    """Test that --json flag outputs valid JSON."""
    result = run("disasm-hints", ROBOTO, "--table", "fpgm", "--json")
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert "instructions" in data
    assert "total_instruction_count" in data
    assert "font" in data


def test_disasm_hints_json_structure() -> None:
    """Test that JSON output has expected structure."""
    result = run("disasm-hints", ROBOTO, "--table", "fpgm", "--json")
    assert result.returncode == 0
    data = json.loads(result.stdout)

    assert isinstance(data["font"], dict)
    assert "format" in data["font"]
    assert "num_glyphs" in data["font"]

    assert isinstance(data["instructions"], list)
    assert isinstance(data["total_instruction_count"], int)

    for instr_report in data["instructions"]:
        if "instructions" in instr_report:
            for instruction in instr_report["instructions"]:
                assert "opcode" in instruction
                assert "mnemonic" in instruction
                assert "args" in instruction
                assert "offset" in instruction


def test_disasm_hints_json_output_to_file(tmp_path: Path) -> None:
    """Test that --json-output flag writes JSON report to file."""
    output_file = tmp_path / "disasm-report.json"
    result = run("disasm-hints", ROBOTO, "--table", "fpgm", "--json-output", str(output_file))
    assert result.returncode == 0
    assert f"Saved: {output_file}" in result.stdout
    assert output_file.exists()
    data = json.loads(output_file.read_text())
    assert "instructions" in data
    assert "total_instruction_count" in data


def test_disasm_hints_non_ttf_font_exits_with_error() -> None:
    """Test that non-TTF fonts produce error."""
    pfb_path = str(Path(__file__).resolve().parents[1] / "testdata" / "OpenSans-Regular.pfb")
    result = run("disasm-hints", pfb_path)
    assert result.returncode != 0
    combined_output = result.stdout + result.stderr
    assert "disasm-hints inspection is only supported" in combined_output


def test_disasm_hints_invalid_glyph_id_exits_with_error() -> None:
    """Test that invalid glyph ID produces error."""
    result = run("disasm-hints", ROBOTO, "--glyph", "invalid")
    assert result.returncode != 0


def test_disasm_hints_all_tables() -> None:
    """Test that disasm-hints without --table shows all available tables."""
    result = run("disasm-hints", ROBOTO)
    assert result.returncode == 0
    out = result.stdout
    assert "fpgm" in out.lower() or "font program" in out.lower() or "prep" in out.lower() or "pre-program" in out.lower()


def test_disasm_hints_glyph_range_out_of_bounds() -> None:
    """Test that out of range glyph ID produces error message."""
    result = run("disasm-hints", ROBOTO, "--glyph", "999999")
    assert result.returncode == 0
    assert "out of range" in result.stdout
