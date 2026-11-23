"""Tests for GDEF table parser (Glyph Definition)."""

from __future__ import annotations

from pathlib import Path

from aspose_font import TtfFont
from aspose_font._io import BinaryReader
from aspose_font.ttf.tables.gdef import (
    GdefTable,
    _CaretValue,
)


class TestClassDefinitionTable:
    """Test class definition table parsing."""

    def test_class_format_1_single_glyphs(self):
        """Test format 1 class definition with individual glyph indices."""
        from aspose_font.ttf.tables.gdef import _parse_class_definition

        data = b"\x00\x01\x00\x03\x00\x01\x00\x02\x00\x03"
        class_def = _parse_class_definition(BinaryReader(data), 0, data)

        assert class_def.format == 1
        assert class_def.get_class(0) == 1
        assert class_def.get_class(1) == 2
        assert class_def.get_class(2) == 3
        assert class_def.get_class(3) == 0

    def test_class_format_2_range_records(self):
        """Test format 2 class definition with range records."""
        from aspose_font.ttf.tables.gdef import _parse_class_definition

        data = (
            b"\x00\x02\x00\x02"
            b"\x00\x01\x00\x02\x00\x01"
            b"\x00\x05\x00\x07\x00\x02"
        )
        class_def = _parse_class_definition(BinaryReader(data), 0, data)

        assert class_def.format == 2
        assert class_def.get_class(0) == 0
        assert class_def.get_class(1) == 1
        assert class_def.get_class(2) == 1
        assert class_def.get_class(3) == 0
        assert class_def.get_class(5) == 2
        assert class_def.get_class(6) == 2
        assert class_def.get_class(7) == 2
        assert class_def.get_class(8) == 0

    def test_class_format_2_empty_range(self):
        """Test format 2 class definition with no matching range."""
        from aspose_font.ttf.tables.gdef import _parse_class_definition

        data = (
            b"\x00\x02\x00\x01"
            b"\x00\x10\x00\x1F\x00\x01"
        )
        class_def = _parse_class_definition(BinaryReader(data), 0, data)

        assert class_def.get_class(0) == 0
        assert class_def.get_class(15) == 0
        assert class_def.get_class(16) == 1
        assert class_def.get_class(31) == 1
        assert class_def.get_class(32) == 0


class TestCaretValue:
    """Test CaretValue parsing."""

    def test_caret_format_1(self):
        """Test caret format 1 (design units)."""
        caret = _CaretValue(format=1, value=500)
        assert caret.format == 1
        assert caret.value == 500

    def test_caret_format_2(self):
        """Test caret format 2 (contour point)."""
        caret = _CaretValue(format=2, value=0, contour_point=3)
        assert caret.format == 2
        assert caret.contour_point == 3

    def test_caret_format_3(self):
        """Test caret format 3 (device variation)."""
        caret = _CaretValue(format=3, value=100, device_table_offset=6)
        assert caret.format == 3
        assert caret.device_table_offset == 6


class TestLigatureCaretList:
    """Test ligature caret list parsing."""

    def test_parse_ligature_caret_list_empty(self):
        """Test parsing empty ligature caret list."""
        from aspose_font.ttf.tables.gdef import _parse_ligature_caret_list

        data = b"\x00\x00"
        lig_carets = _parse_ligature_caret_list(BinaryReader(data), 0, data)

        assert lig_carets.caret_count == 0
        assert lig_carets.caret_values == []

    def test_parse_ligature_caret_list_with_carets(self):
        """Test parsing ligature caret list with carets."""
        from aspose_font.ttf.tables.gdef import _parse_ligature_caret_list

        # GDEF ligature caret list structure:
        # - uint16: caret count (2 carets)
        # - uint16[2]: offsets from this table start to each caret value
        # - At offset 6: CaretValue format 1 (value=50)
        # - At offset 10: CaretValue format 1 (value=100)
        # Offsets are relative to the start of the ligature caret list
        data = (
            b"\x00\x02"           # bytes 0-1: caret_count = 2
            b"\x00\x06\x00\x0A"   # bytes 2-5: offsets to caret values (6 and 10)
            b"\x00\x01\x00\x32"  # bytes 6-9: caret 1 value (format=1, value=50)
            b"\x00\x01\x00\x64"  # bytes 10-13: caret 2 value (format=1, value=100)
        )
        lig_carets = _parse_ligature_caret_list(BinaryReader(data), 0, data)

        assert lig_carets.caret_count == 2
        assert len(lig_carets.caret_values) == 2
        assert lig_carets.caret_values[0].format == 1
        assert lig_carets.caret_values[0].value == 50
        assert lig_carets.caret_values[1].format == 1
        assert lig_carets.caret_values[1].value == 100


