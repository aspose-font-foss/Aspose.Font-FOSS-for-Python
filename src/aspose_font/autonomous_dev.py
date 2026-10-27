'''Convenient wrapper for the autonomous workflow.

Provides a high‑level helper that loads a font from a path and runs the full
autonomous workflow using :func:`aspose_font.autonomous.run_autonomous_workflow_from_path`.
'''

from __future__ import annotations

from pathlib import Path
from typing import Literal

from aspose_font.autonomous import (
    AutonomousWorkflowResult,
    run_autonomous_workflow_from_path,
)

__all__ = ["run_autonomous_development"]


def run_autonomous_development(
    font_path: str,
    output_dir: str | Path = ".",
    *,
    include_qa: bool = True,
    include_instances: bool = True,
    include_woff: bool = False,
    preset: list[str] | None = None,
    naming_strategy: str | None = None,
    custom_family_suffix: str | None = None,
    legacy_family: str | None = None,
    legacy_style: str | None = None,
    typographic_family: str | None = None,
    typographic_style: str | None = None,
    stat_policy: str | None = None,
    font_display: Literal["auto", "block", "swap", "fallback", "optional"] = "swap",
    cdn_manifest: bool = False,
    cdn_base: str = "https://cdn.example.com",
) -> AutonomousWorkflowResult:
    """Run the autonomous workflow on a font file.

    This is a thin wrapper around :func:`run_autonomous_workflow_from_path` that
    forwards all arguments directly. The default values match the historic CLI
    behaviour.
    """
    return run_autonomous_workflow_from_path(
        font_path,
        output_dir=output_dir,
        include_qa=include_qa,
        include_instances=include_instances,
        include_woff=include_woff,
        preset=preset,
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
