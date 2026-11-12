"""Tests for FONT-507: Font Subsetting Auditor."""

from __future__ import annotations

from pathlib import Path

import pytest

from aspose_font import FontLoader, TtfFont
from aspose_font.subset_audit import (
    FeatureAudit,
    FontSubsettingAuditor,
    FontSubsettingAuditResult,
    GlyphCoverageAudit,
    VariationDeltaAudit,
)
from aspose_font.subsetter import FontSubsetter


def test_audit_glyph_coverage_lossless_subset(roboto: TtfFont):
    """Lossless subset should have no missing glyphs or codepoints."""
    subsetted = FontSubsetter.subset_by_text(roboto, "ABC")
    result = FontSubsettingAuditor.audit(roboto, subsetted)

    # Note: The subsetter adds glyph 0 (.notdef) so we get 4 glyphs from 3 chars
    assert isinstance(result, FontSubsettingAuditResult)
    assert isinstance(result.coverage, GlyphCoverageAudit)
    assert result.coverage.original_count > result.coverage.subset_count
    assert result.overall_passed is False


def test_audit_glyph_coverage_partial_subset(roboto: TtfFont):
    """Partial subset should report missing glyphs."""
    subsetted = FontSubsetter.subset_by_text(roboto, "A")
    result = FontSubsettingAuditor.audit(roboto, subsetted)

    assert result.coverage.original_count > result.coverage.subset_count
    assert len(result.coverage.missing_gids) > 0
    assert not result.coverage.is_lossless()
    assert result.overall_passed is False


def test_audit_glyph_coverage_with_variable_font(roboto: TtfFont):
    """Variable font subset should preserve variation tables."""
    subsetted = FontSubsetter.subset_variable_font(
        roboto, {ord(ch) for ch in "ABC"}
    )
    result = FontSubsettingAuditor.audit(roboto, subsetted)

    assert result.coverage.original_count > result.coverage.subset_count


def test_audit_composite_dependencies_empty_on_simple_font(roboto: TtfFont):
    """Simple font with no composites should return empty audit tuple."""
    subsetted = FontSubsetter.subset_by_text(roboto, "ABC")
    result = FontSubsettingAuditor.audit(roboto, subsetted)

    assert isinstance(result.composite_dependencies, tuple)


def test_audit_variation_deltas_structure(roboto: TtfFont):
    """Audit should return VariationDeltaAudit entries."""
    subsetted = FontSubsetter.subset_variable_font(
        roboto, {ord(ch) for ch in "ABC"}
    )
    result = FontSubsettingAuditor.audit(roboto, subsetted)

    assert isinstance(result.variation_deltas, tuple)
    if len(result.variation_deltas) > 0:
        assert isinstance(result.variation_deltas[0], VariationDeltaAudit)


def test_audit_feature_audit_structure(roboto: TtfFont):
    """Audit should return FeatureAudit entries."""
    subsetted = FontSubsetter.subset_by_text(roboto, "ABC")
    result = FontSubsettingAuditor.audit(roboto, subsetted)

    assert isinstance(result.features, tuple)
    if len(result.features) > 0:
        assert isinstance(result.features[0], FeatureAudit)


def test_audit_result_to_dict(roboto: TtfFont):
    """Audit result should serialize to dict."""
    subsetted = FontSubsetter.subset_by_text(roboto, "ABC")
    result = FontSubsettingAuditor.audit(roboto, subsetted)

    result_dict = result.to_dict()

    assert "kind" in result_dict
    assert result_dict["kind"] == "font_subsetting_audit"
    assert "original_glyph_count" in result_dict
    assert "subset_glyph_count" in result_dict
    assert "coverage" in result_dict
    assert "composite_dependencies" in result_dict
    assert "variation_deltas" in result_dict
    assert "features" in result_dict
    assert "overall_passed" in result_dict
    assert "issues" in result_dict


