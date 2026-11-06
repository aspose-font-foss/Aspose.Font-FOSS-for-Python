"""TTF GSUB table parser (Glyph Substitution)."""

from __future__ import annotations

from dataclasses import dataclass, field

from aspose_font._io import BinaryReader
from aspose_font._types import GlyphId


@dataclass(slots=True)
class SubstitutionSubtable:
    format: int
    coverage_offset: int


@dataclass(slots=True)
class SingleSubstitutionFormat1(SubstitutionSubtable):
    coverage_offset: int
    delta_glyph_id: int


@dataclass(slots=True)
class SingleSubstitutionFormat2(SubstitutionSubtable):
    coverage_offset: int
    substitution_count: int
    substitute_glyph_ids: list[int]


@dataclass(slots=True)
class LigatureSubstitutionFormat1(SubstitutionSubtable):
    coverage_offset: int
    ligature_set_count: int
    ligature_set_offsets: list[int]


@dataclass(slots=True)
class LigatureSet:
    ligature_count: int
    ligature_offsets: list[int]


@dataclass(slots=True)
class Ligature:
    component_glyph_ids: list[int]
    ligature_glyph_id: int


@dataclass(slots=True)
class CoverageTable:
    format: int
    glyph_indices: list[int]
    glyph_range_records: list[tuple[int, int, int]] | None = None


@dataclass(slots=True)
class FeatureTable:
    feature_tag: str
    feature_params_offset: int
    lookup_index_count: int
    lookup_list_indices: list[int]


@dataclass(slots=True)
class ScriptTable:
    default_lang_sys_offset: int
    lang_sys_count: int
    lang_sys_records: list[tuple[str, int]]


@dataclass(slots=True)
class LangSysTable:
    req_feature_index: int
    feature_index_count: int
    feature_indices: list[int]


def _parse_coverage(r: BinaryReader, offset: int) -> CoverageTable:
    pos = r.tell()
    r.seek(offset)
    fmt = r.read_u16()
    if fmt == 1:
        glyph_count = r.read_u16()
        glyph_indices = [r.read_u16() for _ in range(glyph_count)]
        r.seek(pos)
        return CoverageTable(format=fmt, glyph_indices=glyph_indices)
    elif fmt == 2:
        range_count = r.read_u16()
        glyph_range_records: list[tuple[int, int, int]] = []
        for _ in range(range_count):
            start = r.read_u16()
            end = r.read_u16()
            start_index = r.read_u16()
            glyph_range_records.append((start, end, start_index))
        r.seek(pos)
        return CoverageTable(
            format=fmt, glyph_indices=[], glyph_range_records=glyph_range_records
        )
    else:
        r.seek(pos)
        raise ValueError(f"Unknown coverage format: {fmt}")


def _parse_ligature(r: BinaryReader, offset: int) -> Ligature:
    pos = r.tell()
    r.seek(offset)
    component_glyph_ids = []
    ligature_glyph_id = r.read_u16()
    component_count = r.read_u16()
    for _ in range(component_count - 1):
        component_glyph_ids.append(r.read_u16())
    r.seek(pos)
    return Ligature(
        component_glyph_ids=component_glyph_ids, ligature_glyph_id=ligature_glyph_id
    )


def _parse_ligature_set(r: BinaryReader, offset: int) -> LigatureSet:
    pos = r.tell()
    r.seek(offset)
    ligature_count = r.read_u16()
    ligature_offsets = [r.read_u16() for _ in range(ligature_count)]
    r.seek(pos)
    return LigatureSet(
        ligature_count=ligature_count, ligature_offsets=ligature_offsets
    )


def _parse_script_list(
    r: BinaryReader, offset: int, raw: bytes
) -> list[tuple[str, int]] | None:
    if offset == 0:
        return None
    pos = r.tell()
    script_r = BinaryReader(raw)
    script_r.seek(offset)
    script_count = script_r.read_u16()
    scripts = []
    for _ in range(script_count):
        tag = script_r.read_tag()
        script_offset = script_r.read_u16()
        scripts.append((tag, script_offset))
    r.seek(pos)
    return scripts


