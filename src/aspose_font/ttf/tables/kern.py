"""TTF kern table parser."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from aspose_font._io import BinaryReader
from aspose_font._types import GlyphId, KernPair


@dataclass
class KernSubtable:
    """Represents one kern subtable with metadata and parsed data."""
    version: int
    length: int
    coverage: int
    format: int

    pairs: list[KernPair] = field(default_factory=list)
    left_class_table: list[int] = field(default_factory=list)
    right_class_table: list[int] = field(default_factory=list)
    width_class_counts: list[int] = field(default_factory=list)
    width_values: list[int] = field(default_factory=list)
    first_glyph: int = 0
    num_glyphs: int = 0


@dataclass
class KernTable:
    """OpenType kern table with subtable metadata and parsed kern pairs."""
    subtables: list[KernSubtable]
    _raw: bytes

    @property
    def pairs(self) -> list[KernPair]:
        """Backward compatibility: return flattened pairs from all subtables."""
        return self.get_all_pairs()

    @classmethod
    def from_reader(cls, r: BinaryReader, table_length: int) -> "KernTable":
        raw = r.read_bytes(table_length)
        rr = BinaryReader(raw)
        subtables: list[KernSubtable] = []

        try:
            version = rr.read_u32()
            if version == 0x00010000:  # Apple format
                rr.read_u16()  # Skip 2-byte padding
                n_tables = rr.read_u32()
            else:  # OpenType format (version is actually uint16 here)
                rr.seek(0)
                rr.read_u16()
                n_tables = rr.read_u16()
        except Exception:
            return cls(subtables=[], _raw=raw)

        for _ in range(n_tables):
            sub = _parse_subtable(rr, raw)
            if sub:
                subtables.append(sub)

        return cls(subtables=subtables, _raw=raw)

    def get(self, left_gid: GlyphId, right_gid: GlyphId) -> int:
        lv, rv = int(left_gid), int(right_gid)
        for p in self.get_all_pairs():
            if int(p.left) == lv and int(p.right) == rv:
                return p.value
        return 0

    def build_lookup(self) -> dict[tuple[int, int], int]:
        return {(int(p.left), int(p.right)): p.value for p in self.get_all_pairs()}

    def get_all_pairs(self) -> list[KernPair]:
        all_pairs: list[KernPair] = []
        for subtable in self.subtables:
            if subtable.format == 0:
                all_pairs.extend(subtable.pairs)
            elif subtable.format == 2:
                all_pairs.extend(_flatten_format2_pairs(subtable))
        return all_pairs

    def to_bytes(self) -> bytes:
        return self._raw


def _parse_subtable(rr: BinaryReader, raw: bytes) -> Optional[KernSubtable]:
    start = rr.tell()
    if rr.remaining() < 6:
        return None

    try:
        version = rr.read_u16()
        length = rr.read_u16()
        coverage = rr.read_u16()
    except Exception:
        return None

    fmt = coverage & 0x00FF

    if length < 6:
        return None

    end = start + length
    if end > len(raw):
        # Subtable claims to be longer than available data - create stub with raw data
        return KernSubtable(version=version, length=length, coverage=coverage, format=fmt)

    if fmt == 0:
        return _parse_format0(rr, length, coverage)
    elif fmt == 2:
        return _parse_format2(rr, length, coverage, raw)

    rr.seek(end)
    return KernSubtable(
        version=version,
        length=length,
        coverage=coverage,
        format=fmt
    )


def _parse_format0(rr: BinaryReader, length: int, coverage: int) -> KernSubtable:
    try:
        n_pairs = rr.read_u16()
        rr.read_u16()
        rr.read_u16()
        rr.read_u16()
    except Exception:
        return KernSubtable(version=0, length=length, coverage=coverage, format=0)

    pairs: list[KernPair] = []
    pairs_start = rr.tell()

    for _ in range(n_pairs):
        if rr.tell() - pairs_start + 6 > length - 6:
            break
        try:
            left = rr.read_u16()
            right = rr.read_u16()
            value = rr.read_i16()
            pairs.append(KernPair(left=GlyphId(left), right=GlyphId(right), value=value))
        except Exception:
            break

    return KernSubtable(
        version=0,
        length=length,
        coverage=coverage,
        format=0,
        pairs=pairs
    )


def _parse_format2(rr: BinaryReader, length: int, coverage: int, raw: bytes) -> KernSubtable:
    try:
        rr.read_u16()
        first_glyph = rr.read_u16()
        num_glyphs = rr.read_u16()
    except Exception:
        return KernSubtable(version=0, length=length, coverage=coverage, format=2)

    left_class_table = _parse_class_table(rr, num_glyphs)
    right_class_table = _parse_class_table(rr, num_glyphs)

    num_left_classes = max(left_class_table) + 1 if left_class_table else 0

    width_class_counts = []
    for _ in range(num_left_classes):
        try:
            width_class_counts.append(rr.read_u16())
        except Exception:
            break

    num_width_values = sum(width_class_counts)
    width_values = []
    for _ in range(num_width_values):
        try:
            width_values.append(rr.read_i16())
        except Exception:
            break

    return KernSubtable(
        version=0,
        length=length,
        coverage=coverage,
        format=2,
        first_glyph=first_glyph,
        num_glyphs=num_glyphs,
        left_class_table=left_class_table,
        right_class_table=right_class_table,
        width_class_counts=width_class_counts,
        width_values=width_values
    )


def _parse_class_table(rr: BinaryReader, num_glyphs: int) -> list[int]:
    class_table: list[int] = []
    for _ in range(num_glyphs):
        try:
            class_table.append(rr.read_u16())
        except Exception:
            break
    return class_table


def _flatten_format2_pairs(subtable: KernSubtable) -> list[KernPair]:
    pairs: list[KernPair] = []

    for left_idx in range(subtable.num_glyphs):
        left_gid = subtable.first_glyph + left_idx
        left_class = subtable.left_class_table[left_idx] if left_idx < len(subtable.left_class_table) else 0

        for right_idx in range(subtable.num_glyphs):
            right_gid = subtable.first_glyph + right_idx
            right_class = subtable.right_class_table[right_idx] if right_idx < len(subtable.right_class_table) else 0

            # Calculate offset as row-major: left_class * num_right_classes + right_class
            num_right_classes = max(subtable.right_class_table) + 1 if subtable.right_class_table else 1
            row_offset = left_class * num_right_classes + right_class
            if row_offset < len(subtable.width_values):
                value = subtable.width_values[row_offset]
                if value != 0:
                    pairs.append(KernPair(
                        left=GlyphId(left_gid),
                        right=GlyphId(right_gid),
                        value=value
                    ))

    return pairs
