"""Tests for meta table parsing (FONT-517)."""
import pytest

from aspose_font._exceptions import FontParseException
from aspose_font._io import BinaryReader, BinaryWriter
from aspose_font.ttf.tables.meta import MetaTable


def _pack_u32(value: int) -> bytes:
    return value.to_bytes(4, "big")


def _pack_tag(tag: str) -> bytes:
    return tag.encode("ascii").ljust(4, b"\x00")


class TestMetaParsing:
    """Test meta table parsing from binary data."""

    def test_empty_meta_table(self) -> None:
        """Test parsing meta table with zero data maps."""
        bw = BinaryWriter()
        bw.write_u32(1)
        bw.write_u32(0)
        bw.write_u32(0)
        bw.write_u32(0)

        data = bw.to_bytes()
        reader = BinaryReader(data)
        table = MetaTable.from_reader(reader, len(data))

        assert table.major_version == 1
        assert table.minor_version == 0
        assert table.flags == 0
        assert len(table) == 0
        assert table.data_maps == {}
        assert table.design_languages == []
        assert table.supported_languages == []

    def test_meta_table_with_dlng(self) -> None:
        """Test parsing meta table with dlng (design languages) tag."""
        dlng_data = b"Latn,Cyrl"
        data_offset = 28
        data_length = len(dlng_data)

        bw = BinaryWriter()
        bw.write_u32(1)
        bw.write_u32(0)
        bw.write_u32(0)
        bw.write_u32(1)
        bw.write_bytes(_pack_tag("dlng"))
        bw.write_u32(data_offset)
        bw.write_u32(data_length)
        bw.write_bytes(dlng_data)

        data = bw.to_bytes()
        reader = BinaryReader(data)
        table = MetaTable.from_reader(reader, len(data))

        assert len(table) == 1
        assert "dlng" in table.data_maps
        assert table.get_tag_data("dlng") == dlng_data
        assert table.design_languages == ["Latn", "Cyrl"]
        assert table.supported_languages == []

    def test_meta_table_with_slng(self) -> None:
        """Test parsing meta table with slng (supported languages) tag."""
        slng_data = b"Latn,Cyrl,Grek"
        data_offset = 28
        data_length = len(slng_data)

        bw = BinaryWriter()
        bw.write_u32(1)
        bw.write_u32(0)
        bw.write_u32(0)
        bw.write_u32(1)
        bw.write_bytes(_pack_tag("slng"))
        bw.write_u32(data_offset)
        bw.write_u32(data_length)
        bw.write_bytes(slng_data)

        data = bw.to_bytes()
        reader = BinaryReader(data)
        table = MetaTable.from_reader(reader, len(data))

        assert "slng" in table.data_maps
        assert table.get_tag_data("slng") == slng_data
        assert table.supported_languages == ["Latn", "Cyrl", "Grek"]
        assert table.design_languages == []

    def test_meta_table_with_both_dlng_and_slng(self) -> None:
        """Test parsing meta table with both dlng and slng tags."""
        dlng_data = b"Latn"
        slng_data = b"Latn,Cyrl,Grek"

        data_offset = 40
        dlng_offset = data_offset
        slng_offset = dlng_offset + len(dlng_data)

        bw = BinaryWriter()
        bw.write_u32(1)
        bw.write_u32(0)
        bw.write_u32(0)
        bw.write_u32(2)

        bw.write_bytes(_pack_tag("dlng"))
        bw.write_u32(dlng_offset)
        bw.write_u32(len(dlng_data))

        bw.write_bytes(_pack_tag("slng"))
        bw.write_u32(slng_offset)
        bw.write_u32(len(slng_data))

        bw.write_bytes(dlng_data)
        bw.write_bytes(slng_data)

        data = bw.to_bytes()
        reader = BinaryReader(data)
        table = MetaTable.from_reader(reader, len(data))

        assert table.design_languages == ["Latn"]
        assert table.supported_languages == ["Latn", "Cyrl", "Grek"]

    def test_meta_table_with_appl_and_bild(self) -> None:
        """Test parsing meta table with appl and bild reserved tags (binary data)."""
        appl_data = b"\x00\x01\x02\x03"
        bild_data = b"\x04\x05\x06\x07"

        data_offset = 40
        appl_offset = data_offset
        bild_offset = appl_offset + len(appl_data)

        bw = BinaryWriter()
        bw.write_u32(1)
        bw.write_u32(0)
        bw.write_u32(0)
        bw.write_u32(2)

        bw.write_bytes(_pack_tag("appl"))
        bw.write_u32(appl_offset)
        bw.write_u32(len(appl_data))

        bw.write_bytes(_pack_tag("bild"))
        bw.write_u32(bild_offset)
        bw.write_u32(len(bild_data))

        bw.write_bytes(appl_data)
        bw.write_bytes(bild_data)

        data = bw.to_bytes()
        reader = BinaryReader(data)
        table = MetaTable.from_reader(reader, len(data))

        assert table.get_tag_data("appl") == appl_data
        assert table.get_tag_data("bild") == bild_data
        assert table.design_languages == []
        assert table.supported_languages == []

    def test_meta_table_with_custom_tag(self) -> None:
        """Test parsing meta table with custom vendor tag."""
        custom_data = b"custom metadata"
        data_offset = 28
        custom_offset = data_offset
        custom_length = len(custom_data)

        bw = BinaryWriter()
        bw.write_u32(1)
        bw.write_u32(0)
        bw.write_u32(0)
        bw.write_u32(1)
        bw.write_bytes(_pack_tag("VAND"))
        bw.write_u32(custom_offset)
        bw.write_u32(custom_length)
        bw.write_bytes(custom_data)

        data = bw.to_bytes()
        reader = BinaryReader(data)
        table = MetaTable.from_reader(reader, len(data))

        assert "VAND" in table.data_maps
        assert table.get_tag_data("VAND") == custom_data

    def test_invalid_version_raises_font_parse_exception(self) -> None:
        """Test that unsupported meta version raises FontParseException."""
        bw = BinaryWriter()
        bw.write_u32(2)
        bw.write_u32(0)
        bw.write_u32(0)
        bw.write_u32(0)

        data = bw.to_bytes()
        reader = BinaryReader(data)

        with pytest.raises(FontParseException):
            MetaTable.from_reader(reader, len(data))

    def test_meta_table_flags_field(self) -> None:
        """Test that flags field is read but not validated."""
        bw = BinaryWriter()
        bw.write_u32(1)
        bw.write_u32(0)
        bw.write_u32(0x00000001)
        bw.write_u32(0)

        data = bw.to_bytes()
        reader = BinaryReader(data)
        table = MetaTable.from_reader(reader, len(data))

        assert table.flags == 0x00000001

    def test_meta_to_bytes_roundtrip(self) -> None:
        """Test that to_bytes returns the original raw data."""
        dlng_data = b"en"

        bw = BinaryWriter()
        bw.write_u32(1)
        bw.write_u32(0)
        bw.write_u32(0)
        bw.write_u32(1)
        bw.write_bytes(_pack_tag("dlng"))
        bw.write_u32(20)
        bw.write_u32(len(dlng_data))
        bw.write_bytes(dlng_data)

        data = bw.to_bytes()
        reader = BinaryReader(data)
        table = MetaTable.from_reader(reader, len(data))

        assert table.to_bytes() == data

    def test_whitespace_handling_in_dlng(self) -> None:
        """Test that whitespace around comma-separated tags is stripped."""
        dlng_data = b"Latn , Cyrl , Grek"
        data_offset = 28
        data_length = len(dlng_data)

        bw = BinaryWriter()
        bw.write_u32(1)
        bw.write_u32(0)
        bw.write_u32(0)
        bw.write_u32(1)
        bw.write_bytes(_pack_tag("dlng"))
        bw.write_u32(data_offset)
        bw.write_u32(data_length)
        bw.write_bytes(dlng_data)

        data = bw.to_bytes()
        reader = BinaryReader(data)
        table = MetaTable.from_reader(reader, len(data))

        assert table.design_languages == ["Latn", "Cyrl", "Grek"]

    def test_empty_string_in_dlng(self) -> None:
        """Test that empty strings between commas are filtered out."""
        dlng_data = b"Latn,,Cyrl,"
        data_offset = 28
        data_length = len(dlng_data)

        bw = BinaryWriter()
        bw.write_u32(1)
        bw.write_u32(0)
        bw.write_u32(0)
        bw.write_u32(1)
        bw.write_bytes(_pack_tag("dlng"))
        bw.write_u32(data_offset)
        bw.write_u32(data_length)
        bw.write_bytes(dlng_data)

        data = bw.to_bytes()
        reader = BinaryReader(data)
        table = MetaTable.from_reader(reader, len(data))

        assert table.design_languages == ["Latn", "Cyrl"]


