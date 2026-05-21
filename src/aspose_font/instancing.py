"""High-level variable-font instancing helpers."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from typing import TYPE_CHECKING

from aspose_font._exceptions import FontNotSupportedException
from aspose_font.compatibility import CompatibilityChecker, CompatibilityReport
from aspose_font.delta import (
    DeltaInspector,
    GlyphDeltaComparisonReport,
    GlyphDeltaReport,
    TextDeltaComparisonReport,
    TextDeltaReport,
)
from aspose_font.preview import FontPreviewBuilder, PreviewImage
from aspose_font.web import (
    FamilyReviewExportPackage,
    WebFontBuilder,
    WebFontBundle,
    WebFontFamilyPackage,
)

if TYPE_CHECKING:
    from aspose_font.ttf.font import TtfFont
    from aspose_font.variation import VariableAxis, VariableInstance


@dataclass(slots=True, frozen=True)
class ResolvedInstance:
    coordinates: dict[str, float]
    source_instance: "VariableInstance | None"
    is_default: bool

    @property
    def label(self) -> str:
        if self.source_instance is not None:
            return self.source_instance.label
        return "Default" if self.is_default else "Custom"


class SmartInstancer:
    def __init__(self, font: "TtfFont") -> None:
        if not font.is_variable:
            raise FontNotSupportedException("Font is not variable")
        self._font = font

    @property
    def font(self) -> "TtfFont":
        return self._font

    @property
    def axes(self):
        return self._font.variable_axes

    @property
    def named_instances(self):
        return self._font.variable_instances

    @property
    def default_coordinates(self) -> dict[str, float]:
        return {axis.tag: axis.default_value for axis in self.axes}

    def suggest_axis_values(
        self,
        axis_tag: str,
        *,
        include_default: bool = True,
        include_bounds: bool = False,
    ) -> list[float]:
        axis = self._axis_for_tag(axis_tag)
        values: list[float] = []
        if axis.presets:
            values.extend(preset.value for preset in axis.presets)
        else:
            if include_bounds:
                values.extend((axis.min_value, axis.max_value))
            if include_default:
                values.append(axis.default_value)
        if include_bounds:
            values.extend((axis.min_value, axis.max_value))
        if include_default:
            values.append(axis.default_value)
        return _unique_sorted(values)

    def resolve_axis_grid(
        self,
        axis_tag: str,
        values: list[float | str] | tuple[float | str, ...] = (),
        *,
        secondary_axis_tag: str | None = None,
        secondary_values: list[float | str] | tuple[float | str, ...] = (),
        coordinates: dict[str, float | str] | None = None,
        instance_name: str | None = None,
        use_axis_presets: bool = False,
        use_secondary_axis_presets: bool = False,
        include_default: bool = True,
        include_bounds: bool = False,
    ) -> list[ResolvedInstance]:
        primary_axis = self._axis_for_tag(axis_tag)
        primary_values = self._grid_values_for_axis(
            primary_axis,
            values,
            use_presets=use_axis_presets,
            include_default=include_default,
            include_bounds=include_bounds,
            axis_role="Primary",
        )
        secondary_axis = None
        if secondary_axis_tag is not None:
            secondary_axis = self._axis_for_tag(secondary_axis_tag)
        secondary_resolved_values = self._grid_values_for_axis(
            secondary_axis,
            secondary_values,
            use_presets=use_secondary_axis_presets,
            include_default=include_default,
            include_bounds=include_bounds,
            axis_role="Secondary",
        )
        if secondary_axis is None and secondary_values:
            raise ValueError("secondary_values require secondary_axis_tag")
        if secondary_axis is None:
            secondary_iterable: list[float] = [None]  # type: ignore[list-item]
        else:
            secondary_iterable = secondary_resolved_values

        resolved_instances: list[ResolvedInstance] = []
        for primary_value, secondary_value in product(primary_values, secondary_iterable):
            overrides = dict(coordinates or {})
            overrides[axis_tag] = primary_value
            if secondary_axis is not None and secondary_value is not None:
                overrides[secondary_axis_tag] = secondary_value
            resolved_instances.append(
                self.resolve(
                    overrides,
                    instance_name=instance_name,
                )
            )
        return resolved_instances

    def resolve(
        self,
        coordinates: dict[str, float | str] | None = None,
        *,
        instance_name: str | None = None,
        **axis_values: float | str,
    ) -> ResolvedInstance:
        selected_instance = None
        if instance_name is not None:
            selected_instance = self._resolve_named_instance(instance_name)

        resolved = (
            dict(selected_instance.coordinates)
            if selected_instance is not None
            else self.default_coordinates
        )
        overrides = dict(coordinates or {})
        overrides.update(axis_values)

        axis_lookup = {axis.tag: axis for axis in self.axes}
        for tag, value in overrides.items():
            axis = axis_lookup.get(tag)
            if axis is None:
                raise ValueError(f"Unknown variable axis: {tag!r}")
            resolved[tag] = self._resolve_axis_value(axis, value)

        matched_instance = self._matching_instance(resolved)
        return ResolvedInstance(
            coordinates=resolved,
            source_instance=matched_instance,
            is_default=resolved == self.default_coordinates,
        )

    def instantiate(
        self,
        coordinates: dict[str, float | str] | None = None,
        *,
        instance_name: str | None = None,
        naming_strategy: str = "instance-family",
        family_suffix: str | None = None,
        legacy_family_name: str | None = None,
        typographic_family_name: str | None = None,
        legacy_style_name: str | None = None,
        typographic_style_name: str | None = None,
        **axis_values: float | str,
    ) -> "TtfFont":
        resolved = self.resolve(
            coordinates,
            instance_name=instance_name,
            **axis_values,
        )
        return self._font.instantiate(
            resolved.coordinates,
            naming_strategy=naming_strategy,
            family_suffix=family_suffix,
            legacy_family_name=legacy_family_name,
            typographic_family_name=typographic_family_name,
            legacy_style_name=legacy_style_name,
            typographic_style_name=typographic_style_name,
        )

    def preview_naming_policy(
        self,
        coordinates: dict[str, float | str] | None = None,
        *,
        instance_name: str | None = None,
        naming_strategy: str = "instance-family",
        family_suffix: str | None = None,
        legacy_family_name: str | None = None,
        typographic_family_name: str | None = None,
        legacy_style_name: str | None = None,
        typographic_style_name: str | None = None,
        **axis_values: float | str,
    ):
        resolved = self.resolve(
            coordinates,
            instance_name=instance_name,
            **axis_values,
        )
        return self._font.preview_naming_policy(
            resolved.coordinates,
            naming_strategy=naming_strategy,
            family_suffix=family_suffix,
            legacy_family_name=legacy_family_name,
            typographic_family_name=typographic_family_name,
            legacy_style_name=legacy_style_name,
            typographic_style_name=typographic_style_name,
        )

    def instantiate_named(
        self,
        name: str,
        *,
        coordinates: dict[str, float | str] | None = None,
        naming_strategy: str = "instance-family",
        family_suffix: str | None = None,
        legacy_family_name: str | None = None,
        typographic_family_name: str | None = None,
        legacy_style_name: str | None = None,
        typographic_style_name: str | None = None,
        **axis_values: float | str,
    ) -> "TtfFont":
        return self.instantiate(
            coordinates,
            instance_name=name,
            naming_strategy=naming_strategy,
            family_suffix=family_suffix,
            legacy_family_name=legacy_family_name,
            typographic_family_name=typographic_family_name,
            legacy_style_name=legacy_style_name,
            typographic_style_name=typographic_style_name,
            **axis_values,
        )

    def resolve_named_many(
        self,
        names: list[str] | tuple[str, ...] | None = None,
        *,
        include_default: bool = False,
    ) -> list[ResolvedInstance]:
        resolved: list[ResolvedInstance] = []
        if include_default:
            resolved.append(self.resolve())
        selected_names = [instance.label for instance in self.named_instances] if names is None else list(names)
        for name in selected_names:
            resolved.append(self.resolve(instance_name=name))
        return resolved

    def instantiate_many(
        self,
        names: list[str] | tuple[str, ...] | None = None,
        *,
        include_default: bool = False,
        naming_strategy: str = "instance-family",
        family_suffix: str | None = None,
        legacy_family_name: str | None = None,
        typographic_family_name: str | None = None,
        legacy_style_name: str | None = None,
        typographic_style_name: str | None = None,
    ) -> list[tuple[ResolvedInstance, "TtfFont"]]:
        generated: list[tuple[ResolvedInstance, "TtfFont"]] = []
        for resolved in self.resolve_named_many(names, include_default=include_default):
            generated.append(
                (
                    resolved,
                    self._font.instantiate(
                        resolved.coordinates,
                        naming_strategy=naming_strategy,
                        family_suffix=family_suffix,
                        legacy_family_name=legacy_family_name,
                        typographic_family_name=typographic_family_name,
                        legacy_style_name=legacy_style_name,
                        typographic_style_name=typographic_style_name,
                    ),
                )
            )
        return generated

    def build_web_bundle(
        self,
        coordinates: dict[str, float] | None = None,
        *,
        instance_name: str | None = None,
        **kwargs,
    ) -> WebFontBundle:
        resolved = self.resolve(
            coordinates,
            instance_name=instance_name,
        )
        return WebFontBuilder.build(
            self._font,
            instance_coordinates=resolved.coordinates,
            instance_name=instance_name,
            **kwargs,
        )

    def build_preview(
        self,
        coordinates: dict[str, float | str] | None = None,
        *,
        instance_name: str | None = None,
        output_format: str = "png",
        **axis_values: float | str,
    ) -> PreviewImage:
        preview_kwargs = dict(axis_values)
        text = preview_kwargs.pop("text", "Hamburgefons 0123456789")
        size = preview_kwargs.pop("size", 72.0)
        color = preview_kwargs.pop("color", (17, 17, 17))
        background = preview_kwargs.pop("background", (255, 253, 248))
        padding = preview_kwargs.pop("padding", 12)
        antialias = preview_kwargs.pop("antialias", True)
        file_stem = preview_kwargs.pop("file_stem", None)
        if preview_kwargs:
            axis_overrides = {tag: float(value) for tag, value in preview_kwargs.items()}
        else:
            axis_overrides = {}
        resolved = self.resolve(
            coordinates,
            instance_name=instance_name,
            **axis_overrides,
        )
        return FontPreviewBuilder.build(
            self._font,
            text=text,
            size=size,
            color=color,
            background=background,
            padding=padding,
            antialias=antialias,
            file_stem=file_stem,
            instance_coordinates=resolved.coordinates,
            instance_name=instance_name,
            output_format=output_format,
        )

    def build_web_bundles(
        self,
        names: list[str] | tuple[str, ...] | None = None,
        *,
        include_default: bool = False,
        **kwargs,
    ) -> list[tuple[ResolvedInstance, WebFontBundle]]:
        bundles: list[tuple[ResolvedInstance, WebFontBundle]] = []
        for resolved in self.resolve_named_many(names, include_default=include_default):
            instance_name = resolved.source_instance.label if resolved.source_instance is not None else None
            bundle = WebFontBuilder.build(
                self._font,
                instance_coordinates=resolved.coordinates,
                instance_name=instance_name,
                **kwargs,
            )
            bundles.append((resolved, bundle))
        return bundles

    def build_axis_grid_web_bundles(
        self,
        axis_tag: str,
        values: list[float | str] | tuple[float | str, ...] = (),
        *,
        secondary_axis_tag: str | None = None,
        secondary_values: list[float | str] | tuple[float | str, ...] = (),
        coordinates: dict[str, float | str] | None = None,
        instance_name: str | None = None,
        use_axis_presets: bool = False,
        use_secondary_axis_presets: bool = False,
        include_default: bool = True,
        include_bounds: bool = False,
        **kwargs,
    ) -> list[tuple[ResolvedInstance, WebFontBundle]]:
        bundles: list[tuple[ResolvedInstance, WebFontBundle]] = []
        for resolved in self.resolve_axis_grid(
            axis_tag,
            values,
            secondary_axis_tag=secondary_axis_tag,
            secondary_values=secondary_values,
            coordinates=coordinates,
            instance_name=instance_name,
            use_axis_presets=use_axis_presets,
            use_secondary_axis_presets=use_secondary_axis_presets,
            include_default=include_default,
            include_bounds=include_bounds,
        ):
            bundle = WebFontBuilder.build(
                self._font,
                instance_coordinates=resolved.coordinates,
                instance_name=resolved.source_instance.label if resolved.source_instance is not None else instance_name,
                **kwargs,
            )
            bundle.review_label = _sheet_label(resolved.coordinates)
            bundles.append((resolved, bundle))
        return bundles

    def build_axis_grid_web_family_package(
        self,
        axis_tag: str,
        values: list[float | str] | tuple[float | str, ...],
        *,
        secondary_axis_tag: str | None = None,
        secondary_values: list[float | str] | tuple[float | str, ...] = (),
        coordinates: dict[str, float | str] | None = None,
        instance_name: str | None = None,
        family_name: str | None = None,
        **kwargs,
    ) -> WebFontFamilyPackage:
        bundles = [
            bundle
            for _resolved, bundle in self.build_axis_grid_web_bundles(
                axis_tag,
                values,
                secondary_axis_tag=secondary_axis_tag,
                secondary_values=secondary_values,
                coordinates=coordinates,
                instance_name=instance_name,
                **kwargs,
            )
        ]
        return WebFontBuilder.build_family_package(
            bundles,
            family_name=family_name,
            preview_text=kwargs.get("preview_text", "Hamburgefons 0123456789"),
            specimen_template=kwargs.get("specimen_template", "classic"),
        )

    def build_previews(
        self,
        names: list[str] | tuple[str, ...] | None = None,
        *,
        include_default: bool = False,
        text: str = "Hamburgefons 0123456789",
        size: float = 72.0,
        color: tuple[int, int, int] = (17, 17, 17),
        background: tuple[int, int, int] = (255, 253, 248),
        padding: int = 12,
        antialias: bool = True,
        output_format: str = "png",
    ) -> list[tuple[ResolvedInstance, PreviewImage]]:
        previews: list[tuple[ResolvedInstance, PreviewImage]] = []
        for resolved in self.resolve_named_many(names, include_default=include_default):
            instance_name = resolved.source_instance.label if resolved.source_instance is not None else None
            preview = FontPreviewBuilder.build(
                self._font,
                text=text,
                size=size,
                color=color,
                background=background,
                padding=padding,
                antialias=antialias,
                instance_coordinates=resolved.coordinates,
                instance_name=instance_name,
                output_format=output_format,
            )
            previews.append((resolved, preview))
        return previews

    def build_web_family_package(
        self,
        names: list[str] | tuple[str, ...] | None = None,
        *,
        include_default: bool = False,
        family_name: str | None = None,
        **kwargs,
    ) -> WebFontFamilyPackage:
        bundles = [
            bundle
            for _resolved, bundle in self.build_web_bundles(
                names,
                include_default=include_default,
                **kwargs,
            )
        ]
        return WebFontBuilder.build_family_package(
            bundles,
            family_name=family_name,
            preview_text=kwargs.get("preview_text", "Hamburgefons 0123456789"),
            specimen_template=kwargs.get("specimen_template", "classic"),
        )

    def build_axis_grid_previews(
        self,
        axis_tag: str,
        values: list[float] | tuple[float, ...] = (),
        *,
        secondary_axis_tag: str | None = None,
        secondary_values: list[float] | tuple[float, ...] = (),
        coordinates: dict[str, float] | None = None,
        instance_name: str | None = None,
        use_axis_presets: bool = False,
        use_secondary_axis_presets: bool = False,
        include_default: bool = True,
        include_bounds: bool = False,
        text: str = "Hamburgefons 0123456789",
        size: float = 72.0,
        color: tuple[int, int, int] = (17, 17, 17),
        background: tuple[int, int, int] = (255, 253, 248),
        padding: int = 12,
        antialias: bool = True,
        output_format: str = "png",
    ) -> list[tuple[ResolvedInstance, PreviewImage]]:
        resolved_previews: list[tuple[ResolvedInstance, PreviewImage]] = []
        for resolved in self.resolve_axis_grid(
            axis_tag,
            values,
            secondary_axis_tag=secondary_axis_tag,
            secondary_values=secondary_values,
            coordinates=coordinates,
            instance_name=instance_name,
            use_axis_presets=use_axis_presets,
            use_secondary_axis_presets=use_secondary_axis_presets,
            include_default=include_default,
            include_bounds=include_bounds,
        ):
            preview = FontPreviewBuilder.build(
                self._font,
                text=text,
                size=size,
                color=color,
                background=background,
                padding=padding,
                antialias=antialias,
                instance_coordinates=resolved.coordinates,
                instance_name=resolved.source_instance.label if resolved.source_instance is not None else instance_name,
                output_format=output_format,
            )
            resolved_previews.append((resolved, preview))
        return resolved_previews

    def build_axis_grid_sheet(
        self,
        axis_tag: str,
        values: list[float] | tuple[float, ...] = (),
        *,
        secondary_axis_tag: str | None = None,
        secondary_values: list[float] | tuple[float, ...] = (),
        coordinates: dict[str, float] | None = None,
        instance_name: str | None = None,
        use_axis_presets: bool = False,
        use_secondary_axis_presets: bool = False,
        include_default: bool = True,
        include_bounds: bool = False,
        text: str = "Hamburgefons 0123456789",
        size: float = 72.0,
        color: tuple[int, int, int] = (17, 17, 17),
        background: tuple[int, int, int] = (255, 253, 248),
        padding: int = 12,
        antialias: bool = True,
        gap: int = 16,
        file_stem: str = "preview-grid-sheet",
        ) -> PreviewImage:
        previews = self.build_axis_grid_previews(
            axis_tag,
            values,
            secondary_axis_tag=secondary_axis_tag,
            secondary_values=secondary_values,
            coordinates=coordinates,
            instance_name=instance_name,
            use_axis_presets=use_axis_presets,
            use_secondary_axis_presets=use_secondary_axis_presets,
            include_default=include_default,
            include_bounds=include_bounds,
            text=text,
            size=size,
            color=color,
            background=background,
            padding=padding,
            antialias=antialias,
        )
        primary_values = _ordered_unique_coordinates(previews, axis_tag)
        secondary_display_values = (
            _ordered_unique_coordinates(previews, secondary_axis_tag)
            if secondary_axis_tag is not None
            else []
        )
        columns = len(secondary_display_values) if secondary_axis_tag is not None else len(primary_values)
        labels = [_sheet_label(resolved.coordinates) for resolved, _preview in previews]
        title = _sheet_title(
            axis_tag,
            primary_values,
            secondary_axis_tag=secondary_axis_tag,
            secondary_values=secondary_display_values,
            instance_name=instance_name,
        )
        column_headers = (
            [f"{secondary_axis_tag}={_format_axis_value(value)}" for value in secondary_display_values]
            if secondary_axis_tag is not None
            else [f"{axis_tag}={_format_axis_value(value)}" for value in primary_values]
        )
        row_headers = (
            [f"{axis_tag}={_format_axis_value(value)}" for value in primary_values]
            if secondary_axis_tag is not None
            else None
        )
        return FontPreviewBuilder.compose_sheet(
            [preview for _resolved, preview in previews],
            columns=columns,
            gap=gap,
            background=background,
            title=title,
            column_headers=column_headers,
            row_headers=row_headers,
            labels=labels,
            file_stem=file_stem,
        )

    def build_comparison_sheet(
        self,
        *,
        before_coordinates: dict[str, float] | None = None,
        after_coordinates: dict[str, float] | None = None,
        before_instance_name: str | None = None,
        after_instance_name: str | None = None,
        text: str = "Hamburgefons 0123456789",
        size: float = 72.0,
        color: tuple[int, int, int] = (17, 17, 17),
        background: tuple[int, int, int] = (255, 253, 248),
        padding: int = 12,
        antialias: bool = True,
        gap: int = 16,
        file_stem: str = "preview-compare-sheet",
    ) -> PreviewImage:
        before_resolved = self.resolve(
            before_coordinates,
            instance_name=before_instance_name,
        )
        after_resolved = self.resolve(
            after_coordinates,
            instance_name=after_instance_name,
        )
        before_preview = FontPreviewBuilder.build(
            self._font,
            text=text,
            size=size,
            color=color,
            background=background,
            padding=padding,
            antialias=antialias,
            instance_coordinates=before_resolved.coordinates,
            instance_name=(
                before_resolved.source_instance.label
                if before_resolved.source_instance is not None
                else before_instance_name
            ),
        )
        after_preview = FontPreviewBuilder.build(
            self._font,
            text=text,
            size=size,
            color=color,
            background=background,
            padding=padding,
            antialias=antialias,
            instance_coordinates=after_resolved.coordinates,
            instance_name=(
                after_resolved.source_instance.label
                if after_resolved.source_instance is not None
                else after_instance_name
            ),
        )
        diff_preview = FontPreviewBuilder.compose_difference_preview(
            before_preview,
            after_preview,
            file_stem="preview-compare-diff",
            background=background,
        )
        overlay_preview = FontPreviewBuilder.compose_overlay_preview(
            before_preview,
            after_preview,
            file_stem="preview-compare-overlay",
            background=background,
        )
        return FontPreviewBuilder.compose_sheet(
            [before_preview, diff_preview, overlay_preview, after_preview],
            columns=4,
            gap=gap,
            background=background,
            title=_comparison_title(before_resolved, after_resolved),
            column_headers=["Before", "Diff", "Overlay", "After"],
            labels=[
                _comparison_label(before_resolved),
                _comparison_diff_label(before_resolved, after_resolved),
                _comparison_overlay_label(before_resolved, after_resolved),
                _comparison_label(after_resolved),
            ],
            footer_lines=_comparison_notes(before_resolved, after_resolved),
            file_stem=file_stem,
        )

    def build_waterfall_sheet(
        self,
        names: list[str] | tuple[str, ...] | None = None,
        *,
        include_default: bool = False,
        text: str = "Hamburgefons 0123456789",
        file_stem: str = "family-waterfall",
    ) -> PreviewImage:
        return WebFontBuilder.build_family_waterfall_preview(
            self._preview_bundles_for_named_instances(
                names,
                include_default=include_default,
            ),
            preview_text=text,
            file_stem=file_stem,
        )

    def build_matrix_sheet(
        self,
        names: list[str] | tuple[str, ...] | None = None,
        *,
        include_default: bool = False,
        text: str = "Hamburgefons 0123456789",
        file_stem: str = "family-matrix",
    ) -> PreviewImage:
        return WebFontBuilder.build_family_matrix_preview(
            self._preview_bundles_for_named_instances(
                names,
                include_default=include_default,
            ),
            preview_text=text,
            file_stem=file_stem,
        )

    def build_family_review_board(
        self,
        names: list[str] | tuple[str, ...] | None = None,
        *,
        include_default: bool = False,
        text: str = "Hamburgefons 0123456789",
        family_name: str | None = None,
        file_stem: str = "family-review-board",
    ) -> PreviewImage:
        return WebFontBuilder.build_family_review_board(
            self._preview_bundles_for_named_instances(
                names,
                include_default=include_default,
            ),
            family_name=family_name,
            preview_text=text,
            file_stem=file_stem,
        )

    def build_family_review_export_package(
        self,
        names: list[str] | tuple[str, ...] | None = None,
        *,
        include_default: bool = False,
        text: str = "Hamburgefons 0123456789",
        family_name: str | None = None,
        file_stem: str = "family-review-board",
    ) -> FamilyReviewExportPackage:
        return WebFontBuilder.build_family_review_export_package(
            self._preview_bundles_for_named_instances(
                names,
                include_default=include_default,
            ),
            family_name=family_name,
            preview_text=text,
            file_stem=file_stem,
        )

    def check_compatibility(
        self,
        *,
        before_coordinates: dict[str, float] | None = None,
        after_coordinates: dict[str, float] | None = None,
        before_instance_name: str | None = None,
        after_instance_name: str | None = None,
        codepoints: list[int] | tuple[int, ...] | None = None,
        text: str = "",
        ) -> CompatibilityReport:
        return CompatibilityChecker.compare_variable_instances(
            self._font,
            before_coordinates=before_coordinates,
            after_coordinates=after_coordinates,
            before_instance_name=before_instance_name,
            after_instance_name=after_instance_name,
            codepoints=codepoints,
            text=text,
        )

    def inspect_deltas(
        self,
        *,
        glyph_id: int | None = None,
        codepoint: int | None = None,
        coordinates: dict[str, float] | None = None,
        instance_name: str | None = None,
        top_points: int = 8,
        ) -> GlyphDeltaReport:
        return DeltaInspector.inspect_variable_glyph(
            self._font,
            glyph_id=glyph_id,
            codepoint=codepoint,
            coordinates=coordinates,
            instance_name=instance_name,
            top_points=top_points,
        )

    def build_delta_sheet(
        self,
        *,
        glyph_id: int | None = None,
        codepoint: int | None = None,
        coordinates: dict[str, float] | None = None,
        instance_name: str | None = None,
        top_points: int = 8,
        panel_size: int = 220,
        file_stem: str = "delta-sheet",
    ) -> PreviewImage:
        return DeltaInspector.build_delta_sheet(
            self._font,
            glyph_id=glyph_id,
            codepoint=codepoint,
            coordinates=coordinates,
            instance_name=instance_name,
            top_points=top_points,
            panel_size=panel_size,
            file_stem=file_stem,
        )

    def inspect_delta_text(
        self,
        *,
        text: str,
        coordinates: dict[str, float] | None = None,
        instance_name: str | None = None,
        top_points: int = 8,
    ) -> TextDeltaReport:
        return DeltaInspector.inspect_variable_text(
            self._font,
            text=text,
            coordinates=coordinates,
            instance_name=instance_name,
            top_points=top_points,
        )

    def compare_delta_glyph(
        self,
        *,
        glyph_id: int | None = None,
        codepoint: int | None = None,
        before_coordinates: dict[str, float] | None = None,
        after_coordinates: dict[str, float] | None = None,
        before_instance_name: str | None = None,
        after_instance_name: str | None = None,
        top_points: int = 8,
    ) -> GlyphDeltaComparisonReport:
        return DeltaInspector.compare_variable_glyph(
            self._font,
            glyph_id=glyph_id,
            codepoint=codepoint,
            before_coordinates=before_coordinates,
            after_coordinates=after_coordinates,
            before_instance_name=before_instance_name,
            after_instance_name=after_instance_name,
            top_points=top_points,
        )

    def compare_delta_text(
        self,
        *,
        text: str,
        before_coordinates: dict[str, float] | None = None,
        after_coordinates: dict[str, float] | None = None,
        before_instance_name: str | None = None,
        after_instance_name: str | None = None,
        top_points: int = 8,
    ) -> TextDeltaComparisonReport:
        return DeltaInspector.compare_variable_text(
            self._font,
            text=text,
            before_coordinates=before_coordinates,
            after_coordinates=after_coordinates,
            before_instance_name=before_instance_name,
            after_instance_name=after_instance_name,
            top_points=top_points,
        )

    def build_delta_text_sheet(
        self,
        *,
        text: str,
        coordinates: dict[str, float] | None = None,
        instance_name: str | None = None,
        top_points: int = 8,
        panel_size: int = 220,
        columns: int = 3,
        file_stem: str = "delta-text-sheet",
    ) -> PreviewImage:
        return DeltaInspector.build_delta_text_sheet(
            self._font,
            text=text,
            coordinates=coordinates,
            instance_name=instance_name,
            top_points=top_points,
            panel_size=panel_size,
            columns=columns,
            file_stem=file_stem,
        )

    def build_delta_text_comparison_sheet(
        self,
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
        return DeltaInspector.build_delta_text_comparison_sheet(
            self._font,
            text=text,
            before_coordinates=before_coordinates,
            after_coordinates=after_coordinates,
            before_instance_name=before_instance_name,
            after_instance_name=after_instance_name,
            top_points=top_points,
            panel_size=panel_size,
            columns=columns,
            file_stem=file_stem,
        )

    def build_delta_comparison_sheet(
        self,
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
        return DeltaInspector.build_delta_comparison_sheet(
            self._font,
            glyph_id=glyph_id,
            codepoint=codepoint,
            before_coordinates=before_coordinates,
            after_coordinates=after_coordinates,
            before_instance_name=before_instance_name,
            after_instance_name=after_instance_name,
            top_points=top_points,
            panel_size=panel_size,
            file_stem=file_stem,
        )

    def _matching_instance(self, coordinates: dict[str, float]):
        for instance in self.named_instances:
            if instance.coordinates == coordinates:
                return instance
        return None

    def _axis_for_tag(self, axis_tag: str) -> "VariableAxis":
        for axis in self.axes:
            if axis.tag == axis_tag:
                return axis
        raise ValueError(f"Unknown variable axis: {axis_tag!r}")

    def _grid_values_for_axis(
        self,
        axis: "VariableAxis | None",
        values: list[float | str] | tuple[float | str, ...],
        *,
        use_presets: bool,
        include_default: bool,
        include_bounds: bool,
        axis_role: str,
    ) -> list[float]:
        if axis is None:
            return []
        if values:
            return [self._resolve_axis_value(axis, value) for value in values]
        if use_presets:
            suggested = self.suggest_axis_values(
                axis.tag,
                include_default=include_default,
                include_bounds=include_bounds,
            )
            if suggested:
                return suggested
        raise ValueError(f"{axis_role} axis grid requires at least one value")

    def _preview_bundles_for_named_instances(
        self,
        names: list[str] | tuple[str, ...] | None,
        *,
        include_default: bool,
    ) -> list[WebFontBundle]:
        bundles: list[WebFontBundle] = []
        for resolved, instantiated in self.instantiate_many(names, include_default=include_default):
            bundles.append(
                WebFontBundle(
                    family=instantiated.font_family,
                    style=instantiated.font_style,
                    css="",
                    html="",
                    css_filename="",
                    html_filename="",
                    preview_font=instantiated,
                    review_label=resolved.label,
                    manifest={"instance_coordinates": resolved.coordinates},
                )
            )
        return bundles

    def _resolve_named_instance(self, query: str) -> "VariableInstance":
        matched = self._font.get_named_instance(query)
        if matched is not None:
            return matched

        matches = self._find_named_instances(query)
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            names = ", ".join(instance.label for instance in matches)
            raise ValueError(f"Ambiguous named instance: {query!r}. Matches: {names}")
        raise ValueError(f"Unknown named instance: {query!r}")

    def _find_named_instances(self, query: str) -> list["VariableInstance"]:
        needle = _normalize_match_token(query)
        matches: list[VariableInstance] = []
        for instance in self.named_instances:
            if _instance_matches_query(instance, needle):
                matches.append(instance)
        return matches

    def _resolve_axis_value(self, axis: "VariableAxis", value: float | str) -> float:
        if isinstance(value, str):
            raw = value.strip()
            if not raw:
                raise ValueError(f"Empty value is not valid for variable axis: {axis.tag!r}")
            lowered = raw.casefold()
            if lowered in {"min", "minimum"}:
                return axis.min_value
            if lowered == "default":
                return axis.default_value
            if lowered in {"max", "maximum"}:
                return axis.max_value
            preset = axis.get_preset(raw)
            if preset is not None:
                return preset.value
            numeric = _strip_axis_unit(raw, axis.unit_label)
            try:
                return axis.clamp(float(numeric))
            except ValueError as exc:
                options = ", ".join(_symbolic_axis_options(axis))
                raise ValueError(
                    f"Unknown coordinate preset for axis {axis.tag!r}: {value!r}. "
                    f"Expected a number or one of: {options}"
                ) from exc
        return axis.clamp(float(value))


def _sheet_label(coordinates: dict[str, float]) -> str:
    parts = [f"{tag}={_format_axis_value(value)}" for tag, value in sorted(coordinates.items())]
    return " ".join(parts)


def _sheet_title(
    axis_tag: str,
    values: list[float] | tuple[float, ...],
    *,
    secondary_axis_tag: str | None,
    secondary_values: list[float] | tuple[float, ...],
    instance_name: str | None,
) -> str:
    if secondary_axis_tag is None:
        title = f"{axis_tag} sweep ({len(values)} values)"
    else:
        title = (
            f"{axis_tag} x {secondary_axis_tag} grid "
            f"({len(values)} x {len(secondary_values)})"
        )
    if instance_name:
        title = f"{title} base={instance_name}"
    return title


def _comparison_title(before: ResolvedInstance, after: ResolvedInstance) -> str:
    delta = _comparison_delta_summary(before.coordinates, after.coordinates)
    if delta:
        return f"Before vs After ({delta})"
    return "Before vs After"


def _comparison_label(resolved: ResolvedInstance) -> str:
    return f"{resolved.label} {_sheet_label(resolved.coordinates)}".strip()


def _comparison_diff_label(before: ResolvedInstance, after: ResolvedInstance) -> str:
    changed_axes = _changed_axes(before.coordinates, after.coordinates)
    if not changed_axes:
        return "NO DIFF"
    return f"DIFF {', '.join(tag.upper() for tag in changed_axes)}"


def _comparison_overlay_label(before: ResolvedInstance, after: ResolvedInstance) -> str:
    changed_axes = _changed_axes(before.coordinates, after.coordinates)
    if not changed_axes:
        return "OVERLAY SAME"
    return f"OVERLAY {', '.join(tag.upper() for tag in changed_axes)}"


def _comparison_delta_summary(
    before_coordinates: dict[str, float],
    after_coordinates: dict[str, float],
) -> str:
    parts: list[str] = []
    for tag in sorted(set(before_coordinates) | set(after_coordinates)):
        before_value = before_coordinates.get(tag)
        after_value = after_coordinates.get(tag)
        if before_value == after_value:
            continue
        parts.append(
            f"{tag} {_format_axis_value(before_value or 0.0)}->{_format_axis_value(after_value or 0.0)}"
        )
    return ", ".join(parts)


def _comparison_notes(before: ResolvedInstance, after: ResolvedInstance) -> list[str]:
    changed_axes = _changed_axes(before.coordinates, after.coordinates)
    if not changed_axes:
        return ["No axis changes. Both sides resolve to the same coordinates."]
    lines = [f"Changed axes: {', '.join(changed_axes)}"]
    for tag in changed_axes:
        lines.append(
            f"{tag}: {_format_axis_value(before.coordinates[tag])} -> "
            f"{_format_axis_value(after.coordinates[tag])}"
        )
    return lines


def _changed_axes(
    before_coordinates: dict[str, float],
    after_coordinates: dict[str, float],
) -> list[str]:
    changed: list[str] = []
    for tag in sorted(set(before_coordinates) | set(after_coordinates)):
        if before_coordinates.get(tag) != after_coordinates.get(tag):
            changed.append(tag)
    return changed


def _format_axis_value(value: float) -> str:
    if float(value).is_integer():
        return str(int(value))
    return f"{value:.2f}".rstrip("0").rstrip(".")


def _normalize_match_token(value: str) -> str:
    return "".join(ch for ch in value.casefold() if ch.isalnum())


def _instance_matches_query(instance: "VariableInstance", needle: str) -> bool:
    if not needle:
        return False
    candidates = [instance.label]
    if instance.postscript_name is not None:
        candidates.append(instance.postscript_name)
    return any(needle in _normalize_match_token(candidate) for candidate in candidates)


def _strip_axis_unit(value: str, unit_label: str) -> str:
    if unit_label and value.casefold().endswith(unit_label.casefold()):
        return value[: -len(unit_label)].strip()
    return value


def _symbolic_axis_options(axis: "VariableAxis") -> list[str]:
    options = ["min", "default", "max"]
    options.extend(preset.name for preset in axis.presets)
    return options


def _unique_sorted(values: list[float]) -> list[float]:
    return sorted({float(value) for value in values})


def _ordered_unique_coordinates(
    previews: list[tuple[ResolvedInstance, PreviewImage]],
    axis_tag: str | None,
) -> list[float]:
    if axis_tag is None:
        return []
    values: list[float] = []
    seen: set[float] = set()
    for resolved, _preview in previews:
        value = resolved.coordinates[axis_tag]
        if value in seen:
            continue
        seen.add(value)
        values.append(value)
    return values
