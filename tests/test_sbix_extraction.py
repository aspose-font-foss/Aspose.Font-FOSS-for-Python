"""Tests for OpenType sbix table parser (FONT-468)."""

from __future__ import annotations

from io import BytesIO

from aspose_font._io import BinaryReader
from aspose_font.ttf.tables.sbix import BitmapRecord, SbixTable, Strike


class TestStrikeDataclass:
    """Tests for Strike dataclass structure."""

    def test_strike_dataclass_structure(self):
        """Test that Strike has correct fields and values."""
        strike = Strike(ppem=24, resolution=96)
        assert strike.ppem == 24
        assert strike.resolution == 96

    def test_strike_slots(self):
        """Test that Strike uses __slots__ for memory efficiency."""
        strike = Strike(ppem=16, resolution=72)
        assert not hasattr(strike, "__dict__")


class TestBitmapRecordDataclass:
    """Tests for BitmapRecord dataclass structure."""

    def test_bitmap_record_dataclass_structure(self):
        """Test that BitmapRecord has correct fields."""
        record = BitmapRecord(
            glyph_id=5,
            graphic_type="png ",
            origin_offset_x=10,
            origin_offset_y=-5,
            bitmap_data=b"\x89PNG\r\n\x1a\n",
        )
        assert record.glyph_id == 5
        assert record.graphic_type == "png "
        assert record.origin_offset_x == 10
        assert record.origin_offset_y == -5
        assert record.bitmap_data == b"\x89PNG\r\n\x1a\n"

    def test_bitmap_record_slots(self):
        """Test that BitmapRecord uses __slots__ for memory efficiency."""
        record = BitmapRecord(
            glyph_id=1,
            graphic_type="jpg ",
            origin_offset_x=0,
            origin_offset_y=0,
            bitmap_data=b"",
        )
        assert not hasattr(record, "__dict__")


