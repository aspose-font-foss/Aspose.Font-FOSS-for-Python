"""Tests for OpenType CBLC and CBDT table parser (FONT-476)."""

from __future__ import annotations

from io import BytesIO

from aspose_font._io import BinaryReader
from aspose_font.ttf.tables.cbdt import (
    CbdtGlyphBitmap,
    CbdtTable,
    CblcIndexSubTableFormat17,
    CblcIndexSubTableFormat18,
    CblcMetricsBig,
    CblcMetricsSmall,
    CblcStrike,
    CblcTable,
)


class TestCblcStrikeDataclass:
    """Tests for CblcStrike dataclass structure."""

    def test_strike_dataclass_structure(self):
        """Test that CblcStrike has correct fields and values."""
        strike = CblcStrike(ppem=24, max_ppem=48, bit_depth=32, flags=0)
        assert strike.ppem == 24
        assert strike.max_ppem == 48
        assert strike.bit_depth == 32
        assert strike.flags == 0

    def test_strike_dataclass_with_none_max_ppem(self):
        """Test CblcStrike with None max_ppem."""
        strike = CblcStrike(ppem=16, max_ppem=None, bit_depth=8, flags=1)
        assert strike.ppem == 16
        assert strike.max_ppem is None
        assert strike.bit_depth == 8
        assert strike.flags == 1

    def test_strike_slots(self):
        """Test that CblcStrike uses __slots__ for memory efficiency."""
        strike = CblcStrike(ppem=16, max_ppem=32, bit_depth=8, flags=0)
        assert not hasattr(strike, "__dict__")


class TestCblcMetricsDataclasses:
    """Tests for CblcMetrics dataclasses."""

    def test_metrics_small_structure(self):
        """Test that CblcMetricsSmall has correct fields."""
        metrics = CblcMetricsSmall(
            width=32,
            height=32,
            bit_depth=32,
            horizontal_origin_x=0,
            horizontal_origin_y=32,
            vertical_origin_x=0,
            vertical_origin_y=0
        )
        assert metrics.width == 32
        assert metrics.height == 32
        assert metrics.bit_depth == 32
        assert metrics.horizontal_origin_x == 0
        assert metrics.horizontal_origin_y == 32
        assert metrics.vertical_origin_x == 0
        assert metrics.vertical_origin_y == 0

    def test_metrics_small_slots(self):
        """Test that CblcMetricsSmall uses __slots__."""
        metrics = CblcMetricsSmall(
            width=24,
            height=24,
            bit_depth=8,
            horizontal_origin_x=0,
            horizontal_origin_y=24,
            vertical_origin_x=0,
            vertical_origin_y=0
        )
        assert not hasattr(metrics, "__dict__")

    def test_metrics_big_structure(self):
        """Test that CblcMetricsBig has correct fields."""
        metrics = CblcMetricsBig(
            width=64,
            height=64,
            bit_depth=32,
            horizontal_origin_x=0,
            horizontal_origin_y=64,
            vertical_origin_x=0,
            vertical_origin_y=0,
            horizontal_advance=64,
            vertical_advance=64,
            horizontal_bearing_x=0,
            horizontal_bearing_y=64,
            vertical_bearing_x=0,
            vertical_bearing_y=64
        )
        assert metrics.width == 64
        assert metrics.height == 64
        assert metrics.bit_depth == 32
        assert metrics.horizontal_advance == 64
        assert metrics.vertical_advance == 64
        assert metrics.horizontal_bearing_x == 0
        assert metrics.horizontal_bearing_y == 64
        assert metrics.vertical_bearing_x == 0
        assert metrics.vertical_bearing_y == 64

    def test_metrics_big_slots(self):
        """Test that CblcMetricsBig uses __slots__."""
        metrics = CblcMetricsBig(
            width=48,
            height=48,
            bit_depth=32,
            horizontal_origin_x=0,
            horizontal_origin_y=48,
            vertical_origin_x=0,
            vertical_origin_y=0,
            horizontal_advance=48,
            vertical_advance=48,
            horizontal_bearing_x=0,
            horizontal_bearing_y=48,
            vertical_bearing_x=0,
            vertical_bearing_y=48
        )
        assert not hasattr(metrics, "__dict__")


