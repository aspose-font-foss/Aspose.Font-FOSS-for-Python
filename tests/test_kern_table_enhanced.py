"""Enhanced kern table parser tests (FONT-495)."""
from __future__ import annotations

import struct

from aspose_font._io import BinaryReader
from aspose_font._types import GlyphId
from aspose_font.ttf.tables.kern import KernTable


def _make_kern_bin_opentype(subtables: list[bytes]) -> bytes:
    """Build OpenType kern table (version=0, nTables=uint16)."""
    data = struct.pack(">HH", 0, len(subtables))
    for sub in subtables:
        data += sub
    return data


def _make_kern_bin_apple(subtables: list[bytes]) -> bytes:
    """Build Apple kern table (version=0x00010000, nTables=uint32)."""
    data = struct.pack(">IH", 0x00010000, 0)
    data += struct.pack(">I", len(subtables))
    for sub in subtables:
        data += sub
    return data


def _make_format0_subtable(pairs: list[tuple[int, int, int]], coverage: int = 0x0000) -> bytes:
    """Build format 0 kern subtable."""
    n = len(pairs)
    sub_len = 6 + 8 + n * 6
    data = struct.pack(">HHH", 0, sub_len, coverage)
    data += struct.pack(">HHHH", n, n * 6, 0, 0)
    for left, right, value in pairs:
        data += struct.pack(">HHh", left, right, value)
    return data


def _make_format2_subtable(
    num_glyphs: int,
    first_glyph: int,
    left_classes: list[int],
    right_classes: list[int],
    width_counts: list[int],
    width_values: list[int],
    coverage: int = 0x0002,
) -> bytes:
    """Build format 2 kern subtable."""
    assert len(left_classes) == num_glyphs
    assert len(right_classes) == num_glyphs

    # Total subtable length calculation
    # After header (6 chars):
    # - rowWidth (2) + firstGlyph (2) + numGlyphs (2) = 6
    # - left_class_table: num_glyphs * 2
    # - right_class_table: num_glyphs * 2
    # - width_class_counts: len(width_counts) * 2
    # - width_values: len(width_values) * 2
    sub_len = 6 + 6 + (num_glyphs * 2) * 2 + len(width_counts) * 2 + len(width_values) * 2

    # rowWidth should be 4 (leftClass + rightClass fields) + width values per row
    # For simplicity, use a conservative estimate
    max(left_classes) + 1 if left_classes else 1
    row_width = 4 + sum(width_counts) * 2

    data = struct.pack(">HHH", 0, sub_len, coverage)  # version, length, coverage (contains format in bits 7-0)
    data += struct.pack(">HHH", row_width, first_glyph, num_glyphs)

    for c in left_classes:
        data += struct.pack(">H", c)
    for c in right_classes:
        data += struct.pack(">H", c)

    for c in width_counts:
        data += struct.pack(">H", c)
    for v in width_values:
        data += struct.pack(">h", v)

    return data


class TestHeaderParsing:
    def test_opentype_16bit_header_parsing(self) -> None:
        subtable = _make_format0_subtable([(1, 2, -30)])
        data = _make_kern_bin_opentype([subtable])
        table = KernTable.from_reader(BinaryReader(data), len(data))
        assert len(table.subtables) == 1
        assert table.subtables[0].version == 0
        assert table.subtables[0].length == len(subtable)
        assert table.subtables[0].coverage == 0x0000
        assert table.subtables[0].format == 0

    def test_apple_32bit_header_parsing(self) -> None:
        subtable = _make_format0_subtable([(1, 2, -30)])
        data = _make_kern_bin_apple([subtable])
        table = KernTable.from_reader(BinaryReader(data), len(data))
        assert len(table.subtables) == 1
        assert table.subtables[0].format == 0

    def test_multiple_subtables_parsing(self) -> None:
        sub1 = _make_format0_subtable([(1, 2, -30)])
        sub2 = _make_format0_subtable([(3, 4, 20)])
        data = _make_kern_bin_opentype([sub1, sub2])
        table = KernTable.from_reader(BinaryReader(data), len(data))
        assert len(table.subtables) == 2
        assert table.subtables[0].format == 0
        assert table.subtables[1].format == 0

    def test_empty_kern_table(self) -> None:
        data = struct.pack(">HH", 0, 0)
        table = KernTable.from_reader(BinaryReader(data), len(data))
        assert len(table.subtables) == 0
        assert table.get_all_pairs() == []