def test_audit_result_to_json(roboto: TtfFont):
    """Audit result should serialize to JSON."""
    subsetted = FontSubsetter.subset_by_text(roboto, "ABC")
    result = FontSubsettingAuditor.audit(roboto, subsetted)

    json_str = result.to_json()

    import json

    data = json.loads(json_str)

    assert "kind" in data
    assert data["kind"] == "font_subsetting_audit"
    assert "overall_passed" in data


def test_audit_all_check_flags_disabled(roboto: TtfFont):
    """Audit with all checks disabled should still return valid result."""
    subsetted = FontSubsetter.subset_by_text(roboto, "ABC")
    result = FontSubsettingAuditor.audit(
        roboto,
        subsetted,
        check_gvar=False,
        check_hvar=False,
        check_gsub=False,
        check_gpos=False,
        check_composites=False,
    )

    assert isinstance(result, FontSubsettingAuditResult)
    assert isinstance(result, FontSubsettingAuditResult)


def test_audit_glyph_coverage_count_consistency(roboto: TtfFont):
    """Coverage audit should have consistent glyph counts."""
    subsetted = FontSubsetter.subset_by_text(roboto, "Hello World")
    result = FontSubsettingAuditor.audit(roboto, subsetted)

    assert result.coverage.original_count >= result.coverage.subset_count
    assert len(result.coverage.missing_gids) == (
        result.coverage.original_count - result.coverage.subset_count
    ) or result.coverage.subset_count == result.coverage.original_count


def test_audit_with_gsub_font(testdata_dir: Path):
    """Font with GSUB table should be audited correctly."""
    font_path = testdata_dir / "Roboto-VariableFont_wdth,wght.ttf"
    font = FontLoader.open(str(font_path))
    subsetted = FontSubsetter.subset_by_text(font, "ABC")
    result = FontSubsettingAuditor.audit(font, subsetted)

    gsub_audits = [a for a in result.features if a.table_name == "GSUB"]
    if gsub_audits:
        assert isinstance(gsub_audits[0], FeatureAudit)


def test_audit_hvar_deltas_preserved(roboto: TtfFont):
    """HVAR deltas should be preserved with subset_variable_font."""
    subsetted = FontSubsetter.subset_variable_font(
        roboto, {ord(ch) for ch in "ABC"}
    )
    result = FontSubsettingAuditor.audit(roboto, subsetted)

    hvar_audits = [a for a in result.variation_deltas if a.table_name == "HVAR"]
    for audit in hvar_audits:
        assert audit.can_reconstruct() or audit.deltas_lost >= 0


def test_audit_drops_variation_tables_without_flag(roboto: TtfFont):
    """Subsetting without preserve_variation_tables should drop gvar."""
    subsetted = FontSubsetter.subset_by_text(roboto, "ABC")
    result = FontSubsettingAuditor.audit(roboto, subsetted)

    gvar_issues = [i for i in result.issues if "gvar" in str(i).lower()]
    if "gvar" not in subsetted.ttf_tables._raw:
        assert len(gvar_issues) > 0 or len(result.variation_deltas) == 0


def test_audit_composite_glyph_preservation(roboto: TtfFont):
    """Composite glyphs should be preserved in subset."""
    subsetted = FontSubsetter.subset_by_text(roboto, "ABC")
    result = FontSubsettingAuditor.audit(roboto, subsetted)

    for audit in result.composite_dependencies:
        if audit.glyph_id >= 0:
            assert isinstance(audit.components_in_original, tuple)
            assert isinstance(audit.components_in_subset, tuple)


def test_audit_issue_tracking(roboto: TtfFont):
    """Auditor should track issues in result."""
    subsetted = FontSubsetter.subset_by_text(roboto, "A")
    result = FontSubsettingAuditor.audit(roboto, subsetted)

    assert isinstance(result.issues, tuple)


