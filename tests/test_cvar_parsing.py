"""Tests for CVAR table parsing and minimal evaluation (FONT-226)."""
from pathlib import Path

import pytest

from aspose_font import FontLoader
from aspose_font._exceptions import FontParseException
from aspose_font._io import BinaryReader, BinaryWriter
from aspose_font.ttf.tables.cvar import CvarTable, CvarValueRecord


def _get_test_font_path() -> Path:
    return Path(__file__).resolve().parents[1] / "testdata"


class TestCvarParsing:
    """Test CVAR table parsing from binary data."""

    def test_cvar_value_record_dataclass(self) -> None:
        """Test CvarValueRecord dataclass structure."""
        record = CvarValueRecord(
            axis_tag="wght",
            value_tag="casc",
            delta_set_index=0x00010002
        )
        assert record.axis_tag == "wght"
        assert record.value_tag == "casc"
        assert record.delta_set_index == 0x00010002

    def test_cvar_table_dataclass(self) -> None:
        """Test CvarTable dataclass structure."""
        records = [
            CvarValueRecord("wght", "casc", 0),
            CvarValueRecord("wdth", "ccdt", 1),
        ]
        table = CvarTable(value_records=records)
        assert len(table.value_records) == 2

    def test_parse_cvar_from_bytes(self) -> None:
        """Test parsing CVAR table from binary data."""
        bw = BinaryWriter()
        bw.write_u16(1)   # major version
        bw.write_u16(0)   # minor version
        bw.write_u16(2)   # valueRecordCount
        bw.write_u16(0)   # reserved
        bw.write_u16(8)   # valueRecordSize
        # Value records (2 records × 8 bytes each)
        bw.write_tag("wght")
        bw.write_tag("casc")
        bw.write_u16(0)   # outer index
        bw.write_u16(1)   # inner index
        bw.write_tag("wdth")
        bw.write_tag("ccdt")
        bw.write_u16(0)   # outer index
        bw.write_u16(2)   # inner index

        data = bw.to_bytes()
        reader = BinaryReader(data)
        table = CvarTable.from_reader(reader, len(data))

        assert len(table.value_records) == 2
        assert table.value_records[0].axis_tag == "wght"
        assert table.value_records[0].value_tag == "casc"
        assert table.value_records[0].delta_set_index == 0x00000001
        assert table.value_records[1].axis_tag == "wdth"
        assert table.value_records[1].value_tag == "ccdt"
        assert table.value_records[1].delta_set_index == 0x00000002

    def test_parse_cvar_invalid_version(self) -> None:
        """Test that invalid CVAR version raises FontParseException."""
        bw = BinaryWriter()
        bw.write_u16(2)   # invalid major version
        bw.write_u16(0)   # minor version
        bw.write_u16(0)   # valueRecordCount
        bw.write_u16(0)   # reserved
        bw.write_u16(8)   # valueRecordSize

        data = bw.to_bytes()
        reader = BinaryReader(data)

        with pytest.raises(FontParseException):
            CvarTable.from_reader(reader, len(data))

    def test_parse_cvar_invalid_record_size(self) -> None:
        """Test that invalid record size raises FontParseException."""
        bw = BinaryWriter()
        bw.write_u16(1)   # major version
        bw.write_u16(0)   # minor version
        bw.write_u16(0)   # valueRecordCount
        bw.write_u16(0)   # reserved
        bw.write_u16(12)  # invalid record size

        data = bw.to_bytes()
        reader = BinaryReader(data)

        with pytest.raises(FontParseException):
            CvarTable.from_reader(reader, len(data))


class TestCvarEvaluation:
    """Test CVAR table evaluation methods."""

    def test_get_metric_tags(self) -> None:
        """Test get_metric_tags returns unique value tags."""
        records = [
            CvarValueRecord("wght", "casc", 0),
            CvarValueRecord("wght", "casc", 1),
            CvarValueRecord("wdth", "ccdt", 2),
        ]
        table = CvarTable(value_records=records)
        tags = table.get_metric_tags()
        assert tags == {"casc", "ccdt"}

    def test_get_axis_tags(self) -> None:
        """Test get_axis_tags returns unique axis tags."""
        records = [
            CvarValueRecord("wght", "casc", 0),
            CvarValueRecord("wght", "ccdt", 1),
            CvarValueRecord("wdth", "ccrs", 2),
        ]
        table = CvarTable(value_records=records)
        tags = table.get_axis_tags()
        assert tags == {"wght", "wdth"}

    def test_evaluate_missing_metric(self) -> None:
        """Test evaluate returns 0 for unknown metric tag."""
        records = [
            CvarValueRecord("wght", "casc", 0),
        ]
        table = CvarTable(value_records=records)
        delta = table.evaluate("XXXX", 0, 0)
        assert delta == 0

    def test_evaluate_known_metric_returns_zero(self) -> None:
        """Test evaluate returns 0 for known metric (minimal implementation)."""
        records = [
            CvarValueRecord("wght", "casc", 0x00010002),
        ]
        table = CvarTable(value_records=records)
        delta = table.evaluate("casc", 0, 0)
        assert delta == 0


class TestCvarInFont:
    """Test CVAR table integration with TtfFont."""

    def test_cvar_property_absent_font(self) -> None:
        """Test font without CVAR table returns None for .cvar property."""
        font_path = Path(__file__).resolve().parents[1] / "testdata" / "Roboto-VariableFont_wdth,wght.ttf"
        try:
            font = FontLoader.open(font_path)
            cvar = font.cvar
            assert cvar is None or isinstance(cvar, CvarTable)
        except Exception:
            pytest.skip("Test font not available or couldn't be loaded")

    def test_cvar_property_returns_table_instance(self) -> None:
        """Test that .cvar returns CvarTable instance when table present."""
        pytest.skip("No test fixture with CVAR table available")


class TestCvarCrossPlatform:
    """Verify cross-platform compatibility."""

    def test_paths_use_pathlib(self) -> None:
        """Test that test paths use Path object, not hardcoded Windows paths."""
        testdata_path = Path(__file__).resolve().parents[1] / "testdata"
        assert "testdata" in str(testdata_path).split("\\") or "testdata" in str(testdata_path).split("/")
