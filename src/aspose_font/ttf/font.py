"""TTF/OTF font parser and Font interface implementation."""

from __future__ import annotations

from dataclasses import dataclass

from aspose_font._exceptions import FontParseException, GlyphNotFoundException
from aspose_font._font_base import Font, FontEncoding, FontType, GlyphAccessor
from aspose_font._io import BinaryReader
from aspose_font._types import FontMetrics, Glyph, GlyphId, KernPair
from aspose_font.cff.font import CffFont
from aspose_font.serializer import TtfSerializer
from aspose_font.ttf.glyph import TtfGlyphParser
from aspose_font.ttf.tables import (
    AxisRecord,
    CmapTable,
    FvarTable,
    GlyfTable,
    HeadTable,
    HheaTable,
    HmtxTable,
    HvarTable,
    KernTable,
    LocaTable,
    MaxpTable,
    NamedInstance,
    NameTable,
    Os2Table,
    PostTable,
    TtfTableSet,
)
from aspose_font.variation import VariableAxis, VariableInstance, build_language_profiles

_SFNT_TRUE_TYPE = 0x00010000
_SFNT_OTTO = 0x4F54544F


@dataclass(slots=True)
class _TableRecord:
    tag: str
    checksum: int
    offset: int
    length: int


class _TtfEncoding(FontEncoding):
    def __init__(self, cmap: CmapTable) -> None:
        self._subtable = cmap.best_subtable()

    def unicode_to_gid(self, codepoint: int) -> GlyphId:
        gid = self._subtable.get_gid(codepoint)
        if gid is None:
            raise GlyphNotFoundException(codepoint)
        return GlyphId(gid)

    def get_all_codepoints(self) -> list[int]:
        return sorted(self._subtable._mapping.keys())


class _TtfGlyphAccessor(GlyphAccessor):
    def __init__(self, font: "TtfFont") -> None:
        super().__init__(font.encoding)
        self._font = font
        self._cache: dict[int, Glyph] = {}
        tables = font.ttf_tables
        if tables.loca is not None and tables.glyf is not None and tables.hmtx is not None:
            self._parser: TtfGlyphParser | None = TtfGlyphParser(tables.loca, tables.glyf, tables.hmtx)
        else:
            self._parser = None

    def get_glyph_by_id(self, gid: GlyphId) -> Glyph:
        idx = int(gid)
        if idx < 0 or idx >= self._font.num_glyphs:
            raise GlyphNotFoundException(idx)
        cached = self._cache.get(idx)
        if cached is not None:
            return cached

        if self._parser is not None:
            glyph = self._parser.parse(gid)
        else:
            metric_aw = 0
            metric_lsb = 0
            if self._font.ttf_tables.hmtx is not None and idx < len(self._font.ttf_tables.hmtx.metrics):
                metric = self._font.ttf_tables.hmtx.get_metric(idx)
                metric_aw = metric.advance_width
                metric_lsb = metric.lsb
            glyph = Glyph(
                glyph_id=gid,
                glyph_name=None,
                path=None,
                advance_width=metric_aw,
                lsb=metric_lsb,
            )

        if self._font.ttf_tables.post is not None:
            glyph.glyph_name = self._font.ttf_tables.post.glyph_name(idx)

        self._cache[idx] = glyph
        return glyph

    def get_all_glyph_ids(self) -> list[GlyphId]:
        return [GlyphId(i) for i in range(self._font.num_glyphs)]


