"""OpenType SVG table parser for color glyph rendering support."""

from __future__ import annotations

import gzip
from dataclasses import dataclass

from aspose_font._exceptions import FontParseException
from aspose_font._io import BinaryReader


@dataclass(slots=True)
class SVGDocumentRecord:
    """Represents a single SVG document entry in the SVG table document list."""
    start_glyph_id: int
    end_glyph_id: int
    svg_doc_offset: int
    svg_doc_length: int
    svg_doc_format: int


@dataclass
class SVGTable:
    """OpenType SVG table containing SVG documents for color glyphs."""
    version: int
    svg_document_list: list[SVGDocumentRecord]
    _raw: bytes
    _document_list_start: int

    def get_svg(self, glyph_id: int) -> str | None:
        """Retrieve SVG XML string for given glyph_id, or None if not covered."""
        for record in self.svg_document_list:
            if record.start_glyph_id <= glyph_id <= record.end_glyph_id:
                return self._extract_svg(record)
        return None

    def _extract_svg(self, record: SVGDocumentRecord) -> str:
        """Extract and decompress SVG data for a document record."""
        svg_start = self._document_list_start + record.svg_doc_offset
        svg_end = svg_start + record.svg_doc_length
        svg_data = self._raw[svg_start:svg_end]

        if record.svg_doc_format == 1:
            # Gzip compressed
            svg_data = gzip.decompress(svg_data)

        return svg_data.decode("utf-8")

    @classmethod
    def from_reader(cls, r: BinaryReader, length: int) -> "SVGTable":
        """Parse SVG table from binary reader."""
        raw = r.read_bytes(length)
        rr = BinaryReader(raw)

        version = rr.read_u16()
        offset_to_svg_document_list = rr.read_u32()
        _reserved = rr.read_u32()

        if version not in (0, 1):
            raise FontParseException(
                f"Unsupported SVG table version {version}",
                format_name="TTF"
            )

        document_list_start = offset_to_svg_document_list
        rr.seek(document_list_start)

        num_entries = rr.read_u16()
        svg_document_list = []
        for _ in range(num_entries):
            start_glyph_id = rr.read_u16()
            end_glyph_id = rr.read_u16()
            svg_doc_offset = rr.read_u32()
            svg_doc_length = rr.read_u32()
            svg_doc_format = rr.read_u32()

            svg_document_list.append(SVGDocumentRecord(
                start_glyph_id=start_glyph_id,
                end_glyph_id=end_glyph_id,
                svg_doc_offset=svg_doc_offset,
                svg_doc_length=svg_doc_length,
                svg_doc_format=svg_doc_format
            ))

        return cls(
            version=version,
            svg_document_list=svg_document_list,
            _raw=raw,
            _document_list_start=document_list_start
        )

    def to_bytes(self) -> bytes:
        """Serialize SVG table to binary."""
        raise NotImplementedError("SVGTable serialization not yet implemented")
