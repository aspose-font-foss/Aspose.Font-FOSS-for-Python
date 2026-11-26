"""Tests for GPOS table parser (Glyph Positioning)."""

from __future__ import annotations

import pytest

from aspose_font import TtfFont
from aspose_font._io import BinaryReader
from aspose_font._types import GlyphId
from aspose_font.ttf.tables.gpos import (
    FeatureTable,
    GposTable,
    _parse_coverage,
)


class TestGposKerningPairHelper:
    """Test get_kerning_pair() helper method."""

    def test_get_kerning_pair_empty_table(self):
        """Test lookup on empty/unparsed GPOS table returns 0."""
        gpos = GposTable(
            version=0x00010000,
            script_list_offset=0,
            feature_list_offset=0,
            lookup_list_offset=0,
        )
        assert gpos.get_kerning_pair(GlyphId(0), GlyphId(0)) == 0

    def test_get_kerning_pair_no_kern_feature(self):
        """Test that non-kern feature returns 0."""
        feature = FeatureTable(
            feature_tag="dist",
            feature_params_offset=0,
            lookup_index_count=0,
            lookup_list_indices=[],
        )
        gpos = GposTable(
            version=0x00010000,
            script_list_offset=0,
            feature_list_offset=0,
            lookup_list_offset=0,
            feature_list=[feature],
        )
        assert gpos.get_kerning_pair(GlyphId(0), GlyphId(0)) == 0

    def test_get_kerning_pair_consistent_with_get_kern_pairs_empty(self):
        """Test that get_kerning_pair on empty table returns 0."""
        gpos = GposTable(
            version=0x00010000,
            script_list_offset=0,
            feature_list_offset=0,
            lookup_list_offset=0,
        )
        assert gpos.get_kerning_pair(GlyphId(5), GlyphId(10)) == 0
        assert gpos.get_kern_pairs() == []


class TestGposTableParsing:
    """Test GPOS table parsing from byte streams."""

    def test_parse_gpos_coverage_format1(self):
        """Test parsing coverage format 1."""
        data = b"\x00\x01\x00\x03\x00\x05\x00\x0A\x00\x0F"
        r = BinaryReader(data)
        coverage = _parse_coverage(r, 0)

        assert coverage.format == 1
        assert coverage.glyph_indices == [5, 10, 15]
        assert coverage.glyph_range_records is None

    def test_parse_gpos_coverage_format2(self):
        """Test parsing coverage format 2."""
        data = (
            b"\x00\x02\x00\x02"
            b"\x00\x05\x00\x07\x00\x00"
            b"\x00\x0A\x00\x0C\x00\x03"
        )
        r = BinaryReader(data)
        coverage = _parse_coverage(r, 0)

        assert coverage.format == 2
        assert coverage.glyph_indices == []
        assert coverage.glyph_range_records == [
            (5, 7, 0),
            (10, 12, 3),
        ]


class TestGposFeatureHelpers:
    """Test feature list helper methods."""

    def test_list_all_features(self):
        """Test listing all features in GPOS table."""
        feature = FeatureTable(
            feature_tag="kern",
            feature_params_offset=0,
            lookup_index_count=0,
            lookup_list_indices=[],
        )
        gpos = GposTable(
            version=0x00010000,
            script_list_offset=0,
            feature_list_offset=0,
            lookup_list_offset=0,
            feature_list=[feature],
        )
        assert gpos.list_all_features() == ["kern"]

    def test_list_all_features_empty(self):
        """Test listing features on table without feature list."""
        gpos = GposTable(
            version=0x00010000,
            script_list_offset=0,
            feature_list_offset=0,
            lookup_list_offset=0,
        )
        assert gpos.list_all_features() == []

    def test_list_scripts_empty(self):
        """Test listing scripts on table without script list."""
        gpos = GposTable(
            version=0x00010000,
            script_list_offset=0,
            feature_list_offset=0,
            lookup_list_offset=0,
        )
        assert gpos.list_scripts() == []

    def test_get_script_not_found(self):
        """Test getting non-existent script returns None."""
        feature = FeatureTable(
            feature_tag="kern",
            feature_params_offset=0,
            lookup_index_count=0,
            lookup_list_indices=[],
        )
        gpos = GposTable(
            version=0x00010000,
            script_list_offset=0,
            feature_list_offset=0,
            lookup_list_offset=0,
            feature_list=[feature],
            script_list=[("latn", 8)],
        )
        assert gpos.get_script("cyrl") is None


class TestGposIntegration:
    """Integration tests with real font fixtures."""

    def test_gpos_empty_on_font_without_gpos(self, roboto: TtfFont) -> None:
        """Test that font without GPOS returns empty results."""
        gpos = roboto.ttf_tables.gpos
        if gpos is None:
            assert gpos is None
            return

        assert gpos.get_kern_pairs() == []
        assert isinstance(gpos.list_scripts(), list)
        assert isinstance(gpos.list_all_features(), list)

    def test_gpos_get_kerning_pair_empty_on_font_without_gpos(
        self, roboto: TtfFont
    ) -> None:
        """Test get_kerning_pair returns 0 when GPOS is None."""
        gpos = roboto.ttf_tables.gpos
        if gpos is None:
            assert gpos is None
            return

        result = gpos.get_kerning_pair(GlyphId(0), GlyphId(0))
        assert result == 0

    def test_gpos_feature_listing_with_roboto(self, roboto: TtfFont) -> None:
        """Test GPOS feature listing on Roboto (may not have GPOS)."""
        gpos = roboto.ttf_tables.gpos
        if gpos is None:
            pytest.skip("Roboto has no GPOS table")

        features = gpos.list_all_features()
        assert isinstance(features, list)

    def test_gpos_script_listing_with_roboto(self, roboto: TtfFont) -> None:
        """Test GPOS script listing on Roboto (may not have GPOS)."""
        gpos = roboto.ttf_tables.gpos
        if gpos is None:
            pytest.skip("Roboto has no GPOS table")

        scripts = gpos.list_scripts()
        assert isinstance(scripts, list)

    def test_gpos_kerning_with_roboto(self, roboto: TtfFont) -> None:
        """Test GPOS kerning extraction on Roboto (may not have GPOS)."""
        gpos = roboto.ttf_tables.gpos
        if gpos is None:
            pytest.skip("Roboto has no GPOS table")

        kern_pairs = gpos.get_kern_pairs()
        assert isinstance(kern_pairs, list)
