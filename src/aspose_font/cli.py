"""CLI for aspose-font - font inspection, conversion, and web export."""
# ruff: noqa: I001

from __future__ import annotations

import argparse
import json
from collections.abc import Iterable
from typing import Any
from pathlib import Path
import sys

from aspose_font import (
    FontCapabilityBuilder,
    FontCapabilityReport,
    FontCleaner,
    FontLoader,
    FontPreviewBuilder,
    FontQaPackage,
    FontQaReport,
    FontQaReporter,
    FontType,
    TtfFont,
    WebFontBuilder,
    WebFontOptimizer,
    __version__,
    build_web_optimizer_package,
    compute_designspace_coverage,
    generate_waterfall_matrix,
)
from aspose_font.animation import AnimationAsset, AnimationPreviewBuilder
from aspose_font.autonomous import (
    run_autonomous_workflow,
)
from aspose_font.autonomous_dev import run_autonomous_development
from aspose_font.cff.type2 import apply_cff2_blend
from aspose_font.cff2 import Cff2Diagnostic, Cff2Font
from aspose_font.cff2.diagnostic import Cff2DiagnosticAxis
from aspose_font.ci import alert, perf_var_package, perf_cff2_subsetter
from aspose_font.ci.perf import PerformanceRegressionError, run_ci_benchmarks
from aspose_font.converter import FontConverter
from aspose_font.diagnostics.coverage import generate_designspace_coverage_report
from aspose_font.perf.regression_one_command import run_one_command_regression
from aspose_font.performance import measure_load_time
from aspose_font.instances import VariableInstanceBuilder
from aspose_font.preview import generate_designspace_diff_overlay, _convert_png_to_pdf
from aspose_font.delta import generate_overlay
from aspose_font.subset_presets import available_subset_presets
from aspose_font.subsetter import FontSubsetter
from aspose_font.ttf.tables.stat import (
    STATIC_STAT_POLICIES,
    parse_stat_table,
)

_NAMING_STRATEGY_CHOICES = TtfFont.available_naming_strategies()
_STAT_POLICY_CHOICES = STATIC_STAT_POLICIES

_FORMAT_MAP: dict[str, FontType] = {
    "ttf": FontType.TTF,
    "cff": FontType.CFF,
    "woff": FontType.WOFF,
    "woff2": FontType.WOFF2,
    "eot": FontType.EOT,
}

_DEFAULT_PREVIEW_TEXT = "Hamburgefons 0123456789"
_SPECIMEN_TEMPLATES = ("classic", "editorial", "lab")


def _die(msg: str) -> None:
    print(f"Error: {msg}", file=sys.stderr)
    sys.exit(1)


def _parse_cli_int(value: str) -> int:
    try:
        return int(value, 0)
    except ValueError as exc:
        raise ValueError(f"Invalid integer value: {value!r}") from exc


def _parse_range(value: str) -> tuple[int, int]:
    if "-" not in value:
        raise ValueError(f"Invalid range {value!r}. Expected start-end.")
    start_text, end_text = value.split("-", 1)
    start = _parse_cli_int(start_text.strip())
    end = _parse_cli_int(end_text.strip())
    if start > end:
        raise ValueError(f"Invalid range {value!r}. Start must be <= end.")
    return start, end


def _parse_split_range_spec(value: str) -> tuple[str, tuple[int, int]]:
    if ":" not in value:
        raise ValueError(f"--split-ranges format must be NAME:START-END, got: {value}")
    name_part, range_part = value.split(":", 1)
    range_part = range_part.upper().lstrip("U+")
    if "-" not in range_part:
        raise ValueError(f"Range must be START-END, got: {range_part}")
    start_str, end_str = range_part.split("-", 1)
    start_str = start_str.strip()
    end_str = end_str.strip()

    def parse_hex_or_int(s: str) -> int:
        s = s.upper()
        if s.startswith("0X"):
            return int(s, 16)
        try:
            return int(s, 16)
        except ValueError:
            return int(s, 10)

    start = parse_hex_or_int(start_str)
    end = parse_hex_or_int(end_str)
    if start > end:
        raise ValueError(f"Invalid range {name_part}: {start:x} > {end:x}")
    return name_part, (start, end)


def _parse_instance(values: Iterable[str]) -> dict[str, float]:
    coordinates: dict[str, float] = {}
    for value in values:
        if "=" not in value:
            raise ValueError(f"Invalid instance coordinate {value!r}. Expected tag=value.")
        tag, raw = value.split("=", 1)
        tag = tag.strip()
        if len(tag) != 4:
            raise ValueError(f"Invalid axis tag {tag!r}. Expected a 4-character OpenType tag.")
        try:
            coordinates[tag] = float(raw.strip())
        except ValueError as exc:
            raise ValueError(f"Invalid axis value in {value!r}.") from exc
    return coordinates


def _parse_instance_comma_separated(value: str) -> dict[str, float]:
    """Parse comma-separated coordinates from a single string (e.g., 'wght=400,wdth=100')."""
    coordinates: dict[str, float] = {}
    parts = [part.strip() for part in value.split(",") if part.strip()]
    if not parts:
        raise ValueError(f"Invalid instance coordinates {value!r}.")
    for part in parts:
        if "=" not in part:
            raise ValueError(f"Invalid instance coordinate {part!r}. Expected tag=value.")
        tag, raw = part.split("=", 1)
        tag = tag.strip()
        if len(tag) != 4:
            raise ValueError(f"Invalid axis tag {tag!r}. Expected a 4-character OpenType tag.")
        try:
            coordinates[tag] = float(raw.strip())
        except ValueError as exc:
            raise ValueError(f"Invalid axis value in {part!r}.") from exc
    return coordinates


def _parse_symbolic_instance(values: Iterable[str]) -> dict[str, float | str]:
    coordinates: dict[str, float | str] = {}
    for value in values:
        if "=" not in value:
            raise ValueError(f"Invalid instance coordinate {value!r}. Expected tag=value.")
        tag, raw = value.split("=", 1)
        tag = tag.strip()
        raw_value = raw.strip()
        if len(tag) != 4:
            raise ValueError(f"Invalid axis tag {tag!r}. Expected a 4-character OpenType tag.")
        if not raw_value:
            raise ValueError(f"Invalid axis value in {value!r}.")
        try:
            coordinates[tag] = float(raw_value)
        except ValueError:
            coordinates[tag] = raw_value
    return coordinates


def _parse_animation_step(value: str) -> tuple[str | None, dict[str, float | str] | None]:
    raw = value.strip()
    if not raw:
        raise ValueError("Animation path state cannot be empty.")
    if "=" not in raw:
        return raw, None
    parts = [part.strip() for part in raw.split(",") if part.strip()]
    if not parts:
        raise ValueError(f"Invalid animation path state {value!r}.")
    return None, _parse_symbolic_instance(parts)


def _parse_float_list(values: Iterable[str], *, label: str) -> list[float]:
    parsed: list[float] = []
    for value in values:
        try:
            parsed.append(float(value))
        except ValueError as exc:
            raise ValueError(f"Invalid {label} value: {value!r}") from exc
    return parsed


def _load_font(args: argparse.Namespace):
    return FontLoader.open(
        args.file,
        collection_index=getattr(args, "collection_index", None),
    )


def _load_loaded_font(args: argparse.Namespace):
    return FontLoader.load(
        args.file,
        collection_index=getattr(args, "collection_index", None),
    )


def _add_collection_index_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--collection-index",
        type=int,
        help="Select a face index from a TrueType Collection (TTC). Defaults to 0 for TTC inputs.",
    )


def _add_naming_override_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--legacy-family-name",
        help="Explicit legacy/menu family name for name ID 1.",
    )
    parser.add_argument(
        "--typographic-family-name",
        help="Explicit typographic family name for name IDs 16, 21, and 25.",
    )
    parser.add_argument(
        "--legacy-style-name",
        help="Explicit legacy/menu style name for name ID 2.",
    )
    parser.add_argument(
        "--typographic-style-name",
        help="Explicit typographic style name for name IDs 17 and 22.",
    )


def _add_stat_policy_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--stat-policy",
        choices=_STAT_POLICY_CHOICES,
        default="drop",
        help="STAT metadata policy for generated static variable-font outputs (default: drop).",
    )
    parser.add_argument(
        "--preserve-stat-flags",
        nargs="?",
        const="elidable,linked",
        choices=[None, "elidable", "linked", "elidable,linked", "linked,elidable"],
        default=None,
        help="Preserve source STAT AxisValue flags in generated static STAT tables. "
        "Comma-separated: elidable, linked (default: preserve both).",
    )


def _naming_override_kwargs(args: argparse.Namespace) -> dict[str, str | None]:
    return {
        "legacy_family_name": args.legacy_family_name,
        "typographic_family_name": args.typographic_family_name,
        "legacy_style_name": args.legacy_style_name,
        "typographic_style_name": args.typographic_style_name,
    }


