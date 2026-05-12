"""Font subsetting helpers (SPEC-016 / ADR-012)."""

from __future__ import annotations

import copy
import dataclasses
import struct
from collections.abc import Iterable

from aspose_font._exceptions import FontNotSupportedException
from aspose_font._font_base import Font
from aspose_font._io import BinaryReader
from aspose_font.cff.charset import CffCharset
from aspose_font.cff.encoding import CffEncoding
from aspose_font.cff.font import CffFont
from aspose_font.cff.index import CffIndex
from aspose_font.converter import FontConverter
from aspose_font.loader import FontLoader
from aspose_font.serializer import CffSerializer, TtfSerializer
from aspose_font.subset_presets import (
    available_subset_presets,
    codepoints_for_presets,
    expand_unicode_ranges,
)
from aspose_font.ttf.font import TtfFont
from aspose_font.ttf.tables import GlyfTable, HmtxTable, LocaTable, PostTable, TtfTableSet
from aspose_font.ttf.tables.cmap import CmapSubtable, CmapTable
from aspose_font.ttf.tables.hmtx import HMetric
from aspose_font.type1.afm import AfmData
from aspose_font.type1.font import Type1Font
from aspose_font.woff.woff1 import WoffFont
from aspose_font.woff.woff2 import Woff2Font

_MISSING_SAMPLE_LIMIT = 12

_TABLES_TO_DROP = {
    "BASE",
    "GDEF",
    "GPOS",
    "GSUB",
    "JSTF",
    "HVAR",
    "MVAR",
    "VVAR",
    "STAT",
    "avar",
    "cvar",
    "fvar",
    "gvar",
    "kern",
}


@dataclasses.dataclass(frozen=True, slots=True)
class CoverageGroup:
    """Coverage diagnostics for one request source such as a preset, text, or range."""

    kind: str
    label: str
    requested_codepoints: tuple[int, ...]
    covered_codepoints: tuple[int, ...]
    missing_codepoints: tuple[int, ...]

    @property
    def requested_count(self) -> int:
        return len(self.requested_codepoints)

    @property
    def covered_count(self) -> int:
        return len(self.covered_codepoints)

    @property
    def missing_count(self) -> int:
        return len(self.missing_codepoints)

    @property
    def fully_covered(self) -> bool:
        return self.missing_count == 0

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": self.kind,
            "label": self.label,
            "requested_count": self.requested_count,
            "covered_count": self.covered_count,
            "missing_count": self.missing_count,
            "fully_covered": self.fully_covered,
            "requested_codepoints": list(self.requested_codepoints),
            "covered_codepoints": list(self.covered_codepoints),
            "missing_codepoints": list(self.missing_codepoints),
        }

    def summary_dict(self) -> dict[str, object]:
        return {
            "kind": self.kind,
            "label": self.label,
            "requested_count": self.requested_count,
            "covered_count": self.covered_count,
            "missing_count": self.missing_count,
            "fully_covered": self.fully_covered,
            "missing_codepoints_sample": list(self.missing_codepoints[:_MISSING_SAMPLE_LIMIT]),
        }


@dataclasses.dataclass(frozen=True, slots=True)
class SubsetCoverage:
    """Aggregate Unicode coverage diagnostics for a subsetting request."""

    requested_codepoints: tuple[int, ...]
    covered_codepoints: tuple[int, ...]
    missing_codepoints: tuple[int, ...]
    retained_gids: tuple[int, ...]
    groups: tuple[CoverageGroup, ...] = ()

    @property
    def requested_count(self) -> int:
        return len(self.requested_codepoints)

    @property
    def covered_count(self) -> int:
        return len(self.covered_codepoints)

    @property
    def missing_count(self) -> int:
        return len(self.missing_codepoints)

    @property
    def fully_covered(self) -> bool:
        return self.missing_count == 0

    def to_dict(self) -> dict[str, object]:
        return {
            "requested_count": self.requested_count,
            "covered_count": self.covered_count,
            "missing_count": self.missing_count,
            "fully_covered": self.fully_covered,
            "requested_codepoints": list(self.requested_codepoints),
            "covered_codepoints": list(self.covered_codepoints),
            "missing_codepoints": list(self.missing_codepoints),
            "retained_gids": list(self.retained_gids),
            "groups": [group.to_dict() for group in self.groups],
        }

    def summary_dict(self) -> dict[str, object]:
        return {
            "requested_count": self.requested_count,
            "covered_count": self.covered_count,
            "missing_count": self.missing_count,
            "fully_covered": self.fully_covered,
            "missing_codepoints_sample": list(self.missing_codepoints[:_MISSING_SAMPLE_LIMIT]),
            "groups": [group.summary_dict() for group in self.groups],
        }


