"""CLI for aspose-font - font inspection, conversion, and web export."""
from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Iterable

from aspose_font import (
    FontCleaner,
    FontLoader,
    FontPreviewBuilder,
    FontType,
    TtfFont,
    WebFontBuilder,
    __version__,
)
from aspose_font.converter import FontConverter

_NAMING_STRATEGY_CHOICES = TtfFont.available_naming_strategies()

_FORMAT_MAP: dict[str, FontType] = {
    "ttf": FontType.TTF,
    "cff": FontType.CFF,
    "woff": FontType.WOFF,
    "woff2": FontType.WOFF2,
    "eot": FontType.EOT,
}


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


def _naming_override_kwargs(args: argparse.Namespace) -> dict[str, str | None]:
    return {
        "legacy_family_name": args.legacy_family_name,
        "typographic_family_name": args.typographic_family_name,
        "legacy_style_name": args.legacy_style_name,
        "typographic_style_name": args.typographic_style_name,
    }


def _attach_collection_index_args(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    for parser in subparsers.choices.values():
        has_file_arg = any(
            action.dest == "file" and not action.option_strings
            for action in parser._actions
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
        f"{tag}={_format_axis_value(value)}"
        for tag, value in sorted(coordinates.items())
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
            print(f"Missing in {group.get('kind', 'group')} {group.get('label', '')}: {group_sample}")


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
            **_naming_override_kwargs(args),
            instance_coordinates=coordinates,
            instance_name=args.instance_name,
            presets=args.preset,
            text=args.text,
            codepoints=codepoints,
            ranges=ranges,
        )
        written = bundle.write_to(args.output_dir)
    except Exception as exc:
        _die(str(exc))

    _print_web_export_summary(bundle.manifest)
    for path in written:
        print(f"Written: {path}")


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
                resolved = _require_variable_ttf(font).smart_instancer.resolve(instance_name=instance_name)
                steps.append(AnimationStep(coordinates=resolved.coordinates, label=resolved.label))
            else:
                steps.append(AnimationStep(coordinates=dict(coordinates or {}), label=_coordinate_label(dict(coordinates or {}))))
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
                resolved = _require_variable_ttf(font).smart_instancer.resolve(instance_name=instance_name)
                steps.append(AnimationStep(coordinates=resolved.coordinates, label=resolved.label))
            else:
                steps.append(AnimationStep(coordinates=dict(coordinates or {}), label=_coordinate_label(dict(coordinates or {}))))
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
                resolved = _require_variable_ttf(font).smart_instancer.resolve(instance_name=instance_name)
                steps.append(AnimationStep(coordinates=resolved.coordinates, label=resolved.label))
            else:
                steps.append(AnimationStep(coordinates=dict(coordinates or {}), label=_coordinate_label(dict(coordinates or {}))))
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
                resolved = _require_variable_ttf(font).smart_instancer.resolve(instance_name=instance_name)
                steps.append(AnimationStep(coordinates=resolved.coordinates, label=resolved.label))
            else:
                steps.append(AnimationStep(coordinates=dict(coordinates or {}), label=_coordinate_label(dict(coordinates or {}))))
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
        before_coordinates = _parse_symbolic_instance(args.before_instance) if args.before_instance else None
        after_coordinates = _parse_symbolic_instance(args.after_instance) if args.after_instance else None
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
        before_coordinates = _parse_symbolic_instance(args.before_instance) if args.before_instance else None
        after_coordinates = _parse_symbolic_instance(args.after_instance) if args.after_instance else None
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
        summary = "; ".join(_format_component_movement(movement) for movement in report.component_movements[:4])
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
        glyph_label = f"U+{glyph_report.codepoint:04X}" if glyph_report.codepoint is not None else f"GID {glyph_report.glyph_id}"
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
        before_coordinates = _parse_symbolic_instance(args.before_instance) if args.before_instance else None
        after_coordinates = _parse_symbolic_instance(args.after_instance) if args.after_instance else None
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
        before_coordinates = _parse_symbolic_instance(args.before_instance) if args.before_instance else None
        after_coordinates = _parse_symbolic_instance(args.after_instance) if args.after_instance else None
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
        before_coordinates = _parse_symbolic_instance(args.before_instance) if args.before_instance else None
        after_coordinates = _parse_symbolic_instance(args.after_instance) if args.after_instance else None
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
            + "; ".join(_format_component_movement(movement) for movement in report.before.component_movements[:4])
        )
    if report.after.component_movements:
        print(
            "After components:  "
            + "; ".join(_format_component_movement(movement) for movement in report.after.component_movements[:4])
        )
    if report.note:
        print(f"Note:              {report.note}")


