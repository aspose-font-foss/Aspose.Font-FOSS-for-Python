"""Utility functions for Aspose Font library."""
# ruff: noqa: I001

from __future__ import annotations

from pathlib import Path
from typing import Union

from aspose_font.loader import FontLoader, LoadedFont
from aspose_font._exceptions import UnsupportedFontFormatException


def extract_font_metadata(source: Union[str, Path]) -> dict:
    """Extract basic metadata from a font file.

    Parameters
    ----------
    source: Union[str, Path]
        Path-like object or string pointing to a font file.

    Returns
    -------
    dict
        Mapping with keys:
        - ``font_name`` (str): name of the font.
        - ``num_glyphs`` (int): total glyph count.
        - ``is_variable`` (bool): whether the font is variable.
        - ``font_type`` (str): enum name of the detected font type.

    Raises
    ------
    FileNotFoundError
        If the provided path does not exist.
    ValueError
        If the file format is not a supported font.
    """
    # Resolve path and verify existence for string/path input
    if isinstance(source, (str, Path)):
        path = Path(source)
        if not path.is_file():
            raise FileNotFoundError(str(path))
        load_source: Union[str, Path] = path
    else:
        load_source = source

    try:
        loaded: LoadedFont = FontLoader.load(load_source)
    except UnsupportedFontFormatException as exc:
        raise ValueError(str(exc)) from exc

    font = loaded.font
    return {
        "font_name": Path(source).stem if isinstance(source, (str, Path)) else font.font_name,
        "num_glyphs": font.num_glyphs,
        "is_variable": getattr(font, "is_variable", False),
        "font_type": loaded.detected_font_type.name,
    }
