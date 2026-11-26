"""TTF JSTF table parser tests (FONT-499, FONT-534)."""
from __future__ import annotations

import struct

from aspose_font._io import BinaryReader
from aspose_font.ttf.tables.jstf import JstfPriority, JstfTable


def _make_jstf_binary(
    scripts: list[tuple[str, str, list[int]]],
    lookups: list[tuple[int, bytes]],
    version: int = 0x0001,
) -> bytes:
    """Build a minimal JSTF table following OpenType spec.

    JSTF table format:
    - version (2 bytes)
    - script_list_offset (2 bytes) - from start of table to ScriptList
    - lookup_list_offset (2 bytes) - from start of table to LookupList

    ScriptList format:
    - count (2 bytes)
    - records[count]: each is (tag: 4 bytes, offset: 2 bytes from end of ScriptList header)

    Script format:
    - default_lang_sys_offset (2 bytes) - from start of Script table
    - lang_sys_count (2 bytes)
    - lang_sys_records[lang_sys_count]: (tag: 4 bytes, offset: 2 bytes from start of Script)
    - default LangSys (if offset > 0): (req_index: 2 bytes, count: 2 bytes, indices[count])

    LookupList format:
    - count (2 bytes)
    - offsets[count]: (offset: 2 bytes from start of LookupList to each JustificationLookup)

    JustificationLookup format:
    - format (2 bytes)
    - data (variable)
    """

    script_records = []
    script_tables = []

    for script_tag, lang_tag, features in scripts:
        # Build LangSys data
        if features:
            default_lang_sys_data = struct.pack(">HH", features[0], len(features) - 1)
            for feat in features[1:]:
                default_lang_sys_data += struct.pack(">H", feat)
        else:
            default_lang_sys_data = struct.pack(">HH", 0, 0)

        # Script table layout:
        # - default_lang_sys_offset (2 bytes)
        # - lang_sys_count (2 bytes)
        # - LangSys records (tag + offset for each, 6 bytes each)
        # - LangSys tables (at offsets from script table start)

        # Size of header + records before LangSys data
        script_header_record_size = 4 + (6 if lang_tag else 0)

        if lang_tag:
            lang_sys_tag = lang_tag.encode()
            # default_lang_sys_offset = 0 means no default
            # We want to store LangSys at position 0 from script table start
            # So offset should be 0, but parser treats 0 as "no LangSys"
            # So we need to create a separate default LangSys table
            # Actually, in JSTF, if there's a default LangSys, offset > 0
            # The LangSys data comes after the records
            # For 1 LangSys record (6 bytes), LangSys data starts at offset 4+6=10
            # But we want the LangSys to be the default, so we set offset to where it is
            script_table = struct.pack(">HH", script_header_record_size, 1)
            script_table += struct.pack(">4sH", lang_sys_tag, script_header_record_size)
            script_table += default_lang_sys_data
        else:
            script_table = struct.pack(">HH", 0, 0)

        script_tables.append(script_table)

        script_records.append(struct.pack(">4sH", script_tag.encode(), 6))

    script_list = struct.pack(">H", len(scripts)) + b"".join(script_records)

    # JSTF LookupList format:
    # - lookup_count (2 bytes)
    # - offset[0..count-1] (2 bytes each, from start of LookupList to each JustificationLookup)
    # JustificationLookup format:
    # - format (2 bytes)
    # - data (variable)
    # Offsets point from start of LookupList to each JustificationLookup (format field)

    lookup_data = b""
    lookup_offsets = []
    # First lookup format starts after lookup_list header (count + offsets)
    # lookup_list header = 2 (count) + 2 * len(lookups) (offsets)
    lookup_list_header_size = 2 + 2 * len(lookups)
    current_offset = lookup_list_header_size

    for fmt, data in lookups:
        lookup_offsets.append(current_offset)
        lookup_data += struct.pack(">H", fmt) + data
        current_offset += 2 + len(data)

    lookup_list = struct.pack(">H", len(lookups)) + b"".join(
        struct.pack(">H", off) for off in lookup_offsets
    )

    # lookup_list comes after lookup_data
    lookup_list_offset = 6 + len(script_list) + sum(len(st) for st in script_tables)

    result = struct.pack(">HHH", version, 6, lookup_list_offset)

    result += script_list

    for st in script_tables:
        result += st

    result += lookup_list + lookup_data

    return result


