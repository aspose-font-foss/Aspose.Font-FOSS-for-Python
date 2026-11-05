"""Plain-language font capability discovery facade."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from aspose_font._font_base import Font
from aspose_font.subset_presets import SUBSET_PRESETS, codepoints_for_presets
from aspose_font.ttf.font import TtfFont
from aspose_font.variation import VariableAxis

if TYPE_CHECKING:
    pass


@dataclass(frozen=True, slots=True)
class CapabilitySummary:
    """Plain-language summary of font capabilities."""

    label: str
    description: str
    details: dict[str, object]

    def to_dict(self) -> dict[str, object]:
        return {
            "label": self.label,
            "description": self.description,
            "details": self.details,
        }


@dataclass(frozen=True, slots=True)
class AxisDescription:
    """Human-readable description for a font axis."""

    tag: str
    label: str
    description: str | None
    min_value: float
    default_value: float
    max_value: float
    unit_label: str
    default_description: str
    range_summary: str
    presets: list[dict[str, object]]
    css_hint: str

    def to_dict(self) -> dict[str, object]:
        return {
            "tag": self.tag,
            "label": self.label,
            "description": self.description,
            "min_value": self.min_value,
            "default_value": self.default_value,
            "max_value": self.max_value,
            "unit_label": self.unit_label,
            "default_description": self.default_description,
            "range_summary": self.range_summary,
            "presets": self.presets,
            "css_hint": self.css_hint,
        }


@dataclass(frozen=True, slots=True)
class ScriptCoverage:
    """Summary of script coverage for a font."""

    script_family: str
    script_label: str
    unicode_ranges: tuple[tuple[int, int], ...]
    covered_count: int
    requested_count: int
    percentage: float
    web_ready: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "script_family": self.script_family,
            "script_label": self.script_label,
            "unicode_ranges": [list(r) for r in self.unicode_ranges],
            "covered_count": self.covered_count,
            "requested_count": self.requested_count,
            "percentage": self.percentage,
            "web_ready": self.web_ready,
        }


@dataclass(frozen=True, slots=True)
class CSSHints:
    """CSS implementation hints for a font."""

    at_font_face: dict[str, object]
    css_custom_properties: dict[str, str] | None
    font_display: str
    unicode_range: str | None

    def to_dict(self) -> dict[str, object]:
        return {
            "at_font_face": self.at_font_face,
            "css_custom_properties": self.css_custom_properties,
            "font_display": self.font_display,
            "unicode_range": self.unicode_range,
        }


@dataclass(frozen=True, slots=True)
class ReleaseRisk:
    """Release risk flag with severity and explanation."""

    code: str
    severity: str
    message: str
    reason: str
    recommendation: str

    def to_dict(self) -> dict[str, object]:
        return {
            "code": self.code,
            "severity": self.severity,
            "message": self.message,
            "reason": self.reason,
            "recommendation": self.recommendation,
        }


@dataclass(frozen=True, slots=True)
class FontCapabilityReport:
    """Complete capability report for a font."""

    font_identity: dict[str, object]
    axes: tuple[AxisDescription, ...]
    coverage: tuple[ScriptCoverage, ...]
    css_hints: CSSHints
    release_risks: tuple[ReleaseRisk, ...]
    summaries: tuple[CapabilitySummary, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": "font_capability_report",
            "font_identity": self.font_identity,
            "axes": [axis.to_dict() for axis in self.axes],
            "coverage": [coverage.to_dict() for coverage in self.coverage],
            "css_hints": self.css_hints.to_dict(),
            "release_risks": [risk.to_dict() for risk in self.release_risks],
            "summaries": [summary.to_dict() for summary in self.summaries],
        }

    def to_json(self, *, indent: int = 2, sort_keys: bool = True) -> str:
        import json

        return json.dumps(self.to_dict(), indent=indent, sort_keys=sort_keys)


class FontCapabilityBuilder:
    """Build plain-language capability reports for fonts."""

    _COMMON_SCRIPT_FAMILIES: tuple[dict[str, object], ...] = (
        {
            "family": "latin",
            "label": "Latin",
            "ranges": SUBSET_PRESETS.get("latin", ()),
        },
        {
            "family": "latin-ext",
            "label": "Latin Extended",
            "ranges": SUBSET_PRESETS.get("latin-ext", ()),
        },
        {
            "family": "cyrillic",
            "label": "Cyrillic",
            "ranges": SUBSET_PRESETS.get("cyrillic", ()),
        },
        {
            "family": "greek",
            "label": "Greek",
            "ranges": SUBSET_PRESETS.get("greek", ()),
        },
        {
            "family": "hebrew",
            "label": "Hebrew",
            "ranges": SUBSET_PRESETS.get("hebrew", ()),
        },
        {
            "family": "arabic",
            "label": "Arabic",
            "ranges": SUBSET_PRESETS.get("arabic", ()),
        },
        {
            "family": "devanagari",
            "label": "Devanagari",
            "ranges": SUBSET_PRESETS.get("devanagari", ()),
        },
        {
            "family": "thai",
            "label": "Thai",
            "ranges": SUBSET_PRESETS.get("thai", ()),
        },
    )

    _COMMON_AXES: tuple[str, ...] = ("wght", "wdth", "ital", "slnt", "opsz")

    @classmethod
    def build(
        cls,
        font: Font,
        *,
        preferred_languages: str | tuple[str, ...] = "en",
    ) -> FontCapabilityReport:
        """Build a capability report for a font."""
        preferred_tuple = (preferred_languages,) if isinstance(preferred_languages, str) else preferred_languages

        font_identity = cls._build_font_identity(font)
        axes = cls._build_axes_description(font, preferred_languages=preferred_tuple)
        coverage = cls._build_coverage_summary(font, preferred_languages=preferred_tuple)
        css_hints = cls._build_css_hints(font, axes)
        release_risks = cls._build_release_risks(font, axes, coverage)
        summaries = cls._build_summaries(font, axes, coverage, css_hints, release_risks)

        return FontCapabilityReport(
            font_identity=font_identity,
            axes=axes,
            coverage=coverage,
            css_hints=css_hints,
            release_risks=release_risks,
            summaries=summaries,
        )

    @classmethod
    def _build_font_identity(cls, font: Font) -> dict[str, object]:
        return {
            "font_name": font.font_name or "Unknown",
            "font_family": font.font_family or "Unknown",
            "font_style": font.font_style or "Normal",
            "format": font.font_type.value,
            "num_glyphs": font.num_glyphs,
            "is_variable": isinstance(font, TtfFont) and font.is_variable,
        }

    @classmethod
    def _build_axes_description(
        cls,
        font: Font,
        *,
        preferred_languages: tuple[str, ...],
    ) -> tuple[AxisDescription, ...]:
        if not isinstance(font, TtfFont) or not font.is_variable:
            return ()

        axes: list[AxisDescription] = []
        for axis in font.variable_axes:
            if axis.tag not in cls._COMMON_AXES:
                continue

            default_desc = cls._describe_axis_value(axis, axis.default_value)
            preset_list = [
                {
                    "preset_name": preset.name,
                    "value": preset.value,
                    "description": preset.description,
                }
                for preset in axis.presets
            ]

            css_hint_parts: list[str] = []
            if axis.tag in ("wght", "wdth", "opsz", "slnt"):
                css_hint_parts.append(f"`{axis.css_axis_tag}`")
            if axis.presets:
                css_hint_parts.append(f"with presets: {', '.join(p['preset_name'] for p in preset_list[:3])}")
            css_hint = " ".join(css_hint_parts) if css_hint_parts else axis.css_axis_tag

            axes.append(
                AxisDescription(
                    tag=axis.tag,
                    label=axis.name(preferred_languages) or axis.label,
                    description=axis.description,
                    min_value=axis.min_value,
                    default_value=axis.default_value,
                    max_value=axis.max_value,
                    unit_label=axis.unit_label,
                    default_description=default_desc,
                    range_summary=axis.range_summary,
                    presets=preset_list,
                    css_hint=css_hint,
                )
            )

        return tuple(axes)

    @classmethod
    def _describe_axis_value(cls, axis: VariableAxis, value: float) -> str:
        preset = next((p for p in axis.presets if p.value == value), None)
        formatted = axis.format_value(value)
        if preset:
            return f"{preset.name} ({formatted})"
        if value == axis.default_value:
            return f"Default ({formatted})"
        return formatted

    @classmethod
    def _build_coverage_summary(
        cls,
        font: Font,
        *,
        preferred_languages: tuple[str, ...],
    ) -> tuple[ScriptCoverage, ...]:
        coverage: list[ScriptCoverage] = []

        for script in cls._COMMON_SCRIPT_FAMILIES:
            script_family = str(script["family"])
            script_label = str(script["label"])
            ranges = tuple(script["ranges"])

            try:
                codepoints = codepoints_for_presets(script_family)
            except ValueError:
                continue

            requested_count = len(codepoints)
            if requested_count == 0:
                continue

            covered_count = cls._count_covered_codepoints(font, codepoints)
            percentage = (covered_count / requested_count * 100) if requested_count > 0 else 0.0
            web_ready = percentage >= 99.0

            coverage.append(
                ScriptCoverage(
                    script_family=script_family,
                    script_label=script_label,
                    unicode_ranges=ranges,
                    covered_count=covered_count,
                    requested_count=requested_count,
                    percentage=percentage,
                    web_ready=web_ready,
                )
            )

        return tuple(coverage)

    @classmethod
    def _count_covered_codepoints(cls, font: Font, codepoints: set[int]) -> int:
        if isinstance(font, TtfFont) and font.is_variable:
            encoding = font.encoding
        else:
            encoding = font.encoding

        covered = 0
        for codepoint in codepoints:
            try:
                gid = encoding.unicode_to_gid(codepoint)
                if gid is not None and gid != 0:
                    covered += 1
            except Exception:
                pass

        return covered

    @classmethod
    def _build_css_hints(cls, font: Font, axes: tuple[AxisDescription, ...]) -> CSSHints:
        recommended_weight = 400
        for axis in axes:
            if axis.tag == "wght":
                recommended_weight = int(axis.default_value)
                break

        at_font_face: dict[str, object] = {
            "font-family": font.font_family or "Font",
            "src": "url('font.woff2') format('woff2')",
            "font-weight": recommended_weight,
            "font-style": "normal" if not cls._has_italic_axis(axes) else "italic",
            "font-display": "swap",
        }

        css_custom_properties: dict[str, str] | None = None
        if axes:
            custom_properties_parts: list[str] = []
            for axis in axes:
                if axis.tag in ("wght", "wdth", "opsz", "slnt"):
                    custom_properties_parts.append(f"{axis.tag}: var(--{axis.tag})")
            if custom_properties_parts:
                css_custom_properties = {
                    "axis_variables": "  --wght: 400; /* Weight (100–900) */",
                    "usage_example": f"@font-face {{\n{', '.join(custom_properties_parts)};\n}}",
                }

        font_display = "swap"

        unicode_range_parts: list[str] = []
        for script in cls._COMMON_SCRIPT_FAMILIES:
            script_family = str(script["family"])
            if script_family == "latin":
                unicode_range_parts.append("U+0000-00FF")
            elif script_family == "latin-ext":
                unicode_range_parts.append("U+0100-024F, U+1E00-1EFF")
        unicode_range = ", ".join(unicode_range_parts) if unicode_range_parts else None

        return CSSHints(
            at_font_face=at_font_face,
            css_custom_properties=css_custom_properties,
            font_display=font_display,
            unicode_range=unicode_range,
        )

    @classmethod
    def _has_italic_axis(cls, axes: tuple[AxisDescription, ...]) -> bool:
        return any(axis.tag == "ital" for axis in axes)

    @classmethod
    def _build_release_risks(
        cls,
        font: Font,
        axes: tuple[AxisDescription, ...],
        coverage: tuple[ScriptCoverage, ...],
    ) -> tuple[ReleaseRisk, ...]:
        risks: list[ReleaseRisk] = []

        if not isinstance(font, TtfFont) or not font.is_variable:
            if not font.font_name or not font.font_family:
                risks.append(
                    ReleaseRisk(
                        code="missing-font-names",
                        severity="blocker",
                        message="Font is missing required name table entries.",
                        reason="Font name and family name are required for OS installation and CSS matching.",
                        recommendation="Add fontName (name ID 6) and fontFamily (name ID 1) records.",
                    )
                )
        else:
            has_stat = cls._font_has_stat_table(font)
            if not has_stat:
                risks.append(
                    ReleaseRisk(
                        code="missing-stat-table",
                        severity="warning",
                        message="Variable font missing STAT table.",
                        reason="STAT table provides named instance metadata for design apps and CSS.",
                        recommendation="Add STAT table with AxisValue records for each named instance.",
                    )
                )

        for cov in coverage:
            if not cov.web_ready and cov.script_family in ("latin", "latin-ext", "cyrillic", "greek"):
                missing_count = cov.requested_count - cov.covered_count
                if missing_count > 0:
                    severity = "warning" if missing_count < 100 else "blocker"
                    risks.append(
                        ReleaseRisk(
                            code=f"coverage-gap-{cov.script_family}",
                            severity=severity,
                            message=f"{cov.script_label} script has {missing_count} missing codepoints ({cov.percentage:.0f}% covered).",
                            reason=f"Missing codepoints will render as missing glyph boxes for {cov.script_label} text.",
                            recommendation=f"Extend the font with missing {cov.script_label} codepoints or use subsetting to exclude this script.",
                        )
                    )

        return tuple(risks)

    @classmethod
    def _font_has_stat_table(cls, font: Font) -> bool:
        if not isinstance(font, TtfFont):
            return False
        if not font.is_variable:
            return False
        try:
            table = font.ttf_tables.get_raw("STAT")
            return table is not None
        except Exception:
            return False

    @classmethod
    def _build_summaries(
        cls,
        font: Font,
        axes: tuple[AxisDescription, ...],
        coverage: tuple[ScriptCoverage, ...],
        css_hints: CSSHints,
        release_risks: tuple[ReleaseRisk, ...],
    ) -> tuple[CapabilitySummary, ...]:
        summaries: list[CapabilitySummary] = []

        total_axes = len(axes)
        if total_axes == 0:
            axis_summary = CapabilitySummary(
                label="Variable Axes",
                description="Static font with no variable axes.",
                details={"axis_count": 0, "is_variable": False},
            )
        else:
            axis_labels = [a.label for a in axes]
            axis_summary = CapabilitySummary(
                label="Variable Axes",
                description=f"Variable font with {total_axes} axes.",
                details={
                    "axis_count": total_axes,
                    "is_variable": True,
                    "axis_labels": axis_labels,
                },
            )
        summaries.append(axis_summary)

        total_scripts = len(coverage)
        web_ready_scripts = sum(1 for c in coverage if c.web_ready)
        coverage_summary = CapabilitySummary(
            label="Script Coverage",
            description=f"Supports {total_scripts} common script families, {web_ready_scripts} fully web-ready.",
            details={
                "script_family_count": total_scripts,
                "web_ready_count": web_ready_scripts,
                "web_ready_families": [c.script_label for c in coverage if c.web_ready],
            },
        )
        summaries.append(coverage_summary)

        if css_hints.css_custom_properties:
            css_summary = CapabilitySummary(
                label="CSS implementation",
                description="Ready for variable fonts with CSS custom properties.",
                details={
                    "has_css_custom_properties": True,
                    "supports_css_axes": list(css_hints.css_custom_properties.keys()),
                },
            )
        else:
            css_summary = CapabilitySummary(
                label="CSS implementation",
                description="Ready for @font-face usage with static weight/style.",
                details={
                    "has_css_custom_properties": False,
                    "recommended_weight": css_hints.at_font_face.get("font-weight", 400),
                },
            )
        summaries.append(css_summary)

        if release_risks:
            blocker_count = sum(1 for r in release_risks if r.severity == "blocker")
            warning_count = sum(1 for r in release_risks if r.severity == "warning")
            risk_summary = CapabilitySummary(
                label="Release readiness",
                description=f"Found {blocker_count} blocker(s) and {warning_count} warning(s).",
                details={
                    "blocker_count": blocker_count,
                    "warning_count": warning_count,
                    "has_issues": True,
                },
            )
        else:
            risk_summary = CapabilitySummary(
                label="Release readiness",
                description="No release risks detected.",
                details={
                    "blocker_count": 0,
                    "warning_count": 0,
                    "has_issues": False,
                },
            )
        summaries.append(risk_summary)

        return tuple(summaries)


__all__ = [
    "CapabilitySummary",
    "AxisDescription",
    "ScriptCoverage",
    "CSSHints",
    "ReleaseRisk",
    "FontCapabilityReport",
    "FontCapabilityBuilder",
]
