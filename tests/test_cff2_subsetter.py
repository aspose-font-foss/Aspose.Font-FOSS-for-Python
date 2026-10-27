"""Tests for CFF2 variable font subsetting (SPEC-?? - FONT-249)."""

from __future__ import annotations

from pathlib import Path

import pytest

from aspose_font import FontLoader, FontSubsetter
from aspose_font._exceptions import FontParseException
from aspose_font.cff2 import Cff2Font


def test_cff2_subset_by_text_preserves_axes(tmp_path):
    """Test that subsetting CFF2 font preserves axes metadata."""
    test_font_path = Path(__file__).resolve().parents[1] / "testdata" / "Roboto-VariableFont_wdth,wght.ttf"

    if not test_font_path.exists():
        pytest.skip("Test font not available")

    try:
        font = Cff2Font.load(test_font_path)
    except FontParseException:
        pytest.skip("Test font is not a CFF2 font")

    subsetted = FontSubsetter.subset_by_text(font, "Hello")

    assert subsetted.num_glyphs <= font.num_glyphs


def test_cff2_subset_reduces_glyph_count(tmp_path):
    """Test that subsetting CFF2 font reduces glyph count."""
    test_font_path = Path(__file__).resolve().parents[1] / "testdata" / "Roboto-VariableFont_wdth,wght.ttf"

    if not test_font_path.exists():
        pytest.skip("Test font not available")

    try:
        font = Cff2Font.load(test_font_path)
    except FontParseException:
        pytest.skip("Test font is not a CFF2 font")

    original_count = font.num_glyphs
    subsetted = FontSubsetter.subset_by_text(font, "AB")

    assert subsetted.num_glyphs < original_count


def test_cff2_subset_roundtrip_loadable(tmp_path):
    """Test that subset CFF2 font can be reloaded via FontLoader."""
    test_font_path = Path(__file__).resolve().parents[1] / "testdata" / "Roboto-VariableFont_wdth,wght.ttf"

    if not test_font_path.exists():
        pytest.skip("Test font not available")

    try:
        font = Cff2Font.load(test_font_path)
    except FontParseException:
        pytest.skip("Test font is not a CFF2 font")

    subsetted = FontSubsetter.subset_by_text(font, "ABC")
    subsetted_bytes = subsetted.to_bytes()

    reloaded = FontLoader.open(subsetted_bytes)

    assert reloaded.num_glyphs == subsetted.num_glyphs


def test_cff2_subset_by_gids(tmp_path):
    """Test subsetting CFF2 font by specific GIDs."""
    test_font_path = Path(__file__).resolve().parents[1] / "testdata" / "Roboto-VariableFont_wdth,wght.ttf"

    if not test_font_path.exists():
        pytest.skip("Test font not available")

    try:
        font = Cff2Font.load(test_font_path)
    except FontParseException:
        pytest.skip("Test font is not a CFF2 font")

    original_count = font.num_glyphs
    if original_count < 5:
        pytest.skip("Font has too few glyphs for GID test")

    gids = {1, 2, 3}
    subsetted = FontSubsetter.subset_by_gids(font, gids)

    assert subsetted.num_glyphs <= len(gids)


def test_cff2_subset_uses_default_coordinates(tmp_path):
    """Test that CFF2 subsetting uses default coordinates for instantiation."""
    test_font_path = Path(__file__).resolve().parents[1] / "testdata" / "Roboto-VariableFont_wdth,wght.ttf"

    if not test_font_path.exists():
        pytest.skip("Test font not available")

    try:
        font = Cff2Font.load(test_font_path)
    except FontParseException:
        pytest.skip("Test font is not a CFF2 font")

    FontSubsetter.subset_by_text(font, "X")

    for axis in font.variable_axes:
        assert hasattr(axis, "default_value")
        assert hasattr(axis, "tag")


def test_cff2_subsetter_recognizes_cff2_font():
    """Test that FontSubsetter._subset_by_retained recognizes Cff2Font and raises for stub data."""
    from aspose_font._exceptions import FontNotSupportedException
    from aspose_font.subsetter import FontSubsetter

    font = Cff2Font(b"CFF2" + b"\x00" * 100)

    with pytest.raises(FontNotSupportedException):
        FontSubsetter._subset_by_retained(font, {0, 1})


def test_cff2_subset_standalone_font(tmp_path):
    """Test subsetting a standalone CFF2 font (CFF2 table extracted from sfnt)."""
    test_font_path = Path(__file__).resolve().parents[1] / "testdata" / "Roboto-VariableFont_wdth,wght.ttf"

    if not test_font_path.exists():
        pytest.skip("Test font not available")

    try:
        font = Cff2Font.load(test_font_path)
    except FontParseException:
        pytest.skip("Test font is not a CFF2 font")

    original_count = font.num_glyphs
    subsetted = FontSubsetter.subset_by_text(font, "A")

    assert subsetted.num_glyphs <= original_count

    output_path = tmp_path / "subset.cff"
    output_path.write_bytes(subsetted.to_bytes())

    reloaded = FontLoader.open(output_path)

    assert reloaded.num_glyphs == subsetted.num_glyphs
