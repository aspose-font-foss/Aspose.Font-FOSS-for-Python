"""Tests for STAT table synthesis from fvar axes and named instances."""

from pathlib import Path

import pytest

from aspose_font import FontLoader, TtfFont
from aspose_font._exceptions import FontNotSupportedException
from aspose_font.ttf.tables.stat import synthesize_stat_table


@pytest.fixture
def variable_font_without_stat(testdata_dir: Path) -> TtfFont:
    """Create a variable font that lacks STAT table for testing.

    Uses Roboto as base and removes STAT if present.
    """
    roboto_path = testdata_dir / "Roboto-VariableFont_wdth,wght.ttf"
    font = FontLoader.open(str(roboto_path))
    assert isinstance(font, TtfFont)

    has_stat = font.ttf_tables._raw.get("STAT") is not None
    if not has_stat:
        return font

    from aspose_font.serializer import TtfSerializer
    from aspose_font.ttf.tables import TtfTableSet

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
    return FontLoader.open(TtfSerializer.serialize(modified_font))


@pytest.fixture
def variable_font_with_stat(testdata_dir: Path) -> TtfFont:
    """Load a font that has STAT table (Roboto)."""
    roboto_path = testdata_dir / "Roboto-VariableFont_wdth,wght.ttf"
    font = FontLoader.open(str(roboto_path))
    assert isinstance(font, TtfFont)
    return font


class TestSynthesizeStatTable:
    """Test synthesize_stat_table function."""

    def test_synthesize_stat_table_basic(self, variable_font_without_stat: TtfFont) -> None:
        """Verify STAT table is synthesized from fvar axes and instances."""
        stat_data = synthesize_stat_table(variable_font_without_stat)

        assert stat_data is not None
        assert len(stat_data) > 0

        header_version = int.from_bytes(stat_data[0:4], "big")
        major_version = header_version >> 16
        minor_version = header_version & 0xFFFF
        assert major_version == 1
        assert minor_version == 1

        design_axis_count = int.from_bytes(stat_data[6:8], "big")
        assert design_axis_count > 0

        axis_value_count = int.from_bytes(stat_data[12:14], "big")
        assert axis_value_count > 0

    def test_synthesize_stat_table_axis_order(self, variable_font_without_stat: TtfFont) -> None:
        """Verify axes are ordered in standard OpenType order."""
        stat_data = synthesize_stat_table(variable_font_without_stat)

        design_axes_offset = int.from_bytes(stat_data[8:12], "big")
        design_axis_count = int.from_bytes(stat_data[6:8], "big")

        axis_tags = []
        for i in range(design_axis_count):
            axis_offset = design_axes_offset + i * 8
            tag_bytes = stat_data[axis_offset : axis_offset + 4]
            axis_tags.append(tag_bytes.decode("ascii"))

        assert axis_tags[0] == "wght", "wght should be first in standard order (display_order=10)"
        assert axis_tags[1] == "wdth", "wdth should be second (display_order=20)"

    def test_synthesize_stat_table_named_instances(self, variable_font_without_stat: TtfFont) -> None:
        """Verify AxisValue records are created for all named instances."""
        stat_data = synthesize_stat_table(variable_font_without_stat)

        axis_value_count = int.from_bytes(stat_data[12:14], "big")
        axis_values_offset = int.from_bytes(stat_data[14:18], "big")

        axis_value_offsets = []
        for i in range(axis_value_count):
            offset_delta = int.from_bytes(stat_data[axis_values_offset + i * 2 : axis_values_offset + (i + 1) * 2], "big")
            axis_value_offsets.append(axis_values_offset + offset_delta)

        assert axis_value_count > 0
        assert len(axis_value_offsets) == axis_value_count

        for offset in axis_value_offsets:
            value_format = int.from_bytes(stat_data[offset : offset + 2], "big")
            assert value_format == 4, "AllAxisValue records should be Format 4"

    def test_synthesize_stat_table_elidable_flags(self, variable_font_without_stat: TtfFont) -> None:
        """Verify ELIDABLE_AXIS_VALUE_NAME flag (0x0002) is set."""
        stat_data = synthesize_stat_table(variable_font_without_stat)

        axis_value_count = int.from_bytes(stat_data[12:14], "big")
        axis_values_offset = int.from_bytes(stat_data[14:18], "big")

        for i in range(axis_value_count):
            offset_delta = int.from_bytes(stat_data[axis_values_offset + i * 2 : axis_values_offset + (i + 1) * 2], "big")
            value_offset = axis_values_offset + offset_delta
            flags = int.from_bytes(stat_data[value_offset + 2 : value_offset + 4], "big")
            assert flags & 0x0002, "ELIDABLE_AXIS_VALUE_NAME flag should be set"

    def test_synthesize_stat_table_round_trip(self, variable_font_without_stat: TtfFont) -> None:
        """Verify serialized STAT table can be parsed back."""
        from aspose_font._io import BinaryReader

        stat_data = synthesize_stat_table(variable_font_without_stat)

        assert len(stat_data) >= 20

        major_version = int.from_bytes(stat_data[0:2], "big")
        minor_version = int.from_bytes(stat_data[2:4], "big")
        assert (major_version, minor_version) == (1, 1)

        design_axis_size = int.from_bytes(stat_data[4:6], "big")
        assert design_axis_size == 8

        design_axes_offset = int.from_bytes(stat_data[8:12], "big")
        assert design_axes_offset == 20

        axis_value_count = int.from_bytes(stat_data[12:14], "big")
        axis_values_offset = int.from_bytes(stat_data[14:18], "big")

        # Verify we can parse axis values using BinaryReader
        reader = BinaryReader(stat_data)
        reader.seek(axis_values_offset)

        # Read offset deltas and verify axis value records
        parsed_axes = []
        for i in range(axis_value_count):
            offset_delta = reader.read_u16()
            parsed_axes.append(offset_delta)

        assert len(parsed_axes) == axis_value_count
        assert parsed_axes[0] == 36  # First offset delta should be 36 (offset 72 - offset 36)

    def test_synthesize_stat_table_no_stat_skipped(self, variable_font_with_stat: TtfFont) -> None:
        """Verify None is returned when font already has STAT table."""
        if variable_font_with_stat.get_table_bytes("STAT") is None:
            pytest.skip("Roboto test font doesn't have STAT table")

        result = synthesize_stat_table(variable_font_with_stat)

        assert result is None

    def test_synthesize_stat_table_already_has_stat_returns_none(self, variable_font_with_stat: TtfFont) -> None:
        """Verify synthesize_stat_table returns None when STAT already exists."""
        if variable_font_with_stat.get_table_bytes("STAT") is None:
            pytest.skip("Roboto test font doesn't have STAT table")

        result = synthesize_stat_table(variable_font_with_stat)
        assert result is None

    def test_synthesize_stat_table_non_variable_font(self) -> None:
        """Verify FontNotSupportedException for static fonts."""
        from pathlib import Path

        font_path = Path(__file__).resolve().parent.parent / "testdata" / "OpenSans-Regular.cff"
        font = FontLoader.open(str(font_path))

        with pytest.raises(FontNotSupportedException, match="not variable"):
            synthesize_stat_table(font)


