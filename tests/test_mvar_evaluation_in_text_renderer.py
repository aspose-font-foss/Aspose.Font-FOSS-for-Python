"""Tests for MVAR evaluation integration in TextRenderer (FONT-535)."""
from pathlib import Path

from aspose_font import FontLoader
from aspose_font.text import TextRenderer
from aspose_font.ttf.tables.hvar import (
    ItemVariationData,
    ItemVariationStore,
    VariationRegion,
    VariationRegionAxis,
)
from aspose_font.ttf.tables.mvar import MvarTable, MvarValueRecord


def _get_testdata_path() -> Path:
    return Path(__file__).resolve().parents[1] / "testdata"


def _create_synthetic_mvar_store() -> ItemVariationStore:
    """Create a synthetic ItemVariationStore for tests."""
    # 1 axis ('wght'), 1 region (active between 0.0 and 1.0, peak at 1.0)
    region = VariationRegion(
        axes=[VariationRegionAxis(start=0.0, peak=1.0, end=1.0)]
    )
    # subtable 0 has two delta sets: inner=0 -> delta 50, inner=1 -> delta -25
    subtable0 = ItemVariationData(
        region_indexes=[0],
        delta_sets=[[50], [-25]],
    )
    # subtable 1 has one delta set: inner=0 -> delta 100
    subtable1 = ItemVariationData(
        region_indexes=[0],
        delta_sets=[[100]],
    )
    return ItemVariationStore(
        axis_tags=["wght"],
        regions=[region],
        subtables=[subtable0, subtable1],
    )


class TestMvarEvaluateMethod:
    """Test MvarTable.evaluate() implementation and index filtering."""

    def test_evaluate_returns_zero_for_unknown_metric(self) -> None:
        """Test evaluate returns 0 for non-matching value_tag."""
        records = [
            MvarValueRecord("wght", "hasc", 0x00000000),
        ]
        store = _create_synthetic_mvar_store()
        table = MvarTable(value_records=records, item_variation_store=store)
        delta = table.evaluate("unknown", 0, 0, coordinates={"wght": 1.0})
        assert delta == 0

    def test_evaluate_fallback_with_no_store(self) -> None:
        """Test evaluate returns 0 when no ItemVariationStore available."""
        records = [
            MvarValueRecord("wght", "hasc", 0),
        ]
        table = MvarTable(value_records=records, item_variation_store=None)
        delta = table.evaluate("hasc", 0, 0)
        assert delta == 0

    def test_evaluate_with_empty_records(self) -> None:
        """Test evaluate returns 0 for empty value_records."""
        table = MvarTable(value_records=[], item_variation_store=None)
        delta = table.evaluate("hasc", 0, 0)
        assert delta == 0

    def test_evaluate_matching_record_with_store(self) -> None:
        """Test evaluate returns correct delta from ItemVariationStore."""
        records = [
            MvarValueRecord("wght", "hasc", 0x00000000),  # outer=0, inner=0 -> 50
        ]
        store = _create_synthetic_mvar_store()
        table = MvarTable(value_records=records, item_variation_store=store)
        delta = table.evaluate("hasc", 0, 0, coordinates={"wght": 1.0})
        assert delta == 50
        assert isinstance(delta, int)

    def test_evaluate_multiple_records_same_value_tag_differing_indices(self) -> None:
        """Test that evaluate distinguishes between records sharing the same value_tag but differing indices."""
        records = [
            MvarValueRecord("wght", "hasc", 0x00000000),  # outer=0, inner=0 -> 50
            MvarValueRecord("wght", "hasc", 0x00010000),  # outer=1, inner=0 -> 100
            MvarValueRecord("wght", "hcdt", 0x00000001),  # outer=0, inner=1 -> -25
        ]
        store = _create_synthetic_mvar_store()
        table = MvarTable(value_records=records, item_variation_store=store)

        delta_outer0 = table.evaluate("hasc", 0, 0, coordinates={"wght": 1.0})
        delta_outer1 = table.evaluate("hasc", 1, 0, coordinates={"wght": 1.0})
        delta_hcdt = table.evaluate("hcdt", 0, 1, coordinates={"wght": 1.0})

        assert delta_outer0 == 50
        assert delta_outer1 == 100
        assert delta_hcdt == -25

    def test_evaluate_non_matching_indices_returns_zero(self) -> None:
        """Test that evaluate returns 0 when outer/inner index does not match any record."""
        records = [
            MvarValueRecord("wght", "hasc", 0x00000000),
        ]
        store = _create_synthetic_mvar_store()
        table = MvarTable(value_records=records, item_variation_store=store)

        # Record has outer=0, inner=0. Calling with outer=0, inner=1 should return 0
        delta = table.evaluate("hasc", 0, 1, coordinates={"wght": 1.0})
        assert delta == 0

    def test_evaluate_with_axis_tag_filter(self) -> None:
        """Test evaluate disambiguates by axis_tag when provided."""
        records = [
            MvarValueRecord("wght", "hasc", 0x00000000),
            MvarValueRecord("wdth", "hasc", 0x00000000),
        ]
        store = _create_synthetic_mvar_store()
        table = MvarTable(value_records=records, item_variation_store=store)

        delta_wght = table.evaluate("hasc", 0, 0, axis_tag="wght", coordinates={"wght": 1.0})
        assert delta_wght == 50

        delta_opsz = table.evaluate("hasc", 0, 0, axis_tag="opsz", coordinates={"wght": 1.0})
        assert delta_opsz == 0

    def test_evaluate_with_none_coordinates_uses_neutral(self) -> None:
        """Test evaluate with coordinates=None evaluates safely at neutral."""
        records = [
            MvarValueRecord("wght", "hasc", 0x00000000),
        ]
        store = _create_synthetic_mvar_store()
        table = MvarTable(value_records=records, item_variation_store=store)
        delta = table.evaluate("hasc", 0, 0, coordinates=None)
        # At neutral (0.0), scalar is 0.0, so delta is 0
        assert delta == 0


