"""CFF font parser and Font implementation."""

from __future__ import annotations

import re
from dataclasses import dataclass

from aspose_font._exceptions import (
    FontNotSupportedException,
    FontParseException,
    GlyphNotFoundException,
)
from aspose_font._font_base import Font, FontType, GlyphAccessor
from aspose_font._io import BinaryReader
from aspose_font._types import FontMetrics, Glyph, GlyphId, KernPair
from aspose_font.cff.charset import CffCharset
from aspose_font.cff.dict_ import CffDict, PrivateDict, TopDict
from aspose_font.cff.encoding import CffEncoding
from aspose_font.cff.index import CffIndex
from aspose_font.cff.type2 import Type2Interpreter
from aspose_font.serializer import CffSerializer


class _CffGlyphAccessor(GlyphAccessor):
    def __init__(self, font: "CffFont") -> None:
        super().__init__(font.encoding)
        self._font = font
        self._interp = Type2Interpreter(
            global_subrs=font.global_subrs,
            local_subrs=font.local_subrs,
            default_width_x=font.private_dict.default_width_x,
            nominal_width_x=font.private_dict.nominal_width_x,
        )
        self._cache: dict[int, Glyph] = {}

    def get_glyph_by_id(self, gid: GlyphId) -> Glyph:
        idx = int(gid)
        if idx < 0 or idx >= self._font.num_glyphs:
            raise GlyphNotFoundException(idx)
        cached = self._cache.get(idx)
        if cached is not None:
            return cached
        path, advance_width = self._interp.interpret(self._font.charstrings[idx], gid=idx)
        glyph = Glyph(
            glyph_id=gid,
            glyph_name=self._font.charset.name_for(idx),
            path=path if len(path) > 0 else None,
            advance_width=advance_width,
        )
        self._cache[idx] = glyph
        return glyph

    def get_all_glyph_ids(self) -> list[GlyphId]:
        return [GlyphId(i) for i in range(self._font.num_glyphs)]


@dataclass
class _CffHeader:
    major: int
    minor: int
    hdr_size: int
    off_size: int