class TestCoverageFlags:
    def test_horizontal_flag_bit_15_offset(self) -> None:
        subtable = _make_format0_subtable([(1, 2, -30)], coverage=0x0001)
        data = _make_kern_bin_opentype([subtable])
        table = KernTable.from_reader(BinaryReader(data), len(data))
        assert (table.subtables[0].coverage & 0x8000) == 0

    def test_vertical_flag_bit_15_set(self) -> None:
        subtable = _make_format0_subtable([(1, 2, -30)], coverage=0x8001)
        data = _make_kern_bin_opentype([subtable])
        table = KernTable.from_reader(BinaryReader(data), len(data))
        assert (table.subtables[0].coverage & 0x8000) != 0

    def test_cross_stream_flag_bit_14(self) -> None:
        subtable = _make_format0_subtable([(1, 2, -30)], coverage=0x4001)
        data = _make_kern_bin_opentype([subtable])
        table = KernTable.from_reader(BinaryReader(data), len(data))
        assert (table.subtables[0].coverage & 0x4000) != 0

    def test_override_flag_bit_13(self) -> None:
        subtable = _make_format0_subtable([(1, 2, -30)], coverage=0x2001)
        data = _make_kern_bin_opentype([subtable])
        table = KernTable.from_reader(BinaryReader(data), len(data))
        assert (table.subtables[0].coverage & 0x2000) != 0

    def test_format_detection_from_coverage(self) -> None:
        sub_format0 = _make_format0_subtable([(1, 2, -30)], coverage=0x0100)
        sub_format2 = _make_format2_subtable(2, 0, [0, 1], [0, 1], [1, 1], [20], coverage=0x0002)
        data = _make_kern_bin_opentype([sub_format0, sub_format2])
        table = KernTable.from_reader(BinaryReader(data), len(data))
        assert table.subtables[0].format == 0
        assert table.subtables[1].format == 2


class TestFormat0:
    def test_format0_pair_parsing(self) -> None:
        pairs = [(1, 2, -30), (3, 4, 20), (5, 6, 10)]
        subtable = _make_format0_subtable(pairs)
        data = _make_kern_bin_opentype([subtable])
        table = KernTable.from_reader(BinaryReader(data), len(data))
        pairs_found = table.get_all_pairs()
        assert len(pairs_found) == 3
        assert pairs_found[0].left == GlyphId(1)
        assert pairs_found[0].right == GlyphId(2)
        assert pairs_found[0].value == -30

    def test_format0_malformed_truncation(self) -> None:
        malformed = bytes.fromhex(
            "0000"
            "0001"
            "0000"
            "0014"
            "0000"  # Changed from 0001 - coverage=0x0000 means format 0
            "0002"
            "0000"
            "0000"
            "0000"
            "0001"
            "0002"
            "FFE2"
        )
        table = KernTable.from_reader(BinaryReader(malformed), len(malformed))
        assert table.get(GlyphId(1), GlyphId(2)) == -30

    def test_format0_empty(self) -> None:
        subtable = _make_format0_subtable([])
        data = _make_kern_bin_opentype([subtable])
        table = KernTable.from_reader(BinaryReader(data), len(data))
        assert table.get_all_pairs() == []

    def test_format0_negative_values(self) -> None:
        pairs = [(1, 2, -100), (3, 4, -50)]
        subtable = _make_format0_subtable(pairs)
        data = _make_kern_bin_opentype([subtable])
        table = KernTable.from_reader(BinaryReader(data), len(data))
        pairs_found = table.get_all_pairs()
        assert pairs_found[0].value == -100
        assert pairs_found[1].value == -50

    def test_format0_positive_values(self) -> None:
        pairs = [(1, 2, 100), (3, 4, 50)]
        subtable = _make_format0_subtable(pairs)
        data = _make_kern_bin_opentype([subtable])
        table = KernTable.from_reader(BinaryReader(data), len(data))
        pairs_found = table.get_all_pairs()
        assert pairs_found[0].value == 100
        assert pairs_found[1].value == 50


