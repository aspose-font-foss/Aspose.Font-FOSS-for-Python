"""Tests for SPEC-016 font subsetting."""

from __future__ import annotations

from pathlib import Path

import pytest

from aspose_font import CffFont, FontLoader, TtfFont, Type1Font, WoffFont
from aspose_font.subsetter import FontSubsetter
from aspose_font.type1.afm import AfmData, AfmGlyphMetric


def test_subset_by_text_ttf_returns_ttf(roboto: TtfFont):
    subsetted = FontSubsetter.subset_by_text(roboto, "Hello World")
    assert isinstance(subsetted, TtfFont)


def test_subset_by_text_ttf_num_glyphs(roboto: TtfFont):
    subsetted = FontSubsetter.subset_by_text(roboto, "Hello World")
    assert subsetted.num_glyphs <= 10


def test_subset_ttf_roundtrip(roboto: TtfFont):
    subsetted = FontSubsetter.subset_by_text(roboto, "Hello World")
    reloaded = FontLoader.open(subsetted.to_bytes())
    assert isinstance(reloaded, TtfFont)
    assert reloaded.num_glyphs == subsetted.num_glyphs


def test_subset_ttf_encoding_complete(roboto: TtfFont):
    text = "Hello World"
    subsetted = FontSubsetter.subset_by_text(roboto, text)
    reloaded = FontLoader.open(subsetted.to_bytes())
    for cp in {ord(ch) for ch in text}:
        assert int(reloaded.encoding.unicode_to_gid(cp)) >= 0


def test_subset_by_text_cff_returns_cff(opensans_cff: CffFont):
    subsetted = FontSubsetter.subset_by_text(opensans_cff, "AB")
    assert isinstance(subsetted, CffFont)


def test_subset_cff_num_glyphs(opensans_cff: CffFont):
    subsetted = FontSubsetter.subset_by_text(opensans_cff, "AB")
    assert subsetted.num_glyphs <= 3


def test_subset_empty_codepoints(roboto: TtfFont):
    subsetted = FontSubsetter.subset(roboto, set())
    assert subsetted.num_glyphs == 1


def test_subset_woff_returns_woff(saira_woff: WoffFont):
    subsetted = FontSubsetter.subset_by_text(saira_woff, "Hi")
    assert isinstance(subsetted, WoffFont)


def test_subset_type1_returns_type1(testdata_dir: Path):
    type1 = FontLoader.open(str(testdata_dir / "OpenSans-Regular.pfb"))
    subsetted = FontSubsetter.subset_by_text(type1, "A")
    assert isinstance(subsetted, Type1Font)
    assert subsetted.font_type == type1.font_type
    assert subsetted.num_glyphs <= 2


def test_subset_type1_roundtrip_and_encoding(testdata_dir: Path):
    type1 = FontLoader.open(str(testdata_dir / "OpenSans-Regular.pfb"))
    assert isinstance(type1, Type1Font)
    retained_name = type1._gid_to_name[1]
    dropped_name = type1._gid_to_name[2]
    subsetted = FontSubsetter.subset_by_gids(type1, {1})
    reloaded = FontLoader.open(subsetted.to_bytes())
    assert isinstance(reloaded, Type1Font)
    assert retained_name in reloaded._gid_to_name
    assert dropped_name not in reloaded._gid_to_name
    assert reloaded.num_glyphs == 2


def test_subset_type1_preserves_afm_metrics_and_filters_kern(testdata_dir: Path):
    type1 = FontLoader.open(str(testdata_dir / "OpenSans-Regular.pfb"))
    assert isinstance(type1, Type1Font)
    name_a = type1._gid_to_name[1]
    name_b = type1._gid_to_name[2]
    name_c = type1._gid_to_name[3]
    afm = AfmData(
        font_name="Subset Demo",
        family_name="Subset Demo",
        weight="Regular",
        ascender=800,
        descender=-200,
        underline_position=-100,
        underline_thickness=50,
        glyph_metrics={
            name_a: AfmGlyphMetric(name_a, ord("A"), 610, (0, 0, 600, 700)),
            name_b: AfmGlyphMetric(name_b, ord("B"), 640, (0, 0, 620, 700)),
            name_c: AfmGlyphMetric(name_c, ord("C"), 660, (0, 0, 630, 700)),
        },
        kern_pairs=[(name_a, name_b, -40), (name_a, name_c, -15)],
    )
    type1._afm = afm

    subsetted = FontSubsetter.subset_by_gids(type1, {1, 2})
    assert isinstance(subsetted, Type1Font)
    assert subsetted.metrics.advance_width_max == 640
    assert len(subsetted.get_kern_pairs()) == 1
    glyph_a = subsetted.glyph_accessor.get_glyph_by_id(subsetted._name_to_gid[name_a])
    assert glyph_a.advance_width == 610


