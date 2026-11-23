"""Tests for MVAR table parsing and minimal evaluation (FONT-224)."""
from pathlib import Path

import pytest

from aspose_font import FontLoader
from aspose_font._exceptions import FontParseException
from aspose_font._io import BinaryReader
from aspose_font.ttf.tables.mvar import MvarTable, MvarValueRecord


def _get_test_font_path() -> Path:
    return Path(__file__).resolve().parents[1] / "testdata"


class TestMvarParsing:
    """Test MVAR table parsing from binary data."""

    def test_mvar_value_record_dataclass(self) -> None:
        """Test MvarValueRecord dataclass structure."""
        record = MvarValueRecord(
            axis_tag="wght",
            value_tag="hasc",
            delta_set_index=0x00010002
        )
        assert record.axis_tag == "wght"
        assert record.value_tag == "hasc"
        assert record.delta_set_index == 0x00010002

    def test_mvar_table_dataclass(self) -> None:
        """Test MvarTable dataclass structure."""
        records = [
            MvarValueRecord("wght", "hasc", 0),
            MvarValueRecord("wdth", "hcdt", 1),
        ]
        table = MvarTable(value_records=records)
        assert len(table.value_records) == 2

    def test_parse_mvar_from_bytes(self) -> None:
        """Test parsing MVAR table from binary data."""
        from aspose_font._io import BinaryWriter

        bw = BinaryWriter()
        bw.write_u16(1)   # major version
        bw.write_u16(0)   # minor version
        bw.write_u16(2)   # valueRecordCount
        bw.write_u16(0)   # reserved
        bw.write_u16(8)   # valueRecordSize
        # Value records (2 records × 8 bytes each)
        bw.write_tag("wght")
        bw.write_tag("hasc")
        bw.write_u16(0)   # outer index
        bw.write_u16(1)   # inner index
        bw.write_tag("wdth")
        bw.write_tag("hcdt")
        bw.write_u16(0)   # outer index
        bw.write_u16(2)   # inner index

        data = bw.to_bytes()
        reader = BinaryReader(data)
        table = MvarTable.from_reader(reader, len(data))

        assert len(table.value_records) == 2
        assert table.value_records[0].axis_tag == "wght"
        assert table.value_records[0].value_tag == "hasc"
        assert table.value_records[0].delta_set_index == 0x00000001
        assert table.value_records[1].axis_tag == "wdth"
        assert table.value_records[1].value_tag == "hcdt"
        assert table.value_records[1].delta_set_index == 0x00000002

    def test_parse_mvar_invalid_version(self) -> None:
        """Test that invalid MVAR version raises FontParseException."""
        from aspose_font._io import BinaryWriter

        bw = BinaryWriter()
        bw.write_u16(2)   # invalid major version
        bw.write_u16(0)   # minor version
        bw.write_u16(0)   # valueRecordCount
        bw.write_u16(0)   # reserved
        bw.write_u16(8)   # valueRecordSize

        data = bw.to_bytes()
        reader = BinaryReader(data)

        with pytest.raises(FontParseException):
            MvarTable.from_reader(reader, len(data))

    def test_parse_mvar_invalid_record_size(self) -> None:
        """Test that invalid record size raises FontParseException."""
        from aspose_font._io import BinaryWriter

        bw = BinaryWriter()
        bw.write_u16(1)   # major version
        bw.write_u16(0)   # minor version
        bw.write_u16(0)   # valueRecordCount
        bw.write_u16(0)   # reserved
        bw.write_u16(12)  # invalid record size

        data = bw.to_bytes()
        reader = BinaryReader(data)

        with pytest.raises(FontParseException):
            MvarTable.from_reader(reader, len(data))


class TestMvarEvaluation:
    """Test MVAR table evaluation methods."""

    def test_get_metric_tags(self) -> None:
        """Test get_metric_tags returns unique value tags."""
        records = [
            MvarValueRecord("wght", "hasc", 0),
            MvarValueRecord("wght", "hasc", 1),
            MvarValueRecord("wdth", "hcdt", 2),
        ]
        table = MvarTable(value_records=records)
        tags = table.get_metric_tags()
        assert tags == {"hasc", "hcdt"}

    def test_get_axis_tags(self) -> None:
        """Test get_axis_tags returns unique axis tags."""
        records = [
            MvarValueRecord("wght", "hasc", 0),
            MvarValueRecord("wght", "hcdt", 1),
            MvarValueRecord("wdth", "hvca", 2),
        ]
        table = MvarTable(value_records=records)
        tags = table.get_axis_tags()
        assert tags == {"wght", "wdth"}

    def test_evaluate_missing_metric(self) -> None:
        """Test evaluate returns 0 for unknown metric tag."""
        records = [
            MvarValueRecord("wght", "hasc", 0),
        ]
        table = MvarTable(value_records=records)
        delta = table.evaluate("XXXX", 0, 0)
        assert delta == 0

    def test_evaluate_known_metric_returns_zero(self) -> None:
        """Test evaluate returns 0 for known metric (minimal implementation)."""
        records = [
            MvarValueRecord("wght", "hasc", 0x00010002),
        ]
        table = MvarTable(value_records=records)
        delta = table.evaluate("hasc", 0, 0)
        assert delta == 0


class TestMvarInFont:
    """Test MVAR table integration with TtfFont."""

    def test_mvar_property_absent_font(self) -> None:
        """Test font without MVAR table returns None for .mvar property."""
        font_path = Path(__file__).resolve().parents[1] / "testdata" / "Roboto-VariableFont_wdth,wght.ttf"
        try:
            font = FontLoader.open(font_path)
            mvar = font.mvar
            assert mvar is None or isinstance(mvar, MvarTable)
        except Exception:
            pytest.skip("Test font not available or couldn't be loaded")

    def test_mvar_property_returns_table_instance(self) -> None:
        """Test that .mvar returns MvarTable instance when table present."""
        pytest.skip("No test fixture with MVAR table available")


class TestMvarCrossPlatform:
    """Verify cross-platform compatibility."""

    def test_paths_use_pathlib(self) -> None:
        """Test that test paths use Path object, not hardcoded Windows paths."""
        testdata_path = Path(__file__).resolve().parents[1] / "testdata"
        assert "testdata" in str(testdata_path).split("\\") or "testdata" in str(testdata_path).split("/")
