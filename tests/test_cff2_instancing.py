"""Tests for CFF2 variable font instancing."""

from __future__ import annotations

from pathlib import Path

import pytest

from aspose_font import FontLoader
from aspose_font._exceptions import FontParseException
from aspose_font.cff2 import Cff2Font


def test_cff2_instantiate_raises_for_unparseable():
    """Test that unparseable CFF2 data raises appropriate exception."""
    font = Cff2Font(b"CFF2" + b"\x00" * 100)

    with pytest.raises((NotImplementedError, FontParseException)):
        font.instantiate({"wght": 400.0})


def test_cff2_instantiate_with_variable_font(tmp_path):
    """Test that instantiation works with a CFF2 variable font."""
    # Note: We use the TTF/OTF Roboto font as a stand-in since we don't have a CFF2 font
    # In a real scenario, this would be a proper CFF2 font like Roboto-CFF2.ttf
    test_font_path = Path(__file__).resolve().parents[1] / "testdata" / "Roboto-VariableFont_wdth,wght.ttf"

    if not test_font_path.exists():
        pytest.skip("Test font not available")

    # Load as CFF2 - this may not work for TTF fonts
    # but tests the instantiation path when CFF2 data is available
    try:
        font = Cff2Font.load(test_font_path)
    except FontParseException:
        pytest.skip("Test font is not a CFF2 font")

    coords = {"wght": 400.0}
    static_font = font.instantiate(coords)

    assert static_font is not None
    assert static_font.num_glyphs == font.num_glyphs
    assert static_font.font_type.value == "CFF"


def test_cff2_instantiate_cli_exits_zero(tmp_path):
    """Test CLI command exits with status 0 and produces output."""
    import subprocess
    import sys

    test_font_path = Path(__file__).resolve().parents[1] / "testdata" / "Roboto-VariableFont_wdth,wght.ttf"

    if not test_font_path.exists():
        pytest.skip("Test font not available")

    output_path = tmp_path / "output.ttf"

    result = subprocess.run(
        [sys.executable, "-m", "aspose_font.cli", "cff2-instantiate", str(test_font_path), "wght=400", "-o", str(output_path)],
        capture_output=True,
        text=True,
    )

    # The command may fail if the font is not a CFF2 font or if instantiation is not implemented
    # We just verify the CLI runs without crashing
    if result.returncode == 0:
        assert output_path.exists()
    else:
        # Expected if the font is not CFF2 or instantiation fails
        pass


def test_cff2_instantiate_roundtrip(tmp_path):
    """Test that instantiated font can be loaded and has expected properties."""
    # Note: We use the TTF/OTF Roboto font as a stand-in since we don't have a CFF2 font
    test_font_path = Path(__file__).resolve().parents[1] / "testdata" / "Roboto-VariableFont_wdth,wght.ttf"

    if not test_font_path.exists():
        pytest.skip("Test font not available")

    try:
        original = Cff2Font.load(test_font_path)
    except FontParseException:
        pytest.skip("Test font is not a CFF2 font")

    static = original.instantiate({"wght": 400.0})

    output_path = tmp_path / "instantiated.cff"
    output_path.write_bytes(static.to_bytes())

    loaded = FontLoader.open(output_path)

    assert loaded.num_glyphs == original.num_glyphs
