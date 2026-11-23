"""TTF JSTF (Justification) table parser.

The JSTF table provides justification parameters for glyphs used in text layout,
particularly for CJK (Chinese/Japanese/Korean) text handling.

Note: JSTF tables are extremely rare in production fonts (only in CJK fonts).
For MVP, this parser stores raw table bytes and can be enhanced on-demand if needed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from aspose_font._io import BinaryReader


@dataclass
class JstfLangSys:
    """Represents a JSTF language system."""
    req_feature_index: int
    feature_indices: list[int]


@dataclass
class JstfPriority:
    """Represents a JSTF priority record with extension and shrink glyph lists."""
    priority: int
    extender_glyphs: list[int]
    shrinkage_glyphs: list[int]


@dataclass
class JstfScript:
    """Represents a JSTF script with its language systems and priority records."""
    script_tag: str
    default_lang_sys: Optional[JstfLangSys]
    lang_sys_records: list[tuple[str, JstfLangSys]]
    priority: list[JstfPriority]


@dataclass
class JstfLookup:
    """Represents a JSTF justification lookup table."""
    format: int
    _raw: bytes


@dataclass
class JstfTable:
    """OpenType JSTF (Justification) table.

    Contains justification parameters for glyphs used in text layout,
    particularly for CJK (Chinese/Japanese/Korean) text handling.
    """
    version: int
    script_list: list[JstfScript]
    lookup_list: list[JstfLookup]
    priority: list[JstfPriority]
    _raw: bytes = field(default_factory=bytes)

    @classmethod
    def from_reader(cls, r: BinaryReader, table_length: int) -> "JstfTable":
        """Parse JSTF table from BinaryReader."""
        raw = r.read_bytes(table_length)
        rr = BinaryReader(raw)

        try:
            version = rr.read_u16()
        except Exception:
            return cls(version=0, script_list=[], lookup_list=[], priority=[], _raw=raw)

        try:
            script_list_offset = rr.read_u16()
            lookup_list_offset = rr.read_u16()
            priority_offset = rr.read_u16()
        except Exception:
            return cls(version=version, script_list=[], lookup_list=[], priority=[], _raw=raw)

        script_list: list[JstfScript] = []
        lookup_list: list[JstfLookup] = []
        priority: list[JstfPriority] = []

        if script_list_offset > 0 and script_list_offset < len(raw):
            try:
                rr.seek(script_list_offset)
                script_list = _parse_script_list(rr, raw, script_list_offset)
            except Exception:
                pass

        if lookup_list_offset > 0 and lookup_list_offset < len(raw):
            try:
                rr.seek(lookup_list_offset)
                lookup_list = _parse_lookup_list(rr, raw, lookup_list_offset)
            except Exception:
                pass

        if priority_offset > 0 and priority_offset < len(raw):
            try:
                rr.seek(priority_offset)
                priority = _parse_priority_list(rr, raw, priority_offset)
            except Exception:
                pass

        return cls(version=version, script_list=script_list, lookup_list=lookup_list, priority=priority, _raw=raw)

    def to_bytes(self) -> bytes:
        """Return raw table bytes (round-trip support)."""
        return self._raw

    def get_scripts(self) -> list[JstfScript]:
        """Return list of parsed scripts."""
        return self.script_list

    def get_script(self, tag: str) -> Optional["JstfScript"]:
        """Get a specific script by its tag.
        Args:
            tag: 4-character script tag (e.g., 'DFLT', 'latn', 'kana').
        Returns:
            JstfScript if found, None otherwise.
        """
        for script in self.script_list:
            if script.script_tag == tag:
                return script
        return None

    def get_lookup(self, index: int) -> Optional[JstfLookup]:
        """Get a specific justification lookup by index."""
        if 0 <= index < len(self.lookup_list):
            return self.lookup_list[index]
        return None


def _parse_script_list(rr: BinaryReader, raw: bytes, base_offset: int) -> list[JstfScript]:
    """Parse ScriptList table from JSTF table."""
    try:
        count = rr.read_u16()
    except Exception:
        return []

    scripts: list[JstfScript] = []
    script_list_start = rr.tell() - 2

    for _ in range(count):
        try:
            script_tag = rr.read_tag()
            script_offset = rr.read_u16()
        except Exception:
            break

        script_table_offset = script_list_start + 2 + script_offset
        if script_table_offset >= len(raw):
            break

        try:
            script_rr = BinaryReader(raw)
            script_rr.seek(script_table_offset)
            script = _parse_script_table(script_rr, raw, script_table_offset, script_tag)
            if script:
                scripts.append(script)
        except Exception:
            continue

    return scripts


def _parse_script_table(rr: BinaryReader, raw: bytes, base_offset: int, script_tag: str) -> Optional[JstfScript]:
    """Parse Script table from JSTF table."""
    try:
        default_lang_sys_offset = rr.read_u16()
        lang_sys_count = rr.read_u16()
        priority_count = rr.read_u16()
    except Exception:
        return None

    default_lang_sys: Optional[JstfLangSys] = None

    if default_lang_sys_offset > 0:
        try:
            lang_sys_rr = BinaryReader(raw)
            lang_sys_rr.seek(base_offset + default_lang_sys_offset)
            default_lang_sys = _parse_lang_sys(lang_sys_rr)
        except Exception:
            pass

    lang_sys_records: list[tuple[str, JstfLangSys]] = []

    for _ in range(lang_sys_count):
        try:
            lang_sys_tag = rr.read_tag()
            lang_sys_offset = rr.read_u16()
        except Exception:
            break

        lang_sys_table_offset = base_offset + lang_sys_offset
        if lang_sys_table_offset >= len(raw):
            break

        try:
            lang_sys_rr = BinaryReader(raw)
            lang_sys_rr.seek(lang_sys_table_offset)
            lang_sys = _parse_lang_sys(lang_sys_rr)
            if lang_sys:
                lang_sys_records.append((lang_sys_tag, lang_sys))
        except Exception:
            continue

    priority: list[JstfPriority] = []
    if priority_count > 0:
        try:
            priority_offset = rr.tell()
            priority = _parse_priority_list(rr, raw, priority_offset, priority_count)
        except Exception:
            pass

    return JstfScript(
        script_tag=script_tag,
        default_lang_sys=default_lang_sys,
        lang_sys_records=lang_sys_records,
        priority=priority
    )


def _parse_lang_sys(rr: BinaryReader) -> Optional[JstfLangSys]:
    """Parse LangSys table from JSTF table."""
    try:
        req_feature_index = rr.read_u16()
        feature_index_count = rr.read_u16()
    except Exception:
        return None

    feature_indices: list[int] = []

    for _ in range(feature_index_count):
        try:
            feature_indices.append(rr.read_u16())
        except Exception:
            break

    return JstfLangSys(
        req_feature_index=req_feature_index,
        feature_indices=feature_indices
    )


def _parse_lookup_list(rr: BinaryReader, raw: bytes, base_offset: int) -> list[JstfLookup]:
    """Parse LookupList table from JSTF table."""
    try:
        lookup_count = rr.read_u16()
    except Exception:
        return []

    lookups: list[JstfLookup] = []

    for i in range(lookup_count):
        try:
            lookup_offset = rr.read_u16()
        except Exception:
            break

        lookup_table_offset = base_offset + lookup_offset
        if lookup_table_offset >= len(raw):
            break

        try:
            lookup_rr = BinaryReader(raw)
            lookup_rr.seek(lookup_table_offset)
            lookup = _parse_justification_lookup(lookup_rr, raw, lookup_table_offset)
            if lookup:
                lookups.append(lookup)
        except Exception:
            continue

    return lookups


def _parse_justification_lookup(rr: BinaryReader, raw: bytes, base_offset: int) -> Optional[JstfLookup]:
    """Parse JustificationLookup table from JSTF table.

    Since JSTF lookup formats are format-specific and complex, for MVP
    we store the raw data and preserve the format information.
    """
    try:
        format_type = rr.read_u16()
    except Exception:
        return None

    remaining_bytes = len(raw) - rr.tell()
    if remaining_bytes <= 0:
        return None

    lookup_raw = raw[rr.tell():rr.tell() + remaining_bytes]

    return JstfLookup(format=format_type, _raw=lookup_raw)


def _parse_priority_list(rr: BinaryReader, raw: bytes, base_offset: int, count: Optional[int] = None) -> list[JstfPriority]:
    """Parse PriorityList table from JSTF table.
    Args:
        rr: BinaryReader positioned at priority list.
        raw: Raw table bytes for offset resolution.
        base_offset: Base offset for the priority list.
        count: Number of priority records. If None, reads count from stream.
    Returns:
        List of parsed JstfPriority records.
    """
    priority_count = count
    if priority_count is None:
        try:
            priority_count = rr.read_u16()
        except Exception:
            return []

    priorities: list[JstfPriority] = []

    for i in range(priority_count):
        try:
            priority = rr.read_u16()
            extender_count = rr.read_u16()
        except Exception:
            break

        extender_glyphs: list[int] = []
        for j in range(extender_count):
            try:
                glyph = rr.read_u16()
                extender_glyphs.append(glyph)
            except Exception:
                break

        try:
            shrink_count = rr.read_u16()
        except Exception:
            break

        shrinkage_glyphs: list[int] = []
        for j in range(shrink_count):
            try:
                glyph = rr.read_u16()
                shrinkage_glyphs.append(glyph)
            except Exception:
                break

        priorities.append(JstfPriority(
            priority=priority,
            extender_glyphs=extender_glyphs,
            shrinkage_glyphs=shrinkage_glyphs
        ))
    return priorities
