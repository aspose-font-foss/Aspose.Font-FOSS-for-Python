"""Tests for hinting tables (cvt, fpgm, prep) parsers (FONT-536)."""
import pytest

from aspose_font._exceptions import FontParseException
from aspose_font._io import BinaryReader, BinaryWriter
from aspose_font.ttf.tables.hinting import CvtTable, ProgramTable


class TestCvtTableParsing:
    """Test CVT table parsing from binary data."""

    def test_cvt_table_dataclass(self) -> None:
        """Test CvtTable dataclass structure."""
        table = CvtTable(values=[-100, 0, 250])
        assert table.values == [-100, 0, 250]
        assert len(table.values) == 3

    def test_parse_cvt_empty(self) -> None:
        """Test parsing CVT table with no values (version only)."""
        bw = BinaryWriter()
        bw.write_u16(0)

        data = bw.to_bytes()
        reader = BinaryReader(data)
        table = CvtTable.from_reader(reader, len(data))

        assert table.values == []

    def test_parse_cvt_single_value(self) -> None:
        """Test parsing CVT table with a single control value."""
        bw = BinaryWriter()
        bw.write_u16(0)
        bw.write_i16(-100)

        data = bw.to_bytes()
        reader = BinaryReader(data)
        table = CvtTable.from_reader(reader, len(data))

        assert len(table.values) == 1
        assert table.values[0] == -100

    def test_parse_cvt_multiple_values(self) -> None:
        """Test parsing CVT table with multiple control values (positive and negative)."""
        bw = BinaryWriter()
        bw.write_u16(0)
        bw.write_i16(-100)
        bw.write_i16(0)
        bw.write_i16(250)
        bw.write_i16(1000)
        bw.write_i16(-500)

        data = bw.to_bytes()
        reader = BinaryReader(data)
        table = CvtTable.from_reader(reader, len(data))

        assert len(table.values) == 5
        assert table.values[0] == -100
        assert table.values[1] == 0
        assert table.values[2] == 250
        assert table.values[3] == 1000
        assert table.values[4] == -500

    def test_parse_cvt_odd_length_raises(self) -> None:
        """Test that odd length raises FontParseException."""
        bw = BinaryWriter()
        bw.write_u16(0)
        bw.write_i16(100)

        data = bw.to_bytes()
        reader = BinaryReader(data)

        with pytest.raises(FontParseException):
            CvtTable.from_reader(reader, len(data) + 1)

    def test_parse_cvt_mismatched_length_raises(self) -> None:
        """Test that length doesn't match data size raises FontParseException."""
        bw = BinaryWriter()
        bw.write_u16(0)
        bw.write_i16(100)

        data = bw.to_bytes()
        reader = BinaryReader(data)

        with pytest.raises(FontParseException):
            CvtTable.from_reader(reader, 6)

    def test_cvt_round_trip(self) -> None:
        """Test CVT table serialization roundtrip."""
        original = CvtTable(values=[-100, 0, 250, 1000, -500])
        serialized = original.to_bytes()

        reader = BinaryReader(serialized)
        deserialized = CvtTable.from_reader(reader, len(serialized))

        assert deserialized.values == original.values

    def test_cvt_table_round_trip_binary(self) -> None:
        """Test end-to-end binary write/read cycle."""
        original = CvtTable(values=[-32768, 0, 32767])
        binary = original.to_bytes()

        reader = BinaryReader(binary)
        parsed = CvtTable.from_reader(reader, len(binary))

        assert parsed.values == original.values
        assert len(parsed.to_bytes()) == len(binary)


