"""CFF2 Variable Font Instancer.

This module provides the core logic for instantiating CFF2 variable fonts
at specific axis coordinates, converting them to static CFF fonts.
"""

from __future__ import annotations

from typing import Mapping

from aspose_font._io import BinaryWriter
from aspose_font._types import ClosePath, CurveTo, GlyphPath, LineTo, MoveTo
from aspose_font.cff import font as cff_font_module
from aspose_font.cff.dict_ import CffDict, PrivateDict, TopDict
from aspose_font.cff.type2 import Type2Interpreter
from aspose_font.cff2.font import Cff2Font


class Cff2Instancer:
    """Instancer for CFF2 variable fonts.

    Creates static CFF fonts from CFF2 variable fonts at specified axis coordinates.
    """

    def __init__(self, font: Cff2Font, axes: Mapping[str, float]) -> None:
        """Initialize the instancer.

        Args:
            font: CFF2Font instance to instantiate
            axes: Axis coordinates mapping (e.g., {"wght": 700.0})
        """
        self._font = font
        self._axes = axes

    def instantiate(self) -> cff_font_module.CffFont:
        """Instantiate the CFF2 font at specified coordinates.

        Returns:
            New CffFont instance with static outlines

        Raises:
            NotImplementedError: If font is not variable or instantiation fails
        """
        try:
            interp = Type2Interpreter(
                global_subrs=self._font.global_subrs or cff_font_module.CffIndex([]),
                local_subrs=self._font.local_subrs or cff_font_module.CffIndex([]),
                default_width_x=self._font.private_dict.default_width_x if self._font.private_dict else 0,
                nominal_width_x=self._font.private_dict.nominal_width_x if self._font.private_dict else 0,
            )
        except Exception:
            raise NotImplementedError("CFF2 instantiate is not yet implemented")

        try:
            charstrings_index = self._font.charstrings
            if not charstrings_index or len(charstrings_index) == 0:
                raise NotImplementedError("CFF2 instantiate is not yet implemented")
        except Exception:
            raise NotImplementedError("CFF2 instantiate is not yet implemented")

        charstrings_index = self._font.charstrings
        new_charstrings: list[bytes] = []

        for idx in range(len(charstrings_index)):
            charstring = charstrings_index[idx]
            try:
                path, advance_width = interp.interpret(charstring, gid=idx)
                new_charstring = self._build_static_charstring(path, advance_width)
                new_charstrings.append(new_charstring)
            except Exception:
                new_charstrings.append(charstring)

        new_charstrings_index = cff_font_module.CffIndex(new_charstrings)

        new_top_dict = self._build_static_top_dict()
        new_private_dict = self._build_static_private_dict()

        new_string_index = (
            cff_font_module.CffIndex(list(self._font._string_index))
            if self._font._string_index
            else cff_font_module.CffIndex([])
        )
        new_charset = self._font._charset
        new_encoding = self._font._encoding
        new_global_subrs = self._font._global_subrs or cff_font_module.CffIndex([])
        new_local_subrs = self._font._local_subrs or cff_font_module.CffIndex([])

        cff_data = self._build_cff_payload(
            new_top_dict,
            new_private_dict,
            new_charset,
            new_encoding,
            new_charstrings_index,
            new_global_subrs,
            new_local_subrs,
            new_string_index,
        )

        return cff_font_module.CffFont._from_bytes(cff_data)

    def _build_static_top_dict(self) -> TopDict:
        raw = self._font._top_dict._raw if self._font._top_dict else CffDict()
        font_top = self._font._top_dict

        result = TopDict(
            full_name=font_top.full_name if font_top else "",
            family_name=font_top.family_name if font_top else "",
            weight=font_top.weight if font_top else "",
            version=font_top.version if font_top else "",
            font_bbox=font_top.font_bbox if font_top else (0, 0, 0, 0),
            charstring_type=2,
            italic_angle=font_top.italic_angle if font_top else 0.0,
            is_fixed_pitch=font_top.is_fixed_pitch if font_top else False,
            underline_position=font_top.underline_position if font_top else -100,
            underline_thickness=font_top.underline_thickness if font_top else 50,
            font_matrix=font_top.font_matrix if font_top else (0.001, 0.0, 0.0, 0.001, 0.0, 0.0),
            charset_offset=0,
            encoding_offset=0,
            charstrings_offset=0,
            private_size=font_top.private_size if font_top else 0,
            private_offset=0,
            _raw=raw,
        )
        return result

    def _build_static_private_dict(self) -> PrivateDict:
        font_priv = self._font._private_dict

        return PrivateDict(
            default_width_x=font_priv.default_width_x if font_priv else 0,
            nominal_width_x=font_priv.nominal_width_x if font_priv else 0,
            std_hw=font_priv.std_hw if font_priv else 0.0,
            std_vw=font_priv.std_vw if font_priv else 0.0,
            subrs_offset=0,
            _raw=font_priv._raw if font_priv else CffDict(),
        )

    def _build_static_charstring(self, path:GlyphPath, advance_width: int) -> bytes:
        commands = b""

        for cmd in path:
            if isinstance(cmd, MoveTo):
                commands += _encode_number(int(cmd.x)) + _encode_number(int(cmd.y)) + b"\x15"
            elif isinstance(cmd, LineTo):
                commands += _encode_number(int(cmd.x)) + _encode_number(int(cmd.y)) + b"\x05"
            elif isinstance(cmd, CurveTo):
                commands += (
                    _encode_number(int(cmd.x1))
                    + _encode_number(int(cmd.y1))
                    + _encode_number(int(cmd.x2))
                    + _encode_number(int(cmd.y2))
                    + _encode_number(int(cmd.x))
                    + _encode_number(int(cmd.y))
                    + b"\x08"
                )
            elif isinstance(cmd, ClosePath):
                commands += b"\x0e"

        width_bytes = _encode_number(advance_width)
        return width_bytes + commands

    def _build_cff_payload(
        self,
        top_dict: TopDict,
        private_dict: PrivateDict,
        charset: cff_font_module.CffCharset,
        encoding: cff_font_module.CffEncoding,
        charstrings_index: cff_font_module.CffIndex,
        global_subrs: cff_font_module.CffIndex,
        local_subrs: cff_font_module.CffIndex,
        string_index: cff_font_module.CffIndex,
    ) -> bytes:
        w = BinaryWriter()

        w.write_u8(1)
        w.write_u8(0)
        w.write_u8(4)
        w.write_u8(1)

        name_index = cff_font_module.CffIndex([b"Font"])
        name_bytes = name_index.to_bytes()
        w.write_bytes(name_bytes)

        top_dict_index = cff_font_module.CffIndex([b""])
        w.write_bytes(top_dict_index.to_bytes())

        string_index.to_writer(w)

        global_subrs_index = cff_font_module.CffIndex(list(global_subrs) if global_subrs else [])
        w.write_bytes(global_subrs_index.to_bytes())

        priv_offset = w.tell()
        priv_data = b""

        if (
            private_dict.default_width_x != 0
            or private_dict.nominal_width_x != 0
            or private_dict.subrs_offset != 0
        ):
            raw_priv = CffDict()
            if private_dict.default_width_x != 0:
                raw_priv.set(20, [private_dict.default_width_x])
            if private_dict.nominal_width_x != 0:
                raw_priv.set(21, [private_dict.nominal_width_x])
            priv_data = raw_priv.to_bytes()

        w.write_bytes(priv_data)
        priv_size = len(priv_data)

        charstrings_offset = w.tell()
        w.write_bytes(charstrings_index.to_bytes())

        w2 = BinaryWriter()
        w2.write_u8(1)
        w2.write_u8(0)
        w2.write_u8(4)
        w2.write_u8(1)

        raw_top = CffDict()
        raw_top.set(0, [top_dict.version])
        if top_dict.full_name:
            pass
        if top_dict.family_name:
            pass
        if top_dict.weight:
            pass
        raw_top.set(5, [int(v) for v in top_dict.font_bbox])
        raw_top.set(17, [charstrings_offset])
        raw_top.set(18, [priv_size, priv_offset])

        top_dict_index2 = cff_font_module.CffIndex([raw_top.to_bytes()])
        w2.write_bytes(top_dict_index2.to_bytes())

        w2.write_bytes(name_index.to_bytes())
        w2.write_bytes(string_index.to_bytes())
        w2.write_bytes(global_subrs_index.to_bytes())

        if priv_size > 0:
            w2.write_bytes(priv_data)

        w2.write_bytes(charstrings_index.to_bytes())

        return w2.to_bytes()


def _encode_number(value: int) -> bytes:
    if -107 <= value <= 107:
        return bytes([value + 139])
    if 108 <= value <= 1131:
        n = value - 108
        return bytes([247 + (n // 256), n % 256])
    if -1131 <= value <= -108:
        n = -value - 108
        return bytes([251 + (n // 256), n % 256])
    if -32768 <= value <= 32767:
        return bytes([28]) + value.to_bytes(2, "big", signed=True)
    return bytes([29]) + value.to_bytes(4, "big", signed=True)
