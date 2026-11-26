"""Tests for meta-info CLI command (FONT-519)."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from aspose_font._io import BinaryWriter

CLI = [sys.executable, "-m", "aspose_font.cli"]


def run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        CLI + list(args),
        capture_output=True,
        text=True,
    )


def _build_meta_bytes(data_maps: dict[str, bytes]) -> bytes:
    """Build binary meta table from data_maps dict."""
    bw = BinaryWriter()
    bw.write_u32(1)
    bw.write_u32(0)
    bw.write_u32(0)
    bw.write_u32(len(data_maps))

    tag_offset = 16 + len(data_maps) * 12
    current_offset = tag_offset

    for tag, data in data_maps.items():
        bw.write_bytes(tag.encode("ascii").ljust(4, b"\x00"))
        bw.write_u32(current_offset)
        bw.write_u32(len(data))
        current_offset += len(data)

    for tag, data in data_maps.items():
        bw.write_bytes(data)

    return bw.to_bytes()


def create_font_with_meta(tmp_path: Path, meta_bytes: bytes) -> Path:
    """Create minimal TTF with meta table."""
    head = bytes(12) + (0x5F0F3CF5).to_bytes(4, "big") + bytes(54 - 16)
    maxp = (0x00010000).to_bytes(4, "big") + (1).to_bytes(2, "big") + bytes(26)

    num_tables = 3
    offset_table = (
        b"\x00\x01\x00\x00"
        + num_tables.to_bytes(2, "big")
        + (0).to_bytes(2, "big")
        + (0).to_bytes(2, "big")
        + (0).to_bytes(2, "big")
    )

    head_offset = 12 + num_tables * 16
    maxp_offset = head_offset + len(head)
    meta_offset = maxp_offset + len(maxp)

    directory = b""
    directory += b"head" + (0).to_bytes(4, "big") + head_offset.to_bytes(4, "big") + len(head).to_bytes(4, "big")
    directory += b"maxp" + (0).to_bytes(4, "big") + maxp_offset.to_bytes(4, "big") + len(maxp).to_bytes(4, "big")
    directory += b"meta" + (0).to_bytes(4, "big") + meta_offset.to_bytes(4, "big") + len(meta_bytes).to_bytes(4, "big")

    minimal_ttf = offset_table + directory + head + maxp + meta_bytes
    font_path = tmp_path / "meta-font.ttf"
    font_path.write_bytes(minimal_ttf)
    return font_path


def test_meta_info_command_prints_summary_with_dlng_slng(tmp_path: Path) -> None:
    """Test that meta-info prints summary for font with dlng and slng."""
    meta = _build_meta_bytes({
        "dlng": b"Latn,Cyrl",
        "slng": b"Latn,Cyrl,Grek",
    })
    font_path = create_font_with_meta(tmp_path, meta)
    result = run("meta-info", str(font_path))
    assert result.returncode == 0
    out = result.stdout
    assert "meta table inspection" in out
    assert "Design languages:" in out
    assert "Supported languages:" in out
    assert "Latn" in out
    assert "Cyrl" in out
    assert "Grek" in out


def test_meta_info_command_accepts_json_flag(tmp_path: Path) -> None:
    """Test that --json writes valid JSON report."""
    meta = _build_meta_bytes({
        "dlng": b"Latn",
        "slng": b"Latn,Cyrl",
    })
    font_path = create_font_with_meta(tmp_path, meta)
    json_path = tmp_path / "meta-info.json"
    result = run("meta-info", str(font_path), "--json", str(json_path))
    assert result.returncode == 0
    assert json_path.exists()
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)
    assert "tags" in data
    assert "design_languages" in data
    assert "supported_languages" in data
    assert "sizes" in data
    assert data["tags"] == ["dlng", "slng"]
    assert data["design_languages"] == ["Latn"]
    assert data["supported_languages"] == ["Latn", "Cyrl"]
    assert data["sizes"]["dlng"] == 4
    assert data["sizes"]["slng"] == 9


def test_meta_info_command_handles_missing_meta_table_exits_0(tmp_path: Path) -> None:
    """Test that fonts without meta table print notice and exit 0."""
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
    font_path = tmp_path / "no-meta-font.ttf"
    font_path.write_bytes(minimal_ttf)

    result = run("meta-info", str(font_path))
    assert result.returncode == 0
    assert "No meta table present." in result.stdout
    assert "Note:" in result.stdout


def test_meta_info_command_non_ttf_font_exits_error() -> None:
    """Test that non-TTF fonts produce error."""
    pfb_path = str(Path(__file__).resolve().parents[1] / "testdata" / "OpenSans-Regular.pfb")
    result = run("meta-info", pfb_path)
    assert result.returncode != 0
    combined_output = result.stdout + result.stderr
    assert "meta-info inspection is only supported" in combined_output


def test_meta_info_command_shows_other_tags(tmp_path: Path) -> None:
    """Test that meta-info shows other metadata tags (appl, bild, custom)."""
    appl_data = b"\x00\x01\x02\x03"
    custom_data = b"custom vendor data"
    meta = _build_meta_bytes({
        "appl": appl_data,
        "bild": b"\x04\x05\x06\x07",
        "VAND": custom_data,
    })
    font_path = create_font_with_meta(tmp_path, meta)
    result = run("meta-info", str(font_path))
    assert result.returncode == 0
    out = result.stdout
    assert "appl (4 bytes)" in out
    assert "bild (4 bytes)" in out
    assert "VAND (18 bytes)" in out


def test_meta_info_command_with_symbolic_font() -> None:
    """Test meta-info with existing Roboto fixture that has meta table."""
    font_path = str(Path(__file__).resolve().parents[1] / "testdata" / "TTF" / "SymbolicFonts" / "symbol.ttf")
    result = run("meta-info", font_path)
    assert result.returncode == 0
    out = result.stdout
    assert ("meta table inspection" in out or "No meta table present." in out)


def test_meta_info_json_output_structure(tmp_path: Path) -> None:
    """Test that JSON output has complete expected structure."""
    meta = _build_meta_bytes({
        "dlng": b"Latn",
        "slng": b"Latn",
    })
    font_path = create_font_with_meta(tmp_path, meta)
    json_path = tmp_path / "meta-info.json"
    result = run("meta-info", str(font_path), "--json", str(json_path))
    assert result.returncode == 0
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)
    assert isinstance(data["tags"], list)
    assert isinstance(data["design_languages"], list)
    assert isinstance(data["supported_languages"], list)
    assert isinstance(data["sizes"], dict)
    assert isinstance(data["version"], str)
    assert data["version"] == "1.0"
    assert isinstance(data["flags"], int)
