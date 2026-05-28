"""Variable-font instancing helpers for glyf/gvar TrueType fonts."""

from __future__ import annotations

import copy
import dataclasses
import re

from aspose_font._exceptions import FontNotSupportedException, FontParseException
from aspose_font._io import BinaryReader, BinaryWriter
from aspose_font.loader import FontLoader
from aspose_font.serializer import TtfSerializer
from aspose_font.ttf.font import TtfFont
from aspose_font.ttf.tables import GlyfTable, HMetric, LocaTable, TtfTableSet
from aspose_font.ttf.tables.avar import AvarTable
from aspose_font.ttf.tables.gvar import GvarTable, TupleVariation
from aspose_font.ttf.tables.name import NameTable
from aspose_font.ttf.tables.stat import (
    build_static_stat_table,
    extract_stat_name_ids,
    normalize_static_stat_policy,
)

_VARIABLE_TABLES_TO_DROP = {"HVAR", "MVAR", "VVAR", "STAT", "avar", "cvar", "fvar", "gvar"}
_ON_CURVE_POINT = 0x01
_X_SHORT_VECTOR = 0x02
_Y_SHORT_VECTOR = 0x04
_REPEAT_FLAG = 0x08
_X_IS_SAME_OR_POSITIVE_X_SHORT_VECTOR = 0x10
_Y_IS_SAME_OR_POSITIVE_Y_SHORT_VECTOR = 0x20
INSTANCE_NAMING_STRATEGIES = ("instance-family", "preserve-family", "qa-tagged", "menu-safe", "ribbi-safe")
_ARG_1_AND_2_ARE_WORDS = 0x0001
_ARGS_ARE_XY_VALUES = 0x0002
_WE_HAVE_A_SCALE = 0x0008
_MORE_COMPONENTS = 0x0020
_WE_HAVE_AN_X_AND_Y_SCALE = 0x0040
_WE_HAVE_A_TWO_BY_TWO = 0x0080
_WE_HAVE_INSTRUCTIONS = 0x0100


@dataclasses.dataclass(slots=True)
class _SimpleGlyph:
    contour_ends: list[int]
    xs: list[int]
    ys: list[int]
    on_curve: list[bool]
    instructions: bytes


@dataclasses.dataclass(slots=True)
class _CompositeComponent:
    flags: int
    glyph_id: int
    arg1: int
    arg2: int
    args_are_xy_values: bool
    xx: float
    yx: float
    xy: float
    yy: float

    @property
    def dx(self) -> float:
        return float(self.arg1) if self.args_are_xy_values else 0.0

    @property
    def dy(self) -> float:
        return float(self.arg2) if self.args_are_xy_values else 0.0


@dataclasses.dataclass(slots=True)
class _CompositeGlyph:
    components: list[_CompositeComponent]
    instructions: bytes


@dataclasses.dataclass(slots=True)
class _InstantiatedGlyph:
    data: bytes
    lsb: int | None = None
    advance_width: int | None = None


@dataclasses.dataclass(slots=True, frozen=True)
class NamingPolicyPreview:
    """Dry-run result for generated static-instance name records."""

    naming_strategy: str
    family_suffix: str | None
    coordinates: dict[str, float]
    source_instance_name: str | None
    legacy_family_name: str
    legacy_style_name: str
    full_name: str
    postscript_name: str
    typographic_family_name: str
    typographic_style_name: str
    warnings: tuple[str, ...] = ()
    stat_diagnostics: "StatNamingDiagnostics | None" = None
    platform_diagnostics: "PlatformNamingDiagnostics | None" = None

    @property
    def name_ids(self) -> dict[int, str]:
        return {
            1: self.legacy_family_name,
            2: self.legacy_style_name,
            4: self.full_name,
            6: self.postscript_name,
            16: self.typographic_family_name,
            17: self.typographic_style_name,
            21: self.typographic_family_name,
            22: self.typographic_style_name,
            25: self.typographic_family_name,
        }

    def to_dict(self) -> dict[str, object]:
        return {
            "naming_strategy": self.naming_strategy,
            "family_suffix": self.family_suffix,
            "coordinates": dict(self.coordinates),
            "source_instance_name": self.source_instance_name,
            "legacy_family_name": self.legacy_family_name,
            "legacy_style_name": self.legacy_style_name,
            "full_name": self.full_name,
            "postscript_name": self.postscript_name,
            "typographic_family_name": self.typographic_family_name,
            "typographic_style_name": self.typographic_style_name,
            "name_ids": {str(name_id): value for name_id, value in self.name_ids.items()},
            "stat_diagnostics": (
                None if self.stat_diagnostics is None else self.stat_diagnostics.to_dict()
            ),
            "platform_diagnostics": (
                None if self.platform_diagnostics is None else self.platform_diagnostics.to_dict()
            ),
            "warnings": list(self.warnings),
        }


@dataclasses.dataclass(slots=True, frozen=True)
class StatNamingDiagnostics:
    stat_policy: str
    source_has_stat: bool
    static_export_action: str
    typographic_family_ids_emitted: tuple[int, ...]
    typographic_style_ids_emitted: tuple[int, ...]
    legacy_typographic_family_diverges: bool
    legacy_typographic_style_diverges: bool
    source_stat_name_ids: tuple[int, ...] = ()
    covered_source_stat_name_ids: tuple[int, ...] = ()
    uncovered_source_stat_name_ids: tuple[int, ...] = ()
    source_stat_name_labels: tuple[tuple[int, str | None, bool], ...] = ()
    generated_stat_name_ids: tuple[int, ...] = ()
    generated_stat_axis_tags: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "stat_policy": self.stat_policy,
            "source_has_stat": self.source_has_stat,
            "static_export_action": self.static_export_action,
            "typographic_family_ids_emitted": list(self.typographic_family_ids_emitted),
            "typographic_style_ids_emitted": list(self.typographic_style_ids_emitted),
            "source_stat_name_ids": list(self.source_stat_name_ids),
            "covered_source_stat_name_ids": list(self.covered_source_stat_name_ids),
            "uncovered_source_stat_name_ids": list(self.uncovered_source_stat_name_ids),
            "source_stat_name_labels": [
                {"name_id": name_id, "label": label, "covered": covered}
                for name_id, label, covered in self.source_stat_name_labels
            ],
            "generated_stat_name_ids": list(self.generated_stat_name_ids),
            "generated_stat_axis_tags": list(self.generated_stat_axis_tags),
            "legacy_typographic_family_diverges": self.legacy_typographic_family_diverges,
            "legacy_typographic_style_diverges": self.legacy_typographic_style_diverges,
            "notes": list(self.notes),
            "warnings": list(self.warnings),
        }


