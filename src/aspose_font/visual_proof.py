"""Unified visual proofing package generator.

This module coordinates animation sweep, designspace coverage, and capability
discovery into a single developer-friendly output package.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from aspose_font import (
    AnimationPreviewBuilder,
    FontCapabilityBuilder,
    FontLoader,
)
from aspose_font.animation import AnimationAsset
from aspose_font.preview import generate_designspace_diff_overlay
from aspose_font.rasterizer import Rasterizer
from aspose_font.text import TextRenderer
from aspose_font.ttf.font import TtfFont
from aspose_font.variation import compute_designspace_coverage


class VisualProofBuilder:
    """Build visual proof packages for fonts or designspace directories."""

    def build_from_font(self, font_path: Path, output_dir: Path) -> None:
        """Build visual proof package from a single font file.

        Args:
            font_path: Path to font file
            output_dir: Output directory for artifacts
        """
        font = FontLoader.open(font_path)

        if not isinstance(font, TtfFont) or not font.is_variable:
            raise ValueError("Font is not a variable font")

        self._build_package(font, output_dir)

    def build_from_designspace(self, designspace_dir: Path, output_dir: Path) -> None:
        """Build visual proof package from a designspace directory.

        Args:
            designspace_dir: Path to directory containing designspace files
            output_dir: Output directory for artifacts
        """
        designspace_files = list(designspace_dir.glob("*.designspace"))
        if not designspace_files:
            raise ValueError(f"No .designspace file found in {designspace_dir}")

        if len(designspace_files) > 1:
            raise ValueError(f"Multiple .designspace files found in {designspace_dir}")

        designspace_path = designspace_files[0]

        loader = FontLoader.open(designspace_path)
        font = loader.font if hasattr(loader, "font") else loader

        if not isinstance(font, TtfFont) or not font.is_variable:
            raise ValueError("Designspace font is not a variable font")

        self._build_package(font, output_dir)

    def _build_package(self, font: TtfFont, output_dir: Path) -> None:
        """Build complete visual proof package for a font."""
        output_dir.mkdir(parents=True, exist_ok=True)

        self._write_html_index(output_dir)
        self._generate_animation(font, output_dir)
        self._generate_coverage_json(font, output_dir)
        self._generate_coverage_png(font, output_dir)
        self._generate_diff_overlay(font, output_dir)
        self._generate_capability_json(font, output_dir)
        self._write_manifest(output_dir)

    def _write_html_index(self, output_dir: Path) -> None:
        """Write HTML index file."""
        index_path = output_dir / "index.html"
        html_content = """
