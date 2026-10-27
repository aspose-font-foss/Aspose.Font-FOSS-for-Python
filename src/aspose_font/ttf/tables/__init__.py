"""Typed TTF table container and table exports."""

from __future__ import annotations

from dataclasses import dataclass, field

from aspose_font.ttf.tables.avar import AvarTable
from aspose_font.ttf.tables.cmap import CmapTable
from aspose_font.ttf.tables.colr import (
    BaseGlyphRecord,
    BaseGlyphV1Record,
    ColrTable,
    LayerRecord,
    LayerV1Record,
    PaintColrLayers,
    PaintGlyph,
    PaintLinearGradient,
    PaintRadialGradient,
    PaintRotate,
    PaintScale,
    PaintSkew,
    PaintSolid,
    PaintTransform,
    PaintTranslate,
)
from aspose_font.ttf.tables.cpal import ColorPalette, CpalTable
from aspose_font.ttf.tables.cvar import CvarTable
from aspose_font.ttf.tables.feature_variations import FeatureVariationRecord, FeatureVariationTable
from aspose_font.ttf.tables.fvar import AxisRecord, FvarTable, NamedInstance
from aspose_font.ttf.tables.glyf import GlyfTable
from aspose_font.ttf.tables.gpos import GposTable
from aspose_font.ttf.tables.gsub import GsubTable
from aspose_font.ttf.tables.head import HeadTable
from aspose_font.ttf.tables.hhea import HheaTable
from aspose_font.ttf.tables.hmtx import HMetric, HmtxTable
from aspose_font.ttf.tables.hvar import HvarTable
from aspose_font.ttf.tables.kern import KernTable
from aspose_font.ttf.tables.loca import LocaTable
from aspose_font.ttf.tables.maxp import MaxpTable
from aspose_font.ttf.tables.mvar import MvarTable
from aspose_font.ttf.tables.name import NameTable
from aspose_font.ttf.tables.os2 import Os2Table
from aspose_font.ttf.tables.post import PostTable
from aspose_font.ttf.tables.svg import SVGDocumentRecord, SVGTable
from aspose_font.ttf.tables.vvar import VvarTable


@dataclass
class TtfTableSet:
    head: HeadTable | None = None
    hhea: HheaTable | None = None
    maxp: MaxpTable | None = None
    os2: Os2Table | None = None
    name: NameTable | None = None
    post: PostTable | None = None
    cmap: CmapTable | None = None
    loca: LocaTable | None = None
    hmtx: HmtxTable | None = None
    kern: KernTable | None = None
    glyf: GlyfTable | None = None
    gpos: GposTable | None = None
    fvar: FvarTable | None = None
    hvar: HvarTable | None = None
    avar: AvarTable | None = None
    mvar: MvarTable | None = None
    vvar: VvarTable | None = None
    cvar: CvarTable | None = None
    feature_variations: FeatureVariationTable | None = None
    cpal: CpalTable | None = None
    colr: ColrTable | None = None
    gsub: GsubTable | None = None
    svg: SVGTable | None = None
    _raw: dict[str, bytes] = field(default_factory=dict)

    def get_raw(self, tag: str) -> bytes | None:
        if tag in self._raw:
            return self._raw[tag]
        table = _table_for_tag(self, tag)
        if table is None:
            return None
        return table.to_bytes()

    def set_raw(self, tag: str, data: bytes) -> None:
        self._raw[tag] = data

    @property
    def gvar(self) -> object | None:
        raw = self.get_raw("gvar")
        if raw is None:
            return None
        from aspose_font._io import BinaryReader
        from aspose_font.ttf.tables.gvar import GvarTable

        axis_tags = [ax.tag for ax in self.fvar.axes] if self.fvar else []
        return GvarTable.from_reader(BinaryReader(raw), len(raw), axis_tags)


def _table_for_tag(tables: TtfTableSet, tag: str) -> object | None:
    return {
        "head": tables.head,
        "hhea": tables.hhea,
        "maxp": tables.maxp,
        "OS/2": tables.os2,
        "name": tables.name,
        "post": tables.post,
        "cmap": tables.cmap,
        "loca": tables.loca,
        "hmtx": tables.hmtx,
        "kern": tables.kern,
        "glyf": tables.glyf,
        "GPOS": tables.gpos,
        "fvar": tables.fvar,
        "HVAR": tables.hvar,
        "avar": tables.avar,
        "MVAR": tables.mvar,
        "VVAR": tables.vvar,
        "cvar": tables.cvar,
        "FeatureVariations": tables.feature_variations,
        "CPAL": tables.cpal,
        "COLR": tables.colr,
        "GSUB": tables.gsub,
        "SVG ": tables.svg,
    }.get(tag)


__all__ = [
    "TtfTableSet",
    "HeadTable",
    "HheaTable",
    "HvarTable",
    "HMetric",
    "MaxpTable",
    "Os2Table",
    "NameTable",
    "PostTable",
    "CmapTable",
    "LocaTable",
    "HmtxTable",
    "KernTable",
    "GlyfTable",
    "GposTable",
    "FvarTable",
    "AxisRecord",
    "NamedInstance",
    "AvarTable",
    "MvarTable",
    "VvarTable",
    "CvarTable",
    "FeatureVariationTable",
    "FeatureVariationRecord",
    "CpalTable",
    "ColorPalette",
    "ColrTable",
    "BaseGlyphRecord",
    "LayerRecord",
    "PaintSolid",
    "PaintLinearGradient",
    "PaintRadialGradient",
    "PaintGlyph",
    "PaintColrLayers",
    "PaintTransform",
    "PaintTranslate",
    "PaintScale",
    "PaintRotate",
    "PaintSkew",
    "BaseGlyphV1Record",
    "LayerV1Record",
    "GsubTable",
    "SVGTable",
    "SVGDocumentRecord",
]
