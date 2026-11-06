"""Tests for FONT-278: CLI demo command for one-command Web Font Optimizer."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


def test_web_optimize_demo_cli_returns_zero_exit_code():
    """Verify CLI returns exit code 0 on success."""
    result = subprocess.run(
        [sys.executable, "-m", "aspose_font.cli", "web-optimize-demo"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"Expected exit code 0, got {result.returncode}. stderr: {result.stderr}"


def test_web_optimize_demo_cli_prints_demo_output_path():
    """Verify CLI prints 'Demo output:' line with absolute path."""
    result = subprocess.run(
        [sys.executable, "-m", "aspose_font.cli", "web-optimize-demo"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "Demo output:" in result.stdout

    lines = result.stdout.strip().split("\n")
    output_line = next((line for line in lines if line.startswith("Demo output:")), None)
    assert output_line is not None

    match = re.search(r"Demo output:\s*(.+)", output_line)
    assert match is not None
    output_path = Path(match.group(1).strip())
    assert output_path.is_absolute()


def test_web_optimize_demo_cli_prints_size_summary():
    """Verify CLI prints 'Size summary:' line with expected fields."""
    result = subprocess.run(
        [sys.executable, "-m", "aspose_font.cli", "web-optimize-demo"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "Size summary:" in result.stdout

    lines = result.stdout.strip().split("\n")
    summary_line = next((line for line in lines if line.startswith("Size summary:")), None)
    assert summary_line is not None

    assert "source_bytes=" in summary_line
    assert "output_bytes=" in summary_line
    assert "compression_ratio=" in summary_line