def _attach_collection_index_args(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    for parser in subparsers.choices.values():
        has_file_arg = any(
            action.dest == "file" and not action.option_strings for action in parser._actions
        )
        has_collection_index = any(action.dest == "collection_index" for action in parser._actions)
        if has_file_arg and not has_collection_index:
            _add_collection_index_arg(parser)


def _grid_selection_options(args: argparse.Namespace) -> dict[str, bool]:
    return {
        "use_axis_presets": bool(args.use_presets),
        "use_secondary_axis_presets": bool(args.use_secondary_presets),
        "include_default": not bool(args.no_default),
        "include_bounds": bool(args.include_bounds),
    }


def _format_axis_value(value: float) -> str:
    if float(value).is_integer():
        return str(int(value))
    return f"{value:.2f}".rstrip("0").rstrip(".")


def _coordinate_label(coordinates: dict[str, float]) -> str:
    return " ".join(
        f"{tag}={_format_axis_value(value)}" for tag, value in sorted(coordinates.items())
    )


def _format_codepoint(value: int) -> str:
    return f"U+{int(value):04X}"


def _format_codepoint_sample(values: object, *, limit: int = 12) -> str:
    if not isinstance(values, list):
        return ""
    return ", ".join(_format_codepoint(int(value)) for value in values[:limit])


def _print_web_export_summary(manifest: dict[str, object]) -> None:
    print(f"Export mode: {manifest.get('export_mode', 'static')}")
    export_reason = manifest.get("export_reason")
    if export_reason:
        print(f"Export reason: {export_reason}")
    export_note = manifest.get("export_note")
    if export_note and export_note != export_reason:
        print(f"Export note: {export_note}")
    _print_coverage_summary(manifest)


def _print_web_optimizer_summary(manifest: dict[str, object]) -> None:
    performance = manifest.get("performance")
    if isinstance(performance, dict):
        elapsed_ms = performance.get("elapsed_ms")
        load_time_ms = performance.get("load_time_ms")
        subset_time_ms = performance.get("subset_time_ms")
        compress_time_ms = performance.get("compress_time_ms")
        manifest_write_time_ms = performance.get("manifest_write_time_ms")
        total_seconds = performance.get("total_seconds")
        size_summary_seconds = performance.get("size_summary_seconds")
        css_generation_seconds = performance.get("css_generation_seconds")
        specimen_html_seconds = performance.get("specimen_html_seconds")

        print(f"Total time: {elapsed_ms} ms" if elapsed_ms is not None else "")
        if load_time_ms is not None:
            print(f"  Load: {load_time_ms} ms")
        if subset_time_ms is not None:
            print(f"  Subset: {subset_time_ms} ms")
        if compress_time_ms is not None:
            print(f"  Compress: {compress_time_ms} ms")
        if manifest_write_time_ms is not None:
            print(f"  Manifest: {manifest_write_time_ms} ms")
        if total_seconds is not None:
            print(f"Total time (seconds): {total_seconds:.4f}s")
        if size_summary_seconds is not None:
            print(f"  Size summary: {size_summary_seconds:.4f}s")
        if css_generation_seconds is not None:
            print(f"  CSS generation: {css_generation_seconds:.4f}s")
        if specimen_html_seconds is not None:
            print(f"  Specimen HTML: {specimen_html_seconds:.4f}s")
    readiness = manifest.get("readiness")
    size_summary = manifest.get("size_summary")
    print(
        f"Optimizer status: {readiness.get('status', 'unknown') if isinstance(readiness, dict) else 'unknown'}"
    )
    if isinstance(readiness, dict):
        print(f"Optimizer score: {readiness.get('score', 0)}")
    decision_report = manifest.get("decision_report")
    if isinstance(decision_report, dict):
        mode = decision_report.get("mode")
        if mode:
            print(f"Decision: {mode}")
        reason = decision_report.get("reason", "")
        if reason:
            print(f"Reason: {reason}")
    if isinstance(size_summary, dict):
        source_bytes = size_summary.get("source_bytes")
        total_web_font_bytes = size_summary.get("total_web_font_bytes")
        total_package_bytes = size_summary.get("total_package_bytes")
        if source_bytes is not None:
            print(f"Source bytes: {source_bytes}")
        print(f"Web font bytes: {total_web_font_bytes}")
        print(f"Package bytes: {total_package_bytes}")
        reduction_percent = size_summary.get("web_font_delta_vs_source_percent")
        if reduction_percent is not None:
            print(f"Size reduction: {reduction_percent}%")
    notes = manifest.get("notes")
    if isinstance(notes, list):
        for note in notes:
            if not isinstance(note, dict):
                continue
            code = note.get("code", "note")
            message = note.get("message", "")
            print(f"Note {code}: {message}")


def _print_web_optimizer_example_output() -> None:
    example_manifest = {
        "kind": "web_optimizer_package",
        "bundle_manifest_filename": "web-manifest.json",
        "family": "Roboto",
        "style": "Regular",
        "export_mode": "variable-live",
        "decision": "live",
        "decision_report": {
            "decision": "live",
            "mode": "live",
            "reasons": [
                "Variable font with variable export mode enabled. Output supports variable axes."
            ],
            "summary": "Exporting live variable font with full axis support.",
            "remediation": [
                "Variable font ready for web use. Consider adding unicode-range subsetting to reduce payload size."
            ],
            "export_mode": "variable-live",
        },
        "source_path": "testdata/Roboto-VariableFont_wdth,wght.ttf",
        "local_processing": True,
        "privacy_note": "Fonts are processed locally by the Python workflow; no upload is required.",
        "performance": {
            "elapsed_ms": 42,
            "load_time_ms": 10,
            "subset_time_ms": 15,
            "compress_time_ms": 12,
            "manifest_write_time_ms": 5,
        },
        "size_summary": {
            "source_bytes": 184320,
            "output_bytes": 45678,
            "woff2_bytes": 41234,
            "woff_bytes": 45678,
            "compression_ratio": 0.2235,
            "font_assets": [
                {"filename": "roboto-regular.woff2", "media_type": "font/woff2", "bytes": 41234},
                {"filename": "roboto-regular.woff", "media_type": "font/woff", "bytes": 45678},
            ],
            "css_bytes": 3456,
            "html_bytes": 12345,
            "bundle_manifest_bytes": 2345,
            "total_web_font_bytes": 86912,
            "total_package_bytes": 102745,
            "web_font_delta_vs_source_bytes": 97408,
            "web_font_delta_vs_source_percent": 52.85,
        },
        "readiness": {
            "score": 95,
            "status": "ready",
            "reasons": [],
            "performance_note": "Processed in 42 ms",
        },
        "notes": [
            {
                "code": "ready-for-handoff",
                "severity": "info",
                "message": "The generated web font package is ready for frontend handoff.",
            }
        ],
        "bundle": {},
    }
    print(json.dumps(example_manifest, indent=2, sort_keys=True))


def _print_coverage_summary(manifest: dict[str, object]) -> None:
    subset = manifest.get("subset")
    if not isinstance(subset, dict) or not subset.get("applied"):
        return
    coverage = subset.get("coverage")
    if not isinstance(coverage, dict):
        return
    covered_count = int(coverage.get("covered_count", 0))
    requested_count = int(coverage.get("requested_count", 0))
    print(f"Coverage: {covered_count}/{requested_count} requested codepoints covered")
    missing_sample = _format_codepoint_sample(coverage.get("missing_codepoints"))
    if missing_sample:
        print(f"Missing: {missing_sample}")
    groups = coverage.get("groups")
    if not isinstance(groups, list):
        return
    for group in groups:
        if not isinstance(group, dict) or int(group.get("missing_count", 0)) == 0:
            continue
        group_sample = _format_codepoint_sample(group.get("missing_codepoints"))
        if group_sample:
            print(
                f"Missing in {group.get('kind', 'group')} {group.get('label', '')}: {group_sample}"
            )


def _resolve_glyph_target(
    *,
    gid: int | None,
    codepoint_text: str | None,
    character: str | None,
) -> tuple[int | None, int | None]:
    codepoint = _parse_cli_int(codepoint_text) if codepoint_text is not None else None
    if character is not None:
        if len(character) != 1:
            raise ValueError("--char requires exactly one character")
        if codepoint is not None or gid is not None:
            raise ValueError("Choose only one of --gid, --codepoint, or --char")
        codepoint = ord(character)
    return gid, codepoint


def _cmd_info(args: argparse.Namespace) -> None:
    try:
        loaded = _load_loaded_font(args)
    except Exception as exc:
        _die(str(exc))
    font = loaded.font
    m = font.metrics
    print(f"File:        {args.file}")
    print(f"Format:      {font.font_type.value}")
    if loaded.source.collection_index is not None and loaded.source.collection_size is not None:
        print(f"Collection:  {loaded.source.collection_index}/{loaded.source.collection_size - 1}")
    print(f"Name:        {font.font_name or ''}")
    print(f"Family:      {font.font_family or ''}")
    print(f"Style:       {font.font_style or ''}")
    print(f"Glyphs:      {font.num_glyphs}")
    print(f"Units/EM:    {m.units_per_em}")
    print(f"Ascender:    {m.ascender}")
    print(f"Descender:   {m.descender}")
    print(f"Line gap:    {m.line_gap}")


def _cmd_feature_variations(args: argparse.Namespace) -> None:
    try:
        loaded = _load_loaded_font(args)
    except Exception as exc:
        _die(str(exc))

    font = loaded.font
    if not isinstance(font, TtfFont):
        _die("Feature variations are only supported for TTF/OTF fonts")

    tags = font.feature_variations_list()

    if tags is None:
        print("No feature variations found in this font.")
        return

    for tag in tags:
        print(tag)


def _cmd_designspace_coverage(args: argparse.Namespace) -> None:
    try:
        font = _load_font(args)
    except Exception as exc:
        _die(str(exc))

    try:
        result = generate_designspace_coverage_report(font, args.preset)
    except ValueError as exc:
        if "Unknown subset preset" in str(exc):
            _die(
                f"Unknown preset {args.preset!r}. Available: {', '.join(available_subset_presets())}"
            )
        _die(str(exc))
    except Exception as exc:
        _die(str(exc))

    try:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
    except OSError as exc:
        _die(f"Cannot write to {args.output!r}: {exc}")

    print(
        f"Coverage: {result['covered_codepoints']}/{result['total_codepoints']} codepoints covered"
    )
    print(f"Written: {args.output}")


def _load_cff2_font(args: argparse.Namespace) -> Cff2Font:
    return Cff2Font.load(args.file)


def _cmd_cff2_preview(args: argparse.Namespace) -> None:
    """Render a PNG preview of a blended CFF2 glyph outline."""
    try:
        from aspose_font._types import GlyphId

        font = _load_cff2_font(args)

        coordinates = _parse_instance(args.axis) if args.axis else {}

        axes = font.get_axes()
        if axes:
            default_coords = {ax.tag: ax.default_value for ax in axes}
            for tag, value in coordinates.items():
                default_coords[tag] = value
            coordinates = default_coords

        gid = GlyphId(args.gid)

        glyph = font.glyph_accessor.get_glyph_by_id(gid)

        if not coordinates:
            blended_glyph = glyph
        else:
            blended_glyph = apply_cff2_blend(glyph, list(coordinates.values()))

        preview = FontPreviewBuilder.build(
            type(
                "FakeFont",
                (),
                {
                    "metrics": font.metrics,
                    "font_type": font.font_type,
                    "num_glyphs": font.num_glyphs,
                    "encoding": font.encoding,
                    "glyph_accessor": type(
                        "FakeAccessor",
                        (),
                        {
                            "get_glyph_by_id": lambda self, g: (
                                blended_glyph if g.value == args.gid else glyph
                            ),
                            "get_all_glyph_ids": lambda self: [GlyphId(args.gid)],
                        },
                    )(),
                },
            )(),
            text=args.text,
            size=24,
            padding=10,
        )

        written = preview.write_to(args.output)
        print(f"Saved: {written}")

    except Exception as exc:
        _die(str(exc))


def _cmd_cff2_info(args: argparse.Namespace) -> None:
    """Print CFF2 variable font information as JSON."""
    try:
        font = _load_cff2_font(args)
    except Exception as exc:
        _die(str(exc))

    axes = font.get_axes()

    sample_coords = {ax.tag: ax.default_value for ax in axes}
    try:
        sample_blend = font.blend(sample_coords)
    except Exception:
        sample_blend = 0.0

    diagnostic = Cff2Diagnostic(
        font_name=font.font_name,
        num_glyphs=font.num_glyphs,
        axes=[
            Cff2DiagnosticAxis(
                tag=ax.tag,
                min_value=ax.min_value,
                default_value=ax.default_value,
                max_value=ax.max_value,
                name_id=ax.name_id,
            )
            for ax in axes
        ],
        has_fvar=len(axes) > 0,
        sample_blend_result=sample_blend,
    )

    print(json.dumps(diagnostic.to_dict(), indent=2))


def _cmd_glyphs(args: argparse.Namespace) -> None:
    try:
        font = _load_font(args)
    except Exception as exc:
        _die(str(exc))
    limit = args.limit
    print(f"{'GID':<6}{'Name':<20}{'AdvWidth'}")
    for gid_int in range(min(font.num_glyphs, limit)):
        from aspose_font._types import GlyphId

        gid = GlyphId(gid_int)
        try:
            glyph = font.glyph_accessor.get_glyph_by_id(gid)
            name = glyph.glyph_name or ""
            adv = glyph.advance_width
        except Exception:
            name = ""
            adv = 0
        print(f"{gid_int:<6}{name:<20}{adv}")


def _cmd_convert(args: argparse.Namespace) -> None:
    fmt = args.to.lower()
    if fmt not in _FORMAT_MAP:
        _die(f"Unsupported format {args.to!r}. Supported: {', '.join(_FORMAT_MAP)}")
    try:
        font = _load_font(args)
    except Exception as exc:
        _die(str(exc))
    try:
        converted = FontConverter.convert(font, _FORMAT_MAP[fmt])
        data = converted.to_bytes()
    except Exception as exc:
        _die(str(exc))
    try:
        with open(args.output, "wb") as f:
            f.write(data)
    except OSError as exc:
        _die(str(exc))
    print(f"Saved: {args.output}")


def _cmd_metrics(args: argparse.Namespace) -> None:
    try:
        font = _load_font(args)
    except Exception as exc:
        _die(str(exc))
    m = font.metrics
    print(f"units_per_em:       {m.units_per_em}")
    print(f"ascender:           {m.ascender}")
    print(f"descender:          {m.descender}")
    print(f"line_gap:           {m.line_gap}")
    print(f"advance_width_max:  {m.advance_width_max}")
    print(f"underline_position: {m.underline_position}")
    print(f"underline_thickness:{m.underline_thickness}")


def _cmd_qa_report(args: argparse.Namespace) -> None:
    if not args.json_output and not args.html_output and not args.package_output:
        _die("qa-report requires --json-output, --html-output, and/or --package-output")
    try:
        font = _load_font(args)
        codepoints = [_parse_cli_int(value) for value in args.codepoint]
        ranges = [_parse_range(value) for value in args.range]
        preferred_languages = tuple(args.language) if args.language else "en"
        report = FontQaReporter.build(
            font,
            source_label=args.file,
            presets=args.preset,
            text=args.text,
            codepoints=codepoints,
            ranges=ranges,
            preferred_languages=preferred_languages,
            include_compatibility=args.include_extras,
            include_extras=args.include_extras,
            include_decision=args.include_decision,
        )
        package = None
        if args.package_output:
            package = FontQaReporter.build_package(
                font,
                args.package_output,
                source_label=args.file,
                presets=args.preset,
                text=args.text,
                codepoints=codepoints,
                ranges=ranges,
                preferred_languages=preferred_languages,
                preview_text=args.preview_text,
                preview_instance_name=args.preview_instance_name,
                include_compatibility=args.include_extras,
                include_extras=args.include_extras,
                include_decision=args.include_decision,
                ci_fast_mode=getattr(args, "ci_fast", False),
            )
            report = package.report
        if args.json_output:
            report.write_json(args.json_output)
        if args.html_output:
            report.write_html(args.html_output)
        if args.pdf_summary:
            report.write_pdf(args.pdf_summary)
        if args.summary:
            if package is None:
                _die("--summary requires --package-output")
            summary_path = package.directory / "summary.md"
            report.write_markdown(summary_path)
            payload_dict = report.payload.copy()
            artifacts = list(payload_dict.get("artifacts", []))
            artifacts.append({
                "kind": "markdown",
                "label": "QA report markdown summary",
                "path": "summary.md",
                "media_type": "text/markdown",
            })
            payload_dict["artifacts"] = artifacts
            report = FontQaReport(payload_dict)
            report.write_json(package.json_path)
            report.write_html(package.html_path)
            package = None
    except Exception as exc:
        _die(str(exc))

    payload = report.to_dict()
    warnings = payload.get("warnings", [])
    actions = payload.get("next_actions", [])
    identity = payload.get("identity", {})
    coverage = payload.get("coverage")
    decision = payload.get("decision")
    print(
        "QA report: "
        f"{identity.get('font_family', '') if isinstance(identity, dict) else ''} | "
        f"warnings={len(warnings) if isinstance(warnings, list) else 0} | "
        f"next_actions={len(actions) if isinstance(actions, list) else 0}"
    )
    if decision:
        print(
            f"Decision: {decision.get('recommended_action', 'unknown')} | "
            f"rationale={len(decision.get('rationale', []))} items"
        )
    if isinstance(coverage, dict):
        print(
            "Coverage: "
            f"{coverage.get('covered_count', 0)}/{coverage.get('requested_count', 0)} "
            "requested codepoints covered"
        )
    if args.json_output:
        print(f"Written: {args.json_output}")
    if args.html_output:
        print(f"Written: {args.html_output}")
    if args.pdf_summary:
        print(f"Written: {args.pdf_summary}")
    if args.summary:
        summary_path = Path(args.package_output) / "summary.md"
        print(f"Written: {summary_path}")
    if package is not None or args.summary:
        print(f"Package: {Path(args.package_output)}")
        print(f"Written: {Path(args.package_output) / 'qa-report.json'}")
        print(f"Written: {Path(args.package_output) / 'qa-report.html'}")
        preview_path = Path(args.package_output) / "assets" / "preview_main.png"
        if preview_path.exists():
            print(f"Written: {preview_path}")


def _cmd_qa_full_report(args: argparse.Namespace) -> None:
    if not args.output_dir:
        _die("qa-full-report requires --output-dir")
    try:
        font = _load_font(args)
        codepoints = [_parse_cli_int(value) for value in args.codepoint]
        ranges = [_parse_range(value) for value in args.range]
        preferred_languages = tuple(args.language) if args.language else "en"
        package = FontQaReporter.build_full_report(
            font,
            args.output_dir,
            source_label=args.file,
            presets=args.preset,
            text=args.text,
            codepoints=codepoints,
            ranges=ranges,
            preferred_languages=preferred_languages,
            preview_text=args.preview_text,
            preview_instance_name=args.preview_instance_name,
            include_compatibility=args.include_extras,
            include_extras=args.include_extras,
            include_decision=args.include_decision,
        )
    except Exception as exc:
        _die(str(exc))

    payload = package.report.to_dict()
    coverage = payload.get("coverage")
    decision = payload.get("decision")

    print(f"JSON: {package.json_path}")
    print(f"HTML: {package.html_path}")
    print(f"Preview: {package.preview_path}")

    if decision:
        print(
            f"Decision: {decision.get('recommended_action', 'unknown')} | "
            f"rationale={len(decision.get('rationale', []))} items"
        )
    if isinstance(coverage, dict):
        print(
            "Coverage: "
            f"{coverage.get('covered_count', 0)}/{coverage.get('requested_count', 0)} "
            "requested codepoints covered"
        )


def _cmd_decision_report(args: argparse.Namespace) -> None:
    if not args.output:
        _die("decision-report requires --output")
    try:
        font = _load_font(args)
        codepoints = [_parse_cli_int(value) for value in args.codepoint]
        ranges = [_parse_range(value) for value in args.range]
        preferred_languages = tuple(args.language) if args.language else "en"

        if args.package_output:
            package = FontQaReporter.build_package(
                font,
                args.package_output,
                source_label=args.file,
                presets=args.preset,
                text=args.text,
                codepoints=codepoints,
                ranges=ranges,
                preferred_languages=preferred_languages,
                preview_text=args.preview_text,
                preview_instance_name=args.preview_instance_name,
            )
        else:
            report = FontQaReporter.build(
                font,
                source_label=args.file,
                presets=args.preset,
                text=args.text,
                codepoints=codepoints,
                ranges=ranges,
                preferred_languages=preferred_languages,
            )
            package = FontQaPackage(
                report=report,
                directory=Path(args.output).parent,
                json_path=Path(args.output),
                html_path=Path(args.output),
                preview_path=Path(),
                artifacts=[],
            )

        from aspose_font.qa import generate_decision_report

        decision_report = generate_decision_report(package)

        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(decision_report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

        print(f"Decision: {decision_report.get('decision', 'unknown')}")
        print(f"Actions: {len(decision_report.get('recommended_actions', []))}")
        severity = decision_report.get("severity_summary", {})
        print(
            f"Severity: blocker={severity.get('blocker', 0)}, warning={severity.get('warning', 0)}, info={severity.get('info', 0)}"
        )
        print(f"Written: {args.output}")
    except Exception as exc:
        _die(str(exc))



def _cmd_full_report(args: argparse.Namespace) -> None:
    try:
        font_path = args.font
        output_root = Path(args.output)
        output_root.mkdir(parents=True, exist_ok=True)
        # Load font
        font = FontLoader.open(font_path)
        # Web optimizer
        web_dir = output_root / "web"
        web_dir.mkdir(parents=True, exist_ok=True)
        web_pkg = WebFontOptimizer.build(font, source_path=font_path)
        web_pkg.write_to(web_dir)
        # QA report
        qa_dir = output_root / "qa"
        qa_dir.mkdir(parents=True, exist_ok=True)
        FontQaReporter.build_package(font, qa_dir, source_label=font_path)
        # Variable instances
        instance_dir = output_root / "instance"
        instance_dir.mkdir(parents=True, exist_ok=True)
        instance_pkg = VariableInstanceBuilder(font).build_package()
        instance_pkg.write_to(instance_dir, manifest_filename="instance-manifest.json")
        print(f"Full report generated at {output_root}")
    except Exception as exc:
        _die(str(exc))

def _cmd_web_decision_report(args: argparse.Namespace) -> None:
    """CLI subcommand to generate a decision report from optimizer output."""
    try:
        optimizer = WebFontOptimizer(args.file, args.output_dir)
        report = optimizer.generate_decision_report()
        if getattr(args, "output", None):
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            print(f"Written: {args.output}")
        else:
            print(json.dumps(report, indent=2, sort_keys=True))
    except Exception as exc:
        _die(str(exc))

def _cmd_decision_report_cli(args: argparse.Namespace) -> None:
    """CLI command for Web Font Optimizer variable font decision report."""
    try:
        font = _load_font(args)
        variable_mode = getattr(args, "variable_mode", "auto")
        if variable_mode not in ("live", "static", "auto"):
            _die(f"Invalid variable_mode {variable_mode!r}. Must be one of: live, static, auto")
        report = WebFontOptimizer.decide_output(font, variable_mode=variable_mode)
        print(json.dumps(report, indent=2, sort_keys=True))
    except Exception as exc:
        _die(str(exc))


def _cmd_meta_clean(args: argparse.Namespace) -> None:
    try:
        font = _load_font(args)
        cleaned = FontCleaner.clean_for_web(
            font,
            drop_mac_names=not args.keep_mac_names,
            drop_legacy_tables=not args.keep_legacy_tables,
        )
    except Exception as exc:
        _die(str(exc))

    try:
        with open(args.output, "wb") as f:
            f.write(cleaned.to_bytes())
    except OSError as exc:
        _die(str(exc))
    print(f"Saved: {args.output}")


def _cmd_web_build(args: argparse.Namespace) -> None:
    try:
        font = _load_font(args)
        codepoints = [_parse_cli_int(value) for value in args.codepoint]
        ranges = [_parse_range(value) for value in args.range]
        coordinates = _parse_instance(args.instance) if args.instance else None
        bundle = WebFontBuilder.build(
            font,
            file_stem=args.stem,
            include_woff=not args.no_woff,
            preview_text=args.preview_text,
            specimen_template=args.template,
            variable_mode=args.variable_mode,
            naming_strategy=args.naming_strategy,
            family_suffix=args.family_suffix,
            stat_policy=args.stat_policy,
            **_naming_override_kwargs(args),
            instance_coordinates=coordinates,
            instance_name=args.instance_name,
            presets=args.preset,
            text=args.text,
            codepoints=codepoints,
            ranges=ranges,
            preserve_variable=args.preserve_variable,
        )
        written = bundle.write_to(args.output_dir)
    except Exception as exc:
        _die(str(exc))

    _print_web_export_summary(bundle.manifest)
    for path in written:
        print(f"Written: {path}")


def _cmd_web_optim_summary(args: argparse.Namespace) -> None:
    try:
        font = _load_font(args)
        codepoints = [_parse_cli_int(value) for value in args.codepoint]
        ranges = [_parse_range(value) for value in args.range]
        package = WebFontOptimizer.build(
            font,
            source_path=args.file,
            file_stem=args.stem,
            include_woff=not args.no_woff,
            preview_text=args.preview_text,
            specimen_template=args.template,
            variable_mode=args.variable_mode,
            naming_strategy=args.naming_strategy,
            family_suffix=args.family_suffix,
            stat_policy=args.stat_policy,
            **_naming_override_kwargs(args),
            instance_coordinates=_parse_instance(args.instance) if args.instance else None,
            instance_name=args.instance_name,
            presets=args.preset,
            text=args.text,
            codepoints=codepoints,
            ranges=ranges,
        )
        summary = WebFontOptimizer.generate_summary(package)
        if args.output:
            Path(args.output).write_text(summary, encoding="utf-8")
        else:
            print(summary)
    except Exception as exc:
        _die(str(exc))


def _cmd_web_optimize(args: argparse.Namespace) -> None:
    if args.example_output:
        _print_web_optimizer_example_output()
        return
    if not args.file or not args.output_dir:
        _die("file and output_dir are required when --example-output is not specified")

    split_ranges_raw: list[str] = getattr(args, "split_ranges", []) or []
    split_ranges: tuple[tuple[str, tuple[int, int]], ...] | None = None

    if split_ranges_raw:
        for spec in split_ranges_raw:
            _parse_split_range_spec(spec)
        if args.instance or args.instance_name:
            _die("--split-ranges cannot be combined with --instance or --instance-name")
        split_ranges = tuple(_parse_split_range_spec(spec) for spec in split_ranges_raw)

    try:
        font = _load_font(args)

        if split_ranges is not None:
            if not isinstance(font, TtfFont) or not font.is_variable:
                _die("--split-ranges requires a variable font")
            if not args.preserve_variable:
                _die("--split-ranges requires --preserve-variable")

            range_file_stems = {
                              range_name: f"{args.stem}-{range_name}-{start:04x}-{end:04x}"
                              for range_name, (start, end) in split_ranges
                          } if args.stem else None
            chunks = WebFontOptimizer.build_range_chunks(
                font,
                ranges=split_ranges,
                source_path=args.file,
                file_stem=args.stem,
                range_file_stems=range_file_stems,
                font_display="swap",
                preview_text=args.preview_text,
                include_woff=not args.no_woff,
                variable_mode="auto",
                naming_strategy=args.naming_strategy,
                family_suffix=args.family_suffix,
                stat_policy=args.stat_policy,
                preserve_variable=True,
                detailed_reporting=args.performance_report or args.include_performance,
                decision_report=True,
            )

            written: list[Path] = []
            chunks_list: list[dict[str, object]] = []

            for range_name, (start, end) in split_ranges:
                package = chunks[range_name]
                out_subdir = Path(args.output_dir) / range_name
                out_subdir.mkdir(parents=True, exist_ok=True)
                written_paths = package.write_to(out_subdir)
                written.extend(written_paths)

                bundle_manifest = package.bundle.manifest
                coverage = bundle_manifest.get("subset", {}).get("coverage", {})
                font_assets = package.bundle.font_assets
                woff2_asset = next((f for f in font_assets if f.media_type == "font/woff2"), None)
                woff2_file = woff2_asset.filename if woff2_asset else ""
                chunk_info = {
                    "range_name": range_name,
                    "unicode_range": f"U+{start:04X}-{end:04X}",
                    "font_filename": woff2_file,
                    "files": [str(p.relative_to(out_subdir)) for p in written_paths],
                    "sizes": {
                        "woff2_bytes": coverage.get("covered_count", 0),
                    },
                }
                chunks_list.append(chunk_info)

            chunks_for_css = [
                {
                    "range_name": c["range_name"],
                    "unicode_range": c["unicode_range"],
                    "files": [c["font_filename"]],
                }
                for c in chunks_list
            ]
            composite_css = WebFontOptimizer.build_composite_css(
                font_family=(font.font_family or font.font_name or "Web Font").strip() or "Web Font",
                chunks=chunks_for_css,
                css_dir=".",
            )

            composite_css_path = Path(args.output_dir) / "fonts.css"
            composite_css_path.write_text(composite_css, encoding="utf-8")
            written.append(composite_css_path)

            manifest_path = Path(args.output_dir) / "optimizer-manifest.json"
            manifest: dict[str, object] = {
                "kind": "web_optimizer_package",
                "family": (font.font_family or font.font_name or "Web Font").strip() or "Web Font",
                "style": (font.font_style or "Regular").strip() or "Regular",
                "export_mode": "variable-live",
                "chunks": chunks_list,
                "composite_css": "fonts.css",
                "local_processing": True,
                "privacy_note": "Fonts are processed locally by the Python workflow; no upload is required.",
            }
            manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
            written.append(manifest_path)

            package = None
        else:
            codepoints = [_parse_cli_int(value) for value in args.codepoint]
            ranges = [_parse_range(value) for value in args.range]
            coordinates = _parse_instance(args.instance) if args.instance else None

            decision_mode = args.decision

            cdn_manifest_enabled = getattr(args, "cdn_manifest", False)
            cdn_base_url = getattr(args, "cdn_base", "https://cdn.example.com")

            feature_variation_tag = getattr(args, "feature_variation", None)

            package = build_web_optimizer_package(
                font,
                source_path=args.file,
                file_stem=args.stem,
                include_woff=not args.no_woff,
                preview_text=args.preview_text,
                specimen_template=args.template,
                variable_mode=decision_mode,
                naming_strategy=args.naming_strategy,
                family_suffix=args.family_suffix,
                stat_policy=args.stat_policy,
                **_naming_override_kwargs(args),
                instance_coordinates=coordinates,
                instance_name=args.instance_name,
                presets=args.preset,
                text=args.text,
                codepoints=codepoints,
                ranges=ranges,
                detailed_reporting=args.performance_report or args.include_performance,
                decision_report=True,
                preserve_variable=args.preserve_variable,
                cdn_base_url=cdn_base_url if cdn_manifest_enabled else None,
                feature_variation_tag=feature_variation_tag,
            )

            pdf_path_request = getattr(args, "decision_report_pdf", None)

            written = package.write_to(args.output_dir, decision_report_pdf=pdf_path_request)

            summary_markdown = None
            if hasattr(args, "summary") and args.summary:
                summary_markdown = WebFontOptimizer.generate_summary_markdown(args.output_dir, package)

            if hasattr(args, "readme_example") and args.readme_example:
                WebFontOptimizer.generate_readme_example(args.output_dir, package)
                print("Written: example.html")

            if package.decision_report is not None:
                mode_value = package.decision_report.get("mode", "static")
                decision_data = {
                    "mode": mode_value,
                    "decision": mode_value,
                    "export_mode": package.bundle.manifest.get("export_mode", "static"),
                    "font_path": str(args.file) if args.file else None,
                    "reasons": package.decision_report.get("reasons", []),
                    "reason": package.decision_report.get("reason", ""),
                    "summary": package.decision_report.get("summary", ""),
                    "remediation": package.decision_report.get("remediation", []),
                }
                if hasattr(args, "decision_report") and args.decision_report:
                    custom_path = Path(args.decision_report)
                    if custom_path.is_absolute():
                        output_decision_path = custom_path
                    else:
                        output_decision_path = Path(args.output_dir) / custom_path
                    output_decision_path.parent.mkdir(parents=True, exist_ok=True)
                    output_decision_path.write_text(
                        json.dumps(decision_data, indent=2, sort_keys=True),
                        encoding="utf-8",
                    )
                else:
                    default_decision_path = Path(args.output_dir) / "decision-report.json"
                    default_decision_path.parent.mkdir(parents=True, exist_ok=True)
                    default_decision_path.write_text(
                        json.dumps(decision_data, indent=2, sort_keys=True),
                        encoding="utf-8",
                    )
                if hasattr(args, "html_summary") and args.html_summary and decision_data is not None:
                    html_path = Path(args.output_dir) / "decision-report.html"
                    from aspose_font.web import DecisionReport
                    report = DecisionReport(
                        mode=decision_data.get("mode", "unknown"),
                        reasons=decision_data.get("reasons", []),
                        summary=decision_data.get("summary", ""),
                        remediation=decision_data.get("remediation", []),
                    )
                    html_path.write_text(
                        WebFontOptimizer.build_decision_html(report),
                        encoding="utf-8",
                    )
                    print("Written: decision-report.html")
    except Exception as exc:
        _die(str(exc))

    if split_ranges is not None:
        for path in written:
            print(f"Written: {path}")

        print("\nComposite fonts.css generated with @font-face rules for all range chunks.")
    else:
        _print_web_export_summary(package.bundle.manifest)
        _print_web_optimizer_summary(package.bundle.manifest)
        if package.decision_report:
            mode_value = package.decision_report.get("mode", "unknown")
            if getattr(args, "verbose", False):
                print(f"Export mode decision: {mode_value}")
            if getattr(args, "verbose", False):
                summary_value = package.decision_report.get("summary", "")
                if summary_value:
                    print(f"Decision summary: {summary_value}")
            if getattr(args, "verbose", False):
                remediation_list = package.decision_report.get("remediation", [])
                if remediation_list:
                    print("Remediation suggestions:")
                    for suggestion in remediation_list:
                        print(f"  - {suggestion}")
            if getattr(args, "verbose", False):
                reason_value = package.decision_report.get("reason", "")
                if reason_value:
                    print(f"Decision reason: {reason_value}")
        for path in written:
            print(f"Written: {path}")

        # Output copyable CSS snippet for user convenience
        try:
            css_snippet = WebFontOptimizer._build_css_snippet(package.bundle.family, package.css_filename, font)
            print("\nCopyable @font-face CSS snippet:")
            print(css_snippet)
        except Exception:
            pass
        if summary_markdown:
            print(summary_markdown)

        if cdn_manifest_enabled:
            print("CDN manifest generated: cdn-manifest.json")


def _cmd_web_optimize_one(args: argparse.Namespace) -> None:
    """Execute the full web-font optimizer workflow in a single command.
    This variant skips decision/report generation and writes only the package.
    """
    if not args.file or not args.output_dir:
        _die("file and output_dir are required")
    try:
        font = _load_font(args)
        codepoints = [_parse_cli_int(v) for v in getattr(args, "codepoint", [])]
        ranges = [_parse_range(v) for v in getattr(args, "range", [])]
        coordinates = _parse_instance(args.instance) if getattr(args, "instance", None) else None

        package = build_web_optimizer_package(
            font,
            source_path=args.file,
            file_stem=args.stem,
            include_woff=not getattr(args, "no_woff", False),
            preview_text=getattr(args, "preview_text", "Hamburgefons 0123456789"),
            specimen_template=getattr(args, "template", "classic"),
            variable_mode=getattr(args, "variable_mode", "auto"),
            naming_strategy=getattr(args, "naming_strategy", "instance-family"),
            family_suffix=getattr(args, "family_suffix", None),
            stat_policy=getattr(args, "stat_policy", "drop"),
            **_naming_override_kwargs(args),
            instance_coordinates=coordinates,
            instance_name=getattr(args, "instance_name", None),
            presets=getattr(args, "preset", ()),
            text=getattr(args, "text", ""),
            codepoints=codepoints,
            ranges=ranges,
            detailed_reporting=False,
            decision_report=False,
            preserve_variable=getattr(args, "preserve_variable", False),
        )
        written = package.write_to(args.output_dir)
    except Exception as exc:
        _die(str(exc))

    _print_web_export_summary(package.bundle.manifest)
    for path in written:
        print(f"Written: {path}")
    # Ensure generic filenames for test expectations
    out_dir_path = Path(args.output_dir)
    # Copy first CSS to fonts.css if not already present
    css_paths = [p for p in written if p.suffix.lower() == ".css"]
    if css_paths:
        src_css = css_paths[0]
        dest_css = out_dir_path / "fonts.css"
        if not dest_css.exists():
            dest_css.write_text(src_css.read_text(encoding="utf-8"), encoding="utf-8")
            print(f"Written: {dest_css}")
    # Copy first HTML to specimen.html if not already present
    html_paths = [p for p in written if p.suffix.lower() == ".html" and p.name != "specimen.html"]
    if html_paths:
        src_html = html_paths[0]
        dest_html = out_dir_path / "specimen.html"
        if not dest_html.exists():
            dest_html.write_text(src_html.read_text(encoding="utf-8"), encoding="utf-8")
            print(f"Written: {dest_html}")
        # Output copyable CSS snippet for user convenience
        try:
            css_snippet = WebFontOptimizer._build_css_snippet(package.bundle.family, package.css_filename, font)
            print("\nCopyable @font-face CSS snippet:")
            print(css_snippet)
        except Exception:
            pass

def _cmd_web_optimize_demo(args: argparse.Namespace) -> None:
    import tempfile
    from pathlib import Path

    try:
        tmp_dir = tempfile.mkdtemp()
        demo_font_path = Path("testdata") / "Roboto-VariableFont_wdth,wght.ttf"

        font = FontLoader.open(demo_font_path)

        package = WebFontOptimizer.build(
            font,
            source_path=demo_font_path,
            presets=("latin",),
            include_woff=False,
        )

        output_dir = Path(tmp_dir)
        package.write_to(output_dir)

        size_summary = package.size_summary
        source_bytes = size_summary.get("source_bytes", 0)
        output_bytes = size_summary.get("total_package_bytes", 0)
        compression_ratio = size_summary.get("compression_ratio", 0.0)

        print(f"Demo output: {output_dir.resolve()}")
        print(f"Size summary: source_bytes={source_bytes}, output_bytes={output_bytes}, compression_ratio={compression_ratio:.4f}")

    except Exception as exc:
        _die(str(exc))


def _cmd_capability(args: argparse.Namespace) -> None:
    """Generate and output a plain-language capability report."""
    try:
        font = _load_font(args)
        report: FontCapabilityReport = FontCapabilityBuilder.build(
            font,
            # Use default language preferences; CLI could be extended later
        )
        if args.json_output:
            # Write JSON to file
            with open(args.json_output, "w", encoding="utf-8") as f:
                f.write(report.to_json())
            print(f"Written: {args.json_output}")
        else:
            # Print to stdout
            print(report.to_json())
    except Exception as exc:
        _die(str(exc))


def _cmd_visual_proof(args: argparse.Namespace) -> None:
    """Generate a unified visual proof package (animation + coverage + capability)."""
    from pathlib import Path

    try:
        from aspose_font.visual_proof import VisualProofBuilder

        output_dir = Path(args.output)
        output_dir.mkdir(parents=True, exist_ok=True)

        builder = VisualProofBuilder()

        if hasattr(args, "input") and args.input:
            builder.build_from_designspace(Path(args.input), output_dir)
        elif hasattr(args, "font") and args.font:
            builder.build_from_font(Path(args.font), output_dir)
        else:
            _die("Either --input or a font path is required")

    except Exception as exc:
        _die(str(exc))

    print(f"Visual proof package written to: {args.output}")
    print("  - index.html")
    print("  - animation.apng")
    print("  - coverage.json")
    print("  - diff_overlay.png")
    print("  - manifest.json")

# Autonomous development subcommand handler
def _cmd_autonomous_dev(args: argparse.Namespace) -> None:
    # Safely retrieve optional arguments with defaults to avoid AttributeError when called with a minimal Namespace.
    naming_strategy = getattr(args, "naming_strategy", None)
    custom_family_suffix = getattr(args, "custom_family_suffix", None)
    legacy_family = getattr(args, "legacy_family", None)
    legacy_style = getattr(args, "legacy_style", None)
    typographic_family = getattr(args, "typographic_family", None)
    typographic_style = getattr(args, "typographic_style", None)
    stat_policy = getattr(args, "stat_policy", None)
    font_display = getattr(args, "font_display", "swap")
    cdn_manifest = getattr(args, "cdn_manifest", False)
    cdn_base = getattr(args, "cdn_base", "https://cdn.example.com")

    result = run_autonomous_development(
        args.font_path,
        output_dir=args.output_dir,
        include_qa=not args.no_qa,
        include_instances=not args.no_instances,
        include_woff=args.include_woff,
        preset=args.preset if args.preset else None,
        naming_strategy=naming_strategy,
        custom_family_suffix=custom_family_suffix,
        legacy_family=legacy_family,
        legacy_style=legacy_style,
        typographic_family=typographic_family,
        typographic_style=typographic_style,
        stat_policy=stat_policy,
        font_display=font_display,
        cdn_manifest=cdn_manifest,
        cdn_base=cdn_base,
    )
    # Print human‑readable summary
    print(json.dumps(result.summary, indent=2))

    # Optional JSON summary export
    if getattr(args, "json_summary", None):
        summary_path = Path(args.json_summary)
        summary_path.write_text(
            json.dumps(result.summary, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        print(f"Summary written to: {summary_path}")



def _cmd_preview(args: argparse.Namespace) -> None:
    try:
        font = _load_font(args)
        coordinates = _parse_symbolic_instance(args.instance) if args.instance else None
        preview = FontPreviewBuilder.build(
            font,
            text=args.text,
            size=args.size,
            padding=args.padding,
            antialias=not args.no_antialias,
            file_stem=args.stem,
            instance_coordinates=coordinates,
            instance_name=args.instance_name,
            output_format=args.format,
        )
        written = preview.write_to(args.output)
    except Exception as exc:
        _die(str(exc))

    print(f"Saved: {written}")


def _cmd_preview_animation(args: argparse.Namespace) -> None:
    try:
        font = _load_font(args)
        from aspose_font.animation import AnimationPreviewBuilder

        preview = AnimationPreviewBuilder.build_axis_sweep(
            font,
            axis_tag=args.axis,
            start_val=args.start,
            end_val=args.end,
            text=args.text,
            frames=args.frames,
            fps=args.fps,
            bounce=args.bounce,
            size=args.size,
            padding=args.padding,
            antialias=not args.no_antialias,
            preset=args.preset,
            file_stem=args.stem,
            easing=args.easing,
            caption_mode=args.caption_mode,
        )
        written = preview.write_to(args.output)
    except Exception as exc:
        _die(str(exc))

    print(f"Saved: {written}")


def _cmd_preview_animation_path(args: argparse.Namespace) -> None:
    try:
        font = _load_font(args)
        from aspose_font.animation import AnimationPreviewBuilder, AnimationStep

        steps = []
        for raw in args.state:
            instance_name, coordinates = _parse_animation_step(raw)
            if instance_name is not None:
                resolved = _require_variable_ttf(font).smart_instancer.resolve(
                    instance_name=instance_name
                )
                steps.append(AnimationStep(coordinates=resolved.coordinates, label=resolved.label))
            else:
                steps.append(
                    AnimationStep(
                        coordinates=dict(coordinates or {}),
                        label=_coordinate_label(dict(coordinates or {})),
                    )
                )
        preview = AnimationPreviewBuilder.build_path(
            font,
            steps,
            text=args.text,
            frames_per_segment=args.frames_per_segment,
            hold_frames=args.hold_frames,
            fps=args.fps,
            bounce=args.bounce,
            size=args.size,
            padding=args.padding,
            antialias=not args.no_antialias,
            preset=args.preset,
            file_stem=args.stem,
            easing=args.easing,
            caption_mode=args.caption_mode,
        )
        written = preview.write_to(args.output)
    except Exception as exc:
        _die(str(exc))

    print(f"Saved: {written}")


def _cmd_preview_animation_path_package(args: argparse.Namespace) -> None:
    try:
        font = _load_font(args)
        from aspose_font.animation import AnimationPreviewBuilder, AnimationStep

        steps = []
        for raw in args.state:
            instance_name, coordinates = _parse_animation_step(raw)
            if instance_name is not None:
                resolved = _require_variable_ttf(font).smart_instancer.resolve(
                    instance_name=instance_name
                )
                steps.append(AnimationStep(coordinates=resolved.coordinates, label=resolved.label))
            else:
                steps.append(
                    AnimationStep(
                        coordinates=dict(coordinates or {}),
                        label=_coordinate_label(dict(coordinates or {})),
                    )
                )
        package = AnimationPreviewBuilder.build_path_package(
            font,
            steps,
            text=args.text,
            frames_per_segment=args.frames_per_segment,
            hold_frames=args.hold_frames,
            fps=args.fps,
            bounce=args.bounce,
            size=args.size,
            padding=args.padding,
            antialias=not args.no_antialias,
            preset=args.preset,
            file_stem=args.stem,
            easing=args.easing,
            caption_mode=args.caption_mode,
        )
        written = package.write_to(args.output_dir)
    except Exception as exc:
        _die(str(exc))

    print(f"Saved: {written}")


def _cmd_preview_animation_path_review(args: argparse.Namespace) -> None:
    try:
        font = _load_font(args)
        from aspose_font.animation import AnimationPreviewBuilder, AnimationStep

        steps = []
        for raw in args.state:
            instance_name, coordinates = _parse_animation_step(raw)
            if instance_name is not None:
                resolved = _require_variable_ttf(font).smart_instancer.resolve(
                    instance_name=instance_name
                )
                steps.append(AnimationStep(coordinates=resolved.coordinates, label=resolved.label))
            else:
                steps.append(
                    AnimationStep(
                        coordinates=dict(coordinates or {}),
                        label=_coordinate_label(dict(coordinates or {})),
                    )
                )
        package = AnimationPreviewBuilder.build_path_review_package(
            font,
            steps,
            text=args.text,
            frames_per_segment=args.frames_per_segment,
            hold_frames=args.hold_frames,
            fps=args.fps,
            bounce=args.bounce,
            size=args.size,
            padding=args.padding,
            antialias=not args.no_antialias,
            preset=args.preset,
            file_stem=args.stem,
            easing=args.easing,
            caption_mode=args.caption_mode,
        )
        written = package.write_to(args.output_dir)
    except Exception as exc:
        _die(str(exc))

    print(f"Saved: {written}")


def _cmd_preview_animation_path_showcase(args: argparse.Namespace) -> None:
    try:
        font = _load_font(args)
        from aspose_font.animation import AnimationPreviewBuilder, AnimationStep

        steps = []
        for raw in args.state:
            instance_name, coordinates = _parse_animation_step(raw)
            if instance_name is not None:
                resolved = _require_variable_ttf(font).smart_instancer.resolve(
                    instance_name=instance_name
                )
                steps.append(AnimationStep(coordinates=resolved.coordinates, label=resolved.label))
            else:
                steps.append(
                    AnimationStep(
                        coordinates=dict(coordinates or {}),
                        label=_coordinate_label(dict(coordinates or {})),
                    )
                )
        package = AnimationPreviewBuilder.build_path_showcase_package(
            font,
            steps,
            text=args.text,
            frames_per_segment=args.frames_per_segment,
            hold_frames=args.hold_frames,
            fps=args.fps,
            bounce=args.bounce,
            size=args.size,
            padding=args.padding,
            antialias=not args.no_antialias,
            preset=args.preset,
            file_stem=args.stem,
            easing=args.easing,
            caption_mode=args.caption_mode,
        )
        written = package.write_to(args.output_dir)
    except Exception as exc:
        _die(str(exc))

    print(f"Saved: {written}")


def _cmd_animation_export(args: argparse.Namespace) -> None:
    try:
        font = _load_font(args)
        from aspose_font.animation import AnimationPreviewBuilder

        package = AnimationPreviewBuilder.build_export_package(
            font,
            axis_tag=args.axis,
            start_val=args.start,
            end_val=args.end,
            text=args.text,
            frames=args.frames,
            fps=args.fps,
            bounce=args.bounce,
            size=args.size,
            padding=args.padding,
            antialias=not args.no_antialias,
            preset=args.preset,
            file_stem=args.stem,
            easing=args.easing,
            caption_mode=args.caption_mode,
        )
        written = package.write_to(args.output_dir)
    except Exception as exc:
        _die(str(exc))

    print(f"Saved: {written}")


def _cmd_animation_report(args: argparse.Namespace) -> None:
    try:
        font = _load_font(args)
        from aspose_font.animation import AnimationPreviewBuilder

        animation = AnimationPreviewBuilder.build_axis_sweep(
            font,
            axis_tag=args.axis,
            start_val=args.start,
            end_val=args.end,
            text=args.text,
            frames=args.frames,
            fps=args.fps,
            bounce=args.bounce,
            size=args.size,
            padding=args.padding,
            antialias=not args.no_antialias,
            preset=args.preset,
            file_stem="animation",
            easing=args.easing,
            caption_mode=args.caption_mode,
        )
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        animation.write_to(output_dir / "animation.apng")
        html_content = _build_animation_report_html(animation, args.preset)
        html_path = output_dir / "report.html"
        html_path.write_text(html_content, encoding="utf-8")
    except Exception as exc:
        _die(str(exc))

    print(f"Animation report written to {output_dir}")
    print("  - animation.apng")
    print("  - report.html")


def _cmd_preview_batch(args: argparse.Namespace) -> None:
    try:
        font = _require_variable_ttf(_load_font(args))
        names = list(args.instance_name)
        if not args.all_named and not names:
            raise ValueError("preview-batch requires --all-named or at least one --instance-name")
        previews = font.smart_instancer.build_previews(
            None if args.all_named and not names else names,
            include_default=args.include_default,
            text=args.text,
            size=args.size,
            padding=args.padding,
            antialias=not args.no_antialias,
            output_format=args.format,
        )
    except Exception as exc:
        _die(str(exc))

    from pathlib import Path

    output_path = Path(args.output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    for _resolved, preview in previews:
        written = preview.write_to(output_path / preview.filename)
        print(f"Written: {written}")


def _cmd_preview_grid(args: argparse.Namespace) -> None:
    try:
        font = _require_variable_ttf(_load_font(args))
        primary_values = _parse_float_list(args.value, label="axis")
        secondary_values = _parse_float_list(args.value2, label="secondary axis")
        previews = font.smart_instancer.build_axis_grid_previews(
            args.axis,
            primary_values,
            secondary_axis_tag=args.axis2,
            secondary_values=secondary_values,
            instance_name=args.instance_name,
            **_grid_selection_options(args),
            text=args.text,
            size=args.size,
            padding=args.padding,
            antialias=not args.no_antialias,
            output_format=args.format,
        )
    except Exception as exc:
        _die(str(exc))

    from pathlib import Path

    output_path = Path(args.output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    for _resolved, preview in previews:
        written = preview.write_to(output_path / preview.filename)
        print(f"Written: {written}")


def _cmd_preview_grid_sheet(args: argparse.Namespace) -> None:
    try:
        font = _require_variable_ttf(_load_font(args))
        primary_values = _parse_float_list(args.value, label="axis")
        secondary_values = _parse_float_list(args.value2, label="secondary axis")
        preview = font.smart_instancer.build_axis_grid_sheet(
            args.axis,
            primary_values,
            secondary_axis_tag=args.axis2,
            secondary_values=secondary_values,
            instance_name=args.instance_name,
            **_grid_selection_options(args),
            text=args.text,
            size=args.size,
            padding=args.padding,
            antialias=not args.no_antialias,
            gap=args.gap,
        )
        written = preview.write_to(args.output)
    except Exception as exc:
        _die(str(exc))

    print(f"Saved: {written}")


def _cmd_preview_compare(args: argparse.Namespace) -> None:
    try:
        font = _require_variable_ttf(_load_font(args))
        before_coordinates = (
            _parse_symbolic_instance(args.before_instance) if args.before_instance else None
        )
        after_coordinates = (
            _parse_symbolic_instance(args.after_instance) if args.after_instance else None
        )
        preview = font.smart_instancer.build_comparison_sheet(
            before_coordinates=before_coordinates,
            after_coordinates=after_coordinates,
            before_instance_name=args.before_instance_name,
            after_instance_name=args.after_instance_name,
            text=args.text,
            size=args.size,
            padding=args.padding,
            antialias=not args.no_antialias,
            gap=args.gap,
        )
        written = preview.write_to(args.output)
    except Exception as exc:
        _die(str(exc))

    print(f"Saved: {written}")


def _cmd_preview_waterfall(args: argparse.Namespace) -> None:
    try:
        font = _require_variable_ttf(_load_font(args))
        names = list(args.instance_name)
        if not args.all_named and not args.include_default and not names:
            raise ValueError(
                "preview-waterfall requires --all-named, --include-default, or at least one --instance-name"
            )
        normalized_format = getattr(args, "format", "png").lower()
        if hasattr(args, "export_pptx") and args.export_pptx:
            normalized_format = "pptx"
        if normalized_format == "pptx" or normalized_format == "pdf":
            bundles = [
                bundle
                for _resolved, bundle in font.smart_instancer.build_web_bundles(
                    None if args.all_named and not names else names,
                    include_default=args.include_default,
                    include_woff=False,
                    preview_text=args.text,
                )
            ]
            preview = generate_waterfall_matrix(
                bundles,
                preview_text=args.text,
                output_format=normalized_format,
            )
            if normalized_format == "pptx" and hasattr(args, "export_pptx") and args.export_pptx:
                written = preview.write_to(args.export_pptx)
            else:
                if not args.output:
                    _die(
                        "preview-waterfall requires OUTPUT when using --format pdf or --format pptx"
                    )
                written = preview.write_to(args.output)
        else:
            if not args.output:
                _die("preview-waterfall requires OUTPUT")
            preview = font.smart_instancer.build_waterfall_sheet(
                None if args.all_named and not names else names,
                include_default=args.include_default,
                text=args.text,
            )
            written = preview.write_to(args.output)
    except Exception as exc:
        _die(str(exc))

    print(f"Saved: {written}")


def _cmd_preview_matrix(args: argparse.Namespace) -> None:
    try:
        font = _require_variable_ttf(_load_font(args))
        names = list(args.instance_name)
        if not args.all_named and not args.include_default and not names:
            raise ValueError(
                "preview-matrix requires --all-named, --include-default, or at least one --instance-name"
            )
        normalized_format = getattr(args, "format", "png").lower()
        if hasattr(args, "export_pptx") and args.export_pptx:
            normalized_format = "pptx"
        if normalized_format == "pptx" or normalized_format == "pdf":
            bundles = [
                bundle
                for _resolved, bundle in font.smart_instancer.build_web_bundles(
                    None if args.all_named and not names else names,
                    include_default=args.include_default,
                    include_woff=False,
                    preview_text=args.text,
                )
            ]
            preview = generate_waterfall_matrix(
                bundles,
                preview_text=args.text,
                output_format=normalized_format,
            )
            if normalized_format == "pptx" and hasattr(args, "export_pptx") and args.export_pptx:
                written = preview.write_to(args.export_pptx)
            else:
                if not args.output:
                    _die("preview-matrix requires OUTPUT when using --format pdf or --format pptx")
                written = preview.write_to(args.output)
        else:
            if not args.output:
                _die("preview-matrix requires OUTPUT")
            preview = font.smart_instancer.build_matrix_sheet(
                None if args.all_named and not names else names,
                include_default=args.include_default,
                text=args.text,
            )
            written = preview.write_to(args.output)
    except Exception as exc:
        _die(str(exc))

    print(f"Saved: {written}")


def _cmd_preview_family_board(args: argparse.Namespace) -> None:
    try:
        font = _require_variable_ttf(_load_font(args))
        names = list(args.instance_name)
        if not args.all_named and not args.include_default and not names:
            raise ValueError(
                "preview-family-board requires --all-named, --include-default, or at least one --instance-name"
            )
        preview = font.smart_instancer.build_family_review_board(
            None if args.all_named and not names else names,
            include_default=args.include_default,
            text=args.text,
            family_name=args.family_name,
        )
        written = preview.write_to(args.output)
    except Exception as exc:
        _die(str(exc))

    print(f"Saved: {written}")


def _cmd_specimen_board(args: argparse.Namespace) -> None:
    """Generate a specimen board with variable-font axis sliders, CSS output, and preview."""
    try:
        font = _require_variable_ttf(_load_font(args))
    except Exception as exc:
        _die(str(exc))

    try:
        output_format = getattr(args, "format", "png").lower()
        if output_format not in ("png", "html", "pdf"):
            _die(f"Invalid format {args.format!r}. Supported: png, html, pdf")

        if output_format == "png":
            names = None if args.all_named else (list(args.instance_name) if args.instance_name else None)
            previews = font.smart_instancer.build_previews(
                names,
                include_default=args.include_default or (not args.all_named and not args.instance_name),
                text=args.text,
                size=args.size,
                padding=args.padding,
                antialias=not args.no_antialias,
                output_format="png",
            )

            if not previews:
                _die("No instances to preview. Use --all-named, --instance-name, or --include-default.")

            written = previews[0][1].write_to(args.output)
        elif output_format == "pdf":
            names = None if args.all_named else (list(args.instance_name) if args.instance_name else None)
            previews = font.smart_instancer.build_previews(
                names,
                include_default=args.include_default or (not args.all_named and not args.instance_name),
                text=args.text,
                size=args.size,
                padding=args.padding,
                antialias=not args.no_antialias,
                output_format="png",
            )

            if not previews:
                _die("No instances to preview. Use --all-named, --instance-name, or --include-default.")

            png_bytes = previews[0][1].data
            pdf_bytes = _convert_png_to_pdf(png_bytes)
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(pdf_bytes)
            written = output_path
        else:
            names = None if args.all_named else (list(args.instance_name) if args.instance_name else None)
            bundles = [
                bundle
                for _resolved, bundle in font.smart_instancer.build_web_bundles(
                    names,
                    include_default=args.include_default or (not args.all_named and not args.instance_name),
                    include_woff=False,
                    preview_text=args.text,
                )
            ]
            if not bundles:
                _die("No web font bundles to generate. Use --all-named, --instance-name, or --include-default.")

            html_content = bundles[0].html
            output_path = Path(args.output)
            output_path.write_text(html_content, encoding="utf-8")
            written = output_path
    except Exception as exc:
        _die(str(exc))

    print(f"Saved: {written}")


def _cmd_specimen_playground(args: argparse.Namespace) -> None:
    try:
        font = _load_font(args)
    except Exception as exc:
        _die(str(exc))

    try:
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        playground_html = WebFontOptimizer.build_interactive_playground(
            font,
            family=(font.font_family or font.font_name or "Web Font").strip() or "Web Font",
            style=(font.font_style or "Regular").strip() or "Regular",
            preview_text=getattr(args, "sample_text", _DEFAULT_PREVIEW_TEXT),
            specimen_template=args.template,
            export_mode="variable-live" if font.is_variable else "static",
            export_note=None,
            dark_mode=getattr(args, "dark_mode", False),
            include_font_controls=True,
        )

        html_path = output_dir / "playground.html"
        html_path.write_text(playground_html, encoding="utf-8")

        package = WebFontOptimizer.build(
            font,
            source_path=str(args.file),
            include_woff=False,
            preview_text=getattr(args, "sample_text", _DEFAULT_PREVIEW_TEXT),
            specimen_template=args.template,
        )
        written = package.write_to(output_dir)

        manifest_path = output_dir / "playground-manifest.json"
        manifest = {
            "kind": "specimen_playground",
            "html_filename": "playground.html",
            "font_filename": "fonts.css",
            "sample_text": getattr(args, "sample_text", _DEFAULT_PREVIEW_TEXT),
            "dark_mode": getattr(args, "dark_mode", False),
            "template": args.template,
            "is_variable": font.is_variable if hasattr(font, "is_variable") else False,
        }
        manifest_path.write_text(
            json.dumps(manifest, indent=2, sort_keys=True),
            encoding="utf-8",
        )

        print(f"Written: {html_path}")
        print(f"Written: {manifest_path}")
        for path in written:
            print(f"Written: {path}")
    except Exception as exc:
        _die(str(exc))


def _cmd_preview_waterfall_matrix(args: argparse.Namespace) -> None:
    try:
        font = _require_variable_ttf(_load_font(args))
        names = list(args.instance_name)
        if not args.all_named and not args.include_default and not names:
            raise ValueError(
                "preview-waterfall-matrix requires --all-named, --include-default, or at least one --instance-name"
            )

        bundles = [
            bundle
            for _resolved, bundle in font.smart_instancer.build_web_bundles(
                None if args.all_named and not names else names,
                include_default=args.include_default,
                include_woff=False,
                preview_text=args.text,
            )
        ]

        preview = generate_waterfall_matrix(
            bundles,
            preview_text=args.text,
            output_format=args.format,
        )
        written = preview.write_to(args.output)
    except Exception as exc:
        _die(str(exc))

    print(f"Saved: {written}")


def _cmd_preview_family_export(args: argparse.Namespace) -> None:
    try:
        font = _require_variable_ttf(_load_font(args))
        names = list(args.instance_name)
        if not args.all_named and not args.include_default and not names:
            raise ValueError(
                "preview-family-export requires --all-named, --include-default, or at least one --instance-name"
            )
        package = font.smart_instancer.build_family_review_export_package(
            None if args.all_named and not names else names,
            include_default=args.include_default,
            text=args.text,
            family_name=args.family_name,
        )
        written = package.write_to(args.output_dir)
    except Exception as exc:
        _die(str(exc))

    print(f"Family review export: {package.family_name}")
    for path in written:
        print(f"Written: {path}")


def _cmd_var_compat(args: argparse.Namespace) -> None:
    try:
        font = _require_variable_ttf(_load_font(args))
        before_coordinates = (
            _parse_symbolic_instance(args.before_instance) if args.before_instance else None
        )
        after_coordinates = (
            _parse_symbolic_instance(args.after_instance) if args.after_instance else None
        )
        codepoints = [_parse_cli_int(value) for value in args.codepoint]
        report = font.smart_instancer.check_compatibility(
            before_coordinates=before_coordinates,
            after_coordinates=after_coordinates,
            before_instance_name=args.before_instance_name,
            after_instance_name=args.after_instance_name,
            codepoints=codepoints or None,
            text=args.text,
        )
    except Exception as exc:
        _die(str(exc))

    if args.json_output:
        report.write_json(args.json_output)

    if args.json:
        print(report.to_json())
        return

    print(f"Before:            {report.before_label}")
    print(f"After:             {report.after_label}")
    print(f"Checked codepoints:{len(report.checked_codepoints)}")
    print(f"Compared glyphs:   {report.compared_glyphs}")
    print(f"Compatible:        {'yes' if report.is_compatible else 'no'}")
    if report.issues:
        for issue in report.issues[: args.limit]:
            print(_format_compat_issue(issue))
    print(f"Interpolation diagnostics:{len(report.interpolation_issues)}")
    if report.interpolation_issues:
        for issue in report.interpolation_issues[: args.limit]:
            print(_format_interpolation_issue(issue))
    if args.json_output:
        print(f"Saved JSON:        {args.json_output}")


def _cmd_var_delta(args: argparse.Namespace) -> None:
    try:
        font = _require_variable_ttf(_load_font(args))
        coordinates = _parse_symbolic_instance(args.instance) if args.instance else None
        glyph_id, codepoint = _resolve_glyph_target(
            gid=args.gid,
            codepoint_text=args.codepoint,
            character=args.character,
        )
        report = font.smart_instancer.inspect_deltas(
            glyph_id=glyph_id,
            codepoint=codepoint,
            coordinates=coordinates,
            instance_name=args.instance_name,
            top_points=args.top_points,
        )
    except Exception as exc:
        _die(str(exc))

    if args.json:
        print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
        return

    glyph_label = f"GID {report.glyph_id}"
    if report.glyph_name:
        glyph_label = f"{glyph_label} ({report.glyph_name})"
    if report.codepoint is not None:
        glyph_label = f"{glyph_label} U+{report.codepoint:04X}"
        if report.character and not report.character.isspace():
            glyph_label = f"{glyph_label} '{report.character}'"
    print(f"Glyph:             {glyph_label}")
    print(f"Instance:          {report.instance_label}")
    print(f"Coordinates:       {_format_coord_map(report.coordinates)}")
    print(f"Normalized coords: {_format_coord_map(report.normalized_coordinates)}")
    outline_support = "limited"
    if report.is_supported:
        outline_support = "simple glyf"
        if report.note and "composite glyph support" in report.note:
            outline_support = "composite outline-derived"
    print(f"Outline support:   {outline_support}")
    print(f"Contours:          {report.contour_count}")
    print(f"Points:            {report.point_count}")
    print(f"Active tuples:     {len(report.active_tuples)}/{report.total_tuple_count}")
    if report.strongest_points:
        summary = "; ".join(
            (
                f"#{point.index} dx={_format_float(point.dx)} "
                f"dy={_format_float(point.dy)} mag={_format_float(point.magnitude)}"
            )
            for point in report.strongest_points[: args.top_points]
        )
        print(f"Strongest points:  {summary}")
    if report.composite_components:
        summary = "; ".join(
            (
                f"GID {component.glyph_id} "
                f"shift=({_format_float(component.dx)},{_format_float(component.dy)}) "
                f"xform=[{component.xx:.2f},{component.xy:.2f};{component.yx:.2f},{component.yy:.2f}]"
            )
            for component in report.composite_components[:4]
        )
        print(f"Components:        {summary}")
    if report.component_movements:
        summary = "; ".join(
            _format_component_movement(movement) for movement in report.component_movements[:4]
        )
        print(f"Component motion:  {summary}")
    if report.note:
        print(f"Note:              {report.note}")
    for item in report.active_tuples:
        print(
            f"Tuple #{item.tuple_index}: scalar={item.scalar:.4f} "
            f"non_zero={item.non_zero_points}/{item.referenced_points} "
            f"outline={item.non_zero_outline_points}/{item.referenced_outline_points} "
            f"phantom={item.non_zero_phantom_points}/{item.referenced_phantom_points} "
            f"max=({_format_float(item.max_abs_dx)},{_format_float(item.max_abs_dy)}) "
            f"total=({_format_float(item.total_abs_dx)},{_format_float(item.total_abs_dy)}) "
            f"peak={_format_coord_map(item.peak_coords)}"
        )
        for point in item.top_points:
            print(
                f"  point {point.index}: dx={_format_float(point.dx)} "
                f"dy={_format_float(point.dy)} mag={_format_float(point.magnitude)}"
            )




    # Visual diff overlay generation (executed regardless of active tuples)
    if getattr(args, "visual_diff", False):
        from pathlib import Path
        out_dir = Path(getattr(args, "output_dir", "."))
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / "diff_overlay.png"
        # args.instance_a and instance_b are lists; take first element if present
        base_coords = None
        if getattr(args, "instance_a", None):
            base_coords = _parse_instance(args.instance_a)
        compare_coords = None
        if getattr(args, "instance_b", None):
            compare_coords = _parse_instance(args.instance_b)
        generate_overlay(
            base_font_path=args.file,
            compare_font_path=args.file,
            output_path=str(out_path),
            base_coordinates=base_coords,
            compare_coordinates=compare_coords,
        )
        print(f"Visual diff saved: {out_path}")

def _cmd_var_delta_board(args: argparse.Namespace) -> None:
    try:
        font = _require_variable_ttf(_load_font(args))
        coordinates = _parse_symbolic_instance(args.instance) if args.instance else None
        glyph_id, codepoint = _resolve_glyph_target(
            gid=args.gid,
            codepoint_text=args.codepoint,
            character=args.character,
        )
        preview = font.smart_instancer.build_delta_sheet(
            glyph_id=glyph_id,
            codepoint=codepoint,
            coordinates=coordinates,
            instance_name=args.instance_name,
            top_points=args.top_points,
            panel_size=args.panel_size,
        )
        written = preview.write_to(args.output)
    except Exception as exc:
        _die(str(exc))

    print(f"Saved: {written}")


def _cmd_var_delta_text(args: argparse.Namespace) -> None:
    try:
        font = _require_variable_ttf(_load_font(args))
        coordinates = _parse_symbolic_instance(args.instance) if args.instance else None
        report = font.smart_instancer.inspect_delta_text(
            text=args.text,
            coordinates=coordinates,
            instance_name=args.instance_name,
            top_points=args.top_points,
        )
    except Exception as exc:
        _die(str(exc))

    if args.json:
        print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
        return

    print(f"Text:              {report.text!r}")
    print(f"Instance:          {report.instance_label}")
    print(f"Coordinates:       {_format_coord_map(report.coordinates)}")
    print(f"Normalized coords: {_format_coord_map(report.normalized_coordinates)}")
    print(f"Glyphs:            {report.glyph_count}")
    print(f"Active glyphs:     {report.active_glyph_count}")
    print(f"Supported glyphs:  {report.supported_glyph_count}")
    for glyph_report in report.glyph_reports[: args.limit]:
        glyph_label = (
            f"U+{glyph_report.codepoint:04X}"
            if glyph_report.codepoint is not None
            else f"GID {glyph_report.glyph_id}"
        )
        if glyph_report.character and not glyph_report.character.isspace():
            glyph_label = f"{glyph_label} '{glyph_report.character}'"
        strongest = (
            f"#{glyph_report.strongest_points[0].index} mag={_format_float(glyph_report.strongest_points[0].magnitude)}"
            if glyph_report.strongest_points
            else "-"
        )
        print(
            f"{glyph_label}: tuples={len(glyph_report.active_tuples)}/{glyph_report.total_tuple_count} "
            f"points={glyph_report.point_count} strongest={strongest}"
        )


def _cmd_var_delta_text_compare(args: argparse.Namespace) -> None:
    try:
        font = _require_variable_ttf(_load_font(args))
        before_coordinates = (
            _parse_symbolic_instance(args.before_instance) if args.before_instance else None
        )
        after_coordinates = (
            _parse_symbolic_instance(args.after_instance) if args.after_instance else None
        )
        report = font.smart_instancer.compare_delta_text(
            text=args.text,
            before_coordinates=before_coordinates,
            after_coordinates=after_coordinates,
            before_instance_name=args.before_instance_name,
            after_instance_name=args.after_instance_name,
            top_points=args.top_points,
        )
    except Exception as exc:
        _die(str(exc))

    if args.json:
        print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
        return

    print(f"Text:              {report.text!r}")
    print(f"Before:            {report.before_label}")
    print(f"After:             {report.after_label}")
    print(f"Before coords:     {_format_coord_map(report.before_coordinates)}")
    print(f"After coords:      {_format_coord_map(report.after_coordinates)}")
    print(f"Glyphs:            {report.glyph_count}")
    print(f"Comparable glyphs: {report.comparable_glyph_count}")
    print(f"Moved glyphs:      {report.moved_glyph_count}")
    for glyph_report in report.glyph_comparisons[: args.limit]:
        glyph_label = (
            f"U+{glyph_report.codepoint:04X}"
            if glyph_report.codepoint is not None
            else f"GID {glyph_report.glyph_id}"
        )
        if glyph_report.character and not glyph_report.character.isspace():
            glyph_label = f"{glyph_label} '{glyph_report.character}'"
        strongest = (
            f"#{glyph_report.comparison_points[0].index} "
            f"mag={_format_float(glyph_report.comparison_points[0].magnitude)}"
            if glyph_report.comparison_points
            else "-"
        )
        print(
            f"{glyph_label}: comparable={'yes' if glyph_report.is_comparable else 'no'} "
            f"moved={glyph_report.moved_point_count} strongest={strongest}"
        )
        if glyph_report.note:
            print(f"  note: {glyph_report.note}")


def _cmd_var_delta_text_board(args: argparse.Namespace) -> None:
    try:
        font = _require_variable_ttf(_load_font(args))
        coordinates = _parse_symbolic_instance(args.instance) if args.instance else None
        preview = font.smart_instancer.build_delta_text_sheet(
            text=args.text,
            coordinates=coordinates,
            instance_name=args.instance_name,
            top_points=args.top_points,
            panel_size=args.panel_size,
            columns=args.columns,
        )
        written = preview.write_to(args.output)
    except Exception as exc:
        _die(str(exc))

    print(f"Saved: {written}")


def _cmd_var_delta_text_compare_board(args: argparse.Namespace) -> None:
    try:
        font = _require_variable_ttf(_load_font(args))
        before_coordinates = (
            _parse_symbolic_instance(args.before_instance) if args.before_instance else None
        )
        after_coordinates = (
            _parse_symbolic_instance(args.after_instance) if args.after_instance else None
        )
        preview = font.smart_instancer.build_delta_text_comparison_sheet(
            text=args.text,
            before_coordinates=before_coordinates,
            after_coordinates=after_coordinates,
            before_instance_name=args.before_instance_name,
            after_instance_name=args.after_instance_name,
            top_points=args.top_points,
            panel_size=args.panel_size,
            columns=args.columns,
        )
        written = preview.write_to(args.output)
    except Exception as exc:
        _die(str(exc))

    print(f"Saved: {written}")


def _cmd_var_delta_compare(args: argparse.Namespace) -> None:
    try:
        font = _require_variable_ttf(_load_font(args))
        before_coordinates = (
            _parse_symbolic_instance(args.before_instance) if args.before_instance else None
        )
        after_coordinates = (
            _parse_symbolic_instance(args.after_instance) if args.after_instance else None
        )
        glyph_id, codepoint = _resolve_glyph_target(
            gid=args.gid,
            codepoint_text=args.codepoint,
            character=args.character,
        )
        report = font.smart_instancer.compare_delta_glyph(
            glyph_id=glyph_id,
            codepoint=codepoint,
            before_coordinates=before_coordinates,
            after_coordinates=after_coordinates,
            before_instance_name=args.before_instance_name,
            after_instance_name=args.after_instance_name,
            top_points=args.top_points,
        )
    except Exception as exc:
        _die(str(exc))

    if args.json:
        print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
        return

    glyph_label = f"GID {report.glyph_id}"
    if report.glyph_name:
        glyph_label = f"{glyph_label} ({report.glyph_name})"
    if report.codepoint is not None:
        glyph_label = f"{glyph_label} U+{report.codepoint:04X}"
        if report.character and not report.character.isspace():
            glyph_label = f"{glyph_label} '{report.character}'"
    strongest = (
        "; ".join(
            (
                f"#{point.index} dx={_format_float(point.dx)} "
                f"dy={_format_float(point.dy)} mag={_format_float(point.magnitude)}"
            )
            for point in report.comparison_points[:5]
        )
        if report.comparison_points
        else "-"
    )
    print(f"Glyph:             {glyph_label}")
    print(f"Before:            {report.before.instance_label}")
    print(f"Before coords:     {_format_coord_map(report.before.coordinates)}")
    print(f"After:             {report.after.instance_label}")
    print(f"After coords:      {_format_coord_map(report.after.coordinates)}")
    print(f"Comparable:        {'yes' if report.is_comparable else 'no'}")
    print(f"Moved points:      {report.moved_point_count}")
    print(f"Net movement:      {strongest}")
    if report.before.component_movements:
        print(
            "Before components: "
            + "; ".join(
                _format_component_movement(movement)
                for movement in report.before.component_movements[:4]
            )
        )
    if report.after.component_movements:
        print(
            "After components:  "
            + "; ".join(
                _format_component_movement(movement)
                for movement in report.after.component_movements[:4]
            )
        )
    if report.note:
        print(f"Note:              {report.note}")


def _cmd_var_delta_compare_board(args: argparse.Namespace) -> None:
    try:
        font = _require_variable_ttf(_load_font(args))
        before_coordinates = (
            _parse_symbolic_instance(args.before_instance) if args.before_instance else None
        )
        after_coordinates = (
            _parse_symbolic_instance(args.after_instance) if args.after_instance else None
        )
        glyph_id, codepoint = _resolve_glyph_target(
            gid=args.gid,
            codepoint_text=args.codepoint,
            character=args.character,
        )
        preview = font.smart_instancer.build_delta_comparison_sheet(
            glyph_id=glyph_id,
            codepoint=codepoint,
            before_coordinates=before_coordinates,
            after_coordinates=after_coordinates,
            before_instance_name=args.before_instance_name,
            after_instance_name=args.after_instance_name,
            top_points=args.top_points,
            panel_size=args.panel_size,
        )
        written = preview.write_to(args.output)
    except Exception as exc:
        _die(str(exc))

    print(f"Saved: {written}")


def _require_variable_ttf(font) -> TtfFont:
    if not isinstance(font, TtfFont) or not font.is_variable:
        raise ValueError("Command requires a variable TTF font")
    return font


def _format_localization_resolution(resolution) -> str | None:
    if resolution.is_exact_match:
        return None
    selected = resolution.selected_language or "metadata"
    requested = ", ".join(resolution.requested_languages) or "default"
    return (
        f"Label fallback: requested={requested}; selected={selected}; "
        f"reason={resolution.fallback_reason}"
    )


def _format_localization_coverage(coverage) -> str | None:
    if coverage.status == "complete":
        return None
    requested = ", ".join(coverage.requested_languages) or "-"
    available = ", ".join(coverage.available_languages) or "-"
    missing = ", ".join(coverage.missing_languages) or "-"
    return (
        f"Localization coverage: {coverage.status} "
        f"(requested={requested}; available={available}; missing={missing})"
    )


def _print_color_diagnostics(font: TtfFont) -> None:
    """Print color font inspection diagnostics to stdout."""
    colr = font.ttf_tables.colr
    cpal = font.ttf_tables.cpal

    if colr is None or cpal is None:
        print("Color Font Diagnostics:")
        print("  No color font data (COLR/CPAL tables not present)")
        return

    print("Color Font Diagnostics:")
    print(f"  COLR version: {colr.version}")
    print(f"  CPAL version: {cpal.version}")
    print(f"  Color palettes: {len(cpal.palettes)}")
    print(f"  Color records: {cpal.num_color_records}")

    if colr.version == 0:
        print(f"  Color glyphs: {len(colr.base_glyph_records)}")
        print(f"  Base glyph records: {len(colr.base_glyph_records)}")
        print(f"  Layer records: {len(colr.layer_records)}")
    elif colr.version == 1:
        base_count = len(colr.base_glyph_v1_records) if colr.base_glyph_v1_records else 0
        layer_count = len(colr.layer_v1_records) if colr.layer_v1_records else 0
        paint_count = len(colr.paints) if colr.paints else 0
        print(f"  Color glyphs: {base_count}")
        print(f"  Base glyph v1 records: {base_count}")
        print(f"  Layer v1 records: {layer_count}")
        print(f"  Paints: {paint_count}")

    palette_labels_available = any(cpal.palette_labels)
    color_labels_available = any(cpal.color_labels)

    print(
        f"  Palette labels: {'Available' if palette_labels_available else 'N/A (no labels defined)'}"
    )
    print(
        f"  Color labels: {'Available' if color_labels_available else 'N/A (no labels defined)'}"
    )

    for palette_idx, palette in enumerate(cpal.palettes):
        print(f"  Palette {palette_idx}: {len(palette.colors)} colors")
        for color_idx, (r, g, b, a) in enumerate(palette.colors[:8]):
            hex_color = f"#{r:02X}{g:02X}{b:02X}{a:02X}"
            print(f"    [{color_idx}] {hex_color}")
        if len(palette.colors) > 8:
            print(f"    ... and {len(palette.colors) - 8} more colors")


def _cmd_var_info(args: argparse.Namespace) -> None:
    try:
        font = _require_variable_ttf(_load_font(args))
    except Exception as exc:
        _die(str(exc))
    preferred_languages = tuple(args.language) if getattr(args, "language", None) else ("en",)

    if args.json_output:
        try:
            with open(args.json_output, "w", encoding="utf-8") as handle:
                json.dump(
                    font.variable_presentation(preferred_languages=preferred_languages),
                    handle,
                    ensure_ascii=False,
                    indent=2,
                    sort_keys=True,
                )
                handle.write("\n")
        except Exception as exc:
            _die(str(exc))

    print("Axes:")
    for axis in font.variable_axes:
        axis_label = axis.name(preferred_languages) or axis.label
        print(
            f"  {axis.tag}: {axis_label} "
            f"(min={axis.min_value:g}, default={axis.default_value:g}, max={axis.max_value:g}, "
            f"kind={axis.presentation_kind}, step={axis.recommended_step:g})"
        )
        if axis.available_languages:
            print(f"    Languages: {', '.join(axis.available_languages)}")
        fallback = _format_localization_resolution(
            axis.localization_resolution(preferred_languages)
        )
        if fallback:
            print(f"    {fallback}")
        if args.language:
            coverage = _format_localization_coverage(
                axis.localization_coverage(preferred_languages)
            )
            if coverage:
                print(f"    {coverage}")
        if len(axis.available_languages) > 1:
            localized = ", ".join(
                f"{language}={label}"
                for language, label in axis.localized_labels(preferred_languages)
            )
            print(f"    Localized labels: {localized}")
        print(f"    Range: {axis.range_summary}")
        ratio = axis.default_ratio
        if ratio is not None:
            print(f"    Default position: {ratio:.0%} through range")
        if axis.presets:
            presets = ", ".join(
                f"{preset.name}={axis.format_value(preset.value)}" for preset in axis.presets
            )
            print(f"    Presets: {presets}")
        suggested = ", ".join(
            axis.format_value(value)
            for value in font.smart_instancer.suggest_axis_values(
                axis.tag,
                include_default=True,
                include_bounds=True,
            )
        )
        print(f"    Suggested grid: {suggested}")

    print("Named Instances:")
    axes_by_tag = {axis.tag: axis for axis in font.variable_axes}
    for instance in font.variable_instances:
        coords = ", ".join(
            instance.format_coordinates(
                axes_by_tag,
                language=preferred_languages,
                include_tags=True,
            )
        )
        label = instance.name(preferred_languages) or instance.label
        print(f"  {label}: {coords}")
        if instance.available_languages:
            print(f"    Languages: {', '.join(instance.available_languages)}")
        fallback = _format_localization_resolution(
            instance.localization_resolution(preferred_languages)
        )
        if fallback:
            print(f"    {fallback}")
        if args.language:
            coverage = _format_localization_coverage(
                instance.localization_coverage(preferred_languages)
            )
            if coverage:
                print(f"    {coverage}")
        if len(instance.available_languages) > 1:
            localized = ", ".join(
                f"{language}={value}"
                for language, value in instance.localized_labels(preferred_languages)
            )
            print(f"    Localized labels: {localized}")

    if args.color_diagnostics:
        _print_color_diagnostics(font)

    if args.json_output:
        print(f"Saved JSON: {args.json_output}")


def _cmd_var_instance(args: argparse.Namespace) -> None:
    try:
        font = _require_variable_ttf(_load_font(args))
        coordinates = _parse_symbolic_instance(args.instance) if args.instance else None
        apply_avar = getattr(args, "apply_avar", True)
        instantiated = font.smart_instancer.instantiate(
            coordinates,
            instance_name=args.instance_name,
            naming_strategy=args.naming_strategy,
            family_suffix=args.family_suffix,
            legacy_family_name=args.legacy_family_name,
            typographic_family_name=args.typographic_family_name,
            legacy_style_name=args.legacy_style_name,
            typographic_style_name=args.typographic_style_name,
            stat_policy=args.stat_policy,
            apply_avar=apply_avar,
        )
        instantiated.save(args.output)
    except Exception as exc:
        _die(str(exc))

    if getattr(args, "apply_avar", True):
        print("Avar table mapping: applied")
    else:
        print("Avar table mapping: skipped")
    print(f"Saved: {args.output}")


def _cmd_var_package(args: argparse.Namespace) -> None:
    try:
        input_file = getattr(args, "file", None)
        if not input_file:
            _die("Input file is required.")
        font = _require_variable_ttf(FontLoader.open(input_file))
        compare_axes = args.compare_axes.split(",") if args.compare_axes else None
        from aspose_font.preview import FontPreviewBuilder

        output_dir = Path(args.output_dir)

        from aspose_font.instances import VariableInstanceBuilder, VariableInstancePackage
        from aspose_font.instancing import ResolvedInstance

        if args.instance:
            if len(args.instance) > 1:
                coordinates = _parse_instance(args.instance)
            else:
                value = args.instance[0]
                if "," in value:
                    coordinates = _parse_instance_comma_separated(value)
                else:
                    coordinates = _parse_instance([value])
            original_font = font

            performance_report = getattr(args, "performance_report", False)

            if performance_report:
                import time
                start_time = time.perf_counter()

            font = font.instantiate(
                coordinates,
                naming_strategy=args.naming_strategy,
                family_suffix=args.family_suffix,
                legacy_family_name=args.legacy_family_name,
                typographic_family_name=args.typographic_family_name,
                legacy_style_name=args.legacy_style_name,
                typographic_style_name=args.typographic_style_name,
                stat_policy=args.stat_policy,
                preserve_source_stat_flags=getattr(args, "preserve_source_stat_flags", False),
                apply_avar=getattr(args, "apply_avar", True),
                skip_hvar=getattr(args, "ci_fast", False),
                ci_fast_mode=getattr(args, "ci_fast", False),
            )

            if performance_report:
                elapsed_ms = (time.perf_counter() - start_time) * 1000
                print(f"Build time: {elapsed_ms:.2f} ms")

            from aspose_font.instancing import ResolvedInstance

            resolved = ResolvedInstance(
                coordinates=coordinates,
                source_instance=None,
                is_default=False,
            )
            ci_fast_mode = getattr(args, "ci_fast", False)
            if ci_fast_mode:
                from aspose_font.preview import FontPreviewBuilder
                comparison_board = FontPreviewBuilder.build(
                    original_font,
                    text="H",
                    size=1.0,
                    color=(17, 17, 17),
                    background=(255, 253, 248),
                    padding=0,
                    antialias=False,
                    file_stem="preview",
                )
                # In fast mode, reuse comparison board as specimen board placeholder
                specimen_board = comparison_board
            else:
                comparison_board = original_font.smart_instancer.build_comparison_sheet(
                    text=args.preview_text,
                    file_stem="preview",
                    compare_axes=compare_axes,
                )
                # Generate specimen board PNG with STAT policy caption
                specimen_caption = f"STAT policy: {args.stat_policy}"
                specimen_board = FontPreviewBuilder.compose_sheet(
                    [comparison_board],
                    columns=1,
                    labels=[specimen_caption],
                    file_stem="specimen_board",
                )
            stat_evidence = {
                "policy": args.stat_policy,
                "instances": [
                    {
                        "label": resolved.label,
                        "coordinates": dict(resolved.coordinates),
                        "source_instance": None,
                    }
                ],
            }
            review_manifest = {
                "package_type": "variable-instance-package",
                "font_filename": "instance.ttf",
                "preview_filename": "preview.png",
                "stat_evidence_filename": "stat-evidence.json",
                "manifest_filename": "manifest.json",
            }
            package = VariableInstancePackage(
                instances=[resolved],
                fonts=[font],
                comparison_board=comparison_board,
                specimen_board=specimen_board,
                stat_evidence=stat_evidence,
                review_manifest=review_manifest,
                preview_text=args.preview_text,
                output_directory=output_dir,
                build_time_ms=elapsed_ms if performance_report else 0.0,
            )
            package.write_to(
                    output_dir,
                    font_filename="instance.ttf",
                    stat_evidence_filename="stat-evidence.json",
                    preview_filename="preview.png",
                    manifest_filename="manifest.json",
                )
        else:
            package = VariableInstanceBuilder(font).build_package(
                names=args.instance_name if args.instance_name else None,
                include_default=not args.no_default,
                naming_strategy=args.naming_strategy,
                family_suffix=args.family_suffix,
                **_naming_override_kwargs(args),
                stat_policy=args.stat_policy,
                preserve_source_stat_flags=getattr(args, "preserve_source_stat_flags", False),
                preview_text=args.preview_text,
                specimen_caption=args.specimen_caption,
                compare_axes=compare_axes,
                apply_avar=getattr(args, "apply_avar", True),
                ci_fast_mode=getattr(args, "ci_fast", False),
            )

            if getattr(args, "performance_report", False):
                print(f"Build time: {package.build_time_ms:.2f} ms")
            if len(package.instances) == 1:
                package.write_to(
                    output_dir,
                    font_filename="instance.ttf",
                    stat_evidence_filename="stat-evidence.json",
                    preview_filename="preview.png",
                    manifest_filename="manifest.json",
                )
            else:
                package.write_to(
                    output_dir,
                    font_filename="instance.ttf",
                    stat_evidence_filename="stat-evidence.json",
                    preview_filename="preview.png",
                    manifest_filename="manifest.json",
                )
                if getattr(args, "specimen_board", False):
                    package.generate_specimen_board(output_dir)
        print(f"Package written to: {output_dir.absolute()}")
        print(f"Instances: {len(package.instances)}")
        print(f"STAT policy: {args.stat_policy}")
        print(f"Preserve STAT flags: {args.preserve_stat_flags}")
        print(f"Apply avar: {getattr(args, 'apply_avar', True)}")
    except Exception as exc:
        _die(str(exc))


def _cmd_stat_fix(args: argparse.Namespace) -> None:
    try:
        font = _require_variable_ttf(_load_font(args))
    except Exception as exc:
        _die(str(exc))

    try:
        raw_stat = font.get_table_bytes("STAT")
    except Exception:
        raw_stat = None

    if raw_stat is None:
        try:
            synth_bytes = font.smart_instancer.synthesize_missing_stat_table()
        except Exception as exc:
            _die(str(exc))

        if getattr(args, "dry_run", False):
            if synth_bytes is None:
                print("STAT table could not be synthesized. No changes needed.")
            else:
                print("STAT table will be synthesized.")
                parsed = parse_stat_table(synth_bytes)
                if parsed:
                    print(f"Version: {parsed['version']}")
                    print(f"Design axes: {len(parsed.get('design_axes', []))}")
                    print(f"Axis values: {len(parsed.get('axis_values', []))}")
            return

        if synth_bytes is None:
            _die("Could not synthesize STAT table. Font may not be variable or lacks fvar.")

        try:
            font.set_table_bytes("STAT", synth_bytes)
        except Exception as exc:
            _die(f"Cannot set STAT table: {exc}")

        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(font.to_bytes())

        print(f"STAT table synthesized and written to: {output_path}")
        return

    try:
        parsed_stat = parse_stat_table(raw_stat)
    except Exception:
        parsed_stat = None

    needs_repair = False
    repair_reasons = []

    if parsed_stat is None:
        needs_repair = True
        repair_reasons.append("STAT table could not be parsed")
    else:
        stat_axes = parsed_stat.get("design_axes", [])
        stat_axis_tags = {axis["tag"] for axis in stat_axes}
        fvar_axes = font.axes
        fvar_axis_tags = {axis.tag for axis in fvar_axes}

        missing_axes = fvar_axis_tags - stat_axis_tags
        if missing_axes:
            needs_repair = True
            repair_reasons.append(f"missing DesignAxis entries for: {', '.join(sorted(missing_axes))}")

    if getattr(args, "dry_run", False):
        if needs_repair:
            print("STAT table has issues and will be repaired:")
            for reason in repair_reasons:
                print(f"  - {reason}")
            return
        print("STAT table is valid. No changes needed.")
        return

    if not needs_repair:
        _die("STAT table is valid. Use --dry-run to inspect without changes.")

    try:
        synth_bytes = font.smart_instancer.synthesize_missing_stat_table()
    except Exception as exc:
        _die(f"Cannot synthesize STAT table: {exc}")

    if synth_bytes is None:
        _die("Could not synthesize STAT table.")

    try:
        font.set_table_bytes("STAT", synth_bytes)
    except Exception as exc:
        _die(f"Cannot set STAT table: {exc}")

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(font.to_bytes())

    print(f"STAT table repaired and written to: {output_path}")


def _cmd_autonomous(args: argparse.Namespace) -> None:
    try:
        font = _load_font(args)

        cdn_manifest_enabled = getattr(args, "cdn_manifest", False)
        cdn_base_url = getattr(args, "cdn_base", "https://cdn.example.com")

        result = run_autonomous_workflow(
            font,
            input_path=args.file,
            output_dir=args.output_dir,
            include_qa=not getattr(args, "no_qa", False),
            include_instances=not getattr(args, "no_instances", False),
            preset=args.preset if args.preset else None,
            naming_strategy=args.naming_strategy,
            custom_family_suffix=args.family_suffix,
            legacy_family=args.legacy_family_name,
            legacy_style=args.legacy_style_name,
            typographic_family=args.typographic_family_name,
            typographic_style=args.typographic_style_name,
            stat_policy=args.stat_policy,
            font_display=args.font_display,
            include_woff=not getattr(args, "no_woff", False),
            cdn_manifest=cdn_manifest_enabled,
            cdn_base=cdn_base_url,
        )

        written = []

        if result.web_package:
            bundle_written = result.web_package.bundle.write_to(args.output_dir)
            written.extend(bundle_written)

            if result.web_package.css:
                css_path = Path(args.output_dir) / result.web_package.bundle.css_filename
                if css_path not in written:
                    written.append(css_path)

            if result.web_package.specimen_html:
                html_path = Path(args.output_dir) / result.web_package.bundle.html_filename
                if html_path not in written:
                    written.append(html_path)

            if result.web_package.manifest:
                manifest_path = Path(args.output_dir) / "optimizer-manifest.json"
                manifest_path.write_text(
                    json.dumps(result.web_package.bundle.manifest, indent=2, sort_keys=True),
                    encoding="utf-8",
                )
                written.append(manifest_path)

            if cdn_manifest_enabled:
                cdn_manifest_path = Path(args.output_dir) / "cdn-manifest.json"
                cdn_manifest_data = getattr(result.web_package, "cdn_manifest", {})
                if cdn_manifest_data:
                    cdn_manifest_path.write_text(
                        json.dumps(cdn_manifest_data, indent=2, sort_keys=True),
                        encoding="utf-8",
                    )
                    written.append(cdn_manifest_path)

        if result.qa_package:
            written.append(result.qa_package.json_path)
            written.append(result.qa_package.html_path)

        if result.instance_package:
            instance_written = result.instance_package.write_to(args.output_dir)
            written.extend(instance_written)

        if getattr(args, "json_summary", None):
            summary_path = Path(args.json_summary)
            summary_path.write_text(
                json.dumps(result.summary, indent=2, sort_keys=True),
                encoding="utf-8",
            )
            written.append(summary_path)



        metrics = result.metrics
        metrics_path = Path(args.output_dir) / "autonomous-metrics.json"
        metrics_path.write_text(
            json.dumps(metrics, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        written.append(metrics_path)

        summary_path = Path(args.output_dir) / "autonomous-summary.json"
        summary_path.write_text(
            json.dumps(result.summary, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        written.append(summary_path)

    except Exception as exc:
        _die(str(exc))

    decision = result.decision
    # Write autonomous decision report JSON if flag provided
    if getattr(args, "decision_report", None) and not getattr(args, "no_decision_report", False):
        decision_data = {
            "decision": decision.workflow,
            "reason": decision.reason,
            "confidence": decision.confidence,
            "detected_font_type": decision.detected_font_type,
            "detected_capabilities": decision.detected_capabilities,
            "recommended_actions": decision.recommended_actions,
        }
        custom_path = Path(args.decision_report)
        if not custom_path.is_absolute():
            custom_path = Path(args.output_dir) / custom_path
        custom_path.parent.mkdir(parents=True, exist_ok=True)
        custom_path.write_text(json.dumps(decision_data, indent=2, sort_keys=True), encoding="utf-8")
    if not getattr(args, "no_decision_report", False):
        print(f"Autonomous workflow decision: {decision.workflow}")
        if getattr(args, "verbose", False):
            print(f"  Reason: {decision.reason}")
            print(f"  Confidence: {decision.confidence:.2f}")
            print(f"  Detected font type: {decision.detected_font_type}")
            print(f"  Detected capabilities: {', '.join(decision.detected_capabilities)}")
            print(f"  Recommended actions: {len(decision.recommended_actions)} item(s)")

    if result.web_package:
        print(f"Web package: {result.web_package.bundle.family} {result.web_package.bundle.style}")
        if result.web_package.bundle.manifest:
            size_summary = result.web_package.bundle.manifest.get("size_summary", {})
            total_bytes = size_summary.get("total_web_font_bytes", 0)
            print(f"  Web font bytes: {total_bytes}")

    if result.qa_package:
        print(f"QA package: {result.qa_package.directory}")

    if result.instance_package:
        print(f"Instance package: {result.instance_package.output_directory}")
        print(f"  Instances: {len(result.instance_package.instances)}")

    print(f"Total time: {metrics.get('total_time_ms', 0)} ms")
    for path in written:
        print(f"Written: {path}")


def _generate_diff_overlay(
    font: Any, output_dir: Path | None, grid: list[dict[str, float]]
) -> None:
    """Generate visual diff overlay for uncovered grid points."""
    axes = font.variable_axes
    if not axes or len(axes) < 2:
        _die("Font must have at least two axes for diff overlay generation")

    axis1 = axes[0].tag
    axis2 = axes[1].tag

    try:
        output_path = (
            output_dir / "designspace-overlay.png"
            if output_dir
            else Path("designspace-overlay.png")
        )
        generate_designspace_diff_overlay(font, axis1, axis2, output_path)
        print(f"Designspace diff overlay written to: {output_path}")
    except Exception as exc:
        _die(f"Failed to generate diff overlay: {exc}")


def _cmd_var_designspace_coverage(args: argparse.Namespace) -> None:
    font = _load_font(args)
    if not font.is_variable:
        _die("Font is not a variable font (no FVAR table).")

    if args.grid:
        grid_path = Path(args.grid)
        if grid_path.is_file():
            try:
                content = grid_path.read_text(encoding="utf-8")
                grid = json.loads(content)
            except json.JSONDecodeError as exc:
                _die(f"Invalid grid JSON file: {exc}")
        else:
            try:
                grid = json.loads(args.grid)
            except json.JSONDecodeError as exc:
                _die(f"Invalid grid JSON: {exc}")

        if not isinstance(grid, list):
            _die("Grid must be a JSON array")
        for item in grid:
            if not isinstance(item, dict):
                _die("Each grid point must be a JSON object")
    else:
        grid = []

    try:
        result = compute_designspace_coverage(font, grid)
    except ValueError as exc:
        _die(str(exc))

    output_dir = Path(args.output_dir) if args.output_dir else None

    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)
        json_path = output_dir / "coverage-report.json"
        try:
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2)
            print(f"Coverage report written to: {json_path}")
        except OSError as exc:
            _die(f"Failed to write JSON report: {exc}")
        else:
            print(json.dumps(result, indent=2))

    if args.generate_diff:
        _generate_diff_overlay(font, output_dir, grid)


def _cmd_batch_workflow(args: argparse.Namespace) -> None:
    from aspose_font.batch_workflow import BatchSummary, process_directory

    try:
        summary: BatchSummary = process_directory(
            input_directory=args.input_dir,
            output_directory=args.output_dir,
            naming_strategy=args.naming_strategy,
            stat_policy=args.stat_policy,
            preview_text=args.preview_text,
        )
    except Exception as exc:
        _die(str(exc))

    print(
        f"Batch complete: {summary.success_count}/{summary.total_count} fonts processed successfully"
    )
    print(f"Output directory: {summary.output_directory}")
    print("Summary written to: batch-summary.json")


def _cmd_var_naming_preview(args: argparse.Namespace) -> None:
    try:
        font = _require_variable_ttf(_load_font(args))
        coordinates = _parse_symbolic_instance(args.instance) if args.instance else None
        preview = font.smart_instancer.preview_naming_policy(
            coordinates,
            instance_name=args.instance_name,
            naming_strategy=args.naming_strategy,
            family_suffix=args.family_suffix,
            stat_policy=args.stat_policy,
            **_naming_override_kwargs(args),
        )
        payload = preview.to_dict()
        if args.json_output:
            with open(args.json_output, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
                handle.write("\n")
    except Exception as exc:
        _die(str(exc))

    print(f"Naming strategy: {preview.naming_strategy}")
    if preview.family_suffix:
        print(f"Family suffix: {preview.family_suffix}")
    if preview.source_instance_name:
        print(f"Source instance: {preview.source_instance_name}")
    print("Effective name IDs:")
    for name_id, value in preview.name_ids.items():
        print(f"  {name_id}: {value}")
    if preview.stat_diagnostics is not None:
        stat = preview.stat_diagnostics

        def _format_axis_value_flag_summary(summary: dict[str, int]) -> str:
            return (
                f"total={summary.get('total', 0)}; "
                f"nonzero={summary.get('nonzero', 0)}; "
                f"older-sibling={summary.get('older_sibling', 0)}; "
                "elidable-axis-value-name="
                f"{summary.get('elidable_axis_value_name', 0)}; "
                f"unknown={summary.get('unknown', 0)}"
            )

        print("STAT diagnostics:")
        print(f"  Policy: {stat.stat_policy}")
        print(f"  Supported STAT policies: {','.join(stat.supported_stat_policies)}")
        print(f"  Source STAT: {'yes' if stat.source_has_stat else 'no'}")
        print(f"  Static export action: {stat.static_export_action}")
        print(f"  STAT policy recommendation: {stat.stat_policy_recommendation}")
        if stat.stat_policy_recommendation_reasons:
            print(
                "  STAT policy recommendation reasons: "
                f"{','.join(stat.stat_policy_recommendation_reasons)}"
            )
        print(f"  STAT policy next action: {stat.stat_policy_next_action}")
        print(f"  STAT policy override suggestion: {stat.stat_policy_override_suggestion or '-'}")
        if stat.stat_policy_override_suggestion_reasons:
            print(
                "  STAT policy override suggestion reasons: "
                f"{','.join(stat.stat_policy_override_suggestion_reasons)}"
            )
        if stat.generated_stat_axis_tags:
            print(f"  Generated STAT axes: {','.join(stat.generated_stat_axis_tags)}")
        if stat.generated_stat_name_ids:
            print(
                "  Generated STAT name IDs: "
                f"{','.join(str(item) for item in stat.generated_stat_name_ids)}"
            )
        print(
            "  Typographic IDs emitted: "
            f"family={','.join(str(item) for item in stat.typographic_family_ids_emitted)}; "
            f"style={','.join(str(item) for item in stat.typographic_style_ids_emitted)}"
        )
        if stat.source_stat_name_ids:
            print(
                "  Source STAT name IDs: "
                f"{','.join(str(item) for item in stat.source_stat_name_ids)}"
            )
            print(
                "  Covered source STAT name IDs: "
                f"{','.join(str(item) for item in stat.covered_source_stat_name_ids) or '-'}"
            )
            print(
                "  Uncovered source STAT name IDs: "
                f"{','.join(str(item) for item in stat.uncovered_source_stat_name_ids) or '-'}"
            )
            if stat.source_stat_name_labels:
                print("  Source STAT labels:")
                for name_id, label, covered in stat.source_stat_name_labels:
                    coverage = "covered" if covered else "uncovered"
                    print(f"    {name_id}: {label or '-'} ({coverage})")
        if stat.source_stat_axis_value_flags:
            print(
                "  Source STAT AxisValue flags: "
                f"{','.join(str(item) for item in stat.source_stat_axis_value_flags)}"
            )
        if stat.source_stat_axis_value_flag_meanings:
            print(
                "  Source STAT AxisValue flag meanings: "
                + "; ".join(
                    f"{flags}={','.join(meanings) or '-'}"
                    for flags, meanings in stat.source_stat_axis_value_flag_meanings
                )
            )
        if stat.source_stat_axis_value_flag_summary.get("total", 0):
            print(
                "  Source STAT AxisValue flag summary: "
                f"{_format_axis_value_flag_summary(stat.source_stat_axis_value_flag_summary)}"
            )
        if stat.generated_stat_axis_value_flags:
            print(f"  Generated STAT AxisValue flags: {stat.generated_stat_axis_value_flags}")
        if stat.generated_stat_axis_value_flag_meanings:
            print(
                "  Generated STAT AxisValue flag meanings: "
                f"{','.join(stat.generated_stat_axis_value_flag_meanings)}"
            )
        if stat.generated_stat_axis_value_flag_summary.get("total", 0):
            print(
                "  Generated STAT AxisValue flag summary: "
                f"{_format_axis_value_flag_summary(stat.generated_stat_axis_value_flag_summary)}"
            )
        if stat.legacy_typographic_family_diverges or stat.legacy_typographic_style_diverges:
            print(
                "  Legacy/typographic divergence: "
                f"family={stat.legacy_typographic_family_diverges}; "
                f"style={stat.legacy_typographic_style_diverges}"
            )
        for note in stat.notes:
            print(f"  Note: {note}")
        for warning in stat.warnings:
            print(f"  Warning: {warning}")
    if preview.platform_diagnostics is not None:
        platform = preview.platform_diagnostics
        print("Platform diagnostics:")
        print(f"  Windows legacy menu safe: {platform.windows_legacy_menu_safe}")
        print(f"  Windows RIBBI style: {platform.windows_legacy_style_ribbi}")
        print(f"  macOS typographic names present: {platform.macos_typographic_names_present}")
        print(f"  macOS typographic divergence: {platform.macos_typographic_names_diverge}")
        print(f"  PostScript name safe: {platform.postscript_name_safe}")
        print(f"  PostScript name length: {platform.postscript_name_length}")
        for note in platform.notes:
            print(f"  Note: {note}")
        for warning in platform.warnings:
            print(f"  Warning: {warning}")
    if preview.warnings:
        print("Warnings:")
        for warning in preview.warnings:
            print(f"  {warning}")
    if args.json_output:
        print(f"Saved JSON: {args.json_output}")


def _slugify_filename(value: str) -> str:
    chars: list[str] = []
    previous_dash = False
    for ch in value.lower():
        if ch.isalnum():
            chars.append(ch)
            previous_dash = False
        else:
            if not previous_dash:
                chars.append("-")
                previous_dash = True
    slug = "".join(chars).strip("-")
    return slug or "instance"


def _format_bbox(bbox: tuple[float, float, float, float] | None) -> str:
    if bbox is None:
        return "-"
    return ",".join(f"{value:g}" for value in bbox)


def _format_geometry_notes(notes: tuple[str, ...]) -> str:
    if not notes:
        return "-"
    return "; ".join(notes)


def _format_compat_issue(issue) -> str:
    char_display = issue.character if issue.character and not issue.character.isspace() else ""
    suffix = f" ({char_display})" if char_display else ""
    return (
        f"U+{issue.codepoint:04X}{suffix}: {issue.reason} | "
        f"before={''.join(issue.before_signature) or '-'} "
        f"after={''.join(issue.after_signature) or '-'} | "
        f"before_stats={issue.before_stats.command_count}/{issue.before_stats.point_count}/{issue.before_stats.contour_count}/aw={issue.before_stats.advance_width} "
        f"after_stats={issue.after_stats.command_count}/{issue.after_stats.point_count}/{issue.after_stats.contour_count}/aw={issue.after_stats.advance_width} | "
        f"before_bbox={_format_bbox(issue.before_stats.bbox)} "
        f"after_bbox={_format_bbox(issue.after_stats.bbox)} | "
        f"geometry_notes={_format_geometry_notes(issue.geometry_notes)}"
    )


def _format_active_tuples(items) -> str:
    if not items:
        return "-"
    return ",".join(f"{item.tuple_index}:{_format_float(item.scalar)}" for item in items)


def _format_tuple_indices(values: tuple[int, ...]) -> str:
    if not values:
        return "-"
    return ",".join(str(value) for value in values)


def _format_retuned_tuples(items) -> str:
    if not items:
        return "-"
    return ",".join(
        f"{item.tuple_index}:{_format_float(item.before_scalar)}->{_format_float(item.after_scalar)}"
        for item in items
    )


def _format_interpolation_issue(issue) -> str:
    char_display = issue.character if issue.character and not issue.character.isspace() else ""
    suffix = f" ({char_display})" if char_display else ""
    return (
        f"U+{issue.codepoint:04X}{suffix}: {issue.reason} | "
        f"before_active={_format_active_tuples(issue.before_active)} "
        f"after_active={_format_active_tuples(issue.after_active)} | "
        f"entered={_format_tuple_indices(issue.entered_tuple_indices)} "
        f"exited={_format_tuple_indices(issue.exited_tuple_indices)} | "
        f"retuned={_format_retuned_tuples(issue.retuned_tuples)}"
    )


def _format_component_movement(movement) -> str:
    strongest = (
        "-" if movement.strongest_point_index is None else f"#{movement.strongest_point_index}"
    )
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
        f"mag={_format_float(movement.strongest_magnitude)} "
        f"total=({_format_float(movement.total_abs_dx)},{_format_float(movement.total_abs_dy)}) "
        f"shift={_format_float(movement.shift_magnitude)}{transform_note}"
    )


def _format_float(value: float) -> str:
    return f"{value:.4f}".rstrip("0").rstrip(".") or "0"


def _format_coord_map(values: dict[str, float]) -> str:
    if not values:
        return "-"
    return ", ".join(f"{tag}={_format_float(value)}" for tag, value in sorted(values.items()))


def _cmd_var_batch(args: argparse.Namespace) -> None:
    try:
        font = _require_variable_ttf(_load_font(args))
        names = list(args.instance_name)
        if not args.all_named and not names:
            raise ValueError("var-batch requires --all-named or at least one --instance-name")
        generated = font.smart_instancer.instantiate_many(
            None if args.all_named and not names else names,
            include_default=args.include_default,
            naming_strategy=args.naming_strategy,
            family_suffix=args.family_suffix,
            stat_policy=args.stat_policy,
            **_naming_override_kwargs(args),
        )
    except Exception as exc:
        _die(str(exc))

    output_dir = args.output_dir
    from pathlib import Path

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    for resolved, instantiated in generated:
        stem = _slugify_filename(instantiated.font_name or f"{font.font_family} {resolved.label}")
        target = output_path / f"{stem}.ttf"
        instantiated.save(str(target))
        print(f"Written: {target}")


def _cmd_web_batch(args: argparse.Namespace) -> None:
    try:
        font = _require_variable_ttf(_load_font(args))
        names = list(args.instance_name)
        if not args.all_named and not names:
            raise ValueError("web-batch requires --all-named or at least one --instance-name")
        codepoints = [_parse_cli_int(value) for value in args.codepoint]
        ranges = [_parse_range(value) for value in args.range]
        generated = font.smart_instancer.build_web_bundles(
            None if args.all_named and not names else names,
            include_default=args.include_default,
            include_woff=not args.no_woff,
            preview_text=args.preview_text,
            specimen_template=args.template,
            naming_strategy=args.naming_strategy,
            family_suffix=args.family_suffix,
            stat_policy=args.stat_policy,
            **_naming_override_kwargs(args),
            presets=args.preset,
            text=args.text,
            codepoints=codepoints,
            ranges=ranges,
        )
    except Exception as exc:
        _die(str(exc))

    from pathlib import Path

    output_path = Path(args.output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    for _resolved, bundle in generated:
        bundle_dir = output_path / _slugify_filename(f"{bundle.family} {bundle.style}")
        written = bundle.write_to(bundle_dir)
        print(
            f"Bundle: {bundle.family} / {bundle.style} | "
            f"export mode: {bundle.manifest.get('export_mode', 'static')}"
        )
        _print_web_export_summary(bundle.manifest)
        for path in written:
            print(f"Written: {path}")


def _cmd_web_grid(args: argparse.Namespace) -> None:
    try:
        font = _require_variable_ttf(_load_font(args))
        primary_values = _parse_float_list(args.value, label="axis")
        secondary_values = _parse_float_list(args.value2, label="secondary axis")
        codepoints = [_parse_cli_int(value) for value in args.codepoint]
        ranges = [_parse_range(value) for value in args.range]
        generated = font.smart_instancer.build_axis_grid_web_bundles(
            args.axis,
            primary_values,
            secondary_axis_tag=args.axis2,
            secondary_values=secondary_values,
            instance_name=args.instance_name,
            **_grid_selection_options(args),
            include_woff=not args.no_woff,
            preview_text=args.preview_text,
            specimen_template=args.template,
            naming_strategy=args.naming_strategy,
            family_suffix=args.family_suffix,
            stat_policy=args.stat_policy,
            **_naming_override_kwargs(args),
            presets=args.preset,
            text=args.text,
            codepoints=codepoints,
            ranges=ranges,
        )
    except Exception as exc:
        _die(str(exc))

    from pathlib import Path

    output_path = Path(args.output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    for resolved, bundle in generated:
        bundle_dir = output_path / _slugify_filename(f"{bundle.family} {bundle.style}")
        written = bundle.write_to(bundle_dir)
        print(
            f"Bundle: {_coordinate_label(resolved.coordinates)} | {bundle.family} / {bundle.style} | "
            f"export mode: {bundle.manifest.get('export_mode', 'static')}"
        )
        _print_web_export_summary(bundle.manifest)
        for path in written:
            print(f"Written: {path}")


def _cmd_web_grid_family(args: argparse.Namespace) -> None:
    try:
        font = _require_variable_ttf(_load_font(args))
        primary_values = _parse_float_list(args.value, label="axis")
        secondary_values = _parse_float_list(args.value2, label="secondary axis")
        codepoints = [_parse_cli_int(value) for value in args.codepoint]
        ranges = [_parse_range(value) for value in args.range]
        package = font.smart_instancer.build_axis_grid_web_family_package(
            args.axis,
            primary_values,
            secondary_axis_tag=args.axis2,
            secondary_values=secondary_values,
            instance_name=args.instance_name,
            family_name=args.family_name,
            **_grid_selection_options(args),
            include_woff=not args.no_woff,
            preview_text=args.preview_text,
            specimen_template=args.template,
            naming_strategy=args.naming_strategy,
            family_suffix=args.family_suffix,
            stat_policy=args.stat_policy,
            **_naming_override_kwargs(args),
            presets=args.preset,
            text=args.text,
            codepoints=codepoints,
            ranges=ranges,
        )
    except Exception as exc:
        _die(str(exc))

    written = package.write_to(args.output_dir)
    print(f"Grid family package: {package.family_name}")
    for bundle in package.bundles:
        print(
            f"Bundle: {bundle.family} / {bundle.style} | "
            f"export mode: {bundle.manifest.get('export_mode', 'static')}"
        )
        _print_web_export_summary(bundle.manifest)
    for path in written:
        print(f"Written: {path}")


def _cmd_web_family(args: argparse.Namespace) -> None:
    try:
        font = _require_variable_ttf(_load_font(args))
        names = list(args.instance_name)
        if not args.all_named and not names:
            raise ValueError("web-family requires --all-named or at least one --instance-name")
        codepoints = [_parse_cli_int(value) for value in args.codepoint]
        ranges = [_parse_range(value) for value in args.range]
        package = font.smart_instancer.build_web_family_package(
            None if args.all_named and not names else names,
            include_default=args.include_default,
            family_name=args.family_name,
            include_woff=not args.no_woff,
            preview_text=args.preview_text,
            specimen_template=args.template,
            naming_strategy=args.naming_strategy,
            family_suffix=args.family_suffix,
            stat_policy=args.stat_policy,
            **_naming_override_kwargs(args),
            presets=args.preset,
            text=args.text,
            codepoints=codepoints,
            ranges=ranges,
        )
    except Exception as exc:
        _die(str(exc))

    written = package.write_to(args.output_dir)
    print(f"Family package: {package.family_name}")
    for bundle in package.bundles:
        print(
            f"Bundle: {bundle.family} / {bundle.style} | "
            f"export mode: {bundle.manifest.get('export_mode', 'static')}"
        )
        _print_web_export_summary(bundle.manifest)
    for path in written:
        print(f"Written: {path}")


def _cmd_perf_regression(args: argparse.Namespace) -> None:
    """Run CI performance regression bench suite and output JSON report."""
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent.parent
    fixture_root = project_root / "testdata" / "Fonts"
    if not fixture_root.exists():
        fixture_root = project_root / "testdata"
    report = run_ci_benchmarks(fixture_root)

    output_path = Path(args.output) if args.output else None

    if output_path:
        output_path.write_text(
            json.dumps(report.summary, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        print(f"Performance regression report written to: {output_path}")
    else:
        print(json.dumps(report.summary, indent=2, sort_keys=True))

    if report.summary.get("overall_status") == "FAIL":
        sys.exit(1)


def _cmd_one_command_regression(args: argparse.Namespace) -> None:
    """Run CI performance regression for one-command web optimizer."""
    script_dir = Path(__file__).resolve()

    def _find_project_root() -> Path | None:
        for parents_level in range(1, 6):
            candidate = script_dir.parents[parents_level]
            if (candidate / "testdata").exists() and (candidate / "backlog" / "docs" / "perf_thresholds.yml").exists():
                return candidate
        return None

    project_root = _find_project_root()

    if project_root is None:
        for parents_level in range(1, 6):
            candidate = script_dir.parents[parents_level]
            if (candidate / "testdata").exists():
                project_root = candidate
                break

    if project_root is None:
        project_root = script_dir.parents[2]

    thresholds_path = project_root / "backlog" / "docs" / "perf_thresholds.yml"
    fixture_root = project_root / "testdata"

    font_path = fixture_root / "Roboto-VariableFont_wdth,wght.ttf"

    if not font_path.exists():
        _die(f"Font fixture not found at {font_path}")

    if not thresholds_path.exists():
        _die(f"Thresholds file not found at {thresholds_path}")

    report = run_one_command_regression(font_path, thresholds_path)

    output_path = Path(args.output) if args.output else None

    if output_path:
        output_path.write_text(
            json.dumps(report, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        print(f"Performance regression report written to: {output_path}")
    else:
        print(json.dumps(report, indent=2, sort_keys=True))

    if not report.get("passed", False):
        sys.exit(1)


def _cmd_performance_load(args: argparse.Namespace) -> None:
    """Measure font load time using FontLoader.open."""
    font_path = Path(args.font_path)
    if not font_path.exists():
        _die(f"Font file not found: {font_path}")

    load_time_seconds = measure_load_time(font_path)
    load_time_ms = load_time_seconds * 1000

    print(f"{load_time_ms:.1f}")


def _build_animation_report_html(animation: AnimationAsset, preset: str) -> str:
    import html

    return (
        "<!doctype html>\n"
        '<html lang="en">\n'
        "<head>\n"
        '  <meta charset="utf-8">\n'
        '  <meta name="viewport" content="width=device-width, initial-scale=1">\n'
        "  <title>Animation Report</title>\n"
        "  <style>body{font-family:Georgia,serif;max-width:960px;margin:32px auto;padding:0 20px;color:#2a241c;background:#fffdf8} img{max-width:100%;height:auto;border:1px solid #d7c7b1}</style>\n"
        "</head>\n"
        "<body>\n"
        "  <h1>Animation Report</h1>\n"
        f"  <p><strong>Preset:</strong> {html.escape(preset)}</p>\n"
        f"  <p><strong>FPS:</strong> {animation.fps} | <strong>Frames:</strong> {animation.frame_count}</p>\n"
        f'  <p><img src="animation.apng" alt="Animation preview"></p>\n'
        "</body>\n"
        "</html>\n"
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="aspose-font",
        description="Pure-Python font inspection and conversion tool.",
    )
    parser.add_argument("--version", action="version", version=f"aspose-font {__version__}")
    parser.add_argument(
        "--performance-check",
        action="store_true",
        help="Run CI performance regression gating benchmarks and exit with non-zero on failure.",
    )
    parser.add_argument(
        "--perf-output",
        metavar="FILE",
        help="Write performance regression report to this path. Defaults to stdout. Requires --performance-check.",
    )
    subparsers = parser.add_subparsers(dest="command", metavar="command")

    p_info = subparsers.add_parser("info", help="Print font metadata.")
    p_info.add_argument("file", help="Path to font file.")
    p_info.set_defaults(func=_cmd_info)

    p_feature_variations = subparsers.add_parser(
        "feature-variations",
        help="List available OpenType feature variation tags.",
        description="List all available OpenType FeatureVariations tags for a variable font.",
    )
    p_feature_variations.add_argument("file", help="Path to font file.")
    p_feature_variations.set_defaults(func=_cmd_feature_variations)

    p_designspace_coverage = subparsers.add_parser(
        "designspace-coverage",
        help="Generate designspace coverage diagnostic report.",
        description="Generate a designspace coverage diagnostic report for a font against a Unicode preset.",
    )
    p_designspace_coverage.add_argument("file", help="Path to font file.")
    p_designspace_coverage.add_argument(
        "--preset",
        required=True,
        help="Unicode preset (e.g., latin, cyrillic, greek, hebrew, arabic, devanagari, thai).",
    )
    p_designspace_coverage.add_argument(
        "--output",
        required=True,
        metavar="FILE",
        help="Output JSON file path.",
    )
    p_designspace_coverage.set_defaults(func=_cmd_designspace_coverage)

    p_glyphs = subparsers.add_parser("glyphs", help="List glyphs (GID, name, advance width).")
    p_glyphs.add_argument("file", help="Path to font file.")
    p_glyphs.add_argument(
        "--limit",
        type=int,
        default=50,
        metavar="N",
        help="Maximum number of glyphs to list (default: 50).",
    )
    p_glyphs.set_defaults(func=_cmd_glyphs)

    p_conv = subparsers.add_parser("convert", help="Convert font to another format.")
    p_conv.add_argument("file", help="Input font file.")
    p_conv.add_argument("output", help="Output file path.")
    p_conv.add_argument(
        "--to",
        required=True,
        metavar="FORMAT",
        help=f"Target format: {', '.join(_FORMAT_MAP)}.",
    )
    p_conv.set_defaults(func=_cmd_convert)

    p_metrics = subparsers.add_parser("metrics", help="Print full font metrics.")
    p_metrics.add_argument("file", help="Path to font file.")
    p_metrics.set_defaults(func=_cmd_metrics)

    p_perf = subparsers.add_parser(
        "perf-regression",
        help="Run CI performance regression gating benchmarks.",
    )
    p_perf.add_argument(
        "--output",
        help="Write JSON report to this path. Defaults to stdout.",
    )
    p_perf.set_defaults(func=_cmd_perf_regression)

    p_onecmd = subparsers.add_parser(
        "one-command-regress",
        help="Run CI performance regression for one-command web optimizer.",
    )
    p_onecmd.add_argument(
        "--output",
        help="Write JSON report to this path. Defaults to stdout.",
    )
    p_onecmd.set_defaults(func=_cmd_one_command_regression)

    p_load = subparsers.add_parser(
        "performance-load",
        help="Measure font load time.",
    )
    p_load.add_argument("font_path", help="Path to font file.")
    p_load.set_defaults(func=_cmd_performance_load)

    p_qa_report = subparsers.add_parser(
        "qa-report",
        help="Write a JSON and/or HTML font QA report.",
    )
    p_qa_report.add_argument("file", help="Path to font file.")
    p_qa_report.add_argument("--json-output", help="Write the QA report JSON to this path.")
    p_qa_report.add_argument("--html-output", help="Write the QA report HTML to this path.")
    p_qa_report.add_argument(
        "--package-output",
        help="Write a QA report package directory with JSON, HTML, and preview PNG.",
    )
    p_qa_report.add_argument(
        "--preset",
        action="append",
        default=[],
        help="Web coverage preset to evaluate. Repeatable.",
    )
    p_qa_report.add_argument(
        "--text",
        default="",
        help="Extra literal text to evaluate for coverage.",
    )
    p_qa_report.add_argument(
        "--preview-text",
        help="Text to render in the package preview PNG. Defaults to --text or a QA sample.",
    )
    p_qa_report.add_argument(
        "--preview-instance-name",
        help="Named variable-font instance to render in the package preview PNG.",
    )
    p_qa_report.add_argument(
        "--codepoint",
        action="append",
        default=[],
        help="Unicode codepoint to evaluate (decimal or 0x-prefixed). Repeatable.",
    )
    p_qa_report.add_argument(
        "--range",
        action="append",
        default=[],
        help="Unicode range to evaluate in start-end form. Repeatable.",
    )
    p_qa_report.add_argument(
        "--language",
        action="append",
        default=[],
        help="Preferred language tag for variable axis and instance labels. Repeatable.",
    )
    p_qa_report.add_argument(
        "--include-extras",
        action="store_true",
        default=False,
        help="Include compatibility, delta, and size summary in the QA report.",
    )
    p_qa_report.add_argument(
        "--include-decision",
        action="store_true",
        default=False,
        help="Include decision analytics in the QA report (recommended action and rationale).",
    )
    p_qa_report.add_argument(
        "--pdf-summary",
        help="Write a concise PDF summary to this path. Contains title, severity score, and top 3 warnings.",
    )
    p_qa_report.add_argument(
        "--summary",
        action="store_true",
        help="Write a markdown summary (summary.md) to the package output directory.",
    )
    p_qa_report.add_argument(
        "--ci-fast",
        action="store_true",
        default=False,
        help="Enable CI fast mode for performance-sensitive workflows (skips expensive preview rendering).",
    )
    p_qa_report.set_defaults(func=_cmd_qa_report)

    p_qa_full_report = subparsers.add_parser(
        "qa-full-report",
        help="Write a combined JSON/HTML QA report package.",
    )
    p_qa_full_report.add_argument("file", help="Path to font file.")
    p_qa_full_report.add_argument(
        "--output-dir",
        required=True,
        help="Output directory for QA report package.",
    )
    p_qa_full_report.add_argument(
        "--preset",
        action="append",
        default=[],
        help="Web coverage preset to evaluate. Repeatable.",
    )
    p_qa_full_report.add_argument(
        "--text",
        default="",
        help="Extra literal text to evaluate for coverage.",
    )
    p_qa_full_report.add_argument(
        "--preview-text",
        help="Text to render in the package preview PNG. Defaults to --text or a QA sample.",
    )
    p_qa_full_report.add_argument(
        "--preview-instance-name",
        help="Named variable-font instance to render in the package preview PNG.",
    )
    p_qa_full_report.add_argument(
        "--codepoint",
        action="append",
        default=[],
        help="Unicode codepoint to evaluate (decimal or 0x-prefixed). Repeatable.",
    )
    p_qa_full_report.add_argument(
        "--range",
        action="append",
        default=[],
        help="Unicode range to evaluate in start-end form. Repeatable.",
    )
    p_qa_full_report.add_argument(
        "--language",
        action="append",
        default=[],
        help="Preferred language tag for variable axis and instance labels. Repeatable.",
    )
    p_qa_full_report.add_argument(
        "--include-extras",
        action="store_true",
        default=False,
        help="Include compatibility, delta, and size summary in the QA report.",
    )
    p_qa_full_report.add_argument(
        "--include-decision",
        action="store_true",
        default=False,
        help="Include decision analytics in the QA report (recommended action and rationale).",
    )
    p_qa_full_report.set_defaults(func=_cmd_qa_full_report)

    p_qa_decision = subparsers.add_parser(
        "qa-decision-report",
        help="Generate a decision report from QA data.",
    )
    p_qa_decision.add_argument("file", help="Path to font file.")
    p_qa_decision.add_argument(
        "--output",
        required=True,
        help="Output path for decision report JSON.",
    )
    p_qa_decision.add_argument(
        "--package-output",
        help="Output directory for QA package (implies --build-qa-package).",
    )
    p_qa_decision.add_argument(
        "--preset",
        action="append",
        default=[],
        help="Web coverage preset to evaluate. Repeatable.",
    )
    p_qa_decision.add_argument(
        "--text",
        default="",
        help="Extra literal text to evaluate for coverage.",
    )
    p_qa_decision.add_argument(
        "--preview-text",
        help="Text to render in the package preview PNG. Defaults to --text or a QA sample.",
    )
    p_qa_decision.add_argument(
        "--preview-instance-name",
        help="Named variable-font instance to render in the package preview PNG.",
    )
    p_qa_decision.add_argument(
        "--codepoint",
        action="append",
        default=[],
        help="Unicode codepoint to evaluate (decimal or 0x-prefixed). Repeatable.",
    )
    p_qa_decision.add_argument(
        "--range",
        action="append",
        default=[],
        help="Unicode range to evaluate in start-end form. Repeatable.",
    )
    p_qa_decision.add_argument(
        "--language",
        action="append",
        default=[],
        help="Preferred language tag for variable axis and instance labels. Repeatable.",
    )
    p_qa_decision.set_defaults(func=_cmd_decision_report)

    p_meta_clean = subparsers.add_parser(
        "meta-clean",
        help="Strip unused metadata tables and legacy Mac name records.",
    )
    p_meta_clean.add_argument("file", help="Input font file.")
    p_meta_clean.add_argument("output", help="Output font file.")
    p_meta_clean.add_argument(
        "--keep-mac-names",
        action="store_true",
        help="Preserve platform_id=1 name records.",
    )
    p_meta_clean.add_argument(
        "--keep-legacy-tables",
        action="store_true",
        help="Preserve legacy DSIG tables.",
    )
    p_meta_clean.set_defaults(func=_cmd_meta_clean)

    p_web = subparsers.add_parser("web-build", help="Generate a web font bundle.")

    # New subcommand: web-decision-report
    p_web_decision_report = subparsers.add_parser(
        "web-decision-report",
        help="Generate decision report JSON from optimizer output.",
        description="Provide the source font and the optimizer output directory to produce a concise decision report.",
    )
    p_web_decision_report.add_argument("file", help="Input font file path.")
    p_web_decision_report.add_argument("output_dir", help="Directory containing optimizer output (optimizer-manifest.json).")
    p_web_decision_report.add_argument(
        "--output",
        help="Write the decision report JSON to this path (default: stdout).",
    )
    p_web_decision_report.set_defaults(func=_cmd_web_decision_report)

    p_web.add_argument("file", help="Input font file.")
    p_web.add_argument("output_dir", help="Output directory for bundle files.")
    p_web.add_argument("--stem", help="Custom output file stem.")
    p_web.add_argument(
        "--preview-text",
        default="Hamburgefons 0123456789",
        help="Preview text for the generated specimen HTML.",
    )
    p_web.add_argument(
        "--template",
        choices=("classic", "editorial", "lab"),
        default="classic",
        help="Specimen template to use for generated HTML/CSS (default: classic).",
    )
    p_web.add_argument(
        "--variable-mode",
        choices=("auto", "live", "static"),
        default="auto",
        help="How to export variable fonts: auto (default), live, or static.",
    )
    p_web.add_argument(
        "--naming-strategy",
        choices=_NAMING_STRATEGY_CHOICES,
        default="instance-family",
        help="Naming policy for static variable-font web exports (default: instance-family).",
    )
    p_web.add_argument(
        "--family-suffix",
        help="Optional custom suffix to append to generated family names for conflict-safe output.",
    )
    _add_naming_override_args(p_web)
    _add_stat_policy_arg(p_web)
    p_web.add_argument(
        "--no-woff",
        action="store_true",
        help="Do not emit WOFF fallback output.",
    )
    p_web.add_argument(
        "--preset",
        action="append",
        default=[],
        help="Subset preset name. Repeatable.",
    )
    p_web.add_argument(
        "--text",
        default="",
        help="Extra literal text to retain in the subset.",
    )
    p_web.add_argument(
        "--codepoint",
        action="append",
        default=[],
        help="Unicode codepoint to retain (decimal or 0x-prefixed). Repeatable.",
    )
    p_web.add_argument(
        "--range",
        action="append",
        default=[],
        help="Unicode range to retain in start-end form. Repeatable.",
    )
    p_web.add_argument(
        "--instance",
        action="append",
        default=[],
        help="Variable-font axis coordinate in tag=value form. Repeatable.",
    )
    p_web.add_argument(
        "--instance-name",
        help="Named instance label to export directly.",
    )
    p_web.add_argument(
        "--preserve-variable",
        action="store_true",
        help="When subsetting a variable font, preserve variable font tables (fvar, gvar, STAT, etc.) "
        "instead of converting to a static instance.",
    )
    p_web.set_defaults(func=_cmd_web_build)

    p_web_optimize = subparsers.add_parser(
        "web-optimize",
        help="Generate an optimized web font handoff package with readiness evidence.",
        epilog="Documentation: https://github.com/aspose-font-foss/Aspose.Font-FOSS-for-Python/blob/main/docs/one_command_web_optimizer.md",
    )
    p_web_optimize.add_argument(
        "file", nargs="?", help="Input font file (optional with --example-output)."
    )
    p_web_optimize.add_argument(
        "output_dir",
        nargs="?",
        help="Output directory for optimizer files (optional with --example-output).",
    )
    p_web_optimize.add_argument("--stem", help="Custom output file stem.")
    p_web_optimize.add_argument(
        "--preview-text",
        default="Hamburgefons 0123456789",
        help="Preview text for the generated specimen HTML.",
    )
    p_web_optimize.add_argument(
        "--template",
        choices=("classic", "editorial", "lab"),
        default="classic",
        help="Specimen template to use for generated HTML/CSS (default: classic).",
    )
    p_web_optimize.add_argument(
        "--variable-mode",
        choices=("auto", "live", "static"),
        default="auto",
        help="How to export variable fonts: auto (default), live, or static.",
    )
    p_web_optimize.add_argument(
        "--naming-strategy",
        choices=_NAMING_STRATEGY_CHOICES,
        default="instance-family",
        help="Naming policy for static variable-font web exports (default: instance-family).",
    )
    p_web_optimize.add_argument(
        "--family-suffix",
        help="Optional custom suffix to append to generated family names for conflict-safe output.",
    )
    _add_naming_override_args(p_web_optimize)
    _add_stat_policy_arg(p_web_optimize)
    p_web_optimize.add_argument(
        "--no-woff",
        action="store_true",
        help="Do not emit WOFF fallback output.",
    )
    p_web_optimize.add_argument(
        "--preset",
        action="append",
        default=[],
        help="Subset preset name. Repeatable.",
    )
    p_web_optimize.add_argument(
        "--text",
        default="",
        help="Extra literal text to retain in the subset.",
    )
    p_web_optimize.add_argument(
        "--codepoint",
        action="append",
        default=[],
        help="Unicode codepoint to retain (decimal or 0x-prefixed). Repeatable.",
    )
    p_web_optimize.add_argument(
        "--range",
        action="append",
        default=[],
        help="Unicode range to retain in start-end form. Repeatable.",
    )
    p_web_optimize.add_argument(
        "--instance",
        action="append",
        default=[],
        help="Variable-font axis coordinate in tag=value form. Repeatable.",
    )
    p_web_optimize.add_argument(
        "--instance-name",
        help="Named instance label to export directly.",
    )
    p_web_optimize.add_argument(
        "--performance-report",
        action="store_true",
        help="Enable detailed performance timing profiling in the optimizer manifest. "
        "Adds load_time_ms, subset_time_ms, compress_time_ms, manifest_write_time_ms "
        "to the performance block.",
    )
    p_web_optimize.add_argument(
        "--include-performance",
        action="store_true",
        help="Include detailed performance timing breakdown in the optimizer manifest. "
        "Adds total_seconds, size_summary_seconds, css_generation_seconds, "
        "specimen_html_seconds to the performance block.",
    )
    p_web_optimize.add_argument(
        "--decision-report",
        nargs="?",
        const="decision-report.json",
        help="Generate a decision report explaining the chosen export mode. "
             "Write to decision-report.json by default, or specify a path for custom output.",
    )
    p_web_optimize.add_argument(
        "--decision",
        type=str,
        choices=("auto", "live", "static", "static-fallback"),
        default="auto",
        help="Explicit decision for export mode: auto (default), live, static, or static-fallback.",
    )
    p_web_optimize.add_argument(
        "--cdn-manifest",
        action="store_true",
        help="Generate CDN manifest (cdn-manifest.json) alongside web font output.",
    )
    p_web_optimize.add_argument(
        "--cdn-base",
        default="https://cdn.example.com",
        help="Base URL for CDN paths in the manifest (default: https://cdn.example.com).",
    )
    p_web_optimize.add_argument(
        "--preserve-variable",
        action="store_true",
        help="When subsetting a variable font, preserve variable font tables (fvar, gvar, STAT, etc.) "
             "instead of converting to a static instance.",
    )
    p_web_optimize.add_argument(
        "--summary",
        action="store_true",
        help="Generate summary.md in output directory.",
    )
    p_web_optimize.add_argument(
        "--readme-example",
        action="store_true",
        help="Generate example.html with optimizer summary and specimen embed.",
    )
    p_web_optimize.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output including decision report details.",
    )
    p_web_optimize.add_argument(
        "--html-summary",
        action="store_true",
        help="Write HTML decision report (decision-report.html) alongside JSON report.",
    )
    p_web_optimize.add_argument(
        "--feature-variation",
        metavar="TAG",
        help="Select a named feature variation to apply during optimization. "
             "Use 'feature-variations' subcommand to list available tags.",
    )
    p_web_optimize.add_argument(
        "--decision-report-pdf",
        "--pdf-report",
        type=str,
        metavar="PATH",
        dest="decision_report_pdf",
        help="Write PDF decision report to the specified path.",
    )
    p_web_optimize.add_argument(
        "--example-output",
        action="store_true",
        help="Write example optimizer manifest to stdout instead of processing a font.",
    )
    p_web_optimize.add_argument(
        "--split-ranges",
        metavar="RANGES",
        action="append",
        default=[],
        help=(
            "Slice font by Unicode ranges. Format: NAME:START-END (repeatable). "
            "Example: --split-ranges latin:U+0000-00FF --split-ranges cyrillic:U+0400-04FF. "
            "A composite fonts.css will be written alongside individual range chunks."
        ),
    )
    p_web_optimize.set_defaults(func=_cmd_web_optimize)

    # One-command optimizer: runs full workflow without decision/report extras
    p_web_opt_one = subparsers.add_parser(
        "web-optimize-one",
        help="Run full web-font optimizer in a single step (no decision/report).",
    )
    p_web_opt_one.add_argument(
        "file", nargs="?", help="Input font file (required)."
    )
    p_web_opt_one.add_argument(
        "output_dir",
        nargs="?",
        help="Destination directory for the optimizer package (required).",
    )
    p_web_opt_one.add_argument("--stem", help="Custom output file stem.")
    p_web_opt_one.add_argument(
        "--preview-text",
        default="Hamburgefons 0123456789",
        help="Preview text for generated specimen HTML.",
    )
    p_web_opt_one.add_argument(
        "--template",
        choices=("classic", "editorial", "lab"),
        default="classic",
        help="Specimen template for HTML/CSS.",
    )
    p_web_opt_one.add_argument(
        "--variable-mode",
        choices=("auto", "live", "static"),
        default="auto",
        help="Variable export mode.",
    )
    p_web_opt_one.add_argument(
        "--naming-strategy",
        choices=_NAMING_STRATEGY_CHOICES,
        default="instance-family",
        help="Naming policy for static outputs.",
    )
    p_web_opt_one.add_argument("--family-suffix", help="Custom suffix for family names.")
    _add_naming_override_args(p_web_opt_one)
    _add_stat_policy_arg(p_web_opt_one)
    p_web_opt_one.add_argument(
        "--no-woff",
        action="store_true",
        help="Do not emit WOFF fallback output.",
    )
    p_web_opt_one.add_argument(
        "--preset",
        action="append",
        default=[],
        help="Subset preset name. Repeatable.",
    )
    p_web_opt_one.add_argument("--text", default="", help="Extra literal text to retain in the subset.")
    p_web_opt_one.add_argument(
        "--codepoint",
        action="append",
        default=[],
        help="Unicode codepoint to retain (decimal or 0x-prefixed). Repeatable.",
    )
    p_web_opt_one.add_argument(
        "--range",
        action="append",
        default=[],
        help="Unicode range to retain in start-end form. Repeatable.",
    )
    p_web_opt_one.add_argument(
        "--instance",
        action="append",
        default=[],
        help="Variable-font axis coordinate in tag=value form. Repeatable.",
    )
    p_web_opt_one.add_argument("--instance-name", help="Named instance label to export directly.")
    p_web_opt_one.add_argument(
        "--preserve-variable",
        action="store_true",
        help="Preserve variable tables when subsetting variable fonts.",
    )
    p_web_opt_one.set_defaults(func=_cmd_web_optimize_one)

    p_web_optimize_demo = subparsers.add_parser(
        "web-optimize-demo",
        help="Run Web Font Optimizer on bundled demo font and print output path.",
        description="Run Web Font Optimizer on the bundled demo font (testdata/Roboto-VariableFont_wdth,wght.ttf), producing a ready-to-show web font handoff package in a temporary directory and printing the output directory path with size summary.",
    )
    p_web_optimize_demo.set_defaults(func=_cmd_web_optimize_demo)

    p_decision_report = subparsers.add_parser(
        "decision-report",
        help="Report variable font export decision (live/static/static_fallback) for Web Font Optimizer.",
    )
    p_decision_report.add_argument(
        "file",
        help="Input font file path.",
    )
    p_decision_report.add_argument(
        "--variable-mode",
        choices=("live", "static", "auto"),
        default="auto",
        help="Requested variable export mode (default: auto).",
    )
    p_decision_report.set_defaults(func=_cmd_decision_report_cli)

    p_web_optim_summary = subparsers.add_parser(
        "web-optim-summary",
        help="Generate a markdown summary of the Web Font Optimizer output",
    )
    p_web_optim_summary.add_argument("file", help="Input font file path")
    p_web_optim_summary.add_argument(
        "--output",
        help="Output file (default: stdout)",
    )
    p_web_optim_summary.add_argument(
        "--stem",
        help="Custom output file stem.",
    )
    p_web_optim_summary.add_argument(
        "--preview-text",
        default="Hamburgefons 0123456789",
        help="Preview text for the generated specimen HTML.",
    )
    p_web_optim_summary.add_argument(
        "--template",
        choices=("classic", "editorial", "lab"),
        default="classic",
        help="Specimen template to use for generated HTML/CSS (default: classic).",
    )
    p_web_optim_summary.add_argument(
        "--variable-mode",
        choices=("auto", "live", "static"),
        default="auto",
        help="How to export variable fonts: auto (default), live, or static.",
    )
    p_web_optim_summary.add_argument(
        "--naming-strategy",
        choices=_NAMING_STRATEGY_CHOICES,
        default="instance-family",
        help="Naming policy for static variable-font web exports (default: instance-family).",
    )
    p_web_optim_summary.add_argument(
        "--family-suffix",
        help="Optional custom suffix to append to generated family names for conflict-safe output.",
    )
    _add_naming_override_args(p_web_optim_summary)
    _add_stat_policy_arg(p_web_optim_summary)
    p_web_optim_summary.add_argument(
        "--no-woff",
        action="store_true",
        help="Do not emit WOFF fallback output.",
    )
    p_web_optim_summary.add_argument(
        "--preset",
        action="append",
        default=[],
        help="Subset preset name. Repeatable.",
    )
    p_web_optim_summary.add_argument(
        "--text",
        default="",
        help="Extra literal text to retain in the subset.",
    )
    p_web_optim_summary.add_argument(
        "--codepoint",
        action="append",
        default=[],
        help="Unicode codepoint to retain (decimal or 0x-prefixed). Repeatable.",
    )
    p_web_optim_summary.add_argument(
        "--range",
        action="append",
        default=[],
        help="Unicode range to retain in start-end form. Repeatable.",
    )
    p_web_optim_summary.add_argument(
        "--instance",
        action="append",
        default=[],
        help="Variable-font axis coordinate in tag=value form. Repeatable.",
    )
    p_web_optim_summary.add_argument(
        "--instance-name",
        help="Named instance label to export directly.",
    )
    p_web_optim_summary.set_defaults(func=_cmd_web_optim_summary)

    p_batch = subparsers.add_parser(
        "batch-workflow",
        help="Process multiple fonts in a directory with full pipeline (optimizer, QA, instances).",
    )
    p_batch.add_argument(
        "input_dir",
        help="Input directory containing font files to process.",
    )
    p_batch.add_argument(
        "output_dir",
        help="Output directory for generated packages (per-font subdirectories created).",
    )
    p_batch.add_argument(
        "--naming-strategy",
        choices=_NAMING_STRATEGY_CHOICES,
        default="instance-family",
        help="Naming policy for static variable-font exports (default: instance-family).",
    )
    p_batch.add_argument(
        "--stat-policy",
        choices=_STAT_POLICY_CHOICES,
        default="drop",
        help="STAT metadata policy for generated static instances (default: drop).",
    )
    p_batch.add_argument(
        "--preview-text",
        default="Hamburgefons 0123456789",
        help="Preview text for generated PNGs (default: Hamburgefons 0123456789).",
    )
    p_batch.set_defaults(func=_cmd_batch_workflow)

    p_preview = subparsers.add_parser("preview", help="Render a PNG text preview.")
    p_preview.add_argument("file", help="Input font file.")
    p_preview.add_argument("output", help="Output PNG file path.")
    p_preview.add_argument(
        "--text",
        default="Hamburgefons 0123456789",
        help="Preview text to render.",
    )
    p_preview.add_argument(
        "--size",
        type=float,
        default=72.0,
        help="Preview size in font units scaled to pixels.",
    )
    p_preview.add_argument(
        "--padding",
        type=int,
        default=12,
        help="Canvas padding in pixels.",
    )
    p_preview.add_argument(
        "--no-antialias",
        action="store_true",
        help="Disable 4x supersampling antialiasing.",
    )
    p_preview.add_argument(
        "--format",
        choices=("png", "svg"),
        default="png",
        help="Preview output format (default: png).",
    )
    p_preview.add_argument("--stem", help="Custom preview filename stem.")
    p_preview.add_argument(
        "--instance",
        action="append",
        default=[],
        help="Variable-font axis coordinate in tag=value form. Repeatable.",
    )
    p_preview.add_argument(
        "--instance-name",
        help="Named instance label to render directly.",
    )
    p_preview.set_defaults(func=_cmd_preview)

    p_preview_batch = subparsers.add_parser(
        "preview-batch", help="Render multiple PNG previews from a variable font."
    )
    p_preview_batch.add_argument("file", help="Variable font file.")
    p_preview_batch.add_argument("output_dir", help="Output directory for generated PNG previews.")
    p_preview_batch.add_argument(
        "--instance-name",
        action="append",
        default=[],
        help="Named instance label to render. Repeatable.",
    )
    p_preview_batch.add_argument(
        "--all-named",
        action="store_true",
        help="Render previews for all named instances from the font.",
    )
    p_preview_batch.add_argument(
        "--include-default",
        action="store_true",
        help="Also render the default coordinates.",
    )
    p_preview_batch.add_argument(
        "--text",
        default="Hamburgefons 0123456789",
        help="Preview text to render.",
    )
    p_preview_batch.add_argument(
        "--size",
        type=float,
        default=72.0,
        help="Preview size in font units scaled to pixels.",
    )
    p_preview_batch.add_argument(
        "--padding",
        type=int,
        default=12,
        help="Canvas padding in pixels.",
    )
    p_preview_batch.add_argument(
        "--no-antialias",
        action="store_true",
        help="Disable 4x supersampling antialiasing.",
    )
    p_preview_batch.add_argument(
        "--format",
        choices=("png", "svg"),
        default="png",
        help="Preview output format for generated files (default: png).",
    )
    p_preview_batch.set_defaults(func=_cmd_preview_batch)

    p_preview_animation = subparsers.add_parser(
        "preview-animation", help="Render an Animated PNG (APNG) sweeping a variable-font axis."
    )
    p_preview_animation.add_argument("file", help="Variable font file.")
    p_preview_animation.add_argument("output", help="Output APNG file path.")
    p_preview_animation.add_argument(
        "--axis",
        required=True,
        help="Primary variable axis tag to sweep.",
    )
    p_preview_animation.add_argument(
        "--start",
        type=float,
        required=True,
        help="Start coordinate on the axis.",
    )
    p_preview_animation.add_argument(
        "--end",
        type=float,
        required=True,
        help="End coordinate on the axis.",
    )
    p_preview_animation.add_argument(
        "--frames",
        type=int,
        help="Number of frames for the sweep segment. Defaults come from the selected preset.",
    )
    p_preview_animation.add_argument(
        "--fps",
        type=int,
        help="Frames per second. Defaults come from the selected preset.",
    )
    p_preview_animation.add_argument(
        "--bounce",
        action="store_true",
        help="Bounce the animation back and forth to create a seamless loop.",
    )
    p_preview_animation.add_argument(
        "--text",
        default="Hamburgefons 0123456789",
        help="Preview text to render.",
    )
    p_preview_animation.add_argument(
        "--size",
        type=float,
        help="Preview size in font units scaled to pixels. Defaults come from the selected preset.",
    )
    p_preview_animation.add_argument(
        "--padding",
        type=int,
        help="Canvas padding in pixels. Defaults come from the selected preset.",
    )
    p_preview_animation.add_argument(
        "--no-antialias",
        action="store_true",
        help="Disable 4x supersampling antialiasing.",
    )
    p_preview_animation.add_argument(
        "--preset",
        choices=AnimationPreviewBuilder.available_presets(),
        default="standard",
        help="Animation export preset (default: standard).",
    )
    p_preview_animation.add_argument(
        "--easing",
        choices=("linear", "ease-in", "ease-out", "ease-in-out"),
        default="linear",
        help="Interpolation easing between animation states (default: linear).",
    )
    p_preview_animation.add_argument(
        "--caption-mode",
        choices=("none", "labels", "coordinates", "both"),
        default="labels",
        help="Frame caption mode baked into the APNG (default: labels).",
    )
    p_preview_animation.add_argument("--stem", help="Custom preview filename stem.")
    p_preview_animation.set_defaults(func=_cmd_preview_animation)

    p_preview_animation_path = subparsers.add_parser(
        "preview-animation-path",
        help="Render an Animated PNG (APNG) along a scripted variable-font path.",
    )
    p_preview_animation_path.add_argument("file", help="Variable font file.")
    p_preview_animation_path.add_argument("output", help="Output APNG file path.")
    p_preview_animation_path.add_argument(
        "--state",
        action="append",
        default=[],
        help="Path state as a named instance label or comma-separated axis assignments like wght=400,wdth=75. Repeatable.",
    )
    p_preview_animation_path.add_argument(
        "--frames-per-segment",
        type=int,
        help="Interpolated frames per path segment. Defaults come from the selected preset.",
    )
    p_preview_animation_path.add_argument(
        "--hold-frames",
        type=int,
        default=0,
        help="Extra duplicate frames to hold on each waypoint (default: 0).",
    )
    p_preview_animation_path.add_argument(
        "--fps",
        type=int,
        help="Frames per second. Defaults come from the selected preset.",
    )
    p_preview_animation_path.add_argument(
        "--bounce",
        action="store_true",
        help="Bounce the animation back and forth to create a seamless loop.",
    )
    p_preview_animation_path.add_argument(
        "--text",
        default="Hamburgefons 0123456789",
        help="Preview text to render.",
    )
    p_preview_animation_path.add_argument(
        "--size",
        type=float,
        help="Preview size in font units scaled to pixels. Defaults come from the selected preset.",
    )
    p_preview_animation_path.add_argument(
        "--padding",
        type=int,
        help="Canvas padding in pixels. Defaults come from the selected preset.",
    )
    p_preview_animation_path.add_argument(
        "--no-antialias",
        action="store_true",
        help="Disable 4x supersampling antialiasing.",
    )
    p_preview_animation_path.add_argument(
        "--preset",
        choices=AnimationPreviewBuilder.available_presets(),
        default="standard",
        help="Animation export preset (default: standard).",
    )
    p_preview_animation_path.add_argument(
        "--easing",
        choices=("linear", "ease-in", "ease-out", "ease-in-out"),
        default="linear",
        help="Interpolation easing between path waypoints (default: linear).",
    )
    p_preview_animation_path.add_argument(
        "--caption-mode",
        choices=("none", "labels", "coordinates", "both"),
        default="labels",
        help="Frame caption mode baked into the APNG (default: labels).",
    )
    p_preview_animation_path.add_argument("--stem", help="Custom preview filename stem.")
    p_preview_animation_path.set_defaults(func=_cmd_preview_animation_path)

    p_preview_animation_path_package = subparsers.add_parser(
        "preview-animation-path-package",
        help="Export a scripted variable-font animation as PNG frames, a storyboard sheet, and a manifest package.",
    )
    p_preview_animation_path_package.add_argument("file", help="Variable font file.")
    p_preview_animation_path_package.add_argument("output_dir", help="Output directory path.")
    p_preview_animation_path_package.add_argument(
        "--state",
        action="append",
        default=[],
        help="Path state as a named instance label or comma-separated axis assignments like wght=400,wdth=75. Repeatable.",
    )
    p_preview_animation_path_package.add_argument(
        "--frames-per-segment",
        type=int,
        help="Interpolated frames per path segment. Defaults come from the selected preset.",
    )
    p_preview_animation_path_package.add_argument(
        "--hold-frames",
        type=int,
        default=0,
        help="Extra duplicate frames to hold on each waypoint (default: 0).",
    )
    p_preview_animation_path_package.add_argument(
        "--fps",
        type=int,
        help="Frames per second recorded in the manifest. Defaults come from the selected preset.",
    )
    p_preview_animation_path_package.add_argument(
        "--bounce",
        action="store_true",
        help="Bounce the animation back and forth to create a seamless loop.",
    )
    p_preview_animation_path_package.add_argument(
        "--text",
        default="Hamburgefons 0123456789",
        help="Preview text to render.",
    )
    p_preview_animation_path_package.add_argument(
        "--size",
        type=float,
        help="Preview size in font units scaled to pixels. Defaults come from the selected preset.",
    )
    p_preview_animation_path_package.add_argument(
        "--padding",
        type=int,
        help="Canvas padding in pixels. Defaults come from the selected preset.",
    )
    p_preview_animation_path_package.add_argument(
        "--no-antialias",
        action="store_true",
        help="Disable 4x supersampling antialiasing.",
    )
    p_preview_animation_path_package.add_argument(
        "--preset",
        choices=AnimationPreviewBuilder.available_presets(),
        default="standard",
        help="Animation export preset (default: standard).",
    )
    p_preview_animation_path_package.add_argument(
        "--easing",
        choices=("linear", "ease-in", "ease-out", "ease-in-out"),
        default="linear",
        help="Interpolation easing between path waypoints (default: linear).",
    )
    p_preview_animation_path_package.add_argument(
        "--caption-mode",
        choices=("none", "labels", "coordinates", "both"),
        default="labels",
        help="Frame caption mode baked into the PNG frames (default: labels).",
    )
    p_preview_animation_path_package.add_argument("--stem", help="Custom export filename stem.")
    p_preview_animation_path_package.set_defaults(func=_cmd_preview_animation_path_package)

    p_preview_animation_path_review = subparsers.add_parser(
        "preview-animation-path-review",
        help="Export a presentation-ready scripted animation review package with frames, storyboard, Markdown, HTML, and manifest output.",
    )
    p_preview_animation_path_review.add_argument("file", help="Variable font file.")
    p_preview_animation_path_review.add_argument("output_dir", help="Output directory path.")
    p_preview_animation_path_review.add_argument(
        "--state",
        action="append",
        default=[],
        help="Path state as a named instance label or comma-separated axis assignments like wght=400,wdth=75. Repeatable.",
    )
    p_preview_animation_path_review.add_argument(
        "--frames-per-segment",
        type=int,
        help="Interpolated frames per path segment. Defaults come from the selected preset.",
    )
    p_preview_animation_path_review.add_argument(
        "--hold-frames",
        type=int,
        default=0,
        help="Extra duplicate frames to hold on each waypoint (default: 0).",
    )
    p_preview_animation_path_review.add_argument(
        "--fps",
        type=int,
        help="Frames per second recorded in the manifest. Defaults come from the selected preset.",
    )
    p_preview_animation_path_review.add_argument(
        "--bounce",
        action="store_true",
        help="Bounce the animation back and forth to create a seamless loop.",
    )
    p_preview_animation_path_review.add_argument(
        "--text",
        default="Hamburgefons 0123456789",
        help="Preview text to render.",
    )
    p_preview_animation_path_review.add_argument(
        "--size",
        type=float,
        help="Preview size in font units scaled to pixels. Defaults come from the selected preset.",
    )
    p_preview_animation_path_review.add_argument(
        "--padding",
        type=int,
        help="Canvas padding in pixels. Defaults come from the selected preset.",
    )
    p_preview_animation_path_review.add_argument(
        "--no-antialias",
        action="store_true",
        help="Disable 4x supersampling antialiasing.",
    )
    p_preview_animation_path_review.add_argument(
        "--preset",
        choices=AnimationPreviewBuilder.available_presets(),
        default="standard",
        help="Animation export preset (default: standard).",
    )
    p_preview_animation_path_review.add_argument(
        "--easing",
        choices=("linear", "ease-in", "ease-out", "ease-in-out"),
        default="linear",
        help="Interpolation easing between path waypoints (default: linear).",
    )
    p_preview_animation_path_review.add_argument(
        "--caption-mode",
        choices=("none", "labels", "coordinates", "both"),
        default="labels",
        help="Frame caption mode baked into the PNG frames (default: labels).",
    )
    p_preview_animation_path_review.add_argument("--stem", help="Custom export filename stem.")
    p_preview_animation_path_review.set_defaults(func=_cmd_preview_animation_path_review)

    p_preview_animation_path_showcase = subparsers.add_parser(
        "preview-animation-path-showcase",
        help="Export a shareable scripted animation showcase package with APNG, storyboard, review files, and manifest output.",
    )
    p_preview_animation_path_showcase.add_argument("file", help="Variable font file.")
    p_preview_animation_path_showcase.add_argument("output_dir", help="Output directory path.")
    p_preview_animation_path_showcase.add_argument(
        "--state",
        action="append",
        default=[],
        help="Path state as a named instance label or comma-separated axis assignments like wght=400,wdth=75. Repeatable.",
    )
    p_preview_animation_path_showcase.add_argument(
        "--frames-per-segment",
        type=int,
        help="Interpolated frames per path segment. Defaults come from the selected preset.",
    )
    p_preview_animation_path_showcase.add_argument(
        "--hold-frames",
        type=int,
        default=0,
        help="Extra duplicate frames to hold on each waypoint (default: 0).",
    )
    p_preview_animation_path_showcase.add_argument(
        "--fps",
        type=int,
        help="Frames per second recorded in the exported APNG and manifests. Defaults come from the selected preset.",
    )
    p_preview_animation_path_showcase.add_argument(
        "--bounce",
        action="store_true",
        help="Bounce the animation back and forth to create a seamless loop.",
    )
    p_preview_animation_path_showcase.add_argument(
        "--text",
        default="Hamburgefons 0123456789",
        help="Preview text to render.",
    )
    p_preview_animation_path_showcase.add_argument(
        "--size",
        type=float,
        help="Preview size in font units scaled to pixels. Defaults come from the selected preset.",
    )
    p_preview_animation_path_showcase.add_argument(
        "--padding",
        type=int,
        help="Canvas padding in pixels. Defaults come from the selected preset.",
    )
    p_preview_animation_path_showcase.add_argument(
        "--no-antialias",
        action="store_true",
        help="Disable 4x supersampling antialiasing.",
    )
    p_preview_animation_path_showcase.add_argument(
        "--preset",
        choices=AnimationPreviewBuilder.available_presets(),
        default="standard",
        help="Animation export preset (default: standard).",
    )
    p_preview_animation_path_showcase.add_argument(
        "--easing",
        choices=("linear", "ease-in", "ease-out", "ease-in-out"),
        default="linear",
        help="Interpolation easing between path waypoints (default: linear).",
    )
    p_preview_animation_path_showcase.add_argument(
        "--caption-mode",
        choices=("none", "labels", "coordinates", "both"),
        default="labels",
        help="Frame caption mode baked into the PNG/APNG outputs (default: labels).",
    )
    p_preview_animation_path_showcase.add_argument("--stem", help="Custom export filename stem.")
    p_preview_animation_path_showcase.set_defaults(func=_cmd_preview_animation_path_showcase)

    p_animation_export = subparsers.add_parser(
        "animation-export",
        help="Export animation as production-ready APNG with JSON manifest.",
    )
    p_animation_export.add_argument("file", help="Variable font file.")
    p_animation_export.add_argument(
        "--output-dir",
        required=True,
        help="Output directory for animation APNG and manifest.json.",
    )
    p_animation_export.add_argument(
        "--axis",
        required=True,
        help="Primary variable axis tag to sweep.",
    )
    p_animation_export.add_argument(
        "--start",
        type=float,
        required=True,
        help="Start coordinate on the axis.",
    )
    p_animation_export.add_argument(
        "--end",
        type=float,
        required=True,
        help="End coordinate on the axis.",
    )
    p_animation_export.add_argument(
        "--frames",
        type=int,
        help="Number of frames for the sweep segment. Defaults come from the selected preset.",
    )
    p_animation_export.add_argument(
        "--fps",
        type=int,
        help="Frames per second. Defaults come from the selected preset.",
    )
    p_animation_export.add_argument(
        "--bounce",
        action="store_true",
        help="Bounce the animation back and forth to create a seamless loop.",
    )
    p_animation_export.add_argument(
        "--text",
        default="Hamburgefons 0123456789",
        help="Preview text to render.",
    )
    p_animation_export.add_argument(
        "--size",
        type=float,
        help="Preview size in font units scaled to pixels. Defaults come from the selected preset.",
    )
    p_animation_export.add_argument(
        "--padding",
        type=int,
        help="Canvas padding in pixels. Defaults come from the selected preset.",
    )
    p_animation_export.add_argument(
        "--no-antialias",
        action="store_true",
        help="Disable 4x supersampling antialiasing.",
    )
    p_animation_export.add_argument(
        "--preset",
        choices=AnimationPreviewBuilder.available_presets(),
        default="standard",
        help="Animation export preset (default: standard).",
    )
    p_animation_export.add_argument(
        "--easing",
        choices=("linear", "ease-in", "ease-out", "ease-in-out"),
        default="linear",
        help="Interpolation easing between animation states (default: linear).",
    )
    p_animation_export.add_argument(
        "--caption-mode",
        choices=("none", "labels", "coordinates", "both"),
        default="labels",
        help="Frame caption mode baked into the APNG (default: labels).",
    )
    p_animation_export.add_argument("--stem", help="Custom preview filename stem.")
    p_animation_export.set_defaults(func=_cmd_animation_export)

    p_animation_report = subparsers.add_parser(
        "animation-report",
        help="Generate an animation APNG and HTML report in a single output directory.",
    )
    p_animation_report.add_argument("file", help="Variable font file.")
    p_animation_report.add_argument(
        "--output-dir",
        required=True,
        help="Output directory for animation.apng and report.html.",
    )
    p_animation_report.add_argument(
        "--axis",
        required=True,
        help="Primary variable axis tag to sweep.",
    )
    p_animation_report.add_argument(
        "--start",
        type=float,
        required=True,
        help="Start coordinate on the axis.",
    )
    p_animation_report.add_argument(
        "--end",
        type=float,
        required=True,
        help="End coordinate on the axis.",
    )
    p_animation_report.add_argument(
        "--frames",
        type=int,
        help="Number of frames for the sweep segment. Defaults come from the selected preset.",
    )
    p_animation_report.add_argument(
        "--fps",
        type=int,
        help="Frames per second. Defaults come from the selected preset.",
    )
    p_animation_report.add_argument(
        "--bounce",
        action="store_true",
        help="Bounce the animation back and forth to create a seamless loop.",
    )
    p_animation_report.add_argument(
        "--text",
        default="Hamburgefons 0123456789",
        help="Preview text to render.",
    )
    p_animation_report.add_argument(
        "--size",
        type=float,
        help="Preview size in font units scaled to pixels. Defaults come from the selected preset.",
    )
    p_animation_report.add_argument(
        "--padding",
        type=int,
        help="Canvas padding in pixels. Defaults come from the selected preset.",
    )
    p_animation_report.add_argument(
        "--no-antialias",
        action="store_true",
        help="Disable 4x supersampling antialiasing.",
    )
    p_animation_report.add_argument(
        "--preset",
        choices=AnimationPreviewBuilder.available_presets(),
        default="standard",
        help="Animation export preset (default: standard).",
    )
    p_animation_report.add_argument(
        "--easing",
        choices=("linear", "ease-in", "ease-out", "ease-in-out"),
        default="linear",
        help="Interpolation easing between animation states (default: linear).",
    )
    p_animation_report.add_argument(
        "--caption-mode",
        choices=("none", "labels", "coordinates", "both"),
        default="labels",
        help="Frame caption mode baked into the APNG (default: labels).",
    )
    p_animation_report.set_defaults(func=_cmd_animation_report)

    p_preview_grid = subparsers.add_parser(
        "preview-grid", help="Render axis-grid PNG previews from a variable font."
    )
    p_preview_grid.add_argument("file", help="Variable font file.")
    p_preview_grid.add_argument("output_dir", help="Output directory for generated PNG previews.")
    p_preview_grid.add_argument(
        "--axis",
        required=True,
        help="Primary variable axis tag to sweep.",
    )
    p_preview_grid.add_argument(
        "--value",
        action="append",
        default=[],
        help="Primary axis value. Repeatable.",
    )
    p_preview_grid.add_argument(
        "--axis2",
        help="Optional secondary variable axis tag.",
    )
    p_preview_grid.add_argument(
        "--value2",
        action="append",
        default=[],
        help="Secondary axis value. Repeatable.",
    )
    p_preview_grid.add_argument(
        "--use-presets",
        action="store_true",
        help="Use suggested preset values for the primary axis when --value is omitted.",
    )
    p_preview_grid.add_argument(
        "--use-secondary-presets",
        action="store_true",
        help="Use suggested preset values for the secondary axis when --value2 is omitted.",
    )
    p_preview_grid.add_argument(
        "--include-bounds",
        action="store_true",
        help="Include min/max axis bounds in preset-driven grid suggestions.",
    )
    p_preview_grid.add_argument(
        "--no-default",
        action="store_true",
        help="Omit the axis default coordinate from preset-driven grid suggestions.",
    )
    p_preview_grid.add_argument(
        "--instance-name",
        help="Optional named instance label to use as the base coordinate set.",
    )
    p_preview_grid.add_argument(
        "--text",
        default="Hamburgefons 0123456789",
        help="Preview text to render.",
    )
    p_preview_grid.add_argument(
        "--size",
        type=float,
        default=72.0,
        help="Preview size in font units scaled to pixels.",
    )
    p_preview_grid.add_argument(
        "--padding",
        type=int,
        default=12,
        help="Canvas padding in pixels.",
    )
    p_preview_grid.add_argument(
        "--no-antialias",
        action="store_true",
        help="Disable 4x supersampling antialiasing.",
    )
    p_preview_grid.add_argument(
        "--format",
        choices=("png", "svg"),
        default="png",
        help="Preview output format for generated files (default: png).",
    )
    p_preview_grid.set_defaults(func=_cmd_preview_grid)

    p_preview_grid_sheet = subparsers.add_parser(
        "preview-grid-sheet", help="Render one composite PNG sheet for a variable-font axis sweep."
    )
    p_preview_grid_sheet.add_argument("file", help="Variable font file.")
    p_preview_grid_sheet.add_argument("output", help="Output PNG file path.")
    p_preview_grid_sheet.add_argument(
        "--axis",
        required=True,
        help="Primary variable axis tag to sweep.",
    )
    p_preview_grid_sheet.add_argument(
        "--value",
        action="append",
        default=[],
        help="Primary axis value. Repeatable.",
    )
    p_preview_grid_sheet.add_argument(
        "--axis2",
        help="Optional secondary variable axis tag.",
    )
    p_preview_grid_sheet.add_argument(
        "--value2",
        action="append",
        default=[],
        help="Secondary axis value. Repeatable.",
    )
    p_preview_grid_sheet.add_argument(
        "--use-presets",
        action="store_true",
        help="Use suggested preset values for the primary axis when --value is omitted.",
    )
    p_preview_grid_sheet.add_argument(
        "--use-secondary-presets",
        action="store_true",
        help="Use suggested preset values for the secondary axis when --value2 is omitted.",
    )
    p_preview_grid_sheet.add_argument(
        "--include-bounds",
        action="store_true",
        help="Include min/max axis bounds in preset-driven grid suggestions.",
    )
    p_preview_grid_sheet.add_argument(
        "--no-default",
        action="store_true",
        help="Omit the axis default coordinate from preset-driven grid suggestions.",
    )
    p_preview_grid_sheet.add_argument(
        "--instance-name",
        help="Optional named instance label to use as the base coordinate set.",
    )
    p_preview_grid_sheet.add_argument(
        "--text",
        default="Hamburgefons 0123456789",
        help="Preview text to render.",
    )
    p_preview_grid_sheet.add_argument(
        "--size",
        type=float,
        default=72.0,
        help="Preview size in font units scaled to pixels.",
    )
    p_preview_grid_sheet.add_argument(
        "--padding",
        type=int,
        default=12,
        help="Canvas padding in pixels.",
    )
    p_preview_grid_sheet.add_argument(
        "--gap",
        type=int,
        default=16,
        help="Gap between preview cells in pixels.",
    )
    p_preview_grid_sheet.add_argument(
        "--no-antialias",
        action="store_true",
        help="Disable 4x supersampling antialiasing.",
    )
    p_preview_grid_sheet.set_defaults(func=_cmd_preview_grid_sheet)

    p_preview_compare = subparsers.add_parser(
        "preview-compare", help="Render a before/after comparison board for a variable font."
    )
    p_preview_compare.add_argument("file", help="Variable font file.")
    p_preview_compare.add_argument("output", help="Output PNG file path.")
    p_preview_compare.add_argument(
        "--before-instance-name",
        help="Named instance label for the before side.",
    )
    p_preview_compare.add_argument(
        "--before-instance",
        action="append",
        default=[],
        help="Before-side variable-font axis coordinate in tag=value form. Repeatable.",
    )
    p_preview_compare.add_argument(
        "--after-instance-name",
        help="Named instance label for the after side.",
    )
    p_preview_compare.add_argument(
        "--after-instance",
        action="append",
        default=[],
        help="After-side variable-font axis coordinate in tag=value form. Repeatable.",
    )
    p_preview_compare.add_argument(
        "--text",
        default="Hamburgefons 0123456789",
        help="Preview text to render.",
    )
    p_preview_compare.add_argument(
        "--size",
        type=float,
        default=72.0,
        help="Preview size in font units scaled to pixels.",
    )
    p_preview_compare.add_argument(
        "--padding",
        type=int,
        default=12,
        help="Canvas padding in pixels.",
    )
    p_preview_compare.add_argument(
        "--gap",
        type=int,
        default=16,
        help="Gap between preview cells in pixels.",
    )
    p_preview_compare.add_argument(
        "--no-antialias",
        action="store_true",
        help="Disable 4x supersampling antialiasing.",
    )
    p_preview_compare.set_defaults(func=_cmd_preview_compare)

    p_preview_waterfall = subparsers.add_parser(
        "preview-waterfall",
        help="Render a standalone waterfall PNG for selected variable-font instances.",
    )
    p_preview_waterfall.add_argument("file", help="Variable font file.")
    p_preview_waterfall.add_argument("output", nargs="?", help="Output PNG file path.")
    p_preview_waterfall.add_argument(
        "--instance-name",
        action="append",
        default=[],
        help="Named instance to include. Repeatable.",
    )
    p_preview_waterfall.add_argument(
        "--all-named",
        action="store_true",
        help="Include all named instances.",
    )
    p_preview_waterfall.add_argument(
        "--include-default",
        action="store_true",
        help="Include the default instance alongside selected named instances.",
    )
    p_preview_waterfall.add_argument(
        "--text",
        default="Hamburgefons 0123456789",
        help="Preview text.",
    )
    p_preview_waterfall.add_argument(
        "--format",
        choices=["png", "pdf", "pptx"],
        default="png",
        help="Output format (default: png).",
    )
    p_preview_waterfall.add_argument(
        "--export-pptx",
        metavar="OUTPUT_PPTX",
        help="Export PPTX file path instead of PNG (deprecated: use --format pptx).",
    )
    p_preview_waterfall.set_defaults(func=_cmd_preview_waterfall)

    p_preview_matrix = subparsers.add_parser(
        "preview-matrix",
        help="Render a standalone matrix PNG for selected variable-font instances.",
    )
    p_preview_matrix.add_argument("file", help="Variable font file.")
    p_preview_matrix.add_argument("output", nargs="?", help="Output PNG file path.")
    p_preview_matrix.add_argument(
        "--instance-name",
        action="append",
        default=[],
        help="Named instance to include. Repeatable.",
    )
    p_preview_matrix.add_argument(
        "--all-named",
        action="store_true",
        help="Include all named instances.",
    )
    p_preview_matrix.add_argument(
        "--include-default",
        action="store_true",
        help="Include the default instance alongside selected named instances.",
    )
    p_preview_matrix.add_argument(
        "--text",
        default="Hamburgefons 0123456789",
        help="Preview text.",
    )
    p_preview_matrix.add_argument(
        "--format",
        choices=["png", "pdf", "pptx"],
        default="png",
        help="Output format (default: png).",
    )
    p_preview_matrix.add_argument(
        "--export-pptx",
        metavar="OUTPUT_PPTX",
        help="Export PPTX file path instead of PNG (deprecated: use --format pptx).",
    )
    p_preview_matrix.set_defaults(func=_cmd_preview_matrix)

    p_preview_family_board = subparsers.add_parser(
        "preview-family-board",
        help="Render one combined family review board PNG for selected variable-font instances.",
    )
    p_preview_family_board.add_argument("file", help="Variable font file.")
    p_preview_family_board.add_argument("output", help="Output PNG file path.")
    p_preview_family_board.add_argument(
        "--instance-name",
        action="append",
        default=[],
        help="Named instance to include. Repeatable.",
    )
    p_preview_family_board.add_argument(
        "--all-named",
        action="store_true",
        help="Include all named instances.",
    )
    p_preview_family_board.add_argument(
        "--include-default",
        action="store_true",
        help="Include the default instance alongside selected named instances.",
    )
    p_preview_family_board.add_argument(
        "--family-name",
        help="Optional board title family name override.",
    )
    p_preview_family_board.add_argument(
        "--text",
        default="Hamburgefons 0123456789",
        help="Preview text.",
    )
    p_preview_family_board.set_defaults(func=_cmd_preview_family_board)

    p_specimen_board = subparsers.add_parser(
        "specimen-board",
        help="Generate a specimen board with variable-font controls and preview.",
        description="Generate a specimen board combining variable-font axis sliders, CSS output, and PNG preview.",
    )
    p_specimen_board.add_argument("file", help="Path to variable font file.")
    p_specimen_board.add_argument("output", help="Output file (PNG) or directory (HTML).")
    p_specimen_board.add_argument(
        "--format",
        choices=["png", "html", "pdf"],
        default="png",
        help="Output format: PNG preview (default), HTML, or PDF.",
    )
    p_specimen_board.add_argument(
        "--instance-name",
        action="append",
        default=[],
        metavar="NAME",
        help="Named instance to preview (e.g., Bold, Condensed). Repeatable.",
    )
    p_specimen_board.add_argument(
        "--all-named",
        action="store_true",
        help="Preview all named instances.",
    )
    p_specimen_board.add_argument(
        "--include-default",
        action="store_true",
        help="Include the default instance in the preview.",
    )
    p_specimen_board.add_argument(
        "--text",
        default=_DEFAULT_PREVIEW_TEXT,
        help="Preview text (default: Hamburgefons 0123456789).",
    )
    p_specimen_board.add_argument(
        "--size",
        type=int,
        default=24,
        metavar="PX",
        help="Font size in pixels (default: 24).",
    )
    p_specimen_board.add_argument(
        "--padding",
        type=int,
        default=10,
        metavar="PX",
        help="Padding around preview in pixels (default: 10).",
    )
    p_specimen_board.add_argument(
        "--no-antialias",
        action="store_true",
        help="Disable antialiasing for PNG output.",
    )
    p_specimen_board.set_defaults(func=_cmd_specimen_board)

    p_specimen_playground = subparsers.add_parser(
        "specimen-playground",
        help="Generate an interactive specimen playground HTML",
        description="Generate an interactive specimen playground with live sliders, sample text editing, and font controls.",
    )
    p_specimen_playground.add_argument("file", help="Path to variable font file.")
    p_specimen_playground.add_argument("output_dir", help="Output directory for playground HTML and font assets.")
    p_specimen_playground.add_argument(
        "--sample-text",
        default=_DEFAULT_PREVIEW_TEXT,
        help="Initial specimen text (default: Hamburgefons 0123456789).",
    )
    p_specimen_playground.add_argument(
        "--dark-mode",
        action="store_true",
        help="Enable dark color scheme.",
    )
    p_specimen_playground.add_argument(
        "--template",
        choices=("classic", "editorial", "lab"),
        default="classic",
        help="Specimen template style (default: classic).",
    )
    p_specimen_playground.set_defaults(func=_cmd_specimen_playground)

    p_preview_waterfall_matrix = subparsers.add_parser(
        "preview-waterfall-matrix",
        help="Render combined waterfall and matrix PNG (or PDF) for selected variable-font instances.",
    )
    p_preview_waterfall_matrix.add_argument("file", help="Variable font file.")
    p_preview_waterfall_matrix.add_argument("output", help="Output PNG or PDF file path.")
    p_preview_waterfall_matrix.add_argument(
        "--format",
        choices=["png", "pdf", "pptx"],
        default="png",
        help="Output format (default: png).",
    )
    p_preview_waterfall_matrix.add_argument(
        "--instance-name",
        action="append",
        default=[],
        help="Named instance to include. Repeatable.",
    )
    p_preview_waterfall_matrix.add_argument(
        "--all-named",
        action="store_true",
        help="Include all named instances.",
    )
    p_preview_waterfall_matrix.add_argument(
        "--include-default",
        action="store_true",
        help="Include the default instance alongside selected named instances.",
    )
    p_preview_waterfall_matrix.add_argument(
        "--text",
        default="Hamburgefons 0123456789",
        help="Preview text.",
    )
    p_preview_waterfall_matrix.set_defaults(func=_cmd_preview_waterfall_matrix)

    p_preview_family_export = subparsers.add_parser(
        "preview-family-export",
        help="Write a reusable family review export pack with PNG, Markdown, HTML, and manifest files.",
    )
    p_preview_family_export.add_argument("file", help="Variable font file.")
    p_preview_family_export.add_argument("output_dir", help="Output directory path.")
    p_preview_family_export.add_argument(
        "--instance-name",
        action="append",
        default=[],
        help="Named instance to include. Repeatable.",
    )
    p_preview_family_export.add_argument(
        "--all-named",
        action="store_true",
        help="Include all named instances.",
    )
    p_preview_family_export.add_argument(
        "--include-default",
        action="store_true",
        help="Include the default instance alongside selected named instances.",
    )
    p_preview_family_export.add_argument(
        "--family-name",
        help="Optional family name override used in captions and headings.",
    )
    p_preview_family_export.add_argument(
        "--text",
        default="Hamburgefons 0123456789",
        help="Preview text.",
    )
    p_preview_family_export.set_defaults(func=_cmd_preview_family_export)

    p_var_compat = subparsers.add_parser(
        "var-compat",
        help="Check outline-command compatibility between two variable-font instance states.",
    )
    p_var_compat.add_argument("file", help="Variable font file.")
    p_var_compat.add_argument(
        "--before-instance-name",
        help="Named instance label for the before side.",
    )
    p_var_compat.add_argument(
        "--before-instance",
        action="append",
        default=[],
        help="Before-side variable-font axis coordinate in tag=value form. Repeatable.",
    )
    p_var_compat.add_argument(
        "--after-instance-name",
        help="Named instance label for the after side.",
    )
    p_var_compat.add_argument(
        "--after-instance",
        action="append",
        default=[],
        help="After-side variable-font axis coordinate in tag=value form. Repeatable.",
    )
    p_var_compat.add_argument(
        "--text",
        default="",
        help="Only check glyphs needed for this text.",
    )
    p_var_compat.add_argument(
        "--codepoint",
        action="append",
        default=[],
        help="Explicit Unicode codepoint to check (decimal or 0x-prefixed). Repeatable.",
    )
    p_var_compat.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Maximum number of issue lines to print (default: 20).",
    )
    p_var_compat.add_argument(
        "--json",
        action="store_true",
        help="Emit the compatibility report as JSON.",
    )
    p_var_compat.add_argument(
        "--json-output",
        help="Write the compatibility report to this JSON file.",
    )
    p_var_compat.set_defaults(func=_cmd_var_compat)

    p_var_delta = subparsers.add_parser(
        "var-delta",
        help="Inspect active gvar tuple deltas for one glyph at a selected variable-font instance state.",
    )
    p_var_delta.add_argument("file", help="Variable font file.")
    p_var_delta.add_argument(
        "--instance-name",
        help="Named instance label to inspect.",
    )
    p_var_delta.add_argument(
        "--instance",
        action="append",
        default=[],
        help="Variable-font axis coordinate in tag=value form. Repeatable.",
    )
    p_var_delta.add_argument(
        "--gid",
        type=int,
        help="Glyph ID to inspect.",
    )
    p_var_delta.add_argument(
        "--codepoint",
        help="Unicode codepoint to inspect (decimal or 0x-prefixed).",
    )
    p_var_delta.add_argument(
        "--char",
        dest="character",
        help="Single character to inspect.",
    )
    p_var_delta.add_argument(
        "--top-points",
        type=int,
        default=8,
        help="Maximum number of strongest point deltas to print per active tuple (default: 8).",
    )
    p_var_delta.add_argument(
        "-a",
        "--instance-a",
        action="append",
        default=[],
        help="Before-state variable-font axis coordinate (tag=value). Repeatable.",
    )
    p_var_delta.add_argument(
        "-b",
        "--instance-b",
        action="append",
        default=[],
        help="After-state variable-font axis coordinate (tag=value). Repeatable.",
    )
    p_var_delta.add_argument(
        "--visual-diff",
        action="store_true",
        help="Generate a PNG visual diff overlay and write diff_overlay.png.",
    )
    p_var_delta.add_argument(
        "-o",
        "--output-dir",
        type=str,
        default=".",
        help="Directory to write diff_overlay.png when --visual-diff is used.",
    )
    p_var_delta.add_argument(
        "--json",
        action="store_true",
        help="Emit the delta report as JSON.",
    )
    p_var_delta.set_defaults(func=_cmd_var_delta)

    p_var_delta_board = subparsers.add_parser(
        "var-delta-board",
        help="Render a PNG board showing default, resolved, and overlay views for one glyph's active deltas.",
    )
    p_var_delta_board.add_argument("file", help="Variable font file.")
    p_var_delta_board.add_argument("output", help="Output PNG file path.")
    p_var_delta_board.add_argument(
        "--instance-name",
        help="Named instance label to inspect.",
    )
    p_var_delta_board.add_argument(
        "--instance",
        action="append",
        default=[],
        help="Variable-font axis coordinate in tag=value form. Repeatable.",
    )
    p_var_delta_board.add_argument(
        "--gid",
        type=int,
        help="Glyph ID to inspect.",
    )
    p_var_delta_board.add_argument(
        "--codepoint",
        help="Unicode codepoint to inspect (decimal or 0x-prefixed).",
    )
    p_var_delta_board.add_argument(
        "--char",
        dest="character",
        help="Single character to inspect.",
    )
    p_var_delta_board.add_argument(
        "--top-points",
        type=int,
        default=8,
        help="Maximum number of strongest moved points to highlight (default: 8).",
    )
    p_var_delta_board.add_argument(
        "--panel-size",
        type=int,
        default=220,
        help="Panel size in pixels for each glyph view (default: 220).",
    )
    p_var_delta_board.set_defaults(func=_cmd_var_delta_board)

    p_var_delta_text = subparsers.add_parser(
        "var-delta-text",
        help="Inspect delta activity across all unique glyphs needed for a text sample.",
    )
    p_var_delta_text.add_argument("file", help="Variable font file.")
    p_var_delta_text.add_argument(
        "--text",
        required=True,
        help="Text sample to inspect.",
    )
    p_var_delta_text.add_argument(
        "--instance-name",
        help="Named instance label to inspect.",
    )
    p_var_delta_text.add_argument(
        "--instance",
        action="append",
        default=[],
        help="Variable-font axis coordinate in tag=value form. Repeatable.",
    )
    p_var_delta_text.add_argument(
        "--top-points",
        type=int,
        default=8,
        help="Maximum number of strongest points to retain per glyph (default: 8).",
    )
    p_var_delta_text.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Maximum number of glyph summary lines to print (default: 20).",
    )
    p_var_delta_text.add_argument(
        "--json",
        action="store_true",
        help="Emit the text-level delta report as JSON.",
    )
    p_var_delta_text.set_defaults(func=_cmd_var_delta_text)

    p_var_delta_text_compare = subparsers.add_parser(
        "var-delta-text-compare",
        help="Compare delta movement across all unique glyphs in a text sample between two instance states.",
    )
    p_var_delta_text_compare.add_argument("file", help="Variable font file.")
    p_var_delta_text_compare.add_argument(
        "--text",
        required=True,
        help="Text sample to inspect.",
    )
    p_var_delta_text_compare.add_argument(
        "--before-instance-name",
        help="Named instance label for the before state.",
    )
    p_var_delta_text_compare.add_argument(
        "--before-instance",
        action="append",
        default=[],
        help="Before-state variable-font axis coordinate in tag=value form. Repeatable.",
    )
    p_var_delta_text_compare.add_argument(
        "--after-instance-name",
        help="Named instance label for the after state.",
    )
    p_var_delta_text_compare.add_argument(
        "--after-instance",
        action="append",
        default=[],
        help="After-state variable-font axis coordinate in tag=value form. Repeatable.",
    )
    p_var_delta_text_compare.add_argument(
        "--top-points",
        type=int,
        default=8,
        help="Maximum number of strongest moved points to retain per glyph comparison (default: 8).",
    )
    p_var_delta_text_compare.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Maximum number of glyph comparison lines to print (default: 20).",
    )
    p_var_delta_text_compare.add_argument(
        "--json",
        action="store_true",
        help="Emit the text comparison report as JSON.",
    )
    p_var_delta_text_compare.set_defaults(func=_cmd_var_delta_text_compare)

    p_cff2_info = subparsers.add_parser(
        "cff2-info",
        help="Print CFF2 variable font stub information.",
    )
    p_cff2_info.add_argument("file", help="Path to font file.")
    p_cff2_info.set_defaults(func=_cmd_cff2_info)

    p_cff2_list_axes = subparsers.add_parser(
        "cff2-list-axes",
        help="List variable axes in CFF2 font",
        description="List all variable axes in a CFF2 font.",
    )
    p_cff2_list_axes.add_argument("file", help="CFF2 font file path")
    p_cff2_list_axes.set_defaults(func=_cmd_cff2_list_axes)

    _add_cff2_instantiate_parser(subparsers)
    _add_var_partial_instance_parser(subparsers)
    _add_var_partial_web_parser(subparsers)
    _add_subset_parser(subparsers)
    _add_web_subset_parser(subparsers)

    p_cff2_preview = subparsers.add_parser(
        "cff2-preview",
        help="Preview blended CFF2 outline",
        description="Render a PNG preview of a CFF2 glyph with variable outlining.",
    )
    p_cff2_preview.add_argument("file", help="Path to CFF2 font file.")
    p_cff2_preview.add_argument("output", help="Output PNG file path.")
    p_cff2_preview.add_argument(
        "--gid",
        type=int,
        default=1,
        help="Glyph ID to preview (default: 1, .notdef).",
    )
    p_cff2_preview.add_argument(
        "--axis",
        action="append",
        default=[],
        help="Variable axis coordinate in tag=value form. Repeatable.",
    )
    p_cff2_preview.add_argument(
        "--text",
        default="H",
        help="Preview text sample (default: 'H').",
    )
    p_cff2_preview.set_defaults(func=_cmd_cff2_preview)

    p_var_delta_text_board = subparsers.add_parser(
        "var-delta-text-board",
        help="Render a PNG board showing delta overlays for all unique glyphs in a text sample.",
    )
    p_var_delta_text_board.add_argument("file", help="Variable font file.")
    p_var_delta_text_board.add_argument("output", help="Output PNG file path.")
    p_var_delta_text_board.add_argument(
        "--text",
        required=True,
        help="Text sample to inspect.",
    )
    p_var_delta_text_board.add_argument(
        "--instance-name",
        help="Named instance label to inspect.",
    )
    p_var_delta_text_board.add_argument(
        "--instance",
        action="append",
        default=[],
        help="Variable-font axis coordinate in tag=value form. Repeatable.",
    )
    p_var_delta_text_board.add_argument(
        "--top-points",
        type=int,
        default=8,
        help="Maximum number of strongest moved points to highlight per glyph (default: 8).",
    )
    p_var_delta_text_board.add_argument(
        "--panel-size",
        type=int,
        default=220,
        help="Panel size in pixels for each glyph view (default: 220).",
    )
    p_var_delta_text_board.add_argument(
        "--columns",
        type=int,
        default=3,
        help="Number of board columns to use (default: 3).",
    )
    p_var_delta_text_board.set_defaults(func=_cmd_var_delta_text_board)

    p_var_delta_text_compare_board = subparsers.add_parser(
        "var-delta-text-compare-board",
        help="Render a PNG board comparing all unique glyphs in a text sample between two instance states.",
    )
    p_var_delta_text_compare_board.add_argument("file", help="Variable font file.")
    p_var_delta_text_compare_board.add_argument("output", help="Output PNG file path.")
    p_var_delta_text_compare_board.add_argument(
        "--text",
        required=True,
        help="Text sample to inspect.",
    )
    p_var_delta_text_compare_board.add_argument(
        "--before-instance-name",
        help="Named instance label for the before state.",
    )
    p_var_delta_text_compare_board.add_argument(
        "--before-instance",
        action="append",
        default=[],
        help="Before-state variable-font axis coordinate in tag=value form. Repeatable.",
    )
    p_var_delta_text_compare_board.add_argument(
        "--after-instance-name",
        help="Named instance label for the after state.",
    )
    p_var_delta_text_compare_board.add_argument(
        "--after-instance",
        action="append",
        default=[],
        help="After-state variable-font axis coordinate in tag=value form. Repeatable.",
    )
    p_var_delta_text_compare_board.add_argument(
        "--top-points",
        type=int,
        default=8,
        help="Maximum number of strongest moved points to highlight per glyph comparison (default: 8).",
    )
    p_var_delta_text_compare_board.add_argument(
        "--panel-size",
        type=int,
        default=220,
        help="Panel size in pixels for each glyph view (default: 220).",
    )
    p_var_delta_text_compare_board.add_argument(
        "--columns",
        type=int,
        default=3,
        help="Number of board columns to use (default: 3).",
    )
    p_var_delta_text_compare_board.set_defaults(func=_cmd_var_delta_text_compare_board)

    p_var_delta_compare = subparsers.add_parser(
        "var-delta-compare",
        help="Compare one glyph between two variable-font instance states with text and JSON report output.",
    )
    p_var_delta_compare.add_argument("file", help="Variable font file.")
    p_var_delta_compare.add_argument(
        "--before-instance-name",
        help="Named instance label for the before state.",
    )
    p_var_delta_compare.add_argument(
        "--before-instance",
        action="append",
        default=[],
        help="Before-state variable-font axis coordinate in tag=value form. Repeatable.",
    )
    p_var_delta_compare.add_argument(
        "--after-instance-name",
        help="Named instance label for the after state.",
    )
    p_var_delta_compare.add_argument(
        "--after-instance",
        action="append",
        default=[],
        help="After-state variable-font axis coordinate in tag=value form. Repeatable.",
    )
    p_var_delta_compare.add_argument(
        "--gid",
        type=int,
        help="Glyph ID to inspect.",
    )
    p_var_delta_compare.add_argument(
        "--codepoint",
        help="Unicode codepoint to inspect (decimal or 0x-prefixed).",
    )
    p_var_delta_compare.add_argument(
        "--char",
        dest="character",
        help="Single character to inspect.",
    )
    p_var_delta_compare.add_argument(
        "--top-points",
        type=int,
        default=8,
        help="Maximum number of strongest moved points to retain in the comparison report (default: 8).",
    )
    p_var_delta_compare.add_argument(
        "--json",
        action="store_true",
        help="Emit the comparison report as JSON.",
    )
    p_var_delta_compare.set_defaults(func=_cmd_var_delta_compare)

    p_var_delta_compare_board = subparsers.add_parser(
        "var-delta-compare-board",
        help="Render a PNG board comparing one glyph between two variable-font instance states.",
    )
    p_var_delta_compare_board.add_argument("file", help="Variable font file.")
    p_var_delta_compare_board.add_argument("output", help="Output PNG file path.")
    p_var_delta_compare_board.add_argument(
        "--before-instance-name",
        help="Named instance label for the before state.",
    )
    p_var_delta_compare_board.add_argument(
        "--before-instance",
        action="append",
        default=[],
        help="Before-state variable-font axis coordinate in tag=value form. Repeatable.",
    )
    p_var_delta_compare_board.add_argument(
        "--after-instance-name",
        help="Named instance label for the after state.",
    )
    p_var_delta_compare_board.add_argument(
        "--after-instance",
        action="append",
        default=[],
        help="After-state variable-font axis coordinate in tag=value form. Repeatable.",
    )
    p_var_delta_compare_board.add_argument(
        "--gid",
        type=int,
        help="Glyph ID to inspect.",
    )
    p_var_delta_compare_board.add_argument(
        "--codepoint",
        help="Unicode codepoint to inspect (decimal or 0x-prefixed).",
    )
    p_var_delta_compare_board.add_argument(
        "--char",
        dest="character",
        help="Single character to inspect.",
    )
    p_var_delta_compare_board.add_argument(
        "--top-points",
        type=int,
        default=8,
        help="Maximum number of strongest moved comparison points to highlight (default: 8).",
    )
    p_var_delta_compare_board.add_argument(
        "--panel-size",
        type=int,
        default=220,
        help="Panel size in pixels for each glyph view (default: 220).",
    )
    p_var_delta_compare_board.set_defaults(func=_cmd_var_delta_compare_board)

    p_var_designspace_coverage = subparsers.add_parser(
        "var-designspace-coverage",
        help="Compute and report designspace coverage for variable fonts.",
    )
    _add_collection_index_arg(p_var_designspace_coverage)
    p_var_designspace_coverage.add_argument(
        "file",
        type=Path,
        help="Path to font file (TTF/OTF with variable axes).",
    )
    p_var_designspace_coverage.add_argument(
        "--grid",
        help="JSON string or path to JSON file containing grid points as list of dicts, "
        'e.g., [{"wght":400,"wdth":100},{"wght":700,"wdth":100}]. '
        "If omitted, uses an empty grid (0 points).",
    )
    p_var_designspace_coverage.add_argument(
        "--output-dir",
        help="Output directory for coverage-report.json (default: stdout).",
    )
    p_var_designspace_coverage.add_argument(
        "--generate-diff",
        action="store_true",
        help="Generate PNG visual diff overlays for uncovered grid points.",
    )
    p_var_designspace_coverage.set_defaults(func=_cmd_var_designspace_coverage)

    p_var_info = subparsers.add_parser(
        "var-info", help="Print variable font axes and named instances."
    )
    p_var_info.add_argument("file", help="Variable font file.")
    p_var_info.add_argument(
        "--language",
        action="append",
        default=[],
        help="Preferred language tag for localized axis and instance names. Repeatable.",
    )
    p_var_info.add_argument(
        "--json-output",
        help="Write a machine-readable variable-axis presentation snapshot to this JSON file.",
    )
    p_var_info.add_argument(
        "--color-diagnostics",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Include color font inspection diagnostics (COLR/CPAL tables).",
    )
    p_var_info.set_defaults(func=_cmd_var_info)

    p_var_instance = subparsers.add_parser(
        "var-instance", help="Create a static instance from a variable font."
    )
    p_var_instance.add_argument("file", help="Variable font file.")
    p_var_instance.add_argument("output", help="Output file path for the static font.")
    p_var_instance.add_argument(
        "--instance-name",
        help="Named instance label to start from.",
    )
    p_var_instance.add_argument(
        "--instance",
        action="append",
        default=[],
        help="Variable-font axis coordinate in tag=value form. Repeatable.",
    )
    p_var_instance.add_argument(
        "--apply-avar",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Apply avar (Axis Variations) table mapping for normalized axis values (default: True).",
    )
    p_var_instance.add_argument(
        "--naming-strategy",
        choices=_NAMING_STRATEGY_CHOICES,
        default="instance-family",
        help="Naming policy for the generated static font (default: instance-family).",
    )
    p_var_instance.add_argument(
        "--family-suffix",
        help="Optional custom suffix to append to the generated family name.",
    )
    p_var_instance.add_argument(
        "--legacy-family-name",
        help="Explicit legacy/menu family name for name ID 1.",
    )
    p_var_instance.add_argument(
        "--typographic-family-name",
        help="Explicit typographic family name for name IDs 16, 21, and 25.",
    )
    p_var_instance.add_argument(
        "--legacy-style-name",
        help="Explicit legacy/menu style name for name ID 2.",
    )
    p_var_instance.add_argument(
        "--typographic-style-name",
        help="Explicit typographic style name for name IDs 17 and 22.",
    )
    _add_stat_policy_arg(p_var_instance)
    p_var_instance.set_defaults(func=_cmd_var_instance)

    p_var_package = subparsers.add_parser(
        "var-package",
        help="Build a variable instance release package (fonts + STAT evidence + review manifest).",
    )
    p_var_package.add_argument(
        "file",
        help="Variable font file.",
    )
    p_var_package.add_argument(
        "output_dir",
        help="Output directory for the release package folder.",
    )
    p_var_package.add_argument(
        "--instance",
        action="append",
        default=[],
        help='Variable-font axis coordinates in tag=value form, comma-separated (e.g., "wght=400,wdth=100").',
    )
    p_var_package.add_argument(
        "--instance-name",
        action="append",
        default=[],
        help="Named instance label to include. Repeatable. By default includes all named instances plus default.",
    )
    p_var_package.add_argument(
        "--no-default",
        action="store_true",
        help="Exclude the default instance from the package.",
    )
    p_var_package.add_argument(
        "--naming-strategy",
        choices=_NAMING_STRATEGY_CHOICES,
        default="instance-family",
        help="Naming strategy for generated instances (default: instance-family).",
    )
    p_var_package.add_argument(
        "--family-suffix",
        help="Additive suffix for family name in generated instances.",
    )
    p_var_package.add_argument(
        "--legacy-family-name",
        help="Explicit legacy/menu family name for name ID 1.",
    )
    p_var_package.add_argument(
        "--typographic-family-name",
        help="Explicit typographic family name for name IDs 16, 21, and 25.",
    )
    p_var_package.add_argument(
        "--legacy-style-name",
        help="Explicit legacy/menu style name for name ID 2.",
    )
    p_var_package.add_argument(
        "--typographic-style-name",
        help="Explicit typographic style name for name IDs 17 and 22.",
    )
    p_var_package.add_argument(
        "--apply-avar",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Apply avar (Axis Variations) table mapping for normalized axis values (default: True).",
    )
    p_var_package.add_argument(
        "--preview-text",
        default="Hamburgefons 0123456789",
        help="Text used in comparison board preview (default: Hamburgefons 0123456789).",
    )
    p_var_package.add_argument(
        "--compare-axes",
        help="Comma-separated list of axis tags to include in comparison board (e.g., 'wght,wdth'). If omitted, all axes are included.",
    )
    p_var_package.add_argument(
        "--ci-fast",
        action="store_true",
        default=False,
        help="Enable CI fast mode for performance-sensitive workflows (reduces preview generation and instance count).",
    )
    p_var_package.add_argument(
        "--performance-report",
        action="store_true",
        default=False,
        help="Print build time in milliseconds to stdout (no output files).",
    )
    p_var_package.add_argument(
        "--specimen-board",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Generate specimen board PNG for the package (produces specimen_board.png).",
    )
    p_var_package.add_argument(
        "--specimen-caption",
        help="Custom caption text for specimen board (default: \"STAT policy: <policy>\").",
    )
    _add_stat_policy_arg(p_var_package)
    p_var_package.set_defaults(func=_cmd_var_package)

    p_stat_fix = subparsers.add_parser(
        "stat-fix",
        help="Repair or synthesize STAT table for variable fonts.",
        description="Inspect or fix missing STAT table in variable fonts.",
    )
    p_stat_fix.add_argument("file", help="Path to input font file.")
    p_stat_fix.add_argument("output", help="Path to output font file (with STAT table).")
    p_stat_fix.add_argument(
        "--dry-run",
        action="store_true",
        help="Show proposed STAT changes without writing output file.",
    )
    p_stat_fix.set_defaults(func=_cmd_stat_fix)

    p_autonomous = subparsers.add_parser(
        "autonomous",
        help="Run autonomous font processing workflow (web optimization + QA + instance packaging).",
    )
    p_autonomous.add_argument(
        "file",
        help="Font file path (TTF, OTF, CFF, WOFF, WOFF2).",
    )
    p_autonomous.add_argument(
        "output_dir",
        help="Output directory for the autonomous workflow deliverable.",
    )
    p_autonomous.add_argument(
        "--preset",
        action="append",
        default=[],
        help="Subset preset name (e.g., latin, latin-ext). Repeatable.",
    )
    p_autonomous.add_argument(
        "--naming-strategy",
        choices=_NAMING_STRATEGY_CHOICES,
        default="instance-family",
        help="Naming strategy for generated instances (default: instance-family).",
    )
    p_autonomous.add_argument(
        "--family-suffix",
        help="Additive suffix for family name in generated instances and web assets.",
    )
    _add_naming_override_args(p_autonomous)
    _add_stat_policy_arg(p_autonomous)
    p_autonomous.add_argument(
        "--font-display",
        choices=("auto", "block", "swap", "fallback", "optional"),
        default="swap",
        help="CSS font-display value for web assets (default: swap).",
    )
    p_autonomous.add_argument(
        "--no-qa",
        action="store_true",
        help="Skip QA report generation.",
    )
    p_autonomous.add_argument(
        "--no-instances",
        action="store_true",
        help="Skip instance package generation.",
    )
    p_autonomous.add_argument(
        "--no-woff",
        action="store_true",
        help="Skip WOFF generation (only WOFF2 will be produced).",
    )
    p_autonomous.add_argument(
        "--cdn-manifest",
        action="store_true",
        help="Generate CDN manifest for web assets.",
    )
    p_autonomous.add_argument(
        "--cdn-base",
        default="https://cdn.example.com",
        help="Base URL for CDN asset references (default: https://cdn.example.com).",
    )
    p_autonomous.add_argument(
        "--json-summary",
        help="Write unified autonomous summary to this JSON file path.",
    )
    p_autonomous.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output including decision report details.",
    )
    p_autonomous.add_argument(
        "--decision-report",
        nargs="?",
        const="decision-report.json",
        help="Write autonomous decision report JSON to file (default decision-report.json).",
    )
    p_autonomous.add_argument(
        "--no-decision-report",
        action="store_true",
        help="Disable decision report output.",
    )
    p_autonomous.set_defaults(func=_cmd_autonomous)

    p_full_report = subparsers.add_parser(
        "full-report",
        help="Generate full pipeline report (web optimizer, QA, variable instances).",
    )
    p_full_report.add_argument("--font", required=True, help="Path to font file.")
    p_full_report.add_argument("--output", required=True, help="Root output directory for report.")
    p_full_report.set_defaults(func=_cmd_full_report)

    p_var_naming_preview = subparsers.add_parser(
        "var-naming-preview",
        help="Preview generated static-instance name records without writing a font.",
    )
    p_var_naming_preview.add_argument("file", help="Variable font file.")
    p_var_naming_preview.add_argument(
        "--instance-name",
        help="Named instance label to preview.",
    )
    p_var_naming_preview.add_argument(
        "--instance",
        action="append",
        default=[],
        help="Variable-font axis coordinate in tag=value form. Repeatable.",
    )
    p_var_naming_preview.add_argument(
        "--naming-strategy",
        choices=_NAMING_STRATEGY_CHOICES,
        default="instance-family",
        help="Naming policy to preview (default: instance-family).",
    )
    p_var_naming_preview.add_argument(
        "--family-suffix",
        help="Optional custom suffix to append to the generated family name.",
    )
    _add_naming_override_args(p_var_naming_preview)
    _add_stat_policy_arg(p_var_naming_preview)
    p_var_naming_preview.add_argument(
        "--json-output",
        help="Write the naming preview payload to this JSON file.",
    )
    p_var_naming_preview.set_defaults(func=_cmd_var_naming_preview)

    p_var_batch = subparsers.add_parser(
        "var-batch", help="Create multiple static instances from a variable font."
    )
    p_var_batch.add_argument("file", help="Variable font file.")
    p_var_batch.add_argument("output_dir", help="Output directory for generated static fonts.")
    p_var_batch.add_argument(
        "--instance-name",
        action="append",
        default=[],
        help="Named instance label to generate. Repeatable.",
    )
    p_var_batch.add_argument(
        "--all-named",
        action="store_true",
        help="Generate all named instances from the font.",
    )
    p_var_batch.add_argument(
        "--include-default",
        action="store_true",
        help="Also generate the default coordinates as a static font.",
    )
    p_var_batch.add_argument(
        "--naming-strategy",
        choices=_NAMING_STRATEGY_CHOICES,
        default="instance-family",
        help="Naming policy for generated static fonts (default: instance-family).",
    )
    p_var_batch.add_argument(
        "--family-suffix",
        help="Optional custom suffix to append to generated family names.",
    )
    _add_naming_override_args(p_var_batch)
    _add_stat_policy_arg(p_var_batch)
    p_var_batch.set_defaults(func=_cmd_var_batch)

    p_web_batch = subparsers.add_parser(
        "web-batch", help="Generate multiple named-instance web bundles."
    )
    p_web_batch.add_argument("file", help="Variable font file.")
    p_web_batch.add_argument(
        "output_dir", help="Output directory for generated web bundle folders."
    )
    p_web_batch.add_argument(
        "--instance-name",
        action="append",
        default=[],
        help="Named instance label to package. Repeatable.",
    )
    p_web_batch.add_argument(
        "--all-named",
        action="store_true",
        help="Package all named instances from the font.",
    )
    p_web_batch.add_argument(
        "--include-default",
        action="store_true",
        help="Also package the default coordinates as a web bundle.",
    )
    p_web_batch.add_argument(
        "--preview-text",
        default="Hamburgefons 0123456789",
        help="Preview text for the generated specimen HTML.",
    )
    p_web_batch.add_argument(
        "--template",
        choices=("classic", "editorial", "lab"),
        default="classic",
        help="Specimen template to use for generated HTML/CSS (default: classic).",
    )
    p_web_batch.add_argument(
        "--no-woff",
        action="store_true",
        help="Do not emit WOFF fallback output.",
    )
    p_web_batch.add_argument(
        "--naming-strategy",
        choices=_NAMING_STRATEGY_CHOICES,
        default="instance-family",
        help="Naming policy for generated static web bundles (default: instance-family).",
    )
    p_web_batch.add_argument(
        "--family-suffix",
        help="Optional custom suffix to append to generated family names.",
    )
    _add_naming_override_args(p_web_batch)
    _add_stat_policy_arg(p_web_batch)
    p_web_batch.add_argument(
        "--preset",
        action="append",
        default=[],
        help="Subset preset name. Repeatable.",
    )
    p_web_batch.add_argument(
        "--text",
        default="",
        help="Extra literal text to retain in the subset.",
    )
    p_web_batch.add_argument(
        "--codepoint",
        action="append",
        default=[],
        help="Unicode codepoint to retain (decimal or 0x-prefixed). Repeatable.",
    )
    p_web_batch.add_argument(
        "--range",
        action="append",
        default=[],
        help="Unicode range to retain in start-end form. Repeatable.",
    )
    p_web_batch.set_defaults(func=_cmd_web_batch)

    p_web_grid = subparsers.add_parser(
        "web-grid", help="Generate web bundles for a variable-font axis sweep."
    )
    p_web_grid.add_argument("file", help="Variable font file.")
    p_web_grid.add_argument("output_dir", help="Output directory for generated web bundle folders.")
    p_web_grid.add_argument(
        "--axis",
        required=True,
        help="Primary variable axis tag to sweep.",
    )
    p_web_grid.add_argument(
        "--value",
        action="append",
        default=[],
        help="Primary axis value. Repeatable.",
    )
    p_web_grid.add_argument(
        "--axis2",
        help="Optional secondary variable axis tag.",
    )
    p_web_grid.add_argument(
        "--value2",
        action="append",
        default=[],
        help="Secondary axis value. Repeatable.",
    )
    p_web_grid.add_argument(
        "--use-presets",
        action="store_true",
        help="Use suggested preset values for the primary axis when --value is omitted.",
    )
    p_web_grid.add_argument(
        "--use-secondary-presets",
        action="store_true",
        help="Use suggested preset values for the secondary axis when --value2 is omitted.",
    )
    p_web_grid.add_argument(
        "--include-bounds",
        action="store_true",
        help="Include min/max axis bounds in preset-driven grid suggestions.",
    )
    p_web_grid.add_argument(
        "--no-default",
        action="store_true",
        help="Omit the axis default coordinate from preset-driven grid suggestions.",
    )
    p_web_grid.add_argument(
        "--instance-name",
        help="Optional named instance label to use as the base coordinate set.",
    )
    p_web_grid.add_argument(
        "--preview-text",
        default="Hamburgefons 0123456789",
        help="Preview text for the generated specimen HTML.",
    )
    p_web_grid.add_argument(
        "--template",
        choices=("classic", "editorial", "lab"),
        default="classic",
        help="Specimen template to use for generated HTML/CSS (default: classic).",
    )
    p_web_grid.add_argument(
        "--no-woff",
        action="store_true",
        help="Do not emit WOFF fallback output.",
    )
    p_web_grid.add_argument(
        "--naming-strategy",
        choices=_NAMING_STRATEGY_CHOICES,
        default="instance-family",
        help="Naming policy for generated static web bundles (default: instance-family).",
    )
    p_web_grid.add_argument(
        "--family-suffix",
        help="Optional custom suffix to append to generated family names.",
    )
    _add_naming_override_args(p_web_grid)
    _add_stat_policy_arg(p_web_grid)
    p_web_grid.add_argument(
        "--preset",
        action="append",
        default=[],
        help="Subset preset name. Repeatable.",
    )
    p_web_grid.add_argument(
        "--text",
        default="",
        help="Extra literal text to retain in the subset.",
    )
    p_web_grid.add_argument(
        "--codepoint",
        action="append",
        default=[],
        help="Unicode codepoint to retain (decimal or 0x-prefixed). Repeatable.",
    )
    p_web_grid.add_argument(
        "--range",
        action="append",
        default=[],
        help="Unicode range to retain in start-end form. Repeatable.",
    )
    p_web_grid.set_defaults(func=_cmd_web_grid)

    p_web_grid_family = subparsers.add_parser(
        "web-grid-family",
        help="Generate one shared family package for a variable-font axis sweep.",
    )
    p_web_grid_family.add_argument("file", help="Variable font file.")
    p_web_grid_family.add_argument("output_dir", help="Output directory for the family package.")
    p_web_grid_family.add_argument(
        "--axis",
        required=True,
        help="Primary variable axis tag to sweep.",
    )
    p_web_grid_family.add_argument(
        "--value",
        action="append",
        default=[],
        help="Primary axis value. Repeatable.",
    )
    p_web_grid_family.add_argument(
        "--axis2",
        help="Optional secondary variable axis tag.",
    )
    p_web_grid_family.add_argument(
        "--value2",
        action="append",
        default=[],
        help="Secondary axis value. Repeatable.",
    )
    p_web_grid_family.add_argument(
        "--use-presets",
        action="store_true",
        help="Use suggested preset values for the primary axis when --value is omitted.",
    )
    p_web_grid_family.add_argument(
        "--use-secondary-presets",
        action="store_true",
        help="Use suggested preset values for the secondary axis when --value2 is omitted.",
    )
    p_web_grid_family.add_argument(
        "--include-bounds",
        action="store_true",
        help="Include min/max axis bounds in preset-driven grid suggestions.",
    )
    p_web_grid_family.add_argument(
        "--no-default",
        action="store_true",
        help="Omit the axis default coordinate from preset-driven grid suggestions.",
    )
    p_web_grid_family.add_argument(
        "--instance-name",
        help="Optional named instance label to use as the base coordinate set.",
    )
    p_web_grid_family.add_argument(
        "--family-name",
        help="Override the shared family package title.",
    )
    p_web_grid_family.add_argument(
        "--preview-text",
        default="Hamburgefons 0123456789",
        help="Preview text for the generated family specimen HTML.",
    )
    p_web_grid_family.add_argument(
        "--template",
        choices=("classic", "editorial", "lab"),
        default="classic",
        help="Specimen template to use for generated HTML/CSS (default: classic).",
    )
    p_web_grid_family.add_argument(
        "--no-woff",
        action="store_true",
        help="Do not emit WOFF fallback output.",
    )
    p_web_grid_family.add_argument(
        "--naming-strategy",
        choices=_NAMING_STRATEGY_CHOICES,
        default="instance-family",
        help="Naming policy for generated static web bundles (default: instance-family).",
    )
    p_web_grid_family.add_argument(
        "--family-suffix",
        help="Optional custom suffix to append to generated family names.",
    )
    _add_naming_override_args(p_web_grid_family)
    _add_stat_policy_arg(p_web_grid_family)
    p_web_grid_family.add_argument(
        "--preset",
        action="append",
        default=[],
        help="Subset preset name. Repeatable.",
    )
    p_web_grid_family.add_argument(
        "--text",
        default="",
        help="Extra literal text to retain in the subset.",
    )
    p_web_grid_family.add_argument(
        "--codepoint",
        action="append",
        default=[],
        help="Unicode codepoint to retain (decimal or 0x-prefixed). Repeatable.",
    )
    p_web_grid_family.add_argument(
        "--range",
        action="append",
        default=[],
        help="Unicode range to retain in start-end form. Repeatable.",
    )
    p_web_grid_family.set_defaults(func=_cmd_web_grid_family)

    p_web_family = subparsers.add_parser(
        "web-family", help="Generate one shared family web package."
    )
    p_web_family.add_argument("file", help="Variable font file.")
    p_web_family.add_argument("output_dir", help="Output directory for the family package.")
    p_web_family.add_argument(
        "--instance-name",
        action="append",
        default=[],
        help="Named instance label to package. Repeatable.",
    )
    p_web_family.add_argument(
        "--all-named",
        action="store_true",
        help="Package all named instances from the font.",
    )
    p_web_family.add_argument(
        "--include-default",
        action="store_true",
        help="Also package the default coordinates.",
    )
    p_web_family.add_argument(
        "--family-name",
        help="Override the shared family package title.",
    )
    p_web_family.add_argument(
        "--preview-text",
        default="Hamburgefons 0123456789",
        help="Preview text for the generated family specimen HTML.",
    )
    p_web_family.add_argument(
        "--template",
        choices=("classic", "editorial", "lab"),
        default="classic",
        help="Specimen template to use for generated HTML/CSS (default: classic).",
    )
    p_web_family.add_argument(
        "--no-woff",
        action="store_true",
        help="Do not emit WOFF fallback output.",
    )
    p_web_family.add_argument(
        "--naming-strategy",
        choices=_NAMING_STRATEGY_CHOICES,
        default="instance-family",
        help="Naming policy for generated static family bundles (default: instance-family).",
    )
    p_web_family.add_argument(
        "--family-suffix",
        help="Optional custom suffix to append to generated family names.",
    )
    _add_naming_override_args(p_web_family)
    _add_stat_policy_arg(p_web_family)
    p_web_family.add_argument(
        "--preset",
        action="append",
        default=[],
        help="Subset preset name. Repeatable.",
    )
    p_web_family.add_argument(
        "--text",
        default="",
        help="Extra literal text to retain in the subset.",
    )
    p_web_family.add_argument(
        "--codepoint",
        action="append",
        default=[],
        help="Unicode codepoint to retain (decimal or 0x-prefixed). Repeatable.",
    )
    p_web_family.add_argument(
        "--range",
        action="append",
        default=[],
        help="Unicode range to retain in start-end form. Repeatable.",
    )
    p_web_family.set_defaults(func=_cmd_web_family)

    p_corpus_report = subparsers.add_parser(
        "corpus-report",
        help="Generate corpus manifest JSON with coverage metrics and failure taxonomy",
    )
    p_corpus_report.add_argument(
        "--output-dir",
        "-o",
        required=True,
        help="Output directory for corpus_manifest.json",
    )
    p_corpus_report.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output",
    )
    p_corpus_report.set_defaults(func=_cmd_corpus_report)

    p_performance = subparsers.add_parser(
        "performance-baseline",
        help="Run performance benchmarks and generate timing report",
    )
    p_performance.add_argument(
        "--output-dir",
        required=True,
        help="Output directory for performance-report.json",
    )
    p_performance.set_defaults(func=_cmd_performance_baseline)

    p_perf_var_package = subparsers.add_parser(
        "perf-var-package",
        help="Benchmark VariableInstanceBuilder.build_package workflow",
    )
    p_perf_var_package.add_argument(
        "--output-dir",
        required=True,
        help="Output directory for performance-var-package.json",
    )
    p_perf_var_package.set_defaults(func=_cmd_perf_var_package)

    p_ci_cff2_subset_perf = subparsers.add_parser(
        "ci-cff2-subset-performance",
        help="Benchmark CFF2 variable font subsetting performance",
    )
    p_ci_cff2_subset_perf.add_argument(
        "--output-dir",
        required=True,
        help="Output directory for performance-cff2-subset.json",
    )
    p_ci_cff2_subset_perf.set_defaults(func=_cmd_ci_cff2_subset_performance)

    p_ci_drift_alert = subparsers.add_parser(
        "ci-drift-alert",
        help="Check performance drift from a JSON report.",
    )
    p_ci_drift_alert.add_argument(
        "--report",
        required=True,
        metavar="FILE",
        help="Path to performance JSON report (e.g., performance-var-package.json).",
    )
    p_ci_drift_alert.set_defaults(func=_cmd_ci_drift_alert)

    p_capability = subparsers.add_parser(
        "capability",
        help="Generate a plain-language font capability report in JSON format.",
    )
    p_capability.add_argument("file", help="Path to font file.")
    p_capability.add_argument(
        "--json-output",
        help="Write the capability report JSON to this path. If omitted, JSON is printed to stdout.",
    )
    p_capability.set_defaults(func=_cmd_capability)

    p_visual_proof = subparsers.add_parser(
        "visual-proof",
        help="Generate a unified visual proof package (animation + coverage + capability).",
        description="Generate a unified visual proof package containing animation sweep, "
        "designspace coverage, visual diff overlay, and plain-language capability report.",
    )
    p_visual_proof.add_argument(
        "--input",
        help="Input designspace directory (takes precedence over --font).",
    )
    p_visual_proof.add_argument(
        "font",
        nargs="?",
        default=None,
        help="Path to font file (ignored if --input is provided).",
    )
    p_visual_proof.add_argument(
        "-o",
        "--output",
        default="visual-proof-output",
        help="Output directory (default: visual-proof-output).",
    )
    p_visual_proof.set_defaults(func=_cmd_visual_proof)

    # Autonomous development subcommand
    p_autonomous_dev = subparsers.add_parser(
        "autonomous-dev",
        help="Run autonomous development workflow on a font.",
        description="Execute the full autonomous development pipeline, generating QA, instances, and optional WOFF output.",
    )
    p_autonomous_dev.add_argument("font_path", help="Path to the input font file.")
    p_autonomous_dev.add_argument(
        "--output-dir",
        default=".",
        help="Directory to write output files (default: current directory).",
    )
    p_autonomous_dev.add_argument(
        "--no-qa",
        action="store_true",
        help="Skip QA report generation.",
    )
    p_autonomous_dev.add_argument(
        "--no-instances",
        action="store_true",
        help="Skip generating variable instances.",
    )
    p_autonomous_dev.add_argument(
        "--include-woff",
        action="store_true",
        help="Include WOFF fallback output.",
    )
    p_autonomous_dev.add_argument(
        "--preset",
        action="append",
        default=[],
        help="Subset preset name (repeatable).",
    )
    p_autonomous_dev.add_argument(
        "--naming-strategy",
        choices=_NAMING_STRATEGY_CHOICES,
        help="Naming strategy for generated instances.",
    )
    p_autonomous_dev.add_argument("--custom-family-suffix", help="Custom family suffix.")
    p_autonomous_dev.add_argument("--legacy-family", help="Legacy family name.")
    p_autonomous_dev.add_argument("--legacy-style", help="Legacy style name.")
    p_autonomous_dev.add_argument("--typographic-family", help="Typographic family name.")
    p_autonomous_dev.add_argument("--typographic-style", help="Typographic style name.")
    p_autonomous_dev.add_argument(
        "--stat-policy",
        choices=_STAT_POLICY_CHOICES,
        help="STAT metadata policy.",
    )
    p_autonomous_dev.add_argument(
        "--font-display",
        choices=("auto", "block", "swap", "fallback", "optional"),
        default="swap",
        help="CSS font-display property (default: swap).",
    )
    p_autonomous_dev.add_argument(
        "--cdn-manifest",
        action="store_true",
        help="Generate CDN manifest.",
    )
    p_autonomous_dev.add_argument(
        "--cdn-base",
        default="https://cdn.example.com",
        help="Base URL for CDN manifest (default: https://cdn.example.com).",
    )
    p_autonomous_dev.add_argument(
        "--json-summary",
        help="Write unified autonomous development summary to this JSON file path.",
    )
    p_autonomous_dev.set_defaults(func=_cmd_autonomous_dev)

    _attach_collection_index_args(subparsers)

    args = parser.parse_args()

    if args.performance_check:
        script_dir = Path(__file__).resolve().parent
        project_root = script_dir.parent.parent
        fixture_root = project_root / "testdata" / "Fonts"
        if not fixture_root.exists():
            fixture_root = project_root / "testdata"

        try:
            report = run_ci_benchmarks(fixture_root, baseline_margin_percent=5.0)
        except PerformanceRegressionError as exc:
            print(f"Performance regression detected: {exc}", file=sys.stderr)
            for metric in exc.metrics:
                print(
                    f"  {metric.name}: {metric.elapsed_ms:.2f}ms exceeds "
                    f"threshold {metric.threshold_ms:.2f}ms",
                    file=sys.stderr,
                )
            sys.exit(1)

        output_path = Path(args.perf_output) if args.perf_output else None

        if output_path:
            output_path.write_text(
                json.dumps(report.summary, indent=2, sort_keys=True),
                encoding="utf-8",
            )
            print(f"Performance regression report written to: {output_path}")
        else:
            print(json.dumps(report.summary, indent=2, sort_keys=True))

        sys.exit(0)

    if args.command is None:
        parser.print_help()
        sys.exit(0)
    args.func(args)


def _cmd_corpus_report(args: argparse.Namespace) -> None:
    """Generate corpus manifest JSON."""
    from pathlib import Path

    from aspose_font.corpus_manifest import build_corpus_manifest

    manifest = build_corpus_manifest()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest.write_to(output_dir / "corpus_manifest.json")

    if args.verbose:
        print(f"Corpus manifest written to {output_dir / 'corpus_manifest.json'}")


def _cmd_performance_baseline(args: argparse.Namespace) -> None:
    """Run performance benchmarks and generate timing report."""
    from datetime import datetime, timezone
    from pathlib import Path

    from aspose_font.performance import BENCHMARKS, run_performance_regression_check

    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent.parent
    font_path = project_root / "testdata" / "Roboto-Regular.ttf"
    if not font_path.exists():
        font_path = project_root / "testdata" / "Roboto-VariableFont_wdth,wght.ttf"

    report_package = run_performance_regression_check(
        font_path=font_path,
        benchmarks=BENCHMARKS,
    )

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    report_path = output_dir / "performance-report.json"
    output_dict = {
        "operation": "performance-baseline",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "workflow": report_package.report.workflow_name,
        "statistics": report_package.report.statistics,
        "threshold_ms": report_package.report.threshold_ms,
        "passing": report_package.report.passing,
        "deviation_percent": report_package.report.deviation_percent,
        "root_causes": report_package.report.root_causes,
        "remediation_notes": report_package.remediation_notes,
        "metadata": report_package.metadata,
    }

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(output_dict, f, indent=2)

    print(f"Performance report written to {report_path}")
    print(f"Status: {'PASS' if report_package.report.passing else 'FAIL'}")
    print(f"Mean latency: {report_package.report.statistics.get('mean', 0):.2f}ms")
    print(f"Threshold: {report_package.report.threshold_ms}ms")


def _cmd_perf_var_package(args: argparse.Namespace) -> None:
    """Benchmark VariableInstanceBuilder.build_package workflow."""
    script_dir = Path(__file__).resolve()

    def _find_project_root() -> Path | None:
        for parents_level in range(1, 6):
            candidate = script_dir.parents[parents_level]
            if (candidate / "testdata").exists():
                return candidate
        return None

    project_root = _find_project_root()

    if project_root is None:
        project_root = script_dir.parents[2]

    fixture_root = project_root / "testdata" / "Fonts"
    if not fixture_root.exists():
        fixture_root = project_root / "testdata"

    metric = perf_var_package.benchmark_var_package(fixture_root)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    report_path = output_dir / "performance-var-package.json"
    output_dict = {
        "build_time_ms": metric.elapsed_ms,
        "threshold_ms": metric.threshold_ms,
        "within_threshold": metric.passed,
        "status": "pass" if metric.passed else "fail",
        "baseline_ms": metric.baseline_ms,
        "variance_percent": metric.variance_percent,
    }

    report_path.write_text(json.dumps(output_dict, indent=2, sort_keys=True), encoding="utf-8")
    print(f"Performance report written to: {report_path}")
    print(f"Build time: {metric.elapsed_ms:.2f}ms")
    print(f"Threshold: {metric.threshold_ms}ms")
    print(f"Status: {'PASS' if metric.passed else 'FAIL'}")


def _cmd_ci_cff2_subset_performance(args: argparse.Namespace) -> None:
    """Benchmark CFF2 variable font subsetting and write JSON report."""
    script_dir = Path(__file__).resolve()

    def _find_project_root() -> Path | None:
        for parents_level in range(1, 6):
            candidate = script_dir.parents[parents_level]
            if (candidate / "testdata").exists():
                return candidate
        return None

    project_root = _find_project_root()
    if project_root is None:
        project_root = script_dir.parents[2]

    fixture_root = project_root / "testdata" / "Fonts"
    if not fixture_root.exists():
        fixture_root = project_root / "testdata"

    metric = perf_cff2_subsetter.benchmark_cff2_subsetter(fixture_root)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    report_path = output_dir / "performance-cff2-subset.json"
    output_dict = {
        "build_time_ms": metric.get("build_time_ms"),
        "threshold_ms": metric.get("threshold_ms"),
        "within_threshold": metric.get("within_threshold"),
    }
    report_path.write_text(json.dumps(output_dict, indent=2, sort_keys=True), encoding="utf-8")
    print(f"Performance report written to: {report_path}")
    print(f"Build time: {metric.get('build_time_ms'):.2f}ms")
    print(f"Threshold: {metric.get('threshold_ms'):.2f}ms")
    print(f"Status: {'PASS' if metric.get('within_threshold') else 'FAIL'}")
    raise SystemExit(0 if metric.get('within_threshold') else 1)

def _cmd_ci_drift_alert(args: argparse.Namespace) -> None:
    """Check performance drift from a JSON report."""
    try:
        result = alert.check_drift(args.report)
    except (FileNotFoundError, ValueError) as exc:
        _die(str(exc))

    print(result["message"])

    if result["drift"]:
        sys.exit(1)
    sys.exit(0)


def _cmd_cff2_list_axes(args: argparse.Namespace) -> None:
    try:
        font = _load_cff2_font(args)
    except Exception as exc:
        _die(str(exc))

    axes = font.list_axes()

    if not axes:
        print("No variable axes found.")
        return

    print("Variable Axes:")
    print("-" * 60)
    for ax in axes:
        print(f"  {ax.tag:6s}  {ax.label}")
        print(f"    Min:  {ax.min_value}")
        print(f"    Default:  {ax.default_value}")
        print(f"    Max:  {ax.max_value}")
        if ax.is_hidden:
            print("    (hidden)")


def _cmd_cff2_instantiate(args: argparse.Namespace) -> None:
    try:
        font = _load_cff2_font(args)
    except Exception as exc:
        _die(str(exc))

    coords = _parse_instance(args.coordinates)

    try:
        static_font = font.instantiate(coords)
    except NotImplementedError as exc:
        _die(f"Instantiation not yet implemented: {exc}")

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    output_format = args.output_format.lower()
    if output_format == "ttf":
        serialized = static_font.to_bytes(FontType.TTF)
    elif output_format == "otf":
        serialized = static_font.to_bytes(FontType.OTF)
    else:
        serialized = static_font.to_bytes(FontType.CFF)

    output_path.write_bytes(serialized)
    print(f"Written: {args.output} ({len(serialized)} bytes)")


def _load_cff2_font(args: argparse.Namespace) -> Cff2Font:
    path = Path(args.file)
    data = path.read_bytes()
    return Cff2Font(data)


def _cmd_subset(args: argparse.Namespace) -> None:
    import json

    input_path = Path(args.file)
    output_path = Path(args.output)

    font = FontLoader.open(input_path)

    has_gvar = hasattr(font, "ttf_tables") and font.ttf_tables._raw.get("gvar") is not None
    has_hvar = hasattr(font, "ttf_tables") and font.ttf_tables._raw.get("HVAR") is not None

    original_gvar_size = len(font.ttf_tables._raw.get("gvar", b"")) if has_gvar else 0
    original_hvar_size = len(font.ttf_tables._raw.get("HVAR", b"")) if has_hvar else 0

    subset_codepoints: set[int] = set()

    if args.text:
        subset_codepoints.update(ord(ch) for ch in args.text)

    if args.glyphs:
        for gid_str in args.glyphs.split(","):
            try:
                subset_codepoints.add(int(gid_str.strip()))
            except ValueError:
                _die(f"Invalid glyph ID: {gid_str!r}")

    if args.preset:
        from aspose_font.subset_presets import codepoints_for_presets

        subset_codepoints.update(codepoints_for_presets(args.preset))

    if args.codepoint:
        for cp in args.codepoint:
            try:
                if cp.startswith("0x"):
                    subset_codepoints.add(int(cp[2:], 16))
                else:
                    subset_codepoints.add(int(cp))
            except ValueError:
                _die(f"Invalid codepoint: {cp!r}")

    if args.range:
        from aspose_font.subset_presets import expand_unicode_ranges

        ranges = []
        for r in args.range:
            if "-" not in r:
                _die(f"Invalid range: {r!r}. Expected start-end.")
            parts = r.split("-", 1)
            try:
                start = int(parts[0])
                end = int(parts[1])
                ranges.append((start, end))
            except ValueError:
                _die(f"Invalid range: {r!r}")
        subset_codepoints.update(expand_unicode_ranges(ranges))

    if getattr(args, "benchmark", False):
        benchmark_result = FontSubsetter.benchmark_subsetting(
            font, subset_codepoints, runs=1
        )
        elapsed = benchmark_result["elapsed_seconds"]
        print(f"Benchmark: {elapsed}s")

    if subset_codepoints:
        subsetted = FontSubsetter.subset(font, subset_codepoints, preserve_variation_tables=args.prune_deltas)
    elif isinstance(font, Cff2Font) and getattr(args, "cff2_subset", False):
        subsetted = FontSubsetter.subset_by_text(font, font.font_name or "ABCD")
    else:
        _die(
            "No subsetting criteria specified. Use --text, --glyphs, --preset, --codepoint, or --range"
        )

    output_bytes = subsetted.to_bytes()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(output_bytes)

    pruned_gvar = original_gvar_size - len(subsetted.ttf_tables._raw.get("gvar", b"")) if has_gvar else 0
    pruned_hvar = original_hvar_size - len(subsetted.ttf_tables._raw.get("HVAR", b"")) if has_hvar else 0

    original_count = font.num_glyphs
    subset_count = subsetted.num_glyphs
    print(f"Original: {original_count} glyphs, Subset: {subset_count} glyphs")
    print(f"Delta pruning: {'enabled' if args.prune_deltas else 'disabled'}")
    if has_gvar:
        print(f"gvar: {original_gvar_size} -> {original_gvar_size - pruned_gvar} bytes (saved {pruned_gvar})")
    if has_hvar:
        print(f"HVAR: {original_hvar_size} -> {original_hvar_size - pruned_hvar} bytes (saved {pruned_hvar})")
    print(f"Total delta bytes saved: {pruned_gvar + pruned_hvar}")
    print(f"Written: {args.output} ({len(output_bytes)} bytes)")

    manifest = {
        "pruned_tables": {
            "gvar": has_gvar,
            "HVAR": has_hvar,
        },
        "delta_bytes_saved": pruned_gvar + pruned_hvar,
    }
    manifest_path = output_path.with_suffix(output_path.suffix + ".manifest.json")
    manifest_path.write_text(json.dumps(manifest, indent=2))


def _cmd_web_subset(args: argparse.Namespace) -> None:
    input_path = Path(args.input)
    output_dir = Path(args.output)
    font = FontLoader.open(input_path)
    codepoints: set[int] = set()
    if getattr(args, "text", None):
        codepoints.update(ord(ch) for ch in args.text)
    if getattr(args, "codepoint", None):
        for cp in args.codepoint:
            try:
                if cp.startswith("0x"):
                    codepoints.add(int(cp[2:], 16))
                else:
                    codepoints.add(int(cp))
            except ValueError:
                _die(f"Invalid codepoint: {cp!r}")
    if getattr(args, "range", None):
        from aspose_font.subset_presets import expand_unicode_ranges
        ranges = []
        for r in args.range:
            if "-" not in r:
                _die(f"Invalid range: {r!r}. Expected start-end.")
            parts = r.split("-", 1)
            try:
                start = int(parts[0])
                end = int(parts[1])
                ranges.append((start, end))
            except ValueError:
                _die(f"Invalid range: {r!r}")
        codepoints.update(expand_unicode_ranges(ranges))
    if not codepoints:
        _die("No subset criteria specified. Use --text, --codepoint, or --range.")
    subsetted = FontSubsetter.subset_variable_font(font, codepoints)
    from aspose_font import WebFontBuilder
    bundle = WebFontBuilder.build(
        subsetted,
        file_stem=args.stem,
        include_woff=not args.no_woff,
        preview_text=args.preview_text,
        specimen_template=args.template,
        variable_mode="auto",
    )
    bundle.manifest["subset_preservation"] = True
    written = bundle.write_to(output_dir)
    print(f"Subsetted font: {subsetted.num_glyphs} glyphs (original: {font.num_glyphs})")
    print(f"Export mode: {bundle.manifest.get('export_mode', 'unknown')}")
    _print_coverage_summary(bundle.manifest)
    for path in written:
        print(f"Written: {path}")


def _add_web_subset_parser(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "web-subset",
        help="Subset a font while preserving variation tables and generate web assets",
        description="Subset a font by codepoints while preserving variable font variation tables (gvar, HVAR, avar, MVAR, VVAR, cvar) and generate a web-ready package (WOFF2/WOFF, CSS, specimen HTML, optimizer-manifest.json).",
    )
    parser.add_argument("input", help="Input font file")
    parser.add_argument("output", help="Output directory for web assets")
    parser.add_argument("--text", help="Text to subset (Unicode characters)")
    parser.add_argument("--codepoint", nargs="+", help="Unicode codepoints (e.g., 0x0041 0x0042)")
    parser.add_argument("--range", nargs="+", help="Unicode ranges (e.g., 0x0041-0x005A)")
    parser.add_argument("--stem", default="subset", help="Output file stem")
    parser.add_argument("--no-woff", action="store_true", help="Skip WOFF generation")
    parser.add_argument("--preview-text", default=_DEFAULT_PREVIEW_TEXT, help="Preview text")
    parser.add_argument("--template", choices=_SPECIMEN_TEMPLATES, default="classic", help="Specimen template")
    parser.set_defaults(func=_cmd_web_subset)


def _add_subset_parser(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "subset",
        help="Subset a font by removing unused glyphs",
        description="Subset a font by removing unused glyphs. Supports text, glyph IDs, presets, codepoints, and ranges.",
    )
    parser.add_argument("file", help="Input font file path")
    parser.add_argument("output", help="Output font file path")
    parser.add_argument("--text", help="Text to subset (Unicode characters)")
    parser.add_argument(
        "--glyphs", help="Comma-separated glyph IDs to subset (e.g., 1,2,3)"
    )
    parser.add_argument(
        "--preset",
        choices=["latin", "latin-ext", "cyrillic", "greek", "greek-ext"],
        help="Predefined codepoint preset",
    )
    parser.add_argument(
        "--codepoint", nargs="+", help="Unicode codepoints (e.g., 0x0041 0x0042)"
    )
    parser.add_argument(
        "--range", nargs="+", help="Unicode ranges (e.g., 0x0041-0x005A)"
    )
    parser.add_argument(
        "--cff2-subset",
        action="store_true",
        help="Use CFF2 text-based subset (for CFF2 fonts).",
    )
    parser.add_argument(
        "--benchmark",
        action="store_true",
        help="Run benchmark and report subsetting time.",
    )
    parser.add_argument(
        "--prune-deltas",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Prune delta variations during subsetting (default: True)",
    )
    parser.set_defaults(func=_cmd_subset)


def _add_cff2_instantiate_parser(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "cff2-instantiate",
        help="Instantiate CFF2 variable font at given coordinates",
        description="Instantiate a CFF2 variable font at specified axis coordinates.",
    )
    parser.add_argument("file", help="Input CFF2 font file path")
    parser.add_argument(
        "coordinates",
        nargs="+",
        metavar="TAG=VALUE",
        help="Axis coordinates (e.g., wght=400 wdth=100)",
    )
    parser.add_argument("-o", "--output", required=True, help="Output font file path")
    parser.add_argument(
        "-f",
        "--output-format",
        choices=["ttf", "otf", "cff"],
        default="cff",
        help="Output format (default: cff)",
    )
    parser.set_defaults(func=_cmd_cff2_instantiate)


def _add_var_partial_instance_parser(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "var-partial-instance",
        help="Create partial static instance of variable font by locking axis coordinates",
        description="Create a partial static instance of a variable font by locking specific axis coordinates while keeping other axes variable.",
    )
    parser.add_argument("file", help="Input variable font file path")
    parser.add_argument("output", help="Output font file path")
    parser.add_argument(
        "--lock-axis",
        nargs="+",
        metavar="TAG=VALUE",
        required=True,
        help="Axis coordinates to lock (e.g., wght=400 wdth=100). At least one required.",
    )
    parser.add_argument(
        "--naming-strategy",
        choices=_NAMING_STRATEGY_CHOICES,
        default="instance-family",
        help="Naming strategy for generated instance (default: instance-family).",
    )
    parser.add_argument(
        "--family-suffix",
        help="Additive suffix appended to family name.",
    )
    _add_naming_override_args(parser)
    _add_stat_policy_arg(parser)
    parser.set_defaults(func=_cmd_var_partial_instance)

def _add_var_partial_web_parser(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "var-partial-web",
        help="Create a partial instance and build a web bundle in one step",
        description=(
            "Lock specific axes, write the resulting static font to the output directory, "
            "and run the standard web-font export on that font."
        ),
    )
    parser.add_argument("file", help="Input variable font file path")
    parser.add_argument("output_dir", help="Directory where the partial TTF and web bundle are written")
    parser.add_argument(
        "--lock-axis",
        nargs="+",
        metavar="TAG=VALUE",
        required=True,
        help="Axis coordinates to lock (e.g. wght=400 wdth=100). At least one required.",
    )
    parser.add_argument("--stem", help="Custom output file stem for the web bundle")
    parser.add_argument(
        "--preview-text",
        default="Hamburgefons 0123456789",
        help="Preview text for the specimen HTML",
    )
    parser.add_argument(
        "--template",
        choices=("classic", "editorial", "lab"),
        default="classic",
        help="Specimen template",
    )
    parser.add_argument(
        "--variable-mode",
        choices=("auto", "live", "static"),
        default="auto",
        help="Variable-font export mode",
    )
    parser.add_argument(
        "--naming-strategy",
        choices=_NAMING_STRATEGY_CHOICES,
        default="instance-family",
        help="Naming policy for static exports",
    )
    parser.add_argument(
        "--family-suffix",
        help="Custom suffix appended to generated family names",
    )
    _add_naming_override_args(parser)
    _add_stat_policy_arg(parser)
    parser.add_argument(
        "--no-woff",
        action="store_true",
        help="Do not emit WOFF fallback output",
    )
    parser.add_argument(
        "--preset",
        action="append",
        default=[],
        help="Subset preset name (repeatable)",
    )
    parser.add_argument("--text", default="", help="Extra literal text to retain in the subset")
    parser.add_argument(
        "--codepoint",
        action="append",
        default=[],
        help="Unicode codepoint to retain (decimal or 0x-prefixed)",
    )
    parser.add_argument(
        "--range",
        action="append",
        default=[],
        help="Unicode range to retain (repeatable)",
    )
    parser.add_argument(
        "--instance",
        action="append",
        default=[],
        help="Variable-font axis coordinate (tag=value) for the web build",
    )
    parser.add_argument("--instance-name", help="Named instance label to export directly")
    parser.add_argument(
        "--preserve-variable",
        action="store_true",
        help="Preserve variable tables when subsetting",
    )
    parser.set_defaults(func=_cmd_var_partial_web)



def _cmd_var_partial_instance(args: argparse.Namespace) -> None:
    try:
        font = _require_variable_ttf(_load_font(args))
    except Exception as exc:
        _die(str(exc))

    try:
        lock_axes = _parse_instance_comma_separated(",".join(args.lock_axis))
    except ValueError as exc:
        _die(str(exc))

    try:
        partial_font = font.smart_instancer.partial_instantiate(
            lock_axes=lock_axes,
            naming_strategy=args.naming_strategy,
            family_suffix=args.family_suffix,
            **_naming_override_kwargs(args),
            stat_policy=args.stat_policy,
        )
    except Exception as exc:
        _die(str(exc))

    try:
        with open(args.output, "wb") as f:
            f.write(partial_font.to_bytes())
    except OSError as exc:
        _die(f"Cannot write to {args.output!r}: {exc}")

    locked_tags = ", ".join(f"{tag}={val}" for tag, val in sorted(lock_axes.items()))
    print(f"Locked axes: {locked_tags}")
    print(f"Output: {args.output}")

def _cmd_var_partial_web(args: argparse.Namespace) -> None:
    try:
        font = _require_variable_ttf(_load_font(args))
    except Exception as exc:
        _die(str(exc))

    try:
        lock_axes = _parse_instance_comma_separated(",".join(args.lock_axis))
    except ValueError as exc:
        _die(str(exc))

    try:
        partial_font = font.smart_instancer.partial_instantiate(
            lock_axes=lock_axes,
            naming_strategy=args.naming_strategy,
            family_suffix=args.family_suffix,
            **_naming_override_kwargs(args),
            stat_policy=args.stat_policy,
        )
    except Exception as exc:
        _die(str(exc))

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    partial_path = out_dir / f"{Path(args.file).stem}-partial.ttf"
    try:
        with open(partial_path, "wb") as f:
            f.write(partial_font.to_bytes())
    except OSError as exc:
        _die(f"Cannot write partial font {partial_path!r}: {exc}")

    codepoints = [_parse_cli_int(v) for v in args.codepoint]
    ranges = [_parse_range(v) for v in args.range]
    instance_coords = _parse_instance(args.instance) if args.instance else None

    try:
        bundle = WebFontBuilder.build(
            partial_font,
            file_stem=args.stem,
            include_woff=not args.no_woff,
            preview_text=args.preview_text,
            specimen_template=args.template,
            variable_mode=args.variable_mode,
            naming_strategy=args.naming_strategy,
            family_suffix=args.family_suffix,
            stat_policy=args.stat_policy,
            **_naming_override_kwargs(args),
            instance_coordinates=instance_coords,
            instance_name=args.instance_name,
            presets=args.preset,
            text=args.text,
            codepoints=codepoints,
            ranges=ranges,
            preserve_variable=args.preserve_variable,
        )
        written = bundle.write_to(str(out_dir))
    except Exception as exc:
        _die(str(exc))

    locked = ", ".join(f"{k}={v}" for k, v in sorted(lock_axes.items()))
    print(f"Locked axes: {locked}")
    print(f"Partial font written to: {partial_path}")
    _print_web_export_summary(bundle.manifest)
    for p in written:
        print(f"Written: {p}")



if __name__ == "__main__":
    main()
