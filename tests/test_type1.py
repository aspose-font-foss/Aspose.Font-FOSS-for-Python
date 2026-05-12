"""Tests for SPEC-006 Type1 parsing."""

from __future__ import annotations

from pathlib import Path

import pytest

from aspose_font import CurveTo, FontLoader, GlyphId, QuadraticTo, Type1Font
from aspose_font._exceptions import FontParseException
from aspose_font.type1.eexec import charstring_decrypt_full, eexec_decrypt
from aspose_font.type1.pfa import pfa_to_ps_stream
from aspose_font.type1.pfb import PFB_ASCII, PFB_BINARY, PFB_EOF, parse_pfb


@pytest.fixture(scope="session")
def opensans_pfb_path(testdata_dir: Path) -> Path:
    return testdata_dir / "OpenSans-Regular.pfb"


@pytest.fixture(scope="session")
def arial_pfa_path(testdata_dir: Path) -> Path:
    return testdata_dir / "Arial.pfa"


def test_pfb_loads(opensans_pfb_path: Path):
    font = FontLoader.open(str(opensans_pfb_path))
    assert isinstance(font, Type1Font)


def test_pfa_loads(arial_pfa_path: Path):
    font = FontLoader.open(str(arial_pfa_path))
    assert isinstance(font, Type1Font)


def test_type1_font_name_nonempty(opensans_pfb_path: Path):
    font = FontLoader.open(str(opensans_pfb_path))
    assert isinstance(font, Type1Font)
    assert font.font_name.strip() != ""


def test_type1_num_glyphs_positive(opensans_pfb_path: Path):
    font = FontLoader.open(str(opensans_pfb_path))
    assert isinstance(font, Type1Font)
    assert font.num_glyphs > 0


def test_type1_glyph_path_has_curveto(opensans_pfb_path: Path):
    font = FontLoader.open(str(opensans_pfb_path))
    assert isinstance(font, Type1Font)
    glyph = font.glyph_accessor.get_glyph_by_id(GlyphId(1))
    assert glyph.path is not None
    assert any(isinstance(cmd, CurveTo) for cmd in glyph.path)


def test_type1_no_quadratic_to(opensans_pfb_path: Path):
    font = FontLoader.open(str(opensans_pfb_path))
    assert isinstance(font, Type1Font)
    glyph = font.glyph_accessor.get_glyph_by_id(GlyphId(1))
    assert glyph.path is not None
    assert not any(isinstance(cmd, QuadraticTo) for cmd in glyph.path)


def test_type1_load_afm(testdata_dir: Path, opensans_pfb_path: Path):
    font = FontLoader.open(str(opensans_pfb_path))
    assert isinstance(font, Type1Font)
    font.load_afm(str(testdata_dir / "Helvetica.afm"))
    assert font.metrics.ascender > 0


def test_eexec_decrypt_known_vector():
    # Encrypted form of b"hello" using key=55665 with 4 zero IV bytes.
    ciphertext = bytes.fromhex("d9d66f6337d2f94c5f")
    assert eexec_decrypt(ciphertext) == b"hello"


def test_charstring_decrypt_known_vector():
    # Encrypted form of b"hello" using key=4330 with lenIV=4.
    ciphertext = bytes.fromhex("10bf31709aa9e33dee")
    assert charstring_decrypt_full(ciphertext, len_iv=4) == b"hello"


def test_pfb_segments_parsed(opensans_pfb_path: Path):
    data = opensans_pfb_path.read_bytes()
    segs = parse_pfb(data)
    assert len(segs) >= 3
    assert segs[0].seg_type == PFB_ASCII
    assert segs[1].seg_type == PFB_BINARY
    assert segs[-1].seg_type == PFB_EOF


def test_pfa_hex_decode():
    pfa = (
        b"%!PS-AdobeFont-1.0: Test\n"
        b"currentfile eexec\n"
        b"41424344\n"
        b"cleartomark\n"
    )
    stream = pfa_to_ps_stream(pfa)
    assert b"ABCD" in stream


def test_malformed_pfb_raises_parse_error():
    with pytest.raises(FontParseException):
        FontLoader.open(b"\x80\x01\x01\x00\x00\x00")


def test_invalid_pfa_eexec_hex_raises_parse_error():
    bad_pfa = (
        b"%!PS-AdobeFont-1.0: Test\n"
        b"currentfile eexec\n"
        b"ZZ-not-hex\n"
        b"cleartomark\n"
    )
    with pytest.raises(FontParseException):
        FontLoader.open(bad_pfa)
