"""Type1 charstring interpreter."""

from __future__ import annotations

from dataclasses import dataclass, field

from aspose_font._exceptions import FontNotSupportedException, FontParseException
from aspose_font._types import ClosePath, CurveTo, GlyphPath, LineTo, MoveTo
from aspose_font.type1.eexec import charstring_decrypt_full

_SUBR_DEPTH_LIMIT = 10


@dataclass(slots=True)
class _T1State:
    stack: list[int | float] = field(default_factory=list)
    path: GlyphPath = field(default_factory=GlyphPath)
    current_x: float = 0.0
    current_y: float = 0.0
    side_bearing_x: float = 0.0
    advance_width: int = 0
    open_path: bool = False
    subr_depth: int = 0


class Type1Interpreter:
    def __init__(self, subrs: list[bytes], len_iv: int = 4) -> None:
        self._len_iv = len_iv
        self._subrs = [charstring_decrypt_full(s, len_iv) for s in subrs]

    def interpret(self, charstring: bytes) -> tuple[GlyphPath, int]:
        state = _T1State()
        data = charstring_decrypt_full(charstring, self._len_iv)
        self._run(data, state)
        if state.open_path:
            state.path.append(ClosePath())
            state.open_path = False
        return state.path, int(state.advance_width)

    def _run(self, data: bytes, state: _T1State) -> str:
        pos = 0
        size = len(data)
        while pos < size:
            b0 = data[pos]
            pos += 1

            if 32 <= b0 <= 246:
                state.stack.append(b0 - 139)
                continue
            if 247 <= b0 <= 250:
                if pos >= size:
                    raise FontParseException("Truncated Type1 number")
                state.stack.append((b0 - 247) * 256 + data[pos] + 108)
                pos += 1
                continue
            if 251 <= b0 <= 254:
                if pos >= size:
                    raise FontParseException("Truncated Type1 number")
                state.stack.append(-(b0 - 251) * 256 - data[pos] - 108)
                pos += 1
                continue
            if b0 == 255:
                if pos + 4 > size:
                    raise FontParseException("Truncated Type1 integer")
                state.stack.append(int.from_bytes(data[pos : pos + 4], "big", signed=True))
                pos += 4
                continue

            if b0 == 1:  # hstem
                state.stack.clear()
            elif b0 == 3:  # vstem
                state.stack.clear()
            elif b0 == 4:  # vmoveto
                if len(state.stack) != 1:
                    raise FontParseException("Invalid vmoveto operands")
                self._moveto(state, 0.0, float(state.stack[0]))
                state.stack.clear()
            elif b0 == 5:  # rlineto
                if len(state.stack) < 2 or (len(state.stack) % 2) != 0:
                    raise FontParseException("Invalid rlineto operands")
                vals = [float(v) for v in state.stack]
                state.stack.clear()
                for i in range(0, len(vals), 2):
                    self._lineto(state, vals[i], vals[i + 1])
            elif b0 == 6:  # hlineto
                if not state.stack:
                    raise FontParseException("Invalid hlineto operands")
                vals = [float(v) for v in state.stack]
                state.stack.clear()
                for dx in vals:
                    self._lineto(state, dx, 0.0)
            elif b0 == 7:  # vlineto
                if not state.stack:
                    raise FontParseException("Invalid vlineto operands")
                vals = [float(v) for v in state.stack]
                state.stack.clear()
                for dy in vals:
                    self._lineto(state, 0.0, dy)
            elif b0 == 8:  # rrcurveto
                if len(state.stack) < 6 or (len(state.stack) % 6) != 0:
                    raise FontParseException("Invalid rrcurveto operands")
                vals = [float(v) for v in state.stack]
                state.stack.clear()
                for i in range(0, len(vals), 6):
                    self._curveto(state, *vals[i : i + 6])
            elif b0 == 9:  # closepath
                self._close_if_open(state)
                state.stack.clear()
            elif b0 == 10:  # callsubr
                if len(state.stack) != 1:
                    raise FontParseException("Invalid callsubr operands")
                idx = int(state.stack.pop())
                if idx < 0 or idx >= len(self._subrs):
                    continue
                if state.subr_depth >= _SUBR_DEPTH_LIMIT:
                    raise FontParseException("Type1 subr recursion limit exceeded")
                state.subr_depth += 1
                result = self._run(self._subrs[idx], state)
                state.subr_depth -= 1
                if result == "return":
                    continue
            elif b0 == 11:  # return
                state.stack.clear()
                return "return"
            elif b0 == 12:  # escape
                if pos >= size:
                    raise FontParseException("Truncated Type1 escape operator")
                esc = data[pos]
                pos += 1
                if esc == 0:  # dotsection
                    state.stack.clear()
                elif esc == 1:  # vstem3
                    state.stack.clear()
                elif esc == 2:  # hstem3
                    state.stack.clear()
                elif esc == 6:  # seac
                    raise FontNotSupportedException("seac accent composite not supported")
                elif esc == 7:  # sbw
                    if len(state.stack) != 4:
                        raise FontParseException("Invalid sbw operands")
                    sbx, sby, wx, _wy = (float(v) for v in state.stack)
                    state.side_bearing_x = sbx
                    state.advance_width = int(wx)
                    state.current_x = sbx
                    state.current_y = sby
                    state.stack.clear()
                elif esc == 12:  # div
                    if len(state.stack) < 2:
                        raise FontParseException("Invalid div operands")
                    b = float(state.stack.pop())
                    a = float(state.stack.pop())
                    if b == 0:
                        raise FontParseException("Division by zero in Type1 div")
                    state.stack.append(a / b)
                elif esc == 16:  # callothersubr
                    if len(state.stack) < 2:
                        raise FontParseException("Invalid callothersubr operands")
                    n_args = int(state.stack.pop())
                    _subr_no = int(state.stack.pop())
                    if n_args > len(state.stack):
                        raise FontParseException("Invalid callothersubr arg count")
                    del state.stack[-n_args:]
                elif esc == 17:  # pop
                    state.stack.append(0)
                elif esc == 33:  # setcurrentpoint
                    if len(state.stack) != 2:
                        raise FontParseException("Invalid setcurrentpoint operands")
                    state.current_x = float(state.stack[0])
                    state.current_y = float(state.stack[1])
                    state.stack.clear()
                else:
                    raise FontParseException(f"Unsupported Type1 escape operator: {esc}")
            elif b0 == 13:  # hsbw
                if len(state.stack) != 2:
                    raise FontParseException("Invalid hsbw operands")
                sbx, wx = (float(v) for v in state.stack)
                state.side_bearing_x = sbx
                state.advance_width = int(wx)
                state.current_x = sbx
                state.stack.clear()
            elif b0 == 14:  # endchar
                state.stack.clear()
                return "endchar"
            elif b0 == 21:  # rmoveto
                if len(state.stack) != 2:
                    raise FontParseException("Invalid rmoveto operands")
                dx, dy = (float(v) for v in state.stack)
                self._moveto(state, dx, dy)
                state.stack.clear()
            elif b0 == 22:  # hmoveto
                if len(state.stack) != 1:
                    raise FontParseException("Invalid hmoveto operands")
                self._moveto(state, float(state.stack[0]), 0.0)
                state.stack.clear()
            else:
                raise FontParseException(f"Unsupported Type1 operator: {b0}")

        return "eof"

    def _close_if_open(self, state: _T1State) -> None:
        if state.open_path:
            state.path.append(ClosePath())
            state.open_path = False

    def _moveto(self, state: _T1State, dx: float, dy: float) -> None:
        self._close_if_open(state)
        state.current_x += dx
        state.current_y += dy
        state.path.append(MoveTo(state.current_x, state.current_y))
        state.open_path = True

    def _lineto(self, state: _T1State, dx: float, dy: float) -> None:
        state.current_x += dx
        state.current_y += dy
        state.path.append(LineTo(state.current_x, state.current_y))
        state.open_path = True

    def _curveto(
        self,
        state: _T1State,
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
