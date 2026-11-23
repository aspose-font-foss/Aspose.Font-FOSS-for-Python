"""CLI tests for CFF2 variable font support."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest


def test_cli_cff2_info_runs_without_error(tmp_path: Path) -> None:
    font_file = tmp_path / "test.cff2"
    font_file.write_bytes(b"CFF2" + b"\x00" * 100)

    result = subprocess.run(
        [sys.executable, "-m", "aspose_font.cli", "cff2-info", str(font_file)],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, f"Command failed: {result.stderr}"


def test_cli_cff2_info_output_valid_json(tmp_path: Path) -> None:
    font_file = tmp_path / "test.cff2"
    font_file.write_bytes(b"CFF2" + b"\x00" * 100)

    result = subprocess.run(
        [sys.executable, "-m", "aspose_font.cli", "cff2-info", str(font_file)],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0

    try:
        json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        pytest.fail(f"CLI output is not valid JSON: {exc}")


def test_cli_cff2_info_output_contains_blend(tmp_path: Path) -> None:
    font_file = tmp_path / "test.cff2"
    font_file.write_bytes(b"CFF2" + b"\x00" * 100)

    result = subprocess.run(
        [sys.executable, "-m", "aspose_font.cli", "cff2-info", str(font_file)],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    output = result.stdout

    import re
    blend_pattern = r'"sample_blend_result":\s*(\d+\.?\d*)'
    assert re.search(blend_pattern, output), f"Expected blend result in output: {output}"


def test_cli_cff2_info_output_contains_font_name(tmp_path: Path) -> None:
    font_file = tmp_path / "test.cff2"
    font_file.write_bytes(b"CFF2" + b"\x00" * 100)

    result = subprocess.run(
        [sys.executable, "-m", "aspose_font.cli", "cff2-info", str(font_file)],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    output = result.stdout

    try:
        payload = json.loads(output)
        assert "font_name" in payload
    except json.JSONDecodeError as exc:
        pytest.fail(f"CLI output is not valid JSON: {exc}")


def test_cli_cff2_info_output_contains_num_glyphs(tmp_path: Path) -> None:
    font_file = tmp_path / "test.cff2"
    font_file.write_bytes(b"CFF2" + b"\x00" * 100)

    result = subprocess.run(
        [sys.executable, "-m", "aspose_font.cli", "cff2-info", str(font_file)],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    output = result.stdout

    try:
        payload = json.loads(output)
        assert "num_glyphs" in payload
    except json.JSONDecodeError as exc:
        pytest.fail(f"CLI output is not valid JSON: {exc}")
