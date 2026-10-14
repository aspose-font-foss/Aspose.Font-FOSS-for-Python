"""Product-shaped font QA reports."""

from __future__ import annotations

import dataclasses
import html
import json
from collections.abc import Iterable
from pathlib import Path

from aspose_font._font_base import Font
from aspose_font.compatibility import CompatibilityChecker
from aspose_font.preview import FontPreviewBuilder
from aspose_font.subsetter import FontSubsetter
from aspose_font.ttf.font import TtfFont

_SCHEMA_VERSION = 1
_MISSING_SAMPLE_LIMIT = 12
_PACKAGE_JSON_NAME = "qa-report.json"
_PACKAGE_HTML_NAME = "qa-report.html"
_ASSETS_DIR_NAME = "assets"
_PACKAGE_MAIN_PREVIEW_NAME = "assets/preview_main.png"
_PACKAGE_AXES_PREVIEW_NAME = "assets/axes_chart.png"
_PACKAGE_INSTANCES_PREVIEW_NAME = "assets/instances_chart.png"
_PACKAGE_COVERAGE_PREVIEW_NAME = "assets/coverage_chart.png"
_DEFAULT_PACKAGE_PREVIEW_TEXT = "Font QA Preview"

_SEVERITY_BLOCKER = "blocker"
_SEVERITY_WARNING = "warning"
_SEVERITY_INFO = "info"