class TestSbixTableParsing:
    """Tests for sbix table binary parsing."""

    def test_parse_empty_sbix_table(self, tmp_path):
        """Test parsing sbix table with zero strikes."""
        stream = BytesIO()
        stream.write(b"\x00\x00")  # version = 0
        stream.write(b"\x00\x00")  # flags = 0
        stream.write(b"\x00\x00\x00\x00")  # num_strikes = 0

        rr = BinaryReader(stream.getvalue())
        table = SbixTable.from_reader(rr, len(stream.getvalue()))

        assert table.version == 0
        assert table.flags == 0
        assert table.strikes == []
        assert table.bitmap_records == []

    def test_parse_sbix_with_single_strike_no_glyphs(self, tmp_path):
        """Test parsing sbix table with one strike but no glyphs."""
        stream = BytesIO()
        stream.write(b"\x00\x00")  # version = 0
        stream.write(b"\x00\x00")  # flags = 0
        stream.write(b"\x00\x00\x00\x01")  # num_strikes = 1
        stream.write(b"\x00\x18")  # ppem = 24
        stream.write(b"\x00\x60")  # resolution = 96
        stream.write(b"\x00\x00\x00\x00")  # offset_to_bitmap_data = 0
        stream.write(b"\x00\x00\x00\x00")  # num_glyphs = 0

        rr = BinaryReader(stream.getvalue())
        table = SbixTable.from_reader(rr, len(stream.getvalue()))

        assert table.version == 0
        assert len(table.strikes) == 1
        assert table.strikes[0].ppem == 24
        assert table.strikes[0].resolution == 96
        assert table.bitmap_records == [[]]

    def test_parse_sbix_with_single_strike_single_glyph(self, tmp_path):
        """Test parsing sbix table with one strike and one PNG glyph."""
        bitmap_data = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIEND\xAE\x42\x60\x82"

        stream = BytesIO()
        stream.write(b"\x00\x00")  # version = 0
        stream.write(b"\x00\x00")  # flags = 0
        stream.write(b"\x00\x00\x00\x01")  # num_strikes = 1
        stream.write(b"\x00\x18")  # ppem = 24
        stream.write(b"\x00\x60")  # resolution = 96
        stream.write(b"\x00\x00\x00\x00")  # offset_to_bitmap_data = 0 (data at byte 24)
        stream.write(b"\x00\x00\x00\x01")  # num_glyphs = 1
        stream.write(b"\x00\x05")  # glyph_id = 5
        stream.write(b"png ")  # graphic_type = png
        stream.write(b"\x00\x0A")  # origin_offset_x = 10
        stream.write(b"\xFF\xF6")  # origin_offset_y = -10
        stream.write((len(bitmap_data)).to_bytes(4, byteorder="big"))  # bitmap_data_length
        stream.write(bitmap_data)  # bitmap_data

        rr = BinaryReader(stream.getvalue())
        table = SbixTable.from_reader(rr, len(stream.getvalue()))

        assert table.version == 0
        assert len(table.strikes) == 1
        assert table.strikes[0].ppem == 24

        records = table.bitmap_records[0]
        assert len(records) == 1
        assert records[0] is not None
        assert records[0].glyph_id == 5
        assert records[0].graphic_type == "png "
        assert records[0].origin_offset_x == 10
        assert records[0].origin_offset_y == -10
        assert records[0].bitmap_data == bitmap_data

    def test_parse_sbix_with_multiple_strikes(self, tmp_path):
        """Test parsing sbix table with multiple bitmap strikes."""
        bitmap_data_16 = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIEND\xAE\x42\x60\x82"
        bitmap_data_24 = b"\x89PNG\r\n\x1a\n\x00\x00\x00\x89IDATx\x9c\x62\x60\x60\x60\x60\x00\x00\x00\x04\x00\x01\xF5\xFF\x65\x82"

        stream = BytesIO()
        stream.write(b"\x00\x00")  # version = 0
        stream.write(b"\x00\x01")  # flags = 1
        stream.write(b"\x00\x00\x00\x02")  # num_strikes = 2

        # Strike 0 record at position 8-15 (offset=0, data at 8+16+0=24)
        stream.write(b"\x00\x10")  # ppem = 16
        stream.write(b"\x00\x48")  # resolution = 72
        stream.write(b"\x00\x00\x00\x00")  # offset_to_bitmap_data = 0

        # Strike 1 record at position 16-23 (offset=32, data at 8+16+32=56)
        stream.write(b"\x00\x18")  # ppem = 24
        stream.write(b"\x00\x60")  # resolution = 96
        stream.write(b"\x00\x00\x00\x26")  # offset_to_bitmap_data = 38 (24 + 38 = 62)

        # Strike 0 data at position 24-55
        stream.write(b"\x00\x00\x00\x01")  # num_glyphs = 1
        stream.write(b"\x00\x03")  # glyph_id = 3
        stream.write(b"png ")  # graphic_type = png
        stream.write(b"\x00\x00")  # origin_offset_x = 0
        stream.write(b"\x00\x00")  # origin_offset_y = 0
        stream.write(len(bitmap_data_16).to_bytes(4, byteorder="big"))
        stream.write(bitmap_data_16)

        # Strike 1 data at position 56
        stream.write(b"\x00\x00\x00\x01")  # num_glyphs = 1
        stream.write(b"\x00\x03")  # glyph_id = 3
        stream.write(b"png ")  # graphic_type = png
        stream.write(b"\x00\x00")  # origin_offset_x = 0
        stream.write(b"\x00\x00")  # origin_offset_y = 0
        stream.write(len(bitmap_data_24).to_bytes(4, byteorder="big"))
        stream.write(bitmap_data_24)

        rr = BinaryReader(stream.getvalue())
        table = SbixTable.from_reader(rr, len(stream.getvalue()))

        assert table.version == 0
        assert table.flags == 1
        assert len(table.strikes) == 2
        assert table.strikes[0].ppem == 16
        assert table.strikes[1].ppem == 24
        assert len(table.bitmap_records) == 2

    def test_parse_sbix_with_multiple_glyphs(self, tmp_path):
        """Test parsing sbix table with multiple glyphs in one strike."""
        bitmap_data_1 = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIEND\xAE\x42\x60\x82"
        bitmap_data_2 = b"\x89PNG\r\n\x1a\n\x00\x00\x00\x89IDATx\x9c\x62\x60\x60\x60\x60\x00\x00\x00\x04\x00\x01\xF5\xFF\x65\x82"

        stream = BytesIO()
        stream.write(b"\x00\x00")  # version = 0
        stream.write(b"\x00\x00")  # flags = 0
        stream.write(b"\x00\x00\x00\x01")  # num_strikes = 1
        stream.write(b"\x00\x18")  # ppem = 24
        stream.write(b"\x00\x60")  # resolution = 96
        stream.write(b"\x00\x00\x00\x00")  # offset_to_bitmap_data = 0
        stream.write(b"\x00\x00\x00\x02")  # num_glyphs = 2

        # Glyph 1 (gid 5)
        stream.write(b"\x00\x05")  # glyph_id = 5
        stream.write(b"png ")  # graphic_type = png
        stream.write(b"\x00\x00")  # origin_offset_x = 0
        stream.write(b"\x00\x00")  # origin_offset_y = 0
        stream.write(len(bitmap_data_1).to_bytes(4, byteorder="big"))
        stream.write(bitmap_data_1)

        # Glyph 2 (gid 7)
        stream.write(b"\x00\x07")  # glyph_id = 7
        stream.write(b"jpg ")  # graphic_type = jpg
        stream.write(b"\x00\x05")  # origin_offset_x = 5
        stream.write(b"\xFF\xFB")  # origin_offset_y = -5
        stream.write(len(bitmap_data_2).to_bytes(4, byteorder="big"))
        stream.write(bitmap_data_2)

        rr = BinaryReader(stream.getvalue())
        table = SbixTable.from_reader(rr, len(stream.getvalue()))

        records = table.bitmap_records[0]
        assert len(records) == 2

        assert records[0] is not None
        assert records[0].glyph_id == 5
        assert records[0].graphic_type == "png "

        assert records[1] is not None
        assert records[1].glyph_id == 7
        assert records[1].graphic_type == "jpg "
        assert records[1].origin_offset_x == 5
        assert records[1].origin_offset_y == -5

    def test_parse_sbix_jpeg_format(self, tmp_path):
        """Test parsing sbix table with JPEG graphic_type."""
        jpeg_data = b"\xFF\xD8\xFF\xE0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"

        stream = BytesIO()
        stream.write(b"\x00\x00")  # version = 0
        stream.write(b"\x00\x00")  # flags = 0
        stream.write(b"\x00\x00\x00\x01")  # num_strikes = 1
        stream.write(b"\x00\x18")  # ppem = 24
        stream.write(b"\x00\x60")  # resolution = 96
        stream.write(b"\x00\x00\x00\x00")  # offset_to_bitmap_data = 0
        stream.write(b"\x00\x00\x00\x01")  # num_glyphs = 1
        stream.write(b"\x00\x05")  # glyph_id = 5
        stream.write(b"jpg ")  # graphic_type = jpg
        stream.write(b"\x00\x00")  # origin_offset_x = 0
        stream.write(b"\x00\x00")  # origin_offset_y = 0
        stream.write(len(jpeg_data).to_bytes(4, byteorder="big"))
        stream.write(jpeg_data)

        rr = BinaryReader(stream.getvalue())
        table = SbixTable.from_reader(rr, len(stream.getvalue()))

        records = table.bitmap_records[0]
        assert records[0] is not None
        assert records[0].graphic_type == "jpg "
        assert records[0].bitmap_data == jpeg_data

    def test_parse_sbix_tiff_format(self, tmp_path):
        """Test parsing sbix table with TIFF graphic_type."""
        tiff_data = b"\x49\x49\x2A\x00\x08\x00\x00\x00"

        stream = BytesIO()
        stream.write(b"\x00\x00")  # version = 0
        stream.write(b"\x00\x00")  # flags = 0
        stream.write(b"\x00\x00\x00\x01")  # num_strikes = 1
        stream.write(b"\x00\x18")  # ppem = 24
        stream.write(b"\x00\x60")  # resolution = 96
        stream.write(b"\x00\x00\x00\x00")  # offset_to_bitmap_data = 0
        stream.write(b"\x00\x00\x00\x01")  # num_glyphs = 1
        stream.write(b"\x00\x05")  # glyph_id = 5
        stream.write(b"tiff")  # graphic_type = tiff
        stream.write(b"\x00\x00")  # origin_offset_x = 0
        stream.write(b"\x00\x00")  # origin_offset_y = 0
        stream.write(len(tiff_data).to_bytes(4, byteorder="big"))
        stream.write(tiff_data)

        rr = BinaryReader(stream.getvalue())
        table = SbixTable.from_reader(rr, len(stream.getvalue()))

        records = table.bitmap_records[0]
        assert records[0] is not None
        assert records[0].graphic_type == "tiff"
        assert records[0].bitmap_data == tiff_data

    def test_sbix_version_validation(self, tmp_path):
        """Test that sbix table with invalid version raises exception."""
        stream = BytesIO()
        stream.write(b"\x00\x01")  # version = 1 (invalid)
        stream.write(b"\x00\x00")  # flags = 0
        stream.write(b"\x00\x00\x00\x00")  # num_strikes = 0

        rr = BinaryReader(stream.getvalue())
        try:
            SbixTable.from_reader(rr, len(stream.getvalue()))
            assert False, "Expected FontParseException"
        except Exception as e:
            assert "Unsupported sbix table version" in str(e)


