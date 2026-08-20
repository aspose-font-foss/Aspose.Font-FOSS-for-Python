"""Tests for variable-font compatibility checking."""

from __future__ import annotations

import json
from dataclasses import dataclass

from aspose_font import (
    ActiveTupleSummary,
    CompatibilityChecker,
    Font,
    FontEncoding,
    FontMetrics,
    Glyph,
    GlyphAccessor,
    GlyphCompatibilityIssue,
    GlyphId,
    GlyphInterpolationIssue,
    GlyphOutlineStats,
    GlyphPath,
    LineTo,
    MoveTo,
    QuadraticTo,
    TtfFont,
    TupleScalarDelta,
)
from aspose_font._font_base import FontType


class _StubEncoding(FontEncoding):
    def __init__(self, mapping: dict[int, int]) -> None:
        self._mapping = mapping

    def unicode_to_gid(self, codepoint: int) -> GlyphId:
        return GlyphId(self._mapping[codepoint])

    def get_all_codepoints(self) -> list[int]:
        return sorted(self._mapping)


class _StubGlyphAccessor(GlyphAccessor):
    def __init__(self, glyphs: dict[int, Glyph], encoding: FontEncoding) -> None:
        super().__init__(encoding)
        self._glyphs = glyphs

    def get_glyph_by_id(self, gid: GlyphId) -> Glyph:
        return self._glyphs[int(gid)]

    def get_all_glyph_ids(self) -> list[GlyphId]:
        return [GlyphId(gid) for gid in sorted(self._glyphs)]


@dataclass
class _StubFont(Font):
    _glyphs: dict[int, Glyph]
    _encoding_impl: FontEncoding

    @property
    def font_type(self) -> FontType:
        return FontType.TTF

    @property
    def font_name(self) -> str:
        return "Stub"

    @property
    def font_family(self) -> str:
        return "Stub"

    @property
    def font_style(self) -> str:
        return "Regular"

    @property
    def num_glyphs(self) -> int:
        return len(self._glyphs)

    @property
    def metrics(self) -> FontMetrics:
        return FontMetrics(1000, 800, -200, 200, 1000, -75, 50)

    @property
    def encoding(self) -> FontEncoding:
        return self._encoding_impl

    @property
    def glyph_accessor(self) -> GlyphAccessor:
        return _StubGlyphAccessor(self._glyphs, self._encoding_impl)


def _glyph(gid: int, *commands) -> Glyph:
    path = GlyphPath(list(commands))
    return Glyph(glyph_id=GlyphId(gid), glyph_name=f"g{gid}", path=path, advance_width=500, lsb=0)


def test_variable_instance_compatibility_report_is_green_for_roboto(roboto: TtfFont) -> None:
    report = roboto.smart_instancer.check_compatibility(
        before_instance_name="Regular",
        after_instance_name="Condensed Bold",
        text="Aspose",
    )
    assert report.before_label == "Regular"
    assert report.after_label == "Condensed Bold"
    assert report.compared_glyphs == len({ord(ch) for ch in "Aspose"})
    assert report.is_compatible is True
    assert report.issues == ()
    assert report.before_normalized_coordinates == {"wdth": 0.0, "wght": 0.0}
    assert report.after_normalized_coordinates["wdth"] < 0.0
    assert report.after_normalized_coordinates["wght"] > 0.0
    assert len(report.interpolation_issues) >= 1
    assert report.interpolation_issues[0].reason == "variation tuples became active"
    assert report.interpolation_issues[0].before_active == ()
    assert len(report.interpolation_issues[0].after_active) >= 1
    assert report.to_dict()["is_compatible"] is True
    assert report.to_dict()["interpolation_issue_count"] >= 1