_SEVERITY_WEIGHTS = {
    _SEVERITY_BLOCKER: 25,
    _SEVERITY_WARNING: 10,
    _SEVERITY_INFO: 0,
}


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

    def write_html(
        self,
        path: str | Path,
        *,
        format: str = "html",
    ) -> Path:
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)

        if format.lower() == "pdf":
            html_str = _build_html(self.payload)
            from aspose_font.preview import _convert_html_to_png, _convert_png_to_pdf
            png_data = _convert_html_to_png(html_str)
            output.write_bytes(_convert_png_to_pdf(png_data))
            return output

        output.write_text(_build_html(self.payload), encoding="utf-8")
        return output

    def write_pdf(self, path: str | Path) -> Path:
        """Write a concise PDF summary of the QA report."""
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        pdf_data = _build_pdf_summary(self.payload)
        output.write_bytes(pdf_data)
        return output

    def write_markdown(self, path: str | Path) -> Path:
        """Write a concise markdown summary of the QA report."""
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        markdown = _build_markdown_summary(self.payload)
        output.write_text(markdown, encoding="utf-8")
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
    compatibility: dict[str, object] | None = None
    delta_summary: dict[str, object] | None = None
    size_summary: dict[str, object] | None = None


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
        include_compatibility: bool = False,
        include_extras: bool = False,
        include_decision: bool = False,
        source_path: str | Path | None = None,
        current_size: int | None = None,
        ci_fast_mode: bool = False,
    ) -> FontQaReport:
        preset_tuple = tuple(str(value) for value in presets)
        codepoint_tuple = tuple(int(value) for value in codepoints)
        range_tuple = tuple(ranges)
        source_path_obj = Path(source_path) if source_path is not None else None

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
        compatibility = cls._build_compatibility_report(font, codepoints=codepoint_tuple, include_compatibility=include_compatibility)
        size_artifacts = cls._build_size_artifacts(font, source_path=source_path_obj, current_size=current_size)
        delta_summary = None
        if include_extras and isinstance(font, TtfFont) and font.is_variable and not ci_fast_mode:
            from aspose_font.delta import DeltaInspector
            delta_report = DeltaInspector.inspect_variable_text(
                font,
                text="H",
                coordinates=None,
            )
            delta_summary = delta_report.to_dict() if delta_report else None
        warnings = cls._warnings(font, coverage=coverage)
        next_actions = cls._next_actions(font, coverage=coverage, warnings=warnings, compatibility=compatibility)
        readiness = _build_readiness(warnings)

        decision = None
        if include_decision:
            is_variable = isinstance(font, TtfFont) and font.is_variable
            if is_variable:
                decision = {
                    "recommended_action": "live",
                    "rationale": [
                        "Variable font with variable axes detected",
                        "Output supports variable axes for responsive typography",
                    ],
                }
            else:
                decision = {
                    "recommended_action": "static_fallback",
                    "rationale": [
                        "Static font or no variable axes available",
                        "Fallback to static export for maximum compatibility",
                    ],
                }

        return FontQaReport(
            {
                "kind": "font_qa_report",
                "schema_version": _SCHEMA_VERSION,
                "identity": identity,
                "metrics": metrics,
                "variable": variable,
                "coverage": coverage,
                "compatibility": compatibility,
                "delta_summary": delta_summary,
                "size_summary": size_artifacts,
                "size_artifacts": size_artifacts,
                "warnings": warnings,
                "readiness": readiness,
                "next_actions": next_actions,
                "decision": decision,
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
        include_compatibility: bool = False,
        include_extras: bool = False,
        include_decision: bool = False,
        source_path: str | Path | None = None,
        current_size: int | None = None,
        ci_fast_mode: bool = False,
    ) -> FontQaPackage:
        report = cls.build(
            font,
            source_label=source_label,
            presets=presets,
            text=text,
            codepoints=codepoints,
            ranges=ranges,
            preferred_languages=preferred_languages,
            include_compatibility=include_compatibility,
            include_extras=include_extras,
            include_decision=include_decision,
            source_path=source_path,
            current_size=current_size,
            ci_fast_mode=ci_fast_mode,
        )
        compatibility = report.payload.get("compatibility")
        delta_summary = report.payload.get("delta_summary")
        size_summary = report.payload.get("size_summary")
        directory = Path(output_dir)
        directory.mkdir(parents=True, exist_ok=True)
        assets_dir = directory / _ASSETS_DIR_NAME
        assets_dir.mkdir(exist_ok=True)

        preview_text_val = preview_text if preview_text is not None else text or _DEFAULT_PACKAGE_PREVIEW_TEXT
        if ci_fast_mode:
            preview_main = FontPreviewBuilder.build(
                font,
                text="H",
                size=1.0,
                color=(17, 17, 17),
                background=(255, 253, 248),
                padding=0,
                antialias=False,
                file_stem="preview_main",
            )
            preview_main_path = preview_main.write_to(assets_dir / "preview_main.png")
            axes_preview_path = None
            instances_preview_path = None
            coverage_preview_path = None
        else:
            preview_main = FontPreviewBuilder.build(
                font,
                text=preview_text_val,
                file_stem="preview_main",
                instance_name=preview_instance_name,
                output_format="png",
            )
            preview_main_path = preview_main.write_to(assets_dir / "preview_main.png")

            axes_preview_path: Path | None = None
            if isinstance(font, TtfFont) and font.is_variable:
                axes_preview = FontPreviewBuilder.build(
                    font,
                    text=_build_axes_summary_text(font),
                    file_stem="axes_chart",
                    instance_name=None,
                    output_format="png",
                )
                axes_preview_path = axes_preview.write_to(assets_dir / "axes_chart.png")

            instances_preview_path: Path | None = None
            if isinstance(font, TtfFont) and font.is_variable and font.variable_instances:
                instances_preview = FontPreviewBuilder.build(
                    font,
                    text=_build_instances_summary_text(font),
                    file_stem="instances_chart",
                    instance_name=None,
                    output_format="png",
                )
                instances_preview_path = instances_preview.write_to(assets_dir / "instances_chart.png")

            coverage_preview_path: Path | None = None
            if report.payload.get("coverage") is not None:
                coverage_preview = FontPreviewBuilder.build(
                    font,
                    text=_build_coverage_summary_text(font, report.payload.get("coverage", {})),
                    file_stem="coverage_chart",
                    instance_name=None,
                    output_format="png",
                )
                coverage_preview_path = coverage_preview.write_to(assets_dir / "coverage_chart.png")

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
                "label": "Main preview image",
                "path": _PACKAGE_MAIN_PREVIEW_NAME,
                "media_type": preview_main.media_type,
            },
        ]

        if axes_preview_path is not None:
            artifacts.append({
                "kind": "preview",
                "label": "Variable axes summary",
                "path": _PACKAGE_AXES_PREVIEW_NAME,
                "media_type": "image/png",
            })

        if instances_preview_path is not None:
            artifacts.append({
                "kind": "preview",
                "label": "Named instances summary",
                "path": _PACKAGE_INSTANCES_PREVIEW_NAME,
                "media_type": "image/png",
            })

        if coverage_preview_path is not None:
            artifacts.append({
                "kind": "preview",
                "label": "Web coverage summary",
                "path": _PACKAGE_COVERAGE_PREVIEW_NAME,
                "media_type": "image/png",
            })

        json_path = directory / _PACKAGE_JSON_NAME
        html_path = directory / _PACKAGE_HTML_NAME

        if include_compatibility and compatibility is not None:
            compatibility_path = directory / "compatibility.json"
            compatibility_json = json.dumps(compatibility, indent=2, sort_keys=True) + "\n"
            compatibility_path.write_text(compatibility_json, encoding="utf-8")
            artifacts.append({
                "kind": "compatibility",
                "label": "Compatibility report",
                "path": "compatibility.json",
                "media_type": "application/json",
            })

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
            preview_path=preview_main_path,
            artifacts=artifacts,
            compatibility=compatibility,
            delta_summary=delta_summary,
            size_summary=size_summary,
        )

    @classmethod
    def build_full_report(
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
        include_compatibility: bool = False,
        include_extras: bool = False,
        include_decision: bool = False,
        source_path: str | Path | None = None,
        current_size: int | None = None,
    ) -> FontQaPackage:
        package = cls.build_package(
            font,
            output_dir,
            source_label=source_label,
            presets=presets,
            text=text,
            codepoints=codepoints,
            ranges=ranges,
            preferred_languages=preferred_languages,
            preview_text=preview_text,
            preview_instance_name=preview_instance_name,
            include_compatibility=include_compatibility,
            include_extras=include_extras,
            include_decision=include_decision,
            source_path=source_path,
            current_size=current_size,
        )
        return package

    @staticmethod
    def _build_compatibility_report(
        font: Font,
        *,
        codepoints: tuple[int, ...],
        include_compatibility: bool,
    ) -> dict[str, object] | None:
        if not include_compatibility:
            return None
        report = CompatibilityChecker.compare_fonts(
            font,
            font,
            before_label="Original",
            after_label="Original",
            codepoints=list(codepoints) if codepoints else None,
        )
        return report.to_dict()

    @staticmethod
    def _build_size_artifacts(
        font: Font,
        *,
        source_path: Path | None,
        current_size: int | None = None,
    ) -> dict[str, object] | None:
        if source_path is None:
            return None
        if current_size is None:
            current_size = len(font.to_bytes())
        source_size: int | None = None
        if source_path.exists():
            source_size = source_path.stat().st_size
        size_delta_bytes: int | None = None
        size_delta_percent: float | None = None
        if source_size is not None:
            size_delta_bytes = current_size - source_size
            if source_size > 0:
                size_delta_percent = (size_delta_bytes / source_size) * 100
        return {
            "current_size_bytes": current_size,
            "source_size_bytes": source_size,
            "size_delta_bytes": size_delta_bytes,
            "size_delta_percent": size_delta_percent,
        }

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
                _build_warning(
                    code="coverage-not-requested",
                    severity=_SEVERITY_INFO,
                    message="No web coverage inputs were requested for this report.",
                    recommendation="Request presets/text/codepoints for web coverage diagnostics.",
                    reason="Coverage gaps cannot be identified without explicit inputs.",
                    next_action="Run build() with presets=('latin',) or similar inputs.",
                )
            )
        elif int(coverage.get("missing_count", 0)) > 0:
            missing_count = int(coverage.get("missing_count", 0))
            severity = _SEVERITY_WARNING if missing_count < 100 else _SEVERITY_BLOCKER

            warnings.append(
                _build_warning(
                    code="missing-requested-codepoints",
                    severity=severity,
                    message=f"{missing_count} requested Unicode codepoints are not covered by the font.",
                    recommendation="Review missing glyphs or adjust the web coverage request.",
                    reason=f"{missing_count} codepoints will render as missing glyph boxes on web.",
                    next_action="Consider subsetting or extending the font with missing glyphs.",
                )
            )

        if isinstance(font, TtfFont) and font.is_variable and coverage is not None:
            warnings.append(
                _build_warning(
                    code="variable-web-subset-fallback",
                    severity=_SEVERITY_INFO,
                    message="Variable-font web subsetting currently uses a static fallback in the web bundle workflow.",
                    recommendation="This is a known limitation and does not affect static web usage.",
                    reason="Web subsetting for variable fonts currently falls back to static behavior.",
                    next_action="Proceed with variable-font web deployment if static fallback suffices.",
                )
            )

        identity_warnings = _check_identity_issues(font)
        warnings.extend(identity_warnings)

        if isinstance(font, TtfFont) and font.is_variable:
            stat_warnings = _check_stat_issues(font)
            warnings.extend(stat_warnings)

        return warnings

    @staticmethod
    def _next_actions(
        font: Font,
        *,
        coverage: dict[str, object] | None,
        warnings: list[dict[str, object]],
        compatibility: dict[str, object] | None = None,
    ) -> list[dict[str, str]]:
        warning_codes = {str(item.get("code", "")) for item in warnings}
        actions: list[dict[str, str]] = []
        if coverage is None:
            actions.append(
                {
                    "code": "add-coverage-inputs",
                    "label": "Run QA with preset/text/codepoint inputs for web readiness.",
                    "priority": "high",
                    "severity_affected": "info",
                }
            )
        if "missing-requested-codepoints" in warning_codes:
            actions.append(
                {
                    "code": "review-missing-codepoints",
                    "label": "Review missing glyphs or adjust the web coverage request.",
                    "priority": "high",
                    "severity_affected": "warning",
                }
            )
        if isinstance(font, TtfFont) and font.is_variable:
            actions.append(
                {
                    "code": "review-variable-instances",
                    "label": "Review named instances and export mode before web handoff.",
                    "priority": "medium",
                    "severity_affected": "info",
                }
            )
        if compatibility is not None:
            actions.append(
                {
                    "code": "review-compatibility-reports",
                    "label": "Review compatibility diagnostics in the QA package.",
                    "priority": "medium",
                    "severity_affected": "info",
                }
            )
        actions.append(
            {
                "code": "build-web-package",
                "label": "Use web-build or WebFontBuilder for a production web package.",
                "priority": "medium",
                "severity_affected": "info",
            }
        )
        return actions


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
            preview_html += (
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


def _build_warning(
    code: str,
    severity: str,
    message: str,
    recommendation: str,
    reason: str,
    next_action: str,
) -> dict[str, object]:
    return {
        "code": code,
        "severity": severity,
        "message": message,
        "remediation": {
            "recommendation": recommendation,
            "reason": reason,
            "next_action": next_action,
        },
    }


def _check_identity_issues(font: Font) -> list[dict[str, object]]:
    warnings: list[dict[str, object]] = []
    identity_problems: list[tuple[str, str, str, str]] = []

    if not font.font_name:
        identity_problems.append((
            "missing-font-name",
            "Font missing required font name record.",
            "Add fontName (strings 6) and fontNameEn (strings 6, 3, 1) name records.",
            "Name records are required for OS font installation and web @font-face rules.",
        ))

    if not font.font_family:
        identity_problems.append((
            "missing-family-name",
            "Font missing required family name record.",
            "Add fontFamily (strings 1) and fontFamilyEn (strings 1, 3, 1) name records.",
            "Family name is required for CSS font-family matching and app menu installation.",
        ))

    for code, message, recommendation, reason in identity_problems:
        warnings.append(_build_warning(
            code=code,
            severity=_SEVERITY_BLOCKER,
            message=message,
            recommendation=recommendation,
            reason=reason,
            next_action="Review NameTable and add missing name entries.",
        ))

    return warnings


def _check_stat_issues(font: TtfFont) -> list[dict[str, object]]:
    """Check STAT table issues for variable fonts.

    Returns a list of warning dicts. Generates a blocker warning if the STAT
    table is missing, and another blocker warning if any AxisValue records
    contain non‑zero flags.
    """
    warnings: list[dict[str, object]] = []
    # Attempt to read raw STAT table data
    try:
        stat_raw = font.ttf_tables.get_raw("STAT")
    except Exception:
        stat_raw = None
    if stat_raw is None:
        warnings.append(
            _build_warning(
                code="missing-stat-table",
                severity=_SEVERITY_BLOCKER,
                message="Variable font missing STAT table.",
                recommendation="Add STAT table with AxisValue records for each named instance.",
                reason="STAT table provides named instance metadata for design apps and CSS.",
                next_action="Add appropriate STAT records to the font.",
            )
        )
        return warnings
    # Extract AxisValue flags from the STAT table
    from aspose_font.ttf.tables.stat import extract_stat_axis_value_flags

    flags = extract_stat_axis_value_flags(stat_raw)
    # Identify any non‑zero flags
    nonzero_flags = [f for f in flags if f != 0]
    if nonzero_flags:
        first_flag = nonzero_flags[0]
        # Optional: include flag meanings in message if desired
        warnings.append(
            _build_warning(
                code="stat-axis-value-flags-nonzero",
                severity=_SEVERITY_BLOCKER,
                message=f"STAT AxisValue flags non‑zero (0x{first_flag:04X}).",
                recommendation="Ensure AxisValue flags are correct or clear them if unnecessary.",
                reason="Non‑default AxisValue flags may affect variable‑font behavior in design tools.",
                next_action="Review and adjust STAT AxisValue flags.",
            )
        )
    return warnings


def _build_readiness(warnings: list[dict[str, object]]) -> dict[str, object]:
    total_score = 100
    prioritized_causes: list[dict[str, object]] = []

    for warning in warnings:
        severity = warning.get("severity", _SEVERITY_INFO)
        weight = _SEVERITY_WEIGHTS.get(severity, 0)
        code = warning.get("code", "unknown")

        total_score -= weight

        prioritized_causes.append({
            "code": code,
            "severity": severity,
            "weight": weight,
            "message": warning.get("message", ""),
        })

    severity_order = {_SEVERITY_BLOCKER: 0, _SEVERITY_WARNING: 1, _SEVERITY_INFO: 2}
    prioritized_causes.sort(key=lambda x: severity_order.get(x["severity"], 3))

    score = max(0, min(100, total_score))
    status = _score_to_status(score)

    return {
        "score": score,
        "status": status,
        "prioritized_causes": prioritized_causes,
    }


def _score_to_status(score: int) -> str:
    if score >= 90:
        return "ready"
    elif score >= 70:
        return "warning"
    elif score >= 50:
        return "caution"
    else:
        return "blocked"


def _severity_color(severity: str) -> str:
    return {
        _SEVERITY_BLOCKER: "#ef4444",
        _SEVERITY_WARNING: "#eab308",
        _SEVERITY_INFO: "#3b82f6",
    }.get(severity, "#6b7280")


def _remediation_html(remediation: object) -> str:
    if not isinstance(remediation, dict):
        return ""
    rec = _escape(remediation.get("recommendation", ""))
    reason = _escape(remediation.get("reason", ""))
    next_action = _escape(remediation.get("next_action", ""))
    return (
        f"<div style=\"margin-top:.25rem;font-size:.85rem;\">"
        f"<strong>→ {rec}</strong><br/>"
        f"<em>Because: {reason}</em><br/>"
        f"<strong>Action:</strong> {next_action}"
        f"</div>")


def _build_axes_summary_text(font: TtfFont) -> str:
    parts = [f"{font.font_family or 'Unknown Font'}"]
    parts.append(f"Axis count: {len(font.variable_axes)}")
    parts.append("")
    for axis in font.variable_axes:
        parts.append(f"{axis.tag:4s}  min: {axis.min_value:8.2f}  default: {axis.default_value:8.2f}  max: {axis.max_value:8.2f}")
    return "\n".join(parts)


def _build_instances_summary_text(font: TtfFont) -> str:
    parts = [f"{font.font_family or 'Unknown Font'}"]
    parts.append(f"Named instances: {len(font.variable_instances)}")
    parts.append("")
    for instance in font.variable_instances[:4]:
        label = instance.name("en") or instance.label
        coords = ", ".join(f"{k}={v:.2f}" for k, v in sorted(instance.coordinates.items()))
        parts.append(f"{label:30s}  [{coords}]")
    return "\n".join(parts)


def _build_coverage_summary_text(font: Font, coverage: dict[str, object]) -> str:
    parts = [f"{font.font_family or 'Unknown Font'}"]
    requested = int(coverage.get("requested_count", 0))
    covered = int(coverage.get("covered_count", 0))
    parts.append(f"Web coverage: {covered}/{requested} codepoints")

    groups = coverage.get("groups", [])
    if groups:
        parts.append("")
        for group in groups[:5]:
            group_label = group.get("label", "")
            covered_count = group.get("covered_count", 0)
            requested_count = group.get("requested_count", 0)
            parts.append(f"  {group_label:20s} {covered_count:4d}/{requested_count:4d}")

    return "\n".join(parts)


def _build_html(payload: dict[str, object]) -> str:
    identity = _dict(payload.get("identity"))
    metrics = _dict(payload.get("metrics"))
    variable = _dict(payload.get("variable"))
    coverage = payload.get("coverage")
    artifacts = _list(payload.get("artifacts"))
    warnings = _list(payload.get("warnings"))
    readiness = payload.get("readiness")
    actions = _list(payload.get("next_actions"))
    decision = payload.get("decision")
    delta_summary = payload.get("delta_summary")
    size_summary = payload.get("size_summary")

    readiness_score = int(readiness.get("score", 100)) if readiness else 100
    readiness_status = str(readiness.get("status", "ready")) if readiness else "ready"
    readiness_color = {
        "ready": "#22c55e",
        "warning": "#eab308",
        "caution": "#f97316",
        "blocked": "#ef4444",
    }.get(readiness_status, "#6b7280")

    warning_items = "".join(
        "<li>"
        f"<strong style=\"color:{_severity_color(item.get('severity', 'info'))}\">"
        f"{_escape(item.get('severity', 'info'))}</strong> "
        f"{_escape(item.get('code', 'warning'))}: {_escape(item.get('message', ''))}"
        f"{_remediation_html(item.get('remediation'))}"
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
        "code{background:#f5f5f5;padding:.1rem .25rem}"
        ".readiness-badge{display:inline-block;padding:.25rem .75rem;border-radius:.375rem;color:#fff;font-weight:600}"
        "</style>\n"
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
        "  <h2>Readiness</h2>\n"
        "  <table><tbody>\n"
        f"    <tr><th>Score</th><td><span class=\"readiness-badge\" style=\"background-color:{readiness_color}\">{readiness_score}</span> ({readiness_status})</td></tr>\n"
        f"    <tr><th>Issues</th><td>{len(warnings)}</td></tr>\n"
        f"    <tr><th>Blockers</th><td>{sum(1 for w in warnings if isinstance(w,dict) and w.get('severity')=='blocker')}</td></tr>\n"
        "  </tbody></table>\n"
        f"  <p>{_escape(readiness.get('prioritized_causes', [])[0].get('message', '')) if readiness and isinstance(readiness.get('prioritized_causes'),list) and len(readiness.get('prioritized_causes', [])) > 0 else ''}</p>\n"
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
        f"{_decision_summary_html(decision)}"
        f"{_delta_summary_html(delta_summary)}"
        f"{_size_summary_html(size_summary)}"
        "</body>\n"
        "</html>\n"
    )


def _delta_summary_html(delta_summary: object) -> str:
    if not isinstance(delta_summary, dict):
        return ""
    title = _escape(delta_summary.get("text", "Delta Summary"))
    glyph_count = delta_summary.get("glyph_count", 0)
    total_movement = delta_summary.get("total_point_movement", 0)
    max_movement = delta_summary.get("max_point_movement", 0)
    return (
        "  <h2>Variable Delta Summary</h2>\n"
        f"  <p><strong>Sample text:</strong> {title}</p>\n"
        "  <table><tbody>\n"
        f"    <tr><th>Glyphs analyzed</th><td>{_escape(glyph_count)}</td></tr>\n"
        f"    <tr><th>Total point movement</th><td>{_escape(total_movement)}</td></tr>\n"
        f"    <tr><th>Max point movement</th><td>{_escape(max_movement)}</td></tr>\n"
        "  </tbody></table>\n"
    )


def _decision_summary_html(decision: object) -> str:
    if not isinstance(decision, dict):
        return ""
    action = _escape(decision.get("recommended_action", "unknown"))
    rationale_list = _list(decision.get("rationale", []))
    rationale_items = "".join(
        f"<li>{_escape(item)}</li>\n" for item in rationale_list if isinstance(item, str)
    )
    return (
        "  <h2>Decision Analytics</h2>\n"
        "  <table><tbody>\n"
        f"    <tr><th>Recommended Action</th><td><strong>{action}</strong></td></tr>\n"
        "  </tbody></table>\n"
        f"  <h3>Rationale</h3>\n"
        f"  <ul>{rationale_items}</ul>\n"
    )


def _size_summary_html(size_summary: object) -> str:
    if not isinstance(size_summary, dict):
        return ""
    current = size_summary.get("current_size_bytes", 0)
    source = size_summary.get("source_size_bytes")
    delta = size_summary.get("size_delta_bytes")
    delta_pct = size_summary.get("size_delta_percent")
    output = (
        "  <h2>Size Summary</h2>\n"
        "  <table><tbody>\n"
        f"    <tr><th>Current size</th><td>{_escape(current)} bytes</td></tr>\n"
    )
    if source is not None:
        output += (
            f"    <tr><th>Source size</th><td>{_escape(source)} bytes</td></tr>\n"
        )
        if delta is not None and delta_pct is not None:
            output += (
                f"    <tr><th>Size delta</th><td>{_escape(delta)} bytes ({_escape(delta_pct)}%)</td></tr>\n"
            )
    output += "  </tbody></table>\n"
    return output


def _build_pdf_summary(payload: dict[str, object]) -> bytes:
    """Build a minimal PDF summary from QA report payload."""
    import zlib

    identity = payload.get("identity", {})
    readiness = payload.get("readiness", {})
    warnings = payload.get("warnings", [])

    title = str(identity.get("font_family", "Font"))
    score = int(readiness.get("score", 100)) if readiness else 100
    status = str(readiness.get("status", "ready")) if readiness else "ready"

    top_warnings = [
        w for w in _list(warnings)
        if isinstance(w, dict) and w.get("severity") in ("blocker", "warning")
    ][:3]

    lines = [
        f"Font QA Report - {title}",
        "",
        f"Readiness Score: {score} [{status.upper()}]",
        "",
        "Top Warnings:",
    ]

    for i, w in enumerate(top_warnings, 1):
        sev = w.get("severity", "info").upper()
        code = w.get("code", "unknown")
        msg = w.get("message", "")[:80]
        lines.append(f"{i}. [{sev}] {code}: {msg}")

    content_str = "\n".join(lines)

    pdf_header = b"%PDF-1.4\n"

    obj1 = b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
    obj2 = b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"

    media_box = b"[0 0 612 792]"
    obj3 = (
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox "
        + media_box
        + b" /Contents 4 0 R >>\nendobj\n"
    )

    compressed = zlib.compress(content_str.encode("latin-1", errors="replace"))
    obj4 = (
        b"4 0 obj\n<< /Filter /FlateDecode /Length "
        + str(len(compressed)).encode()
        + b" >>\nstream\n"
        + compressed
        + b"\nendstream\nendobj\n"
    )

    xref_obj_count = 5
    objects = [obj1, obj2, obj3, obj4]

    xref_start = len(pdf_header) + sum(len(obj) for obj in objects)
    xref_lines = [b"xref\n0 " + str(xref_obj_count).encode() + b"\n"]
    xref_lines.append(b"0000000000 65535 f \n")
    offset = len(pdf_header)
    for obj in objects:
        xref_lines.append(f"{offset:010d} 00000 n \n".encode("ascii"))
        offset += len(obj)

    trailer = (
        b"trailer\n<< /Size " + str(xref_obj_count).encode() + b" /Root 1 0 R >>\n"
        b"startxref\n" + str(xref_start).encode() + b"\n%%EOF\n"
    )

    return pdf_header + b"".join(objects) + b"".join(xref_lines) + trailer


def _build_markdown_summary(payload: dict[str, object]) -> str:
    """Build a concise markdown summary from QA report payload."""
    identity = payload.get("identity", {})
    readiness = payload.get("readiness", {})
    warnings = payload.get("warnings", [])
    coverage = payload.get("coverage")
    next_actions = payload.get("next_actions", [])

    font_family = str(identity.get("font_family", "Unknown Font"))
    font_style = str(identity.get("font_style", ""))
    is_variable = bool(identity.get("is_variable", False))
    format_value = str(identity.get("format", "Unknown"))

    score = int(readiness.get("score", 100)) if readiness else 100
    status = str(readiness.get("status", "ready")) if readiness else "ready"

    warning_count = len([w for w in _list(warnings) if isinstance(w, dict)])
    blocker_count = len([w for w in _list(warnings) if isinstance(w, dict) and w.get("severity") == "blocker"])
    warning_count_only = len([w for w in _list(warnings) if isinstance(w, dict) and w.get("severity") == "warning"])
    info_count = len([w for w in _list(warnings) if isinstance(w, dict) and w.get("severity") == "info"])

    action_count = len([a for a in _list(next_actions) if isinstance(a, dict)])

    coverage_text = "N/A"
    if isinstance(coverage, dict):
        covered = coverage.get("covered_count", 0)
        requested = coverage.get("requested_count", 0)
        coverage_text = f"{covered}/{requested}"

    lines = [
        f"# Font QA Report - {font_family}",
        "",
        "## Summary",
        "",
        f"- **Font:** {font_family} {font_style}".strip(),
        f"- **Format:** {format_value}",
        f"- **Variable:** {'Yes' if is_variable else 'No'}",
        f"- **Readiness Score:** {score} ({status})",
        f"- **Warnings:** {warning_count} (blockers: {blocker_count}, warnings: {warning_count_only}, info: {info_count})",
        f"- **Next Actions:** {action_count}",
        f"- **Coverage:** {coverage_text}",
        "",
    ]

    top_warnings = [
        w for w in _list(warnings)
        if isinstance(w, dict) and w.get("severity") in ("blocker", "warning")
    ][:3]

    if top_warnings:
        lines.extend([
            "## Warnings",
            "",
        ])
        for i, w in enumerate(top_warnings, 1):
            sev = w.get("severity", "info").upper()
            code = w.get("code", "unknown")
            msg = w.get("message", "")[:100]
            lines.append(f"{i}. [{sev}] {code}: {msg}")
        lines.append("")

    if isinstance(coverage, dict):
        lines.extend([
            "## Coverage Details",
            "",
            f"- **Requested:** {coverage.get('requested_count', 0)} codepoints",
            f"- **Covered:** {coverage.get('covered_count', 0)} codepoints",
            f"- **Missing:** {coverage.get('missing_count', 0)} codepoints",
            "",
        ])

    lines.append("---")
    lines.append("*Generated by Font QA Report*")

    return "\n".join(lines)


def generate_decision_report(qa_package: FontQaPackage) -> dict[str, object]:
    """Generate a decision report from QA package data.

    Args:
        qa_package: A FontQaPackage containing QA report data.

    Returns:
        A dictionary with keys:
        - decision: One of "live", "static", or "static_fallback"
        - recommended_actions: List of recommended actions
        - severity_summary: Dict with "blocker", "warning", "info" counts
        - source_label: Source label from the QA package, if available
        - font_format: Font format from the QA report identity
    """
    report = qa_package.report
    payload = report.to_dict()

    identity = payload.get("identity", {})
    is_variable = bool(identity.get("is_variable", False))
    source_label = identity.get("source")
    font_format = identity.get("format", "")

    recommendations: list[str] = []
    decision: str

    if is_variable:
        decision = "live"
        recommendations.append("Export variable font for web usage")
    else:
        decision = "static_fallback"
        recommendations.append("Export as static font")
        recommendations.append("Variable font features not applicable")

    warnings = payload.get("warnings", [])
    severity_summary = {
        "blocker": sum(1 for w in warnings if isinstance(w, dict) and w.get("severity") == "blocker"),
        "warning": sum(1 for w in warnings if isinstance(w, dict) and w.get("severity") == "warning"),
        "info": sum(1 for w in warnings if isinstance(w, dict) and w.get("severity") == "info"),
    }

    return {
        "decision": decision,
        "recommended_actions": recommendations,
        "severity_summary": severity_summary,
        "source_label": source_label,
        "font_format": font_format,
    }


__all__ = ["FontQaPackage", "FontQaReport", "FontQaReporter", "generate_decision_report"]
