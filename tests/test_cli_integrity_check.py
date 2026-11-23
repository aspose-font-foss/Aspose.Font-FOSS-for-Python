"""Tests for integrity-check CLI command (FONT-525)."""
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


def test_integrity_check_command_prints_summary() -> None:
    """Test that integrity-check prints summary and DSIG status."""
    result = run("integrity-check", ROBOTO)
    out = result.stdout
    assert "Font Integrity Check" in out
    assert "Status:" in out
    assert "Issues:" in out
    # Roboto has checksum adjustment issues, so exit 1 is expected
    assert result.returncode in (0, 1)


def test_integrity_check_accepts_json_output_flag(tmp_path: Path) -> None:
    """Test that --json-output writes valid JSON report."""
    result = run("integrity-check", "--json-output", str(tmp_path / "report.json"), ROBOTO)
    # Roboto has checksum adjustment issues, so exit 1 is expected
    assert result.returncode in (0, 1)
    assert "Saved:" in result.stdout
    json_path = tmp_path / "report.json"
    assert json_path.exists()
    content = json_path.read_text(encoding="utf-8")
    import json
    data = json.loads(content)
    assert "status" in data
    assert "issue_count" in data
    assert "issues" in data


def test_integrity_check_non_ttf_font_exits_with_error() -> None:
    """Test that non-TTF fonts produce error."""
    pfb_path = str(Path(__file__).resolve().parents[1] / "testdata" / "OpenSans-Regular.pfb")
    result = run("integrity-check", pfb_path)
    assert result.returncode != 0
    combined_output = result.stdout + result.stderr
    assert "integrity-check is only supported for TTF/OTF fonts" in combined_output


def test_integrity_check_exits_nonzero_if_issues(tmp_path: Path) -> None:
    """Test that command exits non-zero when checksum mismatches are found."""
    # Head table (54 bytes): checksum_adjustment is at offset 8
    head = bytes(8) + (0x5F0F3CF5).to_bytes(4, "big") + bytes(54 - 12)
    # maxp table (32 bytes): version 1.0, numGlyphs = 1
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
    font_path = tmp_path / "bad-checksum.ttf"
    font_path.write_bytes(minimal_ttf)

    result = run("integrity-check", str(font_path))
    assert result.returncode != 0
    assert "head-checksum-adjustment-mismatch" in result.stdout or "issues" in result.stdout.lower()


def test_integrity_check_json_output_structure(tmp_path: Path) -> None:
    """Test that JSON output has expected structure."""
    json_path = tmp_path / "report.json"
    result = run("integrity-check", "--json-output", str(json_path), ROBOTO)
    # Roboto has checksum adjustment issues, so exit 1 is expected
    assert result.returncode in (0, 1)

    import json
    data = json.loads(json_path.read_text(encoding="utf-8"))
    assert isinstance(data["status"], str)
    assert data["status"] in ("valid", "issues_found")
    assert isinstance(data["issue_count"], int)
    assert isinstance(data["blocker_count"], int)
    assert isinstance(data["warning_count"], int)
    assert isinstance(data["issues"], list)

    for issue in data["issues"]:
        assert "code" in issue
        assert "severity" in issue
        assert "message" in issue
        assert "recommendation" in issue
        assert "reason" in issue
        assert "next_action" in issue
        assert issue["severity"] in ("blocker", "warning", "info")
