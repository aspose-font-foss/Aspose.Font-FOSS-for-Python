"""MCP server for aspose_font — run with: python -m aspose_font.mcp."""

from __future__ import annotations

try:
    from mcp.server.fastmcp import FastMCP
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "aspose_font MCP server requires 'mcp' package: pip install aspose-font[mcp]"
    ) from exc

from aspose_font import FontLoader, FontType
from aspose_font._types import CurveTo, LineTo, MoveTo, QuadraticTo
from aspose_font.converter import FontConverter
from aspose_font.subsetter import FontSubsetter
from aspose_font.text import TextRenderer
from aspose_font.ttf.font import TtfFont
from aspose_font.web import WebFontBuilder

mcp = FastMCP("aspose-font")

_TARGET_FORMAT_MAP = {
    "ttf": FontType.TTF,
    "cff": FontType.CFF,
    "woff": FontType.WOFF,
    "woff2": FontType.WOFF2,
    "eot": FontType.EOT,
}


def _err(exc: Exception | str) -> dict:
    return {"error": str(exc)}


def _normalize_ranges(ranges: list[list[int]] | None) -> list[tuple[int, int]]:
    normalized: list[tuple[int, int]] = []
    for item in ranges or []:
        if len(item) != 2:
            raise ValueError(f"Invalid range {item!r}. Expected [start, end].")
        start, end = int(item[0]), int(item[1])
        if start > end:
            raise ValueError(f"Invalid range {item!r}. Start must be <= end.")
        normalized.append((start, end))
    return normalized


@mcp.tool()
def font_info(path: str) -> dict:
    """Return metadata for the font at the given file path."""
    try:
        font = FontLoader.open(path)
        metrics = font.metrics
        result = {
            "format": font.font_type.value,
            "name": font.font_name,
            "family": font.font_family,
            "style": font.font_style,
            "num_glyphs": font.num_glyphs,
            "units_per_em": metrics.units_per_em,
            "ascender": metrics.ascender,
            "descender": metrics.descender,
            "line_gap": metrics.line_gap,
            "advance_width_max": metrics.advance_width_max,
            "is_variable": False,
            "axes": [],
        }
        if isinstance(font, TtfFont) and font.is_variable:
            result["is_variable"] = True
            result["axes"] = [
                {
                    "tag": axis.tag,
                    "min": axis.min_value,
                    "default": axis.default_value,
                    "max": axis.max_value,
                }
                for axis in font.axes
            ]
        return result
    except Exception as exc:
        return _err(exc)


@mcp.tool()
def font_convert(input_path: str, output_path: str, target_format: str) -> dict:
    """Convert a font to the specified format and save it."""
    try:
        fmt = target_format.lower()
        if fmt not in _TARGET_FORMAT_MAP:
            supported = ", ".join(_TARGET_FORMAT_MAP.keys())
            return _err(f"Unsupported target format: {target_format!r}. Supported: {supported}")
        font = FontLoader.open(input_path)
        converted = FontConverter.convert(font, _TARGET_FORMAT_MAP[fmt])
        data = converted.to_bytes()
        with open(output_path, "wb") as f:
            f.write(data)
        return {
            "success": True,
            "output_path": output_path,
            "bytes_written": len(data),
        }
    except Exception as exc:
        return _err(exc)


@mcp.tool()
def glyph_outline(path: str, codepoint: int) -> dict:
    """Return the glyph outline commands for a Unicode codepoint."""
    try:
        font = FontLoader.open(path)
        gid = font.encoding.unicode_to_gid(codepoint)
        glyph = font.glyph_accessor.get_glyph_by_id(gid)
        commands: list[dict] = []
        if glyph.path is not None:
            for cmd in glyph.path:
                if isinstance(cmd, MoveTo):
                    commands.append({"type": "MoveTo", "x": cmd.x, "y": cmd.y})
                elif isinstance(cmd, LineTo):
                    commands.append({"type": "LineTo", "x": cmd.x, "y": cmd.y})
                elif isinstance(cmd, QuadraticTo):
                    commands.append(
                        {
                            "type": "QuadraticTo",
                            "x1": cmd.x1,
                            "y1": cmd.y1,
                            "x": cmd.x,
                            "y": cmd.y,
                        }
                    )
                elif isinstance(cmd, CurveTo):
                    commands.append(
                        {
                            "type": "CurveTo",
                            "x1": cmd.x1,
                            "y1": cmd.y1,
                            "x2": cmd.x2,
                            "y2": cmd.y2,
                            "x": cmd.x,
                            "y": cmd.y,
                        }
                    )
                else:
                    commands.append({"type": type(cmd).__name__})
        return {
            "glyph_id": int(gid),
            "glyph_name": glyph.glyph_name or "",
            "advance_width": glyph.advance_width,
            "commands": commands,
        }
    except Exception as exc:
        return _err(exc)


