"""Product-shaped font QA reports."""

from __future__ import annotations

import dataclasses
import html
import json
from collections.abc import Iterable
from pathlib import Path

from aspose_font._font_base import Font
from aspose_font.preview import FontPreviewBuilder
from aspose_font.subsetter import FontSubsetter
from aspose_font.ttf.font import TtfFont

_SCHEMA_VERSION = 1
_MISSING_SAMPLE_LIMIT = 12
_PACKAGE_JSON_NAME = "qa-report.json"
_PACKAGE_HTML_NAME = "qa-report.html"
_PACKAGE_PREVIEW_NAME = "preview.png"
_DEFAULT_PACKAGE_PREVIEW_TEXT = "Font QA Preview"


@dataclasses.dataclass(frozen=True, slots=True)
class FontQaReport:
    """Structured QA report with JSON and HTML writers."""

    payload: dict[str, object]

    def to_dict(self) -> dict[str, object]:
        return dict(self.payload)

    def to_json(self, *, indent: int = 2, sort_keys: bool = True) -> str:
        return json.dumps(self.payload, indent=indent, sort_keys=sort_keys)

    def write_json(
        self,
        path: str | Path,
        *,
        indent: int = 2,
        sort_keys: bool = True,
    ) -> Path:
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(f"{self.to_json(indent=indent, sort_keys=sort_keys)}\n", encoding="utf-8")
        return output

    def write_html(self, path: str | Path) -> Path:
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(_build_html(self.payload), encoding="utf-8")
        return output


@dataclasses.dataclass(frozen=True, slots=True)
class FontQaPackage:
    """Paths and report data for a self-contained QA report package."""

    report: FontQaReport
    directory: Path
    json_path: Path
    html_path: Path
    preview_path: Path
    artifacts: list[dict[str, str]]


