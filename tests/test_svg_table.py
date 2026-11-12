"""Tests for OpenType SVG table parser (FONT-453)."""

from __future__ import annotations

import gzip
from io import BytesIO

from aspose_font._io import BinaryReader
from aspose_font.ttf.tables.svg import SVGDocumentRecord, SVGTable


class TestSVGDocumentRecordDataclass:
    """Tests for SVGDocumentRecord dataclass structure."""

    def test_svg_document_record_dataclass_structure(self):
        """Test that SVGDocumentRecord has correct fields and defaults."""
        record = SVGDocumentRecord(
            start_glyph_id=5,
            end_glyph_id=10,
            svg_doc_offset=256,
            svg_doc_length=512,
            svg_doc_format=2,
        )
        assert record.start_glyph_id == 5
        assert record.end_glyph_id == 10
        assert record.svg_doc_offset == 256
        assert record.svg_doc_length == 512
        assert record.svg_doc_format == 2

    def test_svg_document_record_slots(self):
        """Test that SVGDocumentRecord uses __slots__ for memory efficiency."""
        record = SVGDocumentRecord(
            start_glyph_id=1,
            end_glyph_id=1,
            svg_doc_offset=0,
            svg_doc_length=100,
            svg_doc_format=2,
        )
        assert not hasattr(record, "__dict__")


class TestSVGTableParsing:
    """Tests for SVG table binary parsing."""

    def test_parse_empty_svg_table(self, tmp_path):
        """Test parsing SVG table with zero documents."""
        svg_xml = b'<?xml version="1.0" encoding="UTF-8"?><svg></svg>'

        stream = BytesIO()
        stream.write(b"\x00\x01")
        stream.write(b"\x00\x00\x00\x0A")  # offset to document list = 10
        stream.write(b"\x00\x00\x00\x00")  # reserved
        stream.write(b"\x00\x00")  # numEntries = 0
        stream.write(svg_xml)

        rr = BinaryReader(stream.getvalue())
        table = SVGTable.from_reader(rr, len(stream.getvalue()))

        assert table.version == 1
        assert table.svg_document_list == []

    def test_parse_single_document_svg_table(self, tmp_path):
        """Test parsing SVG table with a single document record."""
        svg_xml = b'<?xml version="1.0" encoding="UTF-8"?><svg></svg>'

        stream = BytesIO()
        stream.write(b"\x00\x01")
        stream.write(b"\x00\x00\x00\x0A")  # offset to document list = 10
        stream.write(b"\x00\x00\x00\x00")  # reserved
        stream.write(b"\x00\x01")  # numEntries = 1

        # Document list starts at offset 10 from table start
        # numEntries (2 bytes) at position 10-11
        # First record at position 12-27 (16 bytes)
        # SVG data starts at position 28
        # offset from document list start = 28 - 10 = 18
        stream.write(b"\x00\x05")
        stream.write(b"\x00\x05")
        stream.write(b"\x00\x00\x00\x12")  # offset from document list start = 18
        stream.write(len(svg_xml).to_bytes(4, byteorder="big"))
        stream.write(b"\x00\x00\x00\x02")

        stream.write(svg_xml)

        rr = BinaryReader(stream.getvalue())
        table = SVGTable.from_reader(rr, len(stream.getvalue()))

        assert table.version == 1
        assert len(table.svg_document_list) == 1
        record = table.svg_document_list[0]
        assert record.start_glyph_id == 5
        assert record.end_glyph_id == 5
        assert record.svg_doc_offset == 18
        assert record.svg_doc_length == len(svg_xml)
        assert record.svg_doc_format == 2

    def test_parse_multiple_document_svg_table(self, tmp_path):
        """Test parsing SVG table with multiple document records."""
        svg1 = b'<?xml version="1.0"?><svg id="glyph1"></svg>'
        svg2 = b'<?xml version="1.0"?><svg id="glyph2"></svg>'
        svg3 = b'<?xml version="1.0"?><svg id="glyph3"></svg>'

        total_svg = svg1 + svg2 + svg3

        stream = BytesIO()
        stream.write(b"\x00\x01")
        stream.write(b"\x00\x00\x00\x0A")  # offset to document list = 10
        stream.write(b"\x00\x00\x00\x00")  # reserved
        stream.write(b"\x00\x03")  # numEntries = 3

        # Document list starts at position 10
        # numEntries at position 10-11
        # Record 1 at position 12-27
        # Record 2 at position 28-43
        # Record 3 at position 44-59
        # SVG 1 at position 60-(60+len(svg1)-1)
        # SVG 2 at position (60+len(svg1))-(60+len(svg1)+len(svg2)-1)
        # SVG 3 at position (60+len(svg1)+len(svg2))-(60+len(svg1)+len(svg2)+len(svg3)-1)

        svg1_start = 60
        svg2_start = 60 + len(svg1)
        svg3_start = 60 + len(svg1) + len(svg2)

        # Record 1: glyph IDs 1-3
        stream.write(b"\x00\x01")
        stream.write(b"\x00\x03")
        stream.write((svg1_start - 10).to_bytes(4, byteorder="big"))  # offset from document list start
        stream.write(len(svg1).to_bytes(4, byteorder="big"))
        stream.write(b"\x00\x00\x00\x02")

        # Record 2: glyph IDs 5-7
        stream.write(b"\x00\x05")
        stream.write(b"\x00\x07")
        stream.write((svg2_start - 10).to_bytes(4, byteorder="big"))  # offset from document list start
        stream.write(len(svg2).to_bytes(4, byteorder="big"))
        stream.write(b"\x00\x00\x00\x02")

        # Record 3: glyph IDs 10-12
        stream.write(b"\x00\x0A")
        stream.write(b"\x00\x0C")
        stream.write((svg3_start - 10).to_bytes(4, byteorder="big"))  # offset from document list start
        stream.write(len(svg3).to_bytes(4, byteorder="big"))
        stream.write(b"\x00\x00\x00\x02")

        stream.write(total_svg)

        rr = BinaryReader(stream.getvalue())
        table = SVGTable.from_reader(rr, len(stream.getvalue()))

        assert table.version == 1
        assert len(table.svg_document_list) == 3

        r1, r2, r3 = table.svg_document_list
        assert r1.start_glyph_id == 1
        assert r1.end_glyph_id == 3
        assert r2.start_glyph_id == 5
        assert r2.end_glyph_id == 7
        assert r3.start_glyph_id == 10
        assert r3.end_glyph_id == 12

    def test_parse_svg_table_with_gzip_compressed(self, tmp_path):
        """Test parsing SVG table with gzip-compressed SVG format (format 1)."""
        uncompressed = b'<?xml version="1.0"?><svg id="test"></svg>'
        compressed = gzip.compress(uncompressed)

        stream = BytesIO()
        stream.write(b"\x00\x01")
        stream.write(b"\x00\x00\x00\x0A")  # offset to document list = 10
        stream.write(b"\x00\x00\x00\x00")  # reserved
        stream.write(b"\x00\x01")  # numEntries = 1
        stream.write(b"\x00\x05")
        stream.write(b"\x00\x05")
        stream.write(b"\x00\x00\x00\x12")  # offset from document list start = 18
        stream.write(len(compressed).to_bytes(4, byteorder="big"))
        stream.write(b"\x00\x00\x00\x01")
        stream.write(compressed)

        rr = BinaryReader(stream.getvalue())
        table = SVGTable.from_reader(rr, len(stream.getvalue()))

        assert table.version == 1
        assert len(table.svg_document_list) == 1
        record = table.svg_document_list[0]
        assert record.svg_doc_format == 1

    def test_svg_table_header_version_0(self, tmp_path):
        """Test that version 0 SVG table is accepted."""
        stream = BytesIO()
        stream.write(b"\x00\x00")
        stream.write(b"\x00\x00\x00\x0A")  # offset to document list = 10
        stream.write(b"\x00\x00\x00\x00")  # reserved
        stream.write(b"\x00\x00")  # numEntries = 0

        rr = BinaryReader(stream.getvalue())
        table = SVGTable.from_reader(rr, len(stream.getvalue()))

        assert table.version == 0


