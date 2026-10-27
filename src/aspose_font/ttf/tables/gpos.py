"""TTF GPOS table parser (Glyph Positioning)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from aspose_font._io import BinaryReader
from aspose_font._types import GlyphId, KernPair

if TYPE_CHECKING:
    from typing import Optional


@dataclass(slots=True)
class PairAdjustmentRecord:
    left_glyph_id: GlyphId
    right_glyph_id: GlyphId
    left_value: Optional[int]
    right_value: Optional[int]

    @property
    def x_advance(self) -> int:
        """Return left glyph horizontal advance adjustment (font units)."""
        return self.left_value if self.left_value is not None else 0


@dataclass(slots=True)
class PairSet:
    records: list[PairAdjustmentRecord]


@dataclass(slots=True)
class PairPosFormat1Subtable:
    coverage_offset: int
    value_format1: int
    value_format2: int
    pair_sets: list[PairSet]


@dataclass(slots=True)
class PairPosFormat2Subtable:
    coverage_offset: int
    value_format1: int
    value_format2: int
    class_def1_offset: int
    class_def2_offset: int
    class1_count: int
    class2_count: int
    class1_records: list[list[PairAdjustmentRecord]]


@dataclass(slots=True)
class CoverageTable:
    format: int
    glyph_indices: list[int]
    glyph_range_records: Optional[list[tuple[int, int, int]]] = None


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


@dataclass
class GposTable:
    version: int
    script_list_offset: int
    feature_list_offset: int
    lookup_list_offset: int
    script_list: Optional[list[ScriptTable]] = None
    feature_list: Optional[list[FeatureTable]] = None
    lookup_list: Optional[list[object]] = None
    _raw: bytes = field(default_factory=bytes)

    @classmethod
    def from_reader(cls, r: BinaryReader, table_length: int) -> GposTable:
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

    def get_kern_pairs(self) -> list[KernPair]:
        """Extract kern pairs from GPOS table.

        Returns:
            List of KernPair with left/right glyph IDs and kern value in font units.
            Returns empty list if no pair adjustment kerning found.
        """
        if self.feature_list is None or self.lookup_list is None:
            return []

        kern_feature_tables = [
            ft for ft in self.feature_list if ft.feature_tag == "kern"
        ]

        kern_pairs: list[KernPair] = []

        for ft in kern_feature_tables:
            for lookup_idx in ft.lookup_list_indices:
                if lookup_idx >= len(self.lookup_list):
                    continue
                lookup = self.lookup_list[lookup_idx]
                if isinstance(lookup, PairPosFormat1Subtable):
                    kern_pairs.extend(self._extract_pairs_from_format1(lookup))
                elif isinstance(lookup, PairPosFormat2Subtable):
                    kern_pairs.extend(self._extract_pairs_from_format2(lookup))

        return kern_pairs

    def list_scripts(self) -> list[str]:
        """Return list of script tags defined in the GPOS table.

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
        for tag, offset in self.script_list:
            if tag == script_tag:
                return (tag, offset)
        return None

    def list_features_for_script(self, script_tag: str) -> list[str]:
        """Return feature tags available for a specific script.

        Args:
            script_tag: The script tag to query (e.g., 'latn').

        Returns:
            List of feature tags (e.g., ['kern', 'dist', 'abvm', 'blwm']).
            Returns empty list if script or feature list is missing.
        """
        if self.script_list is None or self.feature_list is None:
            return []
        script_record = self.get_script(script_tag)
        if script_record is None:
            return []
        script_offset = script_record[1]
        feature_tags = []

        script_data = self._raw[script_offset:]
        if len(script_data) < 4:
            return []

        default_lang_sys_offset = int.from_bytes(script_data[0:2], 'big')
        lang_sys_count = int.from_bytes(script_data[2:4], 'big')

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
        """Return all feature tags defined in the GPOS table.

        Returns:
            List of all feature tags (e.g., ['kern', 'dist', 'abvm', 'blwm']).
            Returns empty list if feature list is not parsed or missing.
        """
        if self.feature_list is None:
            return []
        return [ft.feature_tag for ft in self.feature_list]

    def _extract_pairs_from_format1(self, subtable: PairPosFormat1Subtable) -> list[KernPair]:
        """Extract kern pairs from PairPosFormat1 subtable."""
        if subtable.pair_sets is None:
            return []

        coverage = _parse_coverage(BinaryReader(self._raw), subtable.coverage_offset)
        if coverage.format == 1:
            coverage_glyphs = coverage.glyph_indices
        else:
            coverage_glyphs = []

        kern_pairs: list[KernPair] = []

        for set_idx, pair_set in enumerate(subtable.pair_sets):
            if set_idx >= len(coverage_glyphs):
                continue
            left_gid = coverage_glyphs[set_idx]

            for record in pair_set.records:
                kern_value = record.x_advance
                if kern_value != 0:
                    kern_pairs.append(
                        KernPair(
                            left=GlyphId(left_gid),
                            right=record.right_glyph_id,
                            value=kern_value,
                        )
                    )

        return kern_pairs

    def _extract_pairs_from_format2(self, subtable: PairPosFormat2Subtable) -> list[KernPair]:
        """Extract kern pairs from PairPosFormat2 subtable."""
        kern_pairs: list[KernPair] = []

        coverage = _parse_coverage(BinaryReader(self._raw), subtable.coverage_offset)
        if coverage.format == 1:
            coverage_glyphs = coverage.glyph_indices
        else:
            return []

        for class1_idx, class1_records in enumerate(subtable.class1_records):
            for class2_idx, record in enumerate(class1_records):
                if class2_idx >= len(coverage_glyphs):
                    continue
                kern_value = record.x_advance
                if kern_value != 0:
                    kern_pairs.append(
                        KernPair(
                            left=GlyphId(coverage_glyphs[class1_idx]),
                            right=record.right_glyph_id,
                            value=kern_value,
                        )
                    )

        return kern_pairs

    def get_kerning_pair(self, left_gid: GlyphId, right_gid: GlyphId) -> int:
        """Return XAdvance delta for specified glyph pair, or 0 if not defined.

        Args:
            left_gid: Left glyph ID
            right_gid: Right glyph ID

        Returns:
            XAdvance adjustment in font units. Returns 0 if pair not found.
        """
        pairs = self.get_kern_pairs()
        for pair in pairs:
            if int(pair.left) == int(left_gid) and int(pair.right) == int(right_gid):
                return pair.value
        return 0


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


