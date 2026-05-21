"""TTF OS/2 table parser."""

from __future__ import annotations

from dataclasses import dataclass

from aspose_font._io import BinaryReader


@dataclass
class Os2Table:
    version: int
    fs_type: int
    s_typo_ascender: int
    s_typo_descender: int
    s_typo_line_gap: int
    us_win_ascent: int
    us_win_descent: int
    fs_selection: int
    panose: bytes
    ach_vend_id: str
    _raw: bytes

    @classmethod
    def from_reader(cls, r: BinaryReader, table_length: int) -> "Os2Table":
        raw = r.read_bytes(table_length)
        rr = BinaryReader(raw)
        version = rr.read_u16()
        rr.read_i16()  # xAvgCharWidth
        rr.read_u16()  # usWeightClass
        rr.read_u16()  # usWidthClass
        fs_type = rr.read_u16()
        # ySubscript* (4), ySuperscript* (4), yStrikeout* (2), sFamilyClass (1)
        for _ in range(11):
            rr.read_i16()
        panose = rr.read_bytes(10)
        rr.read_u32()  # ulUnicodeRange1
        rr.read_u32()  # ulUnicodeRange2
        rr.read_u32()  # ulUnicodeRange3
        rr.read_u32()  # ulUnicodeRange4
        ach_vend_id = rr.read_tag()
        fs_selection = rr.read_u16()
        rr.read_u16()  # usFirstCharIndex
        rr.read_u16()  # usLastCharIndex
        s_typo_ascender = rr.read_i16()
        s_typo_descender = rr.read_i16()
        s_typo_line_gap = rr.read_i16()
        us_win_ascent = rr.read_u16()
        us_win_descent = rr.read_u16()
        return cls(
            version=version,
            fs_type=fs_type,
            s_typo_ascender=s_typo_ascender,
            s_typo_descender=s_typo_descender,
            s_typo_line_gap=s_typo_line_gap,
            us_win_ascent=us_win_ascent,
            us_win_descent=us_win_descent,
            fs_selection=fs_selection,
            panose=panose,
            ach_vend_id=ach_vend_id,
            _raw=raw,
        )

    def to_bytes(self) -> bytes:
        return self._raw
