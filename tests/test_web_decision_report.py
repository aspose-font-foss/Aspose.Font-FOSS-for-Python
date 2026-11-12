"""Tests for the Web Font Optimizer decision report generation.
"""

import json
import subprocess
import sys
from pathlib import Path

from aspose_font.web import WebFontOptimizer


def test_generate_decision_report_method(tmp_path: Path) -> None:
    """Test the generate_decision_report method directly."""
    # Create a minimal optimizer-manifest.json
    manifest = {
        "export_mode": "live",
        "woff2_files": ["fonts/Roboto.woff2"],
        "family_name": "Roboto",
        "readiness": {"score": 85},
    }
    output_dir = tmp_path / "out"
    output_dir.mkdir()
    (output_dir / "optimizer-manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    optimizer = WebFontOptimizer("dummy.ttf", output_dir)
    report = optimizer.generate_decision_report()

    assert isinstance(report, dict)
    assert set(report.keys()) == {"mode", "css_snippet", "readiness_score"}
    assert report["mode"] == "live"
    assert isinstance(report["css_snippet"], str) and "@font-face" in report["css_snippet"]
    assert report["readiness_score"] == 85


def test_cli_web_decision_report(tmp_path: Path) -> None:
    """Test the CLI subcommand ``web-decision-report``."""
    # Setup manifest as before
    manifest = {
        "export_mode": "static",
        "woff2_files": ["fonts/Example.woff2"],
        "family_name": "Example",
        "readiness": {"score": 92},
    }
    output_dir = tmp_path / "out"
    output_dir.mkdir()
    (output_dir / "optimizer-manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    # Run CLI without --output (stdout)
    result = subprocess.run(
        [sys.executable, "-m", "aspose_font.cli", "web-decision-report", "dummy.ttf", str(output_dir)],
        capture_output=True,
        text=True,
        check=True,
    )
    out = json.loads(result.stdout)
    assert out["mode"] == "static"
    assert out["readiness_score"] == 92

    # Run CLI with --output
    out_file = tmp_path / "report.json"
    subprocess.run(
        [
            sys.executable,
            "-m",
            "aspose_font.cli",
            "web-decision-report",
            "dummy.ttf",
            str(output_dir),
            "--output",
            str(out_file),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    assert out_file.is_file()
    file_content = json.loads(out_file.read_text(encoding="utf-8"))
    assert file_content == out
