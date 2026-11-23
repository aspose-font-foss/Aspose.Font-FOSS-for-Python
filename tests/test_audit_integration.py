"""Integration test for FONT-509: WebFontOptimizer with subsetting audit."""

from __future__ import annotations

from aspose_font import WebFontOptimizer
from aspose_font.ttf.font import TtfFont


def test_web_optimizer_includes_subset_audit_for_text_subset(roboto: TtfFont):
    """Audit should be included when subsetting by text."""
    package = WebFontOptimizer.build(
        roboto,
        text="ABC",
        preview_text="ABC",
    )

    manifest = package.bundle.manifest
    assert "subset_audit" in manifest, "subset_audit missing from bundle.manifest"

    audit = manifest["subset_audit"]
    assert audit.get("kind") == "font_subsetting_audit"
    assert "coverage" in audit
    assert "variation_deltas" in audit
    assert "original_glyph_count" in audit
    assert "subset_glyph_count" in audit


def test_web_optimizer_includes_subset_audit_for_codepoint_subset(roboto: TtfFont):
    """Audit should be included when subsetting by codepoints."""
    package = WebFontOptimizer.build(
        roboto,
        codepoints=[65, 66, 67],
        preview_text="ABC",
    )

    manifest = package.bundle.manifest
    assert "subset_audit" in manifest
    audit = manifest["subset_audit"]
    assert audit.get("kind") == "font_subsetting_audit"
    assert "coverage" in audit
    assert "original_glyph_count" in audit
    assert "subset_glyph_count" in audit


def test_web_optimizer_no_audit_for_non_subset_variable(roboto: TtfFont):
    """Audit should be omitted or minimal for non-subset variable fonts."""
    package = WebFontOptimizer.build(
        roboto,
        variable_mode="auto",
        preview_text="Hamburgefons",
    )

    manifest = package.bundle.manifest
    if "subset_audit" in manifest:
        audit = manifest["subset_audit"]
        assert audit.get("kind") == "font_subsetting_audit"
        assert "coverage" in audit


def test_web_optimizer_subset_audit_has_coverage_info(roboto: TtfFont):
    """Audit coverage should include label, counts, and missing glyphs."""
    package = WebFontOptimizer.build(
        roboto,
        text="ABC",
        preview_text="ABC",
    )

    audit = package.bundle.manifest["subset_audit"]
    coverage = audit["coverage"]
    assert coverage.get("kind") == "glyph"
    assert coverage.get("label") == "subset"
    assert "original_count" in coverage
    assert "subset_count" in coverage
    assert "missing_gids" in coverage
    assert "missing_codepoints" in coverage


def test_web_optimizer_subset_audit_structure_with_presets(roboto: TtfFont):
    """Audit should work with presets parameter."""
    package = WebFontOptimizer.build(
        roboto,
        presets=("latin",),
        preview_text="ABC",
    )

    manifest = package.bundle.manifest
    assert "subset_audit" in manifest
    audit = manifest["subset_audit"]
    assert "features" in audit
    assert "composite_dependencies" in audit
    assert "overall_passed" in audit


def test_web_optimizer_subset_audit_to_dict_structure(roboto: TtfFont):
    """Audit result should have correct to_dict() output."""
    package = WebFontOptimizer.build(
        roboto,
        text="A",
        preview_text="A",
    )

    audit = package.bundle.manifest["subset_audit"]

    expected_keys = {
        "kind",
        "original_glyph_count",
        "subset_glyph_count",
        "coverage",
        "composite_dependencies",
        "variation_deltas",
        "features",
        "overall_passed",
        "issues",
    }
    assert set(audit.keys()) == expected_keys
