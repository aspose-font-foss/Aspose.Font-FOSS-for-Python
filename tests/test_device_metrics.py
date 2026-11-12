"""Tests for OpenType Device Metrics (hdmx & vdmx) table parsers."""
from __future__ import annotations

import pytest

from aspose_font._exceptions import FontParseException
from aspose_font._io import BinaryReader, BinaryWriter
from aspose_font.ttf.tables.hdmx import HdmxRecord, HdmxTable, VdmxGroup, VdmxTable


class TestHdmxRecord:
    def test_dataclass_fields(self) -> None:
        record = HdmxRecord(pixel_size=12, widths=[100, 120, 80])
        assert record.pixel_size == 12
        assert record.widths == [100, 120, 80]


class TestVdmxGroup:
    def test_dataclass_fields(self) -> None:
        group = VdmxGroup(y_pel_height=10, y_max=800, y_min=-200)
        assert group.y_pel_height == 10
        assert group.y_max == 800
        assert group.y_min == -200


class TestHdmxTableParsing:
    def test_parse_hdmx_from_bytes(self) -> None:
        bw = BinaryWriter()
        bw.write_u16(0x0001)
        bw.write_u16(2)
        bw.write_u32(8)
        bw.write_u8(12)
        bw.write_u8(3)
        bw.write_i8(100)
        bw.write_i8(120)
        bw.write_i8(80)
        bw.write_u8(14)
        bw.write_u8(2)
        bw.write_i8(-10)
        bw.write_i8(30)
        data = bw.to_bytes()
        reader = BinaryReader(data)

        table = HdmxTable.from_reader(reader, len(data))
        assert table.version == 0x0001
        assert table.num_records == 2
        assert table.size_device_record == 8
        assert len(table.records) == 2

        assert table.records[0].pixel_size == 12
        assert table.records[0].widths == [100, 120, 80]
        assert table.records[1].pixel_size == 14
        assert table.records[1].widths == [-10, 30]

    def test_parse_vdmx_from_bytes(self) -> None:
        bw = BinaryWriter()
        bw.write_u16(0x0001)
        bw.write_u16(2)
        bw.write_u8(1)
        bw.write_u8(0)
        bw.write_u16(12)
        bw.write_u16(1)
        bw.write_u16(0)
        bw.write_u8(50)
        bw.write_u8(50)
        bw.write_u8(50)
        bw.write_u8(1)
        bw.write_u8(2)
        bw.write_u8(10)
        bw.write_i16(800)
        bw.write_i16(-200)
        bw.write_u8(20)
        bw.write_i16(900)
        bw.write_i16(-150)
        data = bw.to_bytes()
        reader = BinaryReader(data)

        table = VdmxTable.from_reader(reader, len(data))
        assert table.version == 0x0001
        assert table.num_recs == 2
        assert table.num_ratios == 1
        assert len(table.groups) == 2
        assert table.groups[0].y_pel_height == 10
        assert table.groups[0].y_max == 800
        assert table.groups[0].y_min == -200
        assert table.groups[1].y_pel_height == 20
        assert table.groups[1].y_max == 900
        assert table.groups[1].y_min == -150

    def test_get_metrics_hdmx_found(self) -> None:
        bw = BinaryWriter()
        bw.write_u16(0x0001)
        bw.write_u16(2)
        bw.write_u32(8)
        bw.write_u8(12)
        bw.write_u8(3)
        bw.write_i8(100)
        bw.write_i8(120)
        bw.write_i8(80)
        bw.write_u8(14)
        bw.write_u8(2)
        bw.write_i8(-10)
        bw.write_i8(30)
        data = bw.to_bytes()
        reader = BinaryReader(data)

        table = HdmxTable.from_reader(reader, len(data))
        metrics = table.get_metrics(12)
        assert metrics is not None
        assert metrics[0] == 120
        assert metrics[1] == 80

    def test_get_metrics_hdmx_not_found(self) -> None:
        bw = BinaryWriter()
        bw.write_u16(0x0001)
        bw.write_u16(1)
        bw.write_u32(4)
        bw.write_u8(12)
        bw.write_u8(1)
        bw.write_i8(100)
        data = bw.to_bytes()
        reader = BinaryReader(data)

        table = HdmxTable.from_reader(reader, len(data))
        assert table.get_metrics(99) is None

    def test_get_metrics_vdmx_found(self) -> None:
        bw = BinaryWriter()
        bw.write_u16(0x0001)
        bw.write_u16(1)
        bw.write_u8(0)
        bw.write_u8(0)
        bw.write_u16(8)
        bw.write_u16(1)
        bw.write_u16(0)
        bw.write_u8(10)
        bw.write_i16(800)
        bw.write_i16(-200)
        data = bw.to_bytes()
        reader = BinaryReader(data)

        table = VdmxTable.from_reader(reader, len(data))
        metrics = table.get_metrics(10)
        assert metrics == (800, -200)

    def test_get_metrics_vdmx_not_found(self) -> None:
        bw = BinaryWriter()
        bw.write_u16(0x0001)
        bw.write_u16(1)
        bw.write_u8(0)
        bw.write_u8(0)
        bw.write_u16(8)
        bw.write_u16(1)
        bw.write_u16(0)
        bw.write_u8(10)
        bw.write_i16(800)
        bw.write_i16(-200)
        data = bw.to_bytes()
        reader = BinaryReader(data)

        table = VdmxTable.from_reader(reader, len(data))
        assert table.get_metrics(99) is None

    def test_parse_hdmx_invalid_version(self) -> None:
        bw = BinaryWriter()
        bw.write_u16(0x0002)
        bw.write_u16(1)
        bw.write_u32(4)
        data = bw.to_bytes()
        reader = BinaryReader(data)

        with pytest.raises(FontParseException) as exc_info:
            HdmxTable.from_reader(reader, len(data))
        assert "Unsupported hdmx table version" in str(exc_info.value)

    def test_parse_vdmx_invalid_version(self) -> None:
        bw = BinaryWriter()
        bw.write_u16(0x0002)
        bw.write_u16(1)
        data = bw.to_bytes()
        reader = BinaryReader(data)

        with pytest.raises(FontParseException) as exc_info:
            VdmxTable.from_reader(reader, len(data))
        assert "Unsupported vdmx table version" in str(exc_info.value)

    def test_parse_hdmx_truncated_data(self) -> None:
        bw = BinaryWriter()
        bw.write_u16(0x0001)
        bw.write_u16(1)
        bw.write_u32(100)
        data = bw.to_bytes()
        reader = BinaryReader(data)

        with pytest.raises(FontParseException):
            HdmxTable.from_reader(reader, len(data))

    def test_parse_vdmx_truncated_data(self) -> None:
        bw = BinaryWriter()
        bw.write_u16(0x0001)
        bw.write_u16(1)
        data = bw.to_bytes()
        reader = BinaryReader(data)

        with pytest.raises(FontParseException):
            VdmxTable.from_reader(reader, len(data))

    def test_empty_hdmx_table(self) -> None:
        bw = BinaryWriter()
        bw.write_u16(0x0001)
        bw.write_u16(0)
        bw.write_u32(4)
        data = bw.to_bytes()
        reader = BinaryReader(data)

        table = HdmxTable.from_reader(reader, len(data))
        assert table.num_records == 0
        assert table.records == []
        assert table.get_metrics(12) is None

    def test_empty_vdmx_table(self) -> None:
        bw = BinaryWriter()
        bw.write_u16(0x0001)
        bw.write_u16(0)
        bw.write_u8(0)
        bw.write_u8(0)
        bw.write_u16(8)
        bw.write_u16(0)
        bw.write_u16(0)
        data = bw.to_bytes()
        reader = BinaryReader(data)

        table = VdmxTable.from_reader(reader, len(data))
        assert table.num_recs == 0
        assert table.groups == []
        assert table.get_metrics(10) is None


class TestCrossPlatform:
    def test_paths_use_pathlib(self) -> None:
        from pathlib import Path
        test_file = Path(__file__).resolve()
        assert test_file.exists()