class TestSbixStrikeRetrieval:
    """Tests for sbix strike retrieval methods."""

    def test_get_strikes_sorted(self, tmp_path):
        """Test get_strikes() returns sorted ppem values."""

        # Build sbix data with correct layout:
        # Header (0-7): version=0, flags=0, num_strikes=3
        # Strike records (8-31): 3 records with offsets 0, 8, 16
        # Strike 0 data (32-35): num_glyphs=0
        # Strike 1 data (40-43): num_glyphs=0
        # Strike 2 data (48-51): num_glyphs=0

        data = (
            b"\x00\x00"  # version = 0
            b"\x00\x00"  # flags = 0
            b"\x00\x00\x00\x03"  # num_strikes = 3

            # Strike 0: 48ppem, offset=0
            b"\x00\x30"  # ppem = 48
            b"\x00\x60"  # resolution = 96
            b"\x00\x00\x00\x00"  # offset_to_bitmap_data = 0

            # Strike 1: 16ppem, offset=8
            b"\x00\x10"  # ppem = 16
            b"\x00\x48"  # resolution = 72
            b"\x00\x00\x00\x08"  # offset_to_bitmap_data = 8

            # Strike 2: 32ppem, offset=16
            b"\x00\x20"  # ppem = 32
            b"\x00\x60"  # resolution = 96
            b"\x00\x00\x00\x10"  # offset_to_bitmap_data = 16

            # Padding: bytes 32-35 are strike 0 data (num_glyphs=0), but we need to fill 32-39 first
            b"\x00\x00\x00\x00\x00\x00\x00\x00"  # bytes 32-39 (strike 0 data + 4 bytes padding)

            # Bytes 40-43: strike 1 data (num_glyphs=0)
            b"\x00\x00\x00\x00"  # strike 1 data

            # Padding: bytes 44-47
            b"\x00\x00\x00\x00"  # bytes 44-47

            # Bytes 48-51: strike 2 data (num_glyphs=0)
            b"\x00\x00\x00\x00"  # strike 2 data
        )

        stream = BytesIO(data)
        rr = BinaryReader(stream.getvalue())
        table = SbixTable.from_reader(rr, len(stream.getvalue()))

        strikes = table.get_strikes()
        assert strikes == [16, 32, 48]

    def test_get_strikes_empty(self, tmp_path):
        """Test get_strikes() returns empty list for no strikes."""
        stream = BytesIO()
        stream.write(b"\x00\x00")  # version = 0
        stream.write(b"\x00\x00")  # flags = 0
        stream.write(b"\x00\x00\x00\x00")  # num_strikes = 0

        rr = BinaryReader(stream.getvalue())
        table = SbixTable.from_reader(rr, len(stream.getvalue()))

        strikes = table.get_strikes()
        assert strikes == []

    def test_get_strikes_multiple(self, tmp_path):
        """Test get_strikes() returns correct order for multiple strikes."""
        stream = BytesIO()
        stream.write(b"\x00\x00")  # version = 0
        stream.write(b"\x00\x00")  # flags = 0
        stream.write(b"\x00\x00\x00\x02")  # num_strikes = 2

        # Strike 0 record at position 8-15 (offset=0, data at 32)
        stream.write(b"\x00\x32")  # ppem = 50
        stream.write(b"\x00\x60")  # resolution = 96
        stream.write(b"\x00\x00\x00\x00")  # offset_to_bitmap_data = 0

        # Strike 1 record at position 16-23 (offset=4, data at 36)
        stream.write(b"\x00\x20")  # ppem = 32
        stream.write(b"\x00\x48")  # resolution = 72
        stream.write(b"\x00\x00\x00\x04")  # offset_to_bitmap_data = 4

        # Strike 0 data at position 24 (num_glyphs only, 4 bytes)
        stream.write(b"\x00\x00\x00\x00")  # num_glyphs = 0

        # Strike 1 data at position 28 (num_glyphs only, 4 bytes)
        stream.write(b"\x00\x00\x00\x00")  # num_glyphs = 0

        rr = BinaryReader(stream.getvalue())
        table = SbixTable.from_reader(rr, len(stream.getvalue()))

        strikes = table.get_strikes()
        assert strikes == [32, 50]


