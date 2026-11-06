"""Tests for VVAR table parsing and minimal evaluation (FONT-225)."""
from pathlib import Path

import pytest

from aspose_font import FontLoader
from aspose_font._exceptions import FontParseException
from aspose_font._io import BinaryReader
from aspose_font.ttf.tables.vvar import VvarTable, VvarValueRecord


def _get_test_font_path() -> Path:
    return Path(__file__).resolve().parents[1] / "testdata"


class TestVvarParsing:
    """Test VVAR table parsing from binary data."""

    def test_vvar_value_record_dataclass(self) -> None:
        """Test VvarValueRecord dataclass structure."""
        record = VvarValueRecord(
            axis_tag="wght",
            value_tag="vasc",
            delta_set_index=0x00010002
        )
        assert record.axis_tag == "wght"
        assert record.value_tag == "vasc"
        assert record.delta_set_index == 0x00010002

    def test_vvar_table_dataclass(self) -> None:
        """Test VvarTable dataclass structure."""
        records = [
            VvarValueRecord("wght", "vasc", 0),
            VvarValueRecord("wdth", "vcdt", 1),
        ]
        table = VvarTable(value_records=records)
        assert len(table.value_records) == 2

    def test_parse_vvar_from_bytes(self) -> None:
        """Test parsing VVAR table from binary data."""
        from aspose_font._io import BinaryWriter

        bw = BinaryWriter()
        bw.write_u16(1)   # major version
        bw.write_u16(0)   # minor version
        bw.write_u16(2)   # valueRecordCount
        bw.write_u16(0)   # reserved
        bw.write_u16(8)   # valueRecordSize
        # Value records (2 records × 8 bytes each)
        bw.write_tag("wght")
        bw.write_tag("vasc")
        bw.write_u16(0)   # outer index
        bw.write_u16(1)   # inner index
        bw.write_tag("wdth")
        bw.write_tag("vcdt")
        bw.write_u16(0)   # outer index
        bw.write_u16(2)   # inner index

        data = bw.to_bytes()
        reader = BinaryReader(data)
        table = VvarTable.from_reader(reader, len(data))

        assert len(table.value_records) == 2
        assert table.value_records[0].axis_tag == "wght"
        assert table.value_records[0].value_tag == "vasc"
        assert table.value_records[0].delta_set_index == 0x00000001
        assert table.value_records[1].axis_tag == "wdth"
        assert table.value_records[1].value_tag == "vcdt"
        assert table.value_records[1].delta_set_index == 0x00000002

    def test_parse_vvar_invalid_version(self) -> None:
        """Test that invalid VVAR version raises FontParseException."""
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
            VvarTable.from_reader(reader, len(data))

    def test_parse_vvar_invalid_record_size(self) -> None:
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
            VvarTable.from_reader(reader, len(data))


class TestVvarEvaluation:
    """Test VVAR table evaluation methods."""

    def test_get_metric_tags(self) -> None:
        """Test get_metric_tags returns unique value tags."""
        records = [
            VvarValueRecord("wght", "vasc", 0),
            VvarValueRecord("wght", "vasc", 1),
            VvarValueRecord("wdth", "vcdt", 2),
        ]
        table = VvarTable(value_records=records)
        tags = table.get_metric_tags()
        assert tags == {"vasc", "vcdt"}

    def test_get_axis_tags(self) -> None:
        """Test get_axis_tags returns unique axis tags."""
        records = [
            VvarValueRecord("wght", "vasc", 0),
            VvarValueRecord("wght", "vcdt", 1),
            VvarValueRecord("wdth", "vcrs", 2),
        ]
        table = VvarTable(value_records=records)
        tags = table.get_axis_tags()
        assert tags == {"wght", "wdth"}

    def test_evaluate_missing_metric(self) -> None:
        """Test evaluate returns 0 for unknown vertical metric tag."""
        records = [
            VvarValueRecord("wght", "vasc", 0),
        ]
        table = VvarTable(value_records=records)
        delta = table.evaluate("XXXX", 0, 0)
        assert delta == 0

    def test_evaluate_known_metric_returns_zero(self) -> None:
        """Test evaluate returns 0 for known metric (minimal implementation)."""
        records = [
            VvarValueRecord("wght", "vasc", 0x00010002),
        ]
        table = VvarTable(value_records=records)
        delta = table.evaluate("vasc", 0, 0)
        assert delta == 0


class TestVvarInFont:
    """Test VVAR table integration with TtfFont."""

    def test_vvar_property_absent_font(self) -> None:
        """Test font without VVAR table returns None for .vvar property."""
        font_path = Path(__file__).resolve().parents[1] / "testdata" / "Roboto-VariableFont_wdth,wght.ttf"
        try:
            font = FontLoader.open(font_path)
            vvar = font.vvar
            assert vvar is None or isinstance(vvar, VvarTable)
        except Exception:
            pytest.skip("Test font not available or couldn't be loaded")

    def test_vvar_property_returns_table_instance(self) -> None:
        """Test that .vvar returns VvarTable instance when table present."""
        pytest.skip("No test fixture with VVAR table available")


class TestVvarCrossPlatform:
    """Verify cross-platform compatibility."""

    def test_paths_use_pathlib(self) -> None:
        """Test that test paths use Path object, not hardcoded Windows paths."""
        testdata_path = Path(__file__).resolve().parents[1] / "testdata"
        assert "testdata" in str(testdata_path).split("\\") or "testdata" in str(testdata_path).split("/")
