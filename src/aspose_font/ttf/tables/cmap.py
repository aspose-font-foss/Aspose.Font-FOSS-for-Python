"""TTF cmap table parser."""

from __future__ import annotations

import math
from dataclasses import dataclass

from aspose_font._exceptions import FontParseException
from aspose_font._io import BinaryReader, BinaryWriter


@dataclass(slots=True)
class CmapSubtable:
    platform_id: int
    encoding_id: int
    format: int
    _mapping: dict[int, int]

    def get_gid(self, codepoint: int) -> int | None:
        return self._mapping.get(codepoint)


@dataclass
class CmapTable:
    subtables: list[CmapSubtable]
    _raw: bytes

    def best_subtable(self) -> CmapSubtable:
        priorities = [
            (3, 10, 12),
            (3, 1, 4),
            (0, None, 4),
            (1, 0, 0),
        ]
        for pid, eid, fmt in priorities:
            for sub in self.subtables:
                if sub.platform_id != pid:
                    continue
                if eid is not None and sub.encoding_id != eid:
                    continue
                if sub.format == fmt:
                    return sub
        raise FontParseException("No supported cmap subtable found")

    @classmethod
    def from_reader(cls, r: BinaryReader, table_length: int) -> "CmapTable":
        raw = r.read_bytes(table_length)
        rr = BinaryReader(raw)
        rr.read_u16()  # version
        num_tables = rr.read_u16()
        records = []
        for _ in range(num_tables):
            platform_id = rr.read_u16()
            encoding_id = rr.read_u16()
            offset = rr.read_u32()
            records.append((platform_id, encoding_id, offset))

        subtables: list[CmapSubtable] = []
        for platform_id, encoding_id, offset in records:
            if offset + 2 > len(raw):
                continue
            fmt = int.from_bytes(raw[offset : offset + 2], "big")
            mapping: dict[int, int] | None = None
            if fmt == 0:
                if offset + 6 > len(raw):
                    continue
                length = int.from_bytes(raw[offset + 2 : offset + 4], "big")
                sub = raw[offset : offset + length]
                mapping = _parse_format0(sub)
            elif fmt == 4:
                if offset + 6 > len(raw):
                    continue
                length = int.from_bytes(raw[offset + 2 : offset + 4], "big")
                sub = raw[offset : offset + length]
                mapping = _parse_format4(sub)
            elif fmt == 6:
                if offset + 6 > len(raw):
                    continue
                length = int.from_bytes(raw[offset + 2 : offset + 4], "big")
                sub = raw[offset : offset + length]
                mapping = _parse_format6(sub)
            elif fmt == 12:
                if offset + 16 > len(raw):
                    continue
                length = int.from_bytes(raw[offset + 4 : offset + 8], "big")
                sub = raw[offset : offset + length]
                mapping = _parse_format12(sub)

            if mapping is not None:
                subtables.append(
                    CmapSubtable(
                        platform_id=platform_id,
                        encoding_id=encoding_id,
                        format=fmt,
                        _mapping=mapping,
                    )
                )

        return cls(subtables=subtables, _raw=raw)

    def to_bytes(self) -> bytes:
        if not self.subtables:
            return self._raw

        subtable_blobs: list[bytes] = []
        for subtable in self.subtables:
            if subtable.format == 0:
                blob = _build_format0(subtable._mapping)
            elif subtable.format == 4:
                blob = _build_format4(subtable._mapping)
            elif subtable.format == 6:
                blob = _build_format6(subtable._mapping)
            elif subtable.format == 12:
                blob = _build_format12(subtable._mapping)
            else:
                raise FontParseException(f"Unsupported cmap format for serialization: {subtable.format}")
            subtable_blobs.append(blob)

        w = BinaryWriter()
        w.write_u16(0)
        w.write_u16(len(self.subtables))
        offset = 4 + len(self.subtables) * 8
        for i, subtable in enumerate(self.subtables):
            w.write_u16(subtable.platform_id)
            w.write_u16(subtable.encoding_id)
            w.write_u32(offset)
            offset += len(subtable_blobs[i])
        for blob in subtable_blobs:
            w.write_bytes(blob)
        return w.to_bytes()


def _build_format0(mapping: dict[int, int]) -> bytes:
    glyphs = bytearray(256)
    for cp, gid in mapping.items():
        if 0 <= cp <= 0xFF:
            glyphs[cp] = gid & 0xFF
    w = BinaryWriter()
    w.write_u16(0)
    w.write_u16(262)
    w.write_u16(0)
    w.write_bytes(bytes(glyphs))
    return w.to_bytes()


def _build_format6(mapping: dict[int, int]) -> bytes:
    bmp = {cp: gid for cp, gid in mapping.items() if 0 <= cp <= 0xFFFF}
    if not bmp:
        first_code = 0
        entry_count = 0
    else:
        first_code = min(bmp)
        last_code = max(bmp)
        entry_count = max(0, last_code - first_code + 1)

    w = BinaryWriter()
    w.write_u16(6)
    w.write_u16(10 + entry_count * 2)
    w.write_u16(0)
    w.write_u16(first_code)
    w.write_u16(entry_count)
    for cp in range(first_code, first_code + entry_count):
        w.write_u16(bmp.get(cp, 0) & 0xFFFF)
    return w.to_bytes()


