"""Batch workflow orchestrator for multi-font pipelines."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from aspose_font import FontLoader, FontQaReporter, VariableInstanceBuilder, WebFontOptimizer
from aspose_font.ttf.font import TtfFont

_SUPPORTED_EXTENSIONS = (".ttf", ".otf", ".cff", ".woff", ".woff2", ".eot", ".pfa", ".pfb")


@dataclass(slots=True, frozen=True)
class BatchResult:
    """Per-font processing result."""

    source_path: str
    source_filename: str
    success: bool
    error_message: str | None
    web_package_dir: Path | None
    qa_package_dir: Path | None
    instance_package_dir: Path | None


@dataclass(slots=True, frozen=True)
class BatchSummary:
    """Top-level batch processing summary."""

    total_count: int
    success_count: int
    failure_count: int
    results: list[BatchResult]
    output_directory: Path

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "kind": "batch_summary",
            "total_count": self.total_count,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "output_directory": str(self.output_directory),
            "results": [
                {
                    "source_path": result.source_path,
                    "source_filename": result.source_filename,
                    "success": result.success,
                    "error_message": result.error_message,
                    "web_package_dir": str(result.web_package_dir) if result.web_package_dir else None,
                    "qa_package_dir": str(result.qa_package_dir) if result.qa_package_dir else None,
                    "instance_package_dir": str(result.instance_package_dir) if result.instance_package_dir else None,
                }
                for result in self.results
            ],
        }

    def write_json(self, path: str | Path) -> Path:
        """Write summary to JSON file."""
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(self.to_dict(), indent=2, sort_keys=True), encoding="utf-8")
        return output_path


def _is_supported_font_file(path: Path) -> bool:
    """Check if file has a supported font extension."""
    return path.suffix.lower() in _SUPPORTED_EXTENSIONS


def _process_single_font(
    source_path: Path,
    output_base: Path,
    naming_strategy: str,
    stat_policy: str,
    preview_text: str,
) -> BatchResult:
    """Process a single font through the three pipeline deliverables."""
    source_filename = source_path.name

    try:
        font = FontLoader.open(source_path)
    except Exception as exc:
        return BatchResult(
            source_path=str(source_path),
            source_filename=source_filename,
            success=False,
            error_message=f"Failed to load font: {exc}",
            web_package_dir=None,
            qa_package_dir=None,
            instance_package_dir=None,
        )

    font_dir = output_base / source_path.stem
    web_package_dir = font_dir / "optimizer"
    qa_package_dir = font_dir / "qa-report"
    instance_package_dir = font_dir / "instances"

    try:
        web_package = WebFontOptimizer.build(
            font,
            source_path=source_path,
            preview_text=preview_text,
            naming_strategy=naming_strategy,
            stat_policy=stat_policy,
        )
        web_package.write_to(web_package_dir)
    except Exception as exc:
        return BatchResult(
            source_path=str(source_path),
            source_filename=source_filename,
            success=False,
            error_message=f"Web font optimizer failed: {exc}",
            web_package_dir=None,
            qa_package_dir=None,
            instance_package_dir=None,
        )

    try:
        FontQaReporter.build_package(
            font,
            qa_package_dir,
            source_label=source_filename,
            preview_text=preview_text,
        )
    except Exception as exc:
        return BatchResult(
            source_path=str(source_path),
            source_filename=source_filename,
            success=False,
            error_message=f"Font QA report failed: {exc}",
            web_package_dir=web_package_dir,
            qa_package_dir=None,
            instance_package_dir=None,
        )

    instance_package_dir_created = None
    if isinstance(font, TtfFont) and font.is_variable:
        try:
            instance_package = VariableInstanceBuilder(font).build_package(
                naming_strategy=naming_strategy,
                stat_policy=stat_policy,
                preview_text=preview_text,
            )
            instance_package.write_to(
                instance_package_dir,
                font_filename="instance.ttf",
                stat_evidence_filename="stat-evidence.json",
                preview_filename="comparison-board.png",
                manifest_filename="review-manifest.json",
            )
            instance_package_dir_created = instance_package_dir
        except Exception as exc:
            return BatchResult(
                source_path=str(source_path),
                source_filename=source_filename,
                success=False,
                error_message=f"Variable instance package failed: {exc}",
                web_package_dir=web_package_dir,
                qa_package_dir=qa_package_dir,
                instance_package_dir=None,
            )

    return BatchResult(
        source_path=str(source_path),
        source_filename=source_filename,
        success=True,
        error_message=None,
        web_package_dir=web_package_dir,
        qa_package_dir=qa_package_dir,
        instance_package_dir=instance_package_dir_created,
    )


def process_directory(
    input_directory: str | Path,
    output_directory: str | Path,
    *,
    naming_strategy: str = "instance-family",
    stat_policy: str = "drop",
    preview_text: str = "Hamburgefons 0123456789",
) -> BatchSummary:
    """Process all font files in a directory.

    Args:
        input_directory: Directory containing source font files
        output_directory: Base directory for output packages
        naming_strategy: Naming policy for static variable-font exports
        stat_policy: STAT metadata policy for generated static instances
        preview_text: Text used in preview PNGs

    Returns:
        BatchSummary with per-font results

    Raises:
        FileNotFoundError: If input directory does not exist
        NotADirectoryError: If input path is not a directory
    """
    input_path = Path(input_directory)
    output_path = Path(output_directory)

    if not input_path.exists():
        raise FileNotFoundError(f"Input directory does not exist: {input_directory}")
    if not input_path.is_dir():
        raise NotADirectoryError(f"Input path is not a directory: {input_directory}")

    output_path.mkdir(parents=True, exist_ok=True)

    font_files = [
        f for f in input_path.iterdir()
        if f.is_file() and _is_supported_font_file(f)
    ]

    results: list[BatchResult] = []
    for font_file in sorted(font_files):
        result = _process_single_font(
            source_path=font_file,
            output_base=output_path,
            naming_strategy=naming_strategy,
            stat_policy=stat_policy,
            preview_text=preview_text,
        )
        results.append(result)

    success_count = sum(1 for r in results if r.success)
    failure_count = len(results) - success_count

    summary = BatchSummary(
        total_count=len(results),
        success_count=success_count,
        failure_count=failure_count,
        results=results,
        output_directory=output_path,
    )

    summary.write_json(output_path / "batch-summary.json")

    return summary


__all__ = ["BatchResult", "BatchSummary", "process_directory"]
