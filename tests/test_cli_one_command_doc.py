"""Tests for FONT-271: One-command Web Font Optimizer documentation reference in CLI help."""

from __future__ import annotations

import subprocess
import sys

CLI = [sys.executable, "-m", "aspose_font.cli"]


def test_web_optimize_help_contains_documentation_url():
    """Verify that aspose-font web-optimize --help includes link to one_command_web_optimizer.md."""
    result = subprocess.run(
        CLI + ["web-optimize", "--help"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "one_command_web_optimizer.md" in result.stdout
    assert "CLI Usage" in result.stdout or "docs/one_command_web_optimizer.md" in result.stdout
