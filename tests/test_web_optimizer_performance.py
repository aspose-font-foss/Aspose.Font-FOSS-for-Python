"""Tests for FONT-210 Web Font Optimizer performance evidence."""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from aspose_font import WebFontOptimizer
from aspose_font.ttf.font import TtfFont


def test_web_optimizer_performance_elapsed_ms_present(roboto: TtfFont):
    """Verify that performance.elapsed_ms is present in the optimizer manifest."""
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


def test_web_optimizer_performance_elapsed_ms_positive(roboto: TtfFont):
    """Verify that performance.elapsed_ms is a positive integer."""
    start = time.perf_counter()
    package = WebFontOptimizer.build(
        roboto,
        source_path=Path("testdata/Roboto-VariableFont_wdth,wght.ttf"),
        presets=("latin",),
        include_woff=False,
    )
    elapsed_ms = package.manifest["performance"]["elapsed_ms"]
    total_elapsed_ms = (time.perf_counter() - start) * 1000

    assert elapsed_ms > 0
    assert elapsed_ms <= round(total_elapsed_ms) + 100


def test_web_optimizer_performance_readiness_includes_note(roboto: TtfFont):
    """Verify that readiness.performance_note is present and contains timing info."""
    package = WebFontOptimizer.build(
        roboto,
        source_path=Path("testdata/Roboto-VariableFont_wdth,wght.ttf"),
        presets=("latin",),
        include_woff=False,
    )

    assert "performance_note" in package.readiness
    assert isinstance(package.readiness["performance_note"], str)
    assert "ms" in package.readiness["performance_note"].lower()


def test_web_optimizer_performance_write_to_includes_manifest(roboto: TtfFont, tmp_path: Path):
    """Verify that the performance section is properly written to optimizer-manifest.json."""
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

    assert "performance" in manifest_data
    assert manifest_data["performance"]["elapsed_ms"] == package.manifest["performance"]["elapsed_ms"]
    assert manifest_data["readiness"]["performance_note"] == package.readiness["performance_note"]


def test_web_optimizer_performance_cli_example_output(capsys: pytest.CaptureFixture[str]):
    """Verify that --example-output produces valid JSON with performance fields."""
    from aspose_font.cli import _print_web_optimizer_example_output

    _print_web_optimizer_example_output()

    captured = capsys.readouterr()
    output = captured.out.strip()

    example_manifest = json.loads(output)

    assert "performance" in example_manifest
    assert "elapsed_ms" in example_manifest["performance"]
    assert isinstance(example_manifest["performance"]["elapsed_ms"], int)
    assert example_manifest["performance"]["elapsed_ms"] > 0

    assert "readiness" in example_manifest
    assert "performance_note" in example_manifest["readiness"]
    assert isinstance(example_manifest["readiness"]["performance_note"], str)
    assert "ms" in example_manifest["readiness"]["performance_note"].lower()


def test_web_optimizer_performance_detailed_timing_with_flag(roboto: TtfFont):
    """Verify that --performance-report flag produces detailed timing breakdown."""
    package = WebFontOptimizer.build(
        roboto,
        source_path=Path("testdata/Roboto-VariableFont_wdth,wght.ttf"),
        presets=("latin",),
        include_woff=False,
        detailed_reporting=True,
    )

    assert "performance" in package.manifest
    assert isinstance(package.manifest["performance"], dict)
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


def test_web_optimizer_performance_cli_flag(capsys: pytest.CaptureFixture[str], tmp_path: Path):
    """Verify that --performance-report flag works via CLI."""
    import subprocess
    import sys

    repo_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [
            sys.executable, "-m", "aspose_font.cli", "web-optimize",
            str(repo_root / "testdata" / "Roboto-VariableFont_wdth,wght.ttf"),
            str(tmp_path),
            "--performance-report",
        ],
        capture_output=True,
        text=True,
        cwd=str(repo_root),
    )

    assert result.returncode == 0

    output = result.stdout
    assert "Total time:" in output
    assert "Load:" in output
    assert "Subset:" in output
    assert "Compress:" in output
    assert "Manifest:" in output

    manifest_path = tmp_path / "optimizer-manifest.json"
    assert manifest_path.exists()

    manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
    performance = manifest_data.get("performance", {})

    assert "load_time_ms" in performance
    assert "subset_time_ms" in performance
    assert "compress_time_ms" in performance
    assert "manifest_write_time_ms" in performance


