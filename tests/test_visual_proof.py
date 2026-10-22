"""Unit tests for visual_proof CLI command."""
from __future__ import annotations

import json
from pathlib import Path

import pytest


def test_visual_proof_command_creates_expected_files(tmp_path: Path) -> None:
    """Verify visual-proof command creates animation.apng, coverage.json, capability.json, diff_overlay.png, index.html, manifest.json."""
    font_path = Path(__file__).resolve().parents[1] / "testdata" / "Roboto-VariableFont_wdth,wght.ttf"

    if not font_path.exists():
        pytest.skip("Test font fixture not available")

    output_dir = tmp_path / "visual-proof-output"
    output_dir.mkdir()

    from aspose_font.visual_proof import run_visual_proof

    run_visual_proof(font_path, output_dir)

    assert (output_dir / "animation.apng").exists(), "animation.apng not created"
    assert (output_dir / "coverage.json").exists(), "coverage.json not created"
    assert (output_dir / "capability.json").exists(), "capability.json not created"
    assert (output_dir / "diff_overlay.png").exists(), "diff_overlay.png not created"
    assert (output_dir / "index.html").exists(), "index.html not created"
    assert (output_dir / "manifest.json").exists(), "manifest.json not created"

    capability_data = json.loads((output_dir / "capability.json").read_text(encoding="utf-8"))
    assert capability_data.get("kind") == "font_capability_report"
    assert "font_identity" in capability_data
    assert "axes" in capability_data


def test_visual_proof_command_with_cli_entrypoint(tmp_path: Path) -> None:
    """Verify CLI entrypoint works via subprocess."""
    import subprocess
    import sys

    font_path = Path(__file__).resolve().parents[1] / "testdata" / "Roboto-VariableFont_wdth,wght.ttf"

    if not font_path.exists():
        pytest.skip("Test font fixture not available")

    output_dir = tmp_path / "cli-output"

    result = subprocess.run(
        [sys.executable, "-m", "aspose_font.cli", "visual-proof", str(font_path), "-o", str(output_dir)],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, f"CLI failed: {result.stderr}"
    assert (output_dir / "animation.apng").exists()
    assert (output_dir / "coverage.json").exists()
    assert (output_dir / "capability.json").exists()
    assert (output_dir / "diff_overlay.png").exists()
    assert (output_dir / "index.html").exists()
    assert (output_dir / "manifest.json").exists()

    capability_data = json.loads((output_dir / "capability.json").read_text(encoding="utf-8"))
    assert capability_data.get("kind") == "font_capability_report"


def test_visual_proof_command_error_for_static_font(tmp_path: Path) -> None:
    """Verify proper error handling for non-variable fonts."""
    font_path = Path(__file__).resolve().parents[1] / "testdata" / "Arial.pfa"

    if not font_path.exists():
        pytest.skip("Static font fixture not available")

    from aspose_font.visual_proof import run_visual_proof

    output_dir = tmp_path / "error-output"

    with pytest.raises(ValueError, match="not a variable font"):
        run_visual_proof(font_path, output_dir)