@mcp.tool()
def text_layout(path: str, text: str, size: float = 1.0, kern: bool = True) -> dict:
    """Lay out text and return positioned glyph metadata."""
    try:
        font = FontLoader.open(path)
        layout = TextRenderer.layout(font, text, size=size, kern=kern)
        return {
            "total_width": layout.total_width,
            "ascender": layout.ascender,
            "descender": layout.descender,
            "glyphs": [
                {
                    "char": gl.char,
                    "glyph_id": int(gl.glyph_id),
                    "x_offset": gl.x_offset,
                    "advance_width": gl.advance_width,
                    "num_commands": len(gl.path) if gl.path is not None else 0,
                }
                for gl in layout.glyphs
            ],
        }
    except Exception as exc:
        return _err(exc)


@mcp.tool()
def font_subset(input_path: str, output_path: str, text: str) -> dict:
    """Subset a font to only the glyphs needed for text and save it."""
    try:
        font = FontLoader.open(input_path)
        original = font.num_glyphs
        subset = FontSubsetter.subset_by_text(font, text)
        data = subset.to_bytes()
        with open(output_path, "wb") as f:
            f.write(data)
        return {
            "original_glyphs": original,
            "subset_glyphs": subset.num_glyphs,
            "output_path": output_path,
            "bytes_written": len(data),
        }
    except Exception as exc:
        return _err(exc)


@mcp.tool()
def web_build(
    input_path: str,
    output_dir: str,
    *,
    file_stem: str | None = None,
    include_woff: bool = True,
    preview_text: str = "Hamburgefons 0123456789",
    instance_coordinates: dict[str, float] | None = None,
    instance_name: str | None = None,
    presets: list[str] | None = None,
    text: str = "",
    codepoints: list[int] | None = None,
    ranges: list[list[int]] | None = None,
    specimen_template: str = "classic",
    variable_mode: str = "auto",
    naming_strategy: str = "instance-family",
    family_suffix: str | None = None,
    legacy_family_name: str | None = None,
    typographic_family_name: str | None = None,
    legacy_style_name: str | None = None,
    typographic_style_name: str | None = None,
    stat_policy: str = "drop",
) -> dict:
    """Build a web-font handoff bundle with CSS, specimen HTML, and WOFF assets."""
    try:
        font = FontLoader.open(input_path)
        bundle = WebFontBuilder.build(
            font,
            file_stem=file_stem,
            include_woff=include_woff,
            preview_text=preview_text,
            variable_mode=variable_mode,
            instance_coordinates=instance_coordinates,
            instance_name=instance_name,
            presets=presets or (),
            text=text,
            codepoints=codepoints or (),
            ranges=_normalize_ranges(ranges),
            specimen_template=specimen_template,
            naming_strategy=naming_strategy,
            family_suffix=family_suffix,
            legacy_family_name=legacy_family_name,
            typographic_family_name=typographic_family_name,
            legacy_style_name=legacy_style_name,
            typographic_style_name=typographic_style_name,
            stat_policy=stat_policy,
        )
        written = bundle.write_to(output_dir)
        return {
            "family": bundle.family,
            "style": bundle.style,
            "css_filename": bundle.css_filename,
            "html_filename": bundle.html_filename,
            "export_mode": bundle.manifest.get("export_mode"),
            "export_note": bundle.manifest.get("export_note"),
            "requested_naming_strategy": bundle.manifest.get("requested_naming_strategy"),
            "requested_family_suffix": bundle.manifest.get("requested_family_suffix"),
            "requested_legacy_family_name": bundle.manifest.get("requested_legacy_family_name"),
            "requested_typographic_family_name": bundle.manifest.get("requested_typographic_family_name"),
            "requested_legacy_style_name": bundle.manifest.get("requested_legacy_style_name"),
            "requested_typographic_style_name": bundle.manifest.get("requested_typographic_style_name"),
            "requested_stat_policy": bundle.manifest.get("requested_stat_policy"),
            "stat_policy_recommendation": bundle.manifest.get("stat_policy_recommendation"),
            "stat_policy_recommendation_reasons": bundle.manifest.get(
                "stat_policy_recommendation_reasons",
                [],
            ),
            "font_assets": [asset.filename for asset in bundle.font_assets],
            "written": [str(path) for path in written],
            "specimen_template": specimen_template,
        }
    except Exception as exc:
        return _err(exc)