@dataclasses.dataclass(frozen=True, slots=True)
class SubsetResult:
    """Subsetting output bundled with the coverage report used to produce it."""

    font: Font
    coverage: SubsetCoverage


class FontSubsetter:
    @staticmethod
    def available_presets() -> tuple[str, ...]:
        return available_subset_presets()

    @classmethod
    def subset(cls, font: Font, codepoints: set[int]) -> Font:
        retained = cls._resolve_codepoints_to_gids(font, codepoints)
        return cls._subset_by_retained(font, retained)

    @classmethod
    def subset_by_text(cls, font: Font, text: str) -> Font:
        return cls.subset(font, {ord(ch) for ch in text})

    @classmethod
    def subset_by_gids(cls, font: Font, gids: set[int]) -> Font:
        retained = {0}
        retained.update(gid for gid in gids if 0 <= gid < font.num_glyphs)
        return cls._subset_by_retained(font, retained)

    @classmethod
    def subset_by_presets(cls, font: Font, presets: str | Iterable[str]) -> Font:
        return cls.subset(font, cls._codepoints_from_presets(presets))

    @classmethod
    def subset_for_web(
        cls,
        font: Font,
        *,
        presets: str | Iterable[str] = (),
        text: str = "",
        codepoints: Iterable[int] = (),
        ranges: Iterable[tuple[int, int] | range] = (),
    ) -> Font:
        resolved = cls.resolve_codepoints(
            presets=presets,
            text=text,
            codepoints=codepoints,
            ranges=ranges,
        )
        return cls.subset(font, resolved)

    @classmethod
    def subset_with_coverage(cls, font: Font, codepoints: set[int]) -> SubsetResult:
        """Subset by codepoints and return both the new font and coverage diagnostics."""

        coverage = cls.analyze_coverage(font, codepoints)
        return SubsetResult(cls._subset_by_retained(font, set(coverage.retained_gids)), coverage)

    @classmethod
    def subset_for_web_with_coverage(
        cls,
        font: Font,
        *,
        presets: str | Iterable[str] = (),
        text: str = "",
        codepoints: Iterable[int] = (),
        ranges: Iterable[tuple[int, int] | range] = (),
    ) -> SubsetResult:
        """Subset from web selection inputs and include grouped coverage diagnostics.

        Example:
            >>> font = FontLoader.open("Roboto.ttf")
            >>> result = FontSubsetter.subset_for_web_with_coverage(
            ...     font,
            ...     presets=("latin",),
            ...     text="Hello",
            ... )
            >>> result.coverage.fully_covered
            True
        """

        coverage = cls.analyze_web_coverage(
            font,
            presets=presets,
            text=text,
            codepoints=codepoints,
            ranges=ranges,
        )
        return SubsetResult(cls._subset_by_retained(font, set(coverage.retained_gids)), coverage)

    @classmethod
    def analyze_coverage(
        cls,
        font: Font,
        codepoints: Iterable[int],
        *,
        groups: Iterable[CoverageGroup] = (),
    ) -> SubsetCoverage:
        """Report which requested Unicode codepoints the font can encode."""

        requested = cls._normalize_codepoints(codepoints)
        covered, missing, retained = cls._coverage_for_codepoints(font, requested)
        return SubsetCoverage(
            requested_codepoints=requested,
            covered_codepoints=covered,
            missing_codepoints=missing,
            retained_gids=retained,
            groups=tuple(groups),
        )

    @classmethod
    def analyze_web_coverage(
        cls,
        font: Font,
        *,
        presets: str | Iterable[str] = (),
        text: str = "",
        codepoints: Iterable[int] = (),
        ranges: Iterable[tuple[int, int] | range] = (),
    ) -> SubsetCoverage:
        """Report coverage for combined preset, text, codepoint, and range inputs."""

        groups: list[CoverageGroup] = []
        preset_names = cls._normalize_presets(presets)
        for preset in preset_names:
            groups.append(
                cls._build_coverage_group(
                    font,
                    kind="preset",
                    label=preset,
                    codepoints=codepoints_for_presets((preset,)),
                )
            )

        if text:
            groups.append(
                cls._build_coverage_group(
                    font,
                    kind="text",
                    label="text",
                    codepoints=(ord(ch) for ch in text),
                )
            )

        explicit_codepoints = tuple(codepoints)
        if explicit_codepoints:
            groups.append(
                cls._build_coverage_group(
                    font,
                    kind="codepoints",
                    label="codepoints",
                    codepoints=explicit_codepoints,
                )
            )

        for item in tuple(ranges):
            range_codepoints = expand_unicode_ranges([item])
            groups.append(
                cls._build_coverage_group(
                    font,
                    kind="range",
                    label=cls._range_label(item),
                    codepoints=range_codepoints,
                )
            )

        aggregate = cls._normalize_codepoints(
            cp for group in groups for cp in group.requested_codepoints
        )
        return cls.analyze_coverage(font, aggregate, groups=groups)

    @classmethod
    def resolve_codepoints(
        cls,
        *,
        presets: str | Iterable[str] = (),
        text: str = "",
        codepoints: Iterable[int] = (),
        ranges: Iterable[tuple[int, int] | range] = (),
    ) -> set[int]:
        resolved = set(int(cp) for cp in codepoints)
        resolved.update(ord(ch) for ch in text)
        if presets:
            resolved.update(cls._codepoints_from_presets(presets))
        if ranges:
            resolved.update(expand_unicode_ranges(list(ranges)))
        return resolved

    @staticmethod
    def _normalize_presets(presets: str | Iterable[str]) -> tuple[str, ...]:
        if isinstance(presets, str):
            return (presets,) if presets else ()
        return tuple(str(value) for value in presets)

    @staticmethod
    def _normalize_codepoints(codepoints: Iterable[int]) -> tuple[int, ...]:
        return tuple(sorted({int(cp) for cp in codepoints}))

    @classmethod
    def _build_coverage_group(
        cls,
        font: Font,
        *,
        kind: str,
        label: str,
        codepoints: Iterable[int],
    ) -> CoverageGroup:
        requested = cls._normalize_codepoints(codepoints)
        covered, missing, _ = cls._coverage_for_codepoints(font, requested)
        return CoverageGroup(
            kind=kind,
            label=label,
            requested_codepoints=requested,
            covered_codepoints=covered,
            missing_codepoints=missing,
        )

    @staticmethod
    def _range_label(item: tuple[int, int] | range) -> str:
        if isinstance(item, range):
            start = int(item.start)
            end = int(item.stop) - 1
        else:
            start = int(item[0])
            end = int(item[1])
        return f"U+{start:04X}-U+{end:04X}"

    @staticmethod
    def _coverage_for_codepoints(
        font: Font,
        codepoints: Iterable[int],
    ) -> tuple[tuple[int, ...], tuple[int, ...], tuple[int, ...]]:
        covered: list[int] = []
        missing: list[int] = []
        retained = {0}
        try:
            available_codepoints = set(font.encoding.get_all_codepoints())
        except Exception:
            available_codepoints = None
        for cp in codepoints:
            if available_codepoints is not None and cp not in available_codepoints:
                missing.append(cp)
                continue
            try:
                gid = int(font.encoding.unicode_to_gid(cp))
            except Exception:
                missing.append(cp)
                continue
            if 0 <= gid < font.num_glyphs:
                covered.append(cp)
                retained.add(gid)
            else:
                missing.append(cp)
        return tuple(covered), tuple(missing), tuple(sorted(retained))

    @staticmethod
    def _codepoints_from_presets(presets: str | Iterable[str]) -> set[int]:
        return codepoints_for_presets(FontSubsetter._normalize_presets(presets))

    @staticmethod
    def _resolve_codepoints_to_gids(font: Font, codepoints: set[int]) -> set[int]:
        retained = {0}
        for cp in codepoints:
            try:
                retained.add(int(font.encoding.unicode_to_gid(cp)))
            except Exception:
                continue
        return retained

    @classmethod
    def _subset_by_retained(cls, font: Font, retained: set[int]) -> Font:
        sorted_old_gids = sorted(retained)

        if isinstance(font, TtfFont):
            return cls._subset_ttf(font, sorted_old_gids)
        if isinstance(font, CffFont):
            return cls._subset_cff(font, sorted_old_gids)
        if isinstance(font, WoffFont):
            subset_inner = cls._subset_ttf(font.inner_font, sorted_old_gids)
            return FontConverter.convert(subset_inner, font.font_type)
        if isinstance(font, Woff2Font):
            subset_inner = cls._subset_ttf(font.inner_font, sorted_old_gids)
            return FontConverter.convert(subset_inner, font.font_type)
        if isinstance(font, Type1Font):
            return cls._subset_type1(font, sorted_old_gids)
        raise FontNotSupportedException(f"Subsetting not supported for {type(font).__name__}")

    @classmethod
    def _subset_ttf(cls, font: TtfFont, sorted_old_gids: list[int]) -> Font:
        tables = font.ttf_tables
        if (
            tables.head is None
            or tables.hhea is None
            or tables.maxp is None
            or tables.cmap is None
            or tables.loca is None
            or tables.hmtx is None
            or tables.glyf is None
        ):
            raise FontNotSupportedException("TTF subsetting requires head/hhea/maxp/cmap/loca/hmtx/glyf")

        gid_map = {old: new for new, old in enumerate(sorted_old_gids)}
        new_count = len(sorted_old_gids)

        glyf_chunks: list[bytes] = []
        new_loca_offsets = [0]
        cursor = 0
        for old_gid in sorted_old_gids:
            glyph_offset = tables.loca.glyph_offset(old_gid)
            glyph_length = tables.loca.glyph_length(old_gid)
            blob = tables.glyf.get_glyph_bytes(glyph_offset, glyph_length)
            if len(blob) >= 2 and struct.unpack_from(">h", blob, 0)[0] < 0:
                blob = cls._remap_composite(blob, gid_map)
            pad = (4 - len(blob) % 4) % 4
            blob = blob + (b"\x00" * pad)
            glyf_chunks.append(blob)
            cursor += len(blob)
            new_loca_offsets.append(cursor)

        new_cmap = CmapTable(
            subtables=[
                CmapSubtable(
                    platform_id=sub.platform_id,
                    encoding_id=sub.encoding_id,
                    format=sub.format,
                    _mapping={
                        cp: gid_map[old_gid]
                        for cp, old_gid in sub._mapping.items()
                        if old_gid in gid_map
                    },
                )
                for sub in tables.cmap.subtables
            ],
            _raw=tables.cmap._raw,
        )
        new_post_raw = cls._make_post_v3(tables.post)
        new_post = PostTable.from_reader(BinaryReader(new_post_raw), len(new_post_raw))
        new_tables = TtfTableSet(
            head=copy.deepcopy(tables.head),
            hhea=dataclasses.replace(tables.hhea, number_of_hmetrics=new_count),
            maxp=dataclasses.replace(tables.maxp, num_glyphs=new_count),
            os2=copy.deepcopy(tables.os2),
            name=copy.deepcopy(tables.name),
            post=new_post,
            cmap=new_cmap,
            loca=LocaTable(offsets=new_loca_offsets),
            hmtx=HmtxTable(
                metrics=[
                    HMetric(
                        advance_width=tables.hmtx.metrics[old_gid].advance_width,
                        lsb=tables.hmtx.metrics[old_gid].lsb,
                    )
                    for old_gid in sorted_old_gids
                ]
            ),
            kern=None,
            glyf=GlyfTable(_data=b"".join(glyf_chunks)),
            fvar=None,
            _raw={tag: data for tag, data in tables._raw.items() if tag not in _TABLES_TO_DROP},
        )
        subset_font = TtfFont(
            sfnt_data=b"",
            tables=new_tables,
            sfnt_version=font._sfnt_version,
        )
        return FontLoader.open(TtfSerializer.serialize(subset_font))

    @staticmethod
    def _remap_composite(glyph_bytes: bytes, gid_map: dict[int, int]) -> bytes:
        more_components = 0x0020
        arg_1_and_2_are_words = 0x0001
        we_have_a_scale = 0x0008
        we_have_an_x_and_y_scale = 0x0040
        we_have_a_two_by_two = 0x0080

        data = bytearray(glyph_bytes)
        pos = 10
        while pos + 4 <= len(data):
            flags = int.from_bytes(data[pos : pos + 2], "big")
            old_gid = int.from_bytes(data[pos + 2 : pos + 4], "big")
            new_gid = gid_map.get(old_gid, 0)
            data[pos + 2 : pos + 4] = new_gid.to_bytes(2, "big")
            pos += 4

            pos += 4 if (flags & arg_1_and_2_are_words) else 2
            if flags & we_have_a_two_by_two:
                pos += 8
            elif flags & we_have_an_x_and_y_scale:
                pos += 4
            elif flags & we_have_a_scale:
                pos += 2

            if not (flags & more_components):
                break
        return bytes(data)

    @staticmethod
    def _make_post_v3(original: PostTable | None) -> bytes:
        italic_angle_bytes = b"\x00\x00\x00\x00"
        underline_position = -100
        underline_thickness = 50
        is_fixed_pitch = 0
        if original is not None:
            if len(original._raw) >= 8:
                italic_angle_bytes = original._raw[4:8]
            else:
                fixed_italic = int(round(original.italic_angle * 65536.0)) & 0xFFFFFFFF
                italic_angle_bytes = fixed_italic.to_bytes(4, "big")
            underline_position = original.underline_position
            underline_thickness = original.underline_thickness
            is_fixed_pitch = original.is_fixed_pitch
        return (
            b"\x00\x03\x00\x00"
            + italic_angle_bytes
            + struct.pack(">hh", underline_position, underline_thickness)
            + struct.pack(">I", is_fixed_pitch)
            + b"\x00" * 16
        )

    @classmethod
    def _subset_cff(cls, font: CffFont, sorted_old_gids: list[int]) -> Font:
        gid_map = {old: new for new, old in enumerate(sorted_old_gids)}
        new_charstrings = CffIndex([font.charstrings[old_gid] for old_gid in sorted_old_gids])
        new_names = [font.charset.name_for(old_gid) for old_gid in sorted_old_gids]
        if new_names and new_names[0] != ".notdef":
            new_names[0] = ".notdef"

        new_code_to_gid: dict[int, int] = {}
        for cp in font.encoding.get_all_codepoints():
            try:
                old_gid = int(font.encoding.unicode_to_gid(cp))
            except Exception:
                continue
            if old_gid in gid_map:
                new_code_to_gid[cp] = gid_map[old_gid]

        subset_font = CffFont(
            data=b"",
            top_dict=copy.deepcopy(font.top_dict),
            private_dict=copy.deepcopy(font.private_dict),
            charset=CffCharset(new_names),
            encoding=CffEncoding(new_code_to_gid),
            charstrings=new_charstrings,
            global_subrs=font.global_subrs,
            local_subrs=font.local_subrs,
            string_index=font.string_index,
        )
        return FontLoader.open(CffSerializer.serialize(subset_font))

    @classmethod
    def _subset_type1(cls, font: Type1Font, sorted_old_gids: list[int]) -> Font:
        retained_names = [
            font._gid_to_name[old_gid]
            for old_gid in sorted_old_gids
            if 0 <= old_gid < len(font._gid_to_name)
        ]
        if ".notdef" in font._font_data.charstrings and ".notdef" not in retained_names:
            retained_names.insert(0, ".notdef")
        retained_name_set = set(retained_names)
        if not retained_name_set:
            raise FontNotSupportedException("Type1 subsetting requires at least one retained glyph")

        subset_data = copy.deepcopy(font._font_data)
        subset_data.charstrings = {
            name: subset_data.charstrings[name]
            for name in retained_names
            if name in subset_data.charstrings
        }
        subset_data.encoding = [
            name if name in retained_name_set else ".notdef" for name in subset_data.encoding
        ]

        subset_font = Type1Font(font._raw_data, subset_data, is_pfa=font._is_pfa)
        subset_afm = cls._subset_type1_afm(font._afm, retained_name_set)
        if subset_afm is not None:
            subset_font._afm = subset_afm

        reloaded = FontLoader.open(subset_font.to_bytes(font.font_type))
        if isinstance(reloaded, Type1Font) and subset_afm is not None:
            reloaded._afm = subset_afm
        return reloaded

    @staticmethod
    def _subset_type1_afm(afm: AfmData | None, retained_names: set[str]) -> AfmData | None:
        if afm is None:
            return None

        subset_afm = copy.deepcopy(afm)
        subset_afm.glyph_metrics = {
            name: metric for name, metric in subset_afm.glyph_metrics.items() if name in retained_names
        }
        subset_afm.kern_pairs = [
            (left, right, value)
            for left, right, value in subset_afm.kern_pairs
            if left in retained_names and right in retained_names
        ]
        return subset_afm