def test_jstf_table_basic_parse() -> None:
    """Test parsing a minimal JSTF table with one script."""
    raw = _make_jstf_binary([
        ("DFLT", "dflt", [10, 20]),
    ], [
        (1, b"\x00\x01\x00\x02"),
    ])
    table = JstfTable.from_reader(BinaryReader(raw), len(raw))

    assert table.version == 0x0001
    assert len(table.get_scripts()) == 1
    assert table.get_scripts()[0].script_tag == "DFLT"


def test_jstf_table_multiple_scripts() -> None:
    """Test parsing JSTF with multiple scripts."""
    raw = _make_jstf_binary([
        ("DFLT", "dflt", []),
        ("latn", "dflt", [5]),
        ("kana", "dflt", [10, 15]),
    ], [])
    table = JstfTable.from_reader(BinaryReader(raw), len(raw))

    scripts = table.get_scripts()
    assert len(scripts) == 3
    assert {s.script_tag for s in scripts} == {"DFLT", "latn", "kana"}


def test_jstf_table_malformed_is_skipped() -> None:
    """Test that malformed subtables don't crash parsing."""
    raw = b"\x00\x01\x00\x02\x00\x03" + b"\xFF" * 100
    table = JstfTable.from_reader(BinaryReader(raw), len(raw))

    assert table is not None
    assert table.version == 0x0001


def test_jstf_table_empty_scripts() -> None:
    """Test JSTF with empty script list."""
    header = struct.pack(">HHH", 0x0001, 6, 8)
    script_data = struct.pack(">H", 0)
    lookup_data = struct.pack(">H", 0)

    raw = header + script_data + lookup_data
    table = JstfTable.from_reader(BinaryReader(raw), len(raw))

    assert table.version == 0x0001
    assert len(table.get_scripts()) == 0
    assert len(table.lookup_list) == 0


def test_jstf_table_round_trip() -> None:
    """Test that to_bytes returns original raw data."""
    raw = _make_jstf_binary([
        ("DFLT", "dflt", [1]),
    ], [
        (2, b"\x00\x03"),
    ])
    table = JstfTable.from_reader(BinaryReader(raw), len(raw))

    assert table.to_bytes() == raw


def test_jstf_priority_dataclass() -> None:
    """Test JstfPriority dataclass fields."""
    priority = JstfPriority(
        priority=1,
        extender_glyphs=[10, 20],
        shrinkage_glyphs=[30]
    )
    assert priority.priority == 1
    assert priority.extender_glyphs == [10, 20]
    assert priority.shrinkage_glyphs == [30]


def test_jstf_table_lookup_access() -> None:
    """Test getting lookups by index."""
    raw = _make_jstf_binary([], [
        (1, b"\x00\x01"),
        (2, b"\x00\x02\x00\x03"),
    ])
    table = JstfTable.from_reader(BinaryReader(raw), len(raw))

    assert len(table.lookup_list) == 2
    lookup0 = table.get_lookup(0)
    lookup1 = table.get_lookup(1)
    lookup_out = table.get_lookup(99)

    assert lookup0 is not None
    assert lookup0.format == 1
    assert lookup1 is not None
    assert lookup1.format == 2
    assert lookup_out is None


def test_jstf_table_lang_sys_features() -> None:
    """Test parsing language system feature indices."""
    raw = _make_jstf_binary([
        ("latn", "dflt", [5, 10, 15]),
    ], [])
    table = JstfTable.from_reader(BinaryReader(raw), len(raw))

    assert len(table.get_scripts()) == 1
    script = table.get_scripts()[0]
    assert script.default_lang_sys is not None
    assert script.default_lang_sys.req_feature_index == 5
    assert script.default_lang_sys.feature_indices == [10, 15]


