"""Tests for subset-preserving variable web export (FONT-292)."""

from pathlib import Path

from aspose_font import TtfFont, WebFontOptimizer


def test_web_optimizer_subset_preserving_variable_preserves_fvar(roboto: TtfFont, tmp_path: Path):
    """Subset a variable font with preserve_variable and verify fvar table is preserved."""
    original_num_glyphs = roboto.num_glyphs
    assert roboto.is_variable, "Roboto should be a variable font for this test"

    result = WebFontOptimizer.build(
        roboto,
        source_path=Path("testdata/Roboto-VariableFont_wdth,wght.ttf"),
        presets=("latin",),
        include_woff=False,
        preserve_variable=True,
    )

    subset_font = result.bundle.preview_font
    assert subset_font.num_glyphs < original_num_glyphs, (
        f"Subset should have fewer glyphs: {subset_font.num_glyphs} vs {original_num_glyphs}"
    )
    assert isinstance(subset_font, TtfFont)
    tables = subset_font.ttf_tables
    assert tables.fvar is not None, "fvar table should be preserved when preserve_variable=True"
    assert subset_font.is_variable, "Output should still be a variable font"


def test_web_optimizer_subset_preserving_variable_preserves_gvar(roboto: TtfFont):
    """Subset a variable font with preserve_variable and verify gvar table is preserved."""
    result = WebFontOptimizer.build(
        roboto,
        source_path=Path("testdata/Roboto-VariableFont_wdth,wght.ttf"),
        presets=("latin",),
        include_woff=False,
        preserve_variable=True,
    )

    subset_font = result.bundle.preview_font
    assert isinstance(subset_font, TtfFont)
    tables = subset_font.ttf_tables
    assert "gvar" in tables._raw, "gvar table should be preserved when preserve_variable=True"


def test_web_optimizer_subset_without_preserve_variable_is_static(roboto: TtfFont):
    """Verify default subsetting produces a static font."""
    result = WebFontOptimizer.build(
        roboto,
        source_path=Path("testdata/Roboto-VariableFont_wdth,wght.ttf"),
        presets=("latin",),
        include_woff=False,
    )

    subset_font = result.bundle.preview_font
    assert subset_font.num_glyphs < roboto.num_glyphs
    assert isinstance(subset_font, TtfFont)
    tables = subset_font.ttf_tables
    assert tables.fvar is None, "fvar table should be removed without preserve_variable"
    assert not subset_font.is_variable, "Output should be a static font"


def test_web_optimizer_builder_subset_preserving_variable(roboto: TtfFont):
    """Test WebFontBuilder with preserve_variable."""
    from aspose_font import WebFontBuilder

    result = WebFontBuilder.build(
        roboto,
        presets=("latin",),
        include_woff=False,
        preserve_variable=True,
    )

    subset_font = result.preview_font
    assert subset_font.num_glyphs < roboto.num_glyphs
    assert isinstance(subset_font, TtfFont)
    tables = subset_font.ttf_tables
    assert tables.fvar is not None, "fvar table should be preserved via WebFontBuilder"
    assert subset_font.is_variable
