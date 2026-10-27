"""Tests for plain-language font capability discovery facade."""

from __future__ import annotations

import json

from aspose_font.capability import (
    AxisDescription,
    CSSHints,
    FontCapabilityBuilder,
    FontCapabilityReport,
    ReleaseRisk,
    ScriptCoverage,
)


def test_capability_report_structure_variable_font(roboto) -> None:
    report = FontCapabilityBuilder.build(roboto, preferred_languages=("en",))

    assert isinstance(report, FontCapabilityReport)
    assert report.font_identity["font_family"] == "Roboto"
    assert report.font_identity["is_variable"] is True
    assert len(report.axes) > 0
    assert len(report.coverage) > 0
    assert isinstance(report.css_hints, CSSHints)
    assert isinstance(report.release_risks, tuple)
    assert isinstance(report.summaries, tuple)


def test_axis_descriptions_with_human_readable_labels(roboto) -> None:
    report = FontCapabilityBuilder.build(roboto, preferred_languages=("en",))

    axis_map = {a.tag: a for a in report.axes}
    assert "wght" in axis_map
    wght = axis_map["wght"]
    assert isinstance(wght, AxisDescription)
    assert wght.tag == "wght"
    assert wght.label == "Weight"
    assert wght.min_value == 100.0
    assert wght.default_value == 400.0
    assert wght.max_value == 900.0
    assert "Light" in wght.default_description or "Regular" in wght.default_description
    assert "100 -> 900" in wght.range_summary
    assert len(wght.presets) > 0
    assert wght.css_hint


def test_axis_presets_include_common_values(roboto) -> None:
    report = FontCapabilityBuilder.build(roboto, preferred_languages=("en",))

    axis_map = {a.tag: a for a in report.axes}
    wght = axis_map.get("wght")
    if wght:
        preset_names = [p["preset_name"] for p in wght.presets]
        assert "Light" in preset_names
        assert "Bold" in preset_names
        assert "Regular" in preset_names


def test_script_coverage_grouped_by_family(roboto) -> None:
    report = FontCapabilityBuilder.build(roboto, preferred_languages=("en",))

    coverage_map = {c.script_family: c for c in report.coverage}
    assert "latin" in coverage_map
    latin = coverage_map["latin"]
    assert isinstance(latin, ScriptCoverage)
    assert latin.script_label == "Latin"
    assert latin.requested_count > 0
    assert latin.covered_count > 0
    assert 0 <= latin.percentage <= 100


def test_script_coverage_web_ready_flag(roboto) -> None:
    report = FontCapabilityBuilder.build(roboto, preferred_languages=("en",))

    latin = next((c for c in report.coverage if c.script_family == "latin"), None)
    if latin:
        assert latin.web_ready is False
        assert latin.percentage < 99.0


def test_css_hints_include_at_font_face(roboto) -> None:
    report = FontCapabilityBuilder.build(roboto, preferred_languages=("en",))

    css = report.css_hints
    assert isinstance(css, CSSHints)
    assert isinstance(css.at_font_face, dict)
    assert "font-family" in css.at_font_face
    assert "src" in css.at_font_face
    assert "font-display" in css.at_font_face
    assert css.font_display == "swap"


def test_css_hints_include_unicode_range_for_latin(roboto) -> None:
    report = FontCapabilityBuilder.build(roboto, preferred_languages=("en",))

    css = report.css_hints
    assert css.unicode_range is not None
    assert "U+0000" in css.unicode_range or "0000" in css.unicode_range


def test_css_custom_properties_for_variable_fonts(roboto) -> None:
    report = FontCapabilityBuilder.build(roboto, preferred_languages=("en",))

    css = report.css_hints
    if report.font_identity["is_variable"]:
        assert css.css_custom_properties is not None
        assert "axis_variables" in css.css_custom_properties
        assert "usage_example" in css.css_custom_properties


def test_release_risks_detects_missing_names_for_static_font(opensans_cff) -> None:
    report = FontCapabilityBuilder.build(opensans_cff, preferred_languages=("en",))

    has_name_issues = any(r.code == "missing-font-names" for r in report.release_risks)
    if not opensans_cff.font_name or not opensans_cff.font_family:
        assert has_name_issues
    else:
        assert not has_name_issues


def test_release_risks_detects_missing_stat_table(roboto) -> None:
    report = FontCapabilityBuilder.build(roboto, preferred_languages=("en",))

    has_stat_issue = any(r.code == "missing-stat-table" for r in report.release_risks)
    assert has_stat_issue is False


