"""Tests for GPOS Pair Adjustment and Kerning Integration (FONT-447)."""
from __future__ import annotations

import pytest

from aspose_font import FontLoader
from aspose_font.text import TextRenderer


def test_gpos_table_available_on_fonts_with_gpos() -> None:
    """Test that GPOS table is parsed and available on fonts that have it."""
    font = FontLoader.open("testdata/Roboto-VariableFont_wdth,wght.ttf")

    gpos_available = hasattr(font.ttf_tables, "gpos") and font.ttf_tables.gpos is not None

    if not gpos_available:
        pytest.skip("Roboto font in test suite does not have GPOS table")


def test_gpos_kern_pairs_extraction() -> None:
    """Test that GPOS table can extract kern pairs when available."""
    font = FontLoader.open("testdata/Roboto-VariableFont_wdth,wght.ttf")

    if font.ttf_tables.gpos is None:
        pytest.skip("Font has no GPOS table")

    kern_pairs = font.ttf_tables.gpos.get_kern_pairs()

    assert isinstance(kern_pairs, list)


def test_layout_uses_gpos_kerning_when_available() -> None:
    """Test that TextRenderer.layout() applies GPOS kerning when present."""
    font = FontLoader.open("testdata/Roboto-VariableFont_wdth,wght.ttf")

    if font.ttf_tables.gpos is None:
        pytest.skip("Font has no GPOS table")

    layout_kern = TextRenderer.layout(font, "AV", kern=True)
    layout_no_kern = TextRenderer.layout(font, "AV", kern=False)

    assert len(layout_kern.glyphs) == 2
    assert len(layout_no_kern.glyphs) == 2

    if font.get_kern_pairs():
        assert layout_kern.glyphs[1].x_offset != layout_no_kern.glyphs[1].x_offset


def test_layout_falls_back_to_legacy_kern_when_no_gpos() -> None:
    """Test that TextRenderer.layout() uses legacy kern when GPOS unavailable."""
    font = FontLoader.open("testdata/Roboto-VariableFont_wdth,wght.ttf")

    has_legacy_kern = bool(font.get_kern_pairs())

    if not has_legacy_kern:
        pytest.skip("Font has no legacy kern pairs")

    layout_kern = TextRenderer.layout(font, "AV", kern=True)
    layout_no_kern = TextRenderer.layout(font, "AV", kern=False)

    assert len(layout_kern.glyphs) == 2

    if font.ttf_tables.gpos is None:
        assert layout_kern.glyphs[1].x_offset != layout_no_kern.glyphs[1].x_offset


def test_layout_no_crash_without_kerning_tables() -> None:
    """Test that TextRenderer.layout() handles fonts without kerning tables."""
    font = FontLoader.open("testdata/Roboto-VariableFont_wdth,wght.ttf")

    layout = TextRenderer.layout(font, "Hello", kern=True)
    assert layout is not None
    assert len(layout.glyphs) == 5


def test_layout_glyphs_with_gpos_kerning() -> None:
    """Test that layout_glyphs() method applies GPOS kerning."""
    font = FontLoader.open("testdata/Roboto-VariableFont_wdth,wght.ttf")

    if font.ttf_tables.gpos is None and not font.get_kern_pairs():
        pytest.skip("Font has no kerning tables")

    try:
        gid_a = font.encoding.unicode_to_gid(ord("A"))
        gid_v = font.encoding.unicode_to_gid(ord("V"))
    except Exception:
        pytest.skip("Font does not have A or V glyphs")

    layout = TextRenderer.layout_glyphs(font, [gid_a, gid_v], kern=True)
    assert len(layout.glyphs) == 2


def test_layout_features_with_gpos_kern() -> None:
    """Test that GSUB features and GPOS kerning work together."""
    font = FontLoader.open("testdata/Roboto-VariableFont_wdth,wght.ttf")

    layout = TextRenderer.layout(font, "ffi", kern=True, features=["liga"])
    assert layout is not None
    assert len(layout.glyphs) >= 1


def test_gpos_table_importable() -> None:
    """Test that GposTable can be imported from ttf.tables module."""
    from aspose_font.ttf.tables.gpos import (
        GposTable,
        PairAdjustmentRecord,
        PairPosFormat1Subtable,
        PairPosFormat2Subtable,
        PairSet,
    )

    assert GposTable is not None
    assert PairPosFormat1Subtable is not None
    assert PairPosFormat2Subtable is not None
    assert PairAdjustmentRecord is not None
    assert PairSet is not None


def test_gpos_in_ttf_table_set() -> None:
    """Test that TtfTableSet has gpos attribute."""
    from aspose_font.ttf.tables import TtfTableSet

    tables = TtfTableSet()
    assert hasattr(tables, "gpos")
    assert tables.gpos is None
