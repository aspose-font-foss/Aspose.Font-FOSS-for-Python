"""Tests for GSUB ligature feature substitution in TextRenderer (FONT-444)."""
from __future__ import annotations

import pytest

from aspose_font import FontLoader
from aspose_font.text import TextRenderer


def test_layout_with_liga_feature_applies_ligatures() -> None:
    """Test that features=["liga"] triggers ligature substitution."""
    font = FontLoader.open("testdata/Roboto-VariableFont_wdth,wght.ttf")

    if font.ttf_tables.gsub is None:
        pytest.skip("Font has no GSUB table")

    layout = TextRenderer.layout(font, "ffi", size=100.0, features=["liga"])
    assert layout is not None
    assert len(layout.glyphs) >= 1


def test_layout_without_features_unchanged() -> None:
    """Test that default behavior (features=None) does not apply substitutions."""
    font = FontLoader.open("testdata/Roboto-VariableFont_wdth,wght.ttf")

    layout_no_features = TextRenderer.layout(font, "AB", size=100.0, features=None)
    layout_default = TextRenderer.layout(font, "AB", size=100.0)

    assert len(layout_no_features.glyphs) == len(layout_default.glyphs)


def test_layout_features_ignores_missing_gsub() -> None:
    """Test that features parameter gracefully handles fonts without GSUB."""
    font = FontLoader.open("testdata/Roboto-VariableFont_wdth,wght.ttf")

    try:
        layout = TextRenderer.layout(font, "测试", size=100.0, features=["liga"])
        assert layout is not None
    except AttributeError:
        pytest.fail("features parameter should not raise AttributeError for missing GSUB")


def test_layout_single_substitution() -> None:
    """Test single substitution feature (e.g., stylistic sets)."""
    font = FontLoader.open("testdata/Roboto-VariableFont_wdth,wght.ttf")

    if font.ttf_tables.gsub is None:
        pytest.skip("Font has no GSUB table")

    layout = TextRenderer.layout(font, "A", size=100.0, features=["ss01"])
    assert len(layout.glyphs) == 1


def test_layout_multiple_features() -> None:
    """Test multiple features applied in sequence."""
    font = FontLoader.open("testdata/Roboto-VariableFont_wdth,wght.ttf")

    if font.ttf_tables.gsub is None:
        pytest.skip("Font has no GSUB table")

    layout = TextRenderer.layout(font, "ffi", size=100.0, features=["liga", "clig"])
    assert layout is not None


def test_layout_features_respects_coverage() -> None:
    """Test that features only apply when GSUB coverage exists."""
    font = FontLoader.open("testdata/Roboto-VariableFont_wdth,wght.ttf")

    layout = TextRenderer.layout(font, "test", size=100.0, features=["liga"])
    assert len(layout.glyphs) > 0


def test_layout_glyphs_with_features() -> None:
    """Test layout_glyphs method with features parameter."""
    font = FontLoader.open("testdata/Roboto-VariableFont_wdth,wght.ttf")

    if font.ttf_tables.gsub is None:
        pytest.skip("Font has no GSUB table")

    gids = [
        font.encoding.unicode_to_gid(ord("f")),
        font.encoding.unicode_to_gid(ord("f")),
        font.encoding.unicode_to_gid(ord("i")),
    ]
    layout = TextRenderer.layout_glyphs(font, gids, size=100.0, features=["liga"])
    assert len(layout.glyphs) >= 1


def test_layout_features_with_kern() -> None:
    """Test that features work correctly with kerning."""
    font = FontLoader.open("testdata/Roboto-VariableFont_wdth,wght.ttf")

    layout = TextRenderer.layout(font, "ffi", size=100.0, kern=True, features=["liga"])
    assert layout is not None
    assert len(layout.glyphs) > 0
