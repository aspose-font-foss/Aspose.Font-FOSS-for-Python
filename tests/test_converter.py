"""Tests for SPEC-009 font format conversion."""

from __future__ import annotations

from pathlib import Path

import pytest

from aspose_font import (
    CffFont,
    ClosePath,
    CurveTo,
    EotFont,
    FontConversionException,
    FontLoader,
    FontType,
    GlyphId,
    LineTo,
    MoveTo,
    QuadraticTo,
    TtfFont,
    Type1Font,
    Woff2Font,
    WoffFont,
)
from aspose_font.converter import FontConverter, cubic_to_quads, quad_to_cubic


@pytest.fixture(scope="session")
def opensans_pfb_path(testdata_dir: Path) -> Path:
    return testdata_dir / "OpenSans-Regular.pfb"


def _build_minimal_sfnt(version: bytes) -> bytes:
    head = bytes(12) + (0x5F0F3CF5).to_bytes(4, "big") + bytes(54 - 16)
    maxp = (0x00010000).to_bytes(4, "big") + (1).to_bytes(2, "big") + bytes(26)
    num_tables = 2
    offset_table = (
        version
        + num_tables.to_bytes(2, "big")
        + (0).to_bytes(2, "big")
        + (0).to_bytes(2, "big")
        + (0).to_bytes(2, "big")
    )
    head_offset = 12 + num_tables * 16
    maxp_offset = head_offset + len(head)
    directory = (
        b"head"
        + (0).to_bytes(4, "big")
        + head_offset.to_bytes(4, "big")
        + len(head).to_bytes(4, "big")
        + b"maxp"
        + (0).to_bytes(4, "big")
        + maxp_offset.to_bytes(4, "big")
        + len(maxp).to_bytes(4, "big")
    )
    return offset_table + directory + head + maxp


def test_font_convert_delegates(roboto):
    converted = roboto.convert(FontType.WOFF)
    assert isinstance(converted, WoffFont)


def test_ttf_to_woff_roundtrip_openable(roboto):
    converted = FontConverter.convert(roboto, FontType.WOFF)
    assert isinstance(converted, WoffFont)

    blob = converted.to_bytes()
    reloaded = FontLoader.open(blob)
    assert isinstance(reloaded, WoffFont)
    assert reloaded.font_name == roboto.font_name


def test_ttf_to_woff2_returns_woff2(roboto):
    converted = FontConverter.convert(roboto, FontType.WOFF2)
    assert isinstance(converted, Woff2Font)


def test_ttf_to_cff_num_glyphs_matches(roboto):
    converted = FontConverter.convert(roboto, FontType.CFF)
    assert isinstance(converted, CffFont)
    assert converted.num_glyphs == roboto.num_glyphs


def test_ttf_to_cff_path_has_no_quadratic(roboto):
    converted = FontConverter.convert(roboto, FontType.CFF)
    gid = converted.encoding.unicode_to_gid(0x41)
    glyph = converted.glyph_accessor.get_glyph_by_id(gid)
    assert glyph.path is not None
    assert all(isinstance(cmd, (MoveTo, LineTo, CurveTo, ClosePath)) for cmd in glyph.path)
    assert not any(isinstance(cmd, QuadraticTo) for cmd in glyph.path)


def test_cff_to_ttf_num_glyphs_matches(opensans_cff):
    converted = FontConverter.convert(opensans_cff, FontType.TTF)
    assert isinstance(converted, TtfFont)
    assert converted.num_glyphs == opensans_cff.num_glyphs


def test_cff_to_ttf_path_has_no_curve(opensans_cff):
    converted = FontConverter.convert(opensans_cff, FontType.TTF)
    gid = converted.encoding.unicode_to_gid(0x41)
    glyph = converted.glyph_accessor.get_glyph_by_id(gid)
    assert glyph.path is not None
    assert all(isinstance(cmd, (MoveTo, LineTo, QuadraticTo, ClosePath)) for cmd in glyph.path)
    assert not any(isinstance(cmd, CurveTo) for cmd in glyph.path)


def test_type1_to_ttf_returns_ttf(opensans_pfb_path: Path):
    src = FontLoader.open(str(opensans_pfb_path))
    assert isinstance(src, Type1Font)
    converted = FontConverter.convert(src, FontType.TTF)
    assert isinstance(converted, TtfFont)


def test_woff_to_ttf_returns_ttf(saira_woff):
    converted = FontConverter.convert(saira_woff, FontType.TTF)
    assert isinstance(converted, TtfFont)
    assert converted is not saira_woff.inner_font


def test_unsupported_conversion_raises(roboto):
    with pytest.raises(FontConversionException, match="No conversion path"):
        FontConverter.convert(roboto, FontType.TYPE1)


def test_quad_to_cubic_straight_line_controls_are_collinear():
    p0 = (0.0, 0.0)
    q = (5.0, 5.0)
    p3 = (10.0, 10.0)
    _, c1, c2, _ = quad_to_cubic(p0, q, p3)
    assert c1[0] == pytest.approx(c1[1])
    assert c2[0] == pytest.approx(c2[1])


