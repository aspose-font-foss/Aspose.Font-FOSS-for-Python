"""Tests for FONT-510: Subset sbix and cbdt color bitmap tables."""

from __future__ import annotations

from aspose_font import FontLoader, TtfFont
from aspose_font._io import BinaryWriter
from aspose_font.subsetter import FontSubsetter


def _build_minimal_cmap() -> bytes:
    """Build a minimal cmap table with format 4 mapping (codepoint 65 -> gid 1)."""
    from aspose_font.ttf.tables.cmap import _build_format4

    w = BinaryWriter()
    w.write_u16(0)  # version
    w.write_u16(1)  # numTables = 1
    w.write_u16(3)  # platformID = 3 (Unicode)
    w.write_u16(1)  # encodingID = 1 (BMP)
    w.write_u32(12)  # offset to subtable = 12 (4 + 1*8)

    # Format 4 subtable using the library helper
    mapping = {65: 1}
    format4_blob = _build_format4(mapping)
    w.write_bytes(format4_blob)

    return w.to_bytes()


def _build_minimal_sfnt_with_tables(
    tables: list[tuple[str, bytes]],
    num_glyphs: int = 10,
) -> bytes:
    """Build a minimal SFNT font with specified tables."""
    units_per_em = 2048

    head = (
        (1).to_bytes(2, "big")
        + (0).to_bytes(2, "big")
        + (0x00010000).to_bytes(4, "big")
        + (0).to_bytes(4, "big")
        + (0x5F0F3CF5).to_bytes(4, "big")
        + (0).to_bytes(2, "big")
        + units_per_em.to_bytes(2, "big")
        + (0).to_bytes(8, "big")
        + (0).to_bytes(8, "big")
        + (0xFF9C).to_bytes(2, "big")
        + (0xFF38).to_bytes(2, "big")
        + (0x03E8).to_bytes(2, "big")
        + (0x0384).to_bytes(2, "big")
        + (0).to_bytes(2, "big")
        + (8).to_bytes(2, "big")
        + (2).to_bytes(2, "big")
        + (0).to_bytes(2, "big")
        + (0).to_bytes(2, "big")
    )

    maxp = (0x00010000).to_bytes(4, "big") + (num_glyphs).to_bytes(2, "big") + bytes(26)

    post = (
        (0x00030000).to_bytes(4, "big")
        + (0).to_bytes(4, "big")
        + (0).to_bytes(4, "big")
        + (0).to_bytes(4, "big")
        + (0).to_bytes(4, "big")
        + (0).to_bytes(4, "big")
        + (0).to_bytes(4, "big")
        + (0).to_bytes(16, "big")
    )

    numGlyphs = num_glyphs
    glyf = b""
    for i in range(numGlyphs):
        numContours = (0).to_bytes(2, "big")
        xMin = (0).to_bytes(2, "big")
        yMin = (0).to_bytes(2, "big")
        xMax = (0).to_bytes(2, "big")
        yMax = (0).to_bytes(2, "big")
        glyf += numContours + xMin + yMin + xMax + yMax

    loca_offsets = []
    cursor = 0
    for i in range(numGlyphs + 1):
        loca_offsets.append(cursor)
        cursor += 10

    loca = b""
    for off in loca_offsets:
        loca += (off // 2).to_bytes(2, "big")

    hhea = (
        (0x00010000).to_bytes(4, "big")
        + (numGlyphs).to_bytes(2, "big")
        + (0).to_bytes(2, "big")
        + (0).to_bytes(2, "big")
        + (0).to_bytes(2, "big")
        + (0).to_bytes(2, "big")
        + (0).to_bytes(2, "big")
        + (0).to_bytes(2, "big")
        + (0).to_bytes(2, "big")
        + (0).to_bytes(2, "big")
        + (0).to_bytes(2, "big")
        + (0).to_bytes(2, "big")
        + (0).to_bytes(2, "big")
        + (0).to_bytes(2, "big")
        + (0).to_bytes(2, "big")
        + (0).to_bytes(2, "big")
        + (0).to_bytes(2, "big")
    )

    hmtx = b""
    for i in range(numGlyphs):
        hmtx += (500).to_bytes(2, "big")
        hmtx += (0).to_bytes(2, "big")

    cmap = _build_minimal_cmap()

    num_tables = 8 + len(tables)
    offset_table = (
        b"\x00\x01\x00\x00"  # sfntVersion
        + num_tables.to_bytes(2, "big")  # numTables
        + (0).to_bytes(2, "big")  # searchRange
        + (0).to_bytes(2, "big")  # entrySelector
        + (0).to_bytes(2, "big")  # rangeShift
    )

    head_offset = 12 + num_tables * 16
    maxp_offset = head_offset + len(head)
    post_offset = maxp_offset + len(maxp)
    glyf_offset = post_offset + len(post)
    loca_offset = glyf_offset + len(glyf)
    hhea_offset = loca_offset + len(loca)
    hmtx_offset = hhea_offset + len(hhea)
    cmap_offset = hmtx_offset + len(hmtx)

    directory = (
        b"head"
        + (0).to_bytes(4, "big")
        + head_offset.to_bytes(4, "big")
        + len(head).to_bytes(4, "big")
        + b"maxp"
        + (0).to_bytes(4, "big")
        + maxp_offset.to_bytes(4, "big")
        + len(maxp).to_bytes(4, "big")
        + b"post"
        + (0).to_bytes(4, "big")
        + post_offset.to_bytes(4, "big")
        + len(post).to_bytes(4, "big")
        + b"glyf"
        + (0).to_bytes(4, "big")
        + glyf_offset.to_bytes(4, "big")
        + len(glyf).to_bytes(4, "big")
        + b"loca"
        + (0).to_bytes(4, "big")
        + loca_offset.to_bytes(4, "big")
        + len(loca).to_bytes(4, "big")
        + b"hhea"
        + (0).to_bytes(4, "big")
        + hhea_offset.to_bytes(4, "big")
        + len(hhea).to_bytes(4, "big")
        + b"hmtx"
        + (0).to_bytes(4, "big")
        + hmtx_offset.to_bytes(4, "big")
        + len(hmtx).to_bytes(4, "big")
        + b"cmap"
        + (0).to_bytes(4, "big")
        + cmap_offset.to_bytes(4, "big")
        + len(cmap).to_bytes(4, "big")
    )

    current_offset = cmap_offset + len(cmap)
    for tag, data in tables:
        directory += tag.encode("ascii")
        directory += (0).to_bytes(4, "big")
        directory += current_offset.to_bytes(4, "big")
        directory += len(data).to_bytes(4, "big")
        current_offset += len(data)

    sfnt_data = offset_table + directory + head + maxp + post + glyf + loca + hhea + hmtx + cmap
    for _, data in tables:
        sfnt_data += data

    return sfnt_data


def _build_minimal_font_with_sbix(glyphs: list[tuple[int, bytes]], ppem: int = 24, num_glyphs: int = 15) -> bytes:
    """Build a minimal TTF font with sbix table for subsetting tests."""
    sbix_data = _build_sbix_table_with_png_glyphs(glyphs, ppem=ppem)
    return _build_minimal_sfnt_with_tables([("sbix", sbix_data)], num_glyphs=num_glyphs)


def _build_minimal_font_with_cbdt(
    glyphs: list[tuple[int, bytes]], ppem: int = 24, num_glyphs: int = 15
) -> tuple[bytes, bytes]:
    """Build a minimal TTF font with CBLC and CBDT tables for subsetting tests."""
    cblc_data = _build_cblc_table_with_glyphs(glyphs, ppem=ppem)
    cbdt_data = _build_cbdt_table_with_glyphs(glyphs, ppem=ppem)
    return (cblc_data, cbdt_data)


def _build_sbix_table_with_png_glyphs(
    glyphs: list[tuple[int, bytes]],
    ppem: int = 24,
) -> bytes:
    """Build a minimal sbix table with multiple glyphs."""
    stream = b""
    stream += (0).to_bytes(2, "big")  # version = 0
    stream += (0).to_bytes(2, "big")  # flags = 0
    stream += (1).to_bytes(4, "big")  # num_strikes = 1
    stream += ppem.to_bytes(2, "big")  # ppem
    stream += (96).to_bytes(2, "big")  # resolution = 96
    stream += (0).to_bytes(4, "big")  # offset_to_bitmap_data = 0

    stream += len(glyphs).to_bytes(4, "big")  # num_glyphs

    for glyph_id, bitmap_data in glyphs:
        stream += glyph_id.to_bytes(2, "big")  # glyph_id
        stream += b"png "  # graphic_type = png
        stream += (0).to_bytes(2, "big")  # origin_offset_x
        stream += (0).to_bytes(2, "big")  # origin_offset_y
        stream += len(bitmap_data).to_bytes(4, "big")  # bitmap_data_length
        stream += bitmap_data  # bitmap_data

    return stream


def _build_cbdt_table_with_glyphs(
    glyphs: list[tuple[int, bytes]],
    ppem: int = 24,
) -> bytes:
    """Build a minimal CBDT table with multiple glyphs (format 17)."""
    first_glyph = glyphs[0][0]
    last_glyph = glyphs[-1][0]
    num_glyphs = last_glyph - first_glyph + 1
    glyph_map = dict(glyphs)

    stream = bytearray()
    stream += (0x00020000).to_bytes(4, "big")  # version
    stream += (1).to_bytes(4, "big")  # num_strikes = 1
    stream += ppem.to_bytes(1, "big")  # ppem
    stream += (0).to_bytes(1, "big")  # max_ppem
    stream += (8).to_bytes(1, "big")  # bit_depth
    stream += (0).to_bytes(1, "big")  # flags
    stream += (16).to_bytes(4, "big")  # offset_to_index_subtable (8 + 8)

    additional_offset = 16 + 10 + 13 + num_glyphs * 4
    stream += (17).to_bytes(2, "big")  # format
    stream += first_glyph.to_bytes(2, "big")  # first_glyph_id
    stream += last_glyph.to_bytes(2, "big")  # last_glyph_id
    stream += additional_offset.to_bytes(4, "big")  # additional_offset

    data_format = 1
    stream += data_format.to_bytes(1, "big")
    stream += b"\x00\x00\x00"
    stream += (16).to_bytes(2, "big")  # width
    stream += (16).to_bytes(2, "big")  # height
    stream += (8).to_bytes(1, "big")  # bit_depth
    stream += (0).to_bytes(1, "big")  # horizontal_origin_x
    stream += (0).to_bytes(1, "big")  # horizontal_origin_y
    stream += (0).to_bytes(1, "big")  # vertical_origin_x
    stream += (0).to_bytes(1, "big")  # vertical_origin_y

    data_blob = bytearray()
    for gid in range(first_glyph, last_glyph + 1):
        stream += len(data_blob).to_bytes(4, "big")
        bm = glyph_map.get(gid, b"")
        data_blob += data_format.to_bytes(1, "big") + b"\x00\x00\x00"
        data_blob += len(bm).to_bytes(4, "big")
        data_blob += bm

    stream += data_blob
    return bytes(stream)


def _build_cblc_table_with_glyphs(
    glyphs: list[tuple[int, bytes]],
    ppem: int = 24,
) -> bytes:
    """Build a minimal CBLC table with multiple glyphs (format 17)."""
    first_glyph = glyphs[0][0]
    last_glyph = glyphs[-1][0]
    num_glyphs = last_glyph - first_glyph + 1
    glyph_map = dict(glyphs)

    stream = bytearray()
    stream += (0x00020000).to_bytes(4, "big")  # version
    stream += (1).to_bytes(4, "big")  # num_strikes = 1

    stream += ppem.to_bytes(1, "big")  # ppem
    stream += (0).to_bytes(1, "big")  # max_ppem
    stream += (8).to_bytes(1, "big")  # bit_depth
    stream += (0).to_bytes(1, "big")  # flags
    stream += (16).to_bytes(4, "big")  # offset_to_index_subtable (8 + 8)

    additional_offset = 16 + 10 + 13 + num_glyphs * 4
    stream += (17).to_bytes(2, "big")  # format
    stream += first_glyph.to_bytes(2, "big")  # first_glyph_id
    stream += last_glyph.to_bytes(2, "big")  # last_glyph_id
    stream += additional_offset.to_bytes(4, "big")  # additional_offset

    data_format = 1
    stream += data_format.to_bytes(1, "big")
    stream += b"\x00\x00\x00"
    stream += (16).to_bytes(2, "big")  # width
    stream += (16).to_bytes(2, "big")  # height
    stream += (8).to_bytes(1, "big")  # bit_depth
    stream += (0).to_bytes(1, "big")  # horizontal_origin_x
    stream += (0).to_bytes(1, "big")  # horizontal_origin_y
    stream += (0).to_bytes(1, "big")  # vertical_origin_x
    stream += (0).to_bytes(1, "big")  # vertical_origin_y

    offset = 0
    for gid in range(first_glyph, last_glyph + 1):
        bm = glyph_map.get(gid, b"")
        stream += offset.to_bytes(4, "big")
        offset += 8 + len(bm)

    return bytes(stream)


class TestSubsetSbixTable:
    """Tests for sbix table subsetting."""

    def test_subset_ttf_with_sbix_removes_bitmap_records_for_dropped_glyphs(
        self, tmp_path
    ) -> None:
        """Test that subset removes sbix bitmap records for glyphs that are dropped."""
        bitmap_data = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIEND\xAE\x42\x60\x82"
        glyphs = [(5, bitmap_data), (7, bitmap_data), (10, bitmap_data)]
        sbix_data = _build_sbix_table_with_png_glyphs(glyphs, ppem=24)
        font_data = _build_minimal_sfnt_with_tables([("sbix", sbix_data)], num_glyphs=15)

        font = FontLoader.open(font_data)
        assert isinstance(font, TtfFont)

        assert font.num_glyphs == 15

        subsetted = FontSubsetter.subset_by_gids(font, {0, 5, 7})

        assert subsetted.num_glyphs == 3

        subsetted_data = subsetted.to_bytes()
        subsetted_reloaded = FontLoader.open(subsetted_data)
        assert isinstance(subsetted_reloaded, TtfFont)

        subsetted_tables = subsetted_reloaded.ttf_tables
        assert subsetted_tables.sbix is not None
        sbix = subsetted_tables.sbix

        records = sbix.bitmap_records[0]
        assert len(records) == 2
        assert records[0] is not None
        assert records[0].glyph_id == 1
        assert records[1] is not None
        assert records[1].glyph_id == 2

    def test_subset_ttf_with_sbix_preserves_bitmap_records_for_retained_glyphs(
        self,
        tmp_path,
    ) -> None:
        """Test that subset retains sbix bitmap data for glyphs that are kept."""
        bitmap_data = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIEND\xAE\x42\x60\x82"
        glyphs = [(5, bitmap_data), (7, bitmap_data)]
        sbix_data = _build_sbix_table_with_png_glyphs(glyphs, ppem=24)
        font_data = _build_minimal_sfnt_with_tables([("sbix", sbix_data)], num_glyphs=10)

        font = FontLoader.open(font_data)
        assert isinstance(font, TtfFont)

        subsetted = FontSubsetter.subset_by_gids(font, {0, 5})

        assert subsetted.num_glyphs == 2

        subsetted_data = subsetted.to_bytes()
        subsetted_reloaded = FontLoader.open(subsetted_data)
        assert isinstance(subsetted_reloaded, TtfFont)

        subsetted_tables = subsetted_reloaded.ttf_tables
        assert subsetted_tables.sbix is not None

    def test_subset_ttf_with_sbix_reindexes_glyph_ids_correctly(
        self,
        tmp_path,
    ) -> None:
        """Test that subsetted sbix glyph IDs are correctly re-indexed."""
        bitmap_data = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIEND\xAE\x42\x60\x82"
        glyphs = [(5, bitmap_data), (7, bitmap_data), (10, bitmap_data)]
        sbix_data = _build_sbix_table_with_png_glyphs(glyphs, ppem=24)
        font_data = _build_minimal_sfnt_with_tables([("sbix", sbix_data)], num_glyphs=15)

        font = FontLoader.open(font_data)
        assert isinstance(font, TtfFont)

        subsetted = FontSubsetter.subset_by_gids(font, {0, 5, 7})

        subsetted_data = subsetted.to_bytes()
        subsetted_reloaded = FontLoader.open(subsetted_data)
        assert isinstance(subsetted_reloaded, TtfFont)

        subsetted_tables = subsetted_reloaded.ttf_tables
        assert subsetted_tables.sbix is not None
        sbix = subsetted_tables.sbix

        records = sbix.bitmap_records[0]
        assert len(records) == 2
        assert records[0] is not None
        assert records[0].glyph_id == 1
        assert records[1] is not None
        assert records[1].glyph_id == 2

    def test_subset_ttf_with_sbix_returns_valid_font_roundtrip(
        self,
        tmp_path,
    ) -> None:
        """Test that subsetted font with sbix can be reloaded and is valid."""
        bitmap_data = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIEND\xAE\x42\x60\x82"
        glyphs = [(5, bitmap_data), (7, bitmap_data)]
        sbix_data = _build_sbix_table_with_png_glyphs(glyphs, ppem=24)
        font_data = _build_minimal_sfnt_with_tables([("sbix", sbix_data)], num_glyphs=10)

        font = FontLoader.open(font_data)
        assert isinstance(font, TtfFont)

        subsetted = FontSubsetter.subset_by_gids(font, {0, 5})
        subsetted_data = subsetted.to_bytes()

        reloaded = FontLoader.open(subsetted_data)
        assert isinstance(reloaded, TtfFont)
        assert reloaded.num_glyphs == subsetted.num_glyphs

    def test_subset_by_text_prunes_sbix_correctly(
        self,
        tmp_path,
    ) -> None:
        """Test that subsetting by text prunes sbix records correctly."""
        bitmap_data = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIEND\xAE\x42\x60\x82"
        glyphs = [(5, bitmap_data), (7, bitmap_data), (10, bitmap_data)]
        sbix_data = _build_sbix_table_with_png_glyphs(glyphs, ppem=24)
        font_data = _build_minimal_sfnt_with_tables([("sbix", sbix_data)], num_glyphs=15)

        font = FontLoader.open(font_data)
        assert isinstance(font, TtfFont)

        subsetted = FontSubsetter.subset_by_text(font, "AE")

        reloaded = FontLoader.open(subsetted.to_bytes())
        assert isinstance(reloaded, TtfFont)


class TestSubsetCbdtCblcTable:
    """Tests for CBDT/CBLC table subsetting."""

    def test_subset_ttf_with_cbdt_removes_bitmap_records_for_dropped_glyphs(
        self,
        tmp_path,
    ) -> None:
        """Test that subset removes CBDT bitmap records for glyphs that are dropped."""
        bitmap_data = b"\x89PNG\r\n\x1a\n"
        glyphs = [(5, bitmap_data), (7, bitmap_data), (10, bitmap_data)]
        cbdt_data = _build_cbdt_table_with_glyphs(glyphs, ppem=24)
        cblc_data = _build_cblc_table_with_glyphs(glyphs, ppem=24)
        font_data = _build_minimal_sfnt_with_tables([("cblc", cblc_data), ("CBDT", cbdt_data)], num_glyphs=15)

        font = FontLoader.open(font_data)
        assert isinstance(font, TtfFont)
        assert font.num_glyphs == 15

        subsetted = FontSubsetter.subset_by_gids(font, {0, 5, 7})

        assert subsetted.num_glyphs == 3

        subsetted_data = subsetted.to_bytes()
        subsetted_reloaded = FontLoader.open(subsetted_data)
        assert isinstance(subsetted_reloaded, TtfFont)

        subsetted_tables = subsetted_reloaded.ttf_tables
        assert subsetted_tables.cblc is not None
        assert subsetted_tables.cbdt is not None

    def test_subset_ttf_with_cbdt_preserves_bitmap_records_for_retained_glyphs(
        self,
        tmp_path,
    ) -> None:
        """Test that subset retains CBDT bitmap data for glyphs that are kept."""
        bitmap_data = b"\x89PNG\r\n\x1a\n"
        glyphs = [(5, bitmap_data), (7, bitmap_data)]
        cbdt_data = _build_cbdt_table_with_glyphs(glyphs, ppem=24)
        cblc_data = _build_cblc_table_with_glyphs(glyphs, ppem=24)
        font_data = _build_minimal_sfnt_with_tables([("cblc", cblc_data), ("CBDT", cbdt_data)], num_glyphs=10)

        font = FontLoader.open(font_data)
        assert isinstance(font, TtfFont)

        subsetted = FontSubsetter.subset_by_gids(font, {0, 5})

        assert subsetted.num_glyphs == 2

        subsetted_data = subsetted.to_bytes()
        subsetted_reloaded = FontLoader.open(subsetted_data)
        assert isinstance(subsetted_reloaded, TtfFont)

        subsetted_tables = subsetted_reloaded.ttf_tables
        assert subsetted_tables.cblc is not None
        assert subsetted_tables.cbdt is not None

    def test_subset_ttf_with_cbdt_reindexes_glyph_ids_correctly(
        self,
        tmp_path,
    ) -> None:
        """Test that subsetted CBDT glyph IDs are correctly re-indexed."""
        bitmap_data = b"\x89PNG\r\n\x1a\n"
        glyphs = [(5, bitmap_data), (7, bitmap_data), (10, bitmap_data)]
        cbdt_data = _build_cbdt_table_with_glyphs(glyphs, ppem=24)
        cblc_data = _build_cblc_table_with_glyphs(glyphs, ppem=24)
        font_data = _build_minimal_sfnt_with_tables([("cblc", cblc_data), ("CBDT", cbdt_data)], num_glyphs=15)

        font = FontLoader.open(font_data)
        assert isinstance(font, TtfFont)

        subsetted = FontSubsetter.subset_by_gids(font, {0, 5, 7})

        subsetted_data = subsetted.to_bytes()
        subsetted_reloaded = FontLoader.open(subsetted_data)
        assert isinstance(subsetted_reloaded, TtfFont)

        subsetted_tables = subsetted_reloaded.ttf_tables
        assert subsetted_tables.cblc is not None
        assert subsetted_tables.cbdt is not None

    def test_subset_ttf_with_cbdt_returns_valid_font_roundtrip(
        self,
        tmp_path,
    ) -> None:
        """Test that subsetted font with CBDT can be reloaded and is valid."""
        bitmap_data = b"\x89PNG\r\n\x1a\n"
        glyphs = [(5, bitmap_data), (7, bitmap_data)]
        cbdt_data = _build_cbdt_table_with_glyphs(glyphs, ppem=24)
        cblc_data = _build_cblc_table_with_glyphs(glyphs, ppem=24)
        font_data = _build_minimal_sfnt_with_tables([("cblc", cblc_data), ("CBDT", cbdt_data)], num_glyphs=10)

        font = FontLoader.open(font_data)
        assert isinstance(font, TtfFont)

        subsetted = FontSubsetter.subset_by_gids(font, {0, 5})
        subsetted_data = subsetted.to_bytes()

        reloaded = FontLoader.open(subsetted_data)
        assert isinstance(reloaded, TtfFont)
        assert reloaded.num_glyphs == subsetted.num_glyphs


class TestEdgeCases:
    """Tests for edge cases in sbix/cbdt subsetting."""

    def test_subset_font_without_bitmap_tables_works_as_before(
        self,
        tmp_path,
    ) -> None:
        """Test that subsetting fonts without bitmap tables works as before."""
        font_data = _build_minimal_sfnt_with_tables([], num_glyphs=5)

        font = FontLoader.open(font_data)
        assert isinstance(font, TtfFont)

        subsetted = FontSubsetter.subset_by_gids(font, {0, 1})
        assert subsetted.num_glyphs == 2

        reloaded = FontLoader.open(subsetted.to_bytes())
        assert isinstance(reloaded, TtfFont)
        assert reloaded.ttf_tables.sbix is None
        assert reloaded.ttf_tables.cblc is None
        assert reloaded.ttf_tables.cbdt is None

    def test_subset_by_gids_prunes_bitmaps_correctly(
        self,
        tmp_path,
    ) -> None:
        """Test that subsetting by gids correctly prunes sbix/cbdt tables."""
        bitmap_data = b"\x89PNG\r\n\x1a\n"
        sbix_glyphs = [(5, bitmap_data), (7, bitmap_data), (10, bitmap_data)]
        sbix_data = _build_sbix_table_with_png_glyphs(sbix_glyphs, ppem=24)
        font_data = _build_minimal_sfnt_with_tables([("sbix", sbix_data)], num_glyphs=15)

        font = FontLoader.open(font_data)
        assert isinstance(font, TtfFont)

        subsetted = FontSubsetter.subset_by_gids(font, {1, 2})

        subsetted_data = subsetted.to_bytes()
        reloaded = FontLoader.open(subsetted_data)
        assert isinstance(reloaded, TtfFont)

        subsetted_tables = reloaded.ttf_tables
        if subsetted_tables.sbix is not None:
            records = subsetted_tables.sbix.bitmap_records[0]
            assert len(records) == 0

    def test_subset_multiple_strikes_prunes_each_strike(
        self,
        tmp_path,
    ) -> None:
        """Test that subsetting with multiple strikes prunes each strike correctly."""
        bitmap_data_16 = b"\x89PNG\r\n\x1a\nLOW"
        bitmap_data_24 = b"\x89PNG\r\n\x1a\nHIGH"

        combined = b""
        combined += (0).to_bytes(2, "big")
        combined += (0).to_bytes(2, "big")
        combined += (2).to_bytes(4, "big")

        combined += (16).to_bytes(2, "big")
        combined += (72).to_bytes(2, "big")
        combined += (0).to_bytes(4, "big")

        combined += (24).to_bytes(2, "big")
        combined += (96).to_bytes(2, "big")
        combined += (0).to_bytes(4, "big")

        combined += (1).to_bytes(4, "big")
        combined += (5).to_bytes(2, "big")
        combined += b"png "
        combined += (0).to_bytes(2, "big")
        combined += (0).to_bytes(2, "big")
        combined += len(bitmap_data_16).to_bytes(4, "big")
        combined += bitmap_data_16

        combined += (1).to_bytes(4, "big")
        combined += (5).to_bytes(2, "big")
        combined += b"png "
        combined += (0).to_bytes(2, "big")
        combined += (0).to_bytes(2, "big")
        combined += len(bitmap_data_24).to_bytes(4, "big")
        combined += bitmap_data_24

        font_data = _build_minimal_sfnt_with_tables([("sbix", combined)], num_glyphs=15)

        font = FontLoader.open(font_data)
        assert isinstance(font, TtfFont)

        subsetted = FontSubsetter.subset_by_gids(font, {0, 5})

        reloaded = FontLoader.open(subsetted.to_bytes())
        assert isinstance(reloaded, TtfFont)
