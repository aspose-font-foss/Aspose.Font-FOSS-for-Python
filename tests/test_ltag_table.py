"""Tests for ltag table parsing (FONT-504)."""
import pytest

from aspose_font._exceptions import FontParseException
from aspose_font._io import BinaryReader, BinaryWriter
from aspose_font.ttf.tables.ltag import LtagTable


def _pack_u16(value: int) -> bytes:
    return value.to_bytes(2, "big")


def _pack_tag(tag: str) -> bytes:
    return tag.encode("ascii") + b"\x00"


class TestLtagParsing:
    """Test ltag table parsing from binary data."""

    def test_empty_ltag_table(self) -> None:
        """Test parsing ltag table with zero tags."""
        bw = BinaryWriter()
        bw.write_u16(1)
        bw.write_u16(0)
        bw.write_u16(0)

        data = bw.to_bytes()
        reader = BinaryReader(data)
        table = LtagTable.from_reader(reader, len(data))

        assert table.major_version == 1
        assert table.minor_version == 0
        assert len(table) == 0
        assert table.tags == []

    def test_single_ltag(self) -> None:
        """Test parsing ltag table with single tag."""
        tag = b"en\x00"
        tag_offset = 8
        bw = BinaryWriter()
        bw.write_u16(1)
        bw.write_u16(0)
        bw.write_u16(1)
        bw.write_u16(tag_offset)
        bw.write_bytes(tag)

        data = bw.to_bytes()
        reader = BinaryReader(data)
        table = LtagTable.from_reader(reader, len(data))

        assert len(table) == 1
        assert table.tags[0] == "en"

    def test_multiple_ltags(self) -> None:
        """Test parsing ltag table with multiple tags."""
        tag1 = b"en\x00"
        tag2 = b"zh-Hans\x00"
        tag3 = b"sr-Latn\x00"
        offset1 = 12
        offset2 = offset1 + len(tag1)
        offset3 = offset2 + len(tag2)

        bw = BinaryWriter()
        bw.write_u16(1)
        bw.write_u16(0)
        bw.write_u16(3)
        bw.write_u16(offset1)
        bw.write_u16(offset2)
        bw.write_u16(offset3)
        bw.write_bytes(tag1)
        bw.write_bytes(tag2)
        bw.write_bytes(tag3)

        data = bw.to_bytes()
        reader = BinaryReader(data)
        table = LtagTable.from_reader(reader, len(data))

        assert len(table) == 3
        assert table.tags[0] == "en"
        assert table.tags[1] == "zh-Hans"
        assert table.tags[2] == "sr-Latn"

    def test_get_language_tag(self) -> None:
        """Test get_language_tag() helper method."""
        tag1 = b"fr\x00"
        tag2 = b"ja\x00"
        offset1 = 10
        offset2 = offset1 + len(tag1)

        bw = BinaryWriter()
        bw.write_u16(1)
        bw.write_u16(0)
        bw.write_u16(2)
        bw.write_u16(offset1)
        bw.write_u16(offset2)
        bw.write_bytes(tag1)
        bw.write_bytes(tag2)

        data = bw.to_bytes()
        reader = BinaryReader(data)
        table = LtagTable.from_reader(reader, len(data))

        assert table.get_language_tag(0) == "fr"
        assert table.get_language_tag(1) == "ja"

    def test_get_language_tag_index_error(self) -> None:
        """Test get_language_tag() raises IndexError for invalid index."""
        tag = b"en\x00"
        offset = 8

        bw = BinaryWriter()
        bw.write_u16(1)
        bw.write_u16(0)
        bw.write_u16(1)
        bw.write_u16(offset)
        bw.write_bytes(tag)

        data = bw.to_bytes()
        reader = BinaryReader(data)
        table = LtagTable.from_reader(reader, len(data))

        with pytest.raises(IndexError):
            table.get_language_tag(5)

    def test_invalid_version_raises_font_parse_exception(self) -> None:
        """Test that unsupported ltag version raises FontParseException."""
        bw = BinaryWriter()
        bw.write_u16(2)
        bw.write_u16(0)
        bw.write_u16(0)

        data = bw.to_bytes()
        reader = BinaryReader(data)

        with pytest.raises(FontParseException):
            LtagTable.from_reader(reader, len(data))

    def test_ltag_dataclass_properties(self) -> None:
        """Test LtagTable dataclass properties and structure."""
        table = LtagTable(
            major_version=1,
            minor_version=0,
            tags=["en", "fr", "de"],
            _raw=b"",
        )

        assert table.major_version == 1
        assert table.minor_version == 0
        assert len(table) == 3
        assert table.tags[1] == "fr"


class TestLtagEdgeCases:
    """Test edge cases in ltag parsing."""

    def test_single_char_tag(self) -> None:
        """Test parsing single-character language code."""
        tag = b"z\x00"
        offset = 8

        bw = BinaryWriter()
        bw.write_u16(1)
        bw.write_u16(0)
        bw.write_u16(1)
        bw.write_u16(offset)
        bw.write_bytes(tag)

        data = bw.to_bytes()
        reader = BinaryReader(data)
        table = LtagTable.from_reader(reader, len(data))

        assert table.tags[0] == "z"

    def test_tag_with_multiple_dashes(self) -> None:
        """Test parsing BCP-47 tag with multiple subtags (e.g., zh-Hans-CN)."""
        tag = b"zh-Hans-CN\x00"
        offset = 8

        bw = BinaryWriter()
        bw.write_u16(1)
        bw.write_u16(0)
        bw.write_u16(1)
        bw.write_u16(offset)
        bw.write_bytes(tag)

        data = bw.to_bytes()
        reader = BinaryReader(data)
        table = LtagTable.from_reader(reader, len(data))

        assert table.tags[0] == "zh-Hans-CN"

    def test_max_uint16_count(self) -> None:
        """Test that count field is properly read as uint16 with empty strings."""
        count = 3

        bw = BinaryWriter()
        bw.write_u16(1)
        bw.write_u16(0)
        bw.write_u16(count)

        for _ in range(count):
            bw.write_u16(8 + count * 2)  # offset to end of header

        for _ in range(count):
            bw.write_bytes(b"\x00")  # empty tag

        data = bw.to_bytes()
        reader = BinaryReader(data)
        table = LtagTable.from_reader(reader, len(data))

        assert len(table) == count
        assert all(tag == "" for tag in table.tags)

    def test_to_bytes_roundtrip(self) -> None:
        """Test that to_bytes returns the original raw data."""
        tag1 = b"en\x00"
        tag2 = b"fr\x00"
        offset1 = 10
        offset2 = offset1 + len(tag1)

        bw = BinaryWriter()
        bw.write_u16(1)
        bw.write_u16(0)
        bw.write_u16(2)
        bw.write_u16(offset1)
        bw.write_u16(offset2)
        bw.write_bytes(tag1)
        bw.write_bytes(tag2)

        data = bw.to_bytes()
        reader = BinaryReader(data)
        table = LtagTable.from_reader(reader, len(data))

        assert table.to_bytes() == data
