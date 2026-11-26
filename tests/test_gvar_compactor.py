"""Tests for FONT-566: Pure-Python Variable Font gvar Delta Compactor Core Engine."""

from __future__ import annotations

from pathlib import Path

import pytest

from aspose_font import FontLoader
from aspose_font.ttf.instancer import TtfInstancer
from aspose_font.ttf.tables.gvar import GvarTable
from aspose_font.ttf.tables.gvar_optimizer import GvarDeltaCompactor


def _get_point_count(font, gid: int) -> int:
    """Get the point count for a glyph from its glyf data."""
    loca = font.ttf_tables.loca
    offset = loca.glyph_offset(gid)
    length = loca.glyph_length(gid)
    if length <= 0:
        return 0
    raw = font.ttf_tables.glyf.get_glyph_bytes(offset, length)
    if len(raw) < 10:
        return 0
    contour_count = int.from_bytes(raw[:2], "big", signed=True)
    if contour_count > 0:
        try:
            simple = TtfInstancer._parse_simple_glyph(raw)
            return len(simple.xs)
        except Exception:
            return 0
    return 0


@pytest.fixture
def roboto_variable(testdata_dir: Path) -> tuple[GvarTable, bytes]:
    """Load Roboto variable font and extract gvar table."""
    from aspose_font import TtfFont

    font = FontLoader.open(str(testdata_dir / "Roboto-VariableFont_wdth,wght.ttf"))
    if isinstance(font, TtfFont) and "gvar" not in font.ttf_tables._raw:
        pytest.skip("Roboto should have gvar table for this test")
    return font.ttf_tables.gvar, font.ttf_tables._raw["gvar"]


class TestGvarDeltaCompactor:
    """Tests for GvarDeltaCompactor core engine."""

    def test_compact_preserves_retained_glyphs(self, roboto_variable: tuple[GvarTable, bytes]):
        """Verify retained glyphs maintain identical variation data after compaction."""
        gvar_table, raw_gvar = roboto_variable

        # Use a glyph that has gvar data and works with reasonable point_count
        # Glyph 0 has gvar data and work with point_count=10
        retained_gid_map = {0: 0}

        compactor = GvarDeltaCompactor()
        result = compactor.compact(gvar_table, retained_gid_map)

        from aspose_font._io import BinaryReader
        new_gvar = GvarTable.from_reader(
            BinaryReader(result.compacted_bytes),
            len(result.compacted_bytes),
            axis_tags=gvar_table._axis_tags,
        )

        original_vars = gvar_table.glyph_variations(0, point_count=10)
        compacted_vars = new_gvar.glyph_variations(0, point_count=10)

        assert len(compacted_vars) == len(original_vars)
        for orig_var, comp_var in zip(original_vars, compacted_vars):
            assert orig_var.peak_coords == comp_var.peak_coords
            assert orig_var.deltas == comp_var.deltas

    def test_compact_removes_unreferenced_glyphs(self, roboto_variable: tuple[GvarTable, bytes]):
        """Verify gvar size decreases when excluding glyphs."""
        gvar_table, raw_gvar = roboto_variable

        retained_gid_map = {i: i for i in range(10)}

        compactor = GvarDeltaCompactor()
        result = compactor.compact(gvar_table, retained_gid_map)

        assert result.compacted_size < len(raw_gvar)
        assert result.removed_glyph_count > 0

    def test_compact_empty_retained_map_returns_minimal_table(self, roboto_variable: tuple[GvarTable, bytes]):
        """Verify compaction with empty map produces valid minimal gvar."""
        gvar_table, _ = roboto_variable

        compactor = GvarDeltaCompactor()
        result = compactor.compact(gvar_table, {})

        assert result.compacted_size < len(gvar_table._raw)
        assert result.retained_glyph_count == 0
        assert result.removed_glyph_count > 0

    def test_compact_roundtrip_stable(self, roboto_variable: tuple[GvarTable, bytes]):
        """Verify compacted gvar can be reloaded without corruption."""
        gvar_table, raw_gvar = roboto_variable

        # Use glyphs that have valid gvar data
        retained_gids = [0, 5, 6]
        retained_gid_map = {old: old for old in retained_gids}

        compactor = GvarDeltaCompactor()
        result = compactor.compact(gvar_table, retained_gid_map)

        from aspose_font._io import BinaryReader
        new_gvar = GvarTable.from_reader(
            BinaryReader(result.compacted_bytes),
            len(result.compacted_bytes),
            axis_tags=gvar_table._axis_tags,
        )

        for new_gid, old_gid in enumerate(retained_gids):
            original_vars = gvar_table.glyph_variations(old_gid, point_count=10)
            new_vars = new_gvar.glyph_variations(new_gid, point_count=10)
            assert len(new_vars) == len(original_vars)

    def test_compact_returns_expected_statistics(self, roboto_variable: tuple[GvarTable, bytes]):
        """Verify CompactionResult provides accurate statistics."""
        gvar_table, raw_gvar = roboto_variable

        retained_gid_map = {i: i for i in range(50)}

        compactor = GvarDeltaCompactor()
        result = compactor.compact(gvar_table, retained_gid_map)

        assert result.original_size == len(raw_gvar)
        assert result.compacted_size < result.original_size
        assert result.retained_glyph_count == 50
        assert result.removed_glyph_count == len(gvar_table.glyph_offsets) - 1 - 50
        assert 0.0 <= result.size_reduction_percent <= 100.0
