"""Tests for FONT-262 Web Font Optimizer readiness and performance evidence."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from aspose_font import WebFontOptimizer
from aspose_font.ttf.font import TtfFont


def test_size_comparison_key_exists(roboto: TtfFont):
    """Verify that size_comparison key exists in the optimizer manifest."""
    package = WebFontOptimizer.build(
        roboto,
        source_path=Path("testdata/Roboto-VariableFont_wdth,wght.ttf"),
        presets=("latin",),
        include_woff=False,
    )

    assert "size_comparison" in package.manifest
    assert isinstance(package.manifest["size_comparison"], dict)


def test_size_comparison_required_fields(roboto: TtfFont):
    """Verify that size_comparison contains all required fields."""
    package = WebFontOptimizer.build(
        roboto,
        source_path=Path("testdata/Roboto-VariableFont_wdth,wght.ttf"),
        presets=("latin",),
        include_woff=False,
    )

    size_comparison = package.manifest["size_comparison"]
    assert "source_bytes" in size_comparison
    assert "output_bytes" in size_comparison
    assert "compression_ratio" in size_comparison
    assert "elapsed_ms" in size_comparison


def test_size_comparison_numerical_plausibility(roboto: TtfFont):
    """Verify that output_bytes <= source_bytes for numerical plausibility."""
    package = WebFontOptimizer.build(
        roboto,
        source_path=Path("testdata/Roboto-VariableFont_wdth,wght.ttf"),
        presets=("latin",),
        include_woff=False,
    )

    size_comparison = package.manifest["size_comparison"]
    source_bytes = size_comparison.get("source_bytes")
    output_bytes = size_comparison.get("output_bytes")

    if source_bytes is not None and output_bytes is not None:
        assert output_bytes <= source_bytes


def test_performance_elapsed_ms_present(roboto: TtfFont):
    """Verify that performance.elapsed_ms exists in the optimizer manifest."""
    package = WebFontOptimizer.build(
        roboto,
        source_path=Path("testdata/Roboto-VariableFont_wdth,wght.ttf"),
        presets=("latin",),
        include_woff=False,
    )

    assert "performance" in package.manifest
    assert isinstance(package.manifest["performance"], dict)
    assert "elapsed_ms" in package.manifest["performance"]
    assert isinstance(package.manifest["performance"]["elapsed_ms"], int)


def test_performance_detailed_timing_with_flag(roboto: TtfFont):
    """Verify that detailed timing breakdown is included when flag is set."""
    package = WebFontOptimizer.build(
        roboto,
        source_path=Path("testdata/Roboto-VariableFont_wdth,wght.ttf"),
        presets=("latin",),
        include_woff=False,
        detailed_reporting=True,
    )

    performance = package.manifest["performance"]
    assert "elapsed_ms" in performance
    assert isinstance(performance["elapsed_ms"], int)
    assert performance["elapsed_ms"] > 0

    assert "load_time_ms" in performance
    assert "subset_time_ms" in performance
    assert "compress_time_ms" in performance
    assert "manifest_write_time_ms" in performance

    for key in ["load_time_ms", "subset_time_ms", "compress_time_ms", "manifest_write_time_ms"]:
        assert isinstance(performance[key], int)
        assert performance[key] >= 0

    detailed_sum = sum(
        performance[key]
        for key in ["load_time_ms", "subset_time_ms", "compress_time_ms", "manifest_write_time_ms"]
    )
    assert detailed_sum <= performance["elapsed_ms"]


def test_cli_summary_prints_new_fields(roboto: TtfFont, tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    """Verify that CLI prints readiness, size reduction %, and elapsed time via web-optimize."""
    import subprocess
    import sys

    repo_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [
            sys.executable, "-m", "aspose_font.cli", "web-optimize",
            str(repo_root / "testdata" / "Roboto-VariableFont_wdth,wght.ttf"),
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
        cwd=str(repo_root),
    )

    assert result.returncode == 0
    output = result.stdout

    assert "Total time:" in output
    assert "Optimizer status:" in output
    assert "Optimizer score:" in output
    assert "Size reduction:" in output

    manifest_path = tmp_path / "optimizer-manifest.json"
    assert manifest_path.exists()

    manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert "size_comparison" in manifest_data
    assert "performance" in manifest_data
    assert "readiness" in manifest_data


def test_size_comparison_written_to_file(roboto: TtfFont, tmp_path: Path):
    """Verify that size_comparison is properly written to optimizer-manifest.json."""
    package = WebFontOptimizer.build(
        roboto,
        source_path=Path("testdata/Roboto-VariableFont_wdth,wght.ttf"),
        presets=("latin",),
        include_woff=False,
    )

    package.write_to(tmp_path)
    manifest_path = tmp_path / "optimizer-manifest.json"

    assert manifest_path.exists()
    manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert "size_comparison" in manifest_data
    size_comparison = manifest_data["size_comparison"]
    assert size_comparison["source_bytes"] == package.manifest["size_comparison"]["source_bytes"]
    assert size_comparison["output_bytes"] == package.manifest["size_comparison"]["output_bytes"]
    assert size_comparison["elapsed_ms"] == package.manifest["size_comparison"]["elapsed_ms"]


def test_size_comparison_values_with_source(roboto: TtfFont):
    """Verify that size_comparison values are correctly populated when source file exists."""
    package = WebFontOptimizer.build(
        roboto,
        source_path=Path("testdata/Roboto-VariableFont_wdth,wght.ttf"),
        presets=("latin",),
        include_woff=False,
    )

    size_comparison = package.manifest["size_comparison"]
    size_summary = package.manifest["size_summary"]

    assert size_comparison["source_bytes"] == size_summary.get("source_bytes")
    assert size_comparison["output_bytes"] == size_summary.get("total_web_font_bytes")
    assert size_comparison["compression_ratio"] == size_summary.get("compression_ratio")