class TestSmartInstancerSynthesize:
    """Test SmartInstancer.synthesize_missing_stat_table method."""

    def test_smart_instancer_synthesize_missing(self, variable_font_without_stat: TtfFont) -> None:
        """Verify SmartInstancer synthesizes STAT when missing."""
        from aspose_font.instancing import SmartInstancer

        instancer = SmartInstancer(variable_font_without_stat)
        stat_data = instancer.synthesize_missing_stat_table()

        assert stat_data is not None
        assert len(stat_data) > 0

        major_version = int.from_bytes(stat_data[0:2], "big")
        minor_version = int.from_bytes(stat_data[2:4], "big")
        assert (major_version, minor_version) == (1, 1)

    def test_smart_instancer_skip_existing(self, variable_font_with_stat: TtfFont) -> None:
        """Verify SmartInstancer returns None when STAT exists."""
        from aspose_font.instancing import SmartInstancer

        if variable_font_with_stat.get_table_bytes("STAT") is None:
            pytest.skip("Roboto test font doesn't have STAT table")

        instancer = SmartInstancer(variable_font_with_stat)
        result = instancer.synthesize_missing_stat_table()

        assert result is None


class TestSynthesizeStatTableEdgeCases:
    """Test edge cases for STAT synthesis."""

    def test_synthesize_stat_table_single_axis(self) -> None:
        """Verify synthesis works with single-axis variable font."""
        # Use a simple single-axis font for testing
        # Create a minimal font with just wght axis


        # Create a minimal valid font with single wght axis
        # This is a simplified approach - just test with a real font

        # Skip this test since we don't have a single-axis test font
        # The existing roboto font has 2 axes, so this test is N/A
        pytest.skip("No single-axis test font available")