class FontQaReporter:
    """Build first-slice QA reports from existing public font APIs."""

    @classmethod
    def build(
        cls,
        font: Font,
        *,
        source_label: str | None = None,
        presets: Iterable[str] = (),
        text: str = "",
        codepoints: Iterable[int] = (),
        ranges: Iterable[tuple[int, int] | range] = (),
        preferred_languages: str | tuple[str, ...] = "en",
    ) -> FontQaReport:
        preset_tuple = tuple(str(value) for value in presets)
        codepoint_tuple = tuple(int(value) for value in codepoints)
        range_tuple = tuple(ranges)

        identity = cls._identity(font, source_label=source_label)
        metrics = cls._metrics(font)
        variable = cls._variable(font, preferred_languages=preferred_languages)
        coverage = cls._coverage(
            font,
            presets=preset_tuple,
            text=text,
            codepoints=codepoint_tuple,
            ranges=range_tuple,
        )
        warnings = cls._warnings(font, coverage=coverage)
        next_actions = cls._next_actions(font, coverage=coverage, warnings=warnings)

        return FontQaReport(
            {
                "kind": "font_qa_report",
                "schema_version": _SCHEMA_VERSION,
                "identity": identity,
                "metrics": metrics,
                "variable": variable,
                "coverage": coverage,
                "warnings": warnings,
                "next_actions": next_actions,
            }
        )

    @classmethod
    def build_package(
        cls,
        font: Font,
        output_dir: str | Path,
        *,
        source_label: str | None = None,
        presets: Iterable[str] = (),
        text: str = "",
        codepoints: Iterable[int] = (),
        ranges: Iterable[tuple[int, int] | range] = (),
        preferred_languages: str | tuple[str, ...] = "en",
        preview_text: str | None = None,
        preview_instance_name: str | None = None,
    ) -> FontQaPackage:
        report = cls.build(
            font,
            source_label=source_label,
            presets=presets,
            text=text,
            codepoints=codepoints,
            ranges=ranges,
            preferred_languages=preferred_languages,
        )
        directory = Path(output_dir)
        directory.mkdir(parents=True, exist_ok=True)

        preview = FontPreviewBuilder.build(
            font,
            text=preview_text if preview_text is not None else text or _DEFAULT_PACKAGE_PREVIEW_TEXT,
            file_stem="preview",
            instance_name=preview_instance_name,
            output_format="png",
        )
        preview_path = preview.write_to(directory / _PACKAGE_PREVIEW_NAME)
        json_path = directory / _PACKAGE_JSON_NAME
        html_path = directory / _PACKAGE_HTML_NAME
        artifacts = [
            {
                "kind": "json",
                "label": "QA report JSON",
                "path": _PACKAGE_JSON_NAME,
                "media_type": "application/json",
            },
            {
                "kind": "html",
                "label": "QA report HTML",
                "path": _PACKAGE_HTML_NAME,
                "media_type": "text/html",
            },
            {
                "kind": "preview",
                "label": "Preview image",
                "path": _PACKAGE_PREVIEW_NAME,
                "media_type": preview.media_type,
            },
        ]
        payload = report.to_dict()
        payload["artifacts"] = artifacts
        packaged_report = FontQaReport(payload)
        packaged_report.write_json(json_path)
        packaged_report.write_html(html_path)
        return FontQaPackage(
            report=packaged_report,
            directory=directory,
            json_path=json_path,
            html_path=html_path,
            preview_path=preview_path,
            artifacts=artifacts,
        )

    @staticmethod
    def _identity(font: Font, *, source_label: str | None) -> dict[str, object]:
        return {
            "source": source_label,
            "format": font.font_type.value,
            "font_name": font.font_name,
            "font_family": font.font_family,
            "font_style": font.font_style,
            "num_glyphs": font.num_glyphs,
            "is_variable": isinstance(font, TtfFont) and font.is_variable,
        }

    @staticmethod
    def _metrics(font: Font) -> dict[str, int]:
        metrics = font.metrics
        return {
            "units_per_em": metrics.units_per_em,
            "ascender": metrics.ascender,
            "descender": metrics.descender,
            "line_gap": metrics.line_gap,
            "advance_width_max": metrics.advance_width_max,
            "underline_position": metrics.underline_position,
            "underline_thickness": metrics.underline_thickness,
        }

    @staticmethod
    def _variable(
        font: Font,
        *,
        preferred_languages: str | tuple[str, ...],
    ) -> dict[str, object]:
        if not isinstance(font, TtfFont) or not font.is_variable:
            return {
                "is_variable": False,
                "axis_count": 0,
                "named_instance_count": 0,
                "axes": [],
                "named_instances_sample": [],
            }

        axes = [
            {
                "tag": axis.tag,
                "label": axis.name(preferred_languages),
                "min": axis.min_value,
                "default": axis.default_value,
                "max": axis.max_value,
                "range_summary": axis.range_summary,
            }
            for axis in font.variable_axes
        ]
        instances = [
            {
                "label": instance.name(preferred_languages) or instance.label,
                "coordinates": dict(instance.coordinates),
            }
            for instance in font.variable_instances[:8]
        ]
        return {
            "is_variable": True,
            "axis_count": len(font.variable_axes),
            "named_instance_count": len(font.variable_instances),
            "axes": axes,
            "named_instances_sample": instances,
        }

    @staticmethod
    def _coverage(
        font: Font,
        *,
        presets: tuple[str, ...],
        text: str,
        codepoints: tuple[int, ...],
        ranges: tuple[tuple[int, int] | range, ...],
    ) -> dict[str, object] | None:
        if not presets and not text and not codepoints and not ranges:
            return None
        coverage = FontSubsetter.analyze_web_coverage(
            font,
            presets=presets,
            text=text,
            codepoints=codepoints,
            ranges=ranges,
        )
        summary = coverage.summary_dict()
        summary["requested_presets"] = list(presets)
        summary["has_text_input"] = bool(text)
        summary["explicit_codepoint_count"] = len(codepoints)
        summary["explicit_range_count"] = len(ranges)
        return summary

    @staticmethod
    def _warnings(
        font: Font,
        *,
        coverage: dict[str, object] | None,
    ) -> list[dict[str, object]]:
        warnings: list[dict[str, object]] = []
        if coverage is None:
            warnings.append(
                {
                    "code": "coverage-not-requested",
                    "severity": "info",
                    "message": "No web coverage inputs were requested for this report.",
                }
            )
        elif int(coverage.get("missing_count", 0)) > 0:
            warnings.append(
                {
                    "code": "missing-requested-codepoints",
                    "severity": "warning",
                    "message": "Some requested Unicode codepoints are not covered by the font.",
                    "missing_count": int(coverage.get("missing_count", 0)),
                    "missing_codepoints_sample": list(
                        coverage.get("missing_codepoints_sample", [])[:_MISSING_SAMPLE_LIMIT]
                    ),
                }
            )

        if isinstance(font, TtfFont) and font.is_variable and coverage is not None:
            warnings.append(
                {
                    "code": "variable-web-subset-fallback",
                    "severity": "info",
                    "message": (
                        "Variable-font web subsetting currently uses a static fallback in "
                        "the web bundle workflow."
                    ),
                }
            )
        return warnings

    @staticmethod
    def _next_actions(
        font: Font,
        *,
        coverage: dict[str, object] | None,
        warnings: list[dict[str, object]],
    ) -> list[dict[str, str]]:
        warning_codes = {str(item.get("code", "")) for item in warnings}
        actions: list[dict[str, str]] = []
        if coverage is None:
            actions.append(
                {
                    "code": "add-coverage-inputs",
                    "label": "Run QA with preset/text/codepoint inputs for web readiness.",
                }
            )
        if "missing-requested-codepoints" in warning_codes:
            actions.append(
                {
                    "code": "review-missing-codepoints",
                    "label": "Review missing glyphs or adjust the web coverage request.",
                }
            )
        if isinstance(font, TtfFont) and font.is_variable:
            actions.append(
                {
                    "code": "review-variable-instances",
                    "label": "Review named instances and export mode before web handoff.",
                }
            )
        actions.append(
            {
                "code": "build-web-package",
                "label": "Use web-build or WebFontBuilder for a production web package.",
            }
        )
        return actions


