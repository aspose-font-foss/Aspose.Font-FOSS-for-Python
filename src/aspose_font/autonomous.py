"""Autonomous font processing workflow."""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Optional

from aspose_font._font_base import Font
from aspose_font.qa import FontQaPackage, FontQaReporter
from aspose_font.ttf.font import TtfFont
from aspose_font.web import WebFontOptimizer, WebFontOptimizerPackage


@dataclass(frozen=True, slots=True)
class AutonomousWorkflowDecision:
    """Automated decision result for font processing strategy."""
    workflow: Literal["web_optimize", "qa_report"]
    reason: str
    confidence: float
    detected_font_type: str
    detected_capabilities: list[str]
    recommended_actions: list[dict[str, str]]


@dataclass(frozen=True, slots=True)
class AutonomousWorkflowResult:
    """Complete autonomous workflow result with all generated artifacts."""
    decision: AutonomousWorkflowDecision
    web_package: Optional[WebFontOptimizerPackage]
    qa_package: Optional[FontQaPackage]
    instance_package: Optional[Any]
    summary: dict[str, Any]
    metrics: dict[str, Any]


def analyze_font_for_autonomous_workflow(font: Font) -> AutonomousWorkflowDecision:
    """
    Analyze a font and determine the optimal autonomous workflow.

    Decision criteria:
    - Variable fonts with meaningful variation: "web_optimize" + "instance_package"
    - Fonts needing QA verification: "qa_report" (always included)
    - Fonts with named instances or axis presets: "instance_package"
    - Static fonts: "web_optimize" only
    """
    detected_capabilities: list[str] = []
    recommended_actions: list[dict[str, str]] = []

    font_type = "variable" if isinstance(font, TtfFont) and font.is_variable else "static"

    if font_type == "variable" and isinstance(font, TtfFont):
        axes = font.variable_axes
        named_instances = font.named_instances

        if len(axes) > 0:
            detected_capabilities.append("variable_axes")
            recommended_actions.append({
                "action": "variable_instancing",
                "rationale": f"Font has {len(axes)} variable axis(es)"
            })

        if len(named_instances) > 0:
            detected_capabilities.append("named_instances")
            recommended_actions.append({
                "action": "named_instance_package",
                "rationale": f"Font has {len(named_instances)} named instance(s)"
            })

        if hasattr(font, 'get_stat_table') and font.get_stat_table() is not None:
            detected_capabilities.append("stat_table")
            recommended_actions.append({
                "action": "stat_preservation",
                "rationale": "Font has STAT table for metadata preservation"
            })

        if len(axes) >= 2:
            detected_capabilities.append("multi_axis_variation")
            recommended_actions.append({
                "action": "axis_grid_web_bundles",
                "rationale": "Multi-axis font supports complex web bundles"
            })

        if len(axes) > 0 and len(named_instances) > 0:
            workflow = "web_optimize"
            confidence = 0.95
            reason = "Variable font with named instances: web optimization is the primary workflow"
            recommended_actions = [
                a for a in recommended_actions if a.get("action") != "named_instance_package"
            ]
        elif len(axes) > 0:
            workflow = "web_optimize"
            confidence = 0.90
            reason = "Variable font with axes: web optimization is the primary workflow"
            recommended_actions = [
                a for a in recommended_actions if a.get("action") != "named_instance_package"
            ]
        else:
            workflow = "web_optimize"
            confidence = 0.75
            reason = "Variable font without named instances: web optimization suffices"
    else:
        workflow = "web_optimize"
        confidence = 0.85
        reason = "Static font: web optimization is the primary workflow"

    detected_capabilities.append("qa_verification")
    recommended_actions.append({
        "action": "quality_assurance",
        "rationale": "Standard QA verification recommended for all fonts"
    })

    return AutonomousWorkflowDecision(
        workflow=workflow,
        reason=reason,
        confidence=confidence,
        detected_font_type=font_type,
        detected_capabilities=detected_capabilities,
        recommended_actions=recommended_actions
    )


