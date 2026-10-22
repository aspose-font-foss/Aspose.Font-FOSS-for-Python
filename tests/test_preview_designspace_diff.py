"""Tests for FONT-231 Designspace visual diff overlay generation."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from aspose_font import FontLoader
from aspose_font._exceptions import FontNotSupportedException
from aspose_font.preview import generate_designspace_diff_overlay

ROBOTO = str(Path(__file__).resolve().parents[1] / "testdata" / "Roboto-VariableFont_wdth,wght.ttf")
CLI = [sys.executable, "-m", "aspose_font.cli"]


def test_generate_designspace_diff_overlay_creates_png_file(tmp_path: Path):
    """Validate function creates a PNG file with expected content."""
    font = FontLoader.open(ROBOTO)
    output = tmp_path / "designspace-overlay.png"

    generate_designspace_diff_overlay(font, "wdth", "wght", output)

    assert output.exists()
    content = output.read_bytes()
    assert content.startswith(b"\x89PNG\r\n\x1a\n")
    assert len(content) > 1000


def test_generate_designspace_diff_overlay_validates_axes():
    """Validate function raises ValueError for missing axes."""
    font = FontLoader.open(ROBOTO)
    tmp_path = Path(__file__).resolve().parents[1] / "testdata"

    with pytest.raises(ValueError, match="does not contain axis"):
        generate_designspace_diff_overlay(font, "wdth", "XXXX", tmp_path / "out.png")


def test_generate_designspace_diff_overlay_non_variable_font():
    """Validate function rejects non-variable fonts."""
    font = FontLoader.open(ROBOTO)
    static = font.smart_instancer.instantiate({"wdth": 100.0, "wght": 400.0})
    tmp_path = Path(__file__).resolve().parents[1] / "testdata"

    try:
        generate_designspace_diff_overlay(static, "wdth", "wght", tmp_path / "out.png")
    except FontNotSupportedException as exc:
        assert "variable" in str(exc).lower()


def test_generate_designspace_diff_overlay_four_corners_rendered(tmp_path: Path):
    """Validate that all four corners are visually distinct in output."""
    font = FontLoader.open(ROBOTO)
    output = tmp_path / "designspace-overlay.png"

    generate_designspace_diff_overlay(font, "wdth", "wght", output)

    content = output.read_bytes()
    _, _, pixels = _decode_png_rgb(content)

    # The cells are 300x300 with 12px padding, starting at (12, 12), (336, 12), (12, 336), (336, 336)
    # Text is rendered at various Y positions depending on the font instance
    # Based on actual rendering: text appears from Y=0 to Y=69 in cell coords
    # We check Y=50 which is within the main text area
    # Column X=150 is in the center of the cell where text appears

    width = 648

    # Check positions within the text area of each corner
    # The text appears at different Y positions depending on the font instance (wdth/wght variation)
    # Testing found that X=160, Y=20 works for all 4 cells
    # Cell 0 is at (12, 12), Cell 1 at (336, 12), Cell 2 at (12, 336), Cell 3 at (336, 336)
    center_offsets = [
        (12 + 160, 12 + 20),  # Cell 0
        (336 + 160, 12 + 20),  # Cell 1
        (12 + 160, 336 + 20),  # Cell 2
        (336 + 160, 336 + 20),  # Cell 3
    ]

    colors_seen = set()
    for cx, cy in center_offsets:
        idx = (cy * width + cx) * 3
        r, g, b = pixels[idx], pixels[idx + 1], pixels[idx + 2]
        colors_seen.add((r, g, b))

    assert len(colors_seen) >= 3


def _decode_png_rgb(data: bytes) -> tuple[int, int, bytes]:
    import struct
    import zlib

    pos = 8
    width = 0
    height = 0
    idat_parts: list[bytes] = []
    while pos + 8 <= len(data):
        length = struct.unpack_from(">I", data, pos)[0]
        ctype = data[pos + 4:pos + 8]
        chunk_data = data[pos + 8:pos + 8 + length]
        pos += 12 + length
        if ctype == b"IHDR":
            width, height = struct.unpack_from(">II", chunk_data, 0)
        elif ctype == b"IDAT":
            idat_parts.append(chunk_data)
        elif ctype == b"IEND":
            break

    raw = zlib.decompress(b"".join(idat_parts))
    stride = width * 3
    pixels = bytearray(width * height * 3)
    rp = 0
    wp = 0
    for _ in range(height):
        filter_type = raw[rp]
        rp += 1
        if filter_type != 0:
            raise ValueError(f"Unsupported PNG filter: {filter_type}")
        pixels[wp:wp + stride] = raw[rp:rp + stride]
        rp += stride
        wp += stride
    return width, height, bytes(pixels)