class TestCblcIndexSubTableParsing:
    """Tests for CBLC index subtable parsing."""

    def test_parse_format17_with_png(self, tmp_path):
        """Test parsing Format 17 subtable with PNG data."""
        stream = BytesIO()
        stream.write(b"\x00\x11")  # format = 17
        stream.write(b"\x00\x01")  # first_glyph_id = 1
        stream.write(b"\x00\x03")  # last_glyph_id = 3
        stream.write(b"\x00\x00\x00\x10")  # additional_offset = 16
        stream.write(b"\x01")  # data_format = 1 (PNG)
        stream.write(b"\x00\x00\x00")  # padding
        stream.write(b"\x00\x20")  # width = 32
        stream.write(b"\x00\x20")  # height = 32
        stream.write(b"\x20")  # bit_depth = 32
        stream.write(b"\x00")  # horizontal_origin_x = 0
        stream.write(b"\x00")  # horizontal_origin_y = 0
        stream.write(b"\x00")  # vertical_origin_x = 0
        stream.write(b"\x00")  # vertical_origin_y = 0
        stream.write(b"\x00\x00\x00\x00")  # offset 0 (unused)
        stream.write(b"\x00\x00\x00\x0C")  # offset 1 (data starts at 16+12=28)
        stream.write(b"\x00\x00\x00\x14")  # offset 2

        subtable = CblcIndexSubTableFormat17(
            format=17,
            first_glyph_id=1,
            last_glyph_id=3,
            additional_offset=16,
            data_format=1,
            metrics=CblcMetricsSmall(
                width=32, height=32, bit_depth=32,
                horizontal_origin_x=0, horizontal_origin_y=0,
                vertical_origin_x=0, vertical_origin_y=0
            ),
            offsets=[0, 12, 20]
        )
        assert subtable.format == 17
        assert subtable.first_glyph_id == 1
        assert subtable.last_glyph_id == 3
        assert subtable.additional_offset == 16
        assert subtable.data_format == 1
        assert len(subtable.offsets) == 3

    def test_parse_format18_with_jpeg(self, tmp_path):
        """Test parsing Format 18 subtable with JPEG data."""
        stream = BytesIO()
        stream.write(b"\x00\x12")  # format = 18
        stream.write(b"\x00\x05")  # first_glyph_id = 5
        stream.write(b"\x00\x07")  # last_glyph_id = 7
        stream.write(b"\x00\x00\x00\x20")  # additional_offset = 32
        stream.write(b"\x02")  # data_format = 2 (JPEG)
        stream.write(b"\x00\x00\x00")  # padding
        stream.write(b"\x00\x00\x00\x40")  # width = 64
        stream.write(b"\x00\x00\x00\x40")  # height = 64
        stream.write(b"\x20")  # bit_depth = 32
        stream.write(b"\x00")  # horizontal_origin_x = 0
        stream.write(b"\x00")  # horizontal_origin_y = 0
        stream.write(b"\x00")  # vertical_origin_x = 0
        stream.write(b"\x00")  # vertical_origin_y = 0
        stream.write(b"\x00\x00\x00\x40")  # horizontal_advance = 64
        stream.write(b"\x00\x00\x00\x40")  # vertical_advance = 64
        stream.write(b"\x00\x00\x00\x00")  # horizontal_bearing_x = 0
        stream.write(b"\x00\x00\x00\x40")  # horizontal_bearing_y = 64
        stream.write(b"\x00\x00\x00\x00")  # vertical_bearing_x = 0
        stream.write(b"\x00\x00\x00\x40")  # vertical_bearing_y = 64
        stream.write(b"\x00\x00\x00\x00")  # offset 0 (unused)
        stream.write(b"\x00\x00\x00\x10")  # offset 1
        stream.write(b"\x00\x00\x00\x18")  # offset 2
        stream.write(b"\x00\x00\x00\x20")  # offset 3

        subtable = CblcIndexSubTableFormat18(
            format=18,
            first_glyph_id=5,
            last_glyph_id=7,
            additional_offset=32,
            data_format=2,
            metrics=CblcMetricsBig(
                width=64, height=64, bit_depth=32,
                horizontal_origin_x=0, horizontal_origin_y=0,
                vertical_origin_x=0, vertical_origin_y=0,
                horizontal_advance=64, vertical_advance=64,
                horizontal_bearing_x=0, horizontal_bearing_y=64,
                vertical_bearing_x=0, vertical_bearing_y=64
            ),
            offsets=[0, 16, 24, 32]
        )
        assert subtable.format == 18
        assert subtable.first_glyph_id == 5
        assert subtable.last_glyph_id == 7
        assert subtable.data_format == 2
        assert len(subtable.offsets) == 4