def test_compare_fonts_reports_topology_issue() -> None:
    encoding = _StubEncoding({ord("A"): 1})
    before_font = _StubFont(
        _glyphs={
            1: _glyph(1, MoveTo(0, 0), QuadraticTo(10, 20, 30, 40)),
        },
        _encoding_impl=encoding,
    )
    after_font = _StubFont(
        _glyphs={
            1: _glyph(1, MoveTo(0, 0), MoveTo(5, 5)),
        },
        _encoding_impl=encoding,
    )
    report = CompatibilityChecker.compare_fonts(
        before_font,
        after_font,
        before_label="One",
        after_label="Two",
        text="A",
    )
    assert report.is_compatible is False
    assert report.compared_glyphs == 1
    assert len(report.issues) == 1
    assert report.issues[0].codepoint == ord("A")
    assert report.issues[0].reason == "contour count differs"
    assert "quadratic segments 1->0" in report.issues[0].geometry_notes
    assert "open/closed contours 1/0->2/0" in report.issues[0].geometry_notes
    assert report.issues[0].before_signature == ("M", "Q")
    assert report.issues[0].after_signature == ("M", "M")
    assert report.issues[0].before_stats.command_count == 2
    assert report.issues[0].before_stats.point_count == 3
    assert report.issues[0].before_stats.contour_count == 1
    assert report.issues[0].before_stats.advance_width == 500
    assert report.issues[0].before_stats.quadratic_count == 1
    assert report.issues[0].before_stats.control_point_count == 1
    assert report.issues[0].before_stats.closed_contour_count == 0
    assert report.issues[0].before_stats.open_contour_count == 1
    assert report.issues[0].before_stats.start_point == (0, 0)
    assert report.issues[0].before_stats.end_point == (30, 40)
    assert report.issues[0].before_stats.bbox == (0, 0, 30, 40)
    assert report.issues[0].after_stats.command_count == 2
    assert report.issues[0].after_stats.point_count == 2
    assert report.issues[0].after_stats.contour_count == 2
    assert report.issues[0].after_stats.advance_width == 500
    assert report.issues[0].after_stats.quadratic_count == 0
    assert report.issues[0].after_stats.control_point_count == 0
    assert report.issues[0].after_stats.closed_contour_count == 0
    assert report.issues[0].after_stats.open_contour_count == 2
    assert report.issues[0].after_stats.start_point == (0, 0)
    assert report.issues[0].after_stats.end_point == (5, 5)
    assert report.issues[0].after_stats.bbox == (0, 0, 5, 5)
    issue_dict = report.issues[0].to_dict()
    assert issue_dict["before_stats"] == {
        "command_count": 2,
        "point_count": 3,
        "contour_count": 1,
        "advance_width": 500,
        "line_count": 0,
        "quadratic_count": 1,
        "cubic_count": 0,
        "control_point_count": 1,
        "closed_contour_count": 0,
        "open_contour_count": 1,
        "start_point": [0.0, 0.0],
        "end_point": [30.0, 40.0],
        "bbox": [0.0, 0.0, 30.0, 40.0],
    }
    assert issue_dict["geometry_notes"] == [
        "quadratic segments 1->0",
        "control points 1->0",
        "open/closed contours 1/0->2/0",
        "bbox size 30,40->5,5",
        "end point 30,40->5,5",
    ]
    assert issue_dict["before_stats"]["line_count"] == 0
    assert issue_dict["after_stats"]["line_count"] == 0


def test_compare_fonts_reports_point_count_issue_when_contours_match() -> None:
    encoding = _StubEncoding({ord("B"): 2})
    before_font = _StubFont(
        _glyphs={
            2: _glyph(2, MoveTo(0, 0), QuadraticTo(10, 20, 30, 40)),
        },
        _encoding_impl=encoding,
    )
    after_font = _StubFont(
        _glyphs={
            2: _glyph(2, MoveTo(0, 0), LineTo(30, 40)),
        },
        _encoding_impl=encoding,
    )
    report = CompatibilityChecker.compare_fonts(
        before_font,
        after_font,
        text="B",
    )
    assert report.is_compatible is False
    assert report.issues[0].reason == "point count differs"
    assert "line segments 0->1" in report.issues[0].geometry_notes
    assert "quadratic segments 1->0" in report.issues[0].geometry_notes
    assert "control points 1->0" in report.issues[0].geometry_notes


def test_compare_fonts_same_signature_keeps_compatibility_semantics() -> None:
    encoding = _StubEncoding({ord("C"): 3})
    before_font = _StubFont(
        _glyphs={
            3: _glyph(3, MoveTo(0, 0), LineTo(40, 0), LineTo(40, 50)),
        },
        _encoding_impl=encoding,
    )
    after_font = _StubFont(
        _glyphs={
            3: Glyph(
                glyph_id=GlyphId(3),
                glyph_name="g3",
                path=GlyphPath([MoveTo(10, 10), LineTo(80, 10), LineTo(80, 90)]),
                advance_width=650,
                lsb=0,
            ),
        },
        _encoding_impl=encoding,
    )

    report = CompatibilityChecker.compare_fonts(before_font, after_font, text="C")

    assert report.is_compatible is True
    assert report.issues == ()
    assert report.interpolation_issues == ()


