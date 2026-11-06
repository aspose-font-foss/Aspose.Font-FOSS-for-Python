"""Tests for VORG table parsing (FONT-488)."""
from pathlib import Path

import pytest

from aspose_font._exceptions import FontParseException
from aspose_font._io import BinaryReader, BinaryWriter
from aspose_font.ttf.tables.vorg import VertOriginYMetric, VorgTable


class TestVorgParsing:
    """Test VORG table parsing from binary data."""

    def test_vert_origin_y_metric_dataclass(self) -> None:
        """Test VertOriginYMetric dataclass structure."""
        metric = VertOriginYMetric(glyph_id=5, vert_origin_y=800)
        assert metric.glyph_id == 5
        assert metric.vert_origin_y == 800

    def test_vorg_table_dataclass(self) -> None:
        """Test VorgTable dataclass structure."""
        metrics = [
            VertOriginYMetric(glyph_id=1, vert_origin_y=750),
            VertOriginYMetric(glyph_id=2, vert_origin_y=760),
        ]
        table = VorgTable(
            major_version=1,
            minor_version=0,
            default_vert_origin_y=800,
            vert_origin_y_metrics=metrics
        )
        assert table.major_version == 1
        assert table.minor_version == 0
        assert table.default_vert_origin_y == 800
        assert len(table.vert_origin_y_metrics) == 2

    def test_parse_vorg_from_bytes(self) -> None:
        """Test parsing VORG table from binary data."""
        bw = BinaryWriter()
        bw.write_u16(1)
        bw.write_u16(0)
        bw.write_i16(800)
        bw.write_u16(2)
        bw.write_u16(1)
        bw.write_i16(750)
        bw.write_u16(2)
        bw.write_i16(760)

        data = bw.to_bytes()
        reader = BinaryReader(data)
        table = VorgTable.from_reader(reader, len(data))

        assert table.major_version == 1
        assert table.minor_version == 0
        assert table.default_vert_origin_y == 800
        assert len(table.vert_origin_y_metrics) == 2
        assert table.vert_origin_y_metrics[0].glyph_id == 1
        assert table.vert_origin_y_metrics[0].vert_origin_y == 750
        assert table.vert_origin_y_metrics[1].glyph_id == 2
        assert table.vert_origin_y_metrics[1].vert_origin_y == 760

    def test_parse_vorg_invalid_version(self) -> None:
        """Test that invalid VORG version raises FontParseException."""
        bw = BinaryWriter()
        bw.write_u16(2)
        bw.write_u16(0)
        bw.write_i16(800)
        bw.write_u16(0)

        data = bw.to_bytes()
        reader = BinaryReader(data)

        with pytest.raises(FontParseException):
            VorgTable.from_reader(reader, len(data))


class TestVorgGetVertOriginY:
    """Test get_vert_origin_y() method."""

    def test_get_metric_returns_glyph_specific_value(self) -> None:
        """Test get_vert_origin_y returns glyph-specific value."""
        metrics = [VertOriginYMetric(glyph_id=5, vert_origin_y=750)]
        table = VorgTable(
            major_version=1,
            minor_version=0,
            default_vert_origin_y=800,
            vert_origin_y_metrics=metrics
        )
        assert table.get_vert_origin_y(5) == 750

    def test_get_metric_returns_default_for_missing_glyph(self) -> None:
        """Test get_vert_origin_y returns default for unknown glyph."""
        metrics = [VertOriginYMetric(glyph_id=5, vert_origin_y=750)]
        table = VorgTable(
            major_version=1,
            minor_version=0,
            default_vert_origin_y=800,
            vert_origin_y_metrics=metrics
        )
        assert table.get_vert_origin_y(10) == 800

    def test_get_metric_prefers_first_match_if_duplicates(self) -> None:
        """Test get_vert_origin_y returns first match if duplicates exist."""
        metrics = [
            VertOriginYMetric(glyph_id=5, vert_origin_y=750),
            VertOriginYMetric(glyph_id=5, vert_origin_y=700),
        ]
        table = VorgTable(
            major_version=1,
            minor_version=0,
            default_vert_origin_y=800,
            vert_origin_y_metrics=metrics
        )
        assert table.get_vert_origin_y(5) == 750


class TestVorgCrossPlatform:
    """Verify cross-platform compatibility."""

    def test_paths_use_pathlib(self) -> None:
        """Test that test paths use Path object, not hardcoded Windows paths."""
        testdata_path = Path(__file__).resolve().parents[1] / "testdata"
        assert "testdata" in str(testdata_path).split("\\") or "testdata" in str(testdata_path).split("/")
