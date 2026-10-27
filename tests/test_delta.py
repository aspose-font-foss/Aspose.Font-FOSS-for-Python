"""Tests for variable-font delta inspection (SPEC-056 / ADR-048 / FONT-60)."""

from __future__ import annotations

import pytest

from aspose_font import (
    DeltaInspector,
    GlyphDeltaComparisonReport,
    GlyphDeltaReport,
    PreviewImage,
    TextDeltaComparisonReport,
    TextDeltaReport,
    TtfFont,
)
from aspose_font.preview import _decode_png_rgb


def test_delta_inspector_reports_active_tuples_for_bold_a(roboto: TtfFont) -> None:
    report = DeltaInspector.inspect_variable_glyph(
        roboto,
        codepoint=ord("A"),
        instance_name="Bold",
        top_points=3,
    )
    assert isinstance(report, GlyphDeltaReport)
    assert report.codepoint == ord("A")
    assert report.character == "A"
    assert report.instance_label == "Bold"
    assert report.is_supported is True
    assert report.point_count > 0
    assert report.contour_count > 0
    assert report.total_tuple_count >= len(report.active_tuples) >= 1
    assert len(report.strongest_points) >= 1
    assert report.active_tuples[0].scalar != 0.0
    assert len(report.active_tuples[0].top_points) <= 3
    assert report.active_tuples[0].referenced_outline_points >= 1
    assert report.active_tuples[0].referenced_phantom_points >= 0
    assert report.strongest_points[0].magnitude >= report.strongest_points[-1].magnitude


def test_smart_instancer_inspect_deltas_accepts_gid(roboto: TtfFont) -> None:
    gid = int(roboto.encoding.unicode_to_gid(ord("A")))
    report = roboto.smart_instancer.inspect_deltas(
        glyph_id=gid,
        coordinates={"wght": 700.0, "wdth": 75.0},
        top_points=2,
    )
    payload = report.to_dict()
    assert payload["glyph_id"] == gid
    assert payload["instance_label"] == "Condensed Bold"
    assert payload["active_tuple_count"] >= 1
    assert payload["strongest_points"]
    assert len(payload["active_tuples"][0]["top_points"]) <= 2
    assert "referenced_outline_points" in payload["active_tuples"][0]
    assert "referenced_phantom_points" in payload["active_tuples"][0]


def test_delta_inspector_requires_target_selector(roboto: TtfFont) -> None:
    with pytest.raises(ValueError, match="requires glyph_id or codepoint"):
        DeltaInspector.inspect_variable_glyph(roboto, instance_name="Bold")


def test_delta_inspector_builds_visual_sheet(roboto: TtfFont) -> None:
    preview = DeltaInspector.build_delta_sheet(
        roboto,
        codepoint=ord("A"),
        instance_name="Bold",
        top_points=3,
    )
    assert isinstance(preview, PreviewImage)
    assert preview.filename == "delta-sheet.png"
    assert preview.data.startswith(b"\x89PNG\r\n\x1a\n")
    _width, _height, pixels = _decode_png_rgb(preview.data)
    triplets = {
        tuple(pixels[index:index + 3])
        for index in range(0, len(pixels), 3)
    }
    assert (198, 109, 42) in triplets
    assert (71, 126, 199) in triplets
    assert (184, 66, 53) in triplets
    assert (214, 207, 194) in triplets
    assert (232, 170, 116) in triplets
    assert (146, 180, 230) in triplets


def test_delta_inspector_reports_text_sample(roboto: TtfFont) -> None:
    report = DeltaInspector.inspect_variable_text(
        roboto,
        text="ABA",
        instance_name="Bold",
        top_points=2,
    )
    assert isinstance(report, TextDeltaReport)
    assert report.text == "ABA"
    assert report.instance_label == "Bold"
    assert report.glyph_count == 2
    assert report.active_glyph_count >= 1
    assert report.supported_glyph_count == report.glyph_count
    assert [glyph.character for glyph in report.glyph_reports] == ["A", "B"]


