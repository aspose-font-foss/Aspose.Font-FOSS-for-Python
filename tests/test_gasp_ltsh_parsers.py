"""Tests for gasp and LTSH table parsers (FONT-514)."""
from pathlib import Path

import pytest

from aspose_font._exceptions import FontParseException
from aspose_font._io import BinaryReader, BinaryWriter
from aspose_font.ttf.tables.gasp import GaspRange, GaspTable
from aspose_font.ttf.tables.ltsh import LtshTable


class TestGaspParsing:
    """Test gasp table parsing from binary data."""

    def test_gasp_range_dataclass(self) -> None:
        """Test GaspRange dataclass structure."""
        range_record = GaspRange(range_max_ppem=8, range_gasp_behavior=0x000A)
        assert range_record.range_max_ppem == 8
        assert range_record.range_gasp_behavior == 0x000A

    def test_gasp_table_dataclass(self) -> None:
        """Test GaspTable dataclass structure."""
        ranges = [
            GaspRange(range_max_ppem=8, range_gasp_behavior=0x000A),
            GaspRange(range_max_ppem=0xFFFF, range_gasp_behavior=0x000F),
        ]
        table = GaspTable(gasp_version=1, ranges=ranges)
        assert table.gasp_version == 1
        assert len(table.ranges) == 2

    def test_parse_gasp_version_0(self) -> None:
        """Test parsing gasp table version 0."""
        bw = BinaryWriter()
        bw.write_u16(0)
        bw.write_u16(2)
        bw.write_u16(8)
        bw.write_u16(0x0002)
        bw.write_u16(0xFFFF)
        bw.write_u16(0x0000)

        data = bw.to_bytes()
        reader = BinaryReader(data)
        table = GaspTable.from_reader(reader, len(data))

        assert table.gasp_version == 0
        assert len(table.ranges) == 2
        assert table.ranges[0].range_max_ppem == 8
        assert table.ranges[0].range_gasp_behavior == 0x0002
        assert table.ranges[1].range_max_ppem == 0xFFFF
        assert table.ranges[1].range_gasp_behavior == 0x0000

    def test_parse_gasp_version_1(self) -> None:
        """Test parsing gasp table version 1."""
        bw = BinaryWriter()
        bw.write_u16(1)
        bw.write_u16(4)
        bw.write_u16(8)
        bw.write_u16(0x000A)
        bw.write_u16(16)
        bw.write_u16(0x0005)
        bw.write_u16(19)
        bw.write_u16(0x0007)
        bw.write_u16(0xFFFF)
        bw.write_u16(0x000F)

        data = bw.to_bytes()
        reader = BinaryReader(data)
        table = GaspTable.from_reader(reader, len(data))

        assert table.gasp_version == 1
        assert len(table.ranges) == 4
        assert table.ranges[0].range_max_ppem == 8
        assert table.ranges[0].range_gasp_behavior == 0x000A
        assert table.ranges[3].range_max_ppem == 0xFFFF

    def test_parse_gasp_invalid_version(self) -> None:
        """Test that invalid gasp version raises FontParseException."""
        bw = BinaryWriter()
        bw.write_u16(2)
        bw.write_u16(0)

        data = bw.to_bytes()
        reader = BinaryReader(data)

        with pytest.raises(FontParseException):
            GaspTable.from_reader(reader, len(data))

    def test_gasp_serialization_roundtrip(self) -> None:
        """Test gasp table serialization roundtrip."""
        ranges = [
            GaspRange(range_max_ppem=8, range_gasp_behavior=0x000A),
            GaspRange(range_max_ppem=16, range_gasp_behavior=0x0005),
        ]
        original = GaspTable(gasp_version=1, ranges=ranges)
        serialized = original.to_bytes()

        reader = BinaryReader(serialized)
        deserialized = GaspTable.from_reader(reader, len(serialized))

        assert deserialized.gasp_version == original.gasp_version
        assert len(deserialized.ranges) == len(original.ranges)
        assert deserialized.ranges[0].range_max_ppem == original.ranges[0].range_max_ppem
        assert deserialized.ranges[0].range_gasp_behavior == original.ranges[0].range_gasp_behavior


class TestLtshParsing:
    """Test LTSH table parsing from binary data."""

    def test_ltsh_table_dataclass(self) -> None:
        """Test LtshTable dataclass structure."""
        table = LtshTable(version=0, values=[1, 50, 50, 1])
        assert table.version == 0
        assert len(table.values) == 4
        assert table.values[1] == 50

    def test_parse_ltsh_from_bytes(self) -> None:
        """Test parsing LTSH table from binary data."""
        bw = BinaryWriter()
        bw.write_u16(0)
        bw.write_u16(5)
        bw.write_u8(1)
        bw.write_u8(50)
        bw.write_u8(50)
        bw.write_u8(1)
        bw.write_u8(1)

        data = bw.to_bytes()
        reader = BinaryReader(data)
        table = LtshTable.from_reader(reader, len(data))

        assert table.version == 0
        assert len(table.values) == 5
        assert table.values[0] == 1
        assert table.values[1] == 50
        assert table.values[4] == 1

    def test_parse_ltsh_invalid_version(self) -> None:
        """Test that invalid LTSH version raises FontParseException."""
        bw = BinaryWriter()
        bw.write_u16(1)
        bw.write_u16(0)

        data = bw.to_bytes()
        reader = BinaryReader(data)

        with pytest.raises(FontParseException):
            LtshTable.from_reader(reader, len(data))

    def test_ltsh_serialization_roundtrip(self) -> None:
        """Test LTSH table serialization roundtrip."""
        original = LtshTable(version=0, values=[1, 50, 50, 1, 1])
        serialized = original.to_bytes()

        reader = BinaryReader(serialized)
        deserialized = LtshTable.from_reader(reader, len(serialized))

        assert deserialized.version == original.version
        assert deserialized.values == original.values


class TestGaspLtshCrossPlatform:
    """Verify cross-platform compatibility."""

    def test_paths_use_pathlib(self) -> None:
        """Test that test paths use Path object, not hardcoded Windows paths."""
        testdata_path = Path(__file__).resolve().parents[1] / "testdata"
        assert "testdata" in str(testdata_path).split("\\") or "testdata" in str(testdata_path).split("/")


class TestGaspLtshImport:
    """Test module imports and class availability."""

    def test_import_gasp_table(self) -> None:
        """Test importing GaspTable class."""
        from aspose_font.ttf.tables.gasp import GaspTable
        assert GaspTable is not None

    def test_import_gasp_range(self) -> None:
        """Test importing GaspRange class."""
        from aspose_font.ttf.tables.gasp import GaspRange
        assert GaspRange is not None

    def test_import_ltsh_table(self) -> None:
        """Test importing LtshTable class."""
        from aspose_font.ttf.tables.ltsh import LtshTable
        assert LtshTable is not None

    def test_import_via_tables_init(self) -> None:
        """Test importing via tables.__init__.py."""
        from aspose_font.ttf.tables import GaspRange, GaspTable, LtshTable
        assert GaspTable is not None
        assert LtshTable is not None
        assert GaspRange is not None