def _cmd_var_delta_compare_board(args: argparse.Namespace) -> None:
    try:
        font = _require_variable_ttf(_load_font(args))
        before_coordinates = _parse_symbolic_instance(args.before_instance) if args.before_instance else None
        after_coordinates = _parse_symbolic_instance(args.after_instance) if args.after_instance else None
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
        fallback = _format_localization_resolution(axis.localization_resolution(preferred_languages))
        if fallback:
            print(f"    {fallback}")
        if args.language:
            coverage = _format_localization_coverage(axis.localization_coverage(preferred_languages))
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
                f"{preset.name}={axis.format_value(preset.value)}"
                for preset in axis.presets
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
        fallback = _format_localization_resolution(instance.localization_resolution(preferred_languages))
        if fallback:
            print(f"    {fallback}")
        if args.language:
            coverage = _format_localization_coverage(instance.localization_coverage(preferred_languages))
            if coverage:
                print(f"    {coverage}")
        if len(instance.available_languages) > 1:
            localized = ", ".join(
                f"{language}={value}"
                for language, value in instance.localized_labels(preferred_languages)
            )
            print(f"    Localized labels: {localized}")
    if args.json_output:
        print(f"Saved JSON: {args.json_output}")


def _cmd_var_instance(args: argparse.Namespace) -> None:
    try:
        font = _require_variable_ttf(_load_font(args))
        coordinates = _parse_symbolic_instance(args.instance) if args.instance else None
        instantiated = font.smart_instancer.instantiate(
            coordinates,
            instance_name=args.instance_name,
            naming_strategy=args.naming_strategy,
            family_suffix=args.family_suffix,
            legacy_family_name=args.legacy_family_name,
            typographic_family_name=args.typographic_family_name,
            legacy_style_name=args.legacy_style_name,
            typographic_style_name=args.typographic_style_name,
        )
        instantiated.save(args.output)
    except Exception as exc:
        _die(str(exc))

    print(f"Saved: {args.output}")


def _cmd_var_naming_preview(args: argparse.Namespace) -> None:
    try:
        font = _require_variable_ttf(_load_font(args))
        coordinates = _parse_symbolic_instance(args.instance) if args.instance else None
        preview = font.smart_instancer.preview_naming_policy(
            coordinates,
            instance_name=args.instance_name,
            naming_strategy=args.naming_strategy,
            family_suffix=args.family_suffix,
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
        print("STAT diagnostics:")
        print(f"  Source STAT: {'yes' if stat.source_has_stat else 'no'}")
        print(f"  Static export action: {stat.static_export_action}")
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
    strongest = "-" if movement.strongest_point_index is None else f"#{movement.strongest_point_index}"
    local_strongest = (
        "-" if movement.local_strongest_point_index is None else f"#{movement.local_strongest_point_index}"
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


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="aspose-font",
        description="Pure-Python font inspection and conversion tool.",
    )
    parser.add_argument("--version", action="version", version=f"aspose-font {__version__}")
    subparsers = parser.add_subparsers(dest="command", metavar="command")

    p_info = subparsers.add_parser("info", help="Print font metadata.")
    p_info.add_argument("file", help="Path to font file.")
    p_info.set_defaults(func=_cmd_info)

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
    p_web.set_defaults(func=_cmd_web_build)

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

    p_preview_batch = subparsers.add_parser("preview-batch", help="Render multiple PNG previews from a variable font.")
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

    from aspose_font.animation import AnimationPreviewBuilder

    p_preview_animation = subparsers.add_parser("preview-animation", help="Render an Animated PNG (APNG) sweeping a variable-font axis.")
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

    p_preview_grid = subparsers.add_parser("preview-grid", help="Render axis-grid PNG previews from a variable font.")
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

    p_preview_grid_sheet = subparsers.add_parser("preview-grid-sheet", help="Render one composite PNG sheet for a variable-font axis sweep.")
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

    p_preview_compare = subparsers.add_parser("preview-compare", help="Render a before/after comparison board for a variable font.")
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
    p_preview_waterfall.add_argument("output", help="Output PNG file path.")
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
    p_preview_waterfall.set_defaults(func=_cmd_preview_waterfall)

    p_preview_matrix = subparsers.add_parser(
        "preview-matrix",
        help="Render a standalone matrix PNG for selected variable-font instances.",
    )
    p_preview_matrix.add_argument("file", help="Variable font file.")
    p_preview_matrix.add_argument("output", help="Output PNG file path.")
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

    p_var_info = subparsers.add_parser("var-info", help="Print variable font axes and named instances.")
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
    p_var_info.set_defaults(func=_cmd_var_info)

    p_var_instance = subparsers.add_parser("var-instance", help="Create a static instance from a variable font.")
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
    p_var_instance.set_defaults(func=_cmd_var_instance)

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
    p_var_naming_preview.add_argument(
        "--json-output",
        help="Write the naming preview payload to this JSON file.",
    )
    p_var_naming_preview.set_defaults(func=_cmd_var_naming_preview)

    p_var_batch = subparsers.add_parser("var-batch", help="Create multiple static instances from a variable font.")
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
    p_var_batch.set_defaults(func=_cmd_var_batch)

    p_web_batch = subparsers.add_parser("web-batch", help="Generate multiple named-instance web bundles.")
    p_web_batch.add_argument("file", help="Variable font file.")
    p_web_batch.add_argument("output_dir", help="Output directory for generated web bundle folders.")
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

    p_web_grid = subparsers.add_parser("web-grid", help="Generate web bundles for a variable-font axis sweep.")
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

    p_web_family = subparsers.add_parser("web-family", help="Generate one shared family web package.")
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

    _attach_collection_index_args(subparsers)

    args = parser.parse_args()
    if args.command is None:
        parser.print_help()
        sys.exit(0)
    args.func(args)


if __name__ == "__main__":
    main()