class TestMvarTextRendererIntegration:
    """Test MVAR integration in TextRenderer.layout()."""

    def test_layout_without_mvar_works_normally(self) -> None:
        """Test layout works without error when font has no MVAR table."""
        font_path = _get_testdata_path() / "Roboto-VariableFont_wdth,wght.ttf"
        font = FontLoader.open(font_path)

        layout = TextRenderer.layout(font, "Test", size=100.0)
        assert layout is not None
        assert len(layout.glyphs) > 0
        assert layout.ascender != 0.0
        assert layout.descender != 0.0

    def test_layout_horizontal_applies_mvar_ascender_descender_deltas(self) -> None:
        """Test that TextRenderer.layout() applies hasc/hcdt deltas to ascender and descender."""
        font_path = _get_testdata_path() / "Roboto-VariableFont_wdth,wght.ttf"
        font = FontLoader.open(font_path)

        layout_before = TextRenderer.layout(font, "Hello", size=100.0)

        # Attach synthetic MVAR table to font.ttf_tables
        region_neutral = VariationRegion(
            axes=[VariationRegionAxis(start=-1.0, peak=0.0, end=1.0)]
        )
        subtable = ItemVariationData(
            region_indexes=[0],
            delta_sets=[[80], [-40]],  # inner=0 -> +80, inner=1 -> -40
        )
        store_neutral = ItemVariationStore(
            axis_tags=["wght"],
            regions=[region_neutral],
            subtables=[subtable],
        )

        mvar_table = MvarTable(
            value_records=[
                MvarValueRecord("wght", "hasc", 0x00000000),  # outer=0, inner=0 (+80)
                MvarValueRecord("wght", "hcdt", 0x00000001),  # outer=0, inner=1 (-40)
            ],
            item_variation_store=store_neutral,
        )

        font.ttf_tables.mvar = mvar_table
        layout_after = TextRenderer.layout(font, "Hello", size=100.0)

        scale = 100.0 / font.metrics.units_per_em
        expected_ascender_delta = 80 * scale
        expected_descender_delta = -40 * scale

        assert abs(layout_after.ascender - (layout_before.ascender + expected_ascender_delta)) < 1e-4
        assert abs(layout_after.descender - (layout_before.descender + expected_descender_delta)) < 1e-4

    def test_layout_vertical_applies_mvar_vasc_vcdt_deltas(self) -> None:
        """Test that vertical layout applies vasc/vcdt deltas to ascender and descender."""
        font_path = _get_testdata_path() / "Roboto-VariableFont_wdth,wght.ttf"
        font = FontLoader.open(font_path)

        layout_before = TextRenderer.layout(font, "Hello", size=100.0, direction="vertical")

        region_neutral = VariationRegion(
            axes=[VariationRegionAxis(start=-1.0, peak=0.0, end=1.0)]
        )
        subtable = ItemVariationData(
            region_indexes=[0],
            delta_sets=[[60], [-30]],
        )
        store_neutral = ItemVariationStore(
            axis_tags=["wght"],
            regions=[region_neutral],
            subtables=[subtable],
        )

        mvar_table = MvarTable(
            value_records=[
                MvarValueRecord("wght", "vasc", 0x00000000),  # outer=0, inner=0 (+60)
                MvarValueRecord("wght", "vcdt", 0x00000001),  # outer=0, inner=1 (-30)
            ],
            item_variation_store=store_neutral,
        )

        font.ttf_tables.mvar = mvar_table
        layout_after = TextRenderer.layout(font, "Hello", size=100.0, direction="vertical")

        scale = 100.0 / font.metrics.units_per_em
        expected_ascender_delta = 60 * scale
        expected_descender_delta = -30 * scale

        assert abs(layout_after.ascender - (layout_before.ascender + expected_ascender_delta)) < 1e-4
        assert abs(layout_after.descender - (layout_before.descender + expected_descender_delta)) < 1e-4

    def test_mvar_does_not_affect_glyph_advances(self) -> None:
        """Test that MVAR affects ascender/descender, not individual glyph advance widths."""
        font_path = _get_testdata_path() / "Roboto-VariableFont_wdth,wght.ttf"
        font = FontLoader.open(font_path)

        layout_no_mvar = TextRenderer.layout(font, "test", size=100.0)

        region_neutral = VariationRegion(
            axes=[VariationRegionAxis(start=-1.0, peak=0.0, end=1.0)]
        )
        subtable = ItemVariationData(
            region_indexes=[0],
            delta_sets=[[100], [-50]],
        )
        store_neutral = ItemVariationStore(
            axis_tags=["wght"],
            regions=[region_neutral],
            subtables=[subtable],
        )
        font.ttf_tables.mvar = MvarTable(
            value_records=[
                MvarValueRecord("wght", "hasc", 0x00000000),
                MvarValueRecord("wght", "hcdt", 0x00000001),
            ],
            item_variation_store=store_neutral,
        )

        layout_with_mvar = TextRenderer.layout(font, "test", size=100.0)

        assert len(layout_no_mvar.glyphs) == len(layout_with_mvar.glyphs)
        for g_no, g_with in zip(layout_no_mvar.glyphs, layout_with_mvar.glyphs):
            assert abs(g_no.advance_width - g_with.advance_width) < 1e-6
            assert abs(g_no.x_offset - g_with.x_offset) < 1e-6
            assert abs(g_no.y_offset - g_with.y_offset) < 1e-6