def test_compatibility_report_write_json(tmp_path) -> None:
    encoding = _StubEncoding({ord("A"): 1})
    before_font = _StubFont(
        _glyphs={
            1: _glyph(1, MoveTo(0, 0), QuadraticTo(10, 20, 30, 40)),
        },
        _encoding_impl=encoding,
    )
    after_font = _StubFont(
        _glyphs={
            1: _glyph(1, MoveTo(0, 0), LineTo(30, 40)),
        },
        _encoding_impl=encoding,
    )
    report = CompatibilityChecker.compare_fonts(before_font, after_font, text="A")
    out = tmp_path / "compatibility-report.json"

    report.write_json(out)

    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["before_label"] == "Before"
    assert payload["after_label"] == "After"
    assert payload["is_compatible"] is False
    assert payload["issues"][0]["reason"] == "point count differs"
    assert payload["interpolation_issues"] == []
    assert payload["issues"][0]["geometry_notes"] == [
        "line segments 0->1",
        "quadratic segments 1->0",
        "control points 1->0",
    ]


def test_glyph_compatibility_issue_to_dict_includes_geometry_notes() -> None:
    issue = GlyphCompatibilityIssue(
        codepoint=ord("A"),
        character="A",
        reason="command topology differs",
        geometry_notes=("line segments 1->2", "bbox size 20,30->40,60"),
        before_signature=("M", "L"),
        after_signature=("M", "L", "L"),
        before_stats=GlyphOutlineStats(
            command_count=2,
            point_count=2,
            contour_count=1,
            advance_width=500,
            line_count=1,
            quadratic_count=0,
            cubic_count=0,
            control_point_count=0,
            closed_contour_count=0,
            open_contour_count=1,
            start_point=(0.0, 0.0),
            end_point=(20.0, 30.0),
            bbox=(0.0, 0.0, 20.0, 30.0),
        ),
        after_stats=GlyphOutlineStats(
            command_count=3,
            point_count=3,
            contour_count=1,
            advance_width=500,
            line_count=2,
            quadratic_count=0,
            cubic_count=0,
            control_point_count=0,
            closed_contour_count=0,
            open_contour_count=1,
            start_point=(0.0, 0.0),
            end_point=(40.0, 60.0),
            bbox=(0.0, 0.0, 40.0, 60.0),
        ),
    )

    payload = issue.to_dict()

    assert payload["geometry_notes"] == [
        "line segments 1->2",
        "bbox size 20,30->40,60",
    ]


def test_glyph_interpolation_issue_to_dict_includes_scalar_changes() -> None:
    issue = GlyphInterpolationIssue(
        codepoint=ord("A"),
        character="A",
        reason="active variation tuples changed",
        before_active=(
            ActiveTupleSummary(
                tuple_index=1,
                scalar=0.5,
                peak_coords={"wght": 1.0},
                start_coords=None,
                end_coords=None,
            ),
        ),
        after_active=(
            ActiveTupleSummary(
                tuple_index=1,
                scalar=0.75,
                peak_coords={"wght": 1.0},
                start_coords=None,
                end_coords=None,
            ),
            ActiveTupleSummary(
                tuple_index=2,
                scalar=1.0,
                peak_coords={"wdth": -1.0},
                start_coords=None,
                end_coords=None,
            ),
        ),
        entered_tuple_indices=(2,),
        exited_tuple_indices=(),
        retuned_tuples=(
            TupleScalarDelta(tuple_index=1, before_scalar=0.5, after_scalar=0.75),
        ),
    )

    payload = issue.to_dict()

    assert payload["entered_tuple_indices"] == [2]
    assert payload["exited_tuple_indices"] == []
    assert payload["retuned_tuples"] == [
        {
            "tuple_index": 1,
            "before_scalar": 0.5,
            "after_scalar": 0.75,
        }
    ]