def _parse_script_list(
    r: BinaryReader, offset: int, raw: bytes
) -> Optional[list[tuple[str, int]]]:
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
) -> Optional[list[FeatureTable]]:
    if offset == 0:
        return None
    pos = r.tell()
    r.seek(offset)
    feature_count = r.read_u16()
    features = []
    for i in range(feature_count):
        tag = r.read_tag()
        feature_offset = r.read_u16()
        feature_pos = offset + feature_offset
        current_pos = r.tell()
        r.seek(feature_pos)
        feature_params = r.read_u16()
        lookup_count = r.read_u16()
        remaining = r.remaining()
        needed = lookup_count * 2
        if needed > remaining:
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
        r.seek(current_pos)
    r.seek(pos)
    return features


def _parse_lookup_list(
    r: BinaryReader, offset: int, raw: bytes
) -> Optional[list[object]]:
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

    lookup_list: list[object] = []
    for lookup_offset in lookup_offsets:
        if lookup_offset == 0:
            continue

        lookup_offset_abs = offset + lookup_offset
        if lookup_offset_abs >= len(raw):
            continue

        try:
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

                try:
                    sub_r2 = BinaryReader(raw)
                    sub_r2.seek(sub_offset_abs)
                    fmt = sub_r2.read_u16()
                    coverage_offset = sub_r2.read_u16()

                    if lookup_type == 2:
                        if fmt == 1:
                            value_format1 = sub_r2.read_u16()
                            value_format2 = sub_r2.read_u16()
                            pair_set_count = sub_r2.read_u16()
                            pair_set_offsets = [
                                sub_r2.read_u16() for _ in range(pair_set_count)
                            ]

                            pair_sets: list[PairSet] = []
                            for pair_set_offset in pair_set_offsets:
                                if pair_set_offset == 0:
                                    continue
                                pair_r = BinaryReader(raw)
                                pair_r.seek(offset + pair_set_offset)
                                pair_count = pair_r.read_u16()
                                records = []
                                for _ in range(pair_count):
                                    right_glyph_id = GlyphId(pair_r.read_u16())
                                    if value_format1 & 0x0001:
                                        left_x_advance = pair_r.read_i16()
                                    else:
                                        left_x_advance = None
                                    if value_format2 & 0x0001:
                                        right_x_advance = pair_r.read_i16()
                                    else:
                                        right_x_advance = None
                                    records.append(
                                        PairAdjustmentRecord(
                                            left_glyph_id=GlyphId(0),
                                            right_glyph_id=right_glyph_id,
                                            left_value=left_x_advance,
                                            right_value=right_x_advance,
                                        )
                                    )
                                pair_sets.append(PairSet(records=records))

                            lookup_list.append(
                                PairPosFormat1Subtable(
                                    coverage_offset=coverage_offset,
                                    value_format1=value_format1,
                                    value_format2=value_format2,
                                    pair_sets=pair_sets,
                                )
                            )
                        elif fmt == 2:
                            value_format1 = sub_r2.read_u16()
                            value_format2 = sub_r2.read_u16()
                            class_def1_offset = sub_r2.read_u16()
                            class_def2_offset = sub_r2.read_u16()
                            class1_count = sub_r2.read_u16()
                            class2_count = sub_r2.read_u16()

                            class1_records: list[list[PairAdjustmentRecord]] = []
                            for _ in range(class1_count):
                                class2_records = []
                                for _ in range(class2_count):
                                    if value_format1 & 0x0001:
                                        left_x_advance = sub_r2.read_i16()
                                    else:
                                        left_x_advance = None
                                    if value_format2 & 0x0001:
                                        right_x_advance = sub_r2.read_i16()
                                    else:
                                        right_x_advance = None
                                    class2_records.append(
                                        PairAdjustmentRecord(
                                            left_glyph_id=GlyphId(0),
                                            right_glyph_id=GlyphId(0),
                                            left_value=left_x_advance,
                                            right_value=right_x_advance,
                                        )
                                    )
                                class1_records.append(class2_records)

                            lookup_list.append(
                                PairPosFormat2Subtable(
                                    coverage_offset=coverage_offset,
                                    value_format1=value_format1,
                                    value_format2=value_format2,
                                    class_def1_offset=class_def1_offset,
                                    class_def2_offset=class_def2_offset,
                                    class1_count=class1_count,
                                    class2_count=class2_count,
                                    class1_records=class1_records,
                                )
                            )
                except Exception:
                    continue
        except Exception:
            continue

    r.seek(pos)
    return lookup_list
