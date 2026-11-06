"""TTF BASE table parser (Baseline table)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from aspose_font._io import BinaryReader

if TYPE_CHECKING:
    from typing import Optional


@dataclass(slots=True)
class _ScriptLangSysRecord:
    """Language system record."""

    lang_sys_tag: str
    baseline_indices: list[int]
    default_baseline: int


@dataclass(slots=True)
class _ScriptRecord:
    """Script record with baseline indices."""

    script_tag: str
    baseline_indices: list[int]
    default_baseline: int
    script_lang_sys: Optional[list[_ScriptLangSysRecord]] = None


@dataclass(slots=True)
class _ScriptList:
    """List of scripts with baseline indices."""

    script_count: int
    scripts: list[_ScriptRecord]


@dataclass(slots=True)
class _BaseAxisTable:
    """Horizontal or vertical baseline axis table."""

    baseline_count: int
    baseline_tags: list[str]
    script_list: _ScriptList


@dataclass
class BaseTable:
    """OpenType BASE (Baseline) table parser."""

    version: int
    horz_base: Optional[_BaseAxisTable] = None
    vert_base: Optional[_BaseAxisTable] = None
    _raw: bytes = field(default_factory=bytes)

    @classmethod
    def from_reader(cls, r: BinaryReader, table_length: int) -> "BaseTable":
        """Parse BASE table from BinaryReader."""
        raw = r.read_bytes(table_length)
        rr = BinaryReader(raw)
        version = rr.read_u32()

        horz_base_offset = rr.read_u32()
        vert_base_offset = rr.read_u32()

        horz_base = None
        if horz_base_offset > 0:
            horz_base = cls._parse_axis_table(rr, horz_base_offset, raw)

        vert_base = None
        if vert_base_offset > 0:
            vert_base = cls._parse_axis_table(rr, vert_base_offset, raw)

        return cls(
            version=version,
            horz_base=horz_base,
            vert_base=vert_base,
            _raw=raw,
        )

    @staticmethod
    def _parse_axis_table(r: BinaryReader, offset: int, raw: bytes) -> _BaseAxisTable | None:
        """Parse a horizontal or vertical baseline axis table."""
        pos = r.tell()
        r.seek(offset)

        if offset < 0 or offset + 8 > len(raw):
            r.seek(pos)
            return None

        try:
            baseline_count = r.read_u16()
            r.read_u16()
            script_list_offset = r.read_u16()

            if offset + baseline_count * 4 + 2 > len(raw):
                r.seek(pos)
                return None

            baseline_tags = []
            for _ in range(baseline_count):
                tag = r.read_tag()
                baseline_tags.append(tag)

            script_list = _parse_script_list(r, script_list_offset, raw)

            r.seek(pos)
            return _BaseAxisTable(
                baseline_count=baseline_count,
                baseline_tags=baseline_tags,
                script_list=script_list,
            )
        except Exception:
            r.seek(pos)
            return None

    def to_bytes(self) -> bytes:
        """Return raw table bytes."""
        return self._raw

    def list_scripts(self) -> list[str]:
        """Return list of script tags in the table.

        Returns:
            List of script tags (e.g., ['DFLT', 'latn', 'cyrl']).
            Returns empty list if script list is not parsed or missing.
        """
        if self.horz_base is None:
            return []
        return [scr.script_tag for scr in self.horz_base.script_list.scripts]

    def list_baseline_tags(self) -> list[str]:
        """Return list of baseline tags.

        Returns:
            List of baseline tags (e.g., ['ROMN', 'HANG']).
            Returns empty list if horizontal axis table is missing.
        """
        if self.horz_base is None:
            return []
        return self.horz_base.baseline_tags

    def get_script(self, script_tag: str) -> _ScriptRecord | None:
        """Return script record for given tag.

        Args:
            script_tag: The script tag to look up (e.g., 'latn').

        Returns:
            ScriptRecord if found, None otherwise.
        """
        if self.horz_base is None:
            return None
        for scr in self.horz_base.script_list.scripts:
            if scr.script_tag == script_tag:
                return scr
        return None

    def list_baseline_tags_for_script(self, script_tag: str) -> list[str]:
        """List baseline tags applicable to a script.

        Args:
            script_tag: The script tag to query (e.g., 'latn').

        Returns:
            List of baseline tags for the script.
            Returns empty list if script or baseline tags missing.
        """
        if self.horz_base is None:
            return []

        script = self.get_script(script_tag)
        if script is None:
            return []

        baseline_tags = self.horz_base.baseline_tags
        result = []
        for idx in script.baseline_indices:
            if 0 <= idx < len(baseline_tags):
                result.append(baseline_tags[idx])
        return result

    def get_default_baseline_for_script(self, script_tag: str) -> str | None:
        """Get the default baseline tag for a script.

        Args:
            script_tag: The script tag to query (e.g., 'latn').

        Returns:
            Default baseline tag, or None if not found.
        """
        if self.horz_base is None:
            return None

        script = self.get_script(script_tag)
        if script is None:
            return None

        baseline_tags = self.horz_base.baseline_tags
        if not script.baseline_indices:
            return None

        default_idx = script.baseline_indices[0]
        if 0 <= default_idx < len(baseline_tags):
            return baseline_tags[default_idx]
        return None


def _parse_script_list(
    r: BinaryReader, offset: int, raw: bytes
) -> _ScriptList:
    """Parse the script list table."""
    pos = r.tell()
    r.seek(offset)

    if offset < 0 or offset + 2 > len(raw):
        r.seek(pos)
        return _ScriptList(script_count=0, scripts=[])

    try:
        script_count = r.read_u16()

        if offset + 2 + script_count * 6 > len(raw):
            r.seek(pos)
            return _ScriptList(script_count=0, scripts=[])

        scripts: list[_ScriptRecord] = []
        for _ in range(script_count):
            script_tag = r.read_tag()
            baseline_count = r.read_u16()
            default_baseline = r.read_u16()

            if offset + 6 + (len(scripts) * 4) + baseline_count * 2 > len(raw):
                r.seek(pos)
                return _ScriptList(script_count=0, scripts=[])

            baseline_indices = [r.read_u16() for _ in range(baseline_count)]

            lang_sys_count = r.read_u16()
            lang_sys_records: list[_ScriptLangSysRecord] = []

            if lang_sys_count > 0:
                if offset + 8 + (script_count * 6) + lang_sys_count * 6 > len(raw):
                    r.seek(pos)
                    return _ScriptList(script_count=0, scripts=[])

                for _ in range(lang_sys_count):
                    lang_sys_tag = r.read_tag()
                    lang_baseline_count = r.read_u16()
                    lang_default_baseline = r.read_u16()
                    lang_baseline_indices = [r.read_u16() for _ in range(lang_baseline_count)]
                    lang_sys_records.append(_ScriptLangSysRecord(
                        lang_sys_tag=lang_sys_tag,
                        baseline_indices=lang_baseline_indices,
                        default_baseline=lang_default_baseline,
                    ))

            scripts.append(_ScriptRecord(
                script_tag=script_tag,
                baseline_indices=baseline_indices,
                default_baseline=default_baseline,
                script_lang_sys=lang_sys_records if lang_sys_records else None,
            ))

        r.seek(pos)
        return _ScriptList(script_count=script_count, scripts=scripts)
    except Exception:
        r.seek(pos)
        return _ScriptList(script_count=0, scripts=[])