@dataclasses.dataclass(slots=True, frozen=True)
class PlatformNamingDiagnostics:
    windows_legacy_menu_safe: bool
    windows_legacy_style_ribbi: bool
    macos_typographic_names_present: bool
    macos_typographic_names_diverge: bool
    postscript_name_safe: bool
    postscript_name_length: int
    postscript_name_sanitized: bool
    notes: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "windows_legacy_menu_safe": self.windows_legacy_menu_safe,
            "windows_legacy_style_ribbi": self.windows_legacy_style_ribbi,
            "macos_typographic_names_present": self.macos_typographic_names_present,
            "macos_typographic_names_diverge": self.macos_typographic_names_diverge,
            "postscript_name_safe": self.postscript_name_safe,
            "postscript_name_length": self.postscript_name_length,
            "postscript_name_sanitized": self.postscript_name_sanitized,
            "notes": list(self.notes),
            "warnings": list(self.warnings),
        }


class TtfInstancer:
    @classmethod
    def preview_naming_policy(
        cls,
        font: TtfFont,
        coordinates: dict[str, float],
        *,
        naming_strategy: str = "instance-family",
        family_suffix: str | None = None,
        legacy_family_name: str | None = None,
        typographic_family_name: str | None = None,
        legacy_style_name: str | None = None,
        typographic_style_name: str | None = None,
        stat_policy: str = "drop",
    ) -> NamingPolicyPreview:
        if font.fvar is None:
            raise FontNotSupportedException("Font is not variable")
        return cls._build_naming_preview(
            font,
            cls._clamped_coordinates(font, coordinates),
            naming_strategy=naming_strategy,
            family_suffix=family_suffix,
            legacy_family_name=legacy_family_name,
            typographic_family_name=typographic_family_name,
            legacy_style_name=legacy_style_name,
            typographic_style_name=typographic_style_name,
            stat_policy=stat_policy,
        )

    @classmethod
    def instantiate(
        cls,
        font: TtfFont,
        coordinates: dict[str, float],
        *,
        naming_strategy: str = "instance-family",
        family_suffix: str | None = None,
        legacy_family_name: str | None = None,
        typographic_family_name: str | None = None,
        legacy_style_name: str | None = None,
        typographic_style_name: str | None = None,
        stat_policy: str = "drop",
    ) -> TtfFont:
        tables = font.ttf_tables
        if font.fvar is None:
            raise FontNotSupportedException("Font is not variable")
        if font.cff_font is not None:
            raise FontNotSupportedException("CFF2 variable fonts are not supported")
        if tables.head is None or tables.maxp is None or tables.loca is None or tables.glyf is None:
            raise FontNotSupportedException("Variable font instancing requires glyf/loca/head/maxp")
        gvar_raw = tables._raw.get("gvar")
        if gvar_raw is None:
            raise FontNotSupportedException("Variable font instancing requires gvar")
        normalized_stat_policy = normalize_static_stat_policy(stat_policy)

        axis_tags = [axis.tag for axis in font.axes]
        clamped_coordinates = cls._clamped_coordinates(font, coordinates)
        normalized = cls._normalized_coordinates(font, clamped_coordinates)
        avar_raw = tables._raw.get("avar")
        if avar_raw is not None:
            avar = AvarTable.from_reader(BinaryReader(avar_raw), len(avar_raw))
            normalized = {
                axis_tags[i]: avar.map_normalized(i, normalized[axis_tags[i]])
                for i in range(len(axis_tags))
            }

        gvar = GvarTable.from_reader(BinaryReader(gvar_raw), len(gvar_raw), axis_tags)
        hvar = font.hvar
        instantiated_by_gid: dict[int, _InstantiatedGlyph] = {}
        visiting: set[int] = set()

        def instantiate_gid(gid: int) -> _InstantiatedGlyph:
            cached = instantiated_by_gid.get(gid)
            if cached is not None:
                return cached
            if gid in visiting:
                raise FontParseException(f"Composite glyph recursion limit at GID {gid}", format_name="TTF")
            visiting.add(gid)
            try:
                offset = tables.loca.glyph_offset(gid)
                length = tables.loca.glyph_length(gid)
                raw = tables.glyf.get_glyph_bytes(offset, length)
                metric = tables.hmtx.get_metric(gid)
                instantiated = cls._instantiate_glyph(
                    raw,
                    gvar,
                    gid,
                    normalized,
                    metric.advance_width,
                    metric.lsb,
                    instantiate_gid,
                )
                instantiated_by_gid[gid] = instantiated
                return instantiated
            finally:
                visiting.remove(gid)

        glyf_chunks: list[bytes] = []
        loca_offsets = [0]
        cursor = 0
        x_min = 0
        y_min = 0
        x_max = 0
        y_max = 0
        has_bounds = False

        for gid in range(tables.maxp.num_glyphs):
            instantiated = instantiate_gid(gid)
            if instantiated.data:
                bounds = cls._glyph_bounds(instantiated.data)
                if bounds is not None:
                    gx_min, gy_min, gx_max, gy_max = bounds
                    if not has_bounds:
                        x_min, y_min, x_max, y_max = bounds
                        has_bounds = True
                    else:
                        x_min = min(x_min, gx_min)
                        y_min = min(y_min, gy_min)
                        x_max = max(x_max, gx_max)
                        y_max = max(y_max, gy_max)
            pad = (4 - len(instantiated.data) % 4) % 4
            glyf_chunks.append(instantiated.data + (b"\x00" * pad))
            cursor += len(instantiated.data) + pad
            loca_offsets.append(cursor)

        new_hmtx = copy.deepcopy(tables.hmtx)
        new_hhea = copy.deepcopy(tables.hhea)
        if new_hmtx is not None:
            for gid, instantiated in instantiated_by_gid.items():
                metric = new_hmtx.metrics[gid]
                new_hmtx.metrics[gid] = HMetric(
                    advance_width=(
                        instantiated.advance_width
                        if instantiated.advance_width is not None and hvar is None
                        else metric.advance_width
                    ),
                    lsb=instantiated.lsb if instantiated.lsb is not None else metric.lsb,
                )
        if new_hmtx is not None and new_hhea is not None and hvar is not None:
            cls._apply_hvar_metrics(
                new_hmtx,
                new_hhea,
                normalized=normalized,
                hvar=hvar,
            )

        new_head = copy.deepcopy(tables.head)
        if has_bounds:
            new_head.x_min = x_min
            new_head.y_min = y_min
            new_head.x_max = x_max
            new_head.y_max = y_max

        new_name = copy.deepcopy(tables.name)
        naming_preview = None
        if new_name is not None:
            naming_preview = cls._apply_instance_names(
                font,
                new_name,
                clamped_coordinates,
                naming_strategy=naming_strategy,
                family_suffix=family_suffix,
                legacy_family_name=legacy_family_name,
                typographic_family_name=typographic_family_name,
                legacy_style_name=legacy_style_name,
                typographic_style_name=typographic_style_name,
                stat_policy=normalized_stat_policy,
            )
        elif normalized_stat_policy == "static":
            raise FontParseException("STAT static policy requires a name table", format_name="TTF")

        raw_tables = {tag: data for tag, data in tables._raw.items() if tag not in _VARIABLE_TABLES_TO_DROP}
        if normalized_stat_policy == "static":
            if naming_preview is None:
                raise FontParseException("STAT static policy requires generated naming metadata", format_name="TTF")
            raw_tables["STAT"] = build_static_stat_table(
                font.axes,
                clamped_coordinates,
                value_name_id=17,
                elided_fallback_name_id=2,
            )

        new_tables = TtfTableSet(
            head=new_head,
            hhea=new_hhea,
            maxp=copy.deepcopy(tables.maxp),
            os2=copy.deepcopy(tables.os2),
            name=new_name,
            post=copy.deepcopy(tables.post),
            cmap=copy.deepcopy(tables.cmap),
            loca=LocaTable(offsets=loca_offsets),
            hmtx=new_hmtx,
            kern=copy.deepcopy(tables.kern),
            glyf=GlyfTable(_data=b"".join(glyf_chunks)),
            fvar=None,
            _raw=raw_tables,
        )
        static_font = TtfFont(sfnt_data=b"", tables=new_tables, sfnt_version=font._sfnt_version)
        return FontLoader.open(TtfSerializer.serialize(static_font))

    @classmethod
    def _apply_hvar_metrics(
        cls,
        hmtx,
        hhea,
        *,
        normalized: dict[str, float],
        hvar,
    ) -> None:
        updated_metrics: list[HMetric] = []
        for gid, metric in enumerate(hmtx.metrics):
            delta = hvar.advance_width_delta(gid, normalized)
            updated_metrics.append(
                HMetric(
                    advance_width=max(0, metric.advance_width + cls._ot_round(delta)),
                    lsb=metric.lsb,
                )
            )
        hmtx.metrics = updated_metrics
        hhea.advance_width_max = max(
            (metric.advance_width for metric in updated_metrics),
            default=0,
        )
        hhea.number_of_hmetrics = cls._number_of_hmetrics(updated_metrics)

    @staticmethod
    def _number_of_hmetrics(metrics: list[HMetric]) -> int:
        if not metrics:
            return 0
        count = len(metrics)
        last_advance = metrics[-1].advance_width
        while count > 1 and metrics[count - 2].advance_width == last_advance:
            count -= 1
        return count

    @classmethod
    def _instantiate_glyph(
        cls,
        raw: bytes,
        gvar: GvarTable,
        gid: int,
        normalized: dict[str, float],
        advance_width: int,
        lsb: int,
        instantiate_gid,
    ) -> _InstantiatedGlyph:
        if len(raw) < 10:
            return _InstantiatedGlyph(data=raw)
        contour_count = int.from_bytes(raw[0:2], "big", signed=True)
        if contour_count == 0:
            phantom_dx, _phantom_dy = cls._phantom_variation_deltas(gvar, gid, normalized)
            updated_lsb, updated_advance = cls._metric_overrides_from_phantoms(
                raw,
                advance_width=advance_width,
                lsb=lsb,
                phantom_dx=phantom_dx,
                new_bounds=cls._glyph_bounds(raw),
            )
            return _InstantiatedGlyph(data=raw, lsb=updated_lsb, advance_width=updated_advance)
        if contour_count < 0:
            composite = cls._parse_composite_glyph(raw)
            composite, phantom_dx, _phantom_dy = cls._apply_composite_variations(
                composite,
                gvar,
                gid,
                normalized,
            )
            bounds = cls._composite_bounds(composite, instantiate_gid)
            data = cls._encode_composite_glyph(composite, bounds)
            updated_lsb, updated_advance = cls._metric_overrides_from_phantoms(
                raw,
                advance_width=advance_width,
                lsb=lsb,
                phantom_dx=phantom_dx,
                new_bounds=bounds,
            )
            return _InstantiatedGlyph(data=data, lsb=updated_lsb, advance_width=updated_advance)

        simple = cls._parse_simple_glyph(raw)
        variations = gvar.glyph_variations(gid, len(simple.xs))
        if not variations:
            return _InstantiatedGlyph(data=raw)

        total_points = len(simple.xs)
        dx = [0.0] * total_points
        dy = [0.0] * total_points
        phantom_dx = [0.0] * 4
        phantom_dy = [0.0] * 4
        changed = False

        for variation in variations:
            scalar = cls._support_scalar(variation, normalized)
            if scalar == 0.0:
                continue
            changed = True
            varied_dx, varied_dy, varied_phantom_dx, varied_phantom_dy = cls._expand_simple_deltas(
                simple,
                variation,
            )
            for point_index in range(total_points):
                dx[point_index] += varied_dx[point_index] * scalar
                dy[point_index] += varied_dy[point_index] * scalar
            for phantom_index in range(4):
                phantom_dx[phantom_index] += varied_phantom_dx[phantom_index] * scalar
                phantom_dy[phantom_index] += varied_phantom_dy[phantom_index] * scalar

        if not changed:
            return _InstantiatedGlyph(data=raw)

        varied_xs = [simple.xs[i] + cls._ot_round(dx[i]) for i in range(total_points)]
        varied_ys = [simple.ys[i] + cls._ot_round(dy[i]) for i in range(total_points)]
        data = cls._encode_simple_glyph(
            contour_ends=simple.contour_ends,
            xs=varied_xs,
            ys=varied_ys,
            on_curve=simple.on_curve,
            instructions=simple.instructions,
        )
        updated_lsb, updated_advance = cls._metric_overrides_from_phantoms(
            raw,
            advance_width=advance_width,
            lsb=lsb,
            phantom_dx=phantom_dx,
            new_bounds=cls._glyph_bounds(data),
        )
        return _InstantiatedGlyph(data=data, lsb=updated_lsb, advance_width=updated_advance)

    @staticmethod
    def _clamped_coordinates(font: TtfFont, coordinates: dict[str, float]) -> dict[str, float]:
        return {
            axis.tag: min(max(float(coordinates.get(axis.tag, axis.default_value)), axis.min_value), axis.max_value)
            for axis in font.axes
        }

    @classmethod
    def _normalized_coordinates(cls, font: TtfFont, coordinates: dict[str, float]) -> dict[str, float]:
        normalized: dict[str, float] = {}
        for axis in font.axes:
            user_value = coordinates[axis.tag]
            if user_value == axis.default_value:
                normalized[axis.tag] = 0.0
            elif user_value < axis.default_value:
                denom = axis.default_value - axis.min_value
                normalized[axis.tag] = 0.0 if denom == 0 else (user_value - axis.default_value) / denom
            else:
                denom = axis.max_value - axis.default_value
                normalized[axis.tag] = 0.0 if denom == 0 else (user_value - axis.default_value) / denom
        return normalized

    @classmethod
    def _apply_instance_names(
        cls,
        font: TtfFont,
        name_table: NameTable,
        coordinates: dict[str, float],
        *,
        naming_strategy: str,
        family_suffix: str | None,
        legacy_family_name: str | None,
        typographic_family_name: str | None,
        legacy_style_name: str | None,
        typographic_style_name: str | None,
        stat_policy: str,
    ) -> NamingPolicyPreview:
        preview = cls._build_naming_preview(
            font,
            coordinates,
            naming_strategy=naming_strategy,
            family_suffix=family_suffix,
            legacy_family_name=legacy_family_name,
            typographic_family_name=typographic_family_name,
            legacy_style_name=legacy_style_name,
            typographic_style_name=typographic_style_name,
            stat_policy=stat_policy,
        )

        name_table.replace_name(1, preview.legacy_family_name)
        name_table.replace_name(2, preview.legacy_style_name)
        name_table.replace_name(4, preview.full_name)
        name_table.replace_name(6, preview.postscript_name)
        name_table.replace_name(16, preview.typographic_family_name)
        name_table.replace_name(17, preview.typographic_style_name)
        name_table.replace_name(21, preview.typographic_family_name)
        name_table.replace_name(22, preview.typographic_style_name)
        name_table.replace_name(25, preview.typographic_family_name)
        for name_id, value in preview.name_ids.items():
            name_table.ensure_english_platform_names(name_id, value)
        name_table.remove_name_ids([26])
        return preview

    @classmethod
    def _build_naming_preview(
        cls,
        font: TtfFont,
        coordinates: dict[str, float],
        *,
        naming_strategy: str,
        family_suffix: str | None,
        legacy_family_name: str | None,
        typographic_family_name: str | None,
        legacy_style_name: str | None,
        typographic_style_name: str | None,
        stat_policy: str,
    ) -> NamingPolicyPreview:
        strategy = cls._normalize_naming_strategy(naming_strategy)
        normalized_stat_policy = normalize_static_stat_policy(stat_policy)
        normalized_suffix = cls._normalize_family_suffix(family_suffix)
        legacy_override = cls._normalize_family_override(legacy_family_name, "legacy_family_name")
        typographic_override = cls._normalize_family_override(
            typographic_family_name,
            "typographic_family_name",
        )
        legacy_style_override = cls._normalize_family_override(legacy_style_name, "legacy_style_name")
        typographic_style_override = cls._normalize_family_override(
            typographic_style_name,
            "typographic_style_name",
        )
        name_table = font.ttf_tables.name
        source_legacy_family = font.font_family or "Font"
        source_legacy_style = font.font_style or "Regular"
        source_postscript = name_table.best_name(6) if name_table is not None else None
        base_family = (
            (name_table.best_name(16) or name_table.best_name(1))
            if name_table is not None
            else None
        ) or font.font_family or "Font"
        style_label = cls._instance_style_label(font, coordinates)
        typographic_style_label = style_label
        legacy_style_label = cls._legacy_style_name_for_strategy(
            font,
            coordinates,
            style_label,
            strategy,
        )
        legacy_family_name = cls._legacy_family_name_for_strategy(
            base_family,
            strategy,
            normalized_suffix,
        )
        typographic_family_name = cls._typographic_family_name_for_strategy(
            base_family,
            strategy,
            normalized_suffix,
        )
        if legacy_override is not None:
            legacy_family_name = legacy_override
        if typographic_override is not None:
            typographic_family_name = typographic_override
        if legacy_style_override is not None:
            legacy_style_label = legacy_style_override
        if typographic_style_override is not None:
            typographic_style_label = typographic_style_override
        full_name = cls._full_name_for_strategy(legacy_family_name, typographic_style_label, strategy)
        postscript_name = cls._sanitize_postscript(legacy_family_name, typographic_style_label)
        warnings: list[str] = []
        if (
            legacy_family_name.casefold() == source_legacy_family.casefold()
            and legacy_style_label.casefold() == source_legacy_style.casefold()
        ):
            warnings.append("legacy-menu-collision: name IDs 1 and 2 match the source font menu names.")
        if source_postscript and postscript_name.casefold() == source_postscript.casefold():
            warnings.append("postscript-collision: name ID 6 matches the source PostScript name.")
        stat_diagnostics = cls._stat_naming_diagnostics(
            font,
            legacy_family_name=legacy_family_name,
            legacy_style_label=legacy_style_label,
            typographic_family_name=typographic_family_name,
            typographic_style_label=typographic_style_label,
            stat_policy=normalized_stat_policy,
        )
        warnings.extend(stat_diagnostics.warnings)
        platform_diagnostics = cls._platform_naming_diagnostics(
            source_legacy_family=source_legacy_family,
            source_legacy_style=source_legacy_style,
            source_postscript=source_postscript,
            legacy_family_name=legacy_family_name,
            legacy_style_label=legacy_style_label,
            typographic_family_name=typographic_family_name,
            typographic_style_label=typographic_style_label,
            postscript_name=postscript_name,
        )
        warnings.extend(platform_diagnostics.warnings)

        return NamingPolicyPreview(
            naming_strategy=strategy,
            family_suffix=normalized_suffix,
            coordinates=dict(coordinates),
            source_instance_name=cls._matched_instance_label(font, coordinates),
            legacy_family_name=legacy_family_name,
            legacy_style_name=legacy_style_label,
            full_name=full_name,
            postscript_name=postscript_name,
            typographic_family_name=typographic_family_name,
            typographic_style_name=typographic_style_label,
            warnings=tuple(warnings),
            stat_diagnostics=stat_diagnostics,
            platform_diagnostics=platform_diagnostics,
        )

    @staticmethod
    def _stat_naming_diagnostics(
        font: TtfFont,
        *,
        legacy_family_name: str,
        legacy_style_label: str,
        typographic_family_name: str,
        typographic_style_label: str,
        stat_policy: str,
    ) -> StatNamingDiagnostics:
        stat_raw = font.ttf_tables._raw.get("STAT")
        source_has_stat = stat_raw is not None
        source_stat_name_ids = extract_stat_name_ids(stat_raw) if stat_raw is not None else ()
        emitted_name_ids = {1, 2, 4, 6, 16, 17, 21, 22, 25}
        generated_stat_name_ids = tuple(sorted({2, 17, *(axis.name_id for axis in font.axes)}))
        generated_stat_axis_tags = tuple(axis.tag for axis in font.axes)
        covered_source_stat_name_ids = tuple(
            name_id for name_id in source_stat_name_ids if name_id in emitted_name_ids
        )
        uncovered_source_stat_name_ids = tuple(
            name_id for name_id in source_stat_name_ids if name_id not in emitted_name_ids
        )
        name_table = font.ttf_tables.name
        source_stat_name_labels = tuple(
            (
                name_id,
                name_table.best_name(name_id) if name_table is not None else None,
                name_id in emitted_name_ids,
            )
            for name_id in source_stat_name_ids
        )
        family_diverges = legacy_family_name.casefold() != typographic_family_name.casefold()
        style_diverges = legacy_style_label.casefold() != typographic_style_label.casefold()
        notes = [
            "Generated static instances emit typographic family/style name IDs 16/17/21/22/25.",
        ]
        warnings: list[str] = []
        if stat_policy == "static":
            notes.append(
                "Generated static instance will synthesize a STAT 1.1 table with source fvar axes "
                "and one format-4 AxisValue for the resolved coordinates."
            )
            static_export_action = "synthesize-static-stat"
        elif source_has_stat:
            notes.append("Source font contains a STAT table.")
            if source_stat_name_ids:
                notes.append(
                    "Source STAT references name IDs "
                    f"{','.join(str(name_id) for name_id in source_stat_name_ids)}."
                )
            else:
                notes.append("Source STAT name IDs could not be parsed or are not present.")
            warnings.append(
                "stat-dropped: static variable-font instancing removes the source STAT table; "
                "name-table diagnostics are provided but STAT reconstruction is not performed."
            )
            static_export_action = "drop-source-stat"
        else:
            notes.append("Source font does not contain a STAT table.")
            static_export_action = "none"
        if family_diverges or style_diverges:
            notes.append(
                "Legacy menu names diverge from typographic names; modern apps may use typographic "
                "name IDs while legacy menus use IDs 1/2."
            )
        return StatNamingDiagnostics(
            stat_policy=stat_policy,
            source_has_stat=source_has_stat,
            static_export_action=static_export_action,
            typographic_family_ids_emitted=(16, 21, 25),
            typographic_style_ids_emitted=(17, 22),
            legacy_typographic_family_diverges=family_diverges,
            legacy_typographic_style_diverges=style_diverges,
            source_stat_name_ids=source_stat_name_ids,
            covered_source_stat_name_ids=covered_source_stat_name_ids,
            uncovered_source_stat_name_ids=uncovered_source_stat_name_ids,
            source_stat_name_labels=source_stat_name_labels,
            generated_stat_name_ids=generated_stat_name_ids if stat_policy == "static" else (),
            generated_stat_axis_tags=generated_stat_axis_tags if stat_policy == "static" else (),
            notes=tuple(notes),
            warnings=tuple(warnings),
        )

    @staticmethod
    def _platform_naming_diagnostics(
        *,
        source_legacy_family: str,
        source_legacy_style: str,
        source_postscript: str | None,
        legacy_family_name: str,
        legacy_style_label: str,
        typographic_family_name: str,
        typographic_style_label: str,
        postscript_name: str,
    ) -> PlatformNamingDiagnostics:
        legacy_menu_collision = (
            legacy_family_name.casefold() == source_legacy_family.casefold()
            and legacy_style_label.casefold() == source_legacy_style.casefold()
        )
        postscript_collision = (
            source_postscript is not None
            and postscript_name.casefold() == source_postscript.casefold()
        )
        windows_legacy_style_ribbi = legacy_style_label in {
            "Regular",
            "Bold",
            "Italic",
            "Bold Italic",
        }
        postscript_name_safe = (
            len(postscript_name) <= 63
            and bool(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9]*-[A-Za-z0-9]+", postscript_name))
            and not postscript_collision
        )
        postscript_name_sanitized = f"{legacy_family_name}-{typographic_style_label}" != postscript_name
        typographic_diverges = (
            legacy_family_name.casefold() != typographic_family_name.casefold()
            or legacy_style_label.casefold() != typographic_style_label.casefold()
        )
        notes = [
            "Windows legacy menus primarily use name IDs 1/2.",
            "macOS and modern apps can prefer typographic name IDs 16/17/21/22/25.",
            "PostScript name ID 6 should stay ASCII-only, unique, and short.",
        ]
        warnings: list[str] = []
        if legacy_menu_collision:
            warnings.append(
                "windows-menu-collision: name IDs 1/2 match the source font legacy menu names."
            )
        if not windows_legacy_style_ribbi:
            warnings.append(
                "windows-non-ribbi-style: legacy style name is not Regular/Bold/Italic/Bold Italic."
            )
        if postscript_collision:
            warnings.append("postscript-platform-collision: name ID 6 matches the source font.")
        if len(postscript_name) > 63:
            warnings.append("postscript-name-long: name ID 6 is longer than 63 characters.")
        if postscript_name_sanitized:
            warnings.append(
                "postscript-name-sanitized: name ID 6 stripped unsupported characters from "
                "family/style names."
            )
        return PlatformNamingDiagnostics(
            windows_legacy_menu_safe=not legacy_menu_collision,
            windows_legacy_style_ribbi=windows_legacy_style_ribbi,
            macos_typographic_names_present=True,
            macos_typographic_names_diverge=typographic_diverges,
            postscript_name_safe=postscript_name_safe,
            postscript_name_length=len(postscript_name),
            postscript_name_sanitized=postscript_name_sanitized,
            notes=tuple(notes),
            warnings=tuple(warnings),
        )

    @staticmethod
    def available_naming_strategies() -> tuple[str, ...]:
        return INSTANCE_NAMING_STRATEGIES

    @staticmethod
    def _normalize_naming_strategy(value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in INSTANCE_NAMING_STRATEGIES:
            choices = ", ".join(INSTANCE_NAMING_STRATEGIES)
            raise ValueError(
                f"Unknown naming strategy {value!r}. Expected one of: {choices}"
            )
        return normalized

    @staticmethod
    def _normalize_family_suffix(value: str | None) -> str | None:
        if value is None:
            return None
        normalized = " ".join(value.strip().split())
        return normalized or None

    @staticmethod
    def _normalize_family_override(value: str | None, field_name: str) -> str | None:
        if value is None:
            return None
        normalized = " ".join(value.strip().split())
        if not normalized:
            raise ValueError(f"{field_name} must not be blank")
        return normalized

    @staticmethod
    def _legacy_family_name_for_strategy(
        base_family: str,
        naming_strategy: str,
        family_suffix: str | None,
    ) -> str:
        if family_suffix:
            return f"{base_family} {family_suffix}"
        if naming_strategy == "preserve-family":
            return base_family
        if naming_strategy == "qa-tagged":
            return f"{base_family} QA"
        return f"{base_family} Instance"

    @staticmethod
    def _typographic_family_name_for_strategy(
        base_family: str,
        naming_strategy: str,
        family_suffix: str | None,
    ) -> str:
        if naming_strategy in {"menu-safe", "ribbi-safe"}:
            return base_family
        return TtfInstancer._legacy_family_name_for_strategy(
            base_family,
            naming_strategy,
            family_suffix,
        )

    @classmethod
    def _legacy_style_name_for_strategy(
        cls,
        font: TtfFont,
        coordinates: dict[str, float],
        style_label: str,
        naming_strategy: str,
    ) -> str:
        if naming_strategy != "ribbi-safe":
            return style_label
        is_bold = cls._is_bold_style(font, coordinates, style_label)
        is_italic = cls._is_italic_style(font, coordinates, style_label)
        if is_bold and is_italic:
            return "Bold Italic"
        if is_bold:
            return "Bold"
        if is_italic:
            return "Italic"
        return "Regular"

    @staticmethod
    def _full_name_for_strategy(
        family_name: str,
        style_label: str,
        naming_strategy: str,
    ) -> str:
        if naming_strategy == "instance-family" and style_label == "Regular":
            return family_name
        return f"{family_name} {style_label}"

    @classmethod
    def _instance_style_label(cls, font: TtfFont, coordinates: dict[str, float]) -> str:
        matched_instance = None
        for instance in font.variable_instances:
            if cls._same_coordinates(instance.coordinates, coordinates):
                matched_instance = instance
                break
        if matched_instance is not None:
            return matched_instance.label

        parts: list[str] = []
        for axis in font.variable_axes:
            value = coordinates[axis.tag]
            if value == axis.default_value:
                continue
            label = axis.label
            parts.append(f"{label} {cls._format_coord(value)}")
        return "Regular" if not parts else " ".join(parts)

    @classmethod
    def _matched_instance_label(cls, font: TtfFont, coordinates: dict[str, float]) -> str | None:
        for instance in font.variable_instances:
            if cls._same_coordinates(instance.coordinates, coordinates):
                return instance.label
        return None

    @classmethod
    def _is_bold_style(
        cls,
        font: TtfFont,
        coordinates: dict[str, float],
        style_label: str,
    ) -> bool:
        normalized = style_label.casefold()
        if any(
            marker in normalized
            for marker in ("bold", "black", "heavy", "semibold", "demibold", "extrabold", "ultrabold")
        ):
            return True
        axis = font.get_axis("wght")
        if axis is not None:
            value = coordinates.get("wght", axis.default_value)
            return value >= max(axis.default_value, 600.0)
        return False

    @classmethod
    def _is_italic_style(
        cls,
        font: TtfFont,
        coordinates: dict[str, float],
        style_label: str,
    ) -> bool:
        normalized = style_label.casefold()
        if "italic" in normalized or "oblique" in normalized:
            return True
        ital_axis = font.get_axis("ital")
        if ital_axis is not None and coordinates.get("ital", ital_axis.default_value) >= 0.5:
            return True
        slnt_axis = font.get_axis("slnt")
        if slnt_axis is not None and abs(coordinates.get("slnt", slnt_axis.default_value)) > 0.01:
            return True
        return False

    @staticmethod
    def _same_coordinates(a: dict[str, float], b: dict[str, float], tolerance: float = 1e-6) -> bool:
        if a.keys() != b.keys():
            return False
        return all(abs(a[key] - b[key]) <= tolerance for key in a)

    @staticmethod
    def _format_coord(value: float) -> str:
        if float(value).is_integer():
            return str(int(value))
        return f"{value:.2f}".rstrip("0").rstrip(".")

    @staticmethod
    def _sanitize_postscript(family_name: str, style_label: str) -> str:
        def clean(part: str) -> str:
            return re.sub(r"[^A-Za-z0-9]", "", part)

        family = clean(family_name) or "Font"
        style = clean(style_label) or "Regular"
        return f"{family}-{style}"

    @staticmethod
    def _support_scalar(variation: TupleVariation, normalized: dict[str, float]) -> float:
        scalar = 1.0
        for axis_tag, peak in variation.peak_coords.items():
            coord = normalized.get(axis_tag, 0.0)
            if peak == 0.0:
                continue
            start = variation.start_coords[axis_tag] if variation.start_coords is not None else (-1.0 if peak < 0.0 else 0.0)
            end = variation.end_coords[axis_tag] if variation.end_coords is not None else (0.0 if peak < 0.0 else 1.0)
            if coord < start or coord > end:
                return 0.0
            if coord == peak:
                continue
            if coord < peak:
                denom = peak - start
                if denom == 0:
                    return 0.0
                scalar *= (coord - start) / denom
            else:
                denom = end - peak
                if denom == 0:
                    return 0.0
                scalar *= (end - coord) / denom
            if scalar == 0.0:
                return 0.0
        return scalar

    @classmethod
    def _phantom_variation_deltas(
        cls,
        gvar: GvarTable,
        gid: int,
        normalized: dict[str, float],
    ) -> tuple[list[float], list[float]]:
        variations = gvar.glyph_variations(gid, 0)
        phantom_dx = [0.0] * 4
        phantom_dy = [0.0] * 4
        for variation in variations:
            scalar = cls._support_scalar(variation, normalized)
            if scalar == 0.0:
                continue
            points = variation.points if variation.points is not None else list(range(len(variation.deltas)))
            for point_index, (delta_x, delta_y) in zip(points, variation.deltas):
                if point_index >= 4:
                    continue
                phantom_dx[point_index] += delta_x * scalar
                phantom_dy[point_index] += delta_y * scalar
        return phantom_dx, phantom_dy

    @classmethod
    def _apply_composite_variations(
        cls,
        composite: _CompositeGlyph,
        gvar: GvarTable,
        gid: int,
        normalized: dict[str, float],
    ) -> tuple[_CompositeGlyph, list[float], list[float]]:
        components = copy.deepcopy(composite.components)
        phantom_dx = [0.0] * 4
        phantom_dy = [0.0] * 4
        variations = gvar.glyph_variations(gid, 0)
        component_count = len(components)
        for variation in variations:
            scalar = cls._support_scalar(variation, normalized)
            if scalar == 0.0:
                continue
            points = variation.points if variation.points is not None else list(range(len(variation.deltas)))
            for point_index, (delta_x, delta_y) in zip(points, variation.deltas):
                if point_index < component_count:
                    component = components[point_index]
                    if not component.args_are_xy_values:
                        raise FontNotSupportedException("Unsupported composite glyph arguments for instancing")
                    component.arg1 += cls._ot_round(delta_x * scalar)
                    component.arg2 += cls._ot_round(delta_y * scalar)
                    if not (-128 <= component.arg1 <= 127 and -128 <= component.arg2 <= 127):
                        component.flags |= _ARG_1_AND_2_ARE_WORDS
                    continue
                phantom_index = point_index - component_count
                if 0 <= phantom_index < 4:
                    phantom_dx[phantom_index] += delta_x * scalar
                    phantom_dy[phantom_index] += delta_y * scalar
                    continue
                raise FontNotSupportedException("Unsupported composite gvar variation")
        return _CompositeGlyph(components=components, instructions=composite.instructions), phantom_dx, phantom_dy

    @classmethod
    def _expand_simple_deltas(
        cls,
        simple: _SimpleGlyph,
        variation: TupleVariation,
    ) -> tuple[list[float], list[float], list[float], list[float]]:
        point_count = len(simple.xs)
        expanded_dx = [0.0] * point_count
        expanded_dy = [0.0] * point_count
        phantom_dx = [0.0] * 4
        phantom_dy = [0.0] * 4
        if variation.points is None:
            for point_index, (delta_x, delta_y) in enumerate(variation.deltas):
                if point_index < point_count:
                    expanded_dx[point_index] = float(delta_x)
                    expanded_dy[point_index] = float(delta_y)
                elif point_index < point_count + 4:
                    phantom_index = point_index - point_count
                    phantom_dx[phantom_index] = float(delta_x)
                    phantom_dy[phantom_index] = float(delta_y)
                else:
                    raise FontParseException("Invalid gvar point run for glyph instancing", format_name="TTF")
            return expanded_dx, expanded_dy, phantom_dx, phantom_dy

        touched_dx: list[float | None] = [None] * point_count
        touched_dy: list[float | None] = [None] * point_count
        for point_index, (delta_x, delta_y) in zip(variation.points, variation.deltas):
            if point_index < point_count:
                touched_dx[point_index] = float(delta_x)
                touched_dy[point_index] = float(delta_y)
            elif point_index < point_count + 4:
                phantom_index = point_index - point_count
                phantom_dx[phantom_index] = float(delta_x)
                phantom_dy[phantom_index] = float(delta_y)
            else:
                raise FontParseException("Invalid gvar point run for glyph instancing", format_name="TTF")

        expanded_dx = cls._interpolate_untouched_points(simple.contour_ends, simple.xs, touched_dx)
        expanded_dy = cls._interpolate_untouched_points(simple.contour_ends, simple.ys, touched_dy)
        return expanded_dx, expanded_dy, phantom_dx, phantom_dy

    @classmethod
    def _interpolate_untouched_points(
        cls,
        contour_ends: list[int],
        coords: list[int],
        touched: list[float | None],
    ) -> list[float]:
        expanded = [0.0 if value is None else float(value) for value in touched]
        contour_start = 0
        for contour_end in contour_ends:
            point_indices = list(range(contour_start, contour_end + 1))
            contour_start = contour_end + 1
            touched_indices = [index for index in point_indices if touched[index] is not None]
            if not touched_indices:
                continue
            if len(touched_indices) == 1:
                fill = float(touched[touched_indices[0]])
                for index in point_indices:
                    expanded[index] = fill
                continue

            ordered = touched_indices
            for segment_index, left_index in enumerate(ordered):
                right_index = ordered[(segment_index + 1) % len(ordered)]
                left_delta = float(touched[left_index])
                right_delta = float(touched[right_index])
                cls._fill_interpolated_segment(
                    expanded,
                    coords,
                    point_indices,
                    left_index,
                    right_index,
                    left_delta,
                    right_delta,
                )
        return expanded

    @staticmethod
    def _fill_interpolated_segment(
        expanded: list[float],
        coords: list[int],
        contour_indices: list[int],
        left_index: int,
        right_index: int,
        left_delta: float,
        right_delta: float,
    ) -> None:
        left_pos = contour_indices.index(left_index)
        right_pos = contour_indices.index(right_index)
        if left_pos < right_pos:
            segment = contour_indices[left_pos:right_pos + 1]
        else:
            segment = contour_indices[left_pos:] + contour_indices[:right_pos + 1]
        left_coord = coords[left_index]
        right_coord = coords[right_index]
        for point_index in segment:
            coord = coords[point_index]
            if left_coord == right_coord:
                expanded[point_index] = (left_delta + right_delta) / 2.0
                continue
            ratio = (coord - left_coord) / (right_coord - left_coord)
            if ratio < 0.0:
                ratio = 0.0
            elif ratio > 1.0:
                ratio = 1.0
            expanded[point_index] = left_delta + ((right_delta - left_delta) * ratio)

    @classmethod
    def _metric_overrides_from_phantoms(
        cls,
        raw: bytes,
        *,
        advance_width: int,
        lsb: int,
        phantom_dx: list[float],
        new_bounds: tuple[int, int, int, int] | None,
    ) -> tuple[int | None, int | None]:
        if new_bounds is None:
            return None, None
        if len(raw) < 10 or not any(phantom_dx):
            return None, None
        original_bounds = cls._glyph_bounds(raw)
        if original_bounds is None:
            return None, None
        original_x_min = original_bounds[0]
        phantom_left = float(original_x_min - lsb)
        phantom_right = float(phantom_left + advance_width)
        varied_left = phantom_left + phantom_dx[0]
        varied_right = phantom_right + phantom_dx[1]
        updated_lsb = new_bounds[0] - cls._ot_round(varied_left)
        updated_advance = cls._ot_round(varied_right - varied_left)
        return updated_lsb, max(0, updated_advance)

    @staticmethod
    def _parse_composite_glyph(raw: bytes) -> _CompositeGlyph:
        if len(raw) < 10:
            raise FontParseException("Unsupported composite glyph data", format_name="TTF")
        r = BinaryReader(raw)
        contour_count = r.read_i16()
        if contour_count >= 0:
            raise FontParseException("Unsupported composite glyph data", format_name="TTF")
        r.read_i16()
        r.read_i16()
        r.read_i16()
        r.read_i16()
        components: list[_CompositeComponent] = []
        last_flags = 0
        while True:
            flags = r.read_u16()
            last_flags = flags
            component_gid = r.read_u16()
            if flags & _ARG_1_AND_2_ARE_WORDS:
                arg1 = r.read_i16()
                arg2 = r.read_i16()
            else:
                arg1 = r.read_i8()
                arg2 = r.read_i8()
            xx = 1.0
            yx = 0.0
            xy = 0.0
            yy = 1.0
            if flags & _WE_HAVE_A_SCALE:
                scale = r.read_f2dot14()
                xx = scale
                yy = scale
            elif flags & _WE_HAVE_AN_X_AND_Y_SCALE:
                xx = r.read_f2dot14()
                yy = r.read_f2dot14()
            elif flags & _WE_HAVE_A_TWO_BY_TWO:
                xx = r.read_f2dot14()
                yx = r.read_f2dot14()
                xy = r.read_f2dot14()
                yy = r.read_f2dot14()
            components.append(
                _CompositeComponent(
                    flags=flags,
                    glyph_id=component_gid,
                    arg1=arg1,
                    arg2=arg2,
                    args_are_xy_values=bool(flags & _ARGS_ARE_XY_VALUES),
                    xx=xx,
                    yx=yx,
                    xy=xy,
                    yy=yy,
                )
            )
            if not (flags & _MORE_COMPONENTS):
                break
        instructions = b""
        if last_flags & _WE_HAVE_INSTRUCTIONS:
            instructions = r.read_bytes(r.read_u16())
        return _CompositeGlyph(components=components, instructions=instructions)

    @classmethod
    def _encode_composite_glyph(
        cls,
        composite: _CompositeGlyph,
        bounds: tuple[int, int, int, int] | None,
    ) -> bytes:
        x_min, y_min, x_max, y_max = bounds if bounds is not None else (0, 0, 0, 0)
        w = BinaryWriter()
        w.write_i16(-1)
        w.write_i16(x_min)
        w.write_i16(y_min)
        w.write_i16(x_max)
        w.write_i16(y_max)
        for component in composite.components:
            w.write_u16(component.flags)
            w.write_u16(component.glyph_id)
            if component.flags & _ARG_1_AND_2_ARE_WORDS:
                w.write_i16(component.arg1)
                w.write_i16(component.arg2)
            else:
                w.write_i8(component.arg1)
                w.write_i8(component.arg2)
            if component.flags & _WE_HAVE_A_SCALE:
                w.write_f2dot14(component.xx)
            elif component.flags & _WE_HAVE_AN_X_AND_Y_SCALE:
                w.write_f2dot14(component.xx)
                w.write_f2dot14(component.yy)
            elif component.flags & _WE_HAVE_A_TWO_BY_TWO:
                w.write_f2dot14(component.xx)
                w.write_f2dot14(component.yx)
                w.write_f2dot14(component.xy)
                w.write_f2dot14(component.yy)
        if composite.components and (composite.components[-1].flags & _WE_HAVE_INSTRUCTIONS):
            w.write_u16(len(composite.instructions))
            w.write_bytes(composite.instructions)
        return w.to_bytes()

    @classmethod
    def _composite_bounds(
        cls,
        composite: _CompositeGlyph,
        instantiate_gid,
    ) -> tuple[int, int, int, int] | None:
        bounds: tuple[float, float, float, float] | None = None
        for component in composite.components:
            if not component.args_are_xy_values:
                raise FontNotSupportedException("Unsupported composite glyph arguments for instancing")
            child = instantiate_gid(component.glyph_id)
            child_bounds = cls._glyph_bounds(child.data)
            if child_bounds is None:
                continue
            transformed = cls._transform_bounds(child_bounds, component)
            if bounds is None:
                bounds = transformed
                continue
            bounds = (
                min(bounds[0], transformed[0]),
                min(bounds[1], transformed[1]),
                max(bounds[2], transformed[2]),
                max(bounds[3], transformed[3]),
            )
        if bounds is None:
            return None
        return (
            cls._ot_round(bounds[0]),
            cls._ot_round(bounds[1]),
            cls._ot_round(bounds[2]),
            cls._ot_round(bounds[3]),
        )

    @staticmethod
    def _transform_bounds(
        child_bounds: tuple[int, int, int, int],
        component: _CompositeComponent,
    ) -> tuple[float, float, float, float]:
        x_min, y_min, x_max, y_max = child_bounds
        corners = (
            (x_min, y_min),
            (x_min, y_max),
            (x_max, y_min),
            (x_max, y_max),
        )
        transformed = [
            (
                (component.xx * x) + (component.xy * y) + component.dx,
                (component.yx * x) + (component.yy * y) + component.dy,
            )
            for x, y in corners
        ]
        xs = [item[0] for item in transformed]
        ys = [item[1] for item in transformed]
        return min(xs), min(ys), max(xs), max(ys)

    @staticmethod
    def _parse_simple_glyph(raw: bytes) -> _SimpleGlyph:
        r = BinaryReader(raw)
        contour_count = r.read_i16()
        if contour_count <= 0:
            raise FontParseException("Unsupported gvar tuple encoding", format_name="TTF")
        r.read_i16()
        r.read_i16()
        r.read_i16()
        r.read_i16()
        contour_ends = [r.read_u16() for _ in range(contour_count)]
        point_count = contour_ends[-1] + 1 if contour_ends else 0
        instruction_len = r.read_u16()
        instructions = r.read_bytes(instruction_len)
        flags = TtfInstancer._decode_flags(r, point_count)
        xs = TtfInstancer._decode_coords(
            r,
            point_count,
            flags,
            _X_IS_SAME_OR_POSITIVE_X_SHORT_VECTOR,
            _X_SHORT_VECTOR,
        )
        ys = TtfInstancer._decode_coords(
            r,
            point_count,
            flags,
            _Y_IS_SAME_OR_POSITIVE_Y_SHORT_VECTOR,
            _Y_SHORT_VECTOR,
        )
        on_curve = [bool(flag & _ON_CURVE_POINT) for flag in flags]
        return _SimpleGlyph(contour_ends=contour_ends, xs=xs, ys=ys, on_curve=on_curve, instructions=instructions)

    @staticmethod
    def _decode_flags(r: BinaryReader, point_count: int) -> list[int]:
        flags: list[int] = []
        while len(flags) < point_count:
            flag = r.read_u8()
            flags.append(flag)
            if flag & _REPEAT_FLAG:
                flags.extend([flag] * r.read_u8())
        return flags[:point_count]

    @staticmethod
    def _decode_coords(
        r: BinaryReader,
        point_count: int,
        flags: list[int],
        same_bit: int,
        short_bit: int,
    ) -> list[int]:
        coords: list[int] = []
        current = 0
        for i in range(point_count):
            flag = flags[i]
            if flag & short_bit:
                delta = r.read_u8()
                if not (flag & same_bit):
                    delta = -delta
            elif flag & same_bit:
                delta = 0
            else:
                delta = r.read_i16()
            current += delta
            coords.append(current)
        return coords

    @staticmethod
    def _encode_simple_glyph(
        contour_ends: list[int],
        xs: list[int],
        ys: list[int],
        on_curve: list[bool],
        instructions: bytes,
    ) -> bytes:
        x_min = min(xs) if xs else 0
        y_min = min(ys) if ys else 0
        x_max = max(xs) if xs else 0
        y_max = max(ys) if ys else 0

        flags: list[int] = []
        x_stream = BinaryWriter()
        y_stream = BinaryWriter()
        prev_x = 0
        prev_y = 0
        for x, y, is_on_curve in zip(xs, ys, on_curve):
            flag = _ON_CURVE_POINT if is_on_curve else 0
            dx = x - prev_x
            dy = y - prev_y
            prev_x = x
            prev_y = y

            if dx == 0:
                flag |= _X_IS_SAME_OR_POSITIVE_X_SHORT_VECTOR
            elif 0 < dx <= 255:
                flag |= _X_SHORT_VECTOR | _X_IS_SAME_OR_POSITIVE_X_SHORT_VECTOR
                x_stream.write_u8(dx)
            elif -255 <= dx < 0:
                flag |= _X_SHORT_VECTOR
                x_stream.write_u8(-dx)
            else:
                x_stream.write_i16(dx)

            if dy == 0:
                flag |= _Y_IS_SAME_OR_POSITIVE_Y_SHORT_VECTOR
            elif 0 < dy <= 255:
                flag |= _Y_SHORT_VECTOR | _Y_IS_SAME_OR_POSITIVE_Y_SHORT_VECTOR
                y_stream.write_u8(dy)
            elif -255 <= dy < 0:
                flag |= _Y_SHORT_VECTOR
                y_stream.write_u8(-dy)
            else:
                y_stream.write_i16(dy)

            flags.append(flag)

        packed_flags = BinaryWriter()
        i = 0
        while i < len(flags):
            flag = flags[i]
            run_len = 1
            while i + run_len < len(flags) and flags[i + run_len] == flag and run_len < 256:
                run_len += 1
            if run_len > 1:
                packed_flags.write_u8(flag | _REPEAT_FLAG)
                packed_flags.write_u8(run_len - 1)
            else:
                packed_flags.write_u8(flag)
            i += run_len

        w = BinaryWriter()
        w.write_i16(len(contour_ends))
        w.write_i16(x_min)
        w.write_i16(y_min)
        w.write_i16(x_max)
        w.write_i16(y_max)
        for contour_end in contour_ends:
            w.write_u16(contour_end)
        w.write_u16(len(instructions))
        w.write_bytes(instructions)
        w.write_bytes(packed_flags.to_bytes())
        w.write_bytes(x_stream.to_bytes())
        w.write_bytes(y_stream.to_bytes())
        return w.to_bytes()

    @staticmethod
    def _glyph_bounds(raw: bytes) -> tuple[int, int, int, int] | None:
        if len(raw) < 10:
            return None
        return (
            int.from_bytes(raw[2:4], "big", signed=True),
            int.from_bytes(raw[4:6], "big", signed=True),
            int.from_bytes(raw[6:8], "big", signed=True),
            int.from_bytes(raw[8:10], "big", signed=True),
        )

    @staticmethod
    def _ot_round(value: float) -> int:
        if value >= 0:
            return int(value + 0.5)
        return -int((-value) + 0.5)