def _make_jstf_with_priority(
    scripts: list[tuple[str, str, list[int]]],
    priorities: list[list[tuple[int, list[int], list[int]]]],
    lookups: list[tuple[int, bytes]],
    version: int = 0x0001,
) -> bytes:
    """Build a JSTF table with priority records.

    JSTF table format:
    - version (2 bytes)
    - script_list_offset (2 bytes)
    - lookup_list_offset (2 bytes)
    - priority_list_offset (2 bytes)

    ScriptList format:
    - count (2 bytes)
    - records[count]: (tag: 4 bytes, offset: 2 bytes from end of ScriptList header)

    Script format:
    - default_lang_sys_offset (2 bytes)
     - lang_sys_count (2 bytes)
     - priority_count (2 bytes)
     - lang_sys_records[lang_sys_count]: (tag: 4 bytes, offset: 2 bytes from start of Script)
     - LangSys tables (at offsets from script table start)
     - PriorityList (at end of script table for this script)
     PriorityList format:
    - count (2 bytes)
    - records[count]: (priority: 2 bytes, extender_count: 2 bytes, shrink_count: 2 bytes,
                       extender[glyph_count] (2 bytes each), shrink[glyph_count] (2 bytes each))
    """
    # Build all script tables first to calculate sizes
    script_tables_data = []

    for i, (script_tag, lang_tag, features) in enumerate(scripts):
        script_priorities = priorities[i] if i < len(priorities) else []

        # Build LangSys data
        if features:
            default_lang_sys_data = struct.pack(">HH", features[0], len(features) - 1)
            for feat in features[1:]:
                default_lang_sys_data += struct.pack(">H", feat)
        else:
            default_lang_sys_data = struct.pack(">HH", 0, 0)

        # Build PriorityList data
        priority_data = b""
        if script_priorities:
            priority_data += struct.pack(">H", len(script_priorities))
            for prio, extender, shrink in script_priorities:
                priority_data += struct.pack(">H", prio)
                priority_data += struct.pack(">H", len(extender))
                for glyph in extender:
                    priority_data += struct.pack(">H", glyph)
                priority_data += struct.pack(">H", len(shrink))
                for glyph in shrink:
                    priority_data += struct.pack(">H", glyph)

        # Script table layout
        # Header: 6 bytes (default_lang_sys_offset + lang_sys_count + priority_count)
        # Records: 6 bytes per LangSys (tag + offset)
        # LangSys data at offset
        # PriorityList at end of script table

        script_header_size = 6  # 3 * uint16
        lang_sys_record_size = 6  # 4 (tag) + 2 (offset)

        if lang_tag:
            # LangSys data is at the end of script table, after LangSys records
            # So if we have 1 LangSys record, LangSys data is at offset 6 from script start
            lang_sys_position = script_header_size + lang_sys_record_size
            script_table = struct.pack(">HHH", lang_sys_position, 1, len(script_priorities))
            script_table += struct.pack(">4sH", lang_tag.encode(), lang_sys_position)
            script_table += default_lang_sys_data
        else:
            script_table = struct.pack(">HHH", 0, 0, len(script_priorities))

        # Append priority data at the end of script table
        script_table += priority_data

        script_tables_data.append(script_table)

    # Build ScriptList
    script_list = struct.pack(">H", len(scripts))
    script_list_offset = 8  # After version(2) + offsets(6)

    for i, (script_tag, _, _) in enumerate(scripts):
        offset_to_script = script_list_offset + 2 + i * 6
        script_list += struct.pack(">4sH", script_tag.encode(), offset_to_script)

    # Build LookupList
    lookup_list_data = b""
    lookup_offsets = []
    lookup_list_offset = script_list_offset + len(script_tables_data) * 6 + sum(len(st) for st in script_tables_data)

    current_lookup_offset = 2 + len(lookups) * 2
    for fmt, data in lookups:
        lookup_offsets.append(current_lookup_offset)
        lookup_list_data += struct.pack(">H", fmt) + data
        current_lookup_offset += 2 + len(data)

    lookup_list_header = struct.pack(">H", len(lookups))
    for off in lookup_offsets:
        lookup_list_header += struct.pack(">H", off)

    # Build table
    result = struct.pack(">HHHH", version, 8, lookup_list_offset, lookup_list_offset + len(lookup_list_header) + len(lookup_list_data))
    result += script_list

    for st in script_tables_data:
        result += st

    result += lookup_list_header + lookup_list_data

    return result


