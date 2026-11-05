"""CFF DICT parser and typed top/private dicts."""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from aspose_font._exceptions import FontParseException
from aspose_font._io import BinaryWriter
from aspose_font.cff.index import CffIndex


class TopDictOp:
    VERSION = 0
    NOTICE = 1
    FULL_NAME = 2
    FAMILY_NAME = 3
    WEIGHT = 4
    FONT_BBOX = 5
    CHARSET = 15
    ENCODING = 16
    CHARSTRINGS = 17
    PRIVATE = 18
    IS_FIXED_PITCH = (12, 1)
    ITALIC_ANGLE = (12, 2)
    UNDERLINE_POS = (12, 3)
    UNDERLINE_THICK = (12, 4)
    CHARSTRING_TYPE = (12, 6)
    FONT_MATRIX = (12, 7)


class PrivateDictOp:
    BLUE_VALUES = 6
    OTHER_BLUES = 7
    STD_HW = 10
    STD_VW = 11
    SUBRS = 19
    DEFAULT_WIDTH_X = 20
    NOMINAL_WIDTH_X = 21


@dataclass
class CffDict:
    _data: dict[int | tuple[int, int], list[int | float]] = field(default_factory=dict)

    @classmethod
    def from_bytes(cls, data: bytes) -> "CffDict":
        pos = 0
        stack: list[int | float] = []
        out: dict[int | tuple[int, int], list[int | float]] = {}
        size = len(data)

        while pos < size:
            b0 = data[pos]
            pos += 1
            if b0 <= 21:
                if b0 == 12:
                    if pos >= size:
                        raise FontParseException("Truncated CFF DICT operator")
                    op = (12, data[pos])
                    pos += 1
                else:
                    op = b0
                out[op] = stack.copy()
                stack.clear()
                continue

            if 32 <= b0 <= 246:
                stack.append(b0 - 139)
            elif 247 <= b0 <= 250:
                if pos >= size:
                    raise FontParseException("Truncated CFF DICT integer")
                stack.append((b0 - 247) * 256 + data[pos] + 108)
                pos += 1
            elif 251 <= b0 <= 254:
                if pos >= size:
                    raise FontParseException("Truncated CFF DICT integer")
                stack.append(-(b0 - 251) * 256 - data[pos] - 108)
                pos += 1
            elif b0 == 28:
                if pos + 2 > size:
                    raise FontParseException("Truncated CFF DICT int16")
                stack.append(int.from_bytes(data[pos : pos + 2], "big", signed=True))
                pos += 2
            elif b0 == 29:
                if pos + 4 > size:
                    raise FontParseException("Truncated CFF DICT int32")
                stack.append(int.from_bytes(data[pos : pos + 4], "big", signed=True))
                pos += 4
            elif b0 == 30:
                literal = []
                while True:
                    if pos >= size:
                        raise FontParseException("Truncated CFF DICT real")
                    b = data[pos]
                    pos += 1
                    for nib in (b >> 4, b & 0xF):
                        if nib == 0xF:
                            s = "".join(literal) or "0"
                            stack.append(float(s))
                            literal = None
                            break
                        if nib <= 9:
                            literal.append(str(nib))
                        elif nib == 0xA:
                            literal.append(".")
                        elif nib == 0xB:
                            literal.append("E")
                        elif nib == 0xC:
                            literal.append("E-")
                        elif nib == 0xE:
                            literal.append("-")
                        else:
                            raise FontParseException("Invalid CFF DICT real nibble")
                    if literal is None:
                        break
            else:
                raise FontParseException(f"Unsupported CFF DICT byte: {b0}")

        return cls(_data=out)

    def get(self, op: int | tuple[int, int], default=None):
        return self._data.get(op, default)

    def set(self, op: int | tuple[int, int], value: list[int | float]) -> None:
        self._data[op] = value

    def to_bytes(self) -> bytes:
        w = BinaryWriter()
        for op, operands in self._data.items():
            for operand in operands:
                _write_operand(w, operand)
            _write_operator(w, op)
        return w.to_bytes()


def _write_operator(w: BinaryWriter, op: int | tuple[int, int]) -> None:
    if isinstance(op, tuple):
        if len(op) != 2 or op[0] != 12:
            raise FontParseException(f"Unsupported CFF DICT operator: {op}")
        w.write_u8(12)
        w.write_u8(op[1])
        return
    if op < 0 or op > 21:
        raise FontParseException(f"Unsupported CFF DICT operator: {op}")
    w.write_u8(op)


def _write_operand(w: BinaryWriter, value: int | float) -> None:
    if isinstance(value, float):
        if not math.isfinite(value):
            raise FontParseException("CFF DICT real must be finite")
        _write_real(w, value)
        return
    _write_int(w, value)