class TtfFont(Font):
    def __init__(self, sfnt_data: bytes, tables: TtfTableSet, sfnt_version: int) -> None:
        self._sfnt_data = sfnt_data
        self._tables = tables
        self._sfnt_version = sfnt_version
        self._encoding_impl = _TtfEncoding(tables.cmap) if tables.cmap is not None else None
        self._glyph_accessor_impl = _TtfGlyphAccessor(self) if self._encoding_impl is not None else None
        self._cff_font = None
        self._variable_axes_cache: list[VariableAxis] | None = None
        self._variable_instances_cache: list[VariableInstance] | None = None

    @classmethod
    def _from_reader(
        cls,
        r: BinaryReader,
        font_type: FontType | None = None,
    ) -> "TtfFont":
        del font_type
        data = r.read_bytes(r.remaining())
        rr = BinaryReader(data)

        sfnt_version = rr.read_u32()
        if sfnt_version not in (_SFNT_TRUE_TYPE, _SFNT_OTTO):
            # Keep compatibility with legacy sfnt signatures by treating as TrueType layout.
            if sfnt_version not in (0x74727565, 0x74797031):
                raise FontParseException(f"Unsupported sfnt version: 0x{sfnt_version:08X}")

        num_tables = rr.read_u16()
        rr.read_u16()  # searchRange
        rr.read_u16()  # entrySelector
        rr.read_u16()  # rangeShift

        records: list[_TableRecord] = []
        for _ in range(num_tables):
            records.append(
                _TableRecord(
                    tag=rr.read_tag(),
                    checksum=rr.read_u32(),
                    offset=rr.read_u32(),
                    length=rr.read_u32(),
                )
            )

        tables = TtfTableSet()
        for record in records:
            end = record.offset + record.length
            if end > len(data):
                raise FontParseException(f"Table {record.tag} exceeds file bounds")
            blob = data[record.offset:end]
            tables._raw[record.tag] = blob

        def get_blob(tag: str) -> bytes | None:
            return tables._raw.get(tag)

        head_blob = get_blob("head")
        if head_blob is None:
            raise FontParseException("Missing required table: head")
        if len(head_blob) < 54:
            raise FontParseException("Invalid head table length")
        tables.head = HeadTable.from_reader(BinaryReader(head_blob))

        maxp_blob = get_blob("maxp")
        if maxp_blob is None:
            raise FontParseException("Missing required table: maxp")
        tables.maxp = MaxpTable.from_reader(BinaryReader(maxp_blob), len(maxp_blob))

        hhea_blob = get_blob("hhea")
        if hhea_blob is not None and len(hhea_blob) >= 36:
            tables.hhea = HheaTable.from_reader(BinaryReader(hhea_blob))

        os2_blob = get_blob("OS/2")
        if os2_blob is not None:
            tables.os2 = Os2Table.from_reader(BinaryReader(os2_blob), len(os2_blob))

        name_blob = get_blob("name")
        if name_blob is not None:
            tables.name = NameTable.from_reader(BinaryReader(name_blob), len(name_blob))

        post_blob = get_blob("post")
        if post_blob is not None:
            tables.post = PostTable.from_reader(BinaryReader(post_blob), len(post_blob))

        cmap_blob = get_blob("cmap")
        if cmap_blob is not None:
            tables.cmap = CmapTable.from_reader(BinaryReader(cmap_blob), len(cmap_blob))
            tables.cmap.best_subtable()

        loca_blob = get_blob("loca")
        if loca_blob is not None and tables.head is not None and tables.maxp is not None:
            tables.loca = LocaTable.from_reader(
                BinaryReader(loca_blob),
                num_glyphs=tables.maxp.num_glyphs,
                index_to_loc_format=tables.head.index_to_loc_format,
                table_length=len(loca_blob),
            )

        hmtx_blob = get_blob("hmtx")
        if (
            hmtx_blob is not None
            and tables.maxp is not None
            and tables.hhea is not None
        ):
            tables.hmtx = HmtxTable.from_reader(
                BinaryReader(hmtx_blob),
                num_glyphs=tables.maxp.num_glyphs,
                number_of_hmetrics=tables.hhea.number_of_hmetrics,
                table_length=len(hmtx_blob),
            )

        kern_blob = get_blob("kern")
        if kern_blob is not None:
            tables.kern = KernTable.from_reader(BinaryReader(kern_blob), len(kern_blob))

        glyf_blob = get_blob("glyf")
        if glyf_blob is not None:
            tables.glyf = GlyfTable.from_reader(BinaryReader(glyf_blob), len(glyf_blob))

        font = cls(sfnt_data=data, tables=tables, sfnt_version=sfnt_version)
        cff_blob = get_blob("CFF ")
        if cff_blob is not None:
            font._cff_font = CffFont._from_bytes(cff_blob)
        return font

    @property
    def font_type(self) -> FontType:
        return FontType.OTF if self._sfnt_version == _SFNT_OTTO else FontType.TTF

    @property
    def font_name(self) -> str:
        if self._tables.name is None:
            return ""
        return self._tables.name.get(4) or ""

    @property
    def font_family(self) -> str:
        if self._tables.name is None:
            return ""
        return self._tables.name.get(1) or ""

    @property
    def font_style(self) -> str:
        if self._tables.name is None:
            return ""
        return self._tables.name.get(2) or ""

    @property
    def num_glyphs(self) -> int:
        if self._tables.maxp is None:
            return 0
        return self._tables.maxp.num_glyphs

    @property
    def metrics(self) -> FontMetrics:
        head = self._tables.head
        hhea = self._tables.hhea
        os2 = self._tables.os2
        return FontMetrics(
            units_per_em=head.units_per_em if head is not None else 1000,
            ascender=(os2.s_typo_ascender if os2 is not None else (hhea.ascender if hhea else 0)),
            descender=(os2.s_typo_descender if os2 is not None else (hhea.descender if hhea else 0)),
            line_gap=(os2.s_typo_line_gap if os2 is not None else (hhea.line_gap if hhea else 0)),
            advance_width_max=hhea.advance_width_max if hhea is not None else 0,
            underline_position=(self._tables.post.underline_position if self._tables.post else 0),
            underline_thickness=(self._tables.post.underline_thickness if self._tables.post else 0),
        )

    @property
    def encoding(self) -> FontEncoding:
        if self._encoding_impl is None:
            raise FontParseException("No supported cmap subtable found")
        return self._encoding_impl

    @property
    def glyph_accessor(self) -> GlyphAccessor:
        if self._glyph_accessor_impl is None:
            raise FontParseException("Glyph accessor unavailable: missing cmap")
        return self._glyph_accessor_impl

    @property
    def ttf_tables(self) -> TtfTableSet:
        return self._tables

    def get_table_bytes(self, tag: str) -> bytes:
        data = self._tables.get_raw(tag)
        if data is None:
            raise FontParseException(f"Table not found: {tag}")
        return data

    def set_table_bytes(self, tag: str, data: bytes) -> None:
        self._tables.set_raw(tag, data)
        if tag == "head" and len(data) >= 54:
            self._tables.head = HeadTable.from_reader(BinaryReader(data))
        elif tag == "maxp" and len(data) >= 6:
            self._tables.maxp = MaxpTable.from_reader(BinaryReader(data), len(data))
        elif tag == "hhea" and len(data) >= 36:
            self._tables.hhea = HheaTable.from_reader(BinaryReader(data))
        elif tag == "OS/2":
            self._tables.os2 = Os2Table.from_reader(BinaryReader(data), len(data))
        elif tag == "name":
            self._tables.name = NameTable.from_reader(BinaryReader(data), len(data))
        elif tag == "post":
            self._tables.post = PostTable.from_reader(BinaryReader(data), len(data))
        elif tag == "cmap":
            self._tables.cmap = CmapTable.from_reader(BinaryReader(data), len(data))
            self._encoding_impl = _TtfEncoding(self._tables.cmap)
            self._glyph_accessor_impl = _TtfGlyphAccessor(self)
        elif tag == "kern":
            self._tables.kern = KernTable.from_reader(BinaryReader(data), len(data))
        elif tag == "glyf":
            self._tables.glyf = GlyfTable.from_reader(BinaryReader(data), len(data))
        elif tag == "fvar":
            # Keep lazy parsing semantics and avoid stale cached FVAR.
            self._tables.fvar = None
        elif tag == "HVAR":
            self._tables.hvar = None
        if tag in {"fvar", "name"}:
            self._variable_axes_cache = None
            self._variable_instances_cache = None

    @property
    def cff_font(self):
        return self._cff_font

    @property
    def fvar(self) -> "FvarTable | None":
        """Lazily parse and return the FVAR table, or None if not a variable font."""
        if self._tables.fvar is not None:
            return self._tables.fvar
        raw = self._tables._raw.get("fvar")
        if raw is None:
            return None
        from aspose_font._io import BinaryReader
        self._tables.fvar = FvarTable.from_reader(BinaryReader(raw), len(raw))
        return self._tables.fvar

    @property
    def hvar(self) -> "HvarTable | None":
        if self._tables.hvar is not None:
            return self._tables.hvar
        raw = self._tables._raw.get("HVAR")
        if raw is None:
            return None
        self._tables.hvar = HvarTable.from_reader(
            BinaryReader(raw),
            len(raw),
            axis_tags=[axis.tag for axis in self.axes],
        )
        return self._tables.hvar

    @property
    def is_variable(self) -> bool:
        return self.fvar is not None

    @property
    def axes(self) -> "list[AxisRecord]":
        f = self.fvar
        return f.axes if f is not None else []

    @property
    def named_instances(self) -> "list[NamedInstance]":
        f = self.fvar
        return f.instances if f is not None else []

    @property
    def variable_axes(self) -> list[VariableAxis]:
        if self._variable_axes_cache is not None:
            return self._variable_axes_cache
        name_table = self._tables.name
        axes: list[VariableAxis] = []
        for axis in self.axes:
            names = name_table.localized_names(axis.name_id) if name_table is not None else {}
            axes.append(
                VariableAxis(
                    tag=axis.tag,
                    min_value=axis.min_value,
                    default_value=axis.default_value,
                    max_value=axis.max_value,
                    flags=axis.flags,
                    name_id=axis.name_id,
                    names_by_language=names,
                )
            )
        self._variable_axes_cache = axes
        return axes

    def get_axis(self, tag: str) -> VariableAxis | None:
        for axis in self.variable_axes:
            if axis.tag == tag:
                return axis
        return None

    @property
    def variable_instances(self) -> list[VariableInstance]:
        if self._variable_instances_cache is not None:
            return self._variable_instances_cache
        name_table = self._tables.name
        instances: list[VariableInstance] = []
        for instance in self.named_instances:
            names = name_table.localized_names(instance.name_id) if name_table is not None else {}
            postscript_name = None
            if name_table is not None and instance.postscript_name_id is not None:
                postscript_name = name_table.best_name(instance.postscript_name_id)
            instances.append(
                VariableInstance(
                    coordinates=dict(instance.coordinates),
                    name_id=instance.name_id,
                    postscript_name_id=instance.postscript_name_id,
                    names_by_language=names,
                    postscript_name=postscript_name,
                )
            )
        self._variable_instances_cache = instances
        return instances

    def get_named_instance(
        self,
        name: str,
        *,
        preferred_languages: str | tuple[str, ...] = "en",
    ) -> VariableInstance | None:
        needle = name.casefold()
        for instance in self.variable_instances:
            localized = instance.name(preferred_languages)
            if localized is not None and localized.casefold() == needle:
                return instance
            if instance.label.casefold() == needle:
                return instance
            if instance.postscript_name is not None and instance.postscript_name.casefold() == needle:
                return instance
        return None

    def variable_presentation(
        self,
        *,
        preferred_languages: str | tuple[str, ...] = "en",
        include_suggested_values: bool = True,
    ) -> dict[str, object]:
        axes_by_tag = {axis.tag: axis for axis in self.variable_axes}
        axes: list[dict[str, object]] = []
        grouped_axes: dict[str, list[str]] = {}
        group_orders: dict[str, int] = {}
        for axis in self.variable_axes:
            suggested_values = None
            if include_suggested_values:
                suggested_values = self.smart_instancer.suggest_axis_values(
                    axis.tag,
                    include_default=True,
                    include_bounds=True,
                )
            axes.append(
                axis.to_presentation(
                    language=preferred_languages,
                    suggested_values=suggested_values,
                )
            )
            grouped_axes.setdefault(axis.display_group, []).append(axis.tag)
            group_orders[axis.display_group] = min(
                axis.display_order,
                group_orders.get(axis.display_group, axis.display_order),
            )
        requested_languages = (
            [preferred_languages]
            if isinstance(preferred_languages, str)
            else list(preferred_languages)
        )
        normalized_requested_languages = [
            profile.requested_language
            for profile in build_language_profiles({}, preferred_languages, fallback_label="", fallback_reason="metadata-default")
        ]
        axis_groups = [
            {
                "group": group,
                "label": group.replace("-", " ").title(),
                "display_order": group_orders[group],
                "axis_tags": list(sorted(tags, key=lambda tag: axes_by_tag[tag].display_order)),
                "axis_count": len(tags),
                "language_profiles": [
                    profile.to_dict()
                    for profile in build_language_profiles(
                        {},
                        preferred_languages,
                        fallback_label=group.replace("-", " ").title(),
                        fallback_reason="metadata-default",
                    )
                ],
            }
            for group, tags in sorted(
                grouped_axes.items(),
                key=lambda item: (group_orders[item[0]], item[0]),
            )
        ]
        axis_group_profiles = {
            group["group"]: {
                profile["requested_language"]: profile
                for profile in group["language_profiles"]  # type: ignore[index]
            }
            for group in axis_groups
        }
        axis_profiles = {
            axis.tag: {
                profile.requested_language: profile.to_dict()
                for profile in axis.language_profiles(preferred_languages)
            }
            for axis in self.variable_axes
        }
        instance_profiles = [
            {
                "name_id": instance.name_id,
                "profiles": {
                    profile.requested_language: profile.to_dict()
                    for profile in instance.language_profiles(preferred_languages)
                },
            }
            for instance in self.variable_instances
        ]
        language_profiles = [
            {
                "requested_language": requested_language,
                "axes": {
                    tag: profiles[requested_language]
                    for tag, profiles in axis_profiles.items()
                    if requested_language in profiles
                },
                "axis_groups": {
                    group: profiles[requested_language]
                    for group, profiles in axis_group_profiles.items()
                    if requested_language in profiles
                },
                "named_instances": [
                    {
                        "name_id": item["name_id"],
                        "profile": item["profiles"][requested_language],
                    }
                    for item in instance_profiles
                    if requested_language in item["profiles"]
                ],
            }
            for requested_language in normalized_requested_languages
        ]
        return {
            "font_name": self.font_name,
            "font_family": self.font_family,
            "font_style": self.font_style,
            "is_variable": self.is_variable,
            "preferred_languages": requested_languages,
            "language_profiles": language_profiles,
            "axis_groups": axis_groups,
            "axes": axes,
            "named_instances": [
                instance.to_presentation(
                    axes_by_tag,
                    language=preferred_languages,
                    include_tags=True,
                )
                for instance in self.variable_instances
            ],
        }

    @property
    def smart_instancer(self):
        from aspose_font.instancing import SmartInstancer

        return SmartInstancer(self)

    @staticmethod
    def available_naming_strategies() -> tuple[str, ...]:
        from aspose_font.ttf.instancer import TtfInstancer

        return TtfInstancer.available_naming_strategies()

    def instantiate(
        self,
        coordinates: dict[str, float],
        *,
        naming_strategy: str = "instance-family",
        family_suffix: str | None = None,
        legacy_family_name: str | None = None,
        typographic_family_name: str | None = None,
        legacy_style_name: str | None = None,
        typographic_style_name: str | None = None,
        stat_policy: str = "drop",
    ) -> "TtfFont":
        from aspose_font.ttf.instancer import TtfInstancer

        return TtfInstancer.instantiate(
            self,
            coordinates,
            naming_strategy=naming_strategy,
            family_suffix=family_suffix,
            legacy_family_name=legacy_family_name,
            typographic_family_name=typographic_family_name,
            legacy_style_name=legacy_style_name,
            typographic_style_name=typographic_style_name,
            stat_policy=stat_policy,
        )

    def preview_naming_policy(
        self,
        coordinates: dict[str, float],
        *,
        naming_strategy: str = "instance-family",
        family_suffix: str | None = None,
        legacy_family_name: str | None = None,
        typographic_family_name: str | None = None,
        legacy_style_name: str | None = None,
        typographic_style_name: str | None = None,
        stat_policy: str = "drop",
    ):
        from aspose_font.ttf.instancer import TtfInstancer

        return TtfInstancer.preview_naming_policy(
            self,
            coordinates,
            naming_strategy=naming_strategy,
            family_suffix=family_suffix,
            legacy_family_name=legacy_family_name,
            typographic_family_name=typographic_family_name,
            legacy_style_name=legacy_style_name,
            typographic_style_name=typographic_style_name,
            stat_policy=stat_policy,
        )

    def get_kern_pairs(self) -> list[KernPair]:
        if self._tables.kern is None:
            return []
        return list(self._tables.kern.pairs)

    def to_bytes(self, font_type: FontType | None = None) -> bytes:
        if font_type is not None and font_type != self.font_type:
            return super().to_bytes(font_type)
        return TtfSerializer.serialize(self)
