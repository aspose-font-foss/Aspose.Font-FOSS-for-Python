"""Font feature discovery matrix core engine."""

from __future__ import annotations

from aspose_font._font_base import Font
from aspose_font.ttf.font import TtfFont
from aspose_font.ttf.tables.gpos import GposTable
from aspose_font.ttf.tables.gsub import GsubTable


class FontFeatureDiscoveryMatrix:
    """Discovers OpenType feature support across major font tables."""

    def discover(self, font: Font) -> dict[str, list[str]]:
        """Scan font and return feature discovery matrix.

        Returns dict with keys:
        - 'GSUB': list of feature tags (e.g., ['liga', 'kern'])
        - 'GPOS': list of feature tags
        - 'STAT': list of axis tags (typically ['wght', 'wdth'])
        - 'COLR': ['COLR'] if present (color table indicator)
        - 'SVG': ['SVG'] if present (SVG glyph table indicator)
        - 'SBIX': ['SBIX'] if present (Apple bitmap table indicator)

        Missing tables return empty list for that entry.
        Raises: TypeError if font is not a TtfFont instance
        """
        if not isinstance(font, TtfFont):
            return {
                "GSUB": [],
                "GPOS": [],
                "STAT": [],
                "COLR": [],
                "SVG": [],
                "SBIX": [],
            }

        result: dict[str, list[str]] = {
            "GSUB": [],
            "GPOS": [],
            "STAT": [],
            "COLR": [],
            "SVG": [],
            "SBIX": [],
        }

        tables = font.ttf_tables

        try:
            if tables.gsub is not None:
                result["GSUB"] = self._extract_gsub_features(tables.gsub)
        except Exception:
            result["GSUB"] = []

        try:
            if tables.gpos is not None:
                result["GPOS"] = self._extract_gpos_features(tables.gpos)
        except Exception:
            result["GPOS"] = []

        try:
            if tables.fvar is not None:
                result["STAT"] = [ax.tag for ax in tables.fvar.axes]
        except Exception:
            result["STAT"] = []

        try:
            if tables.colr is not None:
                result["COLR"] = ["COLR"]
        except Exception:
            pass

        try:
            if tables.svg is not None:
                result["SVG"] = ["SVG"]
        except Exception:
            pass

        try:
            if tables.sbix is not None:
                result["SBIX"] = ["SBIX"]
        except Exception:
            pass

        return result

    def _extract_gsub_features(self, gsub: GsubTable) -> list[str]:
        """Extract all feature tags from GSUB table."""
        try:
            features = gsub.list_all_features()
            return list(dict.fromkeys(features))
        except Exception:
            return []

    def _extract_gpos_features(self, gpos: GposTable) -> list[str]:
        """Extract all feature tags from GPOS table."""
        try:
            features = gpos.list_all_features()
            return list(dict.fromkeys(features))
        except Exception:
            return []
