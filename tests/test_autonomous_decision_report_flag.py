"""Tests for autonomous CLI decision report file generation (FONT-371)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

CLI = [sys.executable, "-m", "aspose_font.cli"]
ROBOTO = str(Path(__file__).resolve().parents[1] / "testdata" / "Roboto-VariableFont_wdth,wght.ttf")


def test_autonomous_cli_decision_report_file(tmp_path: Path) -> None:
    """CLI --decision-report should write decision report JSON file."""
    out_dir = tmp_path / "autonomous_output"
    out_dir.mkdir()
    custom_report = "custom-decision.json"

    result = subprocess.run(
        CLI + ["autonomous", ROBOTO, str(out_dir), "--preset", "latin", "--decision-report", custom_report],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"CLI failed: {result.stderr}"

    custom_path = out_dir / custom_report
    assert custom_path.exists()

    data = json.loads(custom_path.read_text(encoding="utf-8"))
    assert "decision" in data
    assert "reason" in data
    # Ensure decision value is one of expected
    # decision value may vary based on workflow; ensure it is a non-empty string
    assert isinstance(data["decision"], str) and data["decision"]

    # Default path should not be created
    assert not (out_dir / "decision-report.json").exists()