class TestCblcTableParsing:
    """Tests for CBLC table parsing."""

    def test_parse_empty_cblo_table(self, tmp_path):
        """Test parsing CBLC table with zero strikes."""
        stream = BytesIO()
        stream.write(b"\x00\x02\x00\x00")  # version = 2.0
        stream.write(b"\x00\x00\x00\x00")  # num_strikes = 0

        rr = BinaryReader(stream.getvalue())
        table = CblcTable.from_reader(rr, len(stream.getvalue()))

        assert table.version == 0x00020000
        assert table.strikes == []
        assert table.index_subtables == []

    def test_parse_cblo_single_strike_no_subtables(self, tmp_path):
        """Test parsing CBLC table with one strike and no subtables."""
        stream = BytesIO()
        stream.write(b"\x00\x02\x00\x00")  # version = 2.0
        stream.write(b"\x00\x00\x00\x01")  # num_strikes = 1
        stream.write(b"\x00")  # ppem = 0 (invalid, will be stored as 0)
        stream.write(b"\x00")  # max_ppem = 0
        stream.write(b"\x20")  # bit_depth = 32
        stream.write(b"\x00")  # flags = 0
        stream.write(b"\x00\x00\x00\x00")  # offset_to_index_subtable = 0

        rr = BinaryReader(stream.getvalue())
        table = CblcTable.from_reader(rr, len(stream.getvalue()))

        assert table.version == 0x00020000
        assert len(table.strikes) == 1
        assert table.strikes[0].ppem == 0
        assert table.strikes[0].max_ppem is None
        assert table.strikes[0].bit_depth == 32
        assert table.strikes[0].flags == 0
        assert len(table.index_subtables) == 0

    def test_parse_cblo_multiple_strikes(self, tmp_path):
        """Test parsing CBLC table with multiple strikes."""
        stream = BytesIO()
        stream.write(b"\x00\x02\x00\x00")  # version = 2.0
        stream.write(b"\x00\x00\x00\x02")  # num_strikes = 2
        stream.write(b"\x00")  # ppem = 0
        stream.write(b"\x00")  # max_ppem = 0
        stream.write(b"\x20")  # bit_depth = 32
        stream.write(b"\x00")  # flags = 0
        stream.write(b"\x00\x00\x00\x18")  # offset_to_index_subtable = 24
        stream.write(b"\x00")  # ppem = 0
        stream.write(b"\x00")  # max_ppem = 0
        stream.write(b"\x20")  # bit_depth = 32
        stream.write(b"\x00")  # flags = 0
        stream.write(b"\x00\x00\x00\x18")  # offset_to_index_subtable = 24

        stream.write(b"\x00\x11")  # format = 17
        stream.write(b"\x00\x01")  # first_glyph_id = 1
        stream.write(b"\x00\x01")  # last_glyph_id = 1
        stream.write(b"\x00\x00\x00\x20")  # additional_offset = 32
        stream.write(b"\x01")  # data_format = 1 (PNG)
        stream.write(b"\x00\x00\x00")  # padding
        stream.write(b"\x00\x20")  # width = 32
        stream.write(b"\x00\x20")  # height = 32
        stream.write(b"\x20")  # bit_depth = 32
        stream.write(b"\x00")  # horizontal_origin_x = 0
        stream.write(b"\x00")  # horizontal_origin_y = 0
        stream.write(b"\x00")  # vertical_origin_x = 0
        stream.write(b"\x00")  # vertical_origin_y = 0
        stream.write(b"\x00\x00\x00\x00")  # offset 0

        rr = BinaryReader(stream.getvalue())
        table = CblcTable.from_reader(rr, len(stream.getvalue()))

        assert table.version == 0x00020000
        assert len(table.strikes) == 2
        assert len(table.index_subtables) == 1