class TestSVGDocumentRetrieval:
    """Tests for SVG document retrieval via get_svg()."""

    def test_get_svg_returns_none_for_uncovered_glyph(self, tmp_path):
        """Test that get_svg returns None for glyph IDs outside all ranges."""
        svg_xml = b'<?xml version="1.0"?><svg id="glyph1"></svg>'

        stream = BytesIO()
        stream.write(b"\x00\x01")
        stream.write(b"\x00\x00\x00\x0A")  # offset to document list = 10
        stream.write(b"\x00\x00\x00\x00")  # reserved
        stream.write(b"\x00\x01")  # numEntries = 1
        stream.write(b"\x00\x05")
        stream.write(b"\x00\x05")
        stream.write(b"\x00\x00\x00\x12")  # offset from document list start = 18
        stream.write(len(svg_xml).to_bytes(4, byteorder="big"))
        stream.write(b"\x00\x00\x00\x02")
        stream.write(svg_xml)

        rr = BinaryReader(stream.getvalue())
        table = SVGTable.from_reader(rr, len(stream.getvalue()))

        assert table.get_svg(4) is None
        assert table.get_svg(6) is None
        assert table.get_svg(100) is None

    def test_get_svg_returns_svg_for_single_document(self, tmp_path):
        """Test that get_svg returns SVG XML for covered glyph IDs."""
        svg_xml = b'<?xml version="1.0"?><svg id="glyph5"></svg>'

        stream = BytesIO()
        stream.write(b"\x00\x01")
        stream.write(b"\x00\x00\x00\x0A")  # offset to document list = 10
        stream.write(b"\x00\x00\x00\x00")  # reserved
        stream.write(b"\x00\x01")  # numEntries = 1
        stream.write(b"\x00\x05")
        stream.write(b"\x00\x05")
        stream.write(b"\x00\x00\x00\x12")  # offset from document list start = 18
        stream.write(len(svg_xml).to_bytes(4, byteorder="big"))
        stream.write(b"\x00\x00\x00\x02")
        stream.write(svg_xml)

        rr = BinaryReader(stream.getvalue())
        table = SVGTable.from_reader(rr, len(stream.getvalue()))

        result = table.get_svg(5)
        assert result is not None
        assert "<?xml" in result
        assert '<svg id="glyph5">' in result

    def test_get_svg_returns_none_when_no_documents(self, tmp_path):
        """Test that get_svg returns None for tables with no document records."""
        stream = BytesIO()
        stream.write(b"\x00\x01")
        stream.write(b"\x00\x00\x00\x0A")  # offset to document list = 10
        stream.write(b"\x00\x00\x00\x00")  # reserved
        stream.write(b"\x00\x00")  # numEntries = 0

        rr = BinaryReader(stream.getvalue())
        table = SVGTable.from_reader(rr, len(stream.getvalue()))

        assert table.get_svg(0) is None
        assert table.get_svg(100) is None

    def test_get_svg_handles_noncontiguous_ranges(self, tmp_path):
        """Test that get_svg correctly handles non-contiguous glyph ID ranges."""
        svg1 = b'<?xml version="1.0"?><svg id="glyph1"></svg>'
        svg2 = b'<?xml version="1.0"?><svg id="glyph10"></svg>'

        stream = BytesIO()
        stream.write(b"\x00\x01")
        stream.write(b"\x00\x00\x00\x0A")  # offset to document list = 10
        stream.write(b"\x00\x00\x00\x00")  # reserved
        stream.write(b"\x00\x02")  # numEntries = 2

        # numEntries at position 10-11
        # Record 1 at position 12-27
        # Record 2 at position 28-43
        # SVG1 at position 44-44+len(svg1)-1 = 44-87
        # SVG2 at position 88-88+len(svg2)-1 = 88-132

        # Record 1: glyph 1, offset from doc list = 44 - 10 = 34
        stream.write(b"\x00\x01")
        stream.write(b"\x00\x01")
        stream.write(b"\x00\x00\x00\x22")  # offset from document list start = 34
        stream.write(len(svg1).to_bytes(4, byteorder="big"))
        stream.write(b"\x00\x00\x00\x02")

        # Record 2: glyph 10, offset from doc list = 88 - 10 = 78
        stream.write(b"\x00\x0A")
        stream.write(b"\x00\x0A")
        stream.write(b"\x00\x00\x00\x4E")  # offset from document list start = 78
        stream.write(len(svg2).to_bytes(4, byteorder="big"))
        stream.write(b"\x00\x00\x00\x02")

        stream.write(svg1 + svg2)

        rr = BinaryReader(stream.getvalue())
        table = SVGTable.from_reader(rr, len(stream.getvalue()))

        assert table.get_svg(1) is not None
        assert 'id="glyph1"' in table.get_svg(1)
        assert table.get_svg(5) is None
        assert table.get_svg(10) is not None
        assert 'id="glyph10"' in table.get_svg(10)


