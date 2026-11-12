"""Tests for meta table language integration in FontCapabilityBuilder (FONT-518)."""

from aspose_font import FontLoader
from aspose_font.capability import FontCapabilityBuilder


def test_capability_report_includes_design_languages_from_meta() -> None:
    """Test that capability report extracts design languages from meta table."""
    font_path = "testdata/TTF/SymbolicFonts/symbol.ttf"
    font = FontLoader.open(font_path)

    if font.ttf_tables.meta is not None and font.ttf_tables.meta.design_languages:
        report = FontCapabilityBuilder.build(font)
        assert report.design_languages == tuple(font.ttf_tables.meta.design_languages)
    else:
        report = FontCapabilityBuilder.build(font)
        assert report.design_languages == ()


def test_capability_report_includes_supported_languages_from_meta() -> None:
    """Test that capability report extracts supported languages from meta table."""
    font_path = "testdata/TTF/SymbolicFonts/symbol.ttf"
    font = FontLoader.open(font_path)

    if font.ttf_tables.meta is not None and font.ttf_tables.meta.supported_languages:
        report = FontCapabilityBuilder.build(font)
        assert report.supported_languages == tuple(font.ttf_tables.meta.supported_languages)
    else:
        report = FontCapabilityBuilder.build(font)
        assert report.supported_languages == ()


def test_capability_report_returns_empty_tuples_without_meta_table(roboto) -> None:
    """Test that fonts without meta table return empty language tuples."""
    report = FontCapabilityBuilder.build(roboto)
    assert report.design_languages == ()
    assert report.supported_languages == ()


def test_capability_report_to_dict_contains_language_fields(roboto) -> None:
    """Test that to_dict includes design_languages and supported_languages."""
    report = FontCapabilityBuilder.build(roboto)
    result = report.to_dict()

    assert "design_languages" in result
    assert "supported_languages" in result
    assert isinstance(result["design_languages"], list)
    assert isinstance(result["supported_languages"], list)


def test_capability_summaries_include_language_information() -> None:
    """Test that language summary is included when meta table has language data."""
    font_path = "testdata/TTF/SymbolicFonts/symbol.ttf"
    font = FontLoader.open(font_path)

    report = FontCapabilityBuilder.build(font)

    summary_labels = [s.label for s in report.summaries]
    if report.design_languages or report.supported_languages:
        assert "Languages" in summary_labels
    else:
        assert "Languages" in summary_labels


def test_language_field_empty_when_meta_absent(opensans_cff) -> None:
    """Test that static fonts without meta return empty language tuples."""
    report = FontCapabilityBuilder.build(opensans_cff)

    assert report.design_languages == ()
    assert report.supported_languages == ()
