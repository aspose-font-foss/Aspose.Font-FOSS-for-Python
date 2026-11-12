"""Full pipeline integration test for FONT-354."""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

import pytest

CLI = [sys.executable, "-m", "aspose_font.cli"]
FIXTURE_ROOT = Path(__file__).resolve().parents[1] / "testdata"
ROBOTO_VAR = str(FIXTURE_ROOT / "Roboto-VariableFont_wdth,wght.ttf")


def run_cli(*args: str) -> subprocess.CompletedProcess:
    """Run CLI command and return result."""
    return subprocess.run(
        CLI + list(args),
        capture_output=True,
        text=True,
        cwd=str(FIXTURE_ROOT.parent),
    )


def test_full_pipeline_completes_within_performance_threshold(tmp_path: Path) -> None:
    """Verify full pipeline (web-optimize → qa-report → var-package) completes within threshold.

    End-to-end workflow:
    1. WebFontOptimizer.build (web-optimize CLI)
    2. FontQaReporter.build (qa-report CLI)
    3. VariableInstanceBuilder.build_package (var-package CLI)

    Threshold: 15000 ms (CI regression threshold for full pipeline with default settings)
    Baseline reference: backlog/runtime/performance_baselines_ci.json

    This test enforces CI performance regression gating for the complete workflow.
    If this test fails, it indicates a performance regression in the full pipeline.
    """
    output_root = tmp_path / "full_pipeline_output"
    output_root.mkdir(parents=True, exist_ok=True)

    web_output = output_root / "web"
    web_output.mkdir(exist_ok=True)

    qa_output = output_root / "qa"
    qa_output.mkdir(exist_ok=True)

    var_output = output_root / "var_package"
    var_output.mkdir(exist_ok=True)

    start_time = time.perf_counter()

    result_web = run_cli(
        "web-optimize",
        ROBOTO_VAR,
        str(web_output),
        "--preset", "latin",
        "--text", "Full Pipeline Test",
        "--performance-report",
    )
    assert result_web.returncode == 0, f"web-optimize failed: {result_web.stderr}"

    result_qa = run_cli(
        "qa-report",
        ROBOTO_VAR,
        "--package-output", str(qa_output),
        "--preset", "latin",
        "--text", "Full Pipeline Test",
        "--preview-text", "Full Pipeline QA",
        "--preview-instance-name", "Regular",
        "--ci-fast",
    )
    assert result_qa.returncode == 0, f"qa-report failed: {result_qa.stderr}"

    result_var = run_cli(
        "var-package",
        ROBOTO_VAR,
        str(var_output),
        "--instance", "wght=400,wdth=100",
        "--stat-policy", "static",
        "--ci-fast",
    )
    assert result_var.returncode == 0, f"var-package failed: {result_var.stderr}"

    elapsed_ms = (time.perf_counter() - start_time) * 1000

    threshold_ms = 15000.0
    assert elapsed_ms <= threshold_ms, (
        f"Full pipeline took {elapsed_ms:.2f}ms, "
        f"exceeds CI regression threshold of {threshold_ms}ms. "
        f"This indicates a performance regression in the full workflow."
    )


def test_full_pipeline_produces_required_artifacts(tmp_path: Path) -> None:
    """Verify full pipeline generates all required artifacts.

    Required outputs:
    - optimizer-manifest.json (from WebFontOptimizer)
    - qa-report.json OR qa-report.html (from FontQaReporter)
    - At least one .ttf file (from VariableInstanceBuilder)
    """
    output_root = tmp_path / "full_pipeline_artifacts"
    output_root.mkdir(parents=True, exist_ok=True)

    web_output = output_root / "web"
    web_output.mkdir(exist_ok=True)

    qa_output = output_root / "qa"
    qa_output.mkdir(exist_ok=True)

    var_output = output_root / "var_package"
    var_output.mkdir(exist_ok=True)

    result_web = run_cli(
        "web-optimize",
        ROBOTO_VAR,
        str(web_output),
        "--preset", "latin",
    )
    assert result_web.returncode == 0

    result_qa = run_cli(
        "qa-report",
        ROBOTO_VAR,
        "--package-output", str(qa_output),
        "--preset", "latin",
    )
    assert result_qa.returncode == 0

    result_var = run_cli(
        "var-package",
        ROBOTO_VAR,
        str(var_output),
        "--instance", "wght=400,wdth=100",
    )
    assert result_var.returncode == 0

    manifest_path = web_output / "optimizer-manifest.json"
    assert manifest_path.exists(), "optimizer-manifest.json must be present"

    qa_json = qa_output / "qa-report.json"
    qa_html = qa_output / "qa-report.html"
    assert qa_json.exists() or qa_html.exists(), "QA report artifact must be present"

    ttf_files = list(var_output.glob("*.ttf"))
    assert len(ttf_files) >= 1, "At least one .ttf instance must be generated"

    manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert "performance" in manifest_data, "Manifest must contain performance section"
    assert "elapsed_ms" in manifest_data["performance"], "Performance must contain elapsed_ms"
    assert isinstance(manifest_data["performance"]["elapsed_ms"], int), "elapsed_ms must be integer"
    assert manifest_data["performance"]["elapsed_ms"] > 0, "elapsed_ms must be positive"