class TestSVGDocumentFormats:
    """Tests for different SVG document formats."""

    def test_get_svg_uncompressed_format(self, tmp_path):
        """Test SVG retrieval for uncompressed format (format 2)."""
        svg_xml = b'<?xml version="1.0"?><svg id="test"></svg>'

        stream = BytesIO()
        stream.write(b"\x00\x01")
        stream.write(b"\x00\x00\x00\x0A")  # offset to document list = 10
        stream.write(b"\x00\x00\x00\x00")  # reserved
        stream.write(b"\x00\x01")  # numEntries = 1
        stream.write(b"\x00\x05")
        stream.write(b"\x00\x05")
        stream.write(b"\x00\x00\x00\x12")  # offset from document list start = 18
        stream.write(len(svg_xml).to_bytes(4, byteorder="big"))
        stream.write(b"\x00\x00\x00\x02")
        stream.write(svg_xml)

        rr = BinaryReader(stream.getvalue())
        table = SVGTable.from_reader(rr, len(stream.getvalue()))

        result = table.get_svg(5)
        assert result is not None
        assert isinstance(result, str)
        assert svg_xml.decode("utf-8") == result

    def test_get_svg_gzip_compressed_format(self, tmp_path):
        """Test SVG retrieval for gzip-compressed format (format 1)."""
        uncompressed = b'<?xml version="1.0"?><svg id="compressed"></svg>'
        compressed = gzip.compress(uncompressed)

        stream = BytesIO()
        stream.write(b"\x00\x01")
        stream.write(b"\x00\x00\x00\x0A")  # offset to document list = 10
        stream.write(b"\x00\x00\x00\x00")  # reserved
        stream.write(b"\x00\x01")  # numEntries = 1
        stream.write(b"\x00\x05")
        stream.write(b"\x00\x05")
        stream.write(b"\x00\x00\x00\x12")  # offset from document list start = 18
        stream.write(len(compressed).to_bytes(4, byteorder="big"))
        stream.write(b"\x00\x00\x00\x01")
        stream.write(compressed)

        rr = BinaryReader(stream.getvalue())
        table = SVGTable.from_reader(rr, len(stream.getvalue()))

        result = table.get_svg(5)
        assert result is not None
        assert isinstance(result, str)
        assert uncompressed.decode("utf-8") == result