def run_autonomous_workflow(
    font: Font,
    input_path: Optional[str] = None,
    output_dir: str | Path = ".",
    include_qa: bool = True,
    include_instances: bool = True,
    preset: Optional[list[str]] = None,
    naming_strategy: Optional[str] = None,
    custom_family_suffix: Optional[str] = None,
    legacy_family: Optional[str] = None,
    legacy_style: Optional[str] = None,
    typographic_family: Optional[str] = None,
    typographic_style: Optional[str] = None,
    stat_policy: Optional[str] = None,
    font_display: Literal["auto", "block", "swap", "fallback", "optional"] = "swap",
    include_woff: bool = False,
    cdn_manifest: bool = False,
    cdn_base: str = "https://cdn.example.com",
) -> AutonomousWorkflowResult:
    """
    One-call autonomous font processing workflow.

    Automatically determines optimal processing strategy and executes:
    - Web optimization (WOFF2/WOFF with CSS/specimen)
    - Quality assurance (severity scoring, compatibility checks)
    - Instance packaging (static instances with STAT preservation)

    All workflows run in sequence with shared metadata and unified output.
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    start_time = time.time()
    metrics: dict[str, Any] = {}

    decision = analyze_font_for_autonomous_workflow(font)

    web_package: Optional[WebFontOptimizerPackage] = None
    qa_package: Optional[FontQaPackage] = None
    instance_package: Optional[Any] = None

    if decision.workflow in ("web_optimize", "combined"):
        web_start = time.time()
        web_package = WebFontOptimizer.build(
            font,
            source_path=input_path,
            presets=preset or [],
            include_woff=include_woff,
            variable_mode="auto",
            naming_strategy=naming_strategy if naming_strategy else "instance-family",
            family_suffix=custom_family_suffix,
            stat_policy=stat_policy if stat_policy else "drop",
            legacy_family_name=legacy_family,
            legacy_style_name=legacy_style,
            typographic_family_name=typographic_family,
            typographic_style_name=typographic_style,
            font_display=font_display,
            cdn_base_url=cdn_base if cdn_manifest else None,
        )
        web_end = time.time()
        metrics["web_optimization_time_ms"] = int((web_end - web_start) * 1000)

    if include_qa:
        qa_start = time.time()
        qa_package = FontQaReporter.build_package(
            font,
            output_dir=output_path,
            source_label=input_path or "",
            presets=preset or [],
            include_compatibility=False,
            include_extras=False,
            include_decision=True,
        )
        qa_end = time.time()
        metrics["qa_report_time_ms"] = int((qa_end - qa_start) * 1000)

    if include_instances and decision.detected_font_type == "variable" and isinstance(font, TtfFont):
        instance_start = time.time()
        try:
            from aspose_font.instances import VariableInstanceBuilder

            builder = VariableInstanceBuilder(font)
            instance_package = builder.build_package(
                naming_strategy=naming_strategy if naming_strategy else "instance-family",
                family_suffix=custom_family_suffix,
                legacy_family_name=legacy_family,
                legacy_style_name=legacy_style,
                typographic_family_name=typographic_family,
                typographic_style_name=typographic_style,
                stat_policy=stat_policy if stat_policy else "drop",
                preview_text="Hamburgefons 0123456789",
            )
            instance_end = time.time()
            metrics["instance_package_time_ms"] = int((instance_end - instance_start) * 1000)
        except Exception:
            metrics["instance_package_time_ms"] = 0

    end_time = time.time()
    metrics["total_time_ms"] = int((end_time - start_time) * 1000)

    summary: dict[str, Any] = {
        "kind": "autonomous_workflow_result",
        "decision": {
            "workflow": decision.workflow,
            "reason": decision.reason,
            "confidence": decision.confidence,
            "detected_font_type": decision.detected_font_type,
            "detected_capabilities": decision.detected_capabilities,
            "recommended_actions": decision.recommended_actions,
        },
        "generated_artifacts": [],
        "output_directory": str(output_path.resolve()),
    }

    if web_package:
        bundle = web_package.bundle
        summary["generated_artifacts"].append({
            "kind": "web_bundle",
            "family": bundle.family,
            "style": bundle.style,
            "css_filename": bundle.css_filename,
            "html_filename": bundle.html_filename,
            "font_assets": [
                {
                    "filename": asset.filename,
                    "media_type": asset.media_type,
                    "bytes": len(asset.data),
                }
                for asset in bundle.font_assets
            ],
            "manifest": bundle.manifest,
        })

    if qa_package:
        summary["generated_artifacts"].append({
            "kind": "qa_package",
            "report_path": str(qa_package.json_path),
            "html_path": str(qa_package.html_path),
            "package_directory": str(qa_package.directory),
        })

    if instance_package:
        summary["generated_artifacts"].append({
            "kind": "instance_package",
            "instances_count": len(instance_package.instances),
            "fonts_count": len(instance_package.fonts),
            "preview_path": str(instance_package.output_directory / "preview.png"),
            "stat_evidence_path": str(instance_package.output_directory / "stat-evidence.json"),
            "manifest_path": str(instance_package.output_directory / "manifest.json"),
        })

    summary["metrics"] = metrics

    return AutonomousWorkflowResult(
        decision=decision,
        web_package=web_package,
        qa_package=qa_package,
        instance_package=instance_package,
        summary=summary,
        metrics=metrics,
    )


def run_autonomous_workflow_from_path(
    font_path: str,
    output_dir: str | Path = ".",
    font_type: Optional[str] = None,
    collection_index: int | None = None,
    **kwargs: Any,
) -> AutonomousWorkflowResult:
    """
    Convenience wrapper that loads font from path and runs autonomous workflow.
    """
    from aspose_font import FontLoader

    font = FontLoader.open(font_path, collection_index=collection_index)
    return run_autonomous_workflow(
        font,
        input_path=font_path,
        output_dir=output_dir,
        **kwargs,
    )
