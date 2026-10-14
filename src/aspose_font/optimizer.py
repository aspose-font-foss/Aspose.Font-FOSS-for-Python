"""Autonomous web font optimization decision engine (FONT-255)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from aspose_font._font_base import Font
from aspose_font.ttf.font import TtfFont
from aspose_font.web import WebFontBundle, WebFontOptimizer, WebFontOptimizerPackage


@dataclass(frozen=True)
class WebFontOptimizerDecision:
    """Automated decision result for web export mode."""

    mode: str
    reason: str
    confidence: float
    affected_axes: list[str]
    recommended_presets: list[str]


@dataclass(slots=True)
class _PreparedFontWithDecision:
    font: Font
    export_mode: str
    decision: WebFontOptimizerDecision


@dataclass(slots=True)
class _PreparedStaticInstance:
    font: Font
    supported_stat_policies: tuple[str, ...] = ()
    stat_policy_recommendation: str | None = None
    stat_policy_recommendation_reasons: tuple[str, ...] = ()
    stat_policy_next_action: str | None = None
    stat_policy_override_suggestion: str | None = None
    stat_policy_override_suggestion_reasons: tuple[str, ...] = ()


@dataclass(slots=True)
class WebFontOptimizerPackageWithDecision:
    """Enhanced web package that includes optimization decision metadata."""

    bundle: WebFontBundle
    decision: WebFontOptimizerDecision
    size_summary: dict[str, Any]
    readiness: dict[str, Any]
    notes: list[dict[str, str]]
    manifest: dict[str, Any]
    css: str = ""
    specimen_html: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    decision_report: dict[str, Any] | None = None
    cdn_manifest: dict[str, Any] | None = None

    def write_to(self, directory: str | Path, *, decision_report_pdf: str | Path | None = None) -> list[Path]:
        """Write the package to a directory.

        Args:
            directory: Output directory path
            decision_report_pdf: Optional path to write PDF decision report

        Returns:
            List of written file paths
        """
        output_dir = Path(directory)
        written = self.bundle.write_to(output_dir)

        manifest_path = output_dir / "optimizer-manifest.json"
        manifest_path.write_text(
            json.dumps(self.manifest, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        written.append(manifest_path)

        if self.decision_report is not None:
            decision_path = output_dir / "decision_report.json"
            decision_path.write_text(
                json.dumps(self.decision_report, indent=2, sort_keys=True),
                encoding="utf-8",
            )
            written.append(decision_path)
            if decision_report_pdf is not None:
                from aspose_font.web import DecisionReport
                pdf_path = Path(decision_report_pdf)
                if not pdf_path.is_absolute():
                    pdf_path = output_dir / pdf_path
                pdf_path.parent.mkdir(parents=True, exist_ok=True)
                report = DecisionReport(
                    mode=self.decision_report.get("mode", "unknown"),
                    reasons=self.decision_report.get("reasons", []),
                    summary=self.decision_report.get("summary", ""),
                    remediation=self.decision_report.get("remediation", []),
                )
                pdf_data = DecisionReport._build_decision_pdf(report)
                pdf_path.write_bytes(pdf_data)
                written.append(pdf_path)

        if self.cdn_manifest is not None:
            cdn_manifest_path = output_dir / "cdn-manifest.json"
            cdn_manifest_path.write_text(
                json.dumps(self.cdn_manifest, indent=2, sort_keys=True),
                encoding="utf-8",
            )
            written.append(cdn_manifest_path)

        return written


def analyze_font_for_web_optimization(font: Font) -> WebFontOptimizerDecision:
    """
    Analyze a font and make an automated decision about optimal web export mode.

    Decision criteria:
    - Variable fonts with >1 axis and meaningful interpolation: "live"
    - Variable fonts with single axis or minimal deltas: "static-fallback"
    - Static fonts: "static"
    - Fonts with unsupported variation tables: "static-fallback"

    Args:
        font: The font to analyze

    Returns:
        WebFontOptimizerDecision with mode, reason, confidence, affected_axes, and recommended_presets
    """
    mode: str
    reason: str
    confidence: float = 0.0
    affected_axes: list[str] = []
    recommended_presets: list[str] = []

    source_is_variable = isinstance(font, TtfFont) and font.is_variable

    if source_is_variable:
        ttf_font = font
        axes = ttf_font.variable_axes
        axis_count = len(axes) if axes else 0

        if axis_count > 1:
            mode = "live"
            confidence = 0.95
            affected_axes = [ax.tag for ax in axes] if axes else []
            recommended_presets = _suggest_presets_for_axes(axes)
            reason = (
                f"Variable font with {axis_count} axes and meaningful interpolation. "
                "Output supports variable axes."
            )
        elif axis_count == 1:
            mode = "static-fallback"
            confidence = 0.85
            affected_axes = [axes[0].tag] if axes else []
            recommended_presets = _suggest_presets_for_axes(axes)
            reason = (
                "Variable font with single axis or minimal deltas. "
                "Recommended fallback to static export for simpler delivery."
            )
        else:
            mode = "static-fallback"
            confidence = 0.80
            reason = "Variable font with no variable axes detected. Fallback to static export."
    else:
        mode = "static"
        confidence = 1.0
        recommended_presets = _suggest_presets_for_static(font)
        reason = "Font is not variable. Static export is appropriate."

    return WebFontOptimizerDecision(
        mode=mode,
        reason=reason,
        confidence=confidence,
        affected_axes=affected_axes,
        recommended_presets=recommended_presets,
    )


def _suggest_presets_for_axes(axes: list[Any] | None) -> list[str]:
    """Suggest subset presets based on available axes."""
    if not axes:
        return []
    presets = []
    for ax in axes:
        if hasattr(ax, "tag"):
            tag = ax.tag
            if tag in ("wght", "wdth", "slnt", "ital", "opsz"):
                presets.append("latin")
                if tag in ("wght", "wdth"):
                    presets.append("latin-ext")
                break
    if not presets:
        presets.append("latin")
    return list(dict.fromkeys(presets))


def _suggest_presets_for_static(font: Font) -> list[str]:
    """Suggest subset presets for static fonts."""
    presets = ["latin"]
    font_name = (font.font_name or "").lower()
    if "cyrillic" in font_name or "russian" in font_name:
        presets.append("cyrillic")
    if "greek" in font_name:
        presets.append("greek")
    if "hebrew" in font_name:
        presets.append("hebrew")
    if "arabic" in font_name:
        presets.append("arabic")
    return presets


def build_web_optimizer_package(
    font: Font,
    *,
    source_path: str | None = None,
    file_stem: str | None = None,
    include_woff: bool = True,
    font_display: str = "swap",
    preview_text: str = "Hamburgefons 0123456789",
    instance_coordinates: dict[str, float] | None = None,
    instance_name: str | None = None,
    presets: str | tuple[str, ...] = (),
    text: str = "",
    codepoints: tuple[int, ...] = (),
    ranges: tuple[tuple[int, int], ...] = (),
    specimen_template: str = "classic",
    variable_mode: str = "auto",
    naming_strategy: str = "instance-family",
    family_suffix: str | None = None,
    legacy_family_name: str | None = None,
    typographic_family_name: str | None = None,
    legacy_style_name: str | None = None,
    typographic_style_name: str | None = None,
    stat_policy: str = "drop",
    decision: WebFontOptimizerDecision | None = None,
    detailed_reporting: bool = False,
    decision_report: bool = True,
    cdn_base_url: str = "https://cdn.example.com",
    feature_variation_tag: str | None = None,
    **kwargs: Any,
) -> WebFontOptimizerPackageWithDecision:
    """
    One-call web font optimization with automated decision-making.

    This function wraps existing WebFontOptimizer functionality but adds:
    - Automated export mode detection and decision logging
    - Decision-based STAT preservation vs. static synthesis logic
    - Enhanced manifest with decision metadata

    Args:
        font: The font to optimize
        source_path: Optional path to source file for size comparison
        file_stem: Optional filename stem for output assets
        include_woff: Include WOFF format alongside WOFF2
        font_display: Font-display value for @font-face
        preview_text: Preview text for specimen HTML
        instance_coordinates: Explicit coordinate values for instance selection
        instance_name: Named instance to instantiate
        presets: Unicode preset names for subsetting
        text: Text content for subsetting
        codepoints: Individual codepoints for subsetting
        ranges: Codepoint ranges for subsetting
        specimen_template: Specimen template style
        variable_mode: Variable export mode ("auto", "live", "static")
        naming_strategy: Font naming strategy
        family_suffix: Custom family suffix
        legacy_family_name: Explicit legacy family name
        typographic_family_name: Explicit typographic family name
        legacy_style_name: Explicit legacy style name
        typographic_style_name: Explicit typographic style name
        stat_policy: STAT metadata policy
        decision: Optional pre-computed decision to use
        detailed_reporting: Enable detailed performance timing profiling
        decision_report: Generate decision report
        cdn_base_url: Base URL for CDN paths in generated manifest
        feature_variation_tag: Feature variation tag to apply (requires FeatureVariations table)
        **kwargs: Additional keyword arguments

    Returns:
        WebFontOptimizerPackageWithDecision containing bundle, decision, and metadata
    """
    if decision is None:
        decision = analyze_font_for_web_optimization(font)

    effective_variable_mode = _resolve_variable_mode(
        variable_mode,
        decision.mode,
        font,
        presets=presets,
        text=text,
        codepoints=codepoints,
        ranges=ranges,
    )

    package: WebFontOptimizerPackage = WebFontOptimizer.build(
        font,
        source_path=source_path,
        file_stem=file_stem,
        include_woff=include_woff,
        font_display=font_display,
        preview_text=preview_text,
        instance_coordinates=instance_coordinates,
        instance_name=instance_name,
        presets=presets,
        text=text,
        codepoints=codepoints,
        ranges=ranges,
        specimen_template=specimen_template,
        variable_mode=effective_variable_mode,
        naming_strategy=naming_strategy,
        family_suffix=family_suffix,
        legacy_family_name=legacy_family_name,
        typographic_family_name=typographic_family_name,
        legacy_style_name=legacy_style_name,
        typographic_style_name=typographic_style_name,
        stat_policy=stat_policy,
        detailed_reporting=detailed_reporting,
        decision_report=decision_report,
        cdn_base_url=cdn_base_url,
        feature_variation_tag=feature_variation_tag,
        **kwargs,
    )

    size_summary = package.size_summary
    readiness = package.readiness
    notes = package.notes

    metadata = {
        "decision_applied": decision.mode,
        "confidence": decision.confidence,
        "affected_axes": decision.affected_axes,
        "recommended_presets": decision.recommended_presets,
        "decision_reason": decision.reason,
    }

    enhanced_manifest = dict(package.manifest)
    enhanced_manifest["decision"] = decision.mode
    enhanced_manifest["decision_confidence"] = decision.confidence
    enhanced_manifest["decision_metadata"] = metadata
    if feature_variation_tag is not None:
        enhanced_manifest["selected_feature_variation"] = feature_variation_tag

    bundle = package.bundle
    bundle.manifest = enhanced_manifest

    decision_report = package.decision_report
    if decision_report is not None:
        decision_report_dict = {
            "mode": decision_report.mode,
            "decision": decision_report.mode,
            "reasons": decision_report.reasons,
            "reason": decision_report.reason,
            "summary": decision_report.summary,
            "remediation": decision_report.remediation,
            "export_mode": decision.mode,
            "font_path": str(source_path) if source_path else None,
            "confidence": decision.confidence,
            "affected_axes": decision.affected_axes,
        }
    else:
        decision_report_dict = None

    return WebFontOptimizerPackageWithDecision(
        bundle=bundle,
        css=package.css,
        specimen_html=package.specimen_html,
        decision=decision,
        size_summary=size_summary,
        readiness=readiness,
        notes=notes,
        manifest=enhanced_manifest,
        metadata=metadata,
        decision_report=decision_report_dict,
        cdn_manifest=package.cdn_manifest,
    )


def _resolve_variable_mode(
    requested_mode: str,
    analyzed_mode: str,
    font: Font,
    *,
    presets: str | tuple[str, ...] = (),
    text: str = "",
    codepoints: tuple[int, ...] = (),
    ranges: tuple[tuple[int, int], ...] = (),
) -> str:
    """Resolve the effective variable mode based on user request and analysis.

    When subsetting is requested (text, codepoints, ranges, or presets), live variable
    export mode is not supported. In auto mode, this returns "auto" so that WebFontOptimizer
    can handle the subsetting by instantiating the font at default coordinates.
    """
    if requested_mode != "auto":
        return requested_mode

    should_subset = bool(text or codepoints or ranges or presets)
    source_is_variable = isinstance(font, TtfFont) and font.is_variable

    if analyzed_mode == "live":
        if should_subset:
            return "auto"
        return "live" if source_is_variable else "static"
    elif analyzed_mode == "static-fallback":
        return "static"
    else:
        return "auto"


def build_web_optimizer_package_with_plan(
    font: Font,
    decision: WebFontOptimizerDecision,
    *,
    source_path: str | None = None,
    file_stem: str | None = None,
    include_woff: bool = True,
    font_display: str = "swap",
    preview_text: str = "Hamburgefons 0123456789",
    instance_coordinates: dict[str, float] | None = None,
    instance_name: str | None = None,
    presets: str | tuple[str, ...] = (),
    text: str = "",
    codepoints: tuple[int, ...] = (),
    ranges: tuple[tuple[int, int], ...] = (),
    specimen_template: str = "classic",
    variable_mode: str = "auto",
    naming_strategy: str = "instance-family",
    family_suffix: str | None = None,
    legacy_family_name: str | None = None,
    typographic_family_name: str | None = None,
    legacy_style_name: str | None = None,
    typographic_style_name: str | None = None,
    stat_policy: str = "drop",
    cdn_base_url: str = "https://cdn.example.com",
    **kwargs: Any,
) -> WebFontOptimizerPackageWithDecision:
    """
    Enhanced version that accepts a pre-computed decision for deterministic workflows.

    Useful for batch processing or when decisions are made externally.

    Args:
        font: The font to optimize
        decision: Pre-computed optimization decision
        source_path: Optional path to source file for size comparison
        file_stem: Optional filename stem for output assets
        include_woff: Include WOFF format alongside WOFF2
        font_display: Font-display value for @font-face
        preview_text: Preview text for specimen HTML
        instance_coordinates: Explicit coordinate values for instance selection
        instance_name: Named instance to instantiate
        presets: Unicode preset names for subsetting
        text: Text content for subsetting
        codepoints: Individual codepoints for subsetting
        ranges: Codepoint ranges for subsetting
        specimen_template: Specimen template style
        variable_mode: Variable export mode ("auto", "live", "static")
        naming_strategy: Font naming strategy
        family_suffix: Custom family suffix
        legacy_family_name: Explicit legacy family name
        typographic_family_name: Explicit typographic family name
        legacy_style_name: Explicit legacy style name
        typographic_style_name: Explicit typographic style name
        stat_policy: STAT metadata policy
        cdn_base_url: Base URL for CDN paths in generated manifest
        **kwargs: Additional keyword arguments

    Returns:
        WebFontOptimizerPackageWithDecision containing bundle, decision, and metadata
    """
    return build_web_optimizer_package(
        font,
        source_path=source_path,
        file_stem=file_stem,
        include_woff=include_woff,
        font_display=font_display,
        preview_text=preview_text,
        instance_coordinates=instance_coordinates,
        instance_name=instance_name,
        presets=presets,
        text=text,
        codepoints=codepoints,
        ranges=ranges,
        specimen_template=specimen_template,
        variable_mode=variable_mode,
        naming_strategy=naming_strategy,
        family_suffix=family_suffix,
        legacy_family_name=legacy_family_name,
        typographic_family_name=typographic_family_name,
        legacy_style_name=legacy_style_name,
        typographic_style_name=typographic_style_name,
        stat_policy=stat_policy,
        decision=decision,
        cdn_base_url=cdn_base_url,
        **kwargs,
    )
