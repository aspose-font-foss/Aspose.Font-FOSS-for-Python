"""Tests for woff2-meta CLI command (FONT-493)."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from aspose_font import FontLoader, WebFontOptimizer

CLI = [sys.executable, "-m", "aspose_font.cli"]


def run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        CLI + list(args),
        capture_output=True,
        text=True,
    )


def test_woff2_meta_command_prints_summary(tmp_path: Path) -> None:
    """Test that woff2-meta prints metadata summary for WOFF2 font with metadata."""
    font = FontLoader.open(str(Path("testdata/Fonts/Roboto-Regular.ttf")))
    package = WebFontOptimizer.build(
        font,
        include_woff=False,
        metadata_vendor_name="Google",
        metadata_vendor_url="https://google.com",
        metadata_copyright="Copyright 2011 Google Inc.",
        metadata_description="Roboto font",
        metadata_license_url="https://google.com/license",
    )

    woff2_asset = next(
        a for a in package.bundle.font_assets
        if a.filename.endswith(".woff2")
    )
    font_path = tmp_path / "test.woff2"
    font_path.write_bytes(woff2_asset.data)

    result = run("woff2-meta", str(font_path))
    assert result.returncode == 0
    out = result.stdout
    assert "WOFF2 extended metadata:" in out
    assert "vendor" in out.lower() or "Google" in out
    assert "copyright" in out.lower() or "Copyright" in out


def test_woff2_meta_accepts_json_output(tmp_path: Path) -> None:
    """Test that --json writes valid JSON report for WOFF2 font with metadata."""
    font = FontLoader.open(str(Path("testdata/Fonts/Roboto-Regular.ttf")))
    package = WebFontOptimizer.build(
        font,
        include_woff=False,
        metadata_vendor_name="Aspose",
        metadata_vendor_url="https://aspose.com",
    )

    woff2_asset = next(
        a for a in package.bundle.font_assets
        if a.filename.endswith(".woff2")
    )
    font_path = tmp_path / "test.woff2"
    font_path.write_bytes(woff2_asset.data)
    json_path = tmp_path / "metadata.json"

    result = run("woff2-meta", str(font_path), "--json", str(json_path))
    assert result.returncode == 0
    assert json_path.exists()
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)
    assert "version" in data
    assert data["version"] == "1.0"
    assert "metadata_blocks" in data
    blocks = data["metadata_blocks"]
    assert isinstance(blocks, dict)


def test_woff2_meta_writes_xml_dump(tmp_path: Path) -> None:
    """Test that --dump-xml writes raw XML metadata to file."""
    font = FontLoader.open(str(Path("testdata/Fonts/Roboto-Regular.ttf")))
    package = WebFontOptimizer.build(
        font,
        include_woff=False,
        metadata_vendor_name="Test",
    )

    woff2_asset = next(
        a for a in package.bundle.font_assets
        if a.filename.endswith(".woff2")
    )
    font_path = tmp_path / "test.woff2"
    font_path.write_bytes(woff2_asset.data)
    xml_path = tmp_path / "metadata.xml"

    result = run("woff2-meta", str(font_path), "--dump-xml", str(xml_path))
    assert result.returncode == 0
    assert xml_path.exists()
    xml_content = xml_path.read_text(encoding="utf-8")
    assert "<?xml" in xml_content or "<metadata" in xml_content
    assert "Test" in xml_content


def test_woff2_meta_font_without_metadata_exits_0(tmp_path: Path) -> None:
    """Test that fonts without metadata print notice and exit 0."""
    font = FontLoader.open(str(Path("testdata/Fonts/Roboto-Regular.ttf")))
    package = WebFontOptimizer.build(
        font,
        include_woff=False,
        metadata_vendor_name=None,
        metadata_vendor_url=None,
        metadata_copyright=None,
        metadata_description=None,
        metadata_license_url=None,
        metadata_credits=None,
    )

    woff2_asset = next(
        a for a in package.bundle.font_assets
        if a.filename.endswith(".woff2")
    )
    font_path = tmp_path / "test-no-meta.woff2"
    font_path.write_bytes(woff2_asset.data)

    result = run("woff2-meta", str(font_path))
    assert result.returncode == 0
    out = result.stdout
    assert "WOFF2 extended metadata:" in out


def test_woff2_meta_non_woff2_font_exits_with_error() -> None:
    """Test that non-WOFF2 fonts produce error."""
    ttf_path = Path("testdata/Fonts/Roboto-Regular.ttf")
    result = run("woff2-meta", str(ttf_path))
    assert result.returncode != 0
    combined_output = result.stdout + result.stderr
    assert "WOFF2 font required" in combined_output


def test_woff2_meta_json_output_structure(tmp_path: Path) -> None:
    """Test that JSON output has expected structure with vendor, license, credits."""
    font = FontLoader.open(str(Path("testdata/Fonts/Roboto-Regular.ttf")))
    credits_list = [
        {"name": "John Doe", "url": "https://designer.example.com", "role": "designer"},
    ]
    package = WebFontOptimizer.build(
        font,
        include_woff=False,
        metadata_vendor_name="Test Vendor",
        metadata_vendor_url="https://vendor.example.com",
        metadata_license_url="https://example.com/license",
        metadata_copyright="Copyright 2024",
        metadata_description="Test font",
        metadata_credits=credits_list,
    )

    woff2_asset = next(
        a for a in package.bundle.font_assets
        if a.filename.endswith(".woff2")
    )
    font_path = tmp_path / "test.woff2"
    font_path.write_bytes(woff2_asset.data)
    json_path = tmp_path / "metadata.json"

    result = run("woff2-meta", str(font_path), "--json", str(json_path))
    assert result.returncode == 0
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)

    blocks = data["metadata_blocks"]
    assert isinstance(blocks["vendor"], dict)
    assert "name" in blocks["vendor"]
    assert "url" in blocks["vendor"]
    assert isinstance(blocks["license"], dict)
    assert "url" in blocks["license"]
    assert "paragraph" in blocks["license"]
    assert isinstance(blocks["credits"], list)


def test_woff2_meta_json_output_contains_expected_values(tmp_path: Path) -> None:
    """Test that JSON output contains the actual metadata values."""
    font = FontLoader.open(str(Path("testdata/Fonts/Roboto-Regular.ttf")))
    package = WebFontOptimizer.build(
        font,
        include_woff=False,
        metadata_vendor_name=" Aspose ",
        metadata_vendor_url="https://aspose.com",
        metadata_license_url="https://aspose.com/license",
        metadata_copyright="Copyright © Aspose",
        metadata_description="Test font for woff2-meta",
    )

    woff2_asset = next(
        a for a in package.bundle.font_assets
        if a.filename.endswith(".woff2")
    )
    font_path = tmp_path / "test.woff2"
    font_path.write_bytes(woff2_asset.data)
    json_path = tmp_path / "metadata.json"

    result = run("woff2-meta", str(font_path), "--json", str(json_path))
    assert result.returncode == 0
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)

    blocks = data["metadata_blocks"]
    assert blocks["vendor"]["name"] == "Aspose"
    assert blocks["vendor"]["url"] == "https://aspose.com"
    assert blocks["license"]["url"] == "https://aspose.com/license"
    assert blocks["copyright"] == "Copyright © Aspose"
    assert blocks["description"] == "Test font for woff2-meta"


def test_woff2_meta_validate_flag_passes_valid_metadata(tmp_path: Path) -> None:
    """Test --validate-metadata exits 0 when metadata passes validation."""
    font = FontLoader.open(str(Path("testdata/Fonts/Roboto-Regular.ttf")))
    package = WebFontOptimizer.build(
        font,
        include_woff=False,
        metadata_vendor_name="Valid Vendor",
        metadata_vendor_url="https://vendor.example.com",
        metadata_copyright="Copyright 2024",
        metadata_description="Test font",
        metadata_license_url="https://example.com/license",
    )

    woff2_asset = next(
        a for a in package.bundle.font_assets
        if a.filename.endswith(".woff2")
    )
    font_path = tmp_path / "test-valid.woff2"
    font_path.write_bytes(woff2_asset.data)

    result = run("woff2-meta", str(font_path), "--validate-metadata")
    assert result.returncode == 0
    assert "validation failed" not in (result.stdout + result.stderr).lower()


def test_woff2_meta_validate_flag_rejects_invalid_vendor_url(tmp_path: Path) -> None:
    """Test --validate-metadata rejects fonts with invalid vendor URL."""
    font = FontLoader.open(str(Path("testdata/Fonts/Roboto-Regular.ttf")))
    package = WebFontOptimizer.build(
        font,
        include_woff=False,
        metadata_vendor_name="Valid Vendor",
        metadata_vendor_url="ftp://invalid-url",
        metadata_copyright="Copyright 2024",
    )

    woff2_asset = next(
        a for a in package.bundle.font_assets
        if a.filename.endswith(".woff2")
    )
    font_path = tmp_path / "test-invalid-url.woff2"
    font_path.write_bytes(woff2_asset.data)

    result = run("woff2-meta", str(font_path), "--validate-metadata")
    assert result.returncode != 0
    combined = result.stdout + result.stderr
    assert "validation failed" in combined.lower() or "url" in combined.lower()
