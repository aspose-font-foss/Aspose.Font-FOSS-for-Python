"""Pure-Python Variable Font gvar Delta Compactor Core Engine (FONT-566)."""

from __future__ import annotations

from dataclasses import dataclass

from aspose_font._io import BinaryWriter
from aspose_font.ttf.tables.gvar import GvarTable


@dataclass(frozen=True, slots=True)
class CompactionResult:
    """Result of gvar table compaction."""

    compacted_bytes: bytes
    removed_glyph_count: int
    retained_glyph_count: int
    original_size: int
    compacted_size: int
    size_reduction_percent: float


class GvarDeltaCompactor:
    """Compacts gvar tables by removing unused glyph delta variations."""

    def compact(
        self,
        gvar_table: GvarTable,
        retained_gid_map: dict[int, int],
    ) -> CompactionResult:
        """Compact gvar table by keeping only retained glyphs.

        Args:
            gvar_table: Parsed GvarTable instance (from GvarTable.from_reader)
            retained_gid_map: Mapping {old_gid: new_gid} for glyphs to retain

        Returns:
            CompactionResult with compacted bytes and statistics
        """
        original_glyph_count = len(gvar_table.glyph_offsets) - 1
        retained_glyph_count = len(retained_gid_map)
        removed_glyph_count = original_glyph_count - retained_glyph_count

        if retained_glyph_count == 0:
            return self._compact_empty(gvar_table, original_glyph_count, removed_glyph_count)

        glyph_data_map: dict[int, bytes] = {}
        for old_gid in retained_gid_map.keys():
            start = gvar_table.glyph_offsets[old_gid]
            end = gvar_table.glyph_offsets[old_gid + 1]
            data_chunk = gvar_table._raw[
                gvar_table.data_offset + start : gvar_table.data_offset + end
            ]
            glyph_data_map[old_gid] = data_chunk

        shared_tuples = gvar_table.shared_tuples
        shared_tuple_count = len(shared_tuples)
        axis_count = gvar_table.axis_count
        shared_tuple_size = shared_tuple_count * axis_count * 2
        shared_bytes_start = gvar_table.data_offset - shared_tuple_size
        shared_bytes = gvar_table._raw[shared_bytes_start : gvar_table.data_offset]

        new_glyph_count = retained_glyph_count
        # Header: 12 bytes for main fields, but we need 20 bytes total for (major, minor, axis_count, shared_tuple_count, offset_to_shared_tuples)
        # Actually: 2+2+2+2+4+2+2+4 = 20 bytes
        header_size = 20
        glyph_offsets_size = (new_glyph_count + 1) * 4  # 4 bytes per offset (long offsets)
        new_shared_offset = header_size + glyph_offsets_size
        new_data_offset = new_shared_offset + len(shared_bytes)

        w = BinaryWriter()
        w.write_u16(1)
        w.write_u16(0)
        w.write_u16(gvar_table.axis_count)
        w.write_u16(len(shared_tuples))
        w.write_u32(new_shared_offset)
        w.write_u16(new_glyph_count)
        w.write_u16(1)
        w.write_u32(new_data_offset)

        new_offsets: list[int] = [0]
        current_offset = 0
        for old_gid in sorted(retained_gid_map.keys()):
            data = glyph_data_map[old_gid]
            current_offset += len(data)
            new_offsets.append(current_offset)

        for offset in new_offsets:
            w.write_u32(offset)

        w.write_bytes(shared_bytes)

        for old_gid in sorted(retained_gid_map.keys()):
            w.write_bytes(glyph_data_map[old_gid])

        compacted_bytes = w.to_bytes()

        original_size = len(gvar_table._raw)
        compacted_size = len(compacted_bytes)
        size_reduction_percent = (
            (original_size - compacted_size) / original_size * 100.0
            if original_size > 0
            else 0.0
        )

        return CompactionResult(
            compacted_bytes=compacted_bytes,
            removed_glyph_count=removed_glyph_count,
            retained_glyph_count=retained_glyph_count,
            original_size=original_size,
            compacted_size=compacted_size,
            size_reduction_percent=size_reduction_percent,
        )

    def _compact_empty(
        self, gvar_table: GvarTable, original_glyph_count: int, removed_glyph_count: int
    ) -> CompactionResult:
        w = BinaryWriter()
        w.write_u16(1)
        w.write_u16(0)
        w.write_u16(gvar_table.axis_count)
        w.write_u16(len(gvar_table.shared_tuples))
        w.write_u32(20)
        w.write_u16(0)
        w.write_u16(1)
        w.write_u32(20)
        w.write_u32(0)

        original_size = len(gvar_table._raw)
        compacted_bytes = w.to_bytes()
        compacted_size = len(compacted_bytes)
        size_reduction_percent = (
            (original_size - compacted_size) / original_size * 100.0
            if original_size > 0
            else 0.0
        )

        return CompactionResult(
            compacted_bytes=compacted_bytes,
            removed_glyph_count=removed_glyph_count,
            retained_glyph_count=0,
            original_size=original_size,
            compacted_size=compacted_size,
            size_reduction_percent=size_reduction_percent,
        )

    @staticmethod
    def compact_for_subset(
        gvar_table: GvarTable,
        raw_gvar_data: bytes,
        sorted_old_gids: list[int],
    ) -> CompactionResult:
        """Convenience method for subset workflow compatibility."""
        gid_map = {old: new for new, old in enumerate(sorted_old_gids)}
        return GvarDeltaCompactor().compact(gvar_table, gid_map)
