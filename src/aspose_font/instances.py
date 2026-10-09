"""Variable font instance release package workflow."""

from __future__ import annotations

import json
import time
from collections.abc import Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from typing import TYPE_CHECKING

from aspose_font.preview import PreviewImage

if TYPE_CHECKING:
    from aspose_font.instancing import ResolvedInstance, SmartInstancer
    from aspose_font.ttf.font import TtfFont


def _filter_coordinates(
    coordinates: dict[str, float],
    compare_axes: Sequence[str] | None,
) -> dict[str, float]:
    if compare_axes is None:
        return coordinates
    return {tag: value for tag, value in coordinates.items() if tag in compare_axes}


@dataclass(slots=True, frozen=True)
class VariableInstancePackage:
    """Single-folder deliverable for variable font instance releases."""

    instances: list["ResolvedInstance"]
    fonts: list["TtfFont"]
    comparison_board: PreviewImage
    stat_evidence: dict[str, object]
    review_manifest: dict[str, object]
    preview_text: str
    output_directory: Path
    build_time_ms: float = 0.0

    def write_to(
        self,
        directory: str | Path,
        *,
        font_filename: str = "instance.ttf",
        stat_evidence_filename: str = "stat-evidence.json",
        preview_filename: str = "preview.png",
        manifest_filename: str = "manifest.json",
    ) -> list[Path]:
        """Write package to filesystem."""
        output_dir = Path(directory)
        output_dir.mkdir(parents=True, exist_ok=True)

        written: list[Path] = []

        font_path: Path | None = None
        for resolved, font in zip(self.instances, self.fonts):
            if len(self.instances) == 1 and font_filename == "instance.ttf":
                font_path = output_dir / font_filename
            else:
                filename = _filename_for_instance(resolved)
                font_path = output_dir / f"{filename}.ttf"
            font.save(font_path)
            written.append(font_path)

        stat_path = output_dir / stat_evidence_filename
        stat_path.write_text(
            json.dumps(self.stat_evidence, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        written.append(stat_path)

        manifest_path = output_dir / manifest_filename
        manifest_path.write_text(
            json.dumps(self.review_manifest, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        written.append(manifest_path)

        comparison_path = output_dir / preview_filename
        self.comparison_board.write_to(comparison_path)
        written.append(comparison_path)

        return written


def _filename_for_instance(resolved: "ResolvedInstance") -> str:
    source_instance = resolved.source_instance
    if source_instance is not None:
        label = source_instance.label
    elif resolved.is_default:
        label = "default"
    else:
        label = "custom"

    coords = "_".join(
        f"{tag}{_format_axis_value(val)}"
        for tag, val in sorted(resolved.coordinates.items())
    )

    safe_label = "".join(c if c.isalnum() or c in (" ", "-", "_") else "_" for c in label)
    safe_coords = "".join(c if c.isalnum() else "_" for c in coords)

    return (
        f"{safe_label.strip().replace(' ', '_')}_{safe_coords}"
        .rstrip("_")
        .replace("__", "_")
    )


def _format_axis_value(value: float) -> str:
    if float(value).is_integer():
        return str(int(value))
    return f"{value:.2f}".rstrip("0").rstrip(".")


class VariableInstanceBuilder:
    """Build variable instance release packages from variable fonts."""

    def __init__(self, font: "TtfFont") -> None:
        if not font.is_variable:
            from aspose_font._exceptions import FontNotSupportedException

            raise FontNotSupportedException("Font is not variable")
        self._font = font

    @property
    def font(self) -> "TtfFont":
        return self._font

    @property
    def smart_instancer(self) -> SmartInstancer:
        from aspose_font.instancing import SmartInstancer
        return SmartInstancer(self._font)

    def build_package(
        self,
        names: list[str] | tuple[str, ...] | None = None,
        *,
        include_default: bool = True,
        naming_strategy: str = "instance-family",
        family_suffix: str | None = None,
        legacy_family_name: str | None = None,
        typographic_family_name: str | None = None,
        legacy_style_name: str | None = None,
        typographic_style_name: str | None = None,
        stat_policy: str = "drop",
        preserve_source_stat_flags: bool | str = False,
        preview_text: str = "Hamburgefons 0123456789",
        compare_axes: Sequence[str] | None = None,
        apply_avar: bool = True,
        max_instances: int | None = None,
        ci_fast_mode: bool = False,
        skip_hvar: bool = False,
    ) -> VariableInstancePackage:
        start_time = time.perf_counter()
        if ci_fast_mode:
            max_instances = 1
            apply_avar = False
            if names is None and include_default:
                instance_names = ["__default__"]
            elif names is None:
                instance_names = [self._font.variable_instances[0].label] if self._font.variable_instances else ["__default__"]
            else:
                instance_names = list(names)[:max_instances]
                if include_default and "__default__" not in instance_names:
                    instance_names.insert(0, "__default__")
        else:
            if names is None:
                instance_names: list[str] = []
                for instance in self._font.variable_instances:
                    instance_names.append(instance.label)
                if include_default:
                    instance_names.insert(0, "__default__")
            else:
                instance_names = list(names)
                if include_default and "__default__" not in instance_names:
                    instance_names.insert(0, "__default__")

            if max_instances is not None and max_instances > 0:
                instance_names = instance_names[:max_instances]

        resolved_instances: list[ResolvedInstance] = []
        generated_fonts: list["TtfFont"] = []

        for name in instance_names:
            if name == "__default__":
                resolved = self.smart_instancer.resolve()
            else:
                resolved = self.smart_instancer.resolve(instance_name=name)

            filtered_coords = _filter_coordinates(resolved.coordinates, compare_axes)

            font = self._font.instantiate(
                filtered_coords,
                naming_strategy=naming_strategy,
                family_suffix=family_suffix,
                legacy_family_name=legacy_family_name,
                typographic_family_name=typographic_family_name,
                legacy_style_name=legacy_style_name,
                typographic_style_name=typographic_style_name,
                stat_policy=stat_policy,
                preserve_source_stat_flags=preserve_source_stat_flags,
                apply_avar=apply_avar,
                skip_hvar=skip_hvar or ci_fast_mode,
                ci_fast_mode=ci_fast_mode,
            )
            if compare_axes is not None:
                resolved = replace(resolved, coordinates=filtered_coords)
            resolved_instances.append(resolved)
            generated_fonts.append(font)

        if ci_fast_mode and len(resolved_instances) == 1:
            from aspose_font.preview import FontPreviewBuilder
            font = generated_fonts[0]
            preview = FontPreviewBuilder.build(
                font,
                text="H",
                size=1.0,
                color=(17, 17, 17),
                background=(255, 253, 248),
                padding=0,
                antialias=False,
                file_stem="preview",
            )
            comparison_board = preview
        elif ci_fast_mode:
            from aspose_font.preview import FontPreviewBuilder
            comparison_board = FontPreviewBuilder.build(
                generated_fonts[0] if generated_fonts else self._font,
                text="H",
                size=1.0,
                color=(17, 17, 17),
                background=(255, 253, 248),
                padding=0,
                antialias=False,
                file_stem="preview",
            )
        else:
            comparison_board = self.smart_instancer.build_comparison_sheet(
                text=preview_text,
                size=8.0 if ci_fast_mode else 24.0,
                antialias=False,
                gap=2 if ci_fast_mode else 4,
                file_stem="comparison-board",
                compare_axes=compare_axes,
            )

        stat_evidence = self._build_stat_evidence(
            resolved_instances,
            generated_fonts,
            stat_policy=stat_policy,
            ci_fast_mode=ci_fast_mode,
        )

        review_manifest = self._build_review_manifest(
            resolved_instances,
            stat_evidence,
            preview_text,
            naming_strategy,
            family_suffix,
        )

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        return VariableInstancePackage(
            instances=resolved_instances,
            fonts=generated_fonts,
            comparison_board=comparison_board,
            stat_evidence=stat_evidence,
            review_manifest=review_manifest,
            preview_text=preview_text,
            output_directory=Path(),
            build_time_ms=elapsed_ms,
        )

    def _build_stat_evidence(
        self,
        resolved_instances: list[ResolvedInstance],
        fonts: list["TtfFont"],
        *,
        stat_policy: str,
        preserve_source_stat_flags: bool | str = False,
        ci_fast_mode: bool = False,
    ) -> dict[str, object]:
        evidence: dict[str, object] = {
            "policy": stat_policy,
            "instances": [],
        }

        for resolved, font in zip(resolved_instances, fonts):
            instance_evidence: dict[str, object] = {
                "label": resolved.label,
                "coordinates": dict(resolved.coordinates),
                "source_instance": (
                    resolved.source_instance.label
                    if resolved.source_instance is not None
                    else None
                ),
            }

            if not ci_fast_mode:
                naming_preview = self._font.preview_naming_policy(
                    resolved.coordinates,
                    naming_strategy="instance-family",
                    family_suffix=None,
                    legacy_family_name=None,
                    typographic_family_name=None,
                    legacy_style_name=None,
                    typographic_style_name=None,
                    stat_policy=stat_policy,
                    preserve_source_stat_flags=preserve_source_stat_flags,
                )
                stat_diag = naming_preview.stat_diagnostics

                if stat_diag is not None:
                    instance_evidence["stat_diagnostics"] = {
                        "stat_policy": stat_diag.stat_policy,
                        "supported_stat_policies": list(stat_diag.supported_stat_policies),
                        "source_has_stat": stat_diag.source_has_stat,
                        "static_export_action": stat_diag.static_export_action,
                        "stat_policy_recommendation": stat_diag.stat_policy_recommendation,
                        "stat_policy_recommendation_reasons": list(
                            stat_diag.stat_policy_recommendation_reasons
                        ),
                        "stat_policy_next_action": stat_diag.stat_policy_next_action,
                        "generated_stat_axis_tags": list(stat_diag.generated_stat_axis_tags),
                        "generated_stat_name_ids": list(stat_diag.generated_stat_name_ids),
                    }

            evidence["instances"].append(instance_evidence)

        return evidence

    def _build_review_manifest(
        self,
        resolved_instances: list[ResolvedInstance],
        stat_evidence: dict[str, object],
        preview_text: str,
        naming_strategy: str,
        family_suffix: str | None,
    ) -> dict[str, object]:
        manifest: dict[str, object] = {
            "kind": "variable_instance_release_package",
            "version": 1,
            "preview_text": preview_text,
            "naming_strategy": naming_strategy,
            "family_suffix": family_suffix,
            "instance_count": len(resolved_instances),
            "instances": [],
            "artifacts": [
                {
                    "kind": "font",
                    "pattern": "*.ttf",
                    "description": "Static instance fonts (one per resolved instance)",
                },
                {
                    "kind": "json",
                    "filename": "stat-evidence.json",
                    "description": "STAT policy decisions and evidence per instance",
                },
                {
                    "kind": "json",
                    "filename": "manifest.json",
                    "description": "This review manifest",
                },
                {
                    "kind": "image",
                    "filename": "preview.png",
                    "description": "Before/after comparison preview sheet",
                },
            ],
        }

        for resolved in resolved_instances:
            instance_manifest: dict[str, object] = {
                "label": resolved.label,
                "is_default": resolved.is_default,
                "coordinates": dict(resolved.coordinates),
                "source_instance": (
                    resolved.source_instance.label
                    if resolved.source_instance is not None
                    else None
                ),
                "stat_decision": (
                    "live"
                    if resolved.is_default or resolved.source_instance is not None
                    else "fallback"
                ),
            }
            manifest["instances"].append(instance_manifest)

        return manifest
