"""Variable-font compatibility checking helpers."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from aspose_font._exceptions import FontNotSupportedException, GlyphNotFoundException
from aspose_font._font_base import Font
from aspose_font._io import BinaryReader
from aspose_font._types import ClosePath, CurveTo, Glyph, LineTo, MoveTo, QuadraticTo
from aspose_font.ttf.instancer import TtfInstancer
from aspose_font.ttf.tables.avar import AvarTable
from aspose_font.ttf.tables.gvar import GvarTable, TupleVariation


@dataclass(slots=True, frozen=True)
class GlyphOutlineStats:
    command_count: int
    point_count: int
    contour_count: int
    advance_width: int
    line_count: int
    quadratic_count: int
    cubic_count: int
    control_point_count: int
    closed_contour_count: int
    open_contour_count: int
    start_point: tuple[float, float] | None
    end_point: tuple[float, float] | None
    bbox: tuple[float, float, float, float] | None

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "command_count": self.command_count,
            "point_count": self.point_count,
            "contour_count": self.contour_count,
            "advance_width": self.advance_width,
            "line_count": self.line_count,
            "quadratic_count": self.quadratic_count,
            "cubic_count": self.cubic_count,
            "control_point_count": self.control_point_count,
            "closed_contour_count": self.closed_contour_count,
            "open_contour_count": self.open_contour_count,
        }
        payload["start_point"] = None if self.start_point is None else [float(value) for value in self.start_point]
        payload["end_point"] = None if self.end_point is None else [float(value) for value in self.end_point]
        if self.bbox is not None:
            payload["bbox"] = [float(value) for value in self.bbox]
        else:
            payload["bbox"] = None
        return payload


@dataclass(slots=True, frozen=True)
class GlyphCompatibilityIssue:
    codepoint: int
    character: str
    reason: str
    geometry_notes: tuple[str, ...]
    before_signature: tuple[str, ...]
    after_signature: tuple[str, ...]
    before_stats: GlyphOutlineStats
    after_stats: GlyphOutlineStats

    def to_dict(self) -> dict[str, object]:
        return {
            "codepoint": self.codepoint,
            "character": self.character,
            "reason": self.reason,
            "geometry_notes": list(self.geometry_notes),
            "before_signature": list(self.before_signature),
            "after_signature": list(self.after_signature),
            "before_stats": self.before_stats.to_dict(),
            "after_stats": self.after_stats.to_dict(),
        }


@dataclass(slots=True, frozen=True)
class ActiveTupleSummary:
    tuple_index: int
    scalar: float
    peak_coords: dict[str, float]
    start_coords: dict[str, float] | None
    end_coords: dict[str, float] | None

    def to_dict(self) -> dict[str, object]:
        return {
            "tuple_index": self.tuple_index,
            "scalar": float(self.scalar),
            "peak_coords": dict(self.peak_coords),
            "start_coords": None if self.start_coords is None else dict(self.start_coords),
            "end_coords": None if self.end_coords is None else dict(self.end_coords),
        }


@dataclass(slots=True, frozen=True)
class TupleScalarDelta:
    tuple_index: int
    before_scalar: float
    after_scalar: float

    def to_dict(self) -> dict[str, object]:
        return {
            "tuple_index": self.tuple_index,
            "before_scalar": float(self.before_scalar),
            "after_scalar": float(self.after_scalar),
        }


@dataclass(slots=True, frozen=True)
class GlyphInterpolationIssue:
    codepoint: int
    character: str
    reason: str
    before_active: tuple[ActiveTupleSummary, ...]
    after_active: tuple[ActiveTupleSummary, ...]
    entered_tuple_indices: tuple[int, ...]
    exited_tuple_indices: tuple[int, ...]
    retuned_tuples: tuple[TupleScalarDelta, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "codepoint": self.codepoint,
            "character": self.character,
            "reason": self.reason,
            "before_active": [item.to_dict() for item in self.before_active],
            "after_active": [item.to_dict() for item in self.after_active],
            "entered_tuple_indices": list(self.entered_tuple_indices),
            "exited_tuple_indices": list(self.exited_tuple_indices),
            "retuned_tuples": [item.to_dict() for item in self.retuned_tuples],
        }


@dataclass(slots=True, frozen=True)
class CompatibilityReport:
    before_label: str
    after_label: str
    checked_codepoints: tuple[int, ...]
    compared_glyphs: int
    before_normalized_coordinates: dict[str, float] = field(default_factory=dict)
    after_normalized_coordinates: dict[str, float] = field(default_factory=dict)
    issues: tuple[GlyphCompatibilityIssue, ...] = field(default_factory=tuple)
    interpolation_issues: tuple[GlyphInterpolationIssue, ...] = field(default_factory=tuple)

    @property
    def is_compatible(self) -> bool:
        return not self.issues

    def to_dict(self) -> dict[str, object]:
        return {
            "before_label": self.before_label,
            "after_label": self.after_label,
            "checked_codepoints": list(self.checked_codepoints),
            "compared_glyphs": self.compared_glyphs,
            "before_normalized_coordinates": dict(self.before_normalized_coordinates),
            "after_normalized_coordinates": dict(self.after_normalized_coordinates),
            "is_compatible": self.is_compatible,
            "issues": [issue.to_dict() for issue in self.issues],
            "interpolation_issue_count": len(self.interpolation_issues),
            "interpolation_issues": [issue.to_dict() for issue in self.interpolation_issues],
        }

    def to_json(self, *, indent: int = 2, sort_keys: bool = True) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=sort_keys)

    def write_json(
        self,
        target: str | Path,
        *,
        indent: int = 2,
        sort_keys: bool = True,
    ) -> None:
        Path(target).write_text(
            f"{self.to_json(indent=indent, sort_keys=sort_keys)}\n",
            encoding="utf-8",
        )


class CompatibilityChecker:
    @staticmethod
    def compare_fonts(
        before: Font,
        after: Font,
        *,
        before_label: str = "Before",
        after_label: str = "After",
        codepoints: list[int] | tuple[int, ...] | None = None,
        text: str = "",
    ) -> CompatibilityReport:
        selected_codepoints = _resolve_codepoints(before, after, codepoints=codepoints, text=text)
        issues: list[GlyphCompatibilityIssue] = []
        compared = 0
        for codepoint in selected_codepoints:
            before_glyph = _glyph_for_codepoint(before, codepoint)
            after_glyph = _glyph_for_codepoint(after, codepoint)
            if before_glyph is None and after_glyph is None:
                continue
            compared += 1
            before_signature = _glyph_signature(before_glyph)
            after_signature = _glyph_signature(after_glyph)
            before_stats = _glyph_outline_stats(before_glyph)
            after_stats = _glyph_outline_stats(after_glyph)
            if before_signature != after_signature:
                issues.append(
                    GlyphCompatibilityIssue(
                        codepoint=codepoint,
                        character=chr(codepoint) if 32 <= codepoint <= 0x10FFFF else "",
                        reason=_signature_reason(
                            before_signature,
                            after_signature,
                            before_stats=before_stats,
                            after_stats=after_stats,
                        ),
                        geometry_notes=tuple(
                            _geometry_notes(
                                before_signature,
                                after_signature,
                                before_stats=before_stats,
                                after_stats=after_stats,
                            )
                        ),
                        before_signature=before_signature,
                        after_signature=after_signature,
                        before_stats=before_stats,
                        after_stats=after_stats,
                    )
                )
        return CompatibilityReport(
            before_label=before_label,
            after_label=after_label,
            checked_codepoints=tuple(selected_codepoints),
            compared_glyphs=compared,
            before_normalized_coordinates={},
            after_normalized_coordinates={},
            issues=tuple(issues),
            interpolation_issues=(),
        )

    @classmethod
    def compare_variable_instances(
        cls,
        font,
        *,
        before_coordinates: dict[str, float] | None = None,
        after_coordinates: dict[str, float] | None = None,
        before_instance_name: str | None = None,
        after_instance_name: str | None = None,
        codepoints: list[int] | tuple[int, ...] | None = None,
        text: str = "",
    ) -> CompatibilityReport:
        if not hasattr(font, "smart_instancer") or not getattr(font, "is_variable", False):
            raise FontNotSupportedException("Compatibility checking requires a variable TTF font")
        before_resolved = font.smart_instancer.resolve(
            before_coordinates,
            instance_name=before_instance_name,
        )
        after_resolved = font.smart_instancer.resolve(
            after_coordinates,
            instance_name=after_instance_name,
        )
        before_font = font.smart_instancer.instantiate(
            before_coordinates,
            instance_name=before_instance_name,
        )
        after_font = font.smart_instancer.instantiate(
            after_coordinates,
            instance_name=after_instance_name,
        )
        report = cls.compare_fonts(
            before_font,
            after_font,
            before_label=before_resolved.label,
            after_label=after_resolved.label,
            codepoints=codepoints,
            text=text,
        )
        before_normalized = _normalized_coordinates_for_font(font, before_resolved.coordinates)
        after_normalized = _normalized_coordinates_for_font(font, after_resolved.coordinates)
        interpolation_issues = _compare_interpolation_support(
            font,
            before_normalized=before_normalized,
            after_normalized=after_normalized,
            codepoints=report.checked_codepoints,
        )
        return CompatibilityReport(
            before_label=report.before_label,
            after_label=report.after_label,
            checked_codepoints=report.checked_codepoints,
            compared_glyphs=report.compared_glyphs,
            before_normalized_coordinates=before_normalized,
            after_normalized_coordinates=after_normalized,
            issues=report.issues,
            interpolation_issues=interpolation_issues,
        )


def _resolve_codepoints(
    before: Font,
    after: Font,
    *,
    codepoints: list[int] | tuple[int, ...] | None,
    text: str,
) -> list[int]:
    if text:
        return sorted({ord(ch) for ch in text})
    if codepoints:
        return sorted({int(codepoint) for codepoint in codepoints})
    before_codepoints = set(before.encoding.get_all_codepoints())
    after_codepoints = set(after.encoding.get_all_codepoints())
    return sorted(before_codepoints & after_codepoints)


def _glyph_for_codepoint(font: Font, codepoint: int) -> Glyph | None:
    try:
        return font.glyph_accessor.get_glyph_by_unicode(codepoint)
    except GlyphNotFoundException:
        return None


def _glyph_signature(glyph: Glyph | None) -> tuple[str, ...]:
    if glyph is None or glyph.path is None or len(glyph.path) == 0:
        return ()
    return tuple(_command_name(command) for command in glyph.path)


def _glyph_outline_stats(glyph: Glyph | None) -> GlyphOutlineStats:
    if glyph is None or glyph.path is None or len(glyph.path) == 0:
        return GlyphOutlineStats(
            command_count=0,
            point_count=0,
            contour_count=0,
            advance_width=0 if glyph is None else glyph.advance_width,
            line_count=0,
            quadratic_count=0,
            cubic_count=0,
            control_point_count=0,
            closed_contour_count=0,
            open_contour_count=0,
            start_point=None,
            end_point=None,
            bbox=None,
        )
    command_count = len(glyph.path)
    point_count = 0
    contour_count = 0
    line_count = 0
    quadratic_count = 0
    cubic_count = 0
    control_point_count = 0
    closed_contour_count = 0
    current_start_point: tuple[float, float] | None = None
    current_end_point: tuple[float, float] | None = None
    first_start_point: tuple[float, float] | None = None
    open_contour = False
    min_x: float | None = None
    min_y: float | None = None
    max_x: float | None = None
    max_y: float | None = None

    def record_point(x: float, y: float) -> None:
        nonlocal min_x, min_y, max_x, max_y
        min_x = x if min_x is None else min(min_x, x)
        min_y = y if min_y is None else min(min_y, y)
        max_x = x if max_x is None else max(max_x, x)
        max_y = y if max_y is None else max(max_y, y)

    for command in glyph.path:
        if isinstance(command, MoveTo):
            point_count += 1
            record_point(command.x, command.y)
            if open_contour:
                contour_count += 1
            if first_start_point is None:
                first_start_point = (command.x, command.y)
            current_start_point = (command.x, command.y)
            current_end_point = (command.x, command.y)
            open_contour = True
        elif isinstance(command, LineTo):
            point_count += 1
            line_count += 1
            record_point(command.x, command.y)
            current_end_point = (command.x, command.y)
        elif isinstance(command, QuadraticTo):
            point_count += 2
            quadratic_count += 1
            control_point_count += 1
            record_point(command.x1, command.y1)
            record_point(command.x, command.y)
            current_end_point = (command.x, command.y)
        elif isinstance(command, CurveTo):
            point_count += 3
            cubic_count += 1
            control_point_count += 2
            record_point(command.x1, command.y1)
            record_point(command.x2, command.y2)
            record_point(command.x, command.y)
            current_end_point = (command.x, command.y)
        elif isinstance(command, ClosePath):
            if open_contour:
                contour_count += 1
                closed_contour_count += 1
                if current_start_point is not None:
                    current_end_point = current_start_point
                open_contour = False
    if open_contour:
        contour_count += 1
    open_contour_count = contour_count - closed_contour_count
    return GlyphOutlineStats(
        command_count=command_count,
        point_count=point_count,
        contour_count=contour_count,
        advance_width=glyph.advance_width,
        line_count=line_count,
        quadratic_count=quadratic_count,
        cubic_count=cubic_count,
        control_point_count=control_point_count,
        closed_contour_count=closed_contour_count,
        open_contour_count=open_contour_count,
        start_point=first_start_point,
        end_point=current_end_point,
        bbox=None if min_x is None else (min_x, min_y or 0.0, max_x or 0.0, max_y or 0.0),
    )


def _command_name(command) -> str:
    if isinstance(command, MoveTo):
        return "M"
    if isinstance(command, LineTo):
        return "L"
    if isinstance(command, QuadraticTo):
        return "Q"
    if isinstance(command, CurveTo):
        return "C"
    if isinstance(command, ClosePath):
        return "Z"
    return type(command).__name__


def _signature_reason(
    before_signature: tuple[str, ...],
    after_signature: tuple[str, ...],
    *,
    before_stats: GlyphOutlineStats,
    after_stats: GlyphOutlineStats,
) -> str:
    if not before_signature and after_signature:
        return "missing outline in before state"
    if before_signature and not after_signature:
        return "missing outline in after state"
    if len(before_signature) != len(after_signature):
        return "command count differs"
    if before_stats.contour_count != after_stats.contour_count:
        return "contour count differs"
    if before_stats.point_count != after_stats.point_count:
        return "point count differs"
    return "command topology differs"


def _normalized_coordinates_for_font(font, coordinates: dict[str, float]) -> dict[str, float]:
    normalized = TtfInstancer._normalized_coordinates(font, coordinates)
    avar_raw = font.ttf_tables._raw.get("avar")
    if avar_raw is None:
        return normalized
    axis_tags = [axis.tag for axis in font.axes]
    avar = AvarTable.from_reader(BinaryReader(avar_raw), len(avar_raw))
    return {
        axis_tags[index]: avar.map_normalized(index, normalized[axis_tags[index]])
        for index in range(len(axis_tags))
    }


def _compare_interpolation_support(
    font,
    *,
    before_normalized: dict[str, float],
    after_normalized: dict[str, float],
    codepoints: tuple[int, ...],
) -> tuple[GlyphInterpolationIssue, ...]:
    gvar_raw = font.ttf_tables._raw.get("gvar")
    if gvar_raw is None:
        return ()
    axis_tags = [axis.tag for axis in font.axes]
    gvar = GvarTable.from_reader(BinaryReader(gvar_raw), len(gvar_raw), axis_tags)
    issues: list[GlyphInterpolationIssue] = []
    for codepoint in codepoints:
        try:
            gid = int(font.encoding.unicode_to_gid(codepoint))
        except Exception:
            continue
        variations = _glyph_variations_for_gid(font, gvar, gid)
        if not variations:
            continue
        before_active = _active_tuples(variations, before_normalized)
        after_active = _active_tuples(variations, after_normalized)
        issue = _interpolation_issue_for_codepoint(
            codepoint,
            before_active=before_active,
            after_active=after_active,
        )
        if issue is not None:
            issues.append(issue)
    return tuple(issues)


def _glyph_variations_for_gid(font, gvar: GvarTable, gid: int) -> list[TupleVariation]:
    if font.ttf_tables.loca is None or font.ttf_tables.glyf is None:
        return []
    offset = font.ttf_tables.loca.glyph_offset(gid)
    length = font.ttf_tables.loca.glyph_length(gid)
    raw = font.ttf_tables.glyf.get_glyph_bytes(offset, length)
    if len(raw) < 10:
        return []
    contour_count = int.from_bytes(raw[0:2], "big", signed=True)
    if contour_count <= 0:
        return gvar.glyph_variations(gid, 0)
    try:
        simple = TtfInstancer._parse_simple_glyph(raw)
    except Exception:
        return []
    return gvar.glyph_variations(gid, len(simple.xs))


def _active_tuples(
    variations: list[TupleVariation],
    normalized: dict[str, float],
) -> tuple[ActiveTupleSummary, ...]:
    active: list[ActiveTupleSummary] = []
    for tuple_index, variation in enumerate(variations):
        scalar = TtfInstancer._support_scalar(variation, normalized)
        if scalar == 0.0:
            continue
        active.append(
            ActiveTupleSummary(
                tuple_index=tuple_index,
                scalar=scalar,
                peak_coords=dict(variation.peak_coords),
                start_coords=None if variation.start_coords is None else dict(variation.start_coords),
                end_coords=None if variation.end_coords is None else dict(variation.end_coords),
            )
        )
    return tuple(active)


def _interpolation_issue_for_codepoint(
    codepoint: int,
    *,
    before_active: tuple[ActiveTupleSummary, ...],
    after_active: tuple[ActiveTupleSummary, ...],
) -> GlyphInterpolationIssue | None:
    before_lookup = {item.tuple_index: item for item in before_active}
    after_lookup = {item.tuple_index: item for item in after_active}
    if not before_lookup and not after_lookup:
        return None
    entered = tuple(sorted(index for index in after_lookup if index not in before_lookup))
    exited = tuple(sorted(index for index in before_lookup if index not in after_lookup))
    retuned = tuple(
        TupleScalarDelta(
            tuple_index=index,
            before_scalar=before_lookup[index].scalar,
            after_scalar=after_lookup[index].scalar,
        )
        for index in sorted(before_lookup.keys() & after_lookup.keys())
        if abs(before_lookup[index].scalar - after_lookup[index].scalar) > 1e-6
    )
    if not entered and not exited and not retuned:
        return None
    if entered and exited:
        reason = "active variation tuples changed"
    elif entered:
        reason = "variation tuples became active"
    elif exited:
        reason = "variation tuples became inactive"
    else:
        reason = "active tuple scalars changed"
    return GlyphInterpolationIssue(
        codepoint=codepoint,
        character=chr(codepoint) if 32 <= codepoint <= 0x10FFFF else "",
        reason=reason,
        before_active=before_active,
        after_active=after_active,
        entered_tuple_indices=entered,
        exited_tuple_indices=exited,
        retuned_tuples=retuned,
    )


def _geometry_notes(
    before_signature: tuple[str, ...],
    after_signature: tuple[str, ...],
    *,
    before_stats: GlyphOutlineStats,
    after_stats: GlyphOutlineStats,
) -> list[str]:
    notes: list[str] = []
    if before_stats.line_count != after_stats.line_count:
        notes.append(f"line segments {before_stats.line_count}->{after_stats.line_count}")
    if before_stats.quadratic_count != after_stats.quadratic_count:
        notes.append(f"quadratic segments {before_stats.quadratic_count}->{after_stats.quadratic_count}")
    if before_stats.cubic_count != after_stats.cubic_count:
        notes.append(f"cubic segments {before_stats.cubic_count}->{after_stats.cubic_count}")
    if before_stats.control_point_count != after_stats.control_point_count:
        notes.append(
            f"control points {before_stats.control_point_count}->{after_stats.control_point_count}"
        )
    if (
        before_stats.closed_contour_count != after_stats.closed_contour_count
        or before_stats.open_contour_count != after_stats.open_contour_count
    ):
        notes.append(
            "open/closed contours "
            f"{before_stats.open_contour_count}/{before_stats.closed_contour_count}"
            f"->{after_stats.open_contour_count}/{after_stats.closed_contour_count}"
        )
    before_bbox_size = _bbox_size(before_stats.bbox)
    after_bbox_size = _bbox_size(after_stats.bbox)
    if before_bbox_size != after_bbox_size and before_bbox_size is not None and after_bbox_size is not None:
        notes.append(
            "bbox size "
            f"{_format_point(before_bbox_size)}->{_format_point(after_bbox_size)}"
        )
    if before_stats.start_point != after_stats.start_point:
        notes.append(
            "start point "
            f"{_format_optional_point(before_stats.start_point)}"
            f"->{_format_optional_point(after_stats.start_point)}"
        )
    if before_stats.end_point != after_stats.end_point:
        notes.append(
            "end point "
            f"{_format_optional_point(before_stats.end_point)}"
            f"->{_format_optional_point(after_stats.end_point)}"
        )
    if before_signature != after_signature and not notes:
        notes.append("signature ordering changed")
    return notes


def _bbox_size(bbox: tuple[float, float, float, float] | None) -> tuple[float, float] | None:
    if bbox is None:
        return None
    min_x, min_y, max_x, max_y = bbox
    return (max_x - min_x, max_y - min_y)


def _format_number(value: float) -> str:
    return f"{value:.4f}".rstrip("0").rstrip(".") or "0"


def _format_point(point: tuple[float, float]) -> str:
    return ",".join(_format_number(value) for value in point)


def _format_optional_point(point: tuple[float, float] | None) -> str:
    if point is None:
        return "-"
    return _format_point(point)


__all__ = [
    "ActiveTupleSummary",
    "GlyphOutlineStats",
    "GlyphCompatibilityIssue",
    "GlyphInterpolationIssue",
    "CompatibilityChecker",
    "CompatibilityReport",
    "TupleScalarDelta",
]