def test_web_optimizer_package_has_detailed_timing_field(roboto: TtfFont):
    """Verify that WebFontOptimizerPackage.detailed_timing field exists and is correctly populated."""
    package = WebFontOptimizer.build(
        roboto,
        source_path=Path("testdata/Roboto-VariableFont_wdth,wght.ttf"),
        presets=("latin",),
        include_woff=False,
        detailed_reporting=True,
    )

    assert hasattr(package, "detailed_timing")
    assert isinstance(package.detailed_timing, dict)
    assert "load_time_ms" in package.detailed_timing
    assert "subset_time_ms" in package.detailed_timing
    assert "compress_time_ms" in package.detailed_timing
    assert "manifest_write_time_ms" in package.detailed_timing


def test_web_optimizer_performance_metrics(roboto: TtfFont):
    """Verify performance.elapsed_ms is present and positive when decision_report=True.

    This test ensures performance metrics work correctly with the decision_report
    flag enabled, covering the scenario where both performance and decision report
    data are included in the optimizer manifest.
    """
    package = WebFontOptimizer.build(
        roboto,
        source_path=Path("testdata/Roboto-VariableFont_wdth,wght.ttf"),
        presets=("latin",),
        include_woff=False,
        decision_report=True,
    )

    assert "performance" in package.manifest
    assert isinstance(package.manifest["performance"], dict)

    assert "elapsed_ms" in package.manifest["performance"]
    elapsed_ms = package.manifest["performance"]["elapsed_ms"]
    assert isinstance(elapsed_ms, int)
    assert elapsed_ms > 0

    assert package.decision_report is not None
    assert "mode" in package.decision_report
    assert "reasons" in package.decision_report
    assert len(package.decision_report["reasons"]) > 0

    assert "performance" in package.manifest
    assert package.manifest["performance"]["elapsed_ms"] == elapsed_ms


def test_web_optimizer_load_time_regression_threshold(roboto: TtfFont):
    """Verify WebFontOptimizer.load_time_ms meets performance regression threshold."""
    package = WebFontOptimizer.build(
        roboto,
        source_path=Path("testdata/Roboto-VariableFont_wdth,wght.ttf"),
        presets=("latin",),
        include_woff=False,
        detailed_reporting=True,
    )

    performance = package.manifest.get("performance", {})
    load_time_ms = performance.get("load_time_ms")

    assert load_time_ms is not None, "load_time_ms should be present when detailed_reporting=True"
    assert isinstance(load_time_ms, int), "load_time_ms should be an integer"
    assert load_time_ms <= 500, f"load_time_ms {load_time_ms}ms exceeds 500ms threshold"


def test_web_optimizer_subset_time_regression_threshold(roboto: TtfFont):
    """Verify WebFontOptimizer.subset_time_ms meets performance regression threshold."""
    package = WebFontOptimizer.build(
        roboto,
        source_path=Path("testdata/Roboto-VariableFont_wdth,wght.ttf"),
        presets=("latin",),
        include_woff=False,
        detailed_reporting=True,
    )

    performance = package.manifest.get("performance", {})
    subset_time_ms = performance.get("subset_time_ms")

    assert subset_time_ms is not None, "subset_time_ms should be present when detailed_reporting=True"
    assert isinstance(subset_time_ms, int), "subset_time_ms should be an integer"
    assert subset_time_ms <= 250, f"subset_time_ms {subset_time_ms}ms exceeds 250ms threshold"


