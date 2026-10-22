"""Tests for SPEC-005 CFF glyph outline extraction (Type 2)."""

from __future__ import annotations

import pytest

from aspose_font import ClosePath, CurveTo, GlyphId, LineTo, MoveTo
from aspose_font._exceptions import FontParseException
from aspose_font.cff.index import CffIndex
from aspose_font.cff.type2 import Type2Interpreter


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
        elif isinstance(cmd, CurveTo):
            out.append(("C", cmd.x1, cmd.y1, cmd.x2, cmd.y2, cmd.x, cmd.y))
    return out


def _enc_num(n: int) -> bytes:
    if -107 <= n <= 107:
        return bytes([n + 139])
    if 108 <= n <= 1131:
        v = n - 108
        return bytes([247 + (v // 256), v % 256])
    if -1131 <= n <= -108:
        v = -n - 108
        return bytes([251 + (v // 256), v % 256])
    return bytes([28]) + int(n).to_bytes(2, "big", signed=True)


def test_notdef_glyph_cff(opensans_cff):
    glyph = opensans_cff.glyph_accessor.get_glyph_by_id(GlyphId(0))
    assert glyph.glyph_id == GlyphId(0)


def test_glyph_path_has_curveto(opensans_cff):
    gid = opensans_cff.encoding.unicode_to_gid(0x41)
    glyph = opensans_cff.glyph_accessor.get_glyph_by_id(gid)
    assert glyph.path is not None
    cmds = _commands(glyph.path)
    assert any(isinstance(c, MoveTo) for c in cmds)
    assert any(isinstance(c, CurveTo) for c in cmds)


def test_curveto_has_three_points(opensans_cff):
    gid = opensans_cff.encoding.unicode_to_gid(0x41)
    glyph = opensans_cff.glyph_accessor.get_glyph_by_id(gid)
    for cmd in _commands(glyph.path):
        if isinstance(cmd, CurveTo):
            assert isinstance(cmd.x1, float)
            assert isinstance(cmd.y1, float)
            assert isinstance(cmd.x2, float)
            assert isinstance(cmd.y2, float)
            assert isinstance(cmd.x, float)
            assert isinstance(cmd.y, float)


def test_glyph_path_ends_with_closepath(opensans_cff):
    gid = opensans_cff.encoding.unicode_to_gid(0x41)
    glyph = opensans_cff.glyph_accessor.get_glyph_by_id(gid)
    cmds = _commands(glyph.path)
    assert isinstance(cmds[-1], ClosePath)


def test_glyph_width_positive(opensans_cff):
    gid = opensans_cff.encoding.unicode_to_gid(0x41)
    glyph = opensans_cff.glyph_accessor.get_glyph_by_id(gid)
    assert glyph.advance_width > 0


def test_type2_rlineto():
    # 0 0 rmoveto, 50 0 rlineto, endchar
    cs = b"".join(
        [
            _enc_num(0),
            _enc_num(0),
            bytes([21]),
            _enc_num(50),
            _enc_num(0),
            bytes([5, 14]),
        ]
    )
    interp = Type2Interpreter(CffIndex([]), CffIndex([]), default_width_x=500, nominal_width_x=0)
    path, width = interp.interpret(cs)
    cmds = _commands(path)
    assert width == 500
    assert isinstance(cmds[0], MoveTo)
    assert isinstance(cmds[1], LineTo)
    assert cmds[1].x == pytest.approx(50.0)
    assert isinstance(cmds[-1], ClosePath)


def test_type2_width_extraction():
    # 50 is width; 0 0 rmoveto.
    cs = b"".join([_enc_num(50), _enc_num(0), _enc_num(0), bytes([21, 14])])
    interp = Type2Interpreter(CffIndex([]), CffIndex([]), default_width_x=500, nominal_width_x=400)
    _, width = interp.interpret(cs)
    assert width == 450


def test_type2_subr_inline_equivalent():
    # Main: 0 0 rmoveto, callsubr(0), endchar. Subr0: 50 0 rlineto, return
    main = b"".join([_enc_num(0), _enc_num(0), bytes([21]), _enc_num(-107), bytes([10, 14])])
    subr0 = b"".join([_enc_num(50), _enc_num(0), bytes([5, 11])])
    interp_subr = Type2Interpreter(CffIndex([]), CffIndex([subr0]), default_width_x=500, nominal_width_x=0)
    path_subr, _ = interp_subr.interpret(main)

    inlined = b"".join([_enc_num(0), _enc_num(0), bytes([21]), _enc_num(50), _enc_num(0), bytes([5, 14])])
    interp_inline = Type2Interpreter(CffIndex([]), CffIndex([]), default_width_x=500, nominal_width_x=0)
    path_inline, _ = interp_inline.interpret(inlined)
    assert _signature(path_subr) == _signature(path_inline)


def test_type2_invalid_subr_index():
    cs = b"".join([_enc_num(0), _enc_num(0), bytes([21]), _enc_num(0), bytes([10, 14])])
    interp = Type2Interpreter(CffIndex([]), CffIndex([]), default_width_x=500, nominal_width_x=0)
    with pytest.raises(FontParseException):
        interp.interpret(cs)


def test_type2_subr_depth_limit():
    # Subr0 recursively calls itself.
    subr0 = b"".join([_enc_num(-107), bytes([10, 11])])
    main = b"".join([_enc_num(-107), bytes([10, 14])])
    interp = Type2Interpreter(CffIndex([]), CffIndex([subr0]), default_width_x=500, nominal_width_x=0)
    with pytest.raises(FontParseException):
        interp.interpret(main)


def test_type2_stack_limit():
    cs = (bytes([139]) * 514) + bytes([14])
    interp = Type2Interpreter(CffIndex([]), CffIndex([]), default_width_x=500, nominal_width_x=0)
    with pytest.raises(FontParseException):
        interp.interpret(cs)
