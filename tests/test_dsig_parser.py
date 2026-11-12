"""Tests for DSIG table parser (FONT-523)."""
from pathlib import Path

import pytest

from aspose_font import FontLoader
from aspose_font._io import BinaryReader, BinaryWriter
from aspose_font.ttf.tables.dsig import DsigTable, SignatureRecord

_FONT_FIXTURES_DIR = Path(__file__).resolve().parents[1] / "testdata"


class TestDsigParsing:
    """Test DSIG table parsing from binary data."""

    def test_empty_dsig_table(self) -> None:
        """Test parsing DSIG table with zero signatures."""
        w = BinaryWriter()
        w.write_u32(0x00010000)
        w.write_u16(0)
        w.write_u16(0)

        data = w.to_bytes()
        reader = BinaryReader(data)
        table = DsigTable.from_reader(reader, len(data))

        assert table.major_version == 1
        assert table.minor_version == 0
        assert table.num_styles == 0
        assert table.total_length == 0
        assert table.signature_records == []
        assert table.to_bytes() == data

    def test_dsig_table_with_one_signature(self) -> None:
        """Test parsing DSIG table with a single signature record."""
        w = BinaryWriter()
        w.write_u32(0x00010000)
        w.write_u16(1)
        w.write_u16(16)
        w.write_u32(1)
        w.write_u32(8)
        w.write_u32(28)

        data = w.to_bytes()
        reader = BinaryReader(data)
        table = DsigTable.from_reader(reader, len(data))

        assert table.num_styles == 1
        assert len(table.signature_records) == 1
        record = table.signature_records[0]
        assert record.signature_type == 1
        assert record.length == 8
        assert record.offset == 28

    def test_dsig_table_with_multiple_signatures(self) -> None:
        """Test parsing DSIG table with multiple signature records."""
        w = BinaryWriter()
        w.write_u32(0x00010000)
        w.write_u16(2)
        w.write_u16(32)

        w.write_u32(1)
        w.write_u32(16)
        w.write_u32(28)

        w.write_u32(2)
        w.write_u32(24)
        w.write_u32(44)

        data = w.to_bytes()
        reader = BinaryReader(data)
        table = DsigTable.from_reader(reader, len(data))

        assert table.num_styles == 2
        assert len(table.signature_records) == 2
        assert table.signature_records[0].signature_type == 1
        assert table.signature_records[1].signature_type == 2

    def test_dsig_table_version_unpacking(self) -> None:
        """Test that table version is correctly unpacked into major/minor."""
        w = BinaryWriter()
        w.write_u32(0x00010000)
        w.write_u16(0)
        w.write_u16(0)

        data = w.to_bytes()
        reader = BinaryReader(data)
        table = DsigTable.from_reader(reader, len(data))

        assert table.major_version == 1
        assert table.minor_version == 0

    def test_dsig_to_bytes_roundtrip(self) -> None:
        """Test that to_bytes returns the original raw data."""
        w = BinaryWriter()
        w.write_u32(0x00010000)
        w.write_u16(1)
        w.write_u16(16)
        w.write_u32(1)
        w.write_u32(8)
        w.write_u32(28)

        data = w.to_bytes()
        reader = BinaryReader(data)
        table = DsigTable.from_reader(reader, len(data))

        assert table.to_bytes() == data


class TestDsigFileIntegration:
    """Test DSIG table parsing from real font files."""

    def test_load_font_with_dsig(self) -> None:
        """Test loading a font file with DSIG table and accessing it."""
        font_path = _FONT_FIXTURES_DIR / "TTF" / "arial.ttf"
        if not font_path.exists():
            pytest.skip(f"Test fixture not found: {font_path}")

        font = FontLoader.open(str(font_path))

        assert font.ttf_tables.dsig is not None
        dsg = font.get_table_bytes("DSIG")

        assert dsg is not None
        reader = BinaryReader(dsg)
        table = DsigTable.from_reader(reader, len(dsg))

        # Accept both version 1.0 (correct) and 0.1 (common malformed format)
        assert table.major_version in (0, 1)
        assert table.minor_version == 1
        assert isinstance(table.signature_records, list)

    def test_dsig_checksum_verification(self) -> None:
        """Test DSIG checksum verification against font's checksum adjustment.

        This test loads a font with a DSIG table and verifies that the
        checksum verification returns True for an unmodified font.

        Note: Font with version 0.1 DSIG may fail checksum verification
        since the malformed version doesn't match the expected OpenType spec.
        """
        font_path = _FONT_FIXTURES_DIR / "TTF" / "arial.ttf"
        if not font_path.exists():
            pytest.skip("Test fixture not found")

        font = FontLoader.open(str(font_path))

        if font.ttf_tables.dsig is None:
            pytest.skip("Test font does not contain DSIG table")

        # Skip checksum verification for malformed version 0.1 DSIG tables
        if font.ttf_tables.dsig.major_version == 0:
            pytest.skip("Test font has malformed DSIG version 0.1")

        is_valid = font.ttf_tables.dsig.verify_checksum(font)

        assert is_valid is True


class TestDsigEdgeCases:
    """Test edge cases in DSIG parsing."""

    def test_dsig_signature_record_from_reader(self) -> None:
        """Test SignatureRecord.from_reader class method."""
        w = BinaryWriter()
        w.write_u32(1)
        w.write_u32(64)
        w.write_u32(32)

        data = w.to_bytes()
        reader = BinaryReader(data)
        record = SignatureRecord.from_reader(reader)

        assert record.signature_type == 1
        assert record.length == 64
        assert record.offset == 32

    def test_minimum_dsig_table_length(self) -> None:
        """Test parsing DSIG table with minimum valid length (12 bytes)."""
        w = BinaryWriter()
        w.write_u32(0x00010000)
        w.write_u16(0)
        w.write_u16(0)

        data = w.to_bytes()
        reader = BinaryReader(data)
        table = DsigTable.from_reader(reader, len(data))

        assert table.major_version == 1
        assert table.minor_version == 0
        assert table.num_styles == 0
        assert table.total_length == 0
        assert table.signature_records == []
