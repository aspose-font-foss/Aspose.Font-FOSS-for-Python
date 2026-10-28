"""Test for visual diff overlay generation via CLI."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_visual_diff_overlay(tmp_path: Path) -> None:
    font_path = Path(__file__).resolve().parents[1] / "testdata" / "Roboto-VariableFont_wdth,wght.ttf"
    out_dir = tmp_path
    cmd = [
        sys.executable,
        "-m",
        "aspose_font.cli",
        "var-delta",
        str(font_path),
        "-a",
        "wght=400",
        "-b",
        "wght=700",
        "--char",
        "A",
        "--visual-diff",
        "-o",
        str(out_dir),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    diff_png = out_dir / "diff_overlay.png"
    assert diff_png.is_file()
    assert diff_png.stat().st_size > 0