def test_delta_inspector_supports_composite_glyph_outlines(roboto: TtfFont) -> None:
    report = DeltaInspector.inspect_variable_glyph(
        roboto,
        codepoint=ord("Á"),
        instance_name="Bold",
        top_points=3,
    )
    assert isinstance(report, GlyphDeltaReport)
    assert report.character == "Á"
    assert report.is_supported is True
    assert report.contour_count > 0
    assert report.point_count > 0
    assert report.composite_components
    assert report.composite_components[0].glyph_id > 0
    assert report.component_movements
    assert report.component_movements[0].glyph_id == report.composite_components[0].glyph_id
    assert report.component_movements[0].active_tuple_count >= 0
    assert report.component_movements[0].shift_magnitude >= 0.0
    assert report.component_movements[0].local_strongest_magnitude >= 0.0
    assert any(item.referenced_phantom_points >= 0 for item in report.active_tuples)
    assert report.note is not None
    assert "child glyph delta analysis" in report.note


def test_composite_component_movement_payload_includes_component_aware_fields(roboto: TtfFont) -> None:
    report = DeltaInspector.inspect_variable_glyph(
        roboto,
        codepoint=ord("Á"),
        instance_name="Bold",
        top_points=3,
    )

    payload = report.to_dict()
    movement = payload["component_movements"][0]
    assert "active_tuple_count" in movement
    assert "local_strongest_point_index" in movement
    assert "local_strongest_magnitude" in movement
    assert "shift_magnitude" in movement
    assert "transform_changed" in movement


def test_delta_inspector_builds_text_visual_sheet(roboto: TtfFont) -> None:
    preview = DeltaInspector.build_delta_text_sheet(
        roboto,
        text="ABA",
        instance_name="Bold",
        top_points=2,
        columns=2,
    )
    assert isinstance(preview, PreviewImage)
    assert preview.filename == "delta-text-sheet.png"
    assert preview.data.startswith(b"\x89PNG\r\n\x1a\n")
    _width, _height, pixels = _decode_png_rgb(preview.data)
    triplets = {
        tuple(pixels[index:index + 3])
        for index in range(0, len(pixels), 3)
    }
    assert (198, 109, 42) in triplets
    assert (71, 126, 199) in triplets
    assert (184, 66, 53) in triplets


def test_delta_inspector_builds_composite_visual_sheet(roboto: TtfFont) -> None:
    preview = DeltaInspector.build_delta_sheet(
        roboto,
        codepoint=ord("Á"),
        instance_name="Bold",
        top_points=3,
    )
    assert isinstance(preview, PreviewImage)
    assert preview.data.startswith(b"\x89PNG\r\n\x1a\n")
    _width, _height, pixels = _decode_png_rgb(preview.data)
    triplets = {
        tuple(pixels[index:index + 3])
        for index in range(0, len(pixels), 3)
    }
    assert (198, 109, 42) in triplets
    assert (71, 126, 199) in triplets


def test_delta_inspector_builds_comparison_sheet(roboto: TtfFont) -> None:
    preview = DeltaInspector.build_delta_comparison_sheet(
        roboto,
        codepoint=ord("A"),
        before_instance_name="Regular",
        after_instance_name="Condensed Bold",
        top_points=3,
    )
    assert isinstance(preview, PreviewImage)
    assert preview.filename == "delta-compare-sheet.png"
    assert preview.data.startswith(b"\x89PNG\r\n\x1a\n")
    _width, _height, pixels = _decode_png_rgb(preview.data)
    triplets = {
        tuple(pixels[index:index + 3])
        for index in range(0, len(pixels), 3)
    }
    assert (198, 109, 42) in triplets
    assert (71, 126, 199) in triplets
    assert (184, 66, 53) in triplets
    assert (214, 207, 194) in triplets
    assert (232, 170, 116) in triplets
    assert (146, 180, 230) in triplets


