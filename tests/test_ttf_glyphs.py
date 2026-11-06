"""Tests for SPEC-003 TTF glyph outline extraction."""

from __future__ import annotations

import pytest

from aspose_font import ClosePath, CurveTo, GlyphId, LineTo, MoveTo, QuadraticTo
from aspose_font.ttf.glyph import TtfGlyphParser
from aspose_font.ttf.tables.glyf import GlyfTable
from aspose_font.ttf.tables.hmtx import HMetric, HmtxTable
from aspose_font.ttf.tables.loca import LocaTable


def _commands(path):
    return list(path) if path is not None else []


def _signature(path):
    out = []
    for cmd in _commands(path):
        if isinstance(cmd, ClosePath):
            out.append(("Z",))
        elif isinstance(cmd, MoveTo):
            out.append(("M", cmd.x, cmd.y))
        elif isinstance(cmd, LineTo):
            out.append(("L", cmd.x, cmd.y))
        elif isinstance(cmd, QuadraticTo):
            out.append(("Q", cmd.x1, cmd.y1, cmd.x, cmd.y))
        elif isinstance(cmd, CurveTo):
            out.append(("C", cmd.x1, cmd.y1, cmd.x2, cmd.y2, cmd.x, cmd.y))
    return out


def test_notdef_glyph_loads(roboto):
    glyph = roboto.glyph_accessor.get_glyph_by_id(GlyphId(0))
    assert glyph.glyph_id == GlyphId(0)


def test_latin_a_has_path(roboto):
    gid = roboto.encoding.unicode_to_gid(0x41)
    glyph = roboto.glyph_accessor.get_glyph_by_id(gid)
    assert glyph.path is not None
    cmds = _commands(glyph.path)
    assert any(isinstance(c, MoveTo) for c in cmds)
    assert any(isinstance(c, (LineTo, QuadraticTo)) for c in cmds)
    assert any(isinstance(c, ClosePath) for c in cmds)


def test_path_no_consecutive_moveto(roboto):
    gid = roboto.encoding.unicode_to_gid(0x41)
    glyph = roboto.glyph_accessor.get_glyph_by_id(gid)
    cmds = _commands(glyph.path)
    for i in range(len(cmds) - 1):
        assert not (isinstance(cmds[i], MoveTo) and isinstance(cmds[i + 1], MoveTo))


def test_space_glyph_has_no_path(roboto):
    gid = roboto.encoding.unicode_to_gid(0x20)
    glyph = roboto.glyph_accessor.get_glyph_by_id(gid)
    assert glyph.path is None


def test_composite_glyph_resolves(roboto):
    try:
        gid = roboto.encoding.unicode_to_gid(0x00C1)  # Latin Capital Letter A with Acute
    except Exception:
        pytest.skip("Composite glyph test codepoint unavailable in font")
    glyph = roboto.glyph_accessor.get_glyph_by_id(gid)
    assert glyph.path is not None
    assert len(_commands(glyph.path)) > 0


def test_get_glyph_idempotent(roboto):
    gid = roboto.encoding.unicode_to_gid(0x41)
    g1 = roboto.glyph_accessor.get_glyph_by_id(gid)
    g2 = roboto.glyph_accessor.get_glyph_by_id(gid)
    assert _signature(g1.path) == _signature(g2.path)


def test_all_glyph_ids_count(roboto):
    gids = roboto.glyph_accessor.get_all_glyph_ids()
    assert len(gids) == roboto.num_glyphs
    assert gids[0] == GlyphId(0)
    assert gids[-1] == GlyphId(roboto.num_glyphs - 1)


def test_quadratic_to_commands_only(roboto):
    gid = roboto.encoding.unicode_to_gid(0x41)
    glyph = roboto.glyph_accessor.get_glyph_by_id(gid)
    for cmd in _commands(glyph.path):
        assert not isinstance(cmd, CurveTo)


def test_flags_to_path_two_off_curve():
    parser = TtfGlyphParser(
        loca=LocaTable([0, 0]),
        glyf=GlyfTable(b""),
        hmtx=HmtxTable([HMetric(advance_width=0, lsb=0)]),
    )
    path = parser._flags_to_path(
        contour_ends=[1],
        flags=[0, 0],  # two consecutive off-curve points
        xs=[0, 100],
        ys=[0, 0],
    )
    cmds = _commands(path)
    assert isinstance(cmds[0], MoveTo)
    assert isinstance(cmds[-1], ClosePath)
    assert cmds[0].x == pytest.approx(50.0)
    assert cmds[0].y == pytest.approx(0.0)
    assert any(isinstance(c, QuadraticTo) for c in cmds)