def test_subset_by_gids(roboto: TtfFont):
    subsetted = FontSubsetter.subset_by_gids(roboto, {5, 10})
    assert isinstance(subsetted, TtfFont)
    assert subsetted.num_glyphs <= 3


def test_available_presets_exposes_common_web_sets():
    presets = FontSubsetter.available_presets()
    assert presets == (
        "latin",
        "latin-ext",
        "cyrillic",
        "greek",
        "hebrew",
        "arabic",
        "devanagari",
        "thai",
    )


def test_subset_by_presets_keeps_requested_script_only(roboto: TtfFont):
    subsetted = FontSubsetter.subset_by_presets(roboto, "cyrillic")
    reloaded = FontLoader.open(subsetted.to_bytes())
    codepoints = set(reloaded.encoding.get_all_codepoints())
    assert 0x0410 in codepoints
    assert 0x0041 not in codepoints


def test_subset_for_web_combines_presets_text_and_ranges(roboto: TtfFont):
    subsetted = FontSubsetter.subset_for_web(
        roboto,
        presets=("latin",),
        text="Ж",
        ranges=[(0x03B1, 0x03B1)],
    )
    reloaded = FontLoader.open(subsetted.to_bytes())
    codepoints = set(reloaded.encoding.get_all_codepoints())
    assert 0x0041 in codepoints
    assert 0x0416 in codepoints
    assert 0x03B1 in codepoints


def test_resolve_codepoints_merges_all_selection_inputs():
    codepoints = FontSubsetter.resolve_codepoints(
        presets=("latin",),
        text="Ж",
        codepoints=[0x20AC],
        ranges=[range(0x03B1, 0x03B2)],
    )
    assert 0x0041 in codepoints
    assert 0x0416 in codepoints
    assert 0x20AC in codepoints
    assert 0x03B1 in codepoints


def test_resolve_codepoints_supports_expanded_web_script_presets():
    codepoints = FontSubsetter.resolve_codepoints(
        presets=("hebrew", "arabic", "devanagari", "thai"),
    )
    assert 0x05D0 in codepoints
    assert 0x0627 in codepoints
    assert 0x0915 in codepoints
    assert 0x0E01 in codepoints


def test_subset_by_presets_unknown_name_raises(roboto: TtfFont):
    with pytest.raises(ValueError, match="Unknown subset preset"):
        FontSubsetter.subset_by_presets(roboto, "emoji")


def test_resolve_codepoints_invalid_range_raises():
    with pytest.raises(ValueError, match="Invalid Unicode range"):
        FontSubsetter.resolve_codepoints(ranges=[(0x0400, 0x03FF)])


def test_analyze_coverage_reports_full_coverage(roboto: TtfFont):
    coverage = FontSubsetter.analyze_coverage(roboto, {ord("A"), ord("B")})

    assert coverage.requested_count == 2
    assert coverage.covered_count == 2
    assert coverage.missing_count == 0
    assert coverage.fully_covered is True
    assert 0 in coverage.retained_gids


def test_analyze_coverage_reports_partial_missing_codepoints(roboto: TtfFont):
    coverage = FontSubsetter.analyze_coverage(roboto, {ord("A"), 0x10FFFF})

    assert coverage.requested_codepoints == (ord("A"), 0x10FFFF)
    assert coverage.covered_codepoints == (ord("A"),)
    assert coverage.missing_codepoints == (0x10FFFF,)
    assert coverage.fully_covered is False


def test_analyze_web_coverage_groups_presets_text_codepoints_and_ranges(roboto: TtfFont):
    coverage = FontSubsetter.analyze_web_coverage(
        roboto,
        presets=("latin",),
        text="A",
        codepoints=[0x10FFFF],
        ranges=[(ord("B"), ord("B"))],
    )

    assert [group.kind for group in coverage.groups] == ["preset", "text", "codepoints", "range"]
    assert coverage.groups[0].label == "latin"
    assert coverage.groups[2].missing_codepoints == (0x10FFFF,)
    assert coverage.groups[3].covered_codepoints == (ord("B"),)
    assert 0x10FFFF in coverage.missing_codepoints


def test_subset_for_web_with_coverage_returns_font_and_diagnostics(roboto: TtfFont):
    result = FontSubsetter.subset_for_web_with_coverage(
        roboto,
        text="A",
        codepoints=[0x10FFFF],
    )

    assert isinstance(result.font, TtfFont)
    assert result.coverage.covered_codepoints == (ord("A"),)
    assert result.coverage.missing_codepoints == (0x10FFFF,)


def test_analyze_web_coverage_empty_request_has_zero_counts(roboto: TtfFont):
    coverage = FontSubsetter.analyze_web_coverage(roboto)

    assert coverage.requested_count == 0
    assert coverage.covered_count == 0
    assert coverage.missing_count == 0
    assert coverage.retained_gids == (0,)
    assert coverage.groups == ()
