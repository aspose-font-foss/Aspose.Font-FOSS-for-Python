"""Type 2 charstring interpreter for CFF glyph outlines."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from aspose_font._exceptions import FontParseException
from aspose_font._types import ClosePath, CurveTo, GlyphPath, LineTo, MoveTo
from aspose_font.cff.index import CffIndex

_LOG = logging.getLogger(__name__)
_STACK_LIMIT = 513
_SUBR_DEPTH_LIMIT = 10


@dataclass
class _InterpState:
    stack: list[int | float] = field(default_factory=list)
    path: GlyphPath = field(default_factory=GlyphPath)
    current_x: float = 0.0
    current_y: float = 0.0
    width: int | None = None
    stem_count: int = 0
    open_path: bool = False
    subr_depth: int = 0
    gid: int = 0


class Type2Interpreter:
    """Interprets Type 2 charstrings into GlyphPath commands."""

    def __init__(
        self,
        global_subrs: CffIndex,
        local_subrs: CffIndex,
        default_width_x: int,
        nominal_width_x: int,
    ) -> None:
        self._global_subrs = global_subrs
        self._local_subrs = local_subrs
        self._default_width_x = default_width_x
        self._nominal_width_x = nominal_width_x

    def interpret(self, charstring: bytes, gid: int = 0) -> tuple[GlyphPath, int]:
        state = _InterpState(gid=gid)
        result = self._run(charstring, state)
        if result != "endchar":
            self._endchar(state)
        width = state.width if state.width is not None else self._default_width_x
        return state.path, int(width)

    def _run(self, data: bytes, state: _InterpState) -> str:
        pos = 0
        size = len(data)
        while pos < size:
            b0 = data[pos]
            pos += 1

            if b0 == 28:
                if pos + 2 > size:
                    raise FontParseException(f"Truncated Type2 shortint in GID {state.gid}")
                self._push(int.from_bytes(data[pos : pos + 2], "big", signed=True), state)
                pos += 2
                continue
            if b0 == 255:
                if pos + 4 > size:
                    raise FontParseException(f"Truncated Type2 fixed number in GID {state.gid}")
                raw = int.from_bytes(data[pos : pos + 4], "big", signed=True)
                self._push(raw / 65536.0, state)
                pos += 4
                continue
            if 32 <= b0 <= 246:
                self._push(b0 - 139, state)
                continue
            if 247 <= b0 <= 250:
                if pos >= size:
                    raise FontParseException(f"Truncated Type2 number in GID {state.gid}")
                self._push((b0 - 247) * 256 + data[pos] + 108, state)
                pos += 1
                continue
            if 251 <= b0 <= 254:
                if pos >= size:
                    raise FontParseException(f"Truncated Type2 number in GID {state.gid}")
                self._push(-(b0 - 251) * 256 - data[pos] - 108, state)
                pos += 1
                continue

            if b0 == 1:
                self._hstem(state)
            elif b0 == 3:
                self._vstem(state)
            elif b0 == 4:
                self._vmoveto(state)
            elif b0 == 5:
                self._rlineto(state)
            elif b0 == 6:
                self._hlineto(state)
            elif b0 == 7:
                self._vlineto(state)
            elif b0 == 8:
                self._rrcurveto(state)
            elif b0 == 10:
                self._callsubr(state)
            elif b0 == 11:
                return "return"
            elif b0 == 12:
                if pos >= size:
                    raise FontParseException(f"Truncated Type2 escape operator in GID {state.gid}")
                esc = data[pos]
                pos += 1
                if esc == 3:
                    self._and(state)
                elif esc == 6:
                    self._seac(state)
                elif esc == 34:
                    self._hflex(state)
                elif esc == 35:
                    self._flex(state)
                elif esc == 36:
                    self._hflex1(state)
                elif esc == 37:
                    self._flex1(state)
                else:
                    _LOG.warning("Unknown Type2 escape operator %s in GID %s", esc, state.gid)
                    raise FontParseException(f"Unknown Type2 escape operator {esc} in GID {state.gid}")
            elif b0 == 14:
                self._endchar(state)
                return "endchar"
            elif b0 == 18:
                self._hstemhm(state)
            elif b0 == 19:
                pos = self._hintmask(state, data, pos)
            elif b0 == 20:
                pos = self._cntrmask(state, data, pos)
            elif b0 == 21:
                self._rmoveto(state)
            elif b0 == 22:
                self._hmoveto(state)
            elif b0 == 23:
                self._vstemhm(state)
            elif b0 == 24:
                self._rcurveline(state)
            elif b0 == 25:
                self._rlinecurve(state)
            elif b0 == 26:
                self._vvcurveto(state)
            elif b0 == 27:
                self._hhcurveto(state)
            elif b0 == 29:
                self._callgsubr(state)
            elif b0 == 30:
                self._vhcurveto(state)
            elif b0 == 31:
                self._hvcurveto(state)
            else:
                _LOG.warning("Unknown Type2 operator %s in GID %s", b0, state.gid)
                raise FontParseException(f"Unknown Type2 operator {b0} in GID {state.gid}")

        return "eof"

    def _push(self, value: int | float, state: _InterpState) -> None:
        state.stack.append(value)
        if len(state.stack) > _STACK_LIMIT:
            raise FontParseException(f"Type2 stack overflow in GID {state.gid}")

    def _close_if_open(self, state: _InterpState) -> None:
        if state.open_path:
            state.path.append(ClosePath())
            state.open_path = False

    def _moveto(self, state: _InterpState, dx: float, dy: float) -> None:
        self._close_if_open(state)
        state.current_x += dx
        state.current_y += dy
        state.path.append(MoveTo(state.current_x, state.current_y))
        state.open_path = True

    def _extract_width(self, state: _InterpState, expected: int) -> None:
        if state.width is None and len(state.stack) == expected + 1:
            state.width = int(state.stack.pop(0)) + self._nominal_width_x

    def _extract_stem_width(self, state: _InterpState) -> None:
        if state.width is None and (len(state.stack) % 2) == 1:
            state.width = int(state.stack.pop(0)) + self._nominal_width_x

    def _consume_stems(self, state: _InterpState) -> None:
        if len(state.stack) % 2 != 0:
            raise FontParseException(f"Invalid Type2 stem operand count in GID {state.gid}")
        state.stem_count += len(state.stack) // 2
        state.stack.clear()

    def _line_to(self, state: _InterpState, dx: float, dy: float) -> None:
        state.current_x += dx
        state.current_y += dy
        state.path.append(LineTo(state.current_x, state.current_y))
        state.open_path = True

    def _curve_to(
        self,
        state: _InterpState,
        dx1: float,
        dy1: float,
        dx2: float,
        dy2: float,
        dx3: float,
        dy3: float,
    ) -> None:
        x1 = state.current_x + dx1
        y1 = state.current_y + dy1
        x2 = x1 + dx2
        y2 = y1 + dy2
        x3 = x2 + dx3
        y3 = y2 + dy3
        state.path.append(CurveTo(x1, y1, x2, y2, x3, y3))
        state.current_x = x3
        state.current_y = y3
        state.open_path = True

    def _rmoveto(self, state: _InterpState) -> None:
        self._extract_width(state, 2)
        if len(state.stack) != 2:
            raise FontParseException(f"Invalid rmoveto operands in GID {state.gid}")
        dx, dy = (float(v) for v in state.stack)
        state.stack.clear()
        self._moveto(state, dx, dy)

    def _hmoveto(self, state: _InterpState) -> None:
        self._extract_width(state, 1)
        if len(state.stack) != 1:
            raise FontParseException(f"Invalid hmoveto operands in GID {state.gid}")
        dx = float(state.stack[0])
        state.stack.clear()
        self._moveto(state, dx, 0.0)

    def _vmoveto(self, state: _InterpState) -> None:
        self._extract_width(state, 1)
        if len(state.stack) != 1:
            raise FontParseException(f"Invalid vmoveto operands in GID {state.gid}")
        dy = float(state.stack[0])
        state.stack.clear()
        self._moveto(state, 0.0, dy)

    def _rlineto(self, state: _InterpState) -> None:
        if len(state.stack) < 2 or (len(state.stack) % 2) != 0:
            raise FontParseException(f"Invalid rlineto operands in GID {state.gid}")
        vals = [float(v) for v in state.stack]
        state.stack.clear()
        for i in range(0, len(vals), 2):
            self._line_to(state, vals[i], vals[i + 1])

    def _hlineto(self, state: _InterpState) -> None:
        if not state.stack:
            raise FontParseException(f"Invalid hlineto operands in GID {state.gid}")
        vals = [float(v) for v in state.stack]
        state.stack.clear()
        horizontal = True
        for v in vals:
            if horizontal:
                self._line_to(state, v, 0.0)
            else:
                self._line_to(state, 0.0, v)
            horizontal = not horizontal

    def _vlineto(self, state: _InterpState) -> None:
        if not state.stack:
            raise FontParseException(f"Invalid vlineto operands in GID {state.gid}")
        vals = [float(v) for v in state.stack]
        state.stack.clear()
        vertical = True
        for v in vals:
            if vertical:
                self._line_to(state, 0.0, v)
            else:
                self._line_to(state, v, 0.0)
            vertical = not vertical

    def _rrcurveto(self, state: _InterpState) -> None:
        if len(state.stack) < 6 or (len(state.stack) % 6) != 0:
            raise FontParseException(f"Invalid rrcurveto operands in GID {state.gid}")
        vals = [float(v) for v in state.stack]
        state.stack.clear()
        for i in range(0, len(vals), 6):
            self._curve_to(state, *vals[i : i + 6])

    def _hhcurveto(self, state: _InterpState) -> None:
        vals = [float(v) for v in state.stack]
        state.stack.clear()
        if len(vals) < 4:
            raise FontParseException(f"Invalid hhcurveto operands in GID {state.gid}")
        idx = 0
        dy1 = 0.0
        if len(vals) % 4 == 1:
            dy1 = vals[0]
            idx = 1
        first = True
        while idx + 3 < len(vals):
            dx1, dx2, dy2, dx3 = vals[idx : idx + 4]
            idx += 4
            self._curve_to(state, dx1, dy1 if first else 0.0, dx2, dy2, dx3, 0.0)
            first = False

    def _vvcurveto(self, state: _InterpState) -> None:
        vals = [float(v) for v in state.stack]
        state.stack.clear()
        if len(vals) < 4:
            raise FontParseException(f"Invalid vvcurveto operands in GID {state.gid}")
        idx = 0
        dx1 = 0.0
        if len(vals) % 4 == 1:
            dx1 = vals[0]
            idx = 1
        first = True
        while idx + 3 < len(vals):
            dy1, dx2, dy2, dy3 = vals[idx : idx + 4]
            idx += 4
            self._curve_to(state, dx1 if first else 0.0, dy1, dx2, dy2, 0.0, dy3)
            first = False

    def _hvcurveto(self, state: _InterpState) -> None:
        vals = [float(v) for v in state.stack]
        state.stack.clear()
        i = 0
        horizontal = True
        while i + 3 < len(vals):
            rem = len(vals) - i
            if horizontal:
                dx1, dx2, dy2, dy3 = vals[i : i + 4]
                i += 4
                dx3 = vals[i] if rem == 5 else 0.0
                if rem == 5:
                    i += 1
                self._curve_to(state, dx1, 0.0, dx2, dy2, dx3, dy3)
            else:
                dy1, dx2, dy2, dx3 = vals[i : i + 4]
                i += 4
                dy3 = vals[i] if rem == 5 else 0.0
                if rem == 5:
                    i += 1
                self._curve_to(state, 0.0, dy1, dx2, dy2, dx3, dy3)
            horizontal = not horizontal

    def _vhcurveto(self, state: _InterpState) -> None:
        vals = [float(v) for v in state.stack]
        state.stack.clear()
        i = 0
        horizontal = False
        while i + 3 < len(vals):
            rem = len(vals) - i
            if horizontal:
                dx1, dx2, dy2, dy3 = vals[i : i + 4]
                i += 4
                dx3 = vals[i] if rem == 5 else 0.0
                if rem == 5:
                    i += 1
                self._curve_to(state, dx1, 0.0, dx2, dy2, dx3, dy3)
            else:
                dy1, dx2, dy2, dx3 = vals[i : i + 4]
                i += 4
                dy3 = vals[i] if rem == 5 else 0.0
                if rem == 5:
                    i += 1
                self._curve_to(state, 0.0, dy1, dx2, dy2, dx3, dy3)
            horizontal = not horizontal

    def _rcurveline(self, state: _InterpState) -> None:
        vals = [float(v) for v in state.stack]
        state.stack.clear()
        if len(vals) < 8 or ((len(vals) - 2) % 6) != 0:
            raise FontParseException(f"Invalid rcurveline operands in GID {state.gid}")
        end = len(vals) - 2
        for i in range(0, end, 6):
            self._curve_to(state, *vals[i : i + 6])
        self._line_to(state, vals[-2], vals[-1])

    def _rlinecurve(self, state: _InterpState) -> None:
        vals = [float(v) for v in state.stack]
        state.stack.clear()
        if len(vals) < 8 or ((len(vals) - 6) % 2) != 0:
            raise FontParseException(f"Invalid rlinecurve operands in GID {state.gid}")
        end = len(vals) - 6
        for i in range(0, end, 2):
            self._line_to(state, vals[i], vals[i + 1])
        self._curve_to(state, *vals[-6:])

    def _flex(self, state: _InterpState) -> None:
        vals = [float(v) for v in state.stack]
        state.stack.clear()
        if len(vals) != 13:
            raise FontParseException(f"Invalid flex operands in GID {state.gid}")
        self._curve_to(state, *vals[0:6])
        self._curve_to(state, *vals[6:12])

    def _hflex(self, state: _InterpState) -> None:
        vals = [float(v) for v in state.stack]
        state.stack.clear()
        if len(vals) != 7:
            raise FontParseException(f"Invalid hflex operands in GID {state.gid}")
        dx1, dx2, dy2, dx3, dx4, dx5, dx6 = vals
        self._curve_to(state, dx1, 0.0, dx2, dy2, dx3, 0.0)
        self._curve_to(state, dx4, 0.0, dx5, -dy2, dx6, 0.0)

    def _hflex1(self, state: _InterpState) -> None:
        vals = [float(v) for v in state.stack]
        state.stack.clear()
        if len(vals) != 9:
            raise FontParseException(f"Invalid hflex1 operands in GID {state.gid}")
        dx1, dy1, dx2, dy2, dx3, dx4, dx5, dy5, dx6 = vals
        self._curve_to(state, dx1, dy1, dx2, dy2, dx3, 0.0)
        self._curve_to(state, dx4, 0.0, dx5, dy5, dx6, -(dy1 + dy2 + dy5))

    def _flex1(self, state: _InterpState) -> None:
        vals = [float(v) for v in state.stack]
        state.stack.clear()
        if len(vals) != 11:
            raise FontParseException(f"Invalid flex1 operands in GID {state.gid}")
        dx1, dy1, dx2, dy2, dx3, dy3, dx4, dy4, dx5, dy5, d6 = vals
        sum_x = dx1 + dx2 + dx3 + dx4 + dx5
        sum_y = dy1 + dy2 + dy3 + dy4 + dy5
        if abs(sum_x) > abs(sum_y):
            dx6, dy6 = d6, -sum_y
        else:
            dx6, dy6 = -sum_x, d6
        self._curve_to(state, dx1, dy1, dx2, dy2, dx3, dy3)
        self._curve_to(state, dx4, dy4, dx5, dy5, dx6, dy6)

    def _subr_bias(self, count: int) -> int:
        if count < 1240:
            return 107
        if count < 33900:
            return 1131
        return 32768

    def _callsubr(self, state: _InterpState) -> None:
        self._call_subroutine(state, self._local_subrs, "subr")

    def _callgsubr(self, state: _InterpState) -> None:
        self._call_subroutine(state, self._global_subrs, "gsubr")

    def _call_subroutine(self, state: _InterpState, table: CffIndex, label: str) -> None:
        if not state.stack:
            raise FontParseException(f"Missing {label} index in GID {state.gid}")
        if state.subr_depth >= _SUBR_DEPTH_LIMIT:
            raise FontParseException(f"Type2 subr depth limit at GID {state.gid}")
        index = int(state.stack.pop()) + self._subr_bias(len(table))
        if index < 0 or index >= len(table):
            raise FontParseException(f"Invalid subr index {index} in GID {state.gid}")
        state.subr_depth += 1
        try:
            self._run(table[index], state)
        finally:
            state.subr_depth -= 1

    def _hstem(self, state: _InterpState) -> None:
        self._extract_stem_width(state)
        self._consume_stems(state)

    def _vstem(self, state: _InterpState) -> None:
        self._extract_stem_width(state)
        self._consume_stems(state)

    def _hstemhm(self, state: _InterpState) -> None:
        self._extract_stem_width(state)
        self._consume_stems(state)

    def _vstemhm(self, state: _InterpState) -> None:
        self._extract_stem_width(state)
        self._consume_stems(state)

    def _hintmask(self, state: _InterpState, data: bytes, pos: int) -> int:
        self._extract_stem_width(state)
        self._consume_stems(state)
        mask_bytes = (state.stem_count + 7) // 8
        end = pos + mask_bytes
        if end > len(data):
            raise FontParseException(f"Truncated hintmask in GID {state.gid}")
        return end

    def _cntrmask(self, state: _InterpState, data: bytes, pos: int) -> int:
        self._extract_stem_width(state)
        self._consume_stems(state)
        mask_bytes = (state.stem_count + 7) // 8
        end = pos + mask_bytes
        if end > len(data):
            raise FontParseException(f"Truncated cntrmask in GID {state.gid}")
        return end

    def _endchar(self, state: _InterpState) -> None:
        if state.width is None and state.stack:
            state.width = int(state.stack.pop(0)) + self._nominal_width_x
        state.stack.clear()
        self._close_if_open(state)

    def _seac(self, state: _InterpState) -> None:
        # Legacy Type 1 accent composition; keep outline generation deterministic.
        self._endchar(state)

    def _and(self, state: _InterpState) -> None:
        if len(state.stack) < 2:
            raise FontParseException(f"Invalid 'and' operands in GID {state.gid}")
        b = state.stack.pop()
        a = state.stack.pop()
        self._push(1 if a and b else 0, state)
