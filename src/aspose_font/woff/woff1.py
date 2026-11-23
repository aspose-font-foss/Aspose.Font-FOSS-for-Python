"""WOFF v1 parser and wrapper font."""

from __future__ import annotations

import math
import zlib
from dataclasses import dataclass

from aspose_font._exceptions import FontParseException
from aspose_font._font_base import Font, FontEncoding, FontType, GlyphAccessor
from aspose_font._io import BinaryReader, BinaryWriter
from aspose_font._types import FontMetrics, KernPair
from aspose_font.ttf.font import TtfFont

_WOFF_SIGNATURE = 0x774F4646


@dataclass(slots=True)
class _WoffTableEntry:
    tag: str
    offset: int
    comp_length: int
    orig_length: int
    orig_checksum: int


class WoffFont(Font):
    def __init__(self, inner: TtfFont, metadata_xml: str = "") -> None:
        self._inner = inner
        self._metadata_xml = metadata_xml

    @classmethod
    def _from_reader(cls, r: BinaryReader) -> "WoffFont":
        data = r.read_bytes(r.remaining())
        rr = BinaryReader(data)

        signature = rr.read_u32()
        if signature != _WOFF_SIGNATURE:
            raise FontParseException("Invalid WOFF signature")
        flavor = rr.read_u32()
        length = rr.read_u32()
        num_tables = rr.read_u16()
        rr.read_u16()  # reserved
        total_sfnt_size = rr.read_u32()
        rr.read_u16()  # majorVersion
        rr.read_u16()  # minorVersion
        meta_offset = rr.read_u32()
        meta_length = rr.read_u32()
        rr.read_u32()  # metaOrigLength
        rr.read_u32()  # privOffset
        rr.read_u32()  # privLength

        if length > len(data):
            raise FontParseException("Invalid WOFF length")

        entries: list[_WoffTableEntry] = []
        for _ in range(num_tables):
            entries.append(
                _WoffTableEntry(
                    tag=rr.read_tag(),
                    offset=rr.read_u32(),
                    comp_length=rr.read_u32(),
                    orig_length=rr.read_u32(),
                    orig_checksum=rr.read_u32(),
                )
            )

        table_map: dict[str, tuple[bytes, int]] = {}
        for entry in entries:
            end = entry.offset + entry.comp_length
            if end > len(data):
                raise FontParseException(f"WOFF table out of bounds: {entry.tag}")
            chunk = data[entry.offset:end]
            if entry.comp_length < entry.orig_length:
                try:
                    decoded = zlib.decompress(chunk)
                except zlib.error as exc:
                    raise FontParseException(f"WOFF table decompression failed: {entry.tag}") from exc
            else:
                decoded = chunk
            if len(decoded) != entry.orig_length:
                raise FontParseException(f"WOFF table length mismatch: {entry.tag}")
            if entry.orig_checksum != 0:
                checksum = _table_checksum(entry.tag, decoded)
                if checksum != entry.orig_checksum:
                    raise FontParseException(f"WOFF table checksum mismatch: {entry.tag}")
            table_map[entry.tag] = (decoded, entry.orig_checksum)

        metadata_xml = ""
        if meta_offset > 0 and meta_length > 0:
            meta_end = meta_offset + meta_length
            if meta_end > len(data):
                raise FontParseException("Invalid WOFF metadata bounds")
            meta_raw = data[meta_offset:meta_end]
            try:
                metadata_xml = zlib.decompress(meta_raw).decode("utf-8", errors="replace")
            except zlib.error as exc:
                raise FontParseException("WOFF metadata decompression failed") from exc

        sfnt = _build_sfnt(flavor, table_map)
        if len(sfnt) != total_sfnt_size:
            raise FontParseException("WOFF sfnt reconstruction size mismatch")
        inner = TtfFont._from_reader(BinaryReader(sfnt))
        return cls(inner=inner, metadata_xml=metadata_xml)

    @property
    def font_type(self) -> FontType:
        return FontType.WOFF

    @property
    def font_name(self) -> str:
        return self._inner.font_name

    @property
    def font_family(self) -> str:
        return self._inner.font_family

    @property
    def font_style(self) -> str:
        return self._inner.font_style

    @property
    def num_glyphs(self) -> int:
        return self._inner.num_glyphs

    @property
    def metrics(self) -> FontMetrics:
        return self._inner.metrics

    @property
    def encoding(self) -> FontEncoding:
        return self._inner.encoding

    @property
    def glyph_accessor(self) -> GlyphAccessor:
        return self._inner.glyph_accessor

    @property
    def metadata_xml(self) -> str:
        return self._metadata_xml

    @property
    def inner_font(self) -> TtfFont:
        return self._inner

    def get_kern_pairs(self) -> list[KernPair]:
        return self._inner.get_kern_pairs()


    def to_bytes(self, font_type: FontType | None = None) -> bytes:
        if font_type is not None and font_type != self.font_type:
            return super().to_bytes(font_type)
        sfnt = self._inner.to_bytes()
        return _build_woff_from_sfnt(sfnt, metadata_xml=self._metadata_xml)


