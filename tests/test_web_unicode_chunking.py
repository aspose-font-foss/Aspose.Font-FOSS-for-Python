"""Tests for Unicode-range chunking for variable WOFF2 exports (FONT-400)."""

from pathlib import Path

from aspose_font import TtfFont, WebFontOptimizer, WebFontOptimizerPackage


def test_build_range_chunks_returns_dict_of_packages(roboto: TtfFont):
    """Test that build_range_chunks returns a dict with packages for each range."""
    result = WebFontOptimizer.build_range_chunks(
        roboto,
        ranges=(
            ("latin", (0x0000, 0x00FF)),
            ("latin-ext", (0x0100, 0x024F)),
        ),
        source_path=Path("testdata/Roboto-VariableFont_wdth,wght.ttf"),
        include_woff=False,
    )

    assert isinstance(result, dict)
    assert set(result.keys()) == {"latin", "latin-ext"}

    for name, package in result.items():
        assert isinstance(package, WebFontOptimizerPackage)
        assert package.bundle.family == "Roboto"
        assert package.manifest["range_name"] == name
        assert package.size_summary["total_web_font_bytes"] > 0


def test_build_range_chunks_preserves_fvar_and_gvar(roboto: TtfFont):
    """Test that chunking preserves fvar/gvar tables in each chunk."""
    result = WebFontOptimizer.build_range_chunks(
        roboto,
        ranges=(("latin", (0x0000, 0x00FF)),),
        source_path=Path("testdata/Roboto-VariableFont_wdth,wght.ttf"),
    )

    chunk = result["latin"]
    subset_font = chunk.bundle.preview_font

    assert isinstance(subset_font, TtfFont)
    assert subset_font.is_variable, "Chunk should remain variable"
    assert subset_font.ttf_tables.fvar is not None, "fvar table must be preserved"
    assert "gvar" in subset_font.ttf_tables._raw, "gvar table must be preserved"


def test_build_range_chunks_manifest_records_coverage(roboto: TtfFont):
    """Test that manifest records codepoint coverage data."""
    result = WebFontOptimizer.build_range_chunks(
        roboto,
        ranges=(("latin", (0x0000, 0x00FF)),),
        source_path=Path("testdata/Roboto-VariableFont_wdth,wght.ttf"),
    )

    manifest = result["latin"].manifest
    assert manifest["range_name"] == "latin"
    assert manifest["range_spec"] == [0x0000, 0x00FF]

    coverage = manifest["coverage"]
    assert coverage["covered_count"] >= 1, "At least some codepoints should be covered"
    assert coverage["total_in_range"] == 256
    assert "coverage_percent" in coverage


def test_build_range_chunks_raises_for_static_font():
    """Test that chunking raises ValueError for non-variable font."""
    from aspose_font import FontLoader

    font = FontLoader.open(Path("testdata/Fonts/Roboto-Regular.ttf"))
    assert not font.is_variable, "Test font should be static"

    import pytest

    with pytest.raises(ValueError, match="Range chunking requires a variable font"):
        WebFontOptimizer.build_range_chunks(
            font,
            ranges=(("latin", (0x0000, 0x00FF)),),
        )


def test_build_range_chunks_raises_for_invalid_range(roboto: TtfFont):
    """Test that chunking raises ValueError for invalid range (start > end)."""
    import pytest

    with pytest.raises(ValueError, match="Invalid range"):
        WebFontOptimizer.build_range_chunks(
            roboto,
            ranges=(("invalid", (0x0100, 0x0050)),),
        )


def test_build_range_chunks_requires_preserve_variable_true(roboto: TtfFont):
    """Test that chunking requires preserve_variable=True."""
    import pytest

    with pytest.raises(ValueError, match="Range chunking requires preserve_variable=True"):
        WebFontOptimizer.build_range_chunks(
            roboto,
            ranges=(("latin", (0x0000, 0x00FF)),),
            preserve_variable=False,
        )
