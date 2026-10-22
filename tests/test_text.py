"""Tests for TextRenderer.layout() (SPEC-014 / ADR-013 / FONT-15)."""
from __future__ import annotations

import math

import pytest

from aspose_font import TtfFont
from aspose_font._types import CurveTo, GlyphId, LineTo, MoveTo, QuadraticTo
from aspose_font.text import GlyphLayout, TextLayout, TextRenderer


def _first_xy(path) -> tuple[float, float] | None:
    if path is None:
        return None
    for cmd in path:
        if isinstance(cmd, (MoveTo, LineTo)):
            return (cmd.x, cmd.y)
        if isinstance(cmd, QuadraticTo):
            return (cmd.x, cmd.y)
        if isinstance(cmd, CurveTo):
            return (cmd.x, cmd.y)
    return None


def test_layout_single_char_returns_one_glyph(roboto: TtfFont) -> None:
    layout = TextRenderer.layout(roboto, "A")
    assert isinstance(layout, TextLayout)
    assert len(layout.glyphs) == 1
    gl = layout.glyphs[0]
    assert isinstance(gl, GlyphLayout)
    assert gl.char == "A"
    assert gl.advance_width > 0


def test_layout_single_char_has_path(roboto: TtfFont) -> None:
    layout = TextRenderer.layout(roboto, "A")
    # "A" should have a non-trivial glyph outline
    assert layout.glyphs[0].path is not None
    assert len(layout.glyphs[0].path) > 0


def test_layout_two_chars_x_offset(roboto: TtfFont) -> None:
    layout = TextRenderer.layout(roboto, "AB")
    assert len(layout.glyphs) == 2
    # Second glyph x_offset == first glyph advance_width (no kern between A,B here)
    a_adv = layout.glyphs[0].advance_width
    b_off = layout.glyphs[1].x_offset
    assert abs(b_off - a_adv) < 1e-6


def test_layout_total_width(roboto: TtfFont) -> None:
    layout = TextRenderer.layout(roboto, "AB", kern=False)
    expected = sum(gl.advance_width for gl in layout.glyphs)
    assert abs(layout.total_width - expected) < 1e-6


def test_layout_empty_string(roboto: TtfFont) -> None:
    layout = TextRenderer.layout(roboto, "")
    assert len(layout.glyphs) == 0
    assert layout.total_width == 0.0


def test_layout_missing_char_fallback(roboto: TtfFont) -> None:
    # U+FFFD replacement character is likely not in Roboto; should fall back to GlyphId(0)
    layout = TextRenderer.layout(roboto, "\uFFFF")
    assert len(layout.glyphs) == 1
    assert layout.glyphs[0].glyph_id == GlyphId(0)


def test_layout_size_scaling(roboto: TtfFont) -> None:
    text = "AB"
    layout = TextRenderer.layout(roboto, text, size=1000.0, kern=False)
    raw_sum = 0
    for ch in text:
        gid = roboto.encoding.unicode_to_gid(ord(ch))
        raw_sum += roboto.glyph_accessor.get_glyph_by_id(gid).advance_width
    expected = raw_sum * 1000.0 / roboto.metrics.units_per_em
    assert math.isclose(layout.total_width, expected, rel_tol=0.0, abs_tol=1e-6)


def test_layout_kern_applied(roboto: TtfFont) -> None:
    kern_pairs = roboto.get_kern_pairs()
    if not kern_pairs:
        pytest.skip("No kern pairs available")

    gid_to_cp: dict[int, int] = {}
    for cp in roboto.encoding.get_all_codepoints():
        gid = int(roboto.encoding.unicode_to_gid(cp))
        gid_to_cp.setdefault(gid, cp)

    chosen = None
    for pair in kern_pairs:
        left = int(pair.left)
        right = int(pair.right)
        if pair.value != 0 and left in gid_to_cp and right in gid_to_cp:
            chosen = pair
            break
    if chosen is None:
        pytest.skip("No renderable kern pair available")

    text = chr(gid_to_cp[int(chosen.left)]) + chr(gid_to_cp[int(chosen.right)])
    layout_no_kern = TextRenderer.layout(roboto, text, kern=False)
    layout_kern = TextRenderer.layout(roboto, text, kern=True)
    assert len(layout_no_kern.glyphs) == 2
    assert len(layout_kern.glyphs) == 2
    assert not math.isclose(
        layout_kern.glyphs[1].x_offset,
        layout_no_kern.glyphs[1].x_offset,
        rel_tol=0.0,
        abs_tol=1e-9,
    )


def test_layout_glyphs_method(roboto: TtfFont) -> None:
    gids = [roboto.encoding.unicode_to_gid(ord("H")), roboto.encoding.unicode_to_gid(ord("i"))]
    layout = TextRenderer.layout_glyphs(roboto, gids)
    assert len(layout.glyphs) == 2
    assert layout.glyphs[0].char == ""  # no source char for layout_glyphs


def test_layout_path_scaled(roboto: TtfFont) -> None:
    l1 = TextRenderer.layout(roboto, "A", size=1.0)
    l2 = TextRenderer.layout(roboto, "A", size=2.0)
    p1 = _first_xy(l1.glyphs[0].path)
    p2 = _first_xy(l2.glyphs[0].path)
    assert p1 is not None
    assert p2 is not None
    assert math.isclose(p2[0], p1[0] * 2.0, rel_tol=0.0, abs_tol=1e-6)
    assert math.isclose(p2[1], p1[1] * 2.0, rel_tol=0.0, abs_tol=1e-6)


def test_layout_path_translated(roboto: TtfFont) -> None:
    layout_ab = TextRenderer.layout(roboto, "AB", kern=False)
    layout_b = TextRenderer.layout(roboto, "B", kern=False)
    p_ab = _first_xy(layout_ab.glyphs[1].path)
    p_b = _first_xy(layout_b.glyphs[0].path)
    assert p_ab is not None
    assert p_b is not None
    expected_shift = layout_ab.glyphs[0].advance_width
    assert math.isclose(p_ab[0] - p_b[0], expected_shift, rel_tol=0.0, abs_tol=1e-6)
