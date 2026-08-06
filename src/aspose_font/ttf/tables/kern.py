"""TTF kern table parser."""

from __future__ import annotations

from dataclasses import dataclass

from aspose_font._io import BinaryReader
from aspose_font._types import GlyphId, KernPair


@dataclass
class KernTable:
    pairs: list[KernPair]
    _raw: bytes

    @classmethod
    def from_reader(cls, r: BinaryReader, table_length: int) -> "KernTable":
        raw = r.read_bytes(table_length)
        rr = BinaryReader(raw)
        pairs: list[KernPair] = []

        try:
            rr.read_u16()  # version
            n_tables = rr.read_u16()
        except Exception:
            return cls(pairs=pairs, _raw=raw)

        for _ in range(n_tables):
            sub_start = rr.tell()
            if rr.remaining() < 6:
                break
            try:
                rr.read_u16()  # subtable version
                length = rr.read_u16()
                coverage = rr.read_u16()
            except Exception:
                break

            if length < 6:
                break

            sub_end = sub_start + length
            if sub_end > len(raw):
                break
            fmt = (coverage >> 8) & 0xFF
            if fmt == 0:
                try:
                    if rr.tell() + 8 <= sub_end:
                        n_pairs = rr.read_u16()
                        rr.read_u16()  # searchRange
                        rr.read_u16()  # entrySelector
                        rr.read_u16()  # rangeShift
                        for _ in range(n_pairs):
                            if rr.tell() + 6 > sub_end:
                                break
                            pairs.append(
                                KernPair(
                                    left=GlyphId(rr.read_u16()),
                                    right=GlyphId(rr.read_u16()),
                                    value=rr.read_i16(),
                                )
                            )
                except Exception:
                    pass
            rr.seek(sub_end)

        return cls(pairs=pairs, _raw=raw)

    def get(self, left_gid: GlyphId, right_gid: GlyphId) -> int:
        """Return kern value in font units, or 0 if pair not found. O(n)."""
        lv, rv = int(left_gid), int(right_gid)
        for p in self.pairs:
            if int(p.left) == lv and int(p.right) == rv:
                return p.value
        return 0

    def build_lookup(self) -> dict[tuple[int, int], int]:
        """Build O(1) lookup dict keyed by (left_gid_value, right_gid_value)."""
        return {(int(p.left), int(p.right)): p.value for p in self.pairs}

    def to_bytes(self) -> bytes:
        return self._raw