class TestFormat2:
    def test_format2_class_table_parsing(self) -> None:
        subtable = _make_format2_subtable(
            num_glyphs=2,
            first_glyph=0,
            left_classes=[0, 1],
            right_classes=[0, 1],
            width_counts=[1, 1],
            width_values=[20, 30],
        )
        data = _make_kern_bin_opentype([subtable])
        table = KernTable.from_reader(BinaryReader(data), len(data))
        st = table.subtables[0]
        assert st.left_class_table == [0, 1]
        assert st.right_class_table == [0, 1]
        assert st.width_class_counts == [1, 1]
        assert st.width_values == [20, 30]
        assert st.first_glyph == 0
        assert st.num_glyphs == 2

    def test_format2_to_pairs_conversion(self) -> None:
        subtable = _make_format2_subtable(
            num_glyphs=2,
            first_glyph=10,
            left_classes=[0, 1],
            right_classes=[0, 1],
            width_counts=[2, 2],
            width_values=[20, 30, 40, 50],
        )
        data = _make_kern_bin_opentype([subtable])
        table = KernTable.from_reader(BinaryReader(data), len(data))
        pairs = table.get_all_pairs()
        assert len(pairs) == 4
        assert (pairs[0].left.value, pairs[0].right.value, pairs[0].value) == (10, 10, 20)

    def test_format2_zero_width_omitted(self) -> None:
        subtable = _make_format2_subtable(
            num_glyphs=2,
            first_glyph=10,
            left_classes=[0, 1],
            right_classes=[0, 1],
            width_counts=[2, 2],
            width_values=[20, 0, 30, 40],
        )
        data = _make_kern_bin_opentype([subtable])
        table = KernTable.from_reader(BinaryReader(data), len(data))
        pairs = table.get_all_pairs()
        for p in pairs:
            assert p.value != 0

    def test_format2_malformed_graceful_recovery(self) -> None:
        malformed = struct.pack(">HHH", 0, 20, 0x0002)
        malformed += struct.pack(">HHHH", 2, 10, 0, 2)
        malformed += struct.pack(">HH", 0, 1)
        malformed += struct.pack(">HH", 0, 1)
        malformed += struct.pack(">H", 1)
        data = _make_kern_bin_opentype([malformed])
        table = KernTable.from_reader(BinaryReader(data), len(data))
        assert len(table.subtables) == 1
        assert table.subtables[0].format == 2

    def test_format2_negative_values(self) -> None:
        subtable = _make_format2_subtable(
            num_glyphs=2,
            first_glyph=10,
            left_classes=[0, 1],
            right_classes=[0, 1],
            width_counts=[2, 2],
            width_values=[-20, -30, -40, -50],
        )
        data = _make_kern_bin_opentype([subtable])
        table = KernTable.from_reader(BinaryReader(data), len(data))
        pairs = table.get_all_pairs()
        assert pairs[0].value == -20


class TestMultiSubtable:
    def test_mixed_format_subtables(self) -> None:
        sub1 = _make_format0_subtable([(1, 2, -30)])
        sub2 = _make_format2_subtable(
            num_glyphs=2,
            first_glyph=5,
            left_classes=[0, 1],
            right_classes=[0, 1],
            width_counts=[2, 2],
            width_values=[20, 30, 40, 50],
        )
        data = _make_kern_bin_opentype([sub1, sub2])
        table = KernTable.from_reader(BinaryReader(data), len(data))
        assert len(table.subtables) == 2
        assert table.subtables[0].format == 0
        assert table.subtables[1].format == 2
        pairs = table.get_all_pairs()
        assert len(pairs) == 5

    def test_overrides_previous_subtable(self) -> None:
        sub1 = _make_format0_subtable([(1, 2, -30)], coverage=0x0000)
        sub2 = _make_format0_subtable([(1, 2, 50)], coverage=0x2000)
        data = _make_kern_bin_opentype([sub1, sub2])
        table = KernTable.from_reader(BinaryReader(data), len(data))
        table.get_all_pairs()
        lookup = table.build_lookup()
        assert lookup[(1, 2)] == 50

    def test_horizontal_and_vertical_subtables(self) -> None:
        horizontal = _make_format0_subtable([(1, 2, -30)], coverage=0x0001)
        vertical = _make_format0_subtable([(3, 4, 20)], coverage=0x8001)
        data = _make_kern_bin_opentype([horizontal, vertical])
        table = KernTable.from_reader(BinaryReader(data), len(data))
        assert len(table.subtables) == 2
        assert (table.subtables[0].coverage & 0x8000) == 0
        assert (table.subtables[1].coverage & 0x8000) != 0


