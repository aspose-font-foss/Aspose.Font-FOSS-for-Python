"""Tests for extract_font_metadata utility."""
# ruff: noqa: I001

from pathlib import Path
import pytest

from aspose_font import extract_font_metadata

# Path to a sample variable font provided in the repository
VARIABLE_FONT = Path(__file__).resolve().parents[1] / "testdata" / "Roboto-VariableFont_wdth,wght.ttf"


def test_extract_metadata_variable_font():
    meta = extract_font_metadata(VARIABLE_FONT)
    assert meta["font_name"] == VARIABLE_FONT.stem
    assert meta["num_glyphs"] > 0
    assert meta["is_variable"] is True
    # Font type should be detected as TTF (enum name)
    assert meta["font_type"] == "TTF"


def test_extract_metadata_nonexistent_path():
    with pytest.raises(FileNotFoundError):
        extract_font_metadata(Path("nonexistent/font.ttf"))


def test_extract_metadata_unsupported_format(tmp_path):
    # Create a simple text file
    txt_file = tmp_path / "sample.txt"
    txt_file.write_text("just some text")
    with pytest.raises(ValueError):
        extract_font_metadata(txt_file)
