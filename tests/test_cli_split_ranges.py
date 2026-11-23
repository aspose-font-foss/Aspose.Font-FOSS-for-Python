"""Tests for --split-ranges flag in WebFontOptimizer CLI (FONT-402)."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from aspose_font import FontLoader

ROBOTO = str(Path(__file__).resolve().parents[1] / "testdata" / "Roboto-VariableFont_wdth,wght.ttf")
CLI = [sys.executable, "-m", "aspose_font.cli"]


def run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        CLI + list(args),
        capture_output=True,
        text=True,
    )


def test_split_ranges_flag_requires_variable_font(tmp_path: Path):
    out_dir = tmp_path / "split-static"
    result = run(
        "web-optimize",
        "testdata/OpenSans-Regular.cff",
        str(out_dir),
        "--split-ranges",
        "latin:U+0000-00FF",
    )
    assert result.returncode != 0
    assert "variable font" in result.stderr.lower() or "requires" in result.stderr.lower()


def test_split_ranges_requires_preserve_variable(tmp_path: Path):
    out_dir = tmp_path / "split-no-preserve"
    result = run(
        "web-optimize",
        ROBOTO,
        str(out_dir),
        "--split-ranges",
        "latin:U+0000-00FF",
    )
    assert result.returncode != 0
    assert "preserve-variable" in result.stderr.lower()


def test_split_ranges_generates_chunked_packages(tmp_path: Path):
    out_dir = tmp_path / "split-ranges"
    result = run(
        "web-optimize",
        ROBOTO,
        str(out_dir),
        "--split-ranges",
        "latin:U+0000-00FF",
        "--preserve-variable",
        "--no-woff",
    )
    assert result.returncode == 0

    latin_dir = out_dir / "latin"
    assert latin_dir.exists()
    assert (latin_dir / "roboto-regular-latin-0000-00ff.woff2").exists()
    assert (latin_dir / "fonts.css").exists()
    assert (latin_dir / "specimen.html").exists()
    assert (latin_dir / "optimizer-manifest.json").exists()

    composite_css = out_dir / "fonts.css"
    assert composite_css.exists()
    css_content = composite_css.read_text(encoding="utf-8")
    assert "U+0000-00FF" in css_content
    assert "@font-face" in css_content

    manifest = json.loads((out_dir / "optimizer-manifest.json").read_text(encoding="utf-8"))
    assert manifest["kind"] == "web_optimizer_package"
    assert "chunks" in manifest
    assert len(manifest["chunks"]) == 1
    assert manifest["chunks"][0]["range_name"] == "latin"
    assert manifest["chunks"][0]["unicode_range"] == "U+0000-00FF"
    assert manifest["composite_css"] == "fonts.css"


def test_split_ranges_multiple_ranges(tmp_path: Path):
    out_dir = tmp_path / "multi-range"
    result = run(
        "web-optimize",
        ROBOTO,
        str(out_dir),
        "--split-ranges",
        "latin:U+0000-00FF",
        "--split-ranges",
        "cyrillic:U+0400-04FF",
        "--preserve-variable",
        "--no-woff",
    )
    assert result.returncode == 0

    assert (out_dir / "latin").exists()
    assert (out_dir / "cyrillic").exists()

    manifest = json.loads((out_dir / "optimizer-manifest.json").read_text(encoding="utf-8"))
    assert len(manifest["chunks"]) == 2
    assert manifest["chunks"][0]["range_name"] == "latin"
    assert manifest["chunks"][1]["range_name"] == "cyrillic"

    # Check that files list includes the woff2 file
    assert any("woff2" in f for f in manifest["chunks"][0].get("files", []))

    css = (out_dir / "fonts.css").read_text(encoding="utf-8")
    assert "U+0000-00FF" in css
    assert "U+0400-04FF" in css


def test_split_ranges_mutually_exclusive_with_instance(tmp_path: Path):
    out_dir = tmp_path / "conflict"
    result = run(
        "web-optimize",
        ROBOTO,
        str(out_dir),
        "--split-ranges",
        "latin:U+0000-00FF",
        "--instance",
        "wght=400",
        "--preserve-variable",
    )
    assert result.returncode != 0
    assert "cannot be combined" in result.stderr.lower() or "mutually exclusive" in result.stderr.lower()


def test_split_ranges_mutually_exclusive_with_instance_name(tmp_path: Path):
    out_dir = tmp_path / "conflict-name"
    result = run(
        "web-optimize",
        ROBOTO,
        str(out_dir),
        "--split-ranges",
        "latin:U+0000-00FF",
        "--instance-name",
        "Regular",
        "--preserve-variable",
    )
    assert result.returncode != 0
    assert "cannot be combined" in result.stderr.lower() or "mutually exclusive" in result.stderr.lower()


def test_split_ranges_preserves_variable_tables(tmp_path: Path):
    out_dir = tmp_path / "preserve-fvar"
    result = run(
        "web-optimize",
        ROBOTO,
        str(out_dir),
        "--split-ranges",
        "latin:U+0000-00FF",
        "--preserve-variable",
        "--no-woff",
    )
    assert result.returncode == 0

    woff2_path = out_dir / "latin" / "roboto-regular-latin-0000-00ff.woff2"
    assert woff2_path.exists()

    from aspose_font import Woff2Font
    loaded = FontLoader.open(str(woff2_path))
    assert isinstance(loaded, Woff2Font)
    assert loaded._inner.is_variable


def test_split_ranges_format_validation(tmp_path: Path):
    out_dir = tmp_path / "format-error"
    result = run(
        "web-optimize",
        ROBOTO,
        str(out_dir),
        "--split-ranges",
        "invalid-range",
        "--preserve-variable",
    )
    assert result.returncode != 0
    assert "format must be" in result.stderr.lower() or "NAME:START-END" in result.stderr


def test_split_ranges_hex_ranges(tmp_path: Path):
    out_dir = tmp_path / "hex-ranges"
    result = run(
        "web-optimize",
        ROBOTO,
        str(out_dir),
        "--split-ranges",
        "latin:0x0000-0x00FF",
        "--preserve-variable",
        "--no-woff",
    )
    assert result.returncode == 0


def test_split_ranges_decimal_ranges(tmp_path: Path):
    out_dir = tmp_path / "decimal-ranges"
    result = run(
        "web-optimize",
        ROBOTO,
        str(out_dir),
        "--split-ranges",
        "latin:0-255",
        "--preserve-variable",
        "--no-woff",
    )
    assert result.returncode == 0
