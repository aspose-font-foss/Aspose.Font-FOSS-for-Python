"""Tests for composite @font-face CSS generation for chunked variable web fonts (FONT-401)."""

from pathlib import Path

from aspose_font import TtfFont, WebFontOptimizer


def test_build_composite_css_returns_valid_css_with_multiple_at_font_face(roboto: TtfFont):
    """Test that build_composite_css outputs valid CSS with correct @font-face count."""
    chunks = {
        "latin": Path("roboto-latin.woff2"),
        "latin-ext": Path("roboto-latin-ext.woff2"),
    }
    css = WebFontOptimizer.build_composite_css(
        font_family="Roboto",
        chunks=chunks,
        font=roboto,
    )

    assert css.count("@font-face") == 2
    assert "font-family: 'Roboto';" in css
    assert "font-display: swap;" in css


def test_build_composite_css_shares_family_name_across_chunks(roboto: TtfFont):
    """Test that all @font-face blocks share the supplied font-family."""
    chunks = {
        "latin": Path("roboto-latin.woff2"),
        "latin-ext": Path("roboto-latin-ext.woff2"),
    }
    css = WebFontOptimizer.build_composite_css(
        font_family="Roboto",
        chunks=chunks,
        font=roboto,
    )

    family_lines = [line for line in css.splitlines() if "font-family:" in line]
    assert all("'Roboto'" in line for line in family_lines)


def test_build_composite_css_includes_unicode_range_per_chunk(roboto: TtfFont):
    """Test that each @font-face block includes correct unicode-range."""
    coverage_dict = {
        "groups": [
            {"kind": "preset", "label": "latin", "coverage": "U+0000-00FF"},
            {"kind": "preset", "label": "latin-ext", "coverage": "U+0100-024F, U+1E00-1EFF"},
        ]
    }
    chunks = {
        "latin": Path("roboto-latin.woff2"),
        "latin-ext": Path("roboto-latin-ext.woff2"),
    }
    css = WebFontOptimizer.build_composite_css(
        font_family="Roboto",
        chunks=chunks,
        font=roboto,
        coverage_dict=coverage_dict,
    )

    assert "U+0000-00FF" in css
    assert "U+0100-024F" in css


def test_build_composite_css_extracts_axis_ranges_from_fvar(roboto: TtfFont):
    """Test that font-weight, font-stretch, font-style are extracted from fvar."""
    chunks = {
        "latin": Path("roboto-latin.woff2"),
    }
    css = WebFontOptimizer.build_composite_css(
        font_family="Roboto",
        chunks=chunks,
        font=roboto,
    )

    assert "font-weight:" in css
    assert "font-stretch:" in css
    assert "font-style:" in css


def test_build_composite_css_raises_for_empty_chunks():
    """Test that empty chunks dict raises ValueError."""
    import pytest

    with pytest.raises(ValueError, match="chunks must contain at least one entry"):
        WebFontOptimizer.build_composite_css(
            font_family="Roboto",
            chunks={},
        )


def test_build_composite_css_raises_for_invalid_family_type():
    """Test that non-string font_family raises TypeError."""
    import pytest

    with pytest.raises(TypeError):
        WebFontOptimizer.build_composite_css(
            font_family=123,
            chunks={"latin": Path("roboto-latin.woff2")},
        )


def test_build_composite_css_uses_filename_from_path_mapping():
    """Test that chunk filenames are correctly referenced in src descriptors."""
    chunks = {
        "latin": Path("chunks/roboto-latin.woff2"),
        "extended": Path("chunks/roboto-extended.woff2"),
    }
    css = WebFontOptimizer.build_composite_css(
        font_family="Roboto",
        chunks=chunks,
    )

    assert "url('./chunks/roboto-latin.woff2')" in css
    assert "url('./chunks/roboto-extended.woff2')" in css


def test_build_composite_css_with_string_paths(roboto: TtfFont):
    """Test that string paths are accepted alongside Path objects."""
    chunks = {
        "latin": "roboto-latin.woff2",
        "latin-ext": "roboto-latin-ext.woff2",
    }
    css = WebFontOptimizer.build_composite_css(
        font_family="Roboto",
        chunks=chunks,
        font=roboto,
    )

    assert "url('./roboto-latin.woff2')" in css
    assert "url('./roboto-latin-ext.woff2')" in css
