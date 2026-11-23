"""Edge case tests for STAT table synthesis."""

import pytest

from aspose_font._exceptions import FontParseException
from aspose_font.ttf.tables.fvar import AxisRecord
from aspose_font.ttf.tables.stat import (
    build_static_stat_table,
    parse_stat_table,
    synthesize_stat_table,
)


class TestBuildStaticStatTableEdgeCases:
    """Test build_static_stat_table edge cases."""

    def test_missing_axis_coordinates_raises(self) -> None:
        """Verify FontParseException when axis not in coordinates."""
        axes = [AxisRecord(tag="wght", min_value=100, default_value=400, max_value=900, flags=0, name_id=256)]
        coordinates = {}  # Empty - missing wght coordinate

        with pytest.raises(FontParseException, match="Missing STAT coordinate for axis"):
            build_static_stat_table(axes, coordinates)

    def test_duplicate_axis_tags_supported(self) -> None:
        """Verify STAT table synthesis handles duplicate axis tags."""
        axes = [
            AxisRecord(tag="wght", min_value=100, default_value=400, max_value=900, flags=0, name_id=256),
            AxisRecord(tag="wght", min_value=200, default_value=500, max_value=800, flags=0, name_id=257),
        ]
        coordinates = {"wght": 400.0}

        stat_data = build_static_stat_table(axes, coordinates)

        assert stat_data is not None
        assert len(stat_data) > 0
        parsed = parse_stat_table(stat_data)
        assert parsed is not None
        assert len(parsed["design_axes"]) == 2

    def test_empty_axes_list_valid(self) -> None:
        """Verify empty axes produces valid STAT 1.1 table."""
        axes = []
        coordinates = {}

        stat_data = build_static_stat_table(axes, coordinates)

        assert stat_data is not None
        assert len(stat_data) > 0

        major_version = int.from_bytes(stat_data[0:2], "big")
        minor_version = int.from_bytes(stat_data[2:4], "big")
        assert (major_version, minor_version) == (1, 1)

        design_axis_count = int.from_bytes(stat_data[6:8], "big")
        assert design_axis_count == 0

        axis_value_count = int.from_bytes(stat_data[12:14], "big")
        assert axis_value_count == 1

    def test_single_coordinate_multi_axis_raises(self) -> None:
        """Verify FontParseException when not all axes have coordinates."""
        axes = [
            AxisRecord(tag="wght", min_value=100, default_value=400, max_value=900, flags=0, name_id=256),
            AxisRecord(tag="wdth", min_value=50, default_value=100, max_value=150, flags=0, name_id=257),
        ]
        coordinates = {"wght": 400.0}

        with pytest.raises(FontParseException, match="Missing STAT coordinate for axis"):
            build_static_stat_table(axes, coordinates)

    def test_invalid_axis_tag_length_raises(self) -> None:
        """Verify FontParseException for axis tag length != 4."""
        axes = [AxisRecord(tag="wg", min_value=100, default_value=400, max_value=900, flags=0, name_id=256)]
        coordinates = {"wg": 400.0}

        with pytest.raises(FontParseException, match="Invalid STAT axis tag"):
            build_static_stat_table(axes, coordinates)

    def test_out_of_range_coordinate_raises(self) -> None:
        """Verify FontParseException for coordinate outside Fixed16.16 range."""
        axes = [AxisRecord(tag="wght", min_value=100, default_value=400, max_value=900, flags=0, name_id=256)]
        coordinates = {"wght": 300000.0}

        with pytest.raises(FontParseException, match="outside Fixed16.16 range"):
            build_static_stat_table(axes, coordinates)

    def test_negative_out_of_range_coordinate_raises(self) -> None:
        """Verify FontParseException for negative coordinate outside Fixed16.16 range."""
        axes = [AxisRecord(tag="wght", min_value=100, default_value=400, max_value=900, flags=0, name_id=256)]
        coordinates = {"wght": -300000.0}

        with pytest.raises(FontParseException, match="outside Fixed16.16 range"):
            build_static_stat_table(axes, coordinates)

    def test_round_trip_via_parse_stat_table(self) -> None:
        """Verify synthesized STAT table can be parsed back."""
        axes = [AxisRecord(tag="wght", min_value=100, default_value=400, max_value=900, flags=0, name_id=256)]
        coordinates = {"wght": 400.0}

        stat_data = build_static_stat_table(axes, coordinates)
        parsed = parse_stat_table(stat_data)

        assert parsed is not None
        assert parsed["version"] == "1.1"
        assert len(parsed["design_axes"]) == 1
        assert parsed["design_axes"][0]["tag"] == "wght"
        assert len(parsed["axis_values"]) == 1

    def test_multiple_axes_all_coordinates_required(self) -> None:
        """Verify all axes must have coordinates even with 3+ axes."""
        axes = [
            AxisRecord(tag="wght", min_value=100, default_value=400, max_value=900, flags=0, name_id=256),
            AxisRecord(tag="wdth", min_value=50, default_value=100, max_value=150, flags=0, name_id=257),
            AxisRecord(tag="slnt", min_value=-10, default_value=0, max_value=10, flags=0, name_id=258),
        ]
        coordinates = {"wght": 400.0, "wdth": 100.0}

        with pytest.raises(FontParseException, match="Missing STAT coordinate for axis.*slnt"):
            build_static_stat_table(axes, coordinates)


