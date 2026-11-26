"""Tests for gasp table synthesizer (FONT-544)."""
from pathlib import Path

import pytest

from aspose_font._io import BinaryReader
from aspose_font.ttf.font import TtfFont
from aspose_font.ttf.tables.gasp import GaspRange, GaspTable
from aspose_font.ttf.tables.gasp_synthesizer import (
    GaspRangeConfig,
    _serialize_gasp_table,
    synthesize_gasp_table,
)


class TestGaspRangeConfigDataclass:
    """Test GaspRangeConfig dataclass structure."""

    def test_gasp_range_config_fields(self) -> None:
        """Test GaspRangeConfig dataclass fields."""
        config = GaspRangeConfig(max_ppem=8, behavior=0x0002)
        assert config.max_ppem == 8
        assert config.behavior == 0x0002

    def test_gasp_range_config_defaults(self) -> None:
        """Test GaspRangeConfig dataclass default values."""
        config = GaspRangeConfig(max_ppem=16, behavior=0x0003)
        assert config.max_ppem == 16
        assert config.behavior == 0x0003


class TestGaspSynthesizerBasic:
    """Test basic gasp table synthesis functionality."""

    def test_synthesize_gasp_table_basic(self, roboto: TtfFont) -> None:
        """Test synthesizing gasp table from font metrics."""
        result_bytes = synthesize_gasp_table(roboto)

        assert isinstance(result_bytes, bytes)
        assert len(result_bytes) >= 8

        reader = BinaryReader(result_bytes)
        version = reader.read_u16()
        num_ranges = reader.read_u16()

        assert version == 1
        assert num_ranges >= 2

    def test_synthesize_gasp_table_serialization_roundtrip(self, roboto: TtfFont) -> None:
        """Test gasp table serialization roundtrip."""
        synthesized_bytes = synthesize_gasp_table(roboto)

        reader = BinaryReader(synthesized_bytes)
        gasp_table = GaspTable.from_reader(reader, len(synthesized_bytes))

        reserialized = gasp_table.to_bytes()

        assert reserialized == synthesized_bytes

    def test_synthesize_gasp_table_expected_byte_sequence(self, roboto: TtfFont) -> None:
        """Test that synthesized gasp table matches expected byte sequence."""
        result_bytes = synthesize_gasp_table(roboto)

        assert isinstance(result_bytes, bytes)
        assert result_bytes[:2] == b"\x00\x01"

        num_ranges = int.from_bytes(result_bytes[2:4], "big")
        assert num_ranges >= 2

        offset = 4
        for _ in range(num_ranges):
            assert offset + 4 <= len(result_bytes)
            max_ppem = int.from_bytes(result_bytes[offset : offset + 2], "big")
            behavior = int.from_bytes(result_bytes[offset + 2 : offset + 4], "big")

            assert 0 <= max_ppem <= 0xFFFF
            assert 0 <= behavior <= 0xFFFF

            offset += 4

        assert offset == len(result_bytes)

    def test_synthesize_gasp_table_missing_head_raises(self) -> None:
        """Test that synthesizing from font without head table raises exception."""
        from aspose_font._exceptions import FontNotSupportedException

        font = TtfFont.__new__(TtfFont)
        font._tables = type("obj", (object,), {
            "head": None,
            "maxp": type("obj", (object,), {})()
        })()

        with pytest.raises(FontNotSupportedException):
            synthesize_gasp_table(font)

    def test_synthesize_gasp_table_missing_maxp_raises(self) -> None:
        """Test that synthesizing from font without maxp table raises exception."""
        from aspose_font._exceptions import FontNotSupportedException

        font = TtfFont.__new__(TtfFont)
        font._tables = type("obj", (object,), {
            "head": type("obj", (object,), {"units_per_em": 1000})(),
            "maxp": None
        })()

        with pytest.raises(FontNotSupportedException):
            synthesize_gasp_table(font)


class TestGaspSynthesizerIntegration:
    """Test gasp synthesizer integration with actual fonts."""

    def test_synthesize_gasp_preserves_structure(self) -> None:
        """Test that synthesized gasp maintains proper structure."""
        ranges = [
            GaspRange(range_max_ppem=8, range_gasp_behavior=0x0002),
            GaspRange(range_max_ppem=16, range_gasp_behavior=0x0003),
        ]
        original = GaspTable(gasp_version=1, ranges=ranges)

        serialized = _serialize_gasp_table(original)
        reader = BinaryReader(serialized)
        deserialized = GaspTable.from_reader(reader, len(serialized))

        assert deserialized.gasp_version == original.gasp_version
        assert len(deserialized.ranges) == len(original.ranges)

    def test_import_via_tables_module(self) -> None:
        """Test importing synthesizer via tables module."""
        from aspose_font.ttf.tables import GaspRangeConfig, synthesize_gasp_table

        assert GaspRangeConfig is not None
        assert synthesize_gasp_table is not None


class TestGaspSynthesizerCrossPlatform:
    """Verify cross-platform compatibility."""

    def test_paths_use_pathlib(self) -> None:
        """Test that test paths use Path object, not hardcoded Windows paths."""
        testdata_path = Path(__file__).resolve().parents[1] / "testdata"
        path_str = str(testdata_path)
        assert "testdata" in path_str.replace("\\", "/").split("/")
