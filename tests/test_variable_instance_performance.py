"""CI performance regression test for Variable Instance Package generation."""

from __future__ import annotations

import json
import time
from pathlib import Path

from aspose_font import FontLoader, VariableInstanceBuilder

FIXTURE_ROOT = Path(__file__).resolve().parent.parent / "testdata"


def test_variable_instance_package_build_performance(tmp_path: Path) -> None:
    """Verify VariableInstanceBuilder.build_package completes within performance threshold.

    This test enforces a performance regression gate for Variable Instance Package
    generation on CI runners. If this test fails, it indicates a performance regression
    in the variable font instancing or package generation workflow.

    Threshold: 100ms (CI regression gate; per src/aspose_font/ci/perf_var_package.py:80)
    Baseline: ~5000ms (from backlog/runtime/performance_var_package_baselines.json)
    """
    font_path = FIXTURE_ROOT / "Roboto-VariableFont_wdth,wght.ttf"
    if not font_path.exists():
        font_path = FIXTURE_ROOT.parent / "Roboto-VariableFont_wdth,wght.ttf"
    if not font_path.exists():
        raise FileNotFoundError(f"Variable font not found at {font_path}")

    font = FontLoader.open(font_path)
    assert font.is_variable, "Test fixture must be a variable font"

    builder = VariableInstanceBuilder(font)

    start_time = time.perf_counter()
    package = builder.build_package(ci_fast_mode=True)
    elapsed_ms = (time.perf_counter() - start_time) * 1000

    assert package is not None

    threshold_ms = 100.0

    assert elapsed_ms <= threshold_ms, (
        f"Variable Instance Package build took {elapsed_ms:.2f}ms, "
        f"exceeds CI regression threshold of {threshold_ms}ms. "
        f"This indicates a performance regression in the VariableInstanceBuilder workflow."
    )

    output_dir = tmp_path / "var_package_output"
    output_dir.mkdir(parents=True, exist_ok=True)

    written_files = package.write_to(output_dir)

    assert len(written_files) >= 4, "Package should write at least 4 files (fonts, stat-evidence.json, manifest.json, preview.png)"

    stat_evidence_path = output_dir / "stat-evidence.json"
    assert stat_evidence_path.exists(), "stat-evidence.json must be written"

    manifest_path = output_dir / "manifest.json"
    assert manifest_path.exists(), "manifest.json must be written"

    manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert "instances" in manifest_data
    assert "statistics" in manifest_data or "artifacts" in manifest_data

