"""Pure-Python gasp table synthesizer (Core Engine) (FONT-544)."""
from __future__ import annotations

from dataclasses import dataclass

from aspose_font._exceptions import FontNotSupportedException
from aspose_font.ttf.tables.gasp import GaspRange, GaspTable

if False:
    from aspose_font.ttf.font import TtfFont


@dataclass(slots=True)
class GaspRangeConfig:
    """Configuration helper for a gasp range entry."""

    max_ppem: int
    behavior: int


def synthesize_gasp_table(font: "TtfFont") -> bytes:
    """Synthesize a gasp table from font metrics.

    Creates a gasp table using reasonable defaults based on font metrics
    (PPEM ranges for typical hinting behaviors).

    Args:
        font: TtfFont instance

    Returns:
        bytes: Serialized gasp table (version 1, typical range configuration)

    Raises:
        FontNotSupportedException: If font does not have required tables (head/maxp)
    """
    if font.ttf_tables.head is None:
        raise FontNotSupportedException("Font is missing required table: head")
    if font.ttf_tables.maxp is None:
        raise FontNotSupportedException("Font is missing required table: maxp")

    units_per_em = font.ttf_tables.head.units_per_em

    ranges = _build_default_gasp_ranges(units_per_em)
    gasp_table = GaspTable(gasp_version=1, ranges=ranges)

    return gasp_table.to_bytes()


def _build_default_gasp_ranges(units_per_em: int) -> list[GaspRange]:
    """Build default gasp ranges based on font units per em.

    Creates standard gasp range configurations based on typical hinting policies:
    - PPEM ≤ 8: Grid-fitting only (behavior=0x0002)
    - PPEM ≤ 16: Grid-fitting + Smooth scaling (behavior=0x0003)
    - PPEM ≤ 24: Grid-fitting + Smooth scaling + ClearType (behavior=0x0007)
    - PPEM > 24: All behaviors (behavior=0x000F)
    """
    max_ppem = max(8, min(24, units_per_em))

    ranges: list[GaspRange] = []

    if max_ppem >= 8:
        ranges.append(GaspRange(range_max_ppem=8, range_gasp_behavior=0x0002))

    if max_ppem >= 16:
        ranges.append(GaspRange(range_max_ppem=16, range_gasp_behavior=0x0003))

    if max_ppem >= 24:
        ranges.append(GaspRange(range_max_ppem=24, range_gasp_behavior=0x0007))

    ranges.append(GaspRange(range_max_ppem=0xFFFF, range_gasp_behavior=0x000F))

    return ranges


def _serialize_gasp_table(gasp_table: GaspTable) -> bytes:
    """Serialize gasp table to binary data.

    Args:
        gasp_table: GaspTable instance

    Returns:
        bytes: Serialized gasp table
    """
    return gasp_table.to_bytes()