def test_delta_inspector_reports_comparison_summary(roboto: TtfFont) -> None:
    report = DeltaInspector.compare_variable_glyph(
        roboto,
        codepoint=ord("A"),
        before_instance_name="Regular",
        after_instance_name="Condensed Bold",
        top_points=3,
    )
    assert isinstance(report, GlyphDeltaComparisonReport)
    assert report.codepoint == ord("A")
    assert report.before.instance_label == "Regular"
    assert report.after.instance_label == "Condensed Bold"
    assert report.is_comparable is True
    assert report.moved_point_count >= 1
    assert len(report.comparison_points) <= 3
    assert report.comparison_points[0].magnitude >= report.comparison_points[-1].magnitude
    payload = report.to_dict()
    assert payload["moved_point_count"] >= 1
    assert payload["before"]["instance_label"] == "Regular"
    assert payload["after"]["instance_label"] == "Condensed Bold"


def test_delta_inspector_reports_text_comparison_summary(roboto: TtfFont) -> None:
    report = DeltaInspector.compare_variable_text(
        roboto,
        text="ABA",
        before_instance_name="Regular",
        after_instance_name="Condensed Bold",
        top_points=2,
    )
    assert isinstance(report, TextDeltaComparisonReport)
    assert report.text == "ABA"
    assert report.before_label == "Regular"
    assert report.after_label == "Condensed Bold"
    assert report.glyph_count == 2
    assert report.comparable_glyph_count >= 1
    assert report.moved_glyph_count >= 1
    assert [item.character for item in report.glyph_comparisons] == ["A", "B"]
    payload = report.to_dict()
    assert payload["before_label"] == "Regular"
    assert payload["after_label"] == "Condensed Bold"
    assert payload["glyph_count"] == 2
    assert payload["moved_glyph_count"] >= 1


def test_delta_inspector_builds_text_comparison_sheet(roboto: TtfFont) -> None:
    preview = DeltaInspector.build_delta_text_comparison_sheet(
        roboto,
        text="ABA",
        before_instance_name="Regular",
        after_instance_name="Condensed Bold",
        top_points=2,
        columns=2,
    )
    assert isinstance(preview, PreviewImage)
    assert preview.filename == "delta-text-compare-sheet.png"
    assert preview.data.startswith(b"\x89PNG\r\n\x1a\n")
    _width, _height, pixels = _decode_png_rgb(preview.data)
    triplets = {
        tuple(pixels[index:index + 3])
        for index in range(0, len(pixels), 3)
    }
    assert (198, 109, 42) in triplets
    assert (71, 126, 199) in triplets
    assert (184, 66, 53) in triplets
    assert (214, 207, 194) in triplets
    assert (232, 170, 116) in triplets
    assert (146, 180, 230) in triplets


def test_delta_text_inspection_requires_non_empty_text(roboto: TtfFont) -> None:
    with pytest.raises(ValueError, match="requires non-empty text"):
        DeltaInspector.inspect_variable_text(
            roboto,
            text="",
            instance_name="Bold",
        )

    with pytest.raises(ValueError, match="requires non-empty text"):
        DeltaInspector.compare_variable_text(
            roboto,
            text="",
            before_instance_name="Regular",
            after_instance_name="Bold",
        )


def test_delta_text_sheet_requires_columns_ge_one(roboto: TtfFont) -> None:
    with pytest.raises(ValueError, match="columns >= 1"):
        DeltaInspector.build_delta_text_sheet(
            roboto,
            text="AB",
            instance_name="Bold",
            columns=0,
        )

    with pytest.raises(ValueError, match="columns >= 1"):
        DeltaInspector.build_delta_text_comparison_sheet(
            roboto,
            text="AB",
            before_instance_name="Regular",
            after_instance_name="Bold",
            columns=0,
        )
