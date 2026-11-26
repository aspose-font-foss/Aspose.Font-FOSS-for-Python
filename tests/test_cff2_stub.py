"""Tests for CFF2 stub implementation."""
from __future__ import annotations

import json
import subprocess
import sys

import pytest

from aspose_font import Cff2Font

pytestmark = pytest.mark.skip(reason="Stub tests deprecated after core metadata implementation")

CLI = [sys.executable, "-m", "aspose_font.cli"]


def test_cff2_font_instantiation():
    """Test Cff2Font can be instantiated with dummy data."""
    dummy_data = b"CFF2" + b"\x00" * 100
    font = Cff2Font(dummy_data)
    assert font is not None


def test_cff2_font_font_type():
    """Test Cff2Font.font_type returns FontType.CFF."""
    dummy_data = b"CFF2" + b"\x00" * 100
    font = Cff2Font(dummy_data)
    assert font.font_type.value == "CFF"


def test_cff2_font_font_name():
    """Test Cff2Font.font_name returns empty string."""
    dummy_data = b"CFF2" + b"\x00" * 100
    font = Cff2Font(dummy_data)
    assert font.font_name == ""


def test_cff2_font_font_family():
    """Test Cff2Font.font_family returns empty string."""
    dummy_data = b"CFF2" + b"\x00" * 100
    font = Cff2Font(dummy_data)
    assert font.font_family == ""


def test_cff2_font_font_style():
    """Test Cff2Font.font_style returns empty string."""
    dummy_data = b"CFF2" + b"\x00" * 100
    font = Cff2Font(dummy_data)
    assert font.font_style == ""


def test_cff2_font_num_glyphs():
    """Test Cff2Font.num_glyphs returns 0."""
    dummy_data = b"CFF2" + b"\x00" * 100
    font = Cff2Font(dummy_data)
    assert font.num_glyphs == 0


def test_cff2_font_metrics():
    """Test Cff2Font.metrics returns None."""
    dummy_data = b"CFF2" + b"\x00" * 100
    font = Cff2Font(dummy_data)
    assert font.metrics is None


def test_cff2_font_encoding():
    """Test Cff2Font.encoding returns None."""
    dummy_data = b"CFF2" + b"\x00" * 100
    font = Cff2Font(dummy_data)
    assert font.encoding is None


def test_cff2_font_glyph_accessor():
    """Test Cff2Font.glyph_accessor returns None."""
    dummy_data = b"CFF2" + b"\x00" * 100
    font = Cff2Font(dummy_data)
    assert font.glyph_accessor is None


def test_cff2_font_variable_axes():
    """Test Cff2Font.variable_axes returns empty list."""
    dummy_data = b"CFF2" + b"\x00" * 100
    font = Cff2Font(dummy_data)
    axes = font.variable_axes
    assert axes == []
    assert isinstance(axes, list)


def test_cff2_cli_info_stub_output():
    """Test cff2-info CLI command returns stub JSON."""
    result = subprocess.run(
        CLI + ["cff2-info", __file__],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["status"] == "stub"
    assert payload["message"] == "CFF2 support pending"