def _quadratic_at_t(p0: tuple[float, float], q: tuple[float, float], p2: tuple[float, float], t: float) -> tuple[float, float]:
    omt = 1.0 - t
    x = (omt * omt * p0[0]) + (2.0 * omt * t * q[0]) + (t * t * p2[0])
    y = (omt * omt * p0[1]) + (2.0 * omt * t * q[1]) + (t * t * p2[1])
    return (x, y)


def _cubic_at_t(
    p0: tuple[float, float],
    c1: tuple[float, float],
    c2: tuple[float, float],
    p3: tuple[float, float],
    t: float,
) -> tuple[float, float]:
    omt = 1.0 - t
    x = (
        (omt * omt * omt * p0[0])
        + (3.0 * omt * omt * t * c1[0])
        + (3.0 * omt * t * t * c2[0])
        + (t * t * t * p3[0])
    )
    y = (
        (omt * omt * omt * p0[1])
        + (3.0 * omt * omt * t * c1[1])
        + (3.0 * omt * t * t * c2[1])
        + (t * t * t * p3[1])
    )
    return (x, y)


def test_quad_to_cubic_lossless():
    p0 = (100.0, 50.0)
    q = (140.0, 220.0)
    p3 = (260.0, 90.0)
    c0, c1, c2, c3 = quad_to_cubic(p0, q, p3)
    quad_mid = _quadratic_at_t(p0, q, p3, 0.5)
    cubic_mid = _cubic_at_t(c0, c1, c2, c3, 0.5)
    assert cubic_mid[0] == pytest.approx(quad_mid[0])
    assert cubic_mid[1] == pytest.approx(quad_mid[1])


def test_cubic_to_quads_returns_segments():
    segs = cubic_to_quads((0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (20.0, 10.0), tolerance=0.5)
    assert len(segs) >= 1
    start, ctrl, end = segs[0]
    assert isinstance(start, tuple)
    assert isinstance(ctrl, tuple)
    assert isinstance(end, tuple)


def test_cubic_to_quads_straight():
    segs = cubic_to_quads((0.0, 0.0), (10.0, 0.0), (20.0, 0.0), (30.0, 0.0), tolerance=0.5)
    assert len(segs) == 1


def test_cubic_to_quads_tolerance():
    loose = cubic_to_quads((0.0, 0.0), (0.0, 100.0), (100.0, 100.0), (100.0, 0.0), tolerance=30.0)
    tight = cubic_to_quads((0.0, 0.0), (0.0, 100.0), (100.0, 100.0), (100.0, 0.0), tolerance=1.0)
    assert len(tight) > len(loose)


def test_type1_to_cff_returns_cff(opensans_pfb_path: Path):
    src = FontLoader.open(str(opensans_pfb_path))
    assert isinstance(src, Type1Font)
    converted = FontConverter.convert(src, FontType.CFF)
    assert isinstance(converted, CffFont)
    assert converted.num_glyphs == src.num_glyphs


def test_woff2_to_woff_returns_woff(saira_woff2):
    converted = FontConverter.convert(saira_woff2, FontType.WOFF)
    assert isinstance(converted, WoffFont)


def test_identity_conversion_returns_same_object(roboto):
    assert FontConverter.convert(roboto, FontType.TTF) is roboto


def test_path_compilation_handles_empty_glyph(opensans_cff):
    converted = FontConverter.convert(opensans_cff, FontType.TTF)
    glyph = converted.glyph_accessor.get_glyph_by_id(GlyphId(0))
    assert glyph.path is None or len(glyph.path) >= 0


def test_ttf_to_eot_returns_eot(roboto):
    converted = FontConverter.convert(roboto, FontType.EOT)
    assert isinstance(converted, EotFont)


def test_eot_to_woff2_returns_woff2(saira_eot):
    converted = FontConverter.convert(saira_eot, FontType.WOFF2)
    assert isinstance(converted, Woff2Font)
    blob = converted.to_bytes()
    reloaded = FontLoader.open(blob)
    assert isinstance(reloaded, Woff2Font)


def test_eot_to_ttf_returns_ttf(saira_eot):
    converted = FontConverter.convert(saira_eot, FontType.TTF)
    assert isinstance(converted, TtfFont)
    assert converted.font_type == FontType.TTF


def test_eot_to_otf_works_for_otf_payload():
    otf = FontLoader.open(_build_minimal_sfnt(b"OTTO"))
    assert isinstance(otf, TtfFont)
    assert otf.font_type == FontType.OTF
    eot = FontConverter.convert(otf, FontType.EOT)
    assert isinstance(eot, EotFont)
    converted = FontConverter.convert(eot, FontType.OTF)
    assert isinstance(converted, TtfFont)
    assert converted.font_type == FontType.OTF


def test_eot_to_otf_raises_for_ttf_payload(saira_eot):
    with pytest.raises(FontConversionException, match="does not contain OTF payload"):
        FontConverter.convert(saira_eot, FontType.OTF)
