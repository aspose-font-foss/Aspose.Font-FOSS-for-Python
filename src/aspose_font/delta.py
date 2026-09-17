"""Variable-font delta inspection helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from math import hypot

from aspose_font._exceptions import FontNotSupportedException, GlyphNotFoundException
from aspose_font._io import BinaryReader
from aspose_font._types import ClosePath, CurveTo, GlyphPath, LineTo, MoveTo, QuadraticTo
from aspose_font.preview import FontPreviewBuilder, PreviewImage, _draw_bitmap_text
from aspose_font.rasterizer import Rasterizer
from aspose_font.ttf.instancer import TtfInstancer
from aspose_font.ttf.tables.avar import AvarTable
from aspose_font.ttf.tables.gvar import GvarTable, TupleVariation

_PANEL_BACKGROUND = (255, 253, 248)
_DEFAULT_COLOR = (198, 109, 42)
_RESOLVED_COLOR = (71, 126, 199)
_ARROW_COLOR = (184, 66, 53)
_MARKER_OUTLINE = (68, 60, 50)
_GUIDE_COLOR = (214, 207, 194)
_DEFAULT_POINT_COLOR = (232, 170, 116)
_RESOLVED_POINT_COLOR = (146, 180, 230)
_ARG_1_AND_2_ARE_WORDS = 0x0001
_ARGS_ARE_XY_VALUES = 0x0002
_WE_HAVE_A_SCALE = 0x0008
_MORE_COMPONENTS = 0x0020
_WE_HAVE_AN_X_AND_Y_SCALE = 0x0040
_WE_HAVE_A_TWO_BY_TWO = 0x0080


@dataclass(slots=True, frozen=True)
class DeltaPoint:
    index: int
    dx: float
    dy: float
    magnitude: float

    def to_dict(self) -> dict[str, float | int]:
        return {
            "index": self.index,
            "dx": float(self.dx),
            "dy": float(self.dy),
            "magnitude": float(self.magnitude),
        }


@dataclass(slots=True, frozen=True)
class DeltaTupleReport:
    tuple_index: int
    scalar: float
    peak_coords: dict[str, float]
    start_coords: dict[str, float] | None
    end_coords: dict[str, float] | None
    referenced_points: int
    referenced_outline_points: int
    referenced_phantom_points: int
    non_zero_points: int
    non_zero_outline_points: int
    non_zero_phantom_points: int
    max_abs_dx: float
    max_abs_dy: float
    total_abs_dx: float
    total_abs_dy: float
    top_points: tuple[DeltaPoint, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, object]:
        return {
            "tuple_index": self.tuple_index,
            "scalar": float(self.scalar),
            "peak_coords": dict(self.peak_coords),
            "start_coords": None if self.start_coords is None else dict(self.start_coords),
            "end_coords": None if self.end_coords is None else dict(self.end_coords),
            "referenced_points": self.referenced_points,
            "referenced_outline_points": self.referenced_outline_points,
            "referenced_phantom_points": self.referenced_phantom_points,
            "non_zero_points": self.non_zero_points,
            "non_zero_outline_points": self.non_zero_outline_points,
            "non_zero_phantom_points": self.non_zero_phantom_points,
            "max_abs_dx": float(self.max_abs_dx),
            "max_abs_dy": float(self.max_abs_dy),
            "total_abs_dx": float(self.total_abs_dx),
            "total_abs_dy": float(self.total_abs_dy),
            "top_points": [point.to_dict() for point in self.top_points],
        }


@dataclass(slots=True, frozen=True)
class CompositeGlyphComponent:
    glyph_id: int
    dx: float
    dy: float
    xx: float
    yx: float
    xy: float
    yy: float

    def to_dict(self) -> dict[str, float | int]:
        return {
            "glyph_id": self.glyph_id,
            "dx": float(self.dx),
            "dy": float(self.dy),
            "xx": float(self.xx),
            "yx": float(self.yx),
            "xy": float(self.xy),
            "yy": float(self.yy),
        }


@dataclass(slots=True, frozen=True)
class CompositeComponentMovement:
    component_index: int
    glyph_id: int
    point_count: int
    strongest_point_index: int | None
    strongest_magnitude: float
    total_abs_dx: float
    total_abs_dy: float
    active_tuple_count: int = 0
    local_strongest_point_index: int | None = None
    local_strongest_magnitude: float = 0.0
    shift_magnitude: float = 0.0
    transform_changed: bool = False
    note: str | None = None

    def to_dict(self) -> dict[str, float | int | bool | None]:
        return {
            "component_index": self.component_index,
            "glyph_id": self.glyph_id,
            "point_count": self.point_count,
            "strongest_point_index": self.strongest_point_index,
            "strongest_magnitude": float(self.strongest_magnitude),
            "total_abs_dx": float(self.total_abs_dx),
            "total_abs_dy": float(self.total_abs_dy),
            "active_tuple_count": self.active_tuple_count,
            "local_strongest_point_index": self.local_strongest_point_index,
            "local_strongest_magnitude": float(self.local_strongest_magnitude),
            "shift_magnitude": float(self.shift_magnitude),
            "transform_changed": self.transform_changed,
            "note": self.note,
        }


@dataclass(slots=True, frozen=True)
class GlyphDeltaReport:
    glyph_id: int
    glyph_name: str | None
    codepoint: int | None
    character: str
    instance_label: str
    coordinates: dict[str, float]
    normalized_coordinates: dict[str, float]
    total_tuple_count: int
    active_tuples: tuple[DeltaTupleReport, ...] = field(default_factory=tuple)
    strongest_points: tuple[DeltaPoint, ...] = field(default_factory=tuple)
    composite_components: tuple[CompositeGlyphComponent, ...] = field(default_factory=tuple)
    component_movements: tuple[CompositeComponentMovement, ...] = field(default_factory=tuple)
    point_count: int = 0
    contour_count: int = 0
    is_supported: bool = True
    note: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "glyph_id": self.glyph_id,
            "glyph_name": self.glyph_name,
            "codepoint": self.codepoint,
            "character": self.character,
            "instance_label": self.instance_label,
            "coordinates": dict(self.coordinates),
            "normalized_coordinates": dict(self.normalized_coordinates),
            "total_tuple_count": self.total_tuple_count,
            "active_tuple_count": len(self.active_tuples),
            "strongest_points": [point.to_dict() for point in self.strongest_points],
            "composite_components": [component.to_dict() for component in self.composite_components],
            "component_movements": [movement.to_dict() for movement in self.component_movements],
            "point_count": self.point_count,
            "contour_count": self.contour_count,
            "is_supported": self.is_supported,
            "note": self.note,
            "active_tuples": [item.to_dict() for item in self.active_tuples],
        }


@dataclass(slots=True, frozen=True)
class TextDeltaReport:
    text: str
    instance_label: str
    coordinates: dict[str, float]
    normalized_coordinates: dict[str, float]
    glyph_reports: tuple[GlyphDeltaReport, ...] = field(default_factory=tuple)

    @property
    def glyph_count(self) -> int:
        return len(self.glyph_reports)

    @property
    def active_glyph_count(self) -> int:
        return sum(1 for report in self.glyph_reports if report.active_tuples)

    @property
    def supported_glyph_count(self) -> int:
        return sum(1 for report in self.glyph_reports if report.is_supported)

    def to_dict(self) -> dict[str, object]:
        return {
            "text": self.text,
            "instance_label": self.instance_label,
            "coordinates": dict(self.coordinates),
            "normalized_coordinates": dict(self.normalized_coordinates),
            "glyph_count": self.glyph_count,
            "active_glyph_count": self.active_glyph_count,
            "supported_glyph_count": self.supported_glyph_count,
            "glyph_reports": [report.to_dict() for report in self.glyph_reports],
        }


@dataclass(slots=True, frozen=True)
class GlyphDeltaComparisonReport:
    glyph_id: int
    glyph_name: str | None
    codepoint: int | None
    character: str
    before: GlyphDeltaReport
    after: GlyphDeltaReport
    comparison_points: tuple[DeltaPoint, ...] = field(default_factory=tuple)
    note: str | None = None

    @property
    def moved_point_count(self) -> int:
        return len(self.comparison_points)

    @property
    def is_comparable(self) -> bool:
        return self.note is None

    def to_dict(self) -> dict[str, object]:
        return {
            "glyph_id": self.glyph_id,
            "glyph_name": self.glyph_name,
            "codepoint": self.codepoint,
            "character": self.character,
            "before": self.before.to_dict(),
            "after": self.after.to_dict(),
            "moved_point_count": self.moved_point_count,
            "is_comparable": self.is_comparable,
            "comparison_points": [point.to_dict() for point in self.comparison_points],
            "note": self.note,
        }


@dataclass(slots=True, frozen=True)
class TextDeltaComparisonReport:
    text: str
    before_label: str
    after_label: str
    before_coordinates: dict[str, float]
    after_coordinates: dict[str, float]
    before_normalized_coordinates: dict[str, float]
    after_normalized_coordinates: dict[str, float]
    glyph_comparisons: tuple[GlyphDeltaComparisonReport, ...] = field(default_factory=tuple)

    @property
    def glyph_count(self) -> int:
        return len(self.glyph_comparisons)

    @property
    def comparable_glyph_count(self) -> int:
        return sum(1 for report in self.glyph_comparisons if report.is_comparable)

    @property
    def moved_glyph_count(self) -> int:
        return sum(1 for report in self.glyph_comparisons if report.moved_point_count > 0)

    def to_dict(self) -> dict[str, object]:
        return {
            "text": self.text,
            "before_label": self.before_label,
            "after_label": self.after_label,
            "before_coordinates": dict(self.before_coordinates),
            "after_coordinates": dict(self.after_coordinates),
            "before_normalized_coordinates": dict(self.before_normalized_coordinates),
            "after_normalized_coordinates": dict(self.after_normalized_coordinates),
            "glyph_count": self.glyph_count,
            "comparable_glyph_count": self.comparable_glyph_count,
            "moved_glyph_count": self.moved_glyph_count,
            "glyph_comparisons": [report.to_dict() for report in self.glyph_comparisons],
        }


@dataclass(slots=True, frozen=True)
class _GlyphDeltaAnalysis:
    report: GlyphDeltaReport
    default_label: str
    default_path: GlyphPath | None
    resolved_path: GlyphPath | None
    default_points: tuple[tuple[float, float], ...]
    resolved_points: tuple[tuple[float, float], ...]
    highlight_points: tuple[DeltaPoint, ...]


@dataclass(slots=True, frozen=True)
class _GlyphDeltaComparison:
    before: _GlyphDeltaAnalysis
    after: _GlyphDeltaAnalysis
    report: GlyphDeltaComparisonReport
    comparison_points: tuple[DeltaPoint, ...]
    note: str | None = None


class DeltaInspector:
    @classmethod
    def inspect_variable_glyph(
        cls,
        font,
        *,
        glyph_id: int | None = None,
        codepoint: int | None = None,
        coordinates: dict[str, float] | None = None,
        instance_name: str | None = None,
        top_points: int = 8,
    ) -> GlyphDeltaReport:
        return cls._analyze_glyph(
            font,
            glyph_id=glyph_id,
            codepoint=codepoint,
            coordinates=coordinates,
            instance_name=instance_name,
            top_points=top_points,
        ).report

    @classmethod
    def build_delta_sheet(
        cls,
        font,
        *,
        glyph_id: int | None = None,
        codepoint: int | None = None,
        coordinates: dict[str, float] | None = None,
        instance_name: str | None = None,
        top_points: int = 8,
        panel_size: int = 220,
        file_stem: str = "delta-sheet",
    ) -> PreviewImage:
        analysis = cls._analyze_glyph(
            font,
            glyph_id=glyph_id,
            codepoint=codepoint,
            coordinates=coordinates,
            instance_name=instance_name,
            top_points=top_points,
        )
        title = _delta_title(analysis.report)
        footer_lines = _delta_footer_lines(analysis.report)
        default_panel = _render_glyph_panel(
            analysis.default_path,
            also_path=analysis.resolved_path,
            panel_size=panel_size,
            primary_color=_DEFAULT_COLOR,
            background=_PANEL_BACKGROUND,
            emphasize_primary=True,
        )
        resolved_panel = _render_glyph_panel(
            analysis.resolved_path,
            also_path=analysis.default_path,
            panel_size=panel_size,
            primary_color=_RESOLVED_COLOR,
            background=_PANEL_BACKGROUND,
            emphasize_primary=True,
        )
        overlay_panel = _render_glyph_panel(
            analysis.default_path,
            also_path=analysis.resolved_path,
            panel_size=panel_size,
            primary_color=_DEFAULT_COLOR,
            secondary_color=_RESOLVED_COLOR,
            background=_PANEL_BACKGROUND,
            before_points=analysis.default_points,
            after_points=analysis.resolved_points,
            highlighted_points=analysis.report.strongest_points,
            emphasize_primary=False,
        )
        diagram_panel = _render_glyph_panel(
            analysis.default_path,
            also_path=analysis.resolved_path,
            panel_size=panel_size,
            primary_color=_DEFAULT_COLOR,
            secondary_color=_RESOLVED_COLOR,
            background=_PANEL_BACKGROUND,
            before_points=analysis.default_points,
            after_points=analysis.resolved_points,
            highlighted_points=analysis.report.strongest_points,
            emphasize_primary=False,
            show_point_cloud=True,
            show_guides=True,
        )
        return FontPreviewBuilder.compose_sheet(
            [default_panel, resolved_panel, overlay_panel, diagram_panel],
            columns=4,
            title=title,
            column_headers=["Default", "Resolved", "Overlay", "Diagram"],
            labels=[
                analysis.default_label,
                analysis.report.instance_label,
                _overlay_label(analysis.report),
                _diagram_label(analysis.report),
            ],
            footer_lines=footer_lines,
            background=(255, 253, 248),
            file_stem=file_stem,
        )

    @classmethod
    def compare_variable_glyph(
        cls,
        font,
        *,
        glyph_id: int | None = None,
        codepoint: int | None = None,
        before_coordinates: dict[str, float] | None = None,
        after_coordinates: dict[str, float] | None = None,
        before_instance_name: str | None = None,
        after_instance_name: str | None = None,
        top_points: int = 8,
    ) -> GlyphDeltaComparisonReport:
        return cls._analyze_glyph_comparison(
            font,
            glyph_id=glyph_id,
            codepoint=codepoint,
            before_coordinates=before_coordinates,
            after_coordinates=after_coordinates,
            before_instance_name=before_instance_name,
            after_instance_name=after_instance_name,
            top_points=top_points,
        ).report

    @classmethod
    def inspect_variable_text(
        cls,
        font,
        *,
        text: str,
        coordinates: dict[str, float] | None = None,
        instance_name: str | None = None,
        top_points: int = 8,
    ) -> TextDeltaReport:
        report, _analyses = cls._analyze_text(
            font,
            text=text,
            coordinates=coordinates,
            instance_name=instance_name,
            top_points=top_points,
        )
        return report

    @classmethod
    def compare_variable_text(
        cls,
        font,
        *,
        text: str,
        before_coordinates: dict[str, float] | None = None,
        after_coordinates: dict[str, float] | None = None,
        before_instance_name: str | None = None,
        after_instance_name: str | None = None,
        top_points: int = 8,
    ) -> TextDeltaComparisonReport:
        if not text:
            raise ValueError("Delta text comparison requires non-empty text")
        before_resolved = font.smart_instancer.resolve(
            before_coordinates,
            instance_name=before_instance_name,
        )
        after_resolved = font.smart_instancer.resolve(
            after_coordinates,
            instance_name=after_instance_name,
        )
        glyph_comparisons = tuple(
            cls._analyze_glyph_comparison(
                font,
                codepoint=codepoint,
                before_coordinates=before_coordinates,
                after_coordinates=after_coordinates,
                before_instance_name=before_instance_name,
                after_instance_name=after_instance_name,
                top_points=top_points,
            ).report
            for codepoint in _unique_codepoints_from_text(text)
        )
        before_normalized_coordinates = (
            dict(glyph_comparisons[0].before.normalized_coordinates) if glyph_comparisons else {}
        )
        after_normalized_coordinates = (
            dict(glyph_comparisons[0].after.normalized_coordinates) if glyph_comparisons else {}
        )
        return TextDeltaComparisonReport(
            text=text,
            before_label=before_resolved.label,
            after_label=after_resolved.label,
            before_coordinates=dict(before_resolved.coordinates),
            after_coordinates=dict(after_resolved.coordinates),
            before_normalized_coordinates=before_normalized_coordinates,
            after_normalized_coordinates=after_normalized_coordinates,
            glyph_comparisons=glyph_comparisons,
        )

    @classmethod
    def build_delta_text_sheet(
        cls,
        font,
        *,
        text: str,
        coordinates: dict[str, float] | None = None,
        instance_name: str | None = None,
        top_points: int = 8,
        panel_size: int = 220,
        columns: int = 3,
        file_stem: str = "delta-text-sheet",
    ) -> PreviewImage:
        if columns < 1:
            raise ValueError("Delta text sheet requires columns >= 1")
        report, analyses = cls._analyze_text(
            font,
            text=text,
            coordinates=coordinates,
            instance_name=instance_name,
            top_points=top_points,
        )
        previews = [
            _render_glyph_panel(
                analysis.default_path,
                also_path=analysis.resolved_path,
                panel_size=panel_size,
                primary_color=_DEFAULT_COLOR,
                secondary_color=_RESOLVED_COLOR,
                background=_PANEL_BACKGROUND,
                before_points=analysis.default_points,
                after_points=analysis.resolved_points,
                highlighted_points=analysis.report.strongest_points,
                emphasize_primary=False,
            )
            for analysis in analyses
        ]
        return FontPreviewBuilder.compose_sheet(
            previews,
            columns=min(columns, len(previews)),
            title=_delta_text_title(report),
            labels=[_text_sheet_label(analysis.report) for analysis in analyses],
            footer_lines=_delta_text_footer_lines(report),
            background=_PANEL_BACKGROUND,
            file_stem=file_stem,
        )

    @classmethod
    def build_delta_text_comparison_sheet(
        cls,
        font,
        *,
        text: str,
        before_coordinates: dict[str, float] | None = None,
        after_coordinates: dict[str, float] | None = None,
        before_instance_name: str | None = None,
        after_instance_name: str | None = None,
        top_points: int = 8,
        panel_size: int = 220,
        columns: int = 3,
        file_stem: str = "delta-text-compare-sheet",
    ) -> PreviewImage:
        if columns < 1:
            raise ValueError("Delta text comparison sheet requires columns >= 1")
        report = cls.compare_variable_text(
            font,
            text=text,
            before_coordinates=before_coordinates,
            after_coordinates=after_coordinates,
            before_instance_name=before_instance_name,
            after_instance_name=after_instance_name,
            top_points=top_points,
        )
        comparisons = [
            cls._analyze_glyph_comparison(
                font,
                codepoint=codepoint,
                before_coordinates=before_coordinates,
                after_coordinates=after_coordinates,
                before_instance_name=before_instance_name,
                after_instance_name=after_instance_name,
                top_points=top_points,
            )
            for codepoint in _unique_codepoints_from_text(text)
        ]
        card_panel_size = max(96, panel_size // 2)
        previews = [
            _build_comparison_card(
                comparison,
                panel_size=card_panel_size,
                file_stem=f"delta-text-compare-glyph-{comparison.report.glyph_id}",
            )
            for comparison in comparisons
        ]
        return FontPreviewBuilder.compose_sheet(
            previews,
            columns=min(columns, len(previews)),
            title=_delta_text_comparison_title(report),
            labels=[_text_comparison_sheet_label(item.report) for item in comparisons],
            footer_lines=_delta_text_comparison_footer_lines(report),
            background=_PANEL_BACKGROUND,
            file_stem=file_stem,
        )

    @classmethod
    def build_delta_comparison_sheet(
        cls,
        font,
        *,
        glyph_id: int | None = None,
        codepoint: int | None = None,
        before_coordinates: dict[str, float] | None = None,
        after_coordinates: dict[str, float] | None = None,
        before_instance_name: str | None = None,
        after_instance_name: str | None = None,
        top_points: int = 8,
        panel_size: int = 220,
        file_stem: str = "delta-compare-sheet",
    ) -> PreviewImage:
        comparison = cls._analyze_glyph_comparison(
            font,
            glyph_id=glyph_id,
            codepoint=codepoint,
            before_coordinates=before_coordinates,
            after_coordinates=after_coordinates,
            before_instance_name=before_instance_name,
            after_instance_name=after_instance_name,
            top_points=top_points,
        )
        return _build_comparison_board(
            comparison,
            panel_size=panel_size,
            file_stem=file_stem,
        )

    @classmethod
    def _analyze_text(
        cls,
        font,
        *,
        text: str,
        coordinates: dict[str, float] | None = None,
        instance_name: str | None = None,
        top_points: int = 8,
    ) -> tuple[TextDeltaReport, list[_GlyphDeltaAnalysis]]:
        if not text:
            raise ValueError("Delta text inspection requires non-empty text")
        resolved = font.smart_instancer.resolve(
            coordinates,
            instance_name=instance_name,
        )
        analyses = [
            cls._analyze_glyph(
                font,
                codepoint=codepoint,
                coordinates=coordinates,
                instance_name=instance_name,
                top_points=top_points,
            )
            for codepoint in _unique_codepoints_from_text(text)
        ]
        normalized_coordinates = analyses[0].report.normalized_coordinates if analyses else {}
        report = TextDeltaReport(
            text=text,
            instance_label=resolved.label,
            coordinates=dict(resolved.coordinates),
            normalized_coordinates=dict(normalized_coordinates),
            glyph_reports=tuple(analysis.report for analysis in analyses),
        )
        return report, analyses

    @classmethod
    def _analyze_glyph_comparison(
        cls,
        font,
        *,
        glyph_id: int | None = None,
        codepoint: int | None = None,
        before_coordinates: dict[str, float] | None = None,
        after_coordinates: dict[str, float] | None = None,
        before_instance_name: str | None = None,
        after_instance_name: str | None = None,
        top_points: int = 8,
    ) -> _GlyphDeltaComparison:
        before = cls._analyze_glyph(
            font,
            glyph_id=glyph_id,
            codepoint=codepoint,
            coordinates=before_coordinates,
            instance_name=before_instance_name,
            top_points=top_points,
        )
        after = cls._analyze_glyph(
            font,
            glyph_id=glyph_id,
            codepoint=codepoint,
            coordinates=after_coordinates,
            instance_name=after_instance_name,
            top_points=top_points,
        )
        note: str | None = None
        comparison_points: tuple[DeltaPoint, ...] = ()
        if not before.report.is_supported or not after.report.is_supported:
            note = "comparative delta workflows currently require supported outline-derived delta data"
        elif len(before.resolved_points) != len(after.resolved_points):
            note = "comparative delta workflows require matching point counts"
        else:
            diff_dx = [
                after_point[0] - before_point[0]
                for before_point, after_point in zip(before.resolved_points, after.resolved_points)
            ]
            diff_dy = [
                after_point[1] - before_point[1]
                for before_point, after_point in zip(before.resolved_points, after.resolved_points)
            ]
            comparison_points = _top_total_points(diff_dx, diff_dy, top_points)
        report = GlyphDeltaComparisonReport(
            glyph_id=before.report.glyph_id,
            glyph_name=before.report.glyph_name,
            codepoint=before.report.codepoint,
            character=before.report.character,
            before=before.report,
            after=after.report,
            comparison_points=comparison_points,
            note=note,
        )
        return _GlyphDeltaComparison(
            before=before,
            after=after,
            report=report,
            comparison_points=comparison_points,
            note=note,
        )

    @classmethod
    def _analyze_glyph(
        cls,
        font,
        *,
        glyph_id: int | None = None,
        codepoint: int | None = None,
        coordinates: dict[str, float] | None = None,
        instance_name: str | None = None,
        top_points: int = 8,
    ) -> _GlyphDeltaAnalysis:
        if not hasattr(font, "smart_instancer") or not getattr(font, "is_variable", False):
            raise FontNotSupportedException("Delta inspection requires a variable TTF font")
        resolved = font.smart_instancer.resolve(
            coordinates,
            instance_name=instance_name,
        )
        default_resolved = font.smart_instancer.resolve()
        target_gid, resolved_codepoint = _resolve_glyph_target(
            font,
            glyph_id=glyph_id,
            codepoint=codepoint,
        )
        glyph_name = None
        try:
            glyph = font.glyph_accessor.get_glyph_by_id(target_gid)
            glyph_name = glyph.glyph_name
        except GlyphNotFoundException:
            glyph = None
        axis_tags = [axis.tag for axis in font.axes]
        normalized = TtfInstancer._normalized_coordinates(font, resolved.coordinates)
        avar_raw = font.ttf_tables._raw.get("avar")
        if avar_raw is not None:
            avar = AvarTable.from_reader(BinaryReader(avar_raw), len(avar_raw))
            normalized = {
                axis_tags[index]: avar.map_normalized(index, normalized[axis_tags[index]])
                for index in range(len(axis_tags))
            }
        gvar_raw = font.ttf_tables._raw.get("gvar")
        if gvar_raw is None:
            raise FontNotSupportedException("Delta inspection requires gvar")
        gvar = GvarTable.from_reader(BinaryReader(gvar_raw), len(gvar_raw), axis_tags)
        if font.ttf_tables.loca is None or font.ttf_tables.glyf is None:
            raise FontNotSupportedException("Delta inspection requires glyf/loca")
        default_font = font.smart_instancer.instantiate(default_resolved.coordinates)
        resolved_font = font.smart_instancer.instantiate(resolved.coordinates)
        default_path = _glyph_path(default_font, int(target_gid))
        resolved_path = _glyph_path(resolved_font, int(target_gid))
        raw = _glyph_bytes(font, int(target_gid))
        contour_count = _glyph_contour_count(raw)
        if contour_count < 0:
            components = _parse_composite_components(raw)
            variations = gvar.glyph_variations(int(target_gid), 0)
            active_reports = [
                _tuple_report(
                    tuple_index,
                    variation,
                    scalar=scalar,
                    outline_point_count=0,
                    top_points=0,
                )
                for tuple_index, variation in enumerate(variations)
                if (scalar := TtfInstancer._support_scalar(variation, normalized)) != 0.0
            ]
            default_points = _path_points(default_path)
            resolved_points = _path_points(resolved_path)
            point_count = min(len(default_points), len(resolved_points))
            strongest_points = _path_delta_points(default_points, resolved_points, top_points)
            component_movements = _component_movements(
                font,
                components,
                coordinates=dict(resolved.coordinates),
                default_font=default_font,
                resolved_font=resolved_font,
                top_points=top_points,
            )
            note = (
                "composite glyph support now derives per-component movement from child glyph delta analysis; "
                "root composite tuple-point diagnostics remain limited"
            )
            report = GlyphDeltaReport(
                glyph_id=int(target_gid),
                glyph_name=glyph_name,
                codepoint=resolved_codepoint,
                character=_character_for_codepoint(resolved_codepoint),
                instance_label=resolved.label,
                coordinates=dict(resolved.coordinates),
                normalized_coordinates=dict(normalized),
                total_tuple_count=len(variations),
                active_tuples=tuple(active_reports),
                strongest_points=strongest_points,
                composite_components=components,
                component_movements=component_movements,
                point_count=point_count,
                contour_count=max(_path_contour_count(resolved_path), _path_contour_count(default_path)),
                is_supported=True,
                note=note,
            )
            return _GlyphDeltaAnalysis(
                report=report,
                default_label=default_resolved.label,
                default_path=default_path,
                resolved_path=resolved_path,
                default_points=default_points[:point_count],
                resolved_points=resolved_points[:point_count],
                highlight_points=strongest_points,
            )
        if contour_count == 0:
            variations = gvar.glyph_variations(int(target_gid), 0)
            report = GlyphDeltaReport(
                glyph_id=int(target_gid),
                glyph_name=glyph_name,
                codepoint=resolved_codepoint,
                character=_character_for_codepoint(resolved_codepoint),
                instance_label=resolved.label,
                coordinates=dict(resolved.coordinates),
                normalized_coordinates=dict(normalized),
                total_tuple_count=len(variations),
                point_count=0,
                contour_count=0,
                is_supported=False,
                note="delta inspection currently requires outline-bearing glyphs",
            )
            return _GlyphDeltaAnalysis(
                report=report,
                default_label=default_resolved.label,
                default_path=default_path,
                resolved_path=resolved_path,
                default_points=(),
                resolved_points=(),
                highlight_points=(),
            )
        simple = TtfInstancer._parse_simple_glyph(raw)
        variations = gvar.glyph_variations(int(target_gid), len(simple.xs))
        active_reports: list[DeltaTupleReport] = []
        total_dx = [0.0] * len(simple.xs)
        total_dy = [0.0] * len(simple.ys)
        for tuple_index, variation in enumerate(variations):
            scalar = TtfInstancer._support_scalar(variation, normalized)
            if scalar == 0.0:
                continue
            active_reports.append(
                _tuple_report(
                    tuple_index,
                    variation,
                    scalar=scalar,
                    outline_point_count=len(simple.xs),
                    top_points=top_points,
                )
            )
            points = variation.points if variation.points is not None else list(range(len(variation.deltas)))
            for point_index, (delta_x, delta_y) in zip(points, variation.deltas):
                if point_index >= len(total_dx):
                    continue
                total_dx[point_index] += delta_x * scalar
                total_dy[point_index] += delta_y * scalar
        report = GlyphDeltaReport(
            glyph_id=int(target_gid),
            glyph_name=glyph_name,
            codepoint=resolved_codepoint,
            character=_character_for_codepoint(resolved_codepoint),
            instance_label=resolved.label,
            coordinates=dict(resolved.coordinates),
            normalized_coordinates=dict(normalized),
            total_tuple_count=len(variations),
            active_tuples=tuple(active_reports),
            strongest_points=_top_total_points(total_dx, total_dy, top_points),
            point_count=len(simple.xs),
            contour_count=len(simple.contour_ends),
        )
        default_points = tuple(zip(simple.xs, simple.ys))
        resolved_points = tuple(
            (simple.xs[index] + total_dx[index], simple.ys[index] + total_dy[index])
            for index in range(len(simple.xs))
        )
        return _GlyphDeltaAnalysis(
            report=report,
            default_label=default_resolved.label,
            default_path=default_path,
            resolved_path=resolved_path,
            default_points=default_points,
            resolved_points=resolved_points,
            highlight_points=report.strongest_points,
        )


def _resolve_glyph_target(font, *, glyph_id: int | None, codepoint: int | None) -> tuple[object, int | None]:
    if glyph_id is not None and codepoint is not None:
        raise ValueError("Choose either glyph_id or codepoint, not both")
    if codepoint is None and glyph_id is None:
        raise ValueError("Delta inspection requires glyph_id or codepoint")
    if codepoint is not None:
        return font.encoding.unicode_to_gid(int(codepoint)), int(codepoint)
    from aspose_font._types import GlyphId

    return GlyphId(int(glyph_id)), None


def _glyph_bytes(font, gid: int) -> bytes:
    loca = font.ttf_tables.loca
    glyf = font.ttf_tables.glyf
    if loca is None or glyf is None:
        return b""
    offset = loca.glyph_offset(gid)
    length = loca.glyph_length(gid)
    return glyf.get_glyph_bytes(offset, length)


def _glyph_contour_count(raw: bytes) -> int:
    if len(raw) < 2:
        return 0
    return int.from_bytes(raw[:2], "big", signed=True)


def _parse_composite_components(raw: bytes) -> tuple[CompositeGlyphComponent, ...]:
    if len(raw) < 10:
        return ()
    reader = BinaryReader(raw)
    contour_count = reader.read_i16()
    if contour_count >= 0:
        return ()
    reader.read_i16()
    reader.read_i16()
    reader.read_i16()
    reader.read_i16()
    components: list[CompositeGlyphComponent] = []
    while True:
        flags = reader.read_u16()
        component_gid = reader.read_u16()
        if flags & _ARG_1_AND_2_ARE_WORDS:
            arg1 = reader.read_i16()
            arg2 = reader.read_i16()
        else:
            arg1 = reader.read_i8()
            arg2 = reader.read_i8()
        dx = float(arg1) if (flags & _ARGS_ARE_XY_VALUES) else 0.0
        dy = float(arg2) if (flags & _ARGS_ARE_XY_VALUES) else 0.0
        xx = 1.0
        yx = 0.0
        xy = 0.0
        yy = 1.0
        if flags & _WE_HAVE_A_SCALE:
            scale = reader.read_f2dot14()
            xx = scale
            yy = scale
        elif flags & _WE_HAVE_AN_X_AND_Y_SCALE:
            xx = reader.read_f2dot14()
            yy = reader.read_f2dot14()
        elif flags & _WE_HAVE_A_TWO_BY_TWO:
            xx = reader.read_f2dot14()
            yx = reader.read_f2dot14()
            xy = reader.read_f2dot14()
            yy = reader.read_f2dot14()
        components.append(
            CompositeGlyphComponent(
                glyph_id=component_gid,
                dx=dx,
                dy=dy,
                xx=xx,
                yx=yx,
                xy=xy,
                yy=yy,
            )
        )
        if not (flags & _MORE_COMPONENTS):
            break
    return tuple(components)


def _character_for_codepoint(codepoint: int | None) -> str:
    if codepoint is None or codepoint < 32 or codepoint > 0x10FFFF:
        return ""
    return chr(codepoint)


def _tuple_report(
    tuple_index: int,
    variation: TupleVariation,
    *,
    scalar: float,
    outline_point_count: int,
    top_points: int,
) -> DeltaTupleReport:
    total_abs_dx = 0.0
    total_abs_dy = 0.0
    max_abs_dx = 0.0
    max_abs_dy = 0.0
    point_reports: list[DeltaPoint] = []
    referenced_points = 0
    referenced_outline_points = 0
    referenced_phantom_points = 0
    non_zero_points = 0
    non_zero_outline_points = 0
    non_zero_phantom_points = 0
    points = variation.points if variation.points is not None else list(range(len(variation.deltas)))
    for point_index, (delta_x, delta_y) in zip(points, variation.deltas):
        referenced_points += 1
        is_phantom = point_index >= outline_point_count
        if is_phantom:
            referenced_phantom_points += 1
        else:
            referenced_outline_points += 1
        applied_dx = delta_x * scalar
        applied_dy = delta_y * scalar
        if applied_dx == 0.0 and applied_dy == 0.0:
            continue
        non_zero_points += 1
        if is_phantom:
            non_zero_phantom_points += 1
        else:
            non_zero_outline_points += 1
        total_abs_dx += abs(applied_dx)
        total_abs_dy += abs(applied_dy)
        max_abs_dx = max(max_abs_dx, abs(applied_dx))
        max_abs_dy = max(max_abs_dy, abs(applied_dy))
        point_reports.append(
            DeltaPoint(
                index=point_index,
                dx=applied_dx,
                dy=applied_dy,
                magnitude=hypot(applied_dx, applied_dy),
            )
        )
    point_reports.sort(key=lambda item: (-item.magnitude, item.index))
    return DeltaTupleReport(
        tuple_index=tuple_index,
        scalar=scalar,
        peak_coords=dict(variation.peak_coords),
        start_coords=None if variation.start_coords is None else dict(variation.start_coords),
        end_coords=None if variation.end_coords is None else dict(variation.end_coords),
        referenced_points=referenced_points,
        referenced_outline_points=referenced_outline_points,
        referenced_phantom_points=referenced_phantom_points,
        non_zero_points=non_zero_points,
        non_zero_outline_points=non_zero_outline_points,
        non_zero_phantom_points=non_zero_phantom_points,
        max_abs_dx=max_abs_dx,
        max_abs_dy=max_abs_dy,
        total_abs_dx=total_abs_dx,
        total_abs_dy=total_abs_dy,
        top_points=tuple(point_reports[:top_points]),
    )


def _glyph_path(font, gid: int) -> GlyphPath | None:
    from aspose_font._types import GlyphId

    try:
        glyph = font.glyph_accessor.get_glyph_by_id(GlyphId(gid))
    except GlyphNotFoundException:
        return None
    return glyph.path


def _path_points(path: GlyphPath | None) -> tuple[tuple[float, float], ...]:
    if path is None:
        return ()
    points: list[tuple[float, float]] = []
    for command in path:
        if isinstance(command, (MoveTo, LineTo)):
            points.append((float(command.x), float(command.y)))
        elif isinstance(command, QuadraticTo):
            points.append((float(command.x), float(command.y)))
        elif isinstance(command, CurveTo):
            points.append((float(command.x), float(command.y)))
    return tuple(points)


def _path_contour_count(path: GlyphPath | None) -> int:
    if path is None:
        return 0
    return sum(1 for command in path if isinstance(command, MoveTo))


def _path_delta_points(
    before_points: tuple[tuple[float, float], ...],
    after_points: tuple[tuple[float, float], ...],
    top_points: int,
) -> tuple[DeltaPoint, ...]:
    limit = min(len(before_points), len(after_points))
    dx = [after_points[index][0] - before_points[index][0] for index in range(limit)]
    dy = [after_points[index][1] - before_points[index][1] for index in range(limit)]
    return _top_total_points(dx, dy, top_points)


def _component_movements(
    font,
    components: tuple[CompositeGlyphComponent, ...],
    *,
    coordinates: dict[str, float],
    default_font,
    resolved_font,
    top_points: int,
) -> tuple[CompositeComponentMovement, ...]:
    movements: list[CompositeComponentMovement] = []
    for component_index, component in enumerate(components):
        default_component = _glyph_path(default_font, component.glyph_id)
        resolved_component = _glyph_path(resolved_font, component.glyph_id)
        default_component_points = _path_points(default_component)
        resolved_component_points = _path_points(resolved_component)
        available = min(len(default_component_points), len(resolved_component_points))
        child_report = DeltaInspector.inspect_variable_glyph(
            font,
            glyph_id=component.glyph_id,
            coordinates=coordinates,
            top_points=top_points,
        )
        transformed_before = tuple(
            _apply_component_transform(point, component)
            for point in default_component_points[:available]
        )
        transformed_after = tuple(
            _apply_component_transform(point, component)
            for point in resolved_component_points[:available]
        )
        if available <= 0:
            movements.append(
                CompositeComponentMovement(
                    component_index=component_index,
                    glyph_id=component.glyph_id,
                    point_count=0,
                    strongest_point_index=None,
                    strongest_magnitude=0.0,
                    total_abs_dx=0.0,
                    total_abs_dy=0.0,
                    active_tuple_count=len(child_report.active_tuples),
                    local_strongest_point_index=None if not child_report.strongest_points else child_report.strongest_points[0].index,
                    local_strongest_magnitude=0.0 if not child_report.strongest_points else child_report.strongest_points[0].magnitude,
                    shift_magnitude=hypot(component.dx, component.dy),
                    transform_changed=not _is_identity_component_transform(component),
                    note=child_report.note,
                )
            )
            continue
        strongest = _path_delta_points(transformed_before, transformed_after, 1)
        total_abs_dx = sum(
            abs(transformed_after[index][0] - transformed_before[index][0])
            for index in range(available)
        )
        total_abs_dy = sum(
            abs(transformed_after[index][1] - transformed_before[index][1])
            for index in range(available)
        )
        movements.append(
            CompositeComponentMovement(
                component_index=component_index,
                glyph_id=component.glyph_id,
                point_count=available,
                strongest_point_index=None if not strongest else strongest[0].index,
                strongest_magnitude=0.0 if not strongest else strongest[0].magnitude,
                total_abs_dx=total_abs_dx,
                total_abs_dy=total_abs_dy,
                active_tuple_count=len(child_report.active_tuples),
                local_strongest_point_index=None if not child_report.strongest_points else child_report.strongest_points[0].index,
                local_strongest_magnitude=0.0 if not child_report.strongest_points else child_report.strongest_points[0].magnitude,
                shift_magnitude=hypot(component.dx, component.dy),
                transform_changed=not _is_identity_component_transform(component),
                note=child_report.note,
            )
        )
    return tuple(movements)


def _apply_component_transform(
    point: tuple[float, float],
    component: CompositeGlyphComponent,
) -> tuple[float, float]:
    x, y = point
    return (
        component.xx * x + component.xy * y + component.dx,
        component.yx * x + component.yy * y + component.dy,
    )


def _is_identity_component_transform(component: CompositeGlyphComponent) -> bool:
    return (
        component.xx == 1.0
        and component.xy == 0.0
        and component.yx == 0.0
        and component.yy == 1.0
    )


def _top_total_points(dx: list[float], dy: list[float], top_points: int) -> tuple[DeltaPoint, ...]:
    ranked: list[DeltaPoint] = []
    for index, (delta_x, delta_y) in enumerate(zip(dx, dy)):
        magnitude = hypot(delta_x, delta_y)
        if magnitude == 0.0:
            continue
        ranked.append(
            DeltaPoint(
                index=index,
                dx=delta_x,
                dy=delta_y,
                magnitude=magnitude,
            )
        )
    ranked.sort(key=lambda item: (-item.magnitude, item.index))
    return tuple(ranked[:top_points])


def _render_glyph_panel(
    path: GlyphPath | None,
    *,
    also_path: GlyphPath | None = None,
    panel_size: int,
    primary_color: tuple[int, int, int],
    background: tuple[int, int, int],
    secondary_color: tuple[int, int, int] | None = None,
    before_points: tuple[tuple[float, float], ...] = (),
    after_points: tuple[tuple[float, float], ...] = (),
    highlighted_points: tuple[DeltaPoint, ...] = (),
    emphasize_primary: bool,
    show_point_cloud: bool = False,
    show_guides: bool = False,
) -> PreviewImage:
    width = max(64, int(panel_size))
    height = width
    raster = Rasterizer(width, height, background)
    bounds = _combined_bbox(path, also_path)
    transform = _fit_transform(bounds, width, height, padding=max(18, width // 10))
    if show_guides:
        _draw_guides(raster._buf, raster.width, raster.height, background)
    if also_path is not None:
        raster.draw_path(
            also_path,
            color=secondary_color or _RESOLVED_COLOR,
            transform=transform,
        )
    if path is not None:
        raster.draw_path(path, color=primary_color, transform=transform)
    if show_point_cloud:
        _draw_point_cloud(
            raster._buf,
            raster.width,
            raster.height,
            before_points,
            transform,
            fill=_DEFAULT_POINT_COLOR,
        )
        _draw_point_cloud(
            raster._buf,
            raster.width,
            raster.height,
            after_points,
            transform,
            fill=_RESOLVED_POINT_COLOR,
        )
    if not emphasize_primary and highlighted_points and before_points and after_points:
        for point in highlighted_points:
            if point.index >= len(before_points) or point.index >= len(after_points):
                continue
            start = _apply_transform(before_points[point.index], transform)
            end = _apply_transform(after_points[point.index], transform)
            _draw_line(raster._buf, raster.width, raster.height, start, end, _ARROW_COLOR)
            _draw_marker(
                raster._buf,
                raster.width,
                raster.height,
                start,
                _DEFAULT_COLOR,
                radius=3 if show_point_cloud else 2,
            )
            _draw_marker(
                raster._buf,
                raster.width,
                raster.height,
                end,
                _RESOLVED_COLOR,
                radius=3 if show_point_cloud else 2,
            )
            label_anchor = _midpoint(start, end) if show_point_cloud else end
            _draw_point_label(raster._buf, raster.width, raster.height, label_anchor, point.index)
    return PreviewImage(
        filename="delta-panel.png",
        media_type="image/png",
        data=raster.to_png(),
    )


def _build_comparison_board(
    comparison: _GlyphDeltaComparison,
    *,
    panel_size: int,
    file_stem: str,
) -> PreviewImage:
    return FontPreviewBuilder.compose_sheet(
        [
            _render_glyph_panel(
                comparison.before.resolved_path,
                also_path=comparison.after.resolved_path,
                panel_size=panel_size,
                primary_color=_DEFAULT_COLOR,
                background=_PANEL_BACKGROUND,
                emphasize_primary=True,
            ),
            _render_glyph_panel(
                comparison.before.resolved_path,
                also_path=comparison.after.resolved_path,
                panel_size=panel_size,
                primary_color=_DEFAULT_COLOR,
                secondary_color=_RESOLVED_COLOR,
                background=_PANEL_BACKGROUND,
                before_points=comparison.before.resolved_points,
                after_points=comparison.after.resolved_points,
                highlighted_points=comparison.comparison_points,
                emphasize_primary=False,
            ),
            _render_glyph_panel(
                comparison.before.resolved_path,
                also_path=comparison.after.resolved_path,
                panel_size=panel_size,
                primary_color=_DEFAULT_COLOR,
                secondary_color=_RESOLVED_COLOR,
                background=_PANEL_BACKGROUND,
                before_points=comparison.before.resolved_points,
                after_points=comparison.after.resolved_points,
                highlighted_points=comparison.comparison_points,
                emphasize_primary=False,
                show_point_cloud=True,
                show_guides=True,
            ),
            _render_glyph_panel(
                comparison.after.resolved_path,
                also_path=comparison.before.resolved_path,
                panel_size=panel_size,
                primary_color=_RESOLVED_COLOR,
                background=_PANEL_BACKGROUND,
                emphasize_primary=True,
            ),
        ],
        columns=4,
        title=_delta_comparison_title(comparison.before.report),
        column_headers=["Before", "Compare", "Diagram", "After"],
        labels=[
            comparison.before.report.instance_label,
            _delta_comparison_label(comparison),
            _diagram_label(comparison.before.report),
            comparison.after.report.instance_label,
        ],
        footer_lines=_delta_comparison_footer_lines(comparison),
        background=_PANEL_BACKGROUND,
        file_stem=file_stem,
    )


def _build_comparison_card(
    comparison: _GlyphDeltaComparison,
    *,
    panel_size: int,
    file_stem: str,
) -> PreviewImage:
    return FontPreviewBuilder.compose_sheet(
        [
            _render_glyph_panel(
                comparison.before.resolved_path,
                also_path=comparison.after.resolved_path,
                panel_size=panel_size,
                primary_color=_DEFAULT_COLOR,
                background=_PANEL_BACKGROUND,
                emphasize_primary=True,
            ),
            _render_glyph_panel(
                comparison.after.resolved_path,
                also_path=comparison.before.resolved_path,
                panel_size=panel_size,
                primary_color=_RESOLVED_COLOR,
                background=_PANEL_BACKGROUND,
                emphasize_primary=True,
            ),
            _render_glyph_panel(
                comparison.before.resolved_path,
                also_path=comparison.after.resolved_path,
                panel_size=panel_size,
                primary_color=_DEFAULT_COLOR,
                secondary_color=_RESOLVED_COLOR,
                background=_PANEL_BACKGROUND,
                before_points=comparison.before.resolved_points,
                after_points=comparison.after.resolved_points,
                highlighted_points=comparison.comparison_points,
                emphasize_primary=False,
            ),
            _render_glyph_panel(
                comparison.before.resolved_path,
                also_path=comparison.after.resolved_path,
                panel_size=panel_size,
                primary_color=_DEFAULT_COLOR,
                secondary_color=_RESOLVED_COLOR,
                background=_PANEL_BACKGROUND,
                before_points=comparison.before.resolved_points,
                after_points=comparison.after.resolved_points,
                highlighted_points=comparison.comparison_points,
                emphasize_primary=False,
                show_point_cloud=True,
                show_guides=True,
            ),
        ],
        columns=2,
        labels=[
            comparison.before.report.instance_label,
            comparison.after.report.instance_label,
            _delta_comparison_label(comparison),
            _diagram_label(comparison.before.report),
        ],
        background=_PANEL_BACKGROUND,
        file_stem=file_stem,
    )


def _combined_bbox(path: GlyphPath | None, also_path: GlyphPath | None) -> tuple[float, float, float, float]:
    boxes = [bbox for bbox in (_path_bbox(path), _path_bbox(also_path)) if bbox is not None]
    if not boxes:
        return (0.0, 0.0, 1.0, 1.0)
    min_x = min(box[0] for box in boxes)
    min_y = min(box[1] for box in boxes)
    max_x = max(box[2] for box in boxes)
    max_y = max(box[3] for box in boxes)
    if max_x == min_x:
        max_x += 1.0
    if max_y == min_y:
        max_y += 1.0
    return (min_x, min_y, max_x, max_y)


def _path_bbox(path: GlyphPath | None) -> tuple[float, float, float, float] | None:
    if path is None or len(path) == 0:
        return None
    min_x: float | None = None
    min_y: float | None = None
    max_x: float | None = None
    max_y: float | None = None

    def record(x: float, y: float) -> None:
        nonlocal min_x, min_y, max_x, max_y
        min_x = x if min_x is None else min(min_x, x)
        min_y = y if min_y is None else min(min_y, y)
        max_x = x if max_x is None else max(max_x, x)
        max_y = y if max_y is None else max(max_y, y)

    for command in path:
        if isinstance(command, (MoveTo, LineTo)):
            record(command.x, command.y)
        elif isinstance(command, QuadraticTo):
            record(command.x1, command.y1)
            record(command.x, command.y)
        elif isinstance(command, CurveTo):
            record(command.x1, command.y1)
            record(command.x2, command.y2)
            record(command.x, command.y)
        elif isinstance(command, ClosePath):
            continue
    if min_x is None or min_y is None or max_x is None or max_y is None:
        return None
    return (min_x, min_y, max_x, max_y)


def _fit_transform(
    bbox: tuple[float, float, float, float],
    width: int,
    height: int,
    *,
    padding: int,
) -> tuple[float, float, float, float, float, float]:
    min_x, min_y, max_x, max_y = bbox
    box_width = max(1.0, max_x - min_x)
    box_height = max(1.0, max_y - min_y)
    available_width = max(1.0, width - padding * 2)
    available_height = max(1.0, height - padding * 2)
    scale = min(available_width / box_width, available_height / box_height)
    content_width = box_width * scale
    content_height = box_height * scale
    offset_x = (width - content_width) / 2.0 - min_x * scale
    offset_y = (height - content_height) / 2.0 + max_y * scale
    return (scale, 0.0, 0.0, -scale, offset_x, offset_y)


def _apply_transform(
    point: tuple[float, float],
    transform: tuple[float, float, float, float, float, float],
) -> tuple[float, float]:
    a, b, c, d, e, f = transform
    x, y = point
    return (a * x + c * y + e, b * x + d * y + f)


def _draw_line(
    pixels: bytearray,
    width: int,
    height: int,
    start: tuple[float, float],
    end: tuple[float, float],
    color: tuple[int, int, int],
) -> None:
    x0 = int(round(start[0]))
    y0 = int(round(start[1]))
    x1 = int(round(end[0]))
    y1 = int(round(end[1]))
    dx = abs(x1 - x0)
    dy = -abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx + dy
    while True:
        _set_pixel(pixels, width, height, x0, y0, color)
        if x0 == x1 and y0 == y1:
            break
        twice_err = 2 * err
        if twice_err >= dy:
            err += dy
            x0 += sx
        if twice_err <= dx:
            err += dx
            y0 += sy


def _draw_marker(
    pixels: bytearray,
    width: int,
    height: int,
    point: tuple[float, float],
    fill: tuple[int, int, int],
    *,
    radius: int = 2,
) -> None:
    cx = int(round(point[0]))
    cy = int(round(point[1]))
    for y in range(cy - radius, cy + radius + 1):
        for x in range(cx - radius, cx + radius + 1):
            if x == cx - radius or x == cx + radius or y == cy - radius or y == cy + radius:
                _set_pixel(pixels, width, height, x, y, _MARKER_OUTLINE)
            else:
                _set_pixel(pixels, width, height, x, y, fill)


def _draw_point_cloud(
    pixels: bytearray,
    width: int,
    height: int,
    points: tuple[tuple[float, float], ...],
    transform: tuple[float, float, float, float, float, float],
    *,
    fill: tuple[int, int, int],
) -> None:
    for point in points:
        screen = _apply_transform(point, transform)
        _draw_marker(pixels, width, height, screen, fill, radius=1)


def _draw_guides(
    pixels: bytearray,
    width: int,
    height: int,
    background: tuple[int, int, int],
) -> None:
    center_x = width // 2
    center_y = height // 2
    for x in range(width):
        if tuple(pixels[(center_y * width + x) * 3:(center_y * width + x) * 3 + 3]) == background:
            _set_pixel(pixels, width, height, x, center_y, _GUIDE_COLOR)
    for y in range(height):
        if tuple(pixels[(y * width + center_x) * 3:(y * width + center_x) * 3 + 3]) == background:
            _set_pixel(pixels, width, height, center_x, y, _GUIDE_COLOR)
    for x in range(8, width, max(24, width // 6)):
        for y in range(8, height, max(24, height // 6)):
            if tuple(pixels[(y * width + x) * 3:(y * width + x) * 3 + 3]) == background:
                _set_pixel(pixels, width, height, x, y, _GUIDE_COLOR)


def _draw_point_label(
    pixels: bytearray,
    width: int,
    height: int,
    point: tuple[float, float],
    index: int,
) -> None:
    text_x = int(round(point[0])) + 5
    text_y = int(round(point[1])) - 9
    _draw_bitmap_text(
        pixels,
        width,
        max(0, text_x),
        max(0, text_y),
        str(index),
        color=_MARKER_OUTLINE,
    )


def _midpoint(
    start: tuple[float, float],
    end: tuple[float, float],
) -> tuple[float, float]:
    return ((start[0] + end[0]) / 2.0, (start[1] + end[1]) / 2.0)


def _set_pixel(
    pixels: bytearray,
    width: int,
    height: int,
    x: int,
    y: int,
    color: tuple[int, int, int],
) -> None:
    if x < 0 or y < 0 or x >= width or y >= height:
        return
    index = (y * width + x) * 3
    pixels[index] = color[0]
    pixels[index + 1] = color[1]
    pixels[index + 2] = color[2]


def _delta_title(report: GlyphDeltaReport) -> str:
    parts = [f"Glyph Delta Inspector GID={report.glyph_id}"]
    if report.codepoint is not None:
        parts.append(f"U+{report.codepoint:04X}")
        if report.character and not report.character.isspace():
            parts.append(report.character)
    return " ".join(parts)


def _overlay_label(report: GlyphDeltaReport) -> str:
    return f"{len(report.active_tuples)} ACTIVE TUPLES"


def _diagram_label(report: GlyphDeltaReport) -> str:
    count = min(4, len(report.strongest_points))
    return f"POINT DIAGRAM #{count}" if count else "POINT DIAGRAM"


def _delta_text_title(report: TextDeltaReport) -> str:
    return f"Delta Text Inspector {report.text!r}"


def _delta_text_comparison_title(report: TextDeltaComparisonReport) -> str:
    return f"Delta Text Compare {report.text!r}"


def _delta_comparison_title(report: GlyphDeltaReport) -> str:
    parts = [f"Glyph Delta Compare GID={report.glyph_id}"]
    if report.codepoint is not None:
        parts.append(f"U+{report.codepoint:04X}")
        if report.character and not report.character.isspace():
            parts.append(report.character)
    return " ".join(parts)


def _text_sheet_label(report: GlyphDeltaReport) -> str:
    parts = [f"GID {report.glyph_id}"]
    if report.codepoint is not None:
        parts.append(f"U+{report.codepoint:04X}")
    if report.character and not report.character.isspace():
        parts.append(repr(report.character))
    parts.append(f"{len(report.active_tuples)}/{report.total_tuple_count} tuples")
    if report.strongest_points:
        parts.append(f"max #{report.strongest_points[0].index}")
    if not report.is_supported:
        parts.append("limited")
    return " ".join(parts)


def _text_comparison_sheet_label(report: GlyphDeltaComparisonReport) -> str:
    parts = [f"GID {report.glyph_id}"]
    if report.codepoint is not None:
        parts.append(f"U+{report.codepoint:04X}")
    if report.character and not report.character.isspace():
        parts.append(repr(report.character))
    parts.append(f"moved={report.moved_point_count}")
    if report.comparison_points:
        parts.append(f"max #{report.comparison_points[0].index}")
    if not report.is_comparable:
        parts.append("limited")
    return " ".join(parts)


def _delta_footer_lines(report: GlyphDeltaReport) -> list[str]:
    lines = [
        (
            f"Resolved {report.instance_label}: "
            f"{len(report.active_tuples)}/{report.total_tuple_count} active tuples, "
            f"{report.point_count} points, {report.contour_count} contours"
        )
    ]
    if report.active_tuples:
        tuple_summary = []
        for item in report.active_tuples[:3]:
            tuple_summary.append(
                f"#{item.tuple_index} scalar={item.scalar:.3f} peak={_coord_summary(item.peak_coords)}"
            )
        lines.append("Tuples: " + "; ".join(tuple_summary))
    if report.strongest_points:
        lines.append(
            "Top points: "
            + "; ".join(
                (
                    f"#{point.index} "
                    f"dx={point.dx:.1f} dy={point.dy:.1f} mag={point.magnitude:.1f}"
                )
                for point in report.strongest_points[:4]
            )
        )
    if report.composite_components:
        lines.append(
            "Components: "
            + "; ".join(
                _component_summary(component)
                for component in report.composite_components[:4]
            )
        )
    if report.component_movements:
        lines.append(
            "Component movement: "
            + "; ".join(
                _component_movement_summary(movement)
                for movement in report.component_movements[:4]
            )
        )
    if report.note:
        lines.append(report.note)
    return lines


def _delta_comparison_label(comparison: _GlyphDeltaComparison) -> str:
    return f"{len(comparison.comparison_points)} MOVED POINTS"


def _delta_comparison_footer_lines(comparison: _GlyphDeltaComparison) -> list[str]:
    before = comparison.before.report
    after = comparison.after.report
    lines = [
        (
            f"Before {before.instance_label}: "
            f"{len(before.active_tuples)}/{before.total_tuple_count} active tuples; "
            f"After {after.instance_label}: "
            f"{len(after.active_tuples)}/{after.total_tuple_count} active tuples"
        ),
        "Before coords: " + _coord_summary(before.coordinates),
        "After coords: " + _coord_summary(after.coordinates),
    ]
    if comparison.comparison_points:
        lines.append(
            "Net movement: "
            + "; ".join(
                (
                    f"#{point.index} "
                    f"dx={point.dx:.1f} dy={point.dy:.1f} mag={point.magnitude:.1f}"
                )
                for point in comparison.comparison_points[:4]
            )
        )
    if comparison.note:
        lines.append(comparison.note)
    return lines


def _delta_text_footer_lines(report: TextDeltaReport) -> list[str]:
    lines = [
        (
            f"Resolved {report.instance_label}: "
            f"{report.active_glyph_count}/{report.glyph_count} glyphs with active deltas, "
            f"{report.supported_glyph_count}/{report.glyph_count} fully supported"
        ),
        "Coordinates: " + _coord_summary(report.coordinates),
        "Normalized: " + _coord_summary(report.normalized_coordinates),
    ]
    ranked = [
        glyph
        for glyph in sorted(
            report.glyph_reports,
            key=lambda item: (
                -(item.strongest_points[0].magnitude if item.strongest_points else 0.0),
                item.glyph_id,
            ),
        )
        if glyph.strongest_points
    ]
    if ranked:
        lines.append(
            "Strongest glyphs: "
            + "; ".join(
                (
                    f"{_glyph_chip(item)} "
                    f"mag={item.strongest_points[0].magnitude:.1f} "
                    f"tuples={len(item.active_tuples)}"
                )
                for item in ranked[:4]
            )
        )
    return lines


def _delta_text_comparison_footer_lines(report: TextDeltaComparisonReport) -> list[str]:
    lines = [
        (
            f"Before {report.before_label}: {_coord_summary(report.before_coordinates)}; "
            f"After {report.after_label}: {_coord_summary(report.after_coordinates)}"
        ),
        (
            f"Comparable glyphs: {report.comparable_glyph_count}/{report.glyph_count}; "
            f"Moved glyphs: {report.moved_glyph_count}/{report.glyph_count}"
        ),
    ]
    ranked = [
        glyph
        for glyph in sorted(
            report.glyph_comparisons,
            key=lambda item: (
                -(item.comparison_points[0].magnitude if item.comparison_points else 0.0),
                item.glyph_id,
            ),
        )
        if glyph.is_comparable and glyph.comparison_points
    ]
    if ranked:
        lines.append(
            "Strongest glyph deltas: "
            + "; ".join(
                (
                    f"{_glyph_chip(item.before)} "
                    f"mag={item.comparison_points[0].magnitude:.1f} "
                    f"moved={item.moved_point_count}"
                )
                for item in ranked[:4]
            )
        )
    return lines


def _glyph_chip(report: GlyphDeltaReport) -> str:
    if report.codepoint is not None:
        if report.character and not report.character.isspace():
            return f"U+{report.codepoint:04X} {report.character}"
        return f"U+{report.codepoint:04X}"
    return f"GID {report.glyph_id}"


def _component_summary(component: CompositeGlyphComponent) -> str:
    transform = f"[{component.xx:.2f},{component.xy:.2f};{component.yx:.2f},{component.yy:.2f}]"
    return (
        f"GID {component.glyph_id} "
        f"shift=({component.dx:.1f},{component.dy:.1f}) "
        f"xform={transform}"
    )


def _component_movement_summary(movement: CompositeComponentMovement) -> str:
    strongest = "-" if movement.strongest_point_index is None else f"#{movement.strongest_point_index}"
    local_strongest = (
        "-"
        if movement.local_strongest_point_index is None
        else f"#{movement.local_strongest_point_index}"
    )
    transform_note = " xform" if movement.transform_changed else ""
    return (
        f"GID {movement.glyph_id} "
        f"pts={movement.point_count} "
        f"top={strongest} "
        f"local={local_strongest} "
        f"tuples={movement.active_tuple_count} "
        f"mag={movement.strongest_magnitude:.1f} "
        f"total=({movement.total_abs_dx:.1f},{movement.total_abs_dy:.1f}) "
        f"shift={movement.shift_magnitude:.1f}{transform_note}"
    )


def _coord_summary(values: dict[str, float]) -> str:
    return ", ".join(f"{tag}={value:g}" for tag, value in sorted(values.items()))


def _unique_codepoints_from_text(text: str) -> list[int]:
    seen: set[int] = set()
    ordered: list[int] = []
    for ch in text:
        codepoint = ord(ch)
        if codepoint in seen:
            continue
        seen.add(codepoint)
        ordered.append(codepoint)
    return ordered


__all__ = [
    "DeltaInspector",
    "DeltaPoint",
    "DeltaTupleReport",
    "GlyphDeltaComparisonReport",
    "GlyphDeltaReport",
    "TextDeltaComparisonReport",
    "TextDeltaReport",
]