class TestSynthesizeStatTableEdgeCases:
    """Test synthesize_stat_table edge cases with real fonts."""

    def test_synthesize_with_missing_stat(self, testdata_dir) -> None:
        """Verify synthesis works when STAT is completely absent."""
        from aspose_font import FontLoader, TtfFont
        from aspose_font.serializer import TtfSerializer
        from aspose_font.ttf.tables import TtfTableSet

        roboto_path = testdata_dir / "Roboto-VariableFont_wdth,wght.ttf"
        font = FontLoader.open(str(roboto_path))
        assert isinstance(font, TtfFont)

        raw_tables = {tag: data for tag, data in font.ttf_tables._raw.items() if tag != "STAT"}
        new_tables = TtfTableSet(
            head=font.ttf_tables.head,
            hhea=font.ttf_tables.hhea,
            maxp=font.ttf_tables.maxp,
            os2=font.ttf_tables.os2,
            name=font.ttf_tables.name,
            post=font.ttf_tables.post,
            cmap=font.ttf_tables.cmap,
            loca=font.ttf_tables.loca,
            hmtx=font.ttf_tables.hmtx,
            kern=font.ttf_tables.kern,
            glyf=font.ttf_tables.glyf,
            fvar=font.ttf_tables.fvar,
            _raw=raw_tables,
        )
        modified_font = TtfFont(sfnt_data=b"", tables=new_tables, sfnt_version=font._sfnt_version)
        font_without_stat = FontLoader.open(TtfSerializer.serialize(modified_font))

        stat_data = synthesize_stat_table(font_without_stat)

        assert stat_data is not None
        parsed = parse_stat_table(stat_data)
        assert parsed is not None
        assert len(parsed["design_axes"]) >= 2

    def test_synthesize_round_trip_preserves_data(self, testdata_dir) -> None:
        """Verify synthesized STAT table round-trips through parse_stat_table."""
        from aspose_font import FontLoader, TtfFont
        from aspose_font.serializer import TtfSerializer
        from aspose_font.ttf.tables import TtfTableSet

        roboto_path = testdata_dir / "Roboto-VariableFont_wdth,wght.ttf"
        font = FontLoader.open(str(roboto_path))
        assert isinstance(font, TtfFont)

        raw_tables = {tag: data for tag, data in font.ttf_tables._raw.items() if tag != "STAT"}
        new_tables = TtfTableSet(
            head=font.ttf_tables.head,
            hhea=font.ttf_tables.hhea,
            maxp=font.ttf_tables.maxp,
            os2=font.ttf_tables.os2,
            name=font.ttf_tables.name,
            post=font.ttf_tables.post,
            cmap=font.ttf_tables.cmap,
            loca=font.ttf_tables.loca,
            hmtx=font.ttf_tables.hmtx,
            kern=font.ttf_tables.kern,
            glyf=font.ttf_tables.glyf,
            fvar=font.ttf_tables.fvar,
            _raw=raw_tables,
        )
        modified_font = TtfFont(sfnt_data=b"", tables=new_tables, sfnt_version=font._sfnt_version)
        font_without_stat = FontLoader.open(TtfSerializer.serialize(modified_font))

        stat_data = synthesize_stat_table(font_without_stat)

        parsed = parse_stat_table(stat_data)
        assert parsed is not None
        assert "design_axes" in parsed
        assert "axis_values" in parsed
        assert parsed["version"] == "1.1"

    def test_synthesize_with_non_variable_font_raises(self, testdata_dir) -> None:
        """Verify FontNotSupportedException for static font."""
        from aspose_font import FontLoader
        from aspose_font._exceptions import FontNotSupportedException

        font_path = testdata_dir / "OpenSans-Regular.cff"
        font = FontLoader.open(str(font_path))

        with pytest.raises(FontNotSupportedException, match="not variable"):
            synthesize_stat_table(font)

    def test_synthesize_already_has_stat_returns_none(self, testdata_dir) -> None:
        """Verify synthesize_stat_table returns None when STAT exists."""
        from aspose_font import FontLoader

        roboto_path = testdata_dir / "Roboto-VariableFont_wdth,wght.ttf"
        font = FontLoader.open(str(roboto_path))

        if font.get_table_bytes("STAT") is None:
            pytest.skip("Roboto test font does not have STAT table")

        result = synthesize_stat_table(font)
        assert result is None