def test_jstf_table_priority_records() -> None:
    """Test parsing JSTF priority records with extender and shrink glyph lists."""
    # Build JSTF table manually with priority records following the OpenType spec

    # JSTF table header (8 bytes):
    # - version (2 bytes)
    # - script_list_offset (2 bytes)
    # - lookup_list_offset (2 bytes)
    # - priority_list_offset (2 bytes)

    # ScriptList at script_list_offset:
    # - count (2 bytes)
    # - records[count]: (tag: 4 bytes, offset: 2 bytes from end of ScriptList header)

    # Script at script_table_offset:
    # - default_lang_sys_offset (2 bytes)
    # - lang_sys_count (2 bytes)
    # - priority_count (2 bytes)
    # - LangSys records
    # - Priority data

    # Priority record format: priority(2) + extender_count(2) + extender_glyphs + shrink_count(2) + shrinkage_glyphs

    # Simple test: DFLT script with 2 priority records, no lang_sys
    # Header: 8 bytes
    # ScriptList: 2 (count) + 6 (record) = 8 bytes
    # Script table: 6 (header) + 14 (priority1) + 10 (priority2) = 30 bytes
    # Total: 46 bytes

    result = []

    # Header
    result.extend([0x00, 0x01])  # version = 0x0001
    result.extend([0x00, 0x08])  # script_list_offset
    result.extend([0x00, 0xFF])  # lookup_list_offset (unused)
    result.extend([0x00, 0xFF])  # priority_list_offset (unused)

    # ScriptList
    result.extend([0x00, 0x01])  # count = 1

    # ScriptRecord: "DFLT" at offset 6 from end of ScriptList header (8 + 2 = 10, so 10 + 6 = 16 is script table)
    result.extend([ord('D'), ord('F'), ord('L'), ord('T')])
    result.extend([0x00, 0x06])  # offset

    # Script table header: default_lang_sys_offset(2) + lang_sys_count(2) + priority_count(2)
    result.extend([0x00, 0x00])  # default_lang_sys_offset = 0 (no default)
    result.extend([0x00, 0x00])  # lang_sys_count = 0 (no lang_sys)
    result.extend([0x00, 0x02])  # priority_count = 2

    # Priority 1: priority=1, extender=[10,20,30], shrink=[40,50]
    result.extend([0x00, 0x01])  # priority
    result.extend([0x00, 0x03])  # extender_count = 3
    result.extend([0x00, 0x0A])  # extender[0] = 10
    result.extend([0x00, 0x14])  # extender[1] = 20
    result.extend([0x00, 0x1E])  # extender[2] = 30
    result.extend([0x00, 0x02])  # shrink_count = 2
    result.extend([0x00, 0x28])  # shrinkage[0] = 40
    result.extend([0x00, 0x32])  # shrinkage[1] = 50

    # Priority 2: priority=2, extender=[60], shrink=[70,80]
    result.extend([0x00, 0x02])  # priority
    result.extend([0x00, 0x01])  # extender_count = 1
    result.extend([0x00, 0x3C])  # extender[0] = 60
    result.extend([0x00, 0x02])  # shrink_count = 2
    result.extend([0x00, 0x46])  # shrinkage[0] = 70
    result.extend([0x00, 0x50])  # shrinkage[1] = 80

    raw = bytes(result)

    table = JstfTable.from_reader(BinaryReader(raw), len(raw))

    assert table.version == 0x0001
    assert len(table.get_scripts()) == 1
    script = table.get_scripts()[0]
    assert script.script_tag == "DFLT"
    assert len(script.priority) == 2
    assert script.priority[0].priority == 1
    assert script.priority[0].extender_glyphs == [10, 20, 30]
    assert script.priority[0].shrinkage_glyphs == [40, 50]
    assert script.priority[1].priority == 2
    assert script.priority[1].extender_glyphs == [60]
    assert script.priority[1].shrinkage_glyphs == [70, 80]


