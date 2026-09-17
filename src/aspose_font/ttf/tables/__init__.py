"""Typed TTF table container and table exports."""

from __future__ import annotations

from dataclasses import dataclass, field

from aspose_font.ttf.tables.cmap import CmapTable
from aspose_font.ttf.tables.fvar import AxisRecord, FvarTable, NamedInstance
from aspose_font.ttf.tables.glyf import GlyfTable
from aspose_font.ttf.tables.head import HeadTable
from aspose_font.ttf.tables.hhea import HheaTable
from aspose_font.ttf.tables.hmtx import HMetric, HmtxTable
from aspose_font.ttf.tables.hvar import HvarTable
from aspose_font.ttf.tables.kern import KernTable
from aspose_font.ttf.tables.loca import LocaTable
from aspose_font.ttf.tables.maxp import MaxpTable
from aspose_font.ttf.tables.name import NameTable
from aspose_font.ttf.tables.os2 import Os2Table
from aspose_font.ttf.tables.post import PostTable


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
    fvar: FvarTable | None = None
    hvar: HvarTable | None = None
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
        "fvar": tables.fvar,
        "HVAR": tables.hvar,
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
    "FvarTable",
    "AxisRecord",
    "NamedInstance",
]