def _build_sfnt(flavor: int, table_map: dict[str, tuple[bytes, int]]) -> bytes:
    tags = sorted(table_map.keys())
    num_tables = len(tags)
    if num_tables == 0:
        raise FontParseException("WOFF contains no tables")

    max_power = 1 << (num_tables.bit_length() - 1)
    search_range = max_power * 16
    entry_selector = int(math.log2(max_power))
    range_shift = num_tables * 16 - search_range

    w = BinaryWriter()
    w.write_u32(flavor)
    w.write_u16(num_tables)
    w.write_u16(search_range)
    w.write_u16(entry_selector)
    w.write_u16(range_shift)

    offset_positions: list[int] = []
    for tag in tags:
        blob, checksum = table_map[tag]
        w.write_tag(tag)
        w.write_u32(checksum if checksum != 0 else _table_checksum(tag, blob))
        offset_positions.append(w.tell())
        w.write_u32(0)
        w.write_u32(len(blob))

    for i, tag in enumerate(tags):
        blob, _ = table_map[tag]
        while w.tell() % 4 != 0:
            w.write_u8(0)
        off = w.tell()
        cur = w.tell()
        w.seek(offset_positions[i])
        w.write_u32(off)
        w.seek(cur)
        w.write_bytes(blob)

    return w.to_bytes()


def _build_woff_from_sfnt(sfnt: bytes, metadata_xml: str = "") -> bytes:
    flavor, tables = _extract_sfnt_tables(sfnt)
    tags = sorted(tables.keys())

    table_blobs: list[tuple[str, bytes, bytes, int]] = []
    for tag in tags:
        orig = tables[tag]
        comp = zlib.compress(orig, level=6)
        best = comp if len(comp) < len(orig) else orig
        table_blobs.append((tag, best, orig, _table_checksum(tag, orig)))

    dir_size = 44 + len(table_blobs) * 20
    offsets: list[int] = []
    pos = dir_size
    for _, comp, _, _ in table_blobs:
        if pos % 4 != 0:
            pos += 4 - (pos % 4)
        offsets.append(pos)
        pos += len(comp)

    meta_offset = 0
    meta_length = 0
    meta_orig_length = 0
    meta_payload = b""
    if metadata_xml:
        meta_orig = metadata_xml.encode("utf-8")
        meta_payload = zlib.compress(meta_orig)
        meta_orig_length = len(meta_orig)
        if pos % 4 != 0:
            pos += 4 - (pos % 4)
        meta_offset = pos
        meta_length = len(meta_payload)
        pos += meta_length

    length = pos

    w = BinaryWriter()
    w.write_u32(_WOFF_SIGNATURE)
    w.write_u32(flavor)
    w.write_u32(length)
    w.write_u16(len(table_blobs))
    w.write_u16(0)
    w.write_u32(len(sfnt))
    w.write_u16(1)
    w.write_u16(0)
    w.write_u32(meta_offset)
    w.write_u32(meta_length)
    w.write_u32(meta_orig_length)
    w.write_u32(0)
    w.write_u32(0)

    for i, (tag, comp, orig, checksum) in enumerate(table_blobs):
        w.write_tag(tag)
        w.write_u32(offsets[i])
        w.write_u32(len(comp))
        w.write_u32(len(orig))
        w.write_u32(checksum)

    for i, (_, comp, _, _) in enumerate(table_blobs):
        while w.tell() < offsets[i]:
            w.write_u8(0)
        w.write_bytes(comp)

    if meta_length > 0:
        while w.tell() < meta_offset:
            w.write_u8(0)
        w.write_bytes(meta_payload)

    return w.to_bytes()


def _extract_sfnt_tables(sfnt: bytes) -> tuple[int, dict[str, bytes]]:
    r = BinaryReader(sfnt)
    flavor = r.read_u32()
    num_tables = r.read_u16()
    r.read_u16()
    r.read_u16()
    r.read_u16()

    records: list[tuple[str, int, int]] = []
    for _ in range(num_tables):
        tag = r.read_tag()
        r.read_u32()  # checksum
        offset = r.read_u32()
        length = r.read_u32()
        records.append((tag, offset, length))

    out: dict[str, bytes] = {}
    for tag, offset, length in records:
        end = offset + length
        if end > len(sfnt):
            raise FontParseException(f"sfnt table out of bounds: {tag}")
        out[tag] = sfnt[offset:end]
    return flavor, out


def _sfnt_checksum(data: bytes) -> int:
    padded = data + (b"\x00" * ((4 - (len(data) % 4)) % 4))
    total = 0
    for i in range(0, len(padded), 4):
        total = (total + int.from_bytes(padded[i : i + 4], "big")) & 0xFFFFFFFF
    return total


def _table_checksum(tag: str, data: bytes) -> int:
    if tag == "head" and len(data) >= 12:
        mutable = bytearray(data)
        mutable[8:12] = b"\x00\x00\x00\x00"
        return _sfnt_checksum(bytes(mutable))
    return _sfnt_checksum(data)