def test_web_optimizer_performance_seconds_keys_present(roboto: TtfFont):
    """Verify that performance dict contains all required second-based keys."""
    package = WebFontOptimizer.build(
        roboto,
        source_path=Path("testdata/Roboto-VariableFont_wdth,wght.ttf"),
        presets=("latin",),
        include_woff=False,
    )

    assert "performance" in package.manifest
    performance = package.manifest["performance"]

    required_keys = [
        "total_seconds",
        "size_summary_seconds",
        "css_generation_seconds",
        "specimen_html_seconds",
    ]
    for key in required_keys:
        assert key in performance, f"Missing key: {key}"
        assert isinstance(performance[key], (int, float)), f"{key} should be numeric"
        assert performance[key] >= 0, f"{key} should be non-negative"


def test_web_optimizer_performance_seconds_values(roboto: TtfFont):
    """Verify that performance seconds values are reasonable and sum correctly."""
    package = WebFontOptimizer.build(
        roboto,
        source_path=Path("testdata/Roboto-VariableFont_wdth,wght.ttf"),
        presets=("latin",),
        include_woff=False,
    )

    performance = package.manifest["performance"]

    total = performance["total_seconds"]
    components = [
        performance["size_summary_seconds"],
        performance["css_generation_seconds"],
        performance["specimen_html_seconds"],
    ]

    assert total >= sum(components) - 0.001, "Total time should exceed component sum"


def test_web_optimizer_performance_cli_include_performance_flag(capsys: pytest.CaptureFixture[str], tmp_path: Path):
    """Verify that --include-performance flag works via CLI and outputs performance section."""
    import subprocess
    import sys

    repo_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [
            sys.executable, "-m", "aspose_font.cli", "web-optimize",
            str(repo_root / "testdata" / "Roboto-VariableFont_wdth,wght.ttf"),
            str(tmp_path),
            "--include-performance",
        ],
        capture_output=True,
        text=True,
        cwd=str(repo_root),
    )

    assert result.returncode == 0

    manifest_path = tmp_path / "optimizer-manifest.json"
    assert manifest_path.exists()

    manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
    performance = manifest_data.get("performance", {})

    required_keys = ["total_seconds", "size_summary_seconds", "css_generation_seconds", "specimen_html_seconds"]
    for key in required_keys:
        assert key in performance, f"Missing {key} in performance manifest"
        assert isinstance(performance[key], (int, float))
        assert performance[key] >= 0

    output = result.stdout
    assert "specimen_html" in output or performance.get("specimen_html_seconds") is not None


def test_web_optimizer_package_performance_available_flag(roboto: TtfFont):
    """Verify that WebFontOptimizerPackage.performance_available is True when performance metrics are present."""
    package = WebFontOptimizer.build(
        roboto,
        source_path=Path("testdata/Roboto-VariableFont_wdth,wght.ttf"),
        presets=("latin",),
        include_woff=False,
    )

    assert package.performance_available is True
    assert "performance_available" in package.manifest
    assert package.manifest["performance_available"] is True


def test_web_optimizer_performance_seconds_vs_ms_consistency(roboto: TtfFont):
    """Verify that seconds-based metrics are consistent with elapsed_ms when detailed_reporting=True."""
    package = WebFontOptimizer.build(
        roboto,
        source_path=Path("testdata/Roboto-VariableFont_wdth,wght.ttf"),
        presets=("latin",),
        include_woff=False,
        detailed_reporting=True,
    )

    performance = package.manifest["performance"]

    elapsed_ms = performance.get("elapsed_ms")
    total_seconds = performance.get("total_seconds")

    if elapsed_ms is not None and total_seconds is not None:
        elapsed_seconds = elapsed_ms / 1000.0
        assert abs(total_seconds - elapsed_seconds) < 0.1, "total_seconds should be approximately elapsed_ms / 1000"


def test_web_optimizer_performance_seconds_in_package_write(roboto: TtfFont, tmp_path: Path):
    """Verify that performance seconds metrics are written to optimizer-manifest.json."""
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

    performance = manifest_data.get("performance", {})
    required_keys = ["total_seconds", "size_summary_seconds", "css_generation_seconds", "specimen_html_seconds"]
    for key in required_keys:
        assert key in performance, f"Missing {key} in written manifest"
        assert isinstance(performance[key], (int, float))
        assert performance[key] >= 0
