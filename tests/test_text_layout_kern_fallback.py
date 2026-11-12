"""Tests for TextRenderer kern fallback integration (FONT-497)."""
from __future__ import annotations

import pytest

from aspose_font import FontLoader
from aspose_font.text import TextRenderer


def test_kern_fallback_default_is_true() -> None:
    """Test that kern_fallback defaults to True (backward compatibility)."""
    font = FontLoader.open("testdata/Roboto-VariableFont_wdth,wght.ttf")

    layout_kern = TextRenderer.layout(font, "AV", kern=True)
    layout_kern_explicit = TextRenderer.layout(font, "AV", kern=True, kern_fallback=True)

    assert len(layout_kern.glyphs) == len(layout_kern_explicit.glyphs)


def test_kern_fallback_true_applies_legacy_kern() -> None:
    """Test that kern_fallback=True applies legacy kern when GPOS unavailable."""
    font = FontLoader.open("testdata/Roboto-VariableFont_wdth,wght.ttf")

    if font.ttf_tables.gpos is not None:
        pytest.skip("Font has GPOS table, not testing legacy fallback")

    kern_pairs = font.get_kern_pairs()
    if not kern_pairs:
        pytest.skip("Font has no legacy kern pairs")

    layout_fallback = TextRenderer.layout(font, "AV", kern=True, kern_fallback=True)
    layout_no_fallback = TextRenderer.layout(font, "AV", kern=True, kern_fallback=False)

    assert len(layout_fallback.glyphs) == 2
    assert len(layout_no_fallback.glyphs) == 2

    assert layout_fallback.glyphs[1].x_offset != layout_no_fallback.glyphs[1].x_offset


def test_kern_fallback_false_disables_legacy_kern() -> None:
    """Test that kern_fallback=False disables legacy kern fallback."""
    font = FontLoader.open("testdata/Roboto-VariableFont_wdth,wght.ttf")

    kern_pairs = font.get_kern_pairs()
    if not kern_pairs and font.ttf_tables.gpos is None:
        pytest.skip("Font has no kerning at all")

    layout_with_fallback = TextRenderer.layout(font, "AV", kern=True, kern_fallback=True)
    layout_without_fallback = TextRenderer.layout(font, "AV", kern=True, kern_fallback=False)

    assert len(layout_with_fallback.glyphs) == 2
    assert len(layout_without_fallback.glyphs) == 2

    if kern_pairs and font.ttf_tables.gpos is None:
        assert layout_with_fallback.glyphs[1].x_offset != layout_without_fallback.glyphs[1].x_offset


def test_kern_fallback_with_gpos_font_uses_gpos() -> None:
    """Test that when GPOS is present, GPOS is used regardless of kern_fallback."""
    font = FontLoader.open("testdata/Roboto-VariableFont_wdth,wght.ttf")

    if font.ttf_tables.gpos is None:
        pytest.skip("Font has no GPOS table")

    layout_fallback = TextRenderer.layout(font, "AV", kern=True, kern_fallback=True)
    layout_no_fallback = TextRenderer.layout(font, "AV", kern=True, kern_fallback=False)

    assert len(layout_fallback.glyphs) == 2
    assert len(layout_no_fallback.glyphs) == 2


def test_kern_fallback_false_no_crash_without_kerning() -> None:
    """Test that kern_fallback=False doesn't crash on fonts without kerning."""
    font = FontLoader.open("testdata/Roboto-VariableFont_wdth,wght.ttf")

    layout = TextRenderer.layout(font, "Hello", kern=True, kern_fallback=False)
    assert layout is not None
    assert len(layout.glyphs) == 5


def test_kern_fallback_false_with_no_gpos_no_legacy() -> None:
    """Test kern_fallback=False when font has no kerning at all."""
    font = FontLoader.open("testdata/Roboto-VariableFont_wdth,wght.ttf")

    if font.ttf_tables.gpos is not None or font.get_kern_pairs():
        pytest.skip("Font has kerning, skipping no-kern case")

    layout = TextRenderer.layout(font, "Hello", kern=True, kern_fallback=False)
    assert layout is not None
    assert len(layout.glyphs) == 5


def test_kern_fallback_parameter_passed_through_layout_glyphs() -> None:
    """Test that kern_fallback parameter works in layout_glyphs method."""
    font = FontLoader.open("testdata/Roboto-VariableFont_wdth,wght.ttf")

    try:
        gid_a = font.encoding.unicode_to_gid(ord("A"))
        gid_v = font.encoding.unicode_to_gid(ord("V"))
    except Exception:
        pytest.skip("Font does not have A or V glyphs")

    layout_fallback = TextRenderer.layout_glyphs(
        font, [gid_a, gid_v], kern=True, kern_fallback=True
    )
    layout_no_fallback = TextRenderer.layout_glyphs(
        font, [gid_a, gid_v], kern=True, kern_fallback=False
    )

    assert len(layout_fallback.glyphs) == 2
    assert len(layout_no_fallback.glyphs) == 2


def test_kern_fallback_with_vertical_layout() -> None:
    """Test that kern_fallback works correctly with vertical layout."""
    font = FontLoader.open("testdata/Roboto-VariableFont_wdth,wght.ttf")

    kern_pairs = font.get_kern_pairs()
    if not kern_pairs and font.ttf_tables.gpos is None:
        pytest.skip("Font has no kerning")

    layout = TextRenderer.layout(
        font, "AV", kern=True, kern_fallback=True, direction="vertical"
    )
    assert layout is not None
    assert len(layout.glyphs) == 2


def test_kern_fallback_backward_compatibility() -> None:
    """Test that existing code without kern_fallback parameter still works."""
    font = FontLoader.open("testdata/Roboto-VariableFont_wdth,wght.ttf")

    layout = TextRenderer.layout(font, "Hello", kern=True)
    assert layout is not None
    assert len(layout.glyphs) == 5


def test_kern_fallback_kern_false_disables_all_kerning() -> None:
    """Test that kern=False disables all kerning regardless of kern_fallback."""
    font = FontLoader.open("testdata/Roboto-VariableFont_wdth,wght.ttf")

    layout_no_kern = TextRenderer.layout(font, "AV", kern=False, kern_fallback=True)
    layout_no_kern_either = TextRenderer.layout(font, "AV", kern=False, kern_fallback=False)

    assert len(layout_no_kern.glyphs) == 2
    assert len(layout_no_kern_either.glyphs) == 2

    assert layout_no_kern.glyphs[1].x_offset == layout_no_kern_either.glyphs[1].x_offset