class TestProgramTableParsing:
    """Test Program table parsing from binary data."""

    def test_program_table_dataclass(self) -> None:
        """Test ProgramTable dataclass structure."""
        table = ProgramTable(code=b"\x00\x01\x02\x03")
        assert table.code == b"\x00\x01\x02\x03"

    def test_parse_fpgm_empty(self) -> None:
        """Test parsing empty font program (0 bytes)."""
        data = b""
        reader = BinaryReader(data)
        table = ProgramTable.from_reader(reader, len(data))

        assert table.code == b""

    def test_parse_fpgm_with_bytecode(self) -> None:
        """Test parsing font program with non-empty bytecode."""
        bytecode = b"\x00\x01\x02\x03\xFF\xFE\xFD\xFC"
        reader = BinaryReader(bytecode)
        table = ProgramTable.from_reader(reader, len(bytecode))

        assert table.code == bytecode

    def test_parse_prep_empty(self) -> None:
        """Test parsing empty control value program."""
        data = b""
        reader = BinaryReader(data)
        table = ProgramTable.from_reader(reader, len(data))

        assert table.code == b""

    def test_parse_prep_with_bytecode(self) -> None:
        """Test parsing control value program with instructions."""
        bytecode = b"\xB0\xB1\xB2\xB3\xFE\xFF"
        reader = BinaryReader(bytecode)
        table = ProgramTable.from_reader(reader, len(bytecode))

        assert table.code == bytecode

    def test_program_round_trip(self) -> None:
        """Test program table serialization roundtrip."""
        original = ProgramTable(code=b"\x00\x01\x02\x03\xFF\xFE\xFD")
        serialized = original.to_bytes()

        assert serialized == original.code

        reader = BinaryReader(serialized)
        deserialized = ProgramTable.from_reader(reader, len(serialized))

        assert deserialized.code == original.code

    def test_parse_program_negative_length_raises(self) -> None:
        """Test that negative length raises FontParseException."""
        data = b""
        reader = BinaryReader(data)

        with pytest.raises(FontParseException):
            ProgramTable.from_reader(reader, -1)


class TestHintingTablesCrossPlatform:
    """Verify cross-platform compatibility."""

    def test_cvt_synthetic_blob(self) -> None:
        """Test CVT parsing with synthetic binary blob (CI compatibility)."""
        cvt_data = (
            b"\x00\x00" +
            b"\xFF\x9C" +
            b"\x00\x00" +
            b"\x00\xFA"
        )
        reader = BinaryReader(cvt_data)
        table = CvtTable.from_reader(reader, len(cvt_data))

        assert table.values == [-100, 0, 250]

    def test_program_synthetic_blob(self) -> None:
        """Test program parsing with synthetic binary blob."""
        bytecode = b"\x00\x01\x02\x03\x04\x05\x06\x07"
        reader = BinaryReader(bytecode)
        table = ProgramTable.from_reader(reader, len(bytecode))

        assert table.code == bytecode

    def test_all_tables_compatible_with_binreader(self) -> None:
        """Verify parsers work with BinaryReader."""
        cvt_data = b"\x00\x00\xFF\xFA\x00\x64"
        cvt_reader = BinaryReader(cvt_data)
        cvt_table = CvtTable.from_reader(cvt_reader, len(cvt_data))
        assert cvt_table.values == [-6, 100]

        prog_data = b"\xAB\xCD\xEF\x12"
        prog_reader = BinaryReader(prog_data)
        prog_table = ProgramTable.from_reader(prog_reader, len(prog_data))
        assert prog_table.code == prog_data


class TestHintingTablesImport:
    """Test module imports and class availability."""

    def test_import_cvt_table(self) -> None:
        """Test importing CvtTable class."""
        from aspose_font.ttf.tables.hinting import CvtTable
        assert CvtTable is not None

    def test_import_program_table(self) -> None:
        """Test importing ProgramTable class."""
        from aspose_font.ttf.tables.hinting import ProgramTable
        assert ProgramTable is not None

    def test_cvt_table_has_required_methods(self) -> None:
        """Test CvtTable has from_reader and to_bytes methods."""
        assert hasattr(CvtTable, "from_reader")
        assert hasattr(CvtTable, "to_bytes")
        assert callable(getattr(CvtTable, "from_reader"))
        assert callable(getattr(CvtTable, "to_bytes"))

    def test_program_table_has_required_methods(self) -> None:
        """Test ProgramTable has from_reader and to_bytes methods."""
        assert hasattr(ProgramTable, "from_reader")
        assert hasattr(ProgramTable, "to_bytes")
        assert callable(getattr(ProgramTable, "from_reader"))
        assert callable(getattr(ProgramTable, "to_bytes"))
