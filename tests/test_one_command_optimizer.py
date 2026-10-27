"""Tests for one‑command Web Font Optimizer CLI (FONT‑370)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

CLI = [sys.executable, "-m", "aspose_font.cli"]
ROBOTO = str(Path(__file__).resolve().parents[1] / "testdata" / "Roboto-VariableFont_wdth,wght.ttf")


def run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        CLI + list(args),
        capture_output=True,
        text=True,
    )


def test_web_optimize_one_produces_package(tmp_path: Path) -> None:
    out_dir = tmp_path / "optimized-web"
    result = run(
        "web-optimize-one",
        ROBOTO,
        str(out_dir),
    )
    assert result.returncode == 0
    # Expect at least one .woff2 or .woff file
    woff2 = list(out_dir.glob("*.woff2"))
    woff = list(out_dir.glob("*.woff"))
    assert woff2 or woff
    # Expect CSS, HTML, manifest files
    assert (out_dir / "fonts.css").exists()
    assert (out_dir / "specimen.html").exists()
    assert (out_dir / "optimizer-manifest.json").exists()
    # Verify manifest contains required keys
    manifest = json.loads((out_dir / "optimizer-manifest.json").read_text(encoding="utf-8"))
    for key in ("size_summary", "readiness", "notes"):
        assert key in manifest
    # Decision report should not be generated in this mode
    assert not (out_dir / "decision-report.json").exists()