def _build_html(payload: dict[str, object]) -> str:
    identity = _dict(payload.get("identity"))
    metrics = _dict(payload.get("metrics"))
    variable = _dict(payload.get("variable"))
    coverage = payload.get("coverage")
    artifacts = _list(payload.get("artifacts"))
    warnings = _list(payload.get("warnings"))
    actions = _list(payload.get("next_actions"))

    warning_items = "".join(
        "<li>"
        f"<strong>{_escape(item.get('severity', 'info'))}</strong> "
        f"{_escape(item.get('code', 'warning'))}: {_escape(item.get('message', ''))}"
        "</li>\n"
        for item in warnings
        if isinstance(item, dict)
    ) or "<li>No warnings.</li>\n"
    action_items = "".join(
        f"<li><strong>{_escape(item.get('code', 'action'))}</strong>: {_escape(item.get('label', ''))}</li>\n"
        for item in actions
        if isinstance(item, dict)
    )
    axis_items = "".join(
        "<li>"
        f"<strong>{_escape(axis.get('tag', ''))}</strong> "
        f"{_escape(axis.get('label', ''))}: {_escape(axis.get('range_summary', ''))}"
        "</li>\n"
        for axis in _list(variable.get("axes"))
        if isinstance(axis, dict)
    ) or "<li>Static font or no variable axes.</li>\n"

    coverage_html = _coverage_html(coverage)
    artifacts_html = _artifacts_html(artifacts)
    return (
        "<!doctype html>\n"
        "<html lang=\"en\">\n"
        "<head>\n"
        "  <meta charset=\"utf-8\">\n"
        f"  <title>{_escape(identity.get('font_family', 'Font'))} QA Report</title>\n"
        "  <style>body{font-family:system-ui,sans-serif;line-height:1.45;margin:2rem;max-width:900px}"
        "table{border-collapse:collapse;width:100%;margin:1rem 0}td,th{border:1px solid #ddd;padding:.45rem;text-align:left}"
        "code{background:#f5f5f5;padding:.1rem .25rem}</style>\n"
        "</head>\n"
        "<body>\n"
        "  <h1>Font QA Report</h1>\n"
        "  <h2>Summary</h2>\n"
        "  <table><tbody>\n"
        f"    <tr><th>Source</th><td>{_escape(identity.get('source', ''))}</td></tr>\n"
        f"    <tr><th>Format</th><td>{_escape(identity.get('format', ''))}</td></tr>\n"
        f"    <tr><th>Family</th><td>{_escape(identity.get('font_family', ''))}</td></tr>\n"
        f"    <tr><th>Style</th><td>{_escape(identity.get('font_style', ''))}</td></tr>\n"
        f"    <tr><th>Glyphs</th><td>{_escape(identity.get('num_glyphs', ''))}</td></tr>\n"
        f"    <tr><th>Variable</th><td>{_escape(variable.get('is_variable', False))}</td></tr>\n"
        "  </tbody></table>\n"
        "  <h2>Metrics</h2>\n"
        "  <table><tbody>\n"
        f"    <tr><th>Units per em</th><td>{_escape(metrics.get('units_per_em', ''))}</td></tr>\n"
        f"    <tr><th>Ascender</th><td>{_escape(metrics.get('ascender', ''))}</td></tr>\n"
        f"    <tr><th>Descender</th><td>{_escape(metrics.get('descender', ''))}</td></tr>\n"
        f"    <tr><th>Line gap</th><td>{_escape(metrics.get('line_gap', ''))}</td></tr>\n"
        "  </tbody></table>\n"
        "  <h2>Variable Axes</h2>\n"
        f"  <p>Axes: {_escape(variable.get('axis_count', 0))}; named instances: {_escape(variable.get('named_instance_count', 0))}</p>\n"
        f"  <ul>{axis_items}</ul>\n"
        "  <h2>Coverage</h2>\n"
        f"{coverage_html}"
        f"{artifacts_html}"
        "  <h2>Warnings</h2>\n"
        f"  <ul>{warning_items}</ul>\n"
        "  <h2>Next Actions</h2>\n"
        f"  <ul>{action_items}</ul>\n"
        "</body>\n"
        "</html>\n"
    )


