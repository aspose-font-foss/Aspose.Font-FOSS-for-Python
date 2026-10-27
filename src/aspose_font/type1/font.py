"""Type1 font parser-backed Font implementation."""

from __future__ import annotations

from collections.abc import Iterable

from aspose_font._exceptions import GlyphNotFoundException
from aspose_font._font_base import Font, FontEncoding, FontType, GlyphAccessor
from aspose_font._types import FontMetrics, Glyph, GlyphId, KernPair
from aspose_font.serializer import Type1Serializer
from aspose_font.type1.afm import AfmData, parse_afm
from aspose_font.type1.charstring import Type1Interpreter
from aspose_font.type1.pfa import pfa_to_ps_stream
from aspose_font.type1.pfb import parse_pfb, pfb_to_ps_stream
from aspose_font.type1.ps_lexer import Type1FontData, parse_type1_ps


class _Type1Encoding(FontEncoding):
    def __init__(self, encoding: list[str], name_to_gid: dict[str, int]) -> None:
        self._encoding = encoding
        self._name_to_gid = name_to_gid

    def unicode_to_gid(self, codepoint: int) -> GlyphId:
        if codepoint < 0 or codepoint > 255:
            raise GlyphNotFoundException(codepoint)
        name = self._encoding[codepoint]
        gid = self._name_to_gid.get(name)
        if gid is None:
            raise GlyphNotFoundException(codepoint)
        return GlyphId(gid)

    def get_all_codepoints(self) -> list[int]:
        out: list[int] = []
        for i, name in enumerate(self._encoding):
            if name in self._name_to_gid:
                out.append(i)
        return out


class _Type1GlyphAccessor(GlyphAccessor):
    def __init__(self, font: "Type1Font") -> None:
        super().__init__(font.encoding)
        self._font = font
        self._interp = Type1Interpreter(font._font_data.subrs, len_iv=font._font_data.len_iv)
        self._cache: dict[int, Glyph] = {}

    def get_glyph_by_id(self, gid: GlyphId) -> Glyph:
        idx = int(gid)
        if idx < 0 or idx >= self._font.num_glyphs:
            raise GlyphNotFoundException(idx)
        cached = self._cache.get(idx)
        if cached is not None:
            return cached

        name = self._font._gid_to_name[idx]
        cs = self._font._font_data.charstrings.get(name)
        if cs is None:
            raise GlyphNotFoundException(idx)

        path, width = self._interp.interpret(cs)
        if self._font._afm is not None:
            metric = self._font._afm.glyph_metrics.get(name)
            if metric is not None:
                width = metric.advance_width

        glyph = Glyph(
            glyph_id=gid,
            glyph_name=name,
            path=path if len(path) > 0 else None,
            advance_width=width,
            lsb=0,
        )
        self._cache[idx] = glyph
        return glyph

    def get_all_glyph_ids(self) -> list[GlyphId]:
        return [GlyphId(i) for i in range(self._font.num_glyphs)]


class Type1Font(Font):
    def __init__(self, raw_data: bytes, font_data: Type1FontData, is_pfa: bool = False) -> None:
        self._raw_data = raw_data
        self._font_data = font_data
        self._is_pfa = is_pfa
        self._afm: AfmData | None = None

        self._gid_to_name = self._build_gid_order(font_data.charstrings.keys())
        self._name_to_gid = {name: i for i, name in enumerate(self._gid_to_name)}
        self._encoding_impl = _Type1Encoding(font_data.encoding, self._name_to_gid)
        self._glyph_accessor_impl = _Type1GlyphAccessor(self)

    @classmethod
    def _from_source(cls, data: bytes) -> "Type1Font":
        is_pfa = data.startswith(b"%!PS")
        if is_pfa:
            return cls._from_pfa(data)
        if data.startswith(b"\x80\x01"):
            return cls._from_pfb(data)
        return cls(data, parse_type1_ps(data), is_pfa=False)

    @classmethod
    def _from_pfb(cls, raw: bytes) -> "Type1Font":
        segs = parse_pfb(raw)
        ps = pfb_to_ps_stream(segs)
        data = parse_type1_ps(ps)
        return cls(raw, data, is_pfa=False)

    @classmethod
    def _from_pfa(cls, raw: bytes) -> "Type1Font":
        ps = pfa_to_ps_stream(raw)
        data = parse_type1_ps(ps)
        return cls(raw, data, is_pfa=True)

    @property
    def font_type(self) -> FontType:
        return FontType.TYPE1_PFA if self._is_pfa else FontType.TYPE1

    @property
    def font_name(self) -> str:
        if self._afm is not None and self._afm.font_name:
            return self._afm.font_name
        if self._font_data.font_name:
            return self._font_data.font_name
        return "Unknown Type1"

    @property
    def font_family(self) -> str:
        if self._afm is not None and self._afm.family_name:
            return self._afm.family_name
        if self._font_data.family_name:
            return self._font_data.family_name
        return self.font_name

    @property
    def font_style(self) -> str:
        if self._afm is not None and self._afm.weight:
            return self._afm.weight
        if self._font_data.weight:
            return self._font_data.weight
        return "Regular"

    @property
    def num_glyphs(self) -> int:
        return len(self._gid_to_name)

    @property
    def metrics(self) -> FontMetrics:
        if self._afm is not None:
            advance_width_max = 0
            if self._afm.glyph_metrics:
                advance_width_max = max(m.advance_width for m in self._afm.glyph_metrics.values())
            return FontMetrics(
                units_per_em=1000,
                ascender=int(self._afm.ascender),
                descender=int(self._afm.descender),
                line_gap=0,
                advance_width_max=advance_width_max,
                underline_position=self._afm.underline_position,
                underline_thickness=self._afm.underline_thickness,
            )

        bbox = self._font_data.font_bbox
        return FontMetrics(
            units_per_em=1000,
            ascender=bbox[3],
            descender=bbox[1],
            line_gap=0,
            advance_width_max=0,
            underline_position=self._font_data.underline_position,
            underline_thickness=self._font_data.underline_thickness,
        )

    @property
    def encoding(self) -> FontEncoding:
        return self._encoding_impl

    @property
    def glyph_accessor(self) -> GlyphAccessor:
        return self._glyph_accessor_impl

    def get_kern_pairs(self) -> list[KernPair]:
        if self._afm is None:
            return []
        result: list[KernPair] = []
        for name_l, name_r, value in self._afm.kern_pairs:
            gid_l = self._name_to_gid.get(name_l)
            gid_r = self._name_to_gid.get(name_r)
            if gid_l is not None and gid_r is not None:
                result.append(KernPair(GlyphId(gid_l), GlyphId(gid_r), value))
        return result


    def load_afm(self, path: str) -> None:
        self._afm = parse_afm(path)

    def to_bytes(self, font_type: FontType | None = None) -> bytes:
        if font_type is None:
            return Type1Serializer.serialize_pfa(self) if self._is_pfa else Type1Serializer.serialize_pfb(self)
        if font_type == FontType.TYPE1:
            return Type1Serializer.serialize_pfb(self)
        if font_type == FontType.TYPE1_PFA:
            return Type1Serializer.serialize_pfa(self)
        return super().to_bytes(font_type)

    @staticmethod
    def _build_gid_order(names: Iterable[str]) -> list[str]:
        uniq = sorted(set(str(n) for n in names if n))
        if ".notdef" in uniq:
            uniq.remove(".notdef")
            return [".notdef"] + uniq
        return uniq