<html>
<head>
    <title>Visual Proof Package</title>
    <meta charset="utf-8">
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 2rem; background: #f8f9fa; }
        h1 { color: #1a1a2e; }
        .artifact { display: block; margin: 0.5rem 0; padding: 1rem; background: white; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); text-decoration: none; color: #333; }
        .artifact:hover { box-shadow: 0 4px 8px rgba(0,0,0,0.15); }
        .artifact span { font-weight: 500; color: #1a1a2e; }
        .artifact small { color: #666; display: block; margin-top: 0.25rem; }
    </style>
</head>
<body>
    <h1>Visual Proof Artifacts</h1>
    <a class='artifact' href='animation.apng'><span>Animation (APNG)</span><small>Variable font animation sweep</small></a>
    <a class='artifact' href='coverage.png'><span>Coverage Diagram</span><small>Designspace coverage diagnostics</small></a>
    <a class='artifact' href='diff_overlay.png'><span>Visual Diff Overlay (PNG)</span><small>Variable font instance comparison</small></a>
    <a class='artifact' href='capability.json'><span>Capability Report (JSON)</span><small>Font capability discovery</small></a>
</body>
</html>
"""
        index_path.write_text(html_content, encoding="utf-8")

    def _generate_animation(self, font: TtfFont, output_dir: Path) -> None:
        """Generate animation sweep APNG."""
        animation = self._build_animation(font)
        animation.write_to(output_dir / "animation.apng")

    def _generate_coverage_json(self, font: TtfFont, output_dir: Path) -> None:
        """Generate coverage report JSON."""
        grid = self._resolve_grid(font)
        coverage_data = compute_designspace_coverage(font, grid)
        coverage_path = output_dir / "coverage.json"
        coverage_path.write_text(json.dumps(coverage_data, indent=2), encoding="utf-8")

    def _generate_coverage_png(self, font: TtfFont, output_dir: Path) -> None:
        """Generate coverage diagram PNG."""
        coverage_data = compute_designspace_coverage(font, self._resolve_grid(font))
        per_axis = coverage_data.get("per_axis_coverage", {})
        total_points = coverage_data.get("total_points", 0)
        covered_points = coverage_data.get("covered_points", 0)

        lines = [
            "Designspace Coverage",
            "====================",
            f"Total points: {total_points}",
            f"Covered: {covered_points}",
            "",
        ]
        for axis_tag, percent in sorted(per_axis.items()):
            lines.append(f"{axis_tag}: {percent:.1f}% covered")

        overlay_text = "\n".join(lines)

        width = 500
        height = 200
        background = (255, 253, 248)
        color = (17, 17, 17)

        canvas = Rasterizer(width, height, background)
        canvas.clear()

        canvas_data = TextRenderer.render_png(
            font,
            overlay_text,
            size=14.0,
            color=color,
            background=background,
            padding=12,
            antialias=True,
        )
        (output_dir / "coverage.png").write_bytes(canvas_data)

    def _generate_diff_overlay(self, font: TtfFont, output_dir: Path) -> None:
        """Generate visual diff overlay PNG."""
        axes = font.variable_axes
        if not axes:
            raise ValueError("Font has no variable axes")

        if len(axes) >= 2:
            axis1_tag = axes[0].tag
            axis2_tag = axes[1].tag
            overlay_bytes = generate_designspace_diff_overlay(font, axis1_tag, axis2_tag)
        else:
            axis1_tag = axes[0].tag
            overlay_bytes = generate_designspace_diff_overlay(font, axis1_tag, axis1_tag)

        (output_dir / "diff_overlay.png").write_bytes(overlay_bytes)

    def _generate_capability_json(self, font: TtfFont, output_dir: Path) -> None:
        """Generate capability report JSON."""
        report = FontCapabilityBuilder.build(font)
        capability_path = output_dir / "capability.json"
        capability_path.write_text(report.to_json(), encoding="utf-8")

    def _write_manifest(self, output_dir: Path) -> None:
        """Write manifest.json with file listing and timestamps."""
        manifest = {
            "package_type": "visual_proof",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "files": [],
        }

        for file_path in sorted(output_dir.iterdir()):
            if file_path.is_file():
                created_dt = datetime.fromtimestamp(file_path.stat().st_ctime, tz=timezone.utc)
                modified_dt = datetime.fromtimestamp(file_path.stat().st_mtime, tz=timezone.utc)
                manifest["files"].append({
                    "name": file_path.name,
                    "size_bytes": file_path.stat().st_size,
                    "created_at": created_dt.isoformat(),
                    "updated_at": modified_dt.isoformat(),
                })

        (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    def _build_animation(self, font: TtfFont) -> AnimationAsset:
        """Build animation sweep using first available axis."""
        axes = font.variable_axes
        if not axes:
            raise ValueError("Font has no variable axes")

        first_axis = axes[0]

        return AnimationPreviewBuilder.build_axis_sweep(
            font,
            axis_tag=first_axis.tag,
            start_val=first_axis.min_value,
            end_val=first_axis.max_value,
            text="Hamburgefons 0123456789",
            frames=12,
            fps=10,
            bounce=False,
            preset="standard",
            file_stem="animation",
        )

    def _resolve_grid(self, font: TtfFont) -> list[dict[str, float]]:
        """Resolve a reasonable grid for coverage computation."""
        axes = font.variable_axes
        if not axes:
            return []

        grid: list[dict[str, float]] = []

        for instance in font.variable_instances:
            grid.append(instance.coordinates)

        if not grid:
            for axis in axes:
                grid.append({axis.tag: axis.default_value for axis in axes})

        return grid


def run_visual_proof(font_path: Path, output_dir: Path) -> None:
    """Run visual proofing pipeline for a font.

    Args:
        font_path: Path to font file
        output_dir: Output directory for artifacts

    Raises:
        ValueError: If font is not a variable font
    """
    builder = VisualProofBuilder()
    builder.build_from_font(font_path, output_dir)


__all__ = [
    "VisualProofBuilder",
    "run_visual_proof",
]