def _artifacts_html(artifacts: list[object]) -> str:
    artifact_items = ""
    preview_html = ""
    for artifact in artifacts:
        if not isinstance(artifact, dict):
            continue
        path = artifact.get("path", "")
        label = artifact.get("label", "")
        kind = artifact.get("kind", "")
        media_type = artifact.get("media_type", "")
        artifact_items += (
            "<li>"
            f"<a href=\"{_escape_attr(path)}\">{_escape(label)}</a> "
            f"<code>{_escape(kind)}</code> {_escape(media_type)}"
            "</li>\n"
        )
        if kind == "preview":
            preview_html = (
                "  <figure>\n"
                f"    <img src=\"{_escape_attr(path)}\" alt=\"{_escape(label)}\" style=\"max-width:100%;height:auto;border:1px solid #ddd\">\n"
                f"    <figcaption>{_escape(label)}</figcaption>\n"
                "  </figure>\n"
            )
    if not artifact_items:
        return ""
    return (
        "  <h2>Artifacts</h2>\n"
        f"{preview_html}"
        f"  <ul>{artifact_items}</ul>\n"
    )


def _coverage_html(coverage: object) -> str:
    if not isinstance(coverage, dict):
        return "  <p>No coverage request was included.</p>\n"
    groups = "".join(
        "<li>"
        f"{_escape(group.get('kind', 'group'))} {_escape(group.get('label', ''))}: "
        f"{_escape(group.get('covered_count', 0))}/{_escape(group.get('requested_count', 0))} covered"
        "</li>\n"
        for group in _list(coverage.get("groups"))
        if isinstance(group, dict)
    )
    return (
        "  <table><tbody>\n"
        f"    <tr><th>Requested</th><td>{_escape(coverage.get('requested_count', 0))}</td></tr>\n"
        f"    <tr><th>Covered</th><td>{_escape(coverage.get('covered_count', 0))}</td></tr>\n"
        f"    <tr><th>Missing</th><td>{_escape(coverage.get('missing_count', 0))}</td></tr>\n"
        f"    <tr><th>Fully covered</th><td>{_escape(coverage.get('fully_covered', False))}</td></tr>\n"
        "  </tbody></table>\n"
        f"  <ul>{groups}</ul>\n"
    )


def _dict(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _list(value: object) -> list[object]:
    return value if isinstance(value, list) else []


def _escape(value: object) -> str:
    return html.escape("" if value is None else str(value))


def _escape_attr(value: object) -> str:
    return html.escape("" if value is None else str(value), quote=True)


__all__ = ["FontQaPackage", "FontQaReport", "FontQaReporter"]