class TestGdefTableParsing:
    """Test GDEF table parsing from byte streams."""

    def test_parse_gdef_version_1_0(self):
        """Test parsing GDEF version 1.0 with all offsets at 0 (no optional tables)."""
        data = (
            b"\x00\x01\x00\x00"
            b"\x00\x00"
            b"\x00\x00"
            b"\x00\x00"
            b"\x00\x00"
        )
        r = BinaryReader(data)
        gdef = GdefTable.from_reader(r, len(data))

        assert gdef.version == 0x00010000
        assert gdef.glyph_class_def_offset == 0
        assert gdef.attachment_point_list_offset == 0
        assert gdef.ligature_caret_list_offset == 0
        assert gdef.mark_attachment_class_def_offset == 0
        assert gdef.glyph_class_def is None
        assert gdef.ligature_caret_list is None
        assert gdef.mark_attachment_class_def is None

    def test_parse_gdef_version_1_2(self):
        """Test parsing GDEF version 1.2 with all offsets at 0 (no optional tables)."""
        data = (
            b"\x00\x01\x00\x02"
            b"\x00\x00"
            b"\x00\x00"
            b"\x00\x00"
            b"\x00\x00"
        )
        r = BinaryReader(data)
        gdef = GdefTable.from_reader(r, len(data))

        assert gdef.version == 0x00010002
        assert gdef.glyph_class_def_offset == 0
        assert gdef.attachment_point_list_offset == 0
        assert gdef.ligature_caret_list_offset == 0
        assert gdef.mark_attachment_class_def_offset == 0
        assert gdef.glyph_class_def is None
        assert gdef.ligature_caret_list is None
        assert gdef.mark_attachment_class_def is None

    def test_parse_gdef_version_1_3(self):
        """Test parsing GDEF version 1.3 with all offsets at 0 (no optional tables)."""
        data = (
            b"\x00\x01\x00\x03"
            b"\x00\x00"
            b"\x00\x00"
            b"\x00\x00"
            b"\x00\x00"
        )
        r = BinaryReader(data)
        gdef = GdefTable.from_reader(r, len(data))

        assert gdef.version == 0x00010003
        assert gdef.glyph_class_def_offset == 0
        assert gdef.attachment_point_list_offset == 0
        assert gdef.ligature_caret_list_offset == 0
        assert gdef.mark_attachment_class_def_offset == 0
        assert gdef.glyph_class_def is None
        assert gdef.ligature_caret_list is None
        assert gdef.mark_attachment_class_def is None

    def test_parse_gdef_with_glyph_class_format_1(self):
        """Test GDEF with glyph class definition format 1."""
        data = (
            b"\x00\x01\x00\x00"
            b"\x00\x0C"
            b"\x00\x00"
            b"\x00\x00"
            b"\x00\x00"
            b"\x00\x01"
            b"\x00\x03"
            b"\x00\x01"
            b"\x00\x02"
            b"\x00\x03"
        )
        r = BinaryReader(data)
        gdef = GdefTable.from_reader(r, len(data))

        assert gdef.get_glyph_class(0) == 1
        assert gdef.get_glyph_class(1) == 2
        assert gdef.get_glyph_class(2) == 3

    def test_parse_gdef_with_glyph_class_format_2(self):
        """Test GDEF with glyph class definition format 2."""
        data = (
            b"\x00\x01\x00\x00"
            b"\x00\x0C"
            b"\x00\x00"
            b"\x00\x00"
            b"\x00\x00"
            b"\x00\x02"
            b"\x00\x01"
            b"\x00\x00"
            b"\x00\x02"
            b"\x00\x01"
        )
        r = BinaryReader(data)
        gdef = GdefTable.from_reader(r, len(data))

        assert gdef.get_glyph_class(0) == 1
        assert gdef.get_glyph_class(1) == 1
        assert gdef.get_glyph_class(2) == 1
        assert gdef.get_glyph_class(3) == 0

    def test_parse_gdef_with_ligature_carets_format_1(self):
        """Test GDEF with ligature carets format 1 (design units)."""
        # GDEF table structure:
        # - uint32: version (1.0)
        # - uint16: glyph_class_def_offset (0)
        # - uint16: attachment_point_list_offset (0)
        # - uint16: ligature_caret_list_offset (12)
        # - uint16: mark_attachment_class_def_offset (0)
        # Then at offset 12 (after header), the ligature caret list:
        # - uint16: caret count (2)
        # - uint16[2]: offsets to caret values (6 and 10 relative to this table)
        # Then at offset 18 (12+6), the first CaretValue:
        # - uint16: format (1)
        # - uint16: value (50)
        # Then at offset 22 (12+10), the second CaretValue:
        # - uint16: format (1)
        # - uint16: value (100)
        data = (
            b"\x00\x01\x00\x00"  # version 1.0 (4 bytes)
            b"\x00\x00"           # glyph_class_def_offset = 0 (2 bytes)
            b"\x00\x00"           # attachment_point_list_offset = 0 (2 bytes)
            b"\x00\x0C"           # ligature_caret_list_offset = 12 (2 bytes)
            b"\x00\x00"           # mark_attachment_class_def_offset = 0 (2 bytes)
            # Ligature caret list at offset 12
            b"\x00\x02"           # caret count = 2 (2 bytes)
            b"\x00\x06\x00\x0A"   # offsets to caret values (6 and 10)
            # First CaretValue at offset 18 (12+6)
            b"\x00\x01\x00\x32"  # format=1, value=50 (4 bytes)
            # Second CaretValue at offset 22 (12+10)
            b"\x00\x01\x00\x64"  # format=1, value=100 (4 bytes)
        )
        r = BinaryReader(data)
        gdef = GdefTable.from_reader(r, len(data))

        carets = gdef.get_ligature_carets(0)
        assert carets == [50]

        carets = gdef.get_ligature_carets(1)
        assert carets == [100]

    def test_parse_gdef_with_mark_attachment_class(self):
        """Test GDEF with mark attachment class definition (format 2)."""
        # GDEF table structure:
        # - uint32: version (1.0)
        # - uint16: glyph_class_def_offset (0)
        # - uint16: attachment_point_list_offset (0)
        # - uint16: ligature_caret_list_offset (0)
        # - uint16: mark_attachment_class_def_offset (16)
        # Then at offset 16, the mark attachment class definition:
        # - uint16: format (2)
        # - uint16: range count (1)
        # - uint16[3]: range record (start=0, end=1, class=2)
        data = (
            b"\x00\x01\x00\x00"  # version 1.0
            b"\x00\x00"           # glyph_class_def_offset = 0
            b"\x00\x00"           # attachment_point_list_offset = 0
            b"\x00\x00"           # ligature_caret_list_offset = 0
            b"\x00\x10"           # mark_attachment_class_def_offset = 16
            # Padding to reach offset 16 (4 bytes of padding)
            b"\x00\x00\x00\x00"
            # Mark attachment class definition at offset 16
            b"\x00\x02"           # format = 2
            b"\x00\x01"           # range count = 1
            b"\x00\x00\x00\x01\x00\x02"  # range record: start=0, end=1, class=2
        )
        r = BinaryReader(data)
        gdef = GdefTable.from_reader(r, len(data))

        assert gdef.get_mark_attachment_class(0) == 2
        assert gdef.get_mark_attachment_class(1) == 2
        assert gdef.get_mark_attachment_class(2) == 0

    def test_get_glyph_class_returns_unassigned_for_missing(self):
        """Test that get_glyph_class returns 0 for unassigned glyphs."""
        data = (
            b"\x00\x01\x00\x00"
            b"\x00\x00"
            b"\x00\x00"
            b"\x00\x00"
            b"\x00\x00"
        )
        r = BinaryReader(data)
        gdef = GdefTable.from_reader(r, len(data))

        assert gdef.get_glyph_class(0) == 0
        assert gdef.get_glyph_class(100) == 0

    def test_get_ligature_carets_empty_when_no_list(self):
        """Test that get_ligature_carets returns empty list when no list defined."""
        data = (
            b"\x00\x01\x00\x00"
            b"\x00\x00"
            b"\x00\x00"
            b"\x00\x00"
            b"\x00\x00"
        )
        r = BinaryReader(data)
        gdef = GdefTable.from_reader(r, len(data))

        assert gdef.get_ligature_carets(0) == []
        assert gdef.get_ligature_carets(99) == []

    def test_get_mark_attachment_class_empty_when_no_def(self):
        """Test that get_mark_attachment_class returns 0 when no definition."""
        data = (
            b"\x00\x01\x00\x00"
            b"\x00\x00"
            b"\x00\x00"
            b"\x00\x00"
            b"\x00\x00"
        )
        r = BinaryReader(data)
        gdef = GdefTable.from_reader(r, len(data))

        assert gdef.get_mark_attachment_class(0) == 0
        assert gdef.get_mark_attachment_class(100) == 0