@mcp.tool()
def web_family_package(
    input_path: str,
    output_dir: str,
    *,
    instance_names: list[str] | None = None,
    all_named: bool = False,
    include_default: bool = False,
    family_name: str | None = None,
    include_woff: bool = True,
    preview_text: str = "Hamburgefons 0123456789",
    presets: list[str] | None = None,
    text: str = "",
    codepoints: list[int] | None = None,
    ranges: list[list[int]] | None = None,
    specimen_template: str = "classic",
    naming_strategy: str = "instance-family",
    family_suffix: str | None = None,
    legacy_family_name: str | None = None,
    typographic_family_name: str | None = None,
    legacy_style_name: str | None = None,
    typographic_style_name: str | None = None,
    stat_policy: str = "drop",
) -> dict:
    """Build a shared family package with specimen pages and comparative preview artifacts."""
    try:
        font = FontLoader.open(input_path)
        if not isinstance(font, TtfFont) or not font.is_variable:
            raise ValueError("web_family_package requires a variable TTF font")
        names = list(instance_names or [])
        if not all_named and not names:
            raise ValueError("web_family_package requires instance_names or all_named=True")
        package = font.smart_instancer.build_web_family_package(
            None if all_named and not names else names,
            include_default=include_default,
            family_name=family_name,
            include_woff=include_woff,
            preview_text=preview_text,
            presets=presets or (),
            text=text,
            codepoints=codepoints or (),
            ranges=_normalize_ranges(ranges),
            specimen_template=specimen_template,
            naming_strategy=naming_strategy,
            family_suffix=family_suffix,
            legacy_family_name=legacy_family_name,
            typographic_family_name=typographic_family_name,
            legacy_style_name=legacy_style_name,
            typographic_style_name=typographic_style_name,
            stat_policy=stat_policy,
        )
        written = package.write_to(output_dir)
        return {
            "family_name": package.family_name,
            "bundle_count": len(package.bundles),
            "css_filename": package.css_filename,
            "html_filename": package.html_filename,
            "assets": [asset.filename for asset in package.assets],
            "bundles": [
                {
                    "family": bundle.family,
                    "style": bundle.style,
                    "requested_naming_strategy": bundle.manifest.get("requested_naming_strategy"),
                    "requested_family_suffix": bundle.manifest.get("requested_family_suffix"),
                    "requested_legacy_family_name": bundle.manifest.get("requested_legacy_family_name"),
                    "requested_typographic_family_name": bundle.manifest.get("requested_typographic_family_name"),
                    "requested_legacy_style_name": bundle.manifest.get("requested_legacy_style_name"),
                    "requested_typographic_style_name": bundle.manifest.get("requested_typographic_style_name"),
                    "requested_stat_policy": bundle.manifest.get("requested_stat_policy"),
                    "stat_policy_recommendation": bundle.manifest.get("stat_policy_recommendation"),
                    "stat_policy_recommendation_reasons": bundle.manifest.get(
                        "stat_policy_recommendation_reasons",
                        [],
                    ),
                    "font_assets": [asset.filename for asset in bundle.font_assets],
                }
                for bundle in package.bundles
            ],
            "written": [str(path) for path in written],
            "specimen_template": specimen_template,
        }
    except Exception as exc:
        return _err(exc)


@mcp.tool()
def var_compat(
    input_path: str,
    *,
    before_coordinates: dict[str, float] | None = None,
    after_coordinates: dict[str, float] | None = None,
    before_instance_name: str | None = None,
    after_instance_name: str | None = None,
    codepoints: list[int] | None = None,
    text: str = "",
) -> dict:
    """Compare two variable-font states and return compatibility diagnostics."""
    try:
        font = FontLoader.open(input_path)
        if not isinstance(font, TtfFont) or not font.is_variable:
            raise ValueError("var_compat requires a variable TTF font")
        report = font.smart_instancer.check_compatibility(
            before_coordinates=before_coordinates,
            after_coordinates=after_coordinates,
            before_instance_name=before_instance_name,
            after_instance_name=after_instance_name,
            codepoints=tuple(codepoints or ()),
            text=text,
        )
        payload = report.to_dict()
        payload["issue_count"] = len(report.issues)
        return payload
    except Exception as exc:
        return _err(exc)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