def test_jstf_table_priority_multiple_scripts() -> None:
    """Test parsing JSTF with priority records for multiple scripts."""
    # Build a simpler JSTF table with 2 scripts - only first has priorities
    # This avoids complex offset calculations

    # Header at offset 0: 8 bytes (version + 3 offsets)
    # ScriptList at offset 8: count(2) + records[2*6] = 14 bytes
    # Script table 0 at offset 22
    # Script table 1 at offset 28

    result = []

    # Header
    result.extend([0x00, 0x01])  # version
    result.extend([0x00, 0x08])  # script_list_offset = 8
    result.extend([0x00, 0xFF])  # lookup_list_offset
    result.extend([0x00, 0xFF])  # priority_list_offset

    # ScriptList: count + 2 records
    result.extend([0x00, 0x02])  # count = 2

    # ScriptTable 0 (latn) at offset 22
    # ScriptTable 1 (kana) at offset 38 (22 + 16 bytes for latn = 6 header + 10 priority)
    # ScriptList header ends at offset 10 (8 + 2 for count)
    # So offset for latn = 22 - 10 = 12, offset for kana = 38 - 10 = 28

    result.extend([ord('l'), ord('a'), ord('t'), ord('n')])
    result.extend([0x00, 0x0C])  # offset from end of header = 12

    result.extend([ord('k'), ord('a'), ord('n'), ord('a')])
    result.extend([0x00, 0x1C])  # offset from end of header = 28

    # Script table 0 (latn): has priority
    result.extend([0x00, 0x00])  # default_lang_sys_offset = 0
    result.extend([0x00, 0x00])  # lang_sys_count = 0
    result.extend([0x00, 0x01])  # priority_count = 1
    result.extend([0x00, 0x01])  # priority = 1
    result.extend([0x00, 0x01])  # extender_count = 1
    result.extend([0x00, 0x05])  # extender[0] = 5
    result.extend([0x00, 0x01])  # shrink_count = 1
    result.extend([0x00, 0x0A])  # shrinkage[0] = 10

    # Script table 1 (kana): no priority
    result.extend([0x00, 0x00])  # default_lang_sys_offset = 0
    result.extend([0x00, 0x00])  # lang_sys_count = 0
    result.extend([0x00, 0x00])  # priority_count = 0

    raw = bytes(result)

    table = JstfTable.from_reader(BinaryReader(raw), len(raw))

    assert table.version == 0x0001
    scripts = table.get_scripts()
    assert len(scripts) == 2
    assert scripts[0].script_tag == "latn"
    assert scripts[1].script_tag == "kana"
    assert len(scripts[0].priority) == 1
    assert scripts[0].priority[0].priority == 1
    assert scripts[0].priority[0].extender_glyphs == [5]
    assert scripts[0].priority[0].shrinkage_glyphs == [10]
    assert len(scripts[1].priority) == 0


def test_jstf_table_get_script_by_tag() -> None:
    """Test get_script() method to query scripts by tag."""
    raw = _make_jstf_binary([
        ("DFLT", "dflt", []),
        ("latn", "dflt", [5]),
        ("kana", "dflt", [10, 15]),
    ], [])

    table = JstfTable.from_reader(BinaryReader(raw), len(raw))

    script = table.get_script("latn")
    assert script is not None
    assert script.script_tag == "latn"

    script = table.get_script("kana")
    assert script is not None
    assert script.script_tag == "kana"

    script = table.get_script("nonexistent")
    assert script is None


def test_jstf_table_priority_empty_priority_list() -> None:
    """Test JSTF with zero priority records in script."""
    raw = _make_jstf_binary([
        ("latn", "dflt", [1]),
    ], [])

    table = JstfTable.from_reader(BinaryReader(raw), len(raw))

    script = table.get_script("latn")
    assert script is not None
    assert len(script.priority) == 0
