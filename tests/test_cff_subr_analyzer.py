"""Tests for CFF/CFF2 subroutine analyzer (FONT-520)."""

from __future__ import annotations

from pathlib import Path

from aspose_font import FontLoader, FontType
from aspose_font.cff.subr_analyzer import (
    SubroutineAnalysis,
    analyze_cff_font,
)


def test_analyze_cff_font_returns_analysis(opensans_cff_path: Path) -> None:
    """Standard CFF font analysis returns SubroutineAnalysis."""
    font = FontLoader.open(str(opensans_cff_path), font_type=FontType.CFF)
    result = analyze_cff_font(font)

    assert isinstance(result, SubroutineAnalysis)
    assert result.font_type == "CFF"
    assert result.num_glyphs > 0
    assert result.global_subrs_count >= 0


def test_analysis_has_non_negative_counts(opensans_cff_path: Path) -> None:
    """All subroutine counts are non-negative."""
    font = FontLoader.open(str(opensans_cff_path), font_type=FontType.CFF)
    result = analyze_cff_font(font)

    assert result.global_subrs_count >= 0
    assert result.local_subrs_count >= 0
    assert result.charstrings_analyzed == result.num_glyphs


def test_global_subrs_in_use_is_subset_of_total(opensans_cff_path: Path) -> None:
    """In-use indices are valid and within total count."""
    font = FontLoader.open(str(opensans_cff_path), font_type=FontType.CFF)
    result = analyze_cff_font(font)

    for idx in result.global_subrs_in_use:
        assert 0 <= idx < result.global_subrs_count
    for idx in result.global_subrs_unused:
        assert 0 <= idx < result.global_subrs_count
    assert len(result.global_subrs_in_use) + len(result.global_subrs_unused) == result.global_subrs_count


def test_local_subrs_unused_may_be_empty(opensans_cff_path: Path) -> None:
    """Local subrs_unused list may be empty if all are used."""
    font = FontLoader.open(str(opensans_cff_path), font_type=FontType.CFF)
    result = analyze_cff_font(font)

    assert isinstance(result.local_subrs_unused, list)
    assert isinstance(result.local_subrs_in_use, list)
    assert result.local_subrs_count >= 0


def test_max_nesting_depth_is_reasonable(opensans_cff_path: Path) -> None:
    """Call depth is bounded (practical fonts rarely exceed 5)."""
    font = FontLoader.open(str(opensans_cff_path), font_type=FontType.CFF)
    result = analyze_cff_font(font)

    assert result.max_nesting_depth >= 0
    assert result.max_nesting_depth <= 20


def test_analysis_to_dict_is_json_serializable(opensans_cff_path: Path) -> None:
    """Analysis.to_dict() produces JSON-compatible dict."""
    import json

    font = FontLoader.open(str(opensans_cff_path), font_type=FontType.CFF)
    result = analyze_cff_font(font)
    data = result.to_dict()

    json_str = json.dumps(data)
    assert isinstance(json_str, str)


def test_analysis_to_dict_contains_required_fields(opensans_cff_path: Path) -> None:
    """JSON dict has all expected keys."""
    font = FontLoader.open(str(opensans_cff_path), font_type=FontType.CFF)
    result = analyze_cff_font(font)
    data = result.to_dict()

    assert "font_name" in data
    assert "font_type" in data
    assert "num_glyphs" in data
    assert "global_subrs" in data
    assert "local_subrs" in data
    assert "max_nesting_depth" in data
    assert "charstrings_analyzed" in data


def test_subroutine_info_has_required_fields(opensans_cff_path: Path) -> None:
    """SubroutineInfo dataclass has required fields."""
    font = FontLoader.open(str(opensans_cff_path), font_type=FontType.CFF)
    result = analyze_cff_font(font)

    for subr in result.global_subrs_info:
        assert hasattr(subr, "index")
        assert hasattr(subr, "byte_size")
        assert hasattr(subr, "call_count")
        assert hasattr(subr, "max_nesting_depth")

    for subr in result.local_subrs_info:
        assert hasattr(subr, "index")
        assert hasattr(subr, "byte_size")
        assert hasattr(subr, "call_count")
        assert hasattr(subr, "max_nesting_depth")


def test_unused_subrs_are_identified(opensans_cff_path: Path) -> None:
    """Unused subrs are correctly identified."""
    font = FontLoader.open(str(opensans_cff_path), font_type=FontType.CFF)
    result = analyze_cff_font(font)

    unused = result.global_subrs_unused + result.local_subrs_unused
    for idx in unused:
        assert isinstance(idx, int)
        assert idx >= 0
