"""Tests for package versioning and PEP 440 compliance."""

from __future__ import annotations

import re
import subprocess
import sys

import aspose_font


def test_package_version_exists() -> None:
    assert hasattr(aspose_font, "__version__")
    assert isinstance(aspose_font.__version__, str)
    assert len(aspose_font.__version__) > 0


def test_cli_version_flag() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "aspose_font.cli", "--version"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert f"aspose-font {aspose_font.__version__}" in result.stdout.strip()


def test_calver_format_pep440() -> None:
    pep440_pattern = re.compile(
        r"^([1-9][0-9]*!)?(0|[1-9][0-9]*)(\.(0|[1-9][0-9]*))*((a|b|rc)(0|[1-9][0-9]*))?(\.post(0|[1-9][0-9]*))?(\.dev(0|[1-9][0-9]*))?$"
    )
    # Ensure current CalVer examples adhere to PEP 440
    examples = ["26.10.1", "26.5.1", "26.12.3", "1.0.0"]
    for ex in examples:
        assert pep440_pattern.match(ex) is not None, f"Version {ex} should be PEP 440 compliant"