class CffFont(Font):
    def __init__(
        self,
        data: bytes,
        top_dict: TopDict,
        private_dict: PrivateDict,
        charset: CffCharset,
        encoding: CffEncoding,
        charstrings: CffIndex,
        global_subrs: CffIndex,
        local_subrs: CffIndex,
        string_index: CffIndex,
    ) -> None:
        self._data = data
        self._top_dict = top_dict
        self._private_dict = private_dict
        self._charset = charset
        self._encoding = encoding
        self._charstrings = charstrings
        self._global_subrs = global_subrs
        self._local_subrs = local_subrs
        self._string_index = string_index
        self._glyph_accessor = _CffGlyphAccessor(self)

    @classmethod
    def _from_bytes(cls, data: bytes) -> "CffFont":
        payload = _extract_cff_payload(data)
        font = cls._from_reader(BinaryReader(payload))
        font._data = data
        return font

    @classmethod
    def _from_reader(cls, r: BinaryReader) -> "CffFont":
        data = r.read_bytes(r.remaining())
        rr = BinaryReader(data)
        base = 0

        header = _parse_header(rr)
        if header.major != 1:
            raise FontNotSupportedException(f"CFF version {header.major} not supported")
        rr.seek(base + header.hdr_size)

        CffIndex.from_reader(rr)
        top_dict_index = CffIndex.from_reader(rr)
        if len(top_dict_index) == 0:
            raise FontParseException("CFF Top DICT INDEX is empty")
        string_index = CffIndex.from_reader(rr)
        global_subrs = CffIndex.from_reader(rr)

        top_raw = top_dict_index[0]
        raw_top = CffDict.from_bytes(top_raw)
        top_dict = TopDict.from_dict(raw_top, string_index)

        if top_dict.charstrings_offset <= 0 or top_dict.charstrings_offset >= len(data):
            raise FontParseException("Invalid CFF CharStrings offset")

        csr = BinaryReader(data)
        csr.seek(top_dict.charstrings_offset)
        charstrings = CffIndex.from_reader(csr)

        num_glyphs = len(charstrings)
        if num_glyphs <= 0:
            raise FontParseException("CFF CharStrings INDEX is empty")

        charset = _parse_charset(data, top_dict.charset_offset, num_glyphs, string_index)
        encoding = _parse_encoding(data, top_dict.encoding_offset, num_glyphs, charset, string_index)

        private_dict = PrivateDict()
        local_subrs = CffIndex([])
        if top_dict.private_size > 0 and top_dict.private_offset > 0:
            pend = top_dict.private_offset + top_dict.private_size
            if pend > len(data):
                raise FontParseException("Private DICT out of range")
            private_bytes = data[top_dict.private_offset:pend]
            raw_priv = CffDict.from_bytes(private_bytes)
            private_dict = PrivateDict.from_dict(raw_priv)
            private_dict._raw = raw_priv
            if private_dict.subrs_offset > 0:
                sr = BinaryReader(data)
                sr.seek(top_dict.private_offset + private_dict.subrs_offset)
                local_subrs = CffIndex.from_reader(sr)

        return cls(
            data=data,
            top_dict=top_dict,
            private_dict=private_dict,
            charset=charset,
            encoding=encoding,
            charstrings=charstrings,
            global_subrs=global_subrs,
            local_subrs=local_subrs,
            string_index=string_index,
        )

    @property
    def font_type(self) -> FontType:
        return FontType.CFF

    @property
    def font_name(self) -> str:
        return self._top_dict.full_name or self._top_dict.family_name or ""

    @property
    def font_family(self) -> str:
        return self._top_dict.family_name or self._top_dict.full_name or ""

    @property
    def font_style(self) -> str:
        return self._top_dict.weight or "Regular"

    @property
    def num_glyphs(self) -> int:
        return len(self._charstrings)

    @property
    def metrics(self) -> FontMetrics:
        bbox = self._top_dict.font_bbox
        matrix = self._top_dict.font_matrix
        upm = int(round(1.0 / abs(matrix[0]))) if matrix and matrix[0] not in (0.0, 1.0) else 1000
        if upm <= 0:
            upm = 1000
        return FontMetrics(
            units_per_em=upm,
            ascender=bbox[3],
            descender=bbox[1],
            line_gap=0,
            advance_width_max=0,
            underline_position=self._top_dict.underline_position,
            underline_thickness=self._top_dict.underline_thickness,
        )

    @property
    def encoding(self):
        return self._encoding

    @property
    def glyph_accessor(self) -> GlyphAccessor:
        return self._glyph_accessor

    @property
    def top_dict(self) -> TopDict:
        return self._top_dict

    @property
    def private_dict(self) -> PrivateDict:
        return self._private_dict

    @property
    def charstrings(self) -> CffIndex:
        return self._charstrings

    @property
    def global_subrs(self) -> CffIndex:
        return self._global_subrs

    @property
    def local_subrs(self) -> CffIndex:
        return self._local_subrs

    @property
    def charset(self) -> CffCharset:
        return self._charset

    @property
    def string_index(self) -> CffIndex:
        return self._string_index

    def get_kern_pairs(self) -> list[KernPair]:
        return []


    def to_bytes(self, font_type: FontType | None = None) -> bytes:
        if font_type is not None and font_type != self.font_type:
            return super().to_bytes(font_type)
        return CffSerializer.serialize(self)


def _parse_header(r: BinaryReader) -> _CffHeader:
    major = r.read_u8()
    minor = r.read_u8()
    hdr_size = r.read_u8()
    off_size = r.read_u8()
    return _CffHeader(major, minor, hdr_size, off_size)


def _extract_cff_payload(data: bytes) -> bytes:
    if not data.startswith(b"%!PS"):
        return data

    marker = b"StartData"
    idx = data.find(marker)
    if idx < 0:
        return data

    # Find binary payload start right after the StartData line break.
    line_end = data.find(b"\n", idx)
    if line_end < 0:
        return data
    start = line_end + 1

    # If byte count is provided before StartData, respect it.
    line_start = data.rfind(b"\n", 0, idx)
    if line_start < 0:
        line_start = 0
    else:
        line_start += 1
    line = data[line_start:line_end]
    m = re.search(rb"(\d+)\s+StartData", line)
    if m:
        size = int(m.group(1))
        end = min(start + size, len(data))
        return data[start:end]
    return data[start:]


def _parse_charset(data: bytes, offset: int, num_glyphs: int, string_index: CffIndex) -> CffCharset:
    if offset == 0:
        return CffCharset.standard(num_glyphs)
    if offset in (1, 2):
        return CffCharset.standard(num_glyphs)
    if offset <= 0 or offset >= len(data):
        raise FontParseException("CFF charset offset out of range")
    r = BinaryReader(data)
    r.seek(offset)
    return CffCharset.from_reader(r, num_glyphs, string_index)


def _parse_encoding(
    data: bytes,
    offset: int,
    num_glyphs: int,
    charset: CffCharset,
    string_index: CffIndex,
) -> CffEncoding:
    if offset == 0:
        return CffEncoding.standard(charset)
    if offset == 1:
        return CffEncoding.expert(charset)
    if offset <= 0 or offset >= len(data):
        return CffEncoding({})
    r = BinaryReader(data)
    r.seek(offset)
    return CffEncoding.from_reader(r, num_glyphs, charset, string_index)