def _parse_feature_list(
    r: BinaryReader, offset: int
) -> list[FeatureTable] | None:
    if offset == 0:
        return None
    pos = r.tell()
    r.seek(offset)
    feature_count = r.read_u16()
    features = []
    for i in range(feature_count):
        tag = r.read_tag()
        feature_offset = r.read_u16()
        # feature_offset is relative to the start of the FeatureList
        feature_pos = offset + feature_offset
        # Save current position and seek to feature table
        current_pos = r.tell()
        r.seek(feature_pos)
        feature_params = r.read_u16()
        lookup_count = r.read_u16()
        # Check if we have enough data for lookup indices
        remaining = r.remaining()
        needed = lookup_count * 2
        if needed > remaining:
            # Not enough data, use what's available or stop
            lookup_count = min(lookup_count, remaining // 2)
        lookup_indices = [r.read_u16() for _ in range(lookup_count)]
        features.append(
            FeatureTable(
                feature_tag=tag,
                feature_params_offset=feature_params,
                lookup_index_count=lookup_count,
                lookup_list_indices=lookup_indices,
            )
        )
        # Restore position
        r.seek(current_pos)
    r.seek(pos)
    return features


def _parse_lookup_list(
    r: BinaryReader, offset: int, raw: bytes
) -> list[SubstitutionSubtable] | None:
    if offset == 0:
        return None
    pos = r.tell()
    r.seek(offset)
    lookup_count = r.read_u16()

    if lookup_count > 1000:
        r.seek(pos)
        return None

    lookup_offsets = []
    for _ in range(lookup_count):
        lookup_offsets.append(r.read_u16())

    substitution_subtables: list[SubstitutionSubtable] = []
    for lookup_offset in lookup_offsets:
        if lookup_offset == 0:
            continue

        lookup_offset_abs = offset + lookup_offset
        if lookup_offset_abs >= len(raw):
            continue

        sub_r = BinaryReader(raw)
        sub_r.seek(lookup_offset_abs)
        lookup_type = sub_r.read_u16()
        subtable_count = sub_r.read_u16()

        if subtable_count > 500:
            continue

        subtable_offsets = []
        for _ in range(subtable_count):
            subtable_offsets.append(sub_r.read_u16())

        for sub_offset in subtable_offsets:
            if sub_offset == 0:
                continue

            sub_offset_abs = offset + sub_offset
            if sub_offset_abs >= len(raw):
                continue

            sub_r2 = BinaryReader(raw)
            sub_r2.seek(sub_offset_abs)
            fmt = sub_r2.read_u16()
            coverage_offset = sub_r2.read_u16()

            if lookup_type == 1:
                if fmt == 1:
                    delta = sub_r2.read_i16()
                    substitution_subtables.append(
                        SingleSubstitutionFormat1(
                            format=fmt, coverage_offset=coverage_offset, delta_glyph_id=delta
                        )
                    )
                elif fmt == 2:
                    if sub_r2.remaining() < 2:
                        continue
                    sub_count = sub_r2.read_u16()
                    if sub_count > 10000:
                        continue
                    needed = sub_count * 2
                    if sub_r2.remaining() < needed:
                        continue
                    sub_ids = [sub_r2.read_u16() for _ in range(sub_count)]
                    substitution_subtables.append(
                        SingleSubstitutionFormat2(
                            format=fmt, coverage_offset=coverage_offset, substitution_count=sub_count, substitute_glyph_ids=sub_ids
                        )
                    )
            elif lookup_type == 4:
                if fmt == 1:
                    if sub_r2.remaining() < 2:
                        continue
                    lig_set_count = sub_r2.read_u16()
                    if lig_set_count > 1000:
                        continue
                    needed = lig_set_count * 2
                    if sub_r2.remaining() < needed:
                        continue
                    lig_set_offsets = [sub_r2.read_u16() for _ in range(lig_set_count)]
                    substitution_subtables.append(
                        LigatureSubstitutionFormat1(
                            format=fmt, coverage_offset=coverage_offset, ligature_set_count=lig_set_count, ligature_set_offsets=lig_set_offsets
                        )
                    )

    r.seek(pos)
    return substitution_subtables


def _parse_lang_sys(r: BinaryReader, offset: int) -> LangSysTable | None:
    if offset == 0:
        return None
    pos = r.tell()
    r.seek(offset)
    req_feature_index = r.read_u16()
    feature_index_count = r.read_u16()
    feature_indices = [r.read_u16() for _ in range(feature_index_count)]
    r.seek(pos)
    return LangSysTable(
        req_feature_index=req_feature_index,
        feature_index_count=feature_index_count,
        feature_indices=feature_indices,
    )


def _get_script_by_tag(script_list: list[tuple[str, int]], script_tag: str) -> tuple[str, int] | None:
    for tag, offset in script_list:
        if tag == script_tag:
            return (tag, offset)
    return None


def _get_script_by_tag(scripts: list[tuple[str, int]], tag: str) -> tuple[str, int] | None:
    """Helper to find script record by tag."""
    for script_tag, offset in scripts:
        if script_tag == tag:
            return (script_tag, offset)
    return None


@dataclass
class GsubTable:
    version: int
    script_list_offset: int
    feature_list_offset: int
    lookup_list_offset: int
    script_list: list[ScriptTable] | None = None
    feature_list: list[FeatureTable] | None = None
    lookup_list: list[SubstitutionSubtable] | None = None
    _raw: bytes = field(default_factory=bytes)

    @classmethod
    def from_reader(cls, r: BinaryReader, table_length: int) -> GsubTable:
        raw = r.read_bytes(table_length)
        rr = BinaryReader(raw)
        version = rr.read_u32()
        script_list_offset = rr.read_u16()
        feature_list_offset = rr.read_u16()
        lookup_list_offset = rr.read_u16()

        script_list = _parse_script_list(rr, script_list_offset, raw)
        feature_list = _parse_feature_list(rr, feature_list_offset)
        lookup_list = _parse_lookup_list(rr, lookup_list_offset, raw)

        return cls(
            version=version,
            script_list_offset=script_list_offset,
            feature_list_offset=feature_list_offset,
            lookup_list_offset=lookup_list_offset,
            script_list=script_list,
            feature_list=feature_list,
            lookup_list=lookup_list,
            _raw=raw,
        )

    def to_bytes(self) -> bytes:
        return self._raw

    def list_scripts(self) -> list[str]:
        """Return list of script tags defined in the GSUB table.

        Returns:
            List of script tags (e.g., ['DFLT', 'latn', 'cyrl']).
            Returns empty list if script list is not parsed or missing.
        """
        if self.script_list is None:
            return []
        return [tag for tag, _ in self.script_list]

    def get_script(self, script_tag: str) -> tuple[str, int] | None:
        """Return script record for given tag.

        Args:
            script_tag: The script tag to look up (e.g., 'latn').

        Returns:
            Tuple of (tag, offset) if found, None otherwise.
        """
        if self.script_list is None:
            return None
        return _get_script_by_tag(self.script_list, script_tag)

    def list_features_for_script(self, script_tag: str) -> list[str]:
        """Return feature tags available for a specific script.

        Args:
            script_tag: The script tag to query (e.g., 'latn').

        Returns:
            List of feature tags (e.g., ['liga', 'clig', 'smcp']).
            Returns empty list if script or feature list is missing.
        """
        if self.script_list is None or self.feature_list is None:
            return []
        script_record = self.get_script(script_tag)
        if script_record is None:
            return []
        script_offset = script_record[1]
        feature_tags = []

        # Parse the ScriptTable at the offset
        script_data = self._raw[script_offset:]
        if len(script_data) < 4:
            return []

        default_lang_sys_offset = int.from_bytes(script_data[0:2], 'big')
        lang_sys_count = int.from_bytes(script_data[2:4], 'big')

        # Parse default lang sys
        if default_lang_sys_offset > 0 and default_lang_sys_offset < len(script_data):
            lang_sys_data = script_data[default_lang_sys_offset:]
            if len(lang_sys_data) >= 4:
                feature_index_count = int.from_bytes(lang_sys_data[2:4], 'big')
                for i in range(feature_index_count):
                    idx_start = 4 + i * 2
                    if idx_start + 2 <= len(lang_sys_data):
                        feat_idx = int.from_bytes(lang_sys_data[idx_start:idx_start+2], 'big')
                        if feat_idx < len(self.feature_list):
                            feature_tags.append(self.feature_list[feat_idx].feature_tag)

        # Parse language system records
        for i in range(lang_sys_count):
            record_start = 4 + i * 6
            if record_start + 6 > len(script_data):
                break
            lang_offset = int.from_bytes(script_data[record_start+4:record_start+6], 'big')
            if lang_offset > 0 and lang_offset < len(script_data):
                lang_sys_data = script_data[lang_offset:]
                if len(lang_sys_data) >= 4:
                    feature_index_count = int.from_bytes(lang_sys_data[2:4], 'big')
                    for j in range(feature_index_count):
                        idx_start = 4 + j * 2
                        if idx_start + 2 <= len(lang_sys_data):
                            feat_idx = int.from_bytes(lang_sys_data[idx_start:idx_start+2], 'big')
                            if feat_idx < len(self.feature_list):
                                tag = self.feature_list[feat_idx].feature_tag
                                if tag not in feature_tags:
                                    feature_tags.append(tag)

        return feature_tags

    def list_all_features(self) -> list[str]:
        """Return all feature tags defined in the GSUB table.

        Returns:
            List of all feature tags (e.g., ['liga', 'clig', 'smcp', 'ss01']).
            Returns empty list if feature list is not parsed or missing.
        """
        if self.feature_list is None:
            return []
        return [ft.feature_tag for ft in self.feature_list]

    def get_ligatures(self, feature_tag: str = "liga") -> dict[tuple[GlyphId, ...], GlyphId]:
        """Return ligature substitutions for a specific feature.

        Args:
            feature_tag: The feature to query (default: 'liga').

        Returns:
            Mapping from input glyph sequence to output glyph ID.
            Only supports LigatureSubstitutionFormat1 lookup type.
            Returns empty dict if feature or lookup list is missing.
        """
        feature_ligatures: dict[tuple[GlyphId, ...], GlyphId] = {}

        if self.feature_list is None or self.lookup_list is None:
            return feature_ligatures

        feature_tables = [
            ft for ft in self.feature_list if ft.feature_tag == feature_tag
        ]

        lookup_indices: list[int] = []
        for ft in feature_tables:
            lookup_indices.extend(ft.lookup_list_indices)

        for lookup_idx in lookup_indices:
            if lookup_idx >= len(self.lookup_list):
                continue
            lookup = self.lookup_list[lookup_idx]
            if not isinstance(lookup, LigatureSubstitutionFormat1):
                continue

            coverage = _parse_coverage(BinaryReader(self._raw), lookup.coverage_offset)
            coverage_glyphs = [GlyphId(gid) for gid in coverage.glyph_indices]

            for set_idx, offset in enumerate(lookup.ligature_set_offsets):
                if offset == 0:
                    continue
                ligature_set = _parse_ligature_set(
                    BinaryReader(self._raw), offset
                )

                for lig_idx, lig_offset in enumerate(ligature_set.ligature_offsets):
                    if lig_offset == 0:
                        continue
                    ligature = _parse_ligature(
                        BinaryReader(self._raw), lig_offset
                    )

                    input_gids = [coverage_glyphs[set_idx]]
                    input_gids.extend(ligature.component_glyph_ids)
                    input_seq = tuple(GlyphId(gid) for gid in input_gids)
                    feature_ligatures[input_seq] = GlyphId(ligature.ligature_glyph_id)

        return feature_ligatures

    def get_single_substitutions(
        self, feature_tag: str | None = None
    ) -> dict[GlyphId, GlyphId]:
        """Return single substitution mappings for specified feature(s).

        Args:
            feature_tag: Optional feature tag to filter by. If None, returns
                substitutions from all features.

        Returns:
            Mapping from input glyph ID to output glyph ID.
            Supports both SingleSubstitutionFormat1 and Format2 lookup types.
            Returns empty dict if feature or lookup list is missing.
        """
        single_subs: dict[GlyphId, GlyphId] = {}

        if self.feature_list is None or self.lookup_list is None:
            return single_subs

        feature_tables = self.feature_list
        if feature_tag is not None:
            feature_tables = [
                ft for ft in self.feature_list if ft.feature_tag == feature_tag
            ]

        lookup_indices: list[int] = []
        for ft in feature_tables:
            lookup_indices.extend(ft.lookup_list_indices)

        for lookup_idx in lookup_indices:
            if lookup_idx >= len(self.lookup_list):
                continue
            lookup = self.lookup_list[lookup_idx]

            if isinstance(lookup, SingleSubstitutionFormat1):
                coverage = _parse_coverage(
                    BinaryReader(self._raw), lookup.coverage_offset
                )
                for gid in coverage.glyph_indices:
                    new_gid = gid + lookup.delta_glyph_id
                    single_subs[GlyphId(gid)] = GlyphId(new_gid)

            elif isinstance(lookup, SingleSubstitutionFormat2):
                coverage = _parse_coverage(
                    BinaryReader(self._raw), lookup.coverage_offset
                )
                for i, gid in enumerate(coverage.glyph_indices):
                    if i < len(lookup.substitute_glyph_ids):
                        single_subs[GlyphId(gid)] = GlyphId(lookup.substitute_glyph_ids[i])

        return single_subs