class TestCblcStrikeRetrieval:
    """Tests for get_strikes() helper method."""

    def test_get_strikes_sorted(self, tmp_path):
        """Test get_strikes returns sorted list."""
        strike1 = CblcStrike(ppem=48, max_ppem=None, bit_depth=32, flags=0)
        strike2 = CblcStrike(ppem=16, max_ppem=None, bit_depth=8, flags=0)
        strike3 = CblcStrike(ppem=32, max_ppem=None, bit_depth=32, flags=0)

        table = CblcTable(
            version=0x00020000,
            strikes=[strike1, strike2, strike3],
            index_subtables=[]
        )

        strikes = table.get_strikes()
        assert strikes == [16, 32, 48]

    def test_get_strikes_empty(self, tmp_path):
        """Test get_strikes on table with no strikes."""
        table = CblcTable(
            version=0x00020000,
            strikes=[],
            index_subtables=[]
        )
        assert table.get_strikes() == []

    def test_get_strikes_multiple(self, tmp_path):
        """Test get_strikes with various ppem values."""
        strikes = [
            CblcStrike(ppem=ppem, max_ppem=None, bit_depth=32, flags=0)
            for ppem in [12, 24, 48, 64, 8]
        ]
        table = CblcTable(
            version=0x00020000,
            strikes=strikes,
            index_subtables=[]
        )
        assert table.get_strikes() == [8, 12, 24, 48, 64]


class TestCblcBitmapRetrieval:
    """Tests for get_glyph_bitmap() helper method."""

    def test_get_bitmap_no_coverage(self, tmp_path):
        """Test get_glyph_bitmap returns None for missing glyph."""
        strike = CblcStrike(ppem=24, max_ppem=None, bit_depth=32, flags=0)
        subtable = CblcIndexSubTableFormat17(
            format=17,
            first_glyph_id=10,
            last_glyph_id=20,
            additional_offset=128,
            data_format=1,
            metrics=CblcMetricsSmall(
                width=32, height=32, bit_depth=32,
                horizontal_origin_x=0, horizontal_origin_y=32,
                vertical_origin_x=0, vertical_origin_y=0
            ),
            offsets=[0, 12, 20]
        )
        table = CblcTable(
            version=0x00020000,
            strikes=[strike],
            index_subtables=[subtable]
        )

        result = table.get_glyph_bitmap(glyph_id=5, ppem=24)
        assert result is None

    def test_get_bitmap_returns_data(self, tmp_path):
        """Test get_glyph_bitmap returns bitmap data."""
        strike = CblcStrike(ppem=24, max_ppem=None, bit_depth=32, flags=0)

        subtable = CblcIndexSubTableFormat17(
            format=17,
            first_glyph_id=1,
            last_glyph_id=3,
            additional_offset=16,
            data_format=1,
            metrics=CblcMetricsSmall(
                width=32, height=32, bit_depth=32,
                horizontal_origin_x=0, horizontal_origin_y=32,
                vertical_origin_x=0, vertical_origin_y=0
            ),
            offsets=[0, 12, 20]
        )

        table = CblcTable(
            version=0x00020000,
            strikes=[strike],
            index_subtables=[subtable]
        )

        result = table.get_glyph_bitmap(glyph_id=2, ppem=24)
        assert result is None

    def test_get_bitmap_none_ppem_uses_highest(self, tmp_path):
        """Test get_glyph_bitmap with ppem=None uses highest strike."""
        strike_low = CblcStrike(ppem=16, max_ppem=None, bit_depth=8, flags=0)
        strike_high = CblcStrike(ppem=48, max_ppem=None, bit_depth=32, flags=0)

        subtable = CblcIndexSubTableFormat17(
            format=17,
            first_glyph_id=1,
            last_glyph_id=1,
            additional_offset=0,
            data_format=1,
            metrics=CblcMetricsSmall(
                width=64, height=64, bit_depth=32,
                horizontal_origin_x=0, horizontal_origin_y=64,
                vertical_origin_x=0, vertical_origin_y=0
            ),
            offsets=[0]
        )

        table = CblcTable(
            version=0x00020000,
            strikes=[strike_low, strike_high],
            index_subtables=[subtable]
        )

        result = table.get_glyph_bitmap(glyph_id=1, ppem=None)
        assert result is None

    def test_get_bitmap_specific_ppem(self, tmp_path):
        """Test get_glyph_bitmap with specific ppem."""
        strike_16 = CblcStrike(ppem=16, max_ppem=None, bit_depth=8, flags=0)
        strike_32 = CblcStrike(ppem=32, max_ppem=None, bit_depth=32, flags=0)

        subtable = CblcIndexSubTableFormat17(
            format=17,
            first_glyph_id=1,
            last_glyph_id=1,
            additional_offset=0,
            data_format=1,
            metrics=CblcMetricsSmall(
                width=32, height=32, bit_depth=32,
                horizontal_origin_x=0, horizontal_origin_y=32,
                vertical_origin_x=0, vertical_origin_y=0
            ),
            offsets=[0]
        )

        table = CblcTable(
            version=0x00020000,
            strikes=[strike_16, strike_32],
            index_subtables=[subtable]
        )

        result_16 = table.get_glyph_bitmap(glyph_id=1, ppem=16)
        result_32 = table.get_glyph_bitmap(glyph_id=1, ppem=32)
        assert result_16 is None
        assert result_32 is None

    def test_get_bitmap_missing_ppem(self, tmp_path):
        """Test get_glyph_bitmap returns None for missing ppem."""
        strike = CblcStrike(ppem=24, max_ppem=None, bit_depth=32, flags=0)

        subtable = CblcIndexSubTableFormat17(
            format=17,
            first_glyph_id=1,
            last_glyph_id=1,
            additional_offset=0,
            data_format=1,
            metrics=CblcMetricsSmall(
                width=32, height=32, bit_depth=32,
                horizontal_origin_x=0, horizontal_origin_y=32,
                vertical_origin_x=0, vertical_origin_y=0
            ),
            offsets=[0]
        )

        table = CblcTable(
            version=0x00020000,
            strikes=[strike],
            index_subtables=[subtable]
        )

        result = table.get_glyph_bitmap(glyph_id=1, ppem=48)
        assert result is None


