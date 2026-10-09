"""Tests for FONT-345: README example for Web Font Optimizer."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_web_optimizer_cli_generates_readme_example_artifacts(roboto_path: Path, tmp_path: Path) -> None:
    """Verify CLI generates full Web Font Optimizer output with README example."""
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    result = subprocess.run(
        [
            sys.executable, "-m", "aspose_font.cli", "web-optimize",
            str(roboto_path), str(output_dir),
            "--readme-example",
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0

    woff2_files = list(output_dir.glob("*.woff2"))
    assert len(woff2_files) > 0, "At least one .woff2 file should be generated"

    css_files = list(output_dir.glob("*.css"))
    assert len(css_files) > 0, "At least one .css file should be generated"

    html_files = list(output_dir.glob("*.html"))
    assert len(html_files) > 0, "At least one .html file should be generated"

    assert (output_dir / "optimizer-manifest.json").exists(), "optimizer-manifest.json should be generated"


def test_web_optimizer_cli_manifest_contains_readiness_score(roboto_path: Path, tmp_path: Path) -> None:
    """Verify optimizer-manifest.json contains size_summary and readiness with score."""
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    subprocess.run(
        [
            sys.executable, "-m", "aspose_font.cli", "web-optimize",
            str(roboto_path), str(output_dir),
            "--readme-example",
        ],
        capture_output=True,
        text=True,
    )

    manifest_path = output_dir / "optimizer-manifest.json"
    manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert "size_summary" in manifest_data
    size_summary = manifest_data["size_summary"]
    assert isinstance(size_summary, dict)
    assert len(size_summary) > 0, "size_summary should be non-empty"

    assert "readiness" in manifest_data
    readiness = manifest_data["readiness"]
    assert isinstance(readiness, dict)
    assert "score" in readiness, "readiness should contain score field"
    assert isinstance(readiness["score"], (int, float))


def test_web_optimizer_cli_css_contains_font_face_woff2(roboto_path: Path, tmp_path: Path) -> None:
    """Verify generated CSS contains @font-face rule referencing .woff2 file."""
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    subprocess.run(
        [
            sys.executable, "-m", "aspose_font.cli", "web-optimize",
            str(roboto_path), str(output_dir),
            "--readme-example",
        ],
        capture_output=True,
        text=True,
    )

    css_files = list(output_dir.glob("*.css"))
    assert len(css_files) > 0, "At least one .css file should be generated"

    css_content = css_files[0].read_text(encoding="utf-8")

    assert "@font-face {" in css_content, "CSS should contain @font-face rule"
    assert "format('woff2')" in css_content, "CSS should reference woff2 format"
    assert ".woff2" in css_content, "CSS should reference .woff2 file"


def test_web_optimizer_cli_specimen_has_variable_sliders_script(roboto_path: Path, tmp_path: Path) -> None:
    """Verify specimen.html includes <script> element for variable-axis sliders."""
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    subprocess.run(
        [
            sys.executable, "-m", "aspose_font.cli", "web-optimize",
            str(roboto_path), str(output_dir),
            "--readme-example",
        ],
        capture_output=True,
        text=True,
    )

    html_files = list(output_dir.glob("*.html"))
    assert len(html_files) > 0, "At least one .html file should be generated"

    specimen_content = html_files[0].read_text(encoding="utf-8")

    assert "<script" in specimen_content, "Specimen HTML should include <script> element"
    assert "axis" in specimen_content.lower() or "variable" in specimen_content.lower(), \
        "Specimen HTML should include variable/axis controls"


def test_web_optimizer_cli_readme_example_performance(roboto_path: Path, tmp_path: Path) -> None:
    """Verify CLI README example generation completes within CI performance threshold (≤2500ms).

    Threshold rationale:
    - Measured local performance: ~830ms average
    - CI environment is significantly slower due to different hardware and resource contention
    - Threshold accounts for ~3x CI variability with buffer for other operations
    - Consistent with animation export test (1500ms for ~1100ms workflow)
    """
    import time

    output_dir = tmp_path / "output"
    output_dir.mkdir()

    start_time = time.perf_counter()
    subprocess.run(
        [
            sys.executable, "-m", "aspose_font.cli", "web-optimize",
            str(roboto_path), str(output_dir),
            "--readme-example",
        ],
        capture_output=True,
        text=True,
    )
    elapsed_ms = (time.perf_counter() - start_time) * 1000

    assert elapsed_ms <= 2500, (
        f"CLI README example generation took {elapsed_ms:.2f}ms, exceeds 2500ms CI threshold"
    )