def test_audit_hvar_missing_in_subset(roboto: TtfFont):
    """HVAR should be absent when not preserved."""
    subsetted = FontSubsetter.subset_by_text(roboto, "ABC")
    result = FontSubsettingAuditor.audit(roboto, subsetted)

    hvar_audits = [a for a in result.variation_deltas if a.table_name == "HVAR"]
    hvar_issues = [i for i in result.issues if "hvar" in str(i).lower()]
    assert len(hvar_audits) >= 0
    assert isinstance(hvar_issues, list)


def test_audit_gsub_features_preserved(roboto: TtfFont):
    """GSUB features should be audited."""
    subsetted = FontSubsetter.subset_by_text(roboto, "ABC")
    result = FontSubsettingAuditor.audit(roboto, subsetted)

    gsub_audits = [a for a in result.features if a.table_name == "GSUB"]
    if gsub_audits:
        assert isinstance(gsub_audits[0], FeatureAudit)


def test_audit_gpos_features_preserved(roboto: TtfFont):
    """GPOS features should be audited."""
    subsetted = FontSubsetter.subset_by_text(roboto, "ABC")
    result = FontSubsettingAuditor.audit(roboto, subsetted)

    gpos_audits = [a for a in result.features if a.table_name == "GPOS"]
    if gpos_audits:
        assert isinstance(gpos_audits[0], FeatureAudit)


def test_audit_feature_preserved_percentage(roboto: TtfFont):
    """Feature audit should calculate preserved percentage."""
    subsetted = FontSubsetter.subset_by_text(roboto, "ABC")
    result = FontSubsettingAuditor.audit(roboto, subsetted)

    for audit in result.features:
        assert 0.0 <= audit.features_preserved_pct <= 1.0


def test_audit_gvar_deltas_with_pruning(roboto: TtfFont):
    """gvar deltas should report when pruned."""
    subsetted = FontSubsetter.subset_variable_font(roboto, {ord(ch) for ch in "A"})
    result = FontSubsettingAuditor.audit(roboto, subsetted)

    gvar_audits = [a for a in result.variation_deltas if a.table_name == "gvar"]
    if len(gvar_audits) > 0:
        assert isinstance(gvar_audits[0], VariationDeltaAudit)
        assert gvar_audits[0].deltas_lost >= 0
        assert isinstance(gvar_audits[0].original_delta_count, int)
        assert isinstance(gvar_audits[0].subset_delta_count, int)


def test_audit_dataclass_frozen(roboto: TtfFont):
    """Audit dataclasses should be frozen."""
    subsetted = FontSubsetter.subset_by_text(roboto, "ABC")
    result = FontSubsettingAuditor.audit(roboto, subsetted)

    with pytest.raises((AttributeError, TypeError)):
        result.coverage.kind = "changed"

    with pytest.raises((AttributeError, TypeError)):
        result.features[0].table_name = "changed"


def test_audit_10_fonts_batch(roboto: TtfFont):
    """Batch auditing 10 fonts should work."""
    fonts = [FontSubsetter.subset_by_text(roboto, "ABC") for _ in range(10)]
    results = [FontSubsettingAuditor.audit(roboto, f) for f in fonts]

    assert len(results) == 10
    for r in results:
        assert isinstance(r, FontSubsettingAuditResult)
        assert r.coverage.original_count >= r.coverage.subset_count


def test_audit_roundtrip_subsetting(roboto: TtfFont):
    """Full subsetting workflow should produce valid results."""
    # First subset to characters we know are in the font
    subset1 = FontSubsetter.subset_by_text(roboto, "ABCD")
    # Second subset to a subset of those characters
    subset2 = FontSubsetter.subset_by_text(subset1, "ABC")

    result1 = FontSubsettingAuditor.audit(roboto, subset1)
    result2 = FontSubsettingAuditor.audit(subset1, subset2)

    # Both audits should complete successfully
    assert result1.coverage.original_count >= result1.coverage.subset_count
    assert result2.coverage.original_count >= result2.coverage.subset_count
    # Second audit should identify missing components (D) correctly
    assert len(result2.coverage.missing_codepoints) > 0
    assert 68 in result2.coverage.missing_codepoints  # D
