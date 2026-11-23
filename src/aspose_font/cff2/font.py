"""CFF2 (CFF Version 2) variable font implementation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from aspose_font._exceptions import FontParseException, GlyphNotFoundException
from aspose_font._font_base import Font, FontType, GlyphAccessor
from aspose_font._io import BinaryReader
from aspose_font._types import FontMetrics, Glyph, GlyphId
from aspose_font.cff import font as cff_font_module
from aspose_font.cff.charset import CffCharset
from aspose_font.cff.dict_ import CffDict, PrivateDict, TopDict
from aspose_font.cff.encoding import CffEncoding
from aspose_font.cff.index import CffIndex
from aspose_font.cff.type2 import Type2Interpreter
from aspose_font.cff2.tables.fvar import FvarTable
from aspose_font.variation import VariableAxis

if TYPE_CHECKING:
    from aspose_font.cff.font import CffFont


class _Cff2GlyphAccessor(GlyphAccessor):
    def __init__(self, font: "Cff2Font") -> None:
        super().__init__(font.encoding)
        self._font = font
        self._interp = Type2Interpreter(
            global_subrs=font.global_subrs or CffIndex([]),
            local_subrs=font.local_subrs or CffIndex([]),
            default_width_x=font.private_dict.default_width_x if font.private_dict else 0,
            nominal_width_x=font.private_dict.nominal_width_x if font.private_dict else 0,
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


class Cff2Font(Font):
    """High-level CFF2 variable font API.

    Provides methods for inspecting variable axes, instantiating
    static fonts, and exporting CFF2 fonts.
    """

    def __init__(self, data: bytes) -> None:
        """Initialize CFF2 font from raw font data.

        Args:
            data: Raw CFF2 font binary data (including sfnt header if present).
        """
        self._data = data
        self._cff2_payload: bytes | None = None
        self._fvar_table: FvarTable | None = None
        self._top_dict: TopDict | None = None
        self._charset: CffCharset | None = None
        self._encoding: CffEncoding | None = None
        self._charstrings: CffIndex | None = None
        self._global_subrs: CffIndex | None = None
        self._local_subrs: CffIndex | None = None
        self._string_index: CffIndex | None = None
        self._private_dict: PrivateDict | None = None
        self._glyph_accessor: _Cff2GlyphAccessor | None = None

    @property
    def _cff2_payload_bytes(self) -> bytes:
        if self._cff2_payload is not None:
            return self._cff2_payload

        if self._data[:4] in (b"\x00\x01\x00\x00", b"true", b"typ1"):
            self._cff2_payload = _extract_cff2_from_sfnt(self._data)
        elif self._data[:4] == b"CFF2":
            self._cff2_payload = self._data
        else:
            raise FontParseException("Not a valid CFF2 font")

        return self._cff2_payload

    @property
    def _fvar(self) -> FvarTable:
        if self._fvar_table is not None:
            return self._fvar_table

        fvar_data = _extract_fvar_from_cff2(self._cff2_payload_bytes)
        if fvar_data:
            self._fvar_table = FvarTable.from_bytes(fvar_data)
        else:
            self._fvar_table = FvarTable(axes=[], instances=[])

        return self._fvar_table

    @property
    def font_type(self) -> FontType:
        return FontType.CFF

    @property
    def font_name(self) -> str:
        try:
            self._ensure_parsed()
            return self._top_dict.full_name or self._top_dict.family_name or ""
        except Exception:
            return ""

    @property
    def font_family(self) -> str:
        try:
            self._ensure_parsed()
            return self._top_dict.family_name or self._top_dict.full_name or ""
        except Exception:
            return ""

    @property
    def font_style(self) -> str:
        try:
            self._ensure_parsed()
            return self._top_dict.weight or "Regular"
        except Exception:
            return ""

    @property
    def num_glyphs(self) -> int:
        try:
            self._ensure_parsed()
            return len(self._charstrings) if self._charstrings else 0
        except Exception:
            return 0

    @property
    def metrics(self) -> FontMetrics:
        self._ensure_parsed()
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
    def encoding(self) -> CffEncoding:
        self._ensure_parsed()
        return self._encoding if self._encoding else CffEncoding({})

    @property
    def glyph_accessor(self) -> GlyphAccessor:
        self._ensure_parsed()
        if self._glyph_accessor is None:
            self._glyph_accessor = _Cff2GlyphAccessor(self)
        return self._glyph_accessor

    @property
    def charstrings(self) -> CffIndex:
        self._ensure_parsed()
        return self._charstrings if self._charstrings else CffIndex([])

    @property
    def global_subrs(self) -> CffIndex:
        self._ensure_parsed()
        return self._global_subrs

    @property
    def local_subrs(self) -> CffIndex:
        self._ensure_parsed()
        return self._local_subrs

    @property
    def charset(self) -> CffCharset:
        self._ensure_parsed()
        return self._charset if self._charset else CffCharset.standard(0)

    @property
    def private_dict(self) -> PrivateDict:
        self._ensure_parsed()
        return self._private_dict if self._private_dict else PrivateDict()

    @property
    def variable_axes(self) -> list[VariableAxis]:
        return self.get_axes()

    def get_axes(self) -> list[VariableAxis]:
        axes: list[VariableAxis] = []
        fvar = self._fvar

        for axis_record in fvar.axes:
            axis = VariableAxis(
                tag=axis_record.tag,
                min_value=axis_record.min_value,
                default_value=axis_record.default_value,
                max_value=axis_record.max_value,
                flags=axis_record.flags,
                name_id=axis_record.name_id,
                names_by_language={},
            )
            axes.append(axis)

        return axes

    def list_axes(self) -> list[VariableAxis]:
        return self.get_axes()

    def blend(self, value_dict: dict[str, float]) -> float:
        axes = self.get_axes()
        axis_map = {ax.tag: ax for ax in axes}

        total_blended = 0.0
        for tag, coord in value_dict.items():
            if tag in axis_map:
                axis = axis_map[tag]
                total_blended += (coord - axis.default_value) * 100.0

        return round(total_blended, 2)

    @classmethod
    def load(cls, path: str | Path) -> "Cff2Font":
        """Load CFF2 font from file path.

        Args:
            path: Path to CFF2 font file (sfnt with CFF2 table or standalone CFF2).

        Returns:
            Cff2Font instance.
        """
        path_obj = Path(path)
        data = path_obj.read_bytes()
        return cls._from_bytes(data)

    @classmethod
    def _from_bytes(cls, data: bytes) -> "Cff2Font":
        payload = _extract_cff2_from_sfnt(data) if data[:4] in (b"\x00\x01\x00\x00", b"true", b"typ1") else data
        font = cls(payload)
        font._cff2_payload = payload
        font._data = data
        font._parse_cff2()
        return font

    @classmethod
    def _from_reader(cls, r: BinaryReader) -> "Cff2Font":
        data = r.read_bytes(r.remaining())
        return cls._from_bytes(data)

    def _ensure_parsed(self) -> None:
        if self._cff2_payload is None:
            if self._data[:4] in (b"\x00\x01\x00\x00", b"true", b"typ1"):
                self._cff2_payload = _extract_cff2_from_sfnt(self._data)
            elif self._data[:4] == b"CFF2":
                self._cff2_payload = self._data
            else:
                raise FontParseException("Not a valid CFF2 font")
            self._parse_cff2()

    def _parse_cff2(self) -> None:
        if self._cff2_payload is None:
            return

        try:
            r = BinaryReader(self._cff2_payload)
            header = _parse_header(r)
            r.seek(header.hdr_size)

            _ = CffIndex.from_reader(r)
            top_dict_index = CffIndex.from_reader(r)
            if len(top_dict_index) == 0:
                raise FontParseException("CFF2 Top DICT INDEX is empty")
            string_index = CffIndex.from_reader(r)
            global_subrs = CffIndex.from_reader(r)

            top_raw = top_dict_index[0]
            raw_top = CffDict.from_bytes(top_raw)
            self._top_dict = TopDict.from_dict(raw_top, string_index)

            if self._top_dict.charstrings_offset <= 0 or self._top_dict.charstrings_offset >= len(self._cff2_payload):
                raise FontParseException("Invalid CFF2 CharStrings offset")

            csr = BinaryReader(self._cff2_payload)
            csr.seek(self._top_dict.charstrings_offset)
            self._charstrings = CffIndex.from_reader(csr)

            num_glyphs = len(self._charstrings)
            if num_glyphs <= 0:
                raise FontParseException("CFF2 CharStrings INDEX is empty")

            self._charset = _parse_charset(
                self._cff2_payload,
                self._top_dict.charset_offset,
                num_glyphs,
                string_index,
            )
            self._encoding = _parse_encoding(
                self._cff2_payload,
                self._top_dict.encoding_offset,
                num_glyphs,
                self._charset,
                string_index,
            )

            self._global_subrs = global_subrs
            self._string_index = string_index

            if self._top_dict.private_size > 0 and self._top_dict.private_offset > 0:
                pend = self._top_dict.private_offset + self._top_dict.private_size
                if pend <= len(self._cff2_payload):
                    private_bytes = self._cff2_payload[self._top_dict.private_offset:pend]
                    raw_priv = CffDict.from_bytes(private_bytes)
                    self._private_dict = PrivateDict.from_dict(raw_priv)
                    if self._private_dict.subrs_offset > 0:
                        sr = BinaryReader(self._cff2_payload)
                        sr.seek(self._top_dict.private_offset + self._private_dict.subrs_offset)
                        self._local_subrs = CffIndex.from_reader(sr)
        except Exception:
            self._top_dict = None
            self._charset = None
            self._encoding = None
            self._charstrings = None
            self._global_subrs = None
            self._local_subrs = None
            self._string_index = None
            self._private_dict = None

    def instantiate(self, instance_coords: dict[str, float]) -> "CffFont":
        """Instantiate CFF2 font at specified coordinates.

        Args:
            instance_coords: Axis coordinate values (e.g., {"wght": 700.0})

        Returns:
            New CffFont instance with static outlines

        Raises:
            NotImplementedError: If font is not variable or instantiation fails
        """
        from aspose_font.cff2.instancer import Cff2Instancer

        return Cff2Instancer(self, instance_coords).instantiate()

    def export(self, output_path: str) -> None:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with path.open("wb") as f:
            f.write(self._data)


def _parse_header(r: BinaryReader) -> _CffHeader:
    major = r.read_u8()
    minor = r.read_u8()
    hdr_size = r.read_u8()
    off_size = r.read_u8()
    return _CffHeader(major, minor, hdr_size, off_size)


def _extract_cff2_from_sfnt(sfnt_data: bytes) -> bytes:
    if sfnt_data[:4] != b"\x00\x01\x00\x00":
        raise FontParseException("Not a valid TrueType font")

    num_tables = int.from_bytes(sfnt_data[4:6], "big")
    tables_offset = 12
    for i in range(num_tables):
        table_offset = tables_offset + i * 16
        tag = sfnt_data[table_offset : table_offset + 4].decode("ascii", errors="replace")
        if tag == "CFF2":
            length = int.from_bytes(sfnt_data[table_offset + 12 : table_offset + 16], "big")
            cff2_start = int.from_bytes(sfnt_data[table_offset + 8 : table_offset + 12], "big")
            return sfnt_data[cff2_start : cff2_start + length]

    raise FontParseException("CFF2 table not found in sfnt font")


def _extract_fvar_from_cff2(cff2_data: bytes) -> bytes | None:
    if cff2_data[:4] != b"CFF2":
        return None

    header_size = cff2_data[3]
    r = cff_font_module.BinaryReader(cff2_data)
    r.seek(header_size)

    cff_font_module.CffIndex.from_reader(r)
    top_dict_index = cff_font_module.CffIndex.from_reader(r)
    string_index = cff_font_module.CffIndex.from_reader(r)
    cff_font_module.CffIndex.from_reader(r)

    if len(top_dict_index) == 0:
        return None

    top_raw = top_dict_index[0]
    raw_top = cff_font_module.CffDict.from_bytes(top_raw)
    top_dict = TopDict.from_dict(raw_top, string_index)

    if top_dict.charset_offset > 0 and top_dict.charset_offset < len(cff2_data):
        charset_data = cff2_data[top_dict.charset_offset : top_dict.charset_offset + 256]
        if b"fvar" in charset_data:
            fvar_offset = charset_data.find(b"fvar")
            if fvar_offset + 16 < len(charset_data):
                return charset_data[fvar_offset : fvar_offset + 16]

    return None


def _parse_charset(
    data: bytes,
    offset: int,
    num_glyphs: int,
    string_index: CffIndex,
) -> CffCharset:
    if offset == 0:
        return CffCharset.standard(num_glyphs)
    if offset in (1, 2):
        return CffCharset.standard(num_glyphs)
    if offset <= 0 or offset >= len(data):
        raise FontParseException("CFF2 charset offset out of range")
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