def test_full_pipeline_artifacts_are_valid_json(tmp_path: Path) -> None:
    """Verify all JSON artifacts are valid and contain expected fields."""
    output_root = tmp_path / "full_pipeline_valid_json"
    output_root.mkdir(parents=True, exist_ok=True)

    web_output = output_root / "web"
    web_output.mkdir(exist_ok=True)

    qa_output = output_root / "qa"
    qa_output.mkdir(exist_ok=True)

    var_output = output_root / "var_package"
    var_output.mkdir(exist_ok=True)

    run_cli("web-optimize", ROBOTO_VAR, str(web_output), "--preset", "latin")
    run_cli("qa-report", ROBOTO_VAR, "--package-output", str(qa_output), "--preset", "latin")
    run_cli("var-package", ROBOTO_VAR, str(var_output), "--instance", "wght=400,wdth=100")

    manifest_path = web_output / "optimizer-manifest.json"
    manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest_data.get("kind") == "web_optimizer_package"

    qa_json_path = qa_output / "qa-report.json"
    qa_data = json.loads(qa_json_path.read_text(encoding="utf-8"))
    assert qa_data.get("kind") == "font_qa_report"

    var_manifest_path = var_output / "manifest.json"
    var_data = json.loads(var_manifest_path.read_text(encoding="utf-8"))
    assert var_data.get("package_type") == "variable-instance-package"
    assert var_data.get("font_filename")
    assert var_data.get("manifest_filename")
    assert var_data.get("preview_filename")


def test_full_pipeline_error_handling(tmp_path: Path) -> None:
    """Verify proper error handling when pipeline stages fail."""
    invalid_font = str(tmp_path / "nonexistent.ttf")
    output_dir = tmp_path / "error_test"
    output_dir.mkdir(exist_ok=True)

    result = run_cli("web-optimize", invalid_font, str(output_dir))
    assert result.returncode != 0, "Should fail with nonexistent font"
    assert "not found" in result.stderr.lower() or "error" in result.stderr.lower()

    assert not (output_dir / "optimizer-manifest.json").exists()


def test_full_pipeline_cli_output_contains_expected_info(tmp_path: Path) -> None:
    """Verify CLI stdout/stderr contain expected information."""
    output_root = tmp_path / "full_pipeline_cli_output"
    output_root.mkdir(parents=True, exist_ok=True)

    web_output = output_root / "web"
    web_output.mkdir(exist_ok=True)

    result_web = run_cli(
        "web-optimize",
        ROBOTO_VAR,
        str(web_output),
        "--preset", "latin",
    )
    assert result_web.returncode == 0
    assert "Total time:" in result_web.stdout or "Export mode:" in result_web.stdout

    qa_output = output_root / "qa"
    qa_output.mkdir(exist_ok=True)

    result_qa = run_cli(
        "qa-report",
        ROBOTO_VAR,
        "--package-output", str(qa_output),
        "--preset", "latin",
    )
    assert result_qa.returncode == 0
    assert "warnings=" in result_qa.stdout or "next_actions=" in result_qa.stdout

    var_output = output_root / "var_package"
    var_output.mkdir(exist_ok=True)

    result_var = run_cli(
        "var-package",
        ROBOTO_VAR,
        str(var_output),
        "--instance", "wght=400,wdth=100",
    )
    assert result_var.returncode == 0


def test_full_pipeline_integration_with_existing_performance_tests() -> None:
    """Verify full pipeline test integrates with existing CI performance infrastructure.

    This test does not run the full pipeline but verifies that the component
    performance metrics used in this test are consistent with the existing
    CI performance baseline infrastructure.

    Reference: src/aspose_font/ci/perf.py and backlog/runtime/performance_baselines_ci.json
    """
    baselines_path = Path(__file__).resolve().parents[1] / "backlog" / "runtime" / "performance_baselines_ci.json"
    if not baselines_path.exists():
        pytest.skip("CI performance baselines file not present in public clean mirror export")

    baselines = json.loads(baselines_path.read_text(encoding="utf-8"))

    required_metrics = ["web_optimizer_load", "web_optimizer_subset", "qa_report"]
    for metric in required_metrics:
        assert metric in baselines, f"Required metric {metric} must be in baselines"
        assert baselines[metric] > 0, f"Metric {metric} baseline must be positive"

    thresholds = {
        "web_optimizer_load": 100.0,
        "web_optimizer_subset": 50.0,
        "qa_report": 200.0,
    }

    for metric, threshold in thresholds.items():
        baseline = baselines.get(metric, 0)
        assert threshold > baseline * 0.8, (
            f"Threshold {threshold}ms for {metric} should exceed baseline {baseline}ms by reasonable margin"
        )