def test_summaries_produce_plain_language_overview(roboto) -> None:
    report = FontCapabilityBuilder.build(roboto, preferred_languages=("en",))

    summary_labels = [s.label for s in report.summaries]
    assert "Variable Axes" in summary_labels
    assert "Script Coverage" in summary_labels
    assert "CSS implementation" in summary_labels
    assert "Release readiness" in summary_labels


def test_summaries_include_variable_axe_count(roboto) -> None:
    report = FontCapabilityBuilder.build(roboto, preferred_languages=("en",))

    axis_summary = next(s for s in report.summaries if s.label == "Variable Axes")
    assert axis_summary.details["axis_count"] == len(report.axes)
    assert axis_summary.details["is_variable"] is True


def test_variable_axis_default_description(roboto) -> None:
    report = FontCapabilityBuilder.build(roboto, preferred_languages=("en",))

    axis_map = {a.tag: a for a in report.axes}
    wght = axis_map.get("wght")
    if wght:
        desc = wght.default_description
        assert "400" in desc


def test_capability_report_to_dict(roboto) -> None:
    report = FontCapabilityBuilder.build(roboto, preferred_languages=("en",))

    result = report.to_dict()

    assert result["kind"] == "font_capability_report"
    assert "font_identity" in result
    assert "axes" in result
    assert "coverage" in result
    assert "css_hints" in result
    assert "release_risks" in result
    assert "summaries" in result


def test_capability_report_to_json(roboto) -> None:
    report = FontCapabilityBuilder.build(roboto, preferred_languages=("en",))

    json_str = report.to_json(indent=2)
    parsed = json.loads(json_str)

    assert parsed["kind"] == "font_capability_report"
    assert parsed["font_identity"]["font_family"] == "Roboto"


def test_variable_axes_only_common_axes(roboto) -> None:
    report = FontCapabilityBuilder.build(roboto, preferred_languages=("en",))

    axis_tags = [a.tag for a in report.axes]
    for tag in axis_tags:
        assert tag in ("wght", "wdth", "ital", "slnt", "opsz")


def test_static_font_has_empty_axes(opensans_cff) -> None:
    report = FontCapabilityBuilder.build(opensans_cff, preferred_languages=("en",))

    assert len(report.axes) == 0


def test_script_coverage_has_unicode_ranges(roboto) -> None:
    report = FontCapabilityBuilder.build(roboto, preferred_languages=("en",))

    latin = next((c for c in report.coverage if c.script_family == "latin"), None)
    if latin:
        assert len(latin.unicode_ranges) > 0
        assert isinstance(latin.unicode_ranges[0], tuple)
        assert len(latin.unicode_ranges[0]) == 2


def test_script_coverage_counts_match(roboto) -> None:
    report = FontCapabilityBuilder.build(roboto, preferred_languages=("en",))

    for cov in report.coverage:
        if cov.requested_count > 0:
            assert cov.covered_count <= cov.requested_count
            assert cov.percentage <= 100.0


def test_css_hints_format_value(roboto) -> None:
    report = FontCapabilityBuilder.build(roboto, preferred_languages=("en",))

    css = report.css_hints
    assert isinstance(css.font_display, str)
    assert css.font_display in ("auto", "block", "swap", "optional")


def test_multiple_common_scripts_in_coverage(roboto) -> None:
    report = FontCapabilityBuilder.build(roboto, preferred_languages=("en",))

    script_families = [c.script_family for c in report.coverage]
    assert "latin" in script_families
    assert "latin-ext" in script_families


def test_releases_risk_severity_values(roboto) -> None:
    report = FontCapabilityBuilder.build(roboto, preferred_languages=("en",))

    for risk in report.release_risks:
        assert isinstance(risk, ReleaseRisk)
        assert risk.severity in ("blocker", "warning", "info")


def test_capability_report_with_single_language_string(roboto) -> None:
    report = FontCapabilityBuilder.build(roboto, preferred_languages="en")

    assert len(report.axes) > 0
    assert report.font_identity["font_family"] == "Roboto"


def test_capability_report_with_multiple_languages(roboto) -> None:
    report = FontCapabilityBuilder.build(roboto, preferred_languages=("en", "de", "fr"))

    assert len(report.axes) > 0
    assert report.font_identity["font_family"] == "Roboto"