class TestAttachmentPointList:
    """Test attachment point list parsing."""

    def test_parse_attachment_point_list_empty(self):
        """Test parsing empty attachment point list."""
        from aspose_font.ttf.tables.gdef import _parse_attachment_point_list

        data = b"\x00\x00"
        attachment_list = _parse_attachment_point_list(BinaryReader(data), 0, data)

        assert attachment_list.attachment_point_count == 0
        assert attachment_list.attachment_points == []

    def test_parse_attachment_point_list_with_points(self):
        """Test parsing attachment point list with attachment points."""
        from aspose_font.ttf.tables.gdef import _parse_attachment_point_list

        data = (
            b"\x00\x02"
            b"\x00\x05\x00\x02\x00\x01\x00\x02"
            b"\x00\x08\x00\x03\x00\x01\x00\x02\x00\x03"
        )
        attachment_list = _parse_attachment_point_list(BinaryReader(data), 0, data)

        assert attachment_list.attachment_point_count == 2
        assert len(attachment_list.attachment_points) == 2
        assert attachment_list.attachment_points[0] == (5, [1, 2])
        assert attachment_list.attachment_points[1] == (8, [1, 2, 3])


class TestGdefTableMethods:
    """Test GdefTable public methods."""

    def test_get_attachment_points_no_list(self):
        """Test get_attachment_points returns empty list when no list defined."""
        from aspose_font.ttf.tables.gdef import GdefTable

        gdef = GdefTable(
            version=0x00010000,
            glyph_class_def_offset=0,
            attachment_point_list_offset=0,
            ligature_caret_list_offset=0,
            mark_attachment_class_def_offset=0,
        )

        assert gdef.get_attachment_points(0) == []
        assert gdef.get_attachment_points(99) == []

    def test_get_attachment_points_with_list(self):
        """Test get_attachment_points returns points for a glyph."""
        data = (
            b"\x00\x01\x00\x00"
            b"\x00\x00"
            b"\x00\x0C"
            b"\x00\x00"
            b"\x00\x00"
            b"\x00\x02"
            b"\x00\x05\x00\x02\x00\x01\x00\x02"
            b"\x00\x08\x00\x03\x00\x01\x00\x02\x00\x03"
        )
        r = BinaryReader(data)
        gdef = GdefTable.from_reader(r, len(data))

        assert gdef.get_attachment_points(5) == [1, 2]
        assert gdef.get_attachment_points(8) == [1, 2, 3]
        assert gdef.get_attachment_points(99) == []

    def test_get_ligature_carets_with_caret_count_zero(self):
        """Test get_ligature_carets returns empty for glyphs beyond caret_values."""
        data = (
            b"\x00\x01\x00\x00"
            b"\x00\x00"
            b"\x00\x00"
            b"\x00\x0C"
            b"\x00\x00"
            b"\x00\x02"
            b"\x00\x06\x00\x0A"
            b"\x00\x01\x00\x32"
            b"\x00\x01\x00\x64"
        )
        r = BinaryReader(data)
        gdef = GdefTable.from_reader(r, len(data))

        assert gdef.get_ligature_carets(0) == [50]
        assert gdef.get_ligature_carets(1) == [100]
        assert gdef.get_ligature_carets(99) == []

    def test_get_ligature_carets_negative_index(self):
        """Test get_ligature_carets handles negative glyph_id."""
        data = (
            b"\x00\x01\x00\x00"
            b"\x00\x00"
            b"\x00\x00"
            b"\x00\x0C"
            b"\x00\x00"
            b"\x00\x01"
            b"\x00\x06"
            b"\x00\x01\x00\x32"
        )
        r = BinaryReader(data)
        gdef = GdefTable.from_reader(r, len(data))

        assert gdef.get_ligature_carets(-1) == []


class TestGdefIntegration:
    """Integration tests with real font fixtures."""

    def test_gdef_parsed_on_font_with_gdef(self, testdata_dir: Path) -> None:
        """Test that font with GDEF parses it correctly."""
        from aspose_font import FontLoader
        font_path = testdata_dir / "Roboto-VariableFont_wdth,wght.ttf"
        font = FontLoader.open(str(font_path))
        assert isinstance(font, TtfFont)
        gdef = font.ttf_tables.gdef
        assert gdef is not None
        assert gdef.version in (0x00010000, 0x00010002, 0x00010003)
        assert gdef.glyph_class_def is not None
        assert gdef.get_glyph_class(37) == 1