def _build_format12(mapping: dict[int, int]) -> bytes:
    cps = sorted(cp for cp in mapping.keys() if 0 <= cp <= 0x10FFFF)
    groups: list[tuple[int, int, int]] = []
    for cp in cps:
        gid = mapping[cp] & 0xFFFFFFFF
        if not groups:
            groups.append((cp, cp, gid))
            continue
        start, end, start_gid = groups[-1]
        expected_gid = start_gid + (cp - start)
        if cp == end + 1 and gid == expected_gid:
            groups[-1] = (start, cp, start_gid)
        else:
            groups.append((cp, cp, gid))

    w = BinaryWriter()
    w.write_u16(12)
    w.write_u16(0)
    w.write_u32(16 + len(groups) * 12)
    w.write_u32(0)
    w.write_u32(len(groups))
    for start, end, start_gid in groups:
        w.write_u32(start)
        w.write_u32(end)
        w.write_u32(start_gid)
    return w.to_bytes()


def _build_format4(mapping: dict[int, int]) -> bytes:
    pairs = sorted((cp, gid & 0xFFFF) for cp, gid in mapping.items() if 0 <= cp <= 0xFFFF)
    # Generic encoding path: one segment per codepoint + sentinel.
    cps = [cp for cp, _ in pairs]
    gids = [gid for _, gid in pairs]
    seg_count = len(cps) + 1
    seg_count_x2 = seg_count * 2
    max_power = 1 << (seg_count.bit_length() - 1)
    search_range = max_power * 2
    entry_selector = int(math.log2(max_power))
    range_shift = seg_count_x2 - search_range

    w = BinaryWriter()
    length = 16 + seg_count * 8 + len(gids) * 2
    w.write_u16(4)
    w.write_u16(length)
    w.write_u16(0)
    w.write_u16(seg_count_x2)
    w.write_u16(search_range)
    w.write_u16(entry_selector)
    w.write_u16(range_shift)

    for cp in cps:
        w.write_u16(cp)
    w.write_u16(0xFFFF)
    w.write_u16(0)  # reservedPad

    for cp in cps:
        w.write_u16(cp)
    w.write_u16(0xFFFF)

    for _ in cps:
        w.write_i16(0)
    w.write_i16(1)  # sentinel delta

    # For single-codepoint segments this constant points to the corresponding glyphIdArray entry.
    ro = 2 * seg_count
    for _ in cps:
        w.write_u16(ro)
    w.write_u16(0)  # sentinel

    for gid in gids:
        w.write_u16(gid)
    return w.to_bytes()


def _parse_format0(data: bytes) -> dict[int, int]:
    if len(data) < 262:
        return {}
    mapping: dict[int, int] = {}
    glyphs = data[6:262]
    for cp, gid in enumerate(glyphs):
        if gid != 0:
            mapping[cp] = gid
    return mapping


def _parse_format6(data: bytes) -> dict[int, int]:
    if len(data) < 10:
        return {}
    first_code = int.from_bytes(data[6:8], "big")
    entry_count = int.from_bytes(data[8:10], "big")
    mapping: dict[int, int] = {}
    pos = 10
    for idx in range(entry_count):
        if pos + 2 > len(data):
            break
        gid = int.from_bytes(data[pos : pos + 2], "big")
        if gid != 0:
            mapping[first_code + idx] = gid
        pos += 2
    return mapping


def _parse_format12(data: bytes) -> dict[int, int]:
    if len(data) < 16:
        return {}
    n_groups = int.from_bytes(data[12:16], "big")
    pos = 16
    mapping: dict[int, int] = {}
    for _ in range(n_groups):
        if pos + 12 > len(data):
            break
        start_char = int.from_bytes(data[pos : pos + 4], "big")
        end_char = int.from_bytes(data[pos + 4 : pos + 8], "big")
        start_gid = int.from_bytes(data[pos + 8 : pos + 12], "big")
        for cp in range(start_char, end_char + 1):
            mapping[cp] = start_gid + (cp - start_char)
        pos += 12
    return mapping


def _parse_format4(data: bytes) -> dict[int, int]:
    if len(data) < 16:
        return {}

    seg_count = int.from_bytes(data[6:8], "big") // 2
    end_codes_pos = 14
    start_codes_pos = end_codes_pos + seg_count * 2 + 2
    id_delta_pos = start_codes_pos + seg_count * 2
    id_range_offset_pos = id_delta_pos + seg_count * 2

    if id_range_offset_pos + seg_count * 2 > len(data):
        return {}

    end_codes = [
        int.from_bytes(data[end_codes_pos + i * 2 : end_codes_pos + i * 2 + 2], "big")
        for i in range(seg_count)
    ]
    start_codes = [
        int.from_bytes(data[start_codes_pos + i * 2 : start_codes_pos + i * 2 + 2], "big")
        for i in range(seg_count)
    ]
    id_deltas = [
        int.from_bytes(data[id_delta_pos + i * 2 : id_delta_pos + i * 2 + 2], "big", signed=True)
        for i in range(seg_count)
    ]
    id_range_offsets = [
        int.from_bytes(data[id_range_offset_pos + i * 2 : id_range_offset_pos + i * 2 + 2], "big")
        for i in range(seg_count)
    ]

    mapping: dict[int, int] = {}
    for i in range(seg_count):
        start = start_codes[i]
        end = end_codes[i]
        if start == 0xFFFF and end == 0xFFFF:
            continue
        for cp in range(start, end + 1):
            if id_range_offsets[i] == 0:
                gid = (cp + id_deltas[i]) & 0xFFFF
            else:
                ro_word_pos = id_range_offset_pos + i * 2
                glyph_word_pos = ro_word_pos + id_range_offsets[i] + 2 * (cp - start)
                if glyph_word_pos + 2 > len(data):
                    continue
                glyph_index = int.from_bytes(data[glyph_word_pos : glyph_word_pos + 2], "big")
                if glyph_index == 0:
                    gid = 0
                else:
                    gid = (glyph_index + id_deltas[i]) & 0xFFFF
            if gid != 0:
                mapping[cp] = gid

    return mapping