class TestCbdtTableParsing:
    """Tests for CBDT table parsing."""

    def test_parse_empty_cbdt_table(self, tmp_path):
        """Test parsing CBDT table with zero strikes."""
        stream = BytesIO()
        stream.write(b"\x00\x02\x00\x00")  # version = 2.0
        stream.write(b"\x00\x00\x00\x00")  # num_strikes = 0

        rr = BinaryReader(stream.getvalue())
        table = CbdtTable.from_reader(rr, len(stream.getvalue()))

        assert table.version == 0x00020000
        assert table.strikes == []
        assert table.bitmaps == []

    def test_parse_cbdt_single_strike(self, tmp_path):
        """Test parsing CBDT table with one strike and one glyph."""
        bitmap_data = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIEND\xAE\x42\x60\x82"

        stream = BytesIO()
        stream.write(b"\x00\x02\x00\x00")  # version = 2.0 (4 bytes)
        stream.write(b"\x00\x00\x00\x01")  # num_strikes = 1 (4 bytes) = 8 bytes total
        stream.write(b"\x10")  # ppem = 16 (1 byte)
        stream.write(b"\x00")  # max_ppem = 0 (1 byte)
        stream.write(b"\x20")  # bit_depth = 32 (1 byte)
        stream.write(b"\x00")  # flags = 0 (1 byte)
        stream.write(b"\x00\x00\x00\x18")  # offset_to_index_subtable = 24 (4 bytes)
        stream.write(b"\x00\x00\x00\x00")  # padding (4 bytes)
        stream.write(b"\x00\x00\x00\x00")  # padding (4 bytes) = 24 bytes total, now at offset 24

        stream.write(b"\x00\x11")  # format = 17 (2 bytes)
        stream.write(b"\x00\x01")  # first_glyph_id = 1 (2 bytes)
        stream.write(b"\x00\x01")  # last_glyph_id = 1 (2 bytes)
        stream.write(b"\x00\x00\x00\x36")  # additional_offset = 54 (4 bytes)
        stream.write(b"\x01")  # data_format = 1 (PNG) (1 byte)
        stream.write(b"\x00\x00\x00")  # padding (3 bytes)
        stream.write(b"\x00\x20")  # width = 32 (2 bytes)
        stream.write(b"\x00\x20")  # height = 32 (2 bytes)
        stream.write(b"\x20")  # bit_depth = 32 (1 byte)
        stream.write(b"\x00")  # horizontal_origin_x = 0 (1 byte)
        stream.write(b"\x00")  # horizontal_origin_y = 0 (1 byte)
        stream.write(b"\x00")  # vertical_origin_x = 0 (1 byte)
        stream.write(b"\x00")  # vertical_origin_y = 0 (1 byte)
        stream.write(b"\x00\x00\x00\x0C")  # offset 0 = 12 (4 bytes)

        stream.write(b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00")  # padding (15 bytes) to align to position 66 (additional_offset + offset = 54 + 12)
        stream.write(b"\x01")  # data_format = 1 (PNG) at absolute position 66
        stream.write(b"\x00\x00\x00")  # padding (3 bytes)
        stream.write(b"\x00\x00\x00\x14")  # PNG length = 20 (4 bytes)
        stream.write(bitmap_data)  # PNG data (20 bytes)

        rr = BinaryReader(stream.getvalue())
        table = CbdtTable.from_reader(rr, len(stream.getvalue()))

        assert table.version == 0x00020000
        assert len(table.strikes) == 1
        assert len(table.bitmaps) == 1
        assert table.bitmaps[0].glyph_id == 1
        assert table.bitmaps[0].data_format == 1
        assert table.bitmaps[0].bitmap_data == bitmap_data
        assert table.bitmaps[0].width == 32
        assert table.bitmaps[0].height == 32


class TestCblcCbdtIntegration:
    """Tests for CBLC and CBDT integration."""

    def test_cblo_and_cbdt_version_match(self, tmp_path):
        """Test that CBLC and CBDT can have matching versions."""
        cblc_stream = BytesIO()
        cblc_stream.write(b"\x00\x02\x00\x00")
        cblc_stream.write(b"\x00\x00\x00\x00")

        cbdt_stream = BytesIO()
        cbdt_stream.write(b"\x00\x02\x00\x00")
        cbdt_stream.write(b"\x00\x00\x00\x00")

        cblc_rr = BinaryReader(cblc_stream.getvalue())
        cbdt_rr = BinaryReader(cbdt_stream.getvalue())

        cblc_table = CblcTable.from_reader(cblc_rr, len(cblc_stream.getvalue()))
        cbdt_table = CbdtTable.from_reader(cbdt_rr, len(cbdt_stream.getvalue()))

        assert cblc_table.version == cbdt_table.version

    def test_strikes_must_match(self, tmp_path):
        """Test that CBLC and CBDT should have matching strike structures."""
        cblc_stream = BytesIO()
        cblc_stream.write(b"\x00\x02\x00\x00")
        cblc_stream.write(b"\x00\x00\x00\x01")
        cblc_stream.write(b"\x00")  # ppem = 0
        cblc_stream.write(b"\x00")  # max_ppem = 0
        cblc_stream.write(b"\x20")  # bit_depth = 32
        cblc_stream.write(b"\x00")  # flags = 0
        cblc_stream.write(b"\x00\x00\x00\x00")  # offset_to_index_subtable = 0

        cbdt_stream = BytesIO()
        cbdt_stream.write(b"\x00\x02\x00\x00")
        cbdt_stream.write(b"\x00\x00\x00\x01")
        cbdt_stream.write(b"\x00")  # ppem = 0
        cbdt_stream.write(b"\x00")  # max_ppem = 0
        cbdt_stream.write(b"\x20")  # bit_depth = 32
        cbdt_stream.write(b"\x00")  # flags = 0
        cbdt_stream.write(b"\x00\x00\x00\x00")  # offset_to_index_subtable = 0

        cblc_rr = BinaryReader(cblc_stream.getvalue())
        cbdt_rr = BinaryReader(cbdt_stream.getvalue())

        cblc_table = CblcTable.from_reader(cblc_rr, len(cblc_stream.getvalue()))
        cbdt_table = CbdtTable.from_reader(cbdt_rr, len(cbdt_stream.getvalue()))

        assert len(cblc_table.strikes) == len(cbdt_table.strikes)

    def test_glyph_lookup_across_strikes(self, tmp_path):
        """Test glyph lookup across multiple strikes."""
        strikes = [
            CblcStrike(ppem=16, max_ppem=None, bit_depth=8, flags=0),
            CblcStrike(ppem=32, max_ppem=None, bit_depth=32, flags=0),
            CblcStrike(ppem=48, max_ppem=None, bit_depth=32, flags=0),
        ]

        subtable = CblcIndexSubTableFormat17(
            format=17,
            first_glyph_id=1,
            last_glyph_id=1,
            additional_offset=0,
            data_format=1,
            metrics=CblcMetricsSmall(
                width=32, height=32, bit_depth=32,
                horizontal_origin_x=0, horizontal_origin_y=32,
                vertical_origin_x=0, vertical_origin_y=0
            ),
            offsets=[0]
        )

        table = CblcTable(
            version=0x00020000,
            strikes=strikes,
            index_subtables=[subtable]
        )

        for ppem in [16, 32, 48]:
            result = table.get_glyph_bitmap(glyph_id=1, ppem=ppem)
            assert result is None

    def test_complex_font_with_multiple_strikes(self, tmp_path):
        """Test complex font with multiple strikes and subtables."""
        strikes = [
            CblcStrike(ppem=16, max_ppem=None, bit_depth=8, flags=0),
            CblcStrike(ppem=24, max_ppem=None, bit_depth=32, flags=0),
            CblcStrike(ppem=32, max_ppem=None, bit_depth=32, flags=0),
        ]

        subtables = []
        for strike in strikes:
            subtable = CblcIndexSubTableFormat17(
                format=17,
                first_glyph_id=1,
                last_glyph_id=10,
                additional_offset=0,
                data_format=1,
                metrics=CblcMetricsSmall(
                    width=strike.ppem, height=strike.ppem, bit_depth=strike.bit_depth,
                    horizontal_origin_x=0, horizontal_origin_y=strike.ppem,
                    vertical_origin_x=0, vertical_origin_y=0
                ),
                offsets=[0] * 10
            )
            subtables.append(subtable)

        table = CblcTable(
            version=0x00020000,
            strikes=strikes,
            index_subtables=subtables
        )

        assert len(table.strikes) == 3
        assert len(table.index_subtables) == 3
        assert table.get_strikes() == [16, 24, 32]


class TestCbdtGlyphBitmapDataclass:
    """Tests for CbdtGlyphBitmap dataclass."""

    def test_glyph_bitmap_structure(self):
        """Test that CbdtGlyphBitmap has correct fields."""
        bitmap = CbdtGlyphBitmap(
            glyph_id=5,
            data_format=1,
            bitmap_data=b"\x89PNG\r\n\x1a\n",
            width=32,
            height=32,
            bearing_x=0,
            bearing_y=32,
            advance=32
        )
        assert bitmap.glyph_id == 5
        assert bitmap.data_format == 1
        assert bitmap.bitmap_data == b"\x89PNG\r\n\x1a\n"
        assert bitmap.width == 32
        assert bitmap.height == 32
        assert bitmap.bearing_x == 0
        assert bitmap.bearing_y == 32
        assert bitmap.advance == 32

    def test_glyph_bitmap_slots(self):
        """Test that CbdtGlyphBitmap uses __slots__."""
        bitmap = CbdtGlyphBitmap(
            glyph_id=1,
            data_format=1,
            bitmap_data=b"",
            width=24,
            height=24,
            bearing_x=0,
            bearing_y=24,
            advance=24
        )
        assert not hasattr(bitmap, "__dict__")