def _write_int(w: BinaryWriter, value: int) -> None:
    if -107 <= value <= 107:
        w.write_u8(value + 139)
        return
    if 108 <= value <= 1131:
        n = value - 108
        w.write_u8((n // 256) + 247)
        w.write_u8(n % 256)
        return
    if -1131 <= value <= -108:
        n = -value - 108
        w.write_u8((n // 256) + 251)
        w.write_u8(n % 256)
        return
    if -32768 <= value <= 32767:
        w.write_u8(28)
        w.write_i16(value)
        return
    w.write_u8(29)
    w.write_i32(value)


def _write_real(w: BinaryWriter, value: float) -> None:
    s = format(value, ".12g")
    nibbles: list[int] = []
    i = 0
    while i < len(s):
        ch = s[i]
        if ch.isdigit():
            nibbles.append(int(ch))
        elif ch == ".":
            nibbles.append(0xA)
        elif ch in ("e", "E"):
            if i + 1 < len(s) and s[i + 1] == "-":
                nibbles.append(0xC)
                i += 1
            else:
                nibbles.append(0xB)
        elif ch == "-":
            nibbles.append(0xE)
        else:
            raise FontParseException(f"Unsupported CFF DICT real character: {ch}")
        i += 1

    nibbles.append(0xF)
    if len(nibbles) % 2 != 0:
        nibbles.append(0xF)

    w.write_u8(30)
    for i in range(0, len(nibbles), 2):
        w.write_u8((nibbles[i] << 4) | nibbles[i + 1])


def _sid_to_str(sid: int, string_index: CffIndex) -> str:
    from aspose_font.cff.charset import resolve_sid

    return resolve_sid(sid, string_index)


@dataclass
class TopDict:
    full_name: str = ""
    family_name: str = ""
    weight: str = ""
    version: str = ""
    font_bbox: tuple[int, int, int, int] = (0, 0, 0, 0)
    charstring_type: int = 2
    italic_angle: float = 0.0
    is_fixed_pitch: bool = False
    underline_position: int = -100
    underline_thickness: int = 50
    font_matrix: tuple[float, float, float, float, float, float] = (0.001, 0.0, 0.0, 0.001, 0.0, 0.0)
    charset_offset: int = 0
    encoding_offset: int = 0
    charstrings_offset: int = 0
    private_size: int = 0
    private_offset: int = 0
    _raw: CffDict = field(default_factory=CffDict)

    @classmethod
    def from_dict(cls, d: CffDict, string_index: CffIndex) -> "TopDict":
        def get_sid(op: int) -> str:
            vals = d.get(op, [])
            if not vals:
                return ""
            return _sid_to_str(int(vals[0]), string_index)

        bbox_vals = d.get(TopDictOp.FONT_BBOX, [0, 0, 0, 0])
        matrix_vals = d.get(TopDictOp.FONT_MATRIX, [0.001, 0, 0, 0.001, 0, 0])
        priv_vals = d.get(TopDictOp.PRIVATE, [0, 0])
        return cls(
            full_name=get_sid(TopDictOp.FULL_NAME),
            family_name=get_sid(TopDictOp.FAMILY_NAME),
            weight=get_sid(TopDictOp.WEIGHT),
            version=get_sid(TopDictOp.VERSION),
            font_bbox=tuple(int(v) for v in bbox_vals[:4]),
            charstring_type=int((d.get(TopDictOp.CHARSTRING_TYPE, [2]) or [2])[0]),
            italic_angle=float((d.get(TopDictOp.ITALIC_ANGLE, [0.0]) or [0.0])[0]),
            is_fixed_pitch=bool(int((d.get(TopDictOp.IS_FIXED_PITCH, [0]) or [0])[0])),
            underline_position=int((d.get(TopDictOp.UNDERLINE_POS, [-100]) or [-100])[0]),
            underline_thickness=int((d.get(TopDictOp.UNDERLINE_THICK, [50]) or [50])[0]),
            font_matrix=tuple(float(v) for v in matrix_vals[:6]),
            charset_offset=int((d.get(TopDictOp.CHARSET, [0]) or [0])[0]),
            encoding_offset=int((d.get(TopDictOp.ENCODING, [0]) or [0])[0]),
            charstrings_offset=int((d.get(TopDictOp.CHARSTRINGS, [0]) or [0])[0]),
            private_size=int(priv_vals[0]) if len(priv_vals) >= 1 else 0,
            private_offset=int(priv_vals[1]) if len(priv_vals) >= 2 else 0,
            _raw=d,
        )


@dataclass
class PrivateDict:
    default_width_x: int = 0
    nominal_width_x: int = 0
    std_hw: float = 0.0
    std_vw: float = 0.0
    subrs_offset: int = 0
    _raw: CffDict = field(default_factory=CffDict)

    @classmethod
    def from_dict(cls, d: CffDict) -> "PrivateDict":
        return cls(
            default_width_x=int((d.get(PrivateDictOp.DEFAULT_WIDTH_X, [0]) or [0])[0]),
            nominal_width_x=int((d.get(PrivateDictOp.NOMINAL_WIDTH_X, [0]) or [0])[0]),
            std_hw=float((d.get(PrivateDictOp.STD_HW, [0.0]) or [0.0])[0]),
            std_vw=float((d.get(PrivateDictOp.STD_VW, [0.0]) or [0.0])[0]),
            subrs_offset=int((d.get(PrivateDictOp.SUBRS, [0]) or [0])[0]),
            _raw=d,
        )
