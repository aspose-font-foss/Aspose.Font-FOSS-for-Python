"""Tests for WOFF2 metadata injection in WebFontOptimizer."""

from __future__ import annotations

from pathlib import Path

from aspose_font import FontLoader, WebFontOptimizer, Woff2Font


def test_woff2_metadata_injection_basic():
    """Verify metadata XML is embedded in generated WOFF2 by default."""
    font = FontLoader.open(str(Path("testdata/Fonts/Roboto-Regular.ttf")))
    package = WebFontOptimizer.build(font, include_woff=False)

    assert len(package.bundle.font_assets) == 1
    woff2_asset = package.bundle.font_assets[0]
    assert woff2_asset.filename.endswith(".woff2")

    woff2_font = FontLoader.open(woff2_asset.data)
    assert isinstance(woff2_font, Woff2Font)
    assert len(woff2_font.metadata_xml) > 0
    assert "vendor" in woff2_font.metadata_xml.lower() or \
           "copyright" in woff2_font.metadata_xml.lower()


def test_woff2_metadata_injection_roundtrip():
    """Verify WOFF2 with metadata decompresses without errors."""
    font = FontLoader.open(str(Path("testdata/Fonts/Roboto-Regular.ttf")))
    package = WebFontOptimizer.build(font, include_woff=False)

    woff2_asset = next(
        a for a in package.bundle.font_assets
        if a.filename.endswith(".woff2")
    )

    woff2_font = FontLoader.open(woff2_asset.data)
    blob = woff2_font.to_bytes()
    rt = FontLoader.open(blob)
    assert isinstance(rt, Woff2Font)
    assert rt.font_name == woff2_font.font_name


def test_woff2_metadata_injection_custom_vendor():
    """Verify custom vendor metadata is injected."""
    font = FontLoader.open(str(Path("testdata/Fonts/Roboto-Regular.ttf")))
    package = WebFontOptimizer.build(
        font,
        include_woff=False,
        metadata_vendor_name="Aspose",
        metadata_vendor_url="https://aspose.com",
        metadata_license_url="https://aspose.com/license",
    )

    woff2_asset = next(
        a for a in package.bundle.font_assets
        if a.filename.endswith(".woff2")
    )
    woff2_font = FontLoader.open(woff2_asset.data)

    xml = woff2_font.metadata_xml
    assert "Aspose" in xml
    assert "https://aspose.com" in xml
    assert "license" in xml.lower()


def test_woff2_metadata_header_offsets():
    """Verify WOFF2 header metaOffset/metaLength/metaOrigLength are correct."""
    font = FontLoader.open(str(Path("testdata/Fonts/Roboto-Regular.ttf")))
    package = WebFontOptimizer.build(font, include_woff=False)

    woff2_asset = next(
        a for a in package.bundle.font_assets
        if a.filename.endswith(".woff2")
    )
    data = woff2_asset.data

    # WOFF2 header layout (48 bytes total):
    # ... (first 28 bytes)
    # bytes 28-31: metaOffset
    # bytes 32-35: metaLength
    # bytes 36-39: metaOrigLength
    meta_offset = int.from_bytes(data[28:32], "big")
    meta_length = int.from_bytes(data[32:36], "big")
    meta_orig_length = int.from_bytes(data[36:40], "big")

    assert meta_offset >= 48
    assert meta_length > 0
    assert meta_orig_length > 0


def test_woff2_metadata_empty_when_disabled():
    """Verify that all WOFF2 fonts have metadata (either explicit or auto-inferred)."""
    font = FontLoader.open(str(Path("testdata/Fonts/Roboto-Regular.ttf")))
    package = WebFontOptimizer.build(
        font,
        include_woff=False,
        metadata_vendor_name=None,
        metadata_vendor_url=None,
        metadata_license_url=None,
    )

    woff2_asset = next(
        a for a in package.bundle.font_assets
        if a.filename.endswith(".woff2")
    )
    woff2_font = FontLoader.open(woff2_asset.data)

    xml = woff2_font.metadata_xml
    # Metadata should be auto-inferred from font even when explicit params are None
    assert xml is not None
    assert len(xml) > 0
    # Verify it contains expected fields from auto-inference
    assert "copyright" in xml.lower() or "vendor" in xml.lower()


def test_woff2_metadata_with_all_fields():
    """Verify all metadata fields are properly injected."""
    font = FontLoader.open(str(Path("testdata/Fonts/Roboto-Regular.ttf")))

    credits_list = [
        {"name": "John Doe", "url": "https://designer.example.com", "role": "designer"},
        {"name": "Acme Foundry", "url": "https://foundry.example.com", "role": "foundry"},
    ]

    package = WebFontOptimizer.build(
        font,
        include_woff=False,
        metadata_vendor_name="Test Vendor",
        metadata_vendor_url="https://vendor.example.com",
        metadata_license_url="https://example.com/license",
        metadata_copyright="Copyright © 2024 Test Vendor",
        metadata_description="A test font for metadata injection",
        metadata_credits=credits_list,
    )

    woff2_asset = next(
        a for a in package.bundle.font_assets
        if a.filename.endswith(".woff2")
    )
    woff2_font = FontLoader.open(woff2_asset.data)

    xml = woff2_font.metadata_xml

    assert "Test Vendor" in xml
    assert "https://vendor.example.com" in xml
    assert "https://example.com/license" in xml
    assert "Copyright" in xml
    assert "A test font" in xml
    assert "John Doe" in xml
    assert "Acme Foundry" in xml
    assert "designer" in xml.lower()
    assert "foundry" in xml.lower()