class TestLookupMethods:
    def test_kern_table_get_all_pairs(self) -> None:
        pairs = [(1, 2, -30), (3, 4, 20)]
        subtable = _make_format0_subtable(pairs)
        data = _make_kern_bin_opentype([subtable])
        table = KernTable.from_reader(BinaryReader(data), len(data))
        all_pairs = table.get_all_pairs()
        assert len(all_pairs) == 2
        assert all_pairs[0].left == GlyphId(1)
        assert all_pairs[1].left == GlyphId(3)

    def test_kern_table_get_with_format2(self) -> None:
        subtable = _make_format2_subtable(
            num_glyphs=2,
            first_glyph=10,
            left_classes=[0, 1],
            right_classes=[0, 1],
            width_counts=[2, 2],
            width_values=[20, 30, 40, 50],
        )
        data = _make_kern_bin_opentype([subtable])
        table = KernTable.from_reader(BinaryReader(data), len(data))
        assert table.get(GlyphId(10), GlyphId(10)) == 20
        assert table.get(GlyphId(10), GlyphId(11)) == 30
        assert table.get(GlyphId(99), GlyphId(99)) == 0

    def test_kern_table_build_lookup_with_format2(self) -> None:
        subtable = _make_format2_subtable(
            num_glyphs=2,
            first_glyph=10,
            left_classes=[0, 1],
            right_classes=[0, 1],
            width_counts=[2, 2],
            width_values=[20, 30, 40, 50],
        )
        data = _make_kern_bin_opentype([subtable])
        table = KernTable.from_reader(BinaryReader(data), len(data))
        lookup = table.build_lookup()
        assert lookup[(10, 10)] == 20
        assert lookup[(10, 11)] == 30
        assert lookup[(11, 10)] == 40
        assert lookup[(11, 11)] == 50
        assert (99, 99) not in lookup

    def test_kern_table_roundtrip(self) -> None:
        pairs = [(1, 2, -30), (3, 4, 20)]
        subtable = _make_format0_subtable(pairs)
        data = _make_kern_bin_opentype([subtable])
        table = KernTable.from_reader(BinaryReader(data), len(data))
        raw = table.to_bytes()
        reparsed = KernTable.from_reader(BinaryReader(raw), len(raw))
        pairs1 = table.get_all_pairs()
        pairs2 = reparsed.get_all_pairs()
        assert len(pairs1) == len(pairs2)


class TestEdgeCases:
    def test_zero_length_subtable(self) -> None:
        malformed = struct.pack(">HHH", 0, 6, 0x0001)
        data = _make_kern_bin_opentype([malformed])
        table = KernTable.from_reader(BinaryReader(data), len(data))
        assert len(table.subtables) == 1

    def test_oob_subtable_length(self) -> None:
        too_long = struct.pack(">HHH", 0, 1000, 0x0001)
        data = _make_kern_bin_opentype([too_long])
        table = KernTable.from_reader(BinaryReader(data), len(data))
        assert len(table.subtables) == 1

    def test_empty_source(self) -> None:
        table = KernTable.from_reader(BinaryReader(b""), 0)
        assert len(table.subtables) == 0

    def test_single_glyph_format2(self) -> None:
        subtable = _make_format2_subtable(
            num_glyphs=1,
            first_glyph=5,
            left_classes=[0],
            right_classes=[0],
            width_counts=[2],
            width_values=[15, 20],
        )
        data = _make_kern_bin_opentype([subtable])
        table = KernTable.from_reader(BinaryReader(data), len(data))
        pairs = table.get_all_pairs()
        assert len(pairs) == 1
        assert pairs[0].left.value == 5
        assert pairs[0].right.value == 5
        assert pairs[0].value == 15


class TestIntegrationWithExisting:
    def test_get_with_format0_backward_compat(self) -> None:
        pairs = [(1, 2, -30), (3, 4, 20)]
        subtable = _make_format0_subtable(pairs)
        data = _make_kern_bin_opentype([subtable])
        table = KernTable.from_reader(BinaryReader(data), len(data))
        assert table.get(GlyphId(1), GlyphId(2)) == -30
        assert table.get(GlyphId(0), GlyphId(0)) == 0

    def test_build_lookup_with_format0_backward_compat(self) -> None:
        pairs = [(1, 2, -30), (3, 4, 20)]
        subtable = _make_format0_subtable(pairs)
        data = _make_kern_bin_opentype([subtable])
        table = KernTable.from_reader(BinaryReader(data), len(data))
        lookup = table.build_lookup()
        assert lookup[(1, 2)] == -30
        assert lookup[(3, 4)] == 20