class TestMetaIntegration:
    """Test meta table integration with FontLoader."""

    def test_load_font_with_meta_table(self) -> None:
        """Test that FontLoader can open font with meta table."""
        from aspose_font import FontLoader

        font_path = "testdata/TTF/SymbolicFonts/symbol.ttf"
        font = FontLoader.open(font_path)

        assert hasattr(font.ttf_tables, "meta")
        assert font.ttf_tables.meta is not None

        meta = font.ttf_tables.meta
        assert meta.major_version == 1
        assert isinstance(meta.design_languages, list)
        assert isinstance(meta.supported_languages, list)


class TestMetaEdgeCases:
    """Test edge cases in meta parsing."""

    def test_four_char_tag(self) -> None:
        """Test parsing with four-character tag."""
        tag_data = b"WXYZ"
        data_offset = 28
        data_length = len(tag_data)

        bw = BinaryWriter()
        bw.write_u32(1)
        bw.write_u32(0)
        bw.write_u32(0)
        bw.write_u32(1)
        bw.write_bytes(_pack_tag("TEST"))
        bw.write_u32(data_offset)
        bw.write_u32(data_length)
        bw.write_bytes(tag_data)

        data_out = bw.to_bytes()
        reader = BinaryReader(data_out)
        table = MetaTable.from_reader(reader, len(data_out))

        assert "TEST" in table.data_maps
        assert table.get_tag_data("TEST") == tag_data

    def test_many_data_maps(self) -> None:
        """Test parsing meta table with many data maps."""
        num_maps = 5
        tag_offsets = []
        offset = 20 + num_maps * 12

        bw = BinaryWriter()
        bw.write_u32(1)
        bw.write_u32(0)
        bw.write_u32(0)
        bw.write_u32(num_maps)

        for i in range(num_maps):
            tag = f"TAG{i}"
            tag_data = f"metadata{i}".encode("utf-8")
            tag_offsets.append((tag, tag_data, offset))
            offset += len(tag_data)

        for tag, tag_data, _ in tag_offsets:
            bw.write_bytes(_pack_tag(tag))
            bw.write_u32(0)
            bw.write_u32(len(tag_data))

        current_offset = 20 + num_maps * 12
        for j, (_, tag_data, _) in enumerate(tag_offsets):
            bw.write_u32(current_offset)
            current_offset += len(tag_data)

        for _, tag_data, _ in tag_offsets:
            bw.write_bytes(tag_data)

        data = bw.to_bytes()
        reader = BinaryReader(data)
        table = MetaTable.from_reader(reader, len(data))

        assert len(table) == num_maps
        for i in range(num_maps):
            tag = f"TAG{i}"
            assert tag in table.data_maps

    def test_unicode_in_dlng_raises_decode_error(self) -> None:
        """Test handling of invalid UTF-8 in dlng tag (should return empty list)."""
        invalid_utf8 = b"\xff\xfe"
        data_offset = 28

        bw = BinaryWriter()
        bw.write_u32(1)
        bw.write_u32(0)
        bw.write_u32(0)
        bw.write_u32(1)
        bw.write_bytes(_pack_tag("dlng"))
        bw.write_u32(data_offset)
        bw.write_u32(len(invalid_utf8))
        bw.write_bytes(invalid_utf8)

        data = bw.to_bytes()
        reader = BinaryReader(data)
        table = MetaTable.from_reader(reader, len(data))

        assert table.design_languages == []

    def test_get_tag_data_nonexistent_tag(self) -> None:
        """Test that get_tag_data returns None for non-existent tag."""
        bw = BinaryWriter()
        bw.write_u32(1)
        bw.write_u32(0)
        bw.write_u32(0)
        bw.write_u32(0)

        data = bw.to_bytes()
        reader = BinaryReader(data)
        table = MetaTable.from_reader(reader, len(data))

        assert table.get_tag_data("dlng") is None
        assert table.get_tag_data("slng") is None
        assert table.get_tag_data("XXXX") is None
