"""Tests for var-partial-web CLI command (FONT-368)."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

CLI = [sys.executable, "-m", "aspose_font.cli"]


def run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        CLI + list(args),
        capture_output=True,
        text=True,
    )


def test_var_partial_web_creates_partial_and_bundle(tmp_path: Path) -> None:
    test_font = str(Path(__file__).resolve().parents[1] / "testdata" / "Roboto-VariableFont_wdth,wght.ttf")
    out_dir = tmp_path / "partial-web"
    result = run(
        "var-partial-web",
        test_font,
        str(out_dir),
        "--lock-axis",
        "wght=400",
    )
    assert result.returncode == 0, result.stderr
    # Partial font should be written
    partial_path = out_dir / "Roboto-VariableFont_wdth,wght-partial.ttf"
    assert partial_path.exists()
    # At least one web font output (e.g., .woff2) should be generated
    woff2_files = list(out_dir.glob("*.woff2"))
    assert woff2_files, "No .woff2 files generated"