class TestSbixBitmapRetrieval:
    """Tests for sbix bitmap retrieval methods."""

    def test_get_bitmap_no_coverage(self, tmp_path):
        """Test get_bitmap() returns None for uncovered glyph."""
        bitmap_data = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIEND\xAE\x42\x60\x82"

        stream = BytesIO()
        stream.write(b"\x00\x00")  # version = 0
        stream.write(b"\x00\x00")  # flags = 0
        stream.write(b"\x00\x00\x00\x01")  # num_strikes = 1
        stream.write(b"\x00\x18")  # ppem = 24
        stream.write(b"\x00\x60")  # resolution = 96
        stream.write(b"\x00\x00\x00\x00")  # offset_to_bitmap_data = 0
        stream.write(b"\x00\x00\x00\x01")  # num_glyphs = 1
        stream.write(b"\x00\x05")  # glyph_id = 5
        stream.write(b"png ")  # graphic_type = png
        stream.write(b"\x00\x00")  # origin_offset_x = 0
        stream.write(b"\x00\x00")  # origin_offset_y = 0
        stream.write(len(bitmap_data).to_bytes(4, byteorder="big"))
        stream.write(bitmap_data)

        rr = BinaryReader(stream.getvalue())
        table = SbixTable.from_reader(rr, len(stream.getvalue()))

        assert table.get_bitmap(glyph_id=3, ppem=24) is None
        assert table.get_bitmap(glyph_id=10, ppem=24) is None

    def test_get_bitmap_returns_data(self, tmp_path):
        """Test get_bitmap() returns bitmap for covered glyph."""
        bitmap_data = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIEND\xAE\x42\x60\x82"

        stream = BytesIO()
        stream.write(b"\x00\x00")  # version = 0
        stream.write(b"\x00\x00")  # flags = 0
        stream.write(b"\x00\x00\x00\x01")  # num_strikes = 1
        stream.write(b"\x00\x18")  # ppem = 24
        stream.write(b"\x00\x60")  # resolution = 96
        stream.write(b"\x00\x00\x00\x00")  # offset_to_bitmap_data = 0
        stream.write(b"\x00\x00\x00\x01")  # num_glyphs = 1
        stream.write(b"\x00\x05")  # glyph_id = 5
        stream.write(b"png ")  # graphic_type = png
        stream.write(b"\x00\x00")  # origin_offset_x = 0
        stream.write(b"\x00\x00")  # origin_offset_y = 0
        stream.write(len(bitmap_data).to_bytes(4, byteorder="big"))
        stream.write(bitmap_data)

        rr = BinaryReader(stream.getvalue())
        table = SbixTable.from_reader(rr, len(stream.getvalue()))

        result = table.get_bitmap(glyph_id=5, ppem=24)
        assert result == bitmap_data

    def test_get_bitmap_none_ppem_uses_highest(self, tmp_path):
        """Test get_bitmap() with ppem=None uses highest strike."""
        bitmap_data_low = b"\x89PNG\r\n\x1a\nLOW"
        bitmap_data_high = b"\x89PNG\r\n\x1a\nHIGH\x00\x00\x00\x89"

        stream = BytesIO()
        stream.write(b"\x00\x00")  # version = 0
        stream.write(b"\x00\x00")  # flags = 0
        stream.write(b"\x00\x00\x00\x02")  # num_strikes = 2

        # Strike 0 record at position 8-15 (offset=0, data at 24)
        stream.write(b"\x00\x10")  # ppem = 16
        stream.write(b"\x00\x48")  # resolution = 72
        stream.write(b"\x00\x00\x00\x00")  # offset_to_bitmap_data = 0

        # Strike 1 record at position 16-23 (offset=29, data at 53)
        stream.write(b"\x00\x20")  # ppem = 32
        stream.write(b"\x00\x60")  # resolution = 96
        stream.write(b"\x00\x00\x00\x1D")  # offset_to_bitmap_data = 29

        # Strike 0 data at position 24 (4 + 14 + 11 = 29 bytes)
        stream.write(b"\x00\x00\x00\x01")  # num_glyphs = 1
        stream.write(b"\x00\x05")  # glyph_id = 5
        stream.write(b"png ")  # graphic_type = png
        stream.write(b"\x00\x00")  # origin_offset_x = 0
        stream.write(b"\x00\x00")  # origin_offset_y = 0
        stream.write(len(bitmap_data_low).to_bytes(4, byteorder="big"))
        stream.write(bitmap_data_low)

        # Strike 1 data at position 53 (4 + 14 + 16 = 34 bytes)
        stream.write(b"\x00\x00\x00\x01")  # num_glyphs = 1
        stream.write(b"\x00\x05")  # glyph_id = 5
        stream.write(b"png ")  # graphic_type = png
        stream.write(b"\x00\x00")  # origin_offset_x = 0
        stream.write(b"\x00\x00")  # origin_offset_y = 0
        stream.write(len(bitmap_data_high).to_bytes(4, byteorder="big"))
        stream.write(bitmap_data_high)

        rr = BinaryReader(stream.getvalue())
        table = SbixTable.from_reader(rr, len(stream.getvalue()))

        result = table.get_bitmap(glyph_id=5, ppem=None)
        assert result == bitmap_data_high

    def test_get_bitmap_specific_ppem(self, tmp_path):
        """Test get_bitmap() with specific ppem returns correct strike."""
        bitmap_data_16 = b"\x89PNG\r\n\x1a\nLOW"
        bitmap_data_32 = b"\x89PNG\r\n\x1a\nHIGH\x00\x00\x00\x89"

        stream = BytesIO()
        stream.write(b"\x00\x00")  # version = 0
        stream.write(b"\x00\x00")  # flags = 0
        stream.write(b"\x00\x00\x00\x02")  # num_strikes = 2

        # Strike 0 record at position 8-15 (offset=0, data at 24)
        stream.write(b"\x00\x10")  # ppem = 16
        stream.write(b"\x00\x48")  # resolution = 72
        stream.write(b"\x00\x00\x00\x00")  # offset_to_bitmap_data = 0

        # Strike 1 record at position 16-23 (offset=29, data at 53)
        stream.write(b"\x00\x20")  # ppem = 32
        stream.write(b"\x00\x60")  # resolution = 96
        stream.write(b"\x00\x00\x00\x1D")  # offset_to_bitmap_data = 29

        # Strike 0 data at position 24 (4 + 14 + 11 = 29 bytes)
        stream.write(b"\x00\x00\x00\x01")  # num_glyphs = 1
        stream.write(b"\x00\x05")  # glyph_id = 5
        stream.write(b"png ")  # graphic_type = png
        stream.write(b"\x00\x00")  # origin_offset_x = 0
        stream.write(b"\x00\x00")  # origin_offset_y = 0
        stream.write(len(bitmap_data_16).to_bytes(4, byteorder="big"))
        stream.write(bitmap_data_16)

        # Strike 1 data at position 53 (4 + 14 + 16 = 34 bytes)
        stream.write(b"\x00\x00\x00\x01")  # num_glyphs = 1
        stream.write(b"\x00\x05")  # glyph_id = 5
        stream.write(b"png ")  # graphic_type = png
        stream.write(b"\x00\x00")  # origin_offset_x = 0
        stream.write(b"\x00\x00")  # origin_offset_y = 0
        stream.write(len(bitmap_data_32).to_bytes(4, byteorder="big"))
        stream.write(bitmap_data_32)

        rr = BinaryReader(stream.getvalue())
        table = SbixTable.from_reader(rr, len(stream.getvalue()))

        result_16 = table.get_bitmap(glyph_id=5, ppem=16)
        assert result_16 == bitmap_data_16

        result_32 = table.get_bitmap(glyph_id=5, ppem=32)
        assert result_32 == bitmap_data_32

    def test_get_bitmap_missing_ppem(self, tmp_path):
        """Test get_bitmap() returns None for non-existent ppem."""
        bitmap_data = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIEND\xAE\x42\x60\x82"

        stream = BytesIO()
        stream.write(b"\x00\x00")  # version = 0
        stream.write(b"\x00\x00")  # flags = 0
        stream.write(b"\x00\x00\x00\x01")  # num_strikes = 1
        stream.write(b"\x00\x18")  # ppem = 24
        stream.write(b"\x00\x60")  # resolution = 96
        stream.write(b"\x00\x00\x00\x00")  # offset_to_bitmap_data = 0
        stream.write(b"\x00\x00\x00\x01")  # num_glyphs = 1
        stream.write(b"\x00\x05")  # glyph_id = 5
        stream.write(b"png ")  # graphic_type = png
        stream.write(b"\x00\x00")  # origin_offset_x = 0
        stream.write(b"\x00\x00")  # origin_offset_y = 0
        stream.write(len(bitmap_data).to_bytes(4, byteorder="big"))
        stream.write(bitmap_data)

        rr = BinaryReader(stream.getvalue())
        table = SbixTable.from_reader(rr, len(stream.getvalue()))

        assert table.get_bitmap(glyph_id=5, ppem=16) is None
        assert table.get_bitmap(glyph_id=5, ppem=32) is None

    def test_get_bitmap_missing_glyph_in_strike(self, tmp_path):
        """Test get_bitmap() returns None for missing glyph in strike."""
        bitmap_data = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIEND\xAE\x42\x60\x82"

        stream = BytesIO()
        stream.write(b"\x00\x00")  # version = 0
        stream.write(b"\x00\x00")  # flags = 0
        stream.write(b"\x00\x00\x00\x01")  # num_strikes = 1
        stream.write(b"\x00\x18")  # ppem = 24
        stream.write(b"\x00\x60")  # resolution = 96
        stream.write(b"\x00\x00\x00\x00")  # offset_to_bitmap_data = 0
        stream.write(b"\x00\x00\x00\x01")  # num_glyphs = 1
        stream.write(b"\x00\x05")  # glyph_id = 5
        stream.write(b"png ")  # graphic_type = png
        stream.write(b"\x00\x00")  # origin_offset_x = 0
        stream.write(b"\x00\x00")  # origin_offset_y = 0
        stream.write(len(bitmap_data).to_bytes(4, byteorder="big"))
        stream.write(bitmap_data)

        rr = BinaryReader(stream.getvalue())
        table = SbixTable.from_reader(rr, len(stream.getvalue()))

        assert table.get_bitmap(glyph_id=6, ppem=24) is None
