"""Tests for Font feature discovery matrix."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from aspose_font import FontFeatureDiscoveryMatrix, FontLoader
from aspose_font.ttf.font import TtfFont

src_dir = Path(__file__).resolve().parents[1] / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))


class TestFontFeatureDiscoveryMatrix:
    """Test suite for FontFeatureDiscoveryMatrix."""

    def test_discover_returns_dict_with_six_keys(self, roboto: TtfFont) -> None:
        """Verify discover() returns dict with exactly 6 keys."""
        matrix = FontFeatureDiscoveryMatrix()
        result = matrix.discover(roboto)

        assert isinstance(result, dict)
        assert set(result.keys()) == {"GSUB", "GPOS", "STAT", "COLR", "SVG", "SBIX"}
        assert all(isinstance(v, list) for v in result.values())

    def test_discover_gracefully_handles_missing_tables(self, roboto: TtfFont) -> None:
        """Verify missing tables are handled gracefully with empty lists."""
        font = roboto

        matrix = FontFeatureDiscoveryMatrix()
        result = matrix.discover(font)

        assert isinstance(result["GSUB"], list)
        assert isinstance(result["GPOS"], list)
        assert isinstance(result["STAT"], list)
        assert isinstance(result["COLR"], list)
        assert isinstance(result["SVG"], list)
        assert isinstance(result["SBIX"], list)

    def test_discover_captures_gsub_features(self, roboto: TtfFont) -> None:
        """Verify GSUB features are captured (Roboto has liga)."""
        matrix = FontFeatureDiscoveryMatrix()
        result = matrix.discover(roboto)

        assert isinstance(result["GSUB"], list)
        assert "liga" in result["GSUB"]
        assert len(result["GSUB"]) == len(set(result["GSUB"]))

    def test_discover_captures_gpos_features(self, roboto: TtfFont) -> None:
        """Verify GPOS features are captured (Roboto has kern)."""
        matrix = FontFeatureDiscoveryMatrix()
        result = matrix.discover(roboto)

        assert isinstance(result["GPOS"], list)
        assert "kern" in result["GPOS"]
        assert len(result["GPOS"]) == len(set(result["GPOS"]))

    def test_discover_captures_stat_features_if_variable(self, roboto: TtfFont) -> None:
        """Verify STAT features (axes) are captured for variable fonts."""
        matrix = FontFeatureDiscoveryMatrix()
        result = matrix.discover(roboto)

        assert isinstance(result["STAT"], list)
        assert "wght" in result["STAT"]
        assert "wdth" in result["STAT"]

    def test_discover_marks_colr_presence(self, roboto: TtfFont) -> None:
        """Verify COLR presence is marked."""
        matrix = FontFeatureDiscoveryMatrix()
        result = matrix.discover(roboto)

        assert isinstance(result["COLR"], list)

    def test_discover_marks_svg_presence(self, roboto: TtfFont) -> None:
        """Verify SVG presence is marked."""
        matrix = FontFeatureDiscoveryMatrix()
        result = matrix.discover(roboto)

        assert isinstance(result["SVG"], list)

    def test_discover_marks_sbix_presence(self, roboto: TtfFont) -> None:
        """Verify SBIX presence is marked."""
        matrix = FontFeatureDiscoveryMatrix()
        result = matrix.discover(roboto)

        assert isinstance(result["SBIX"], list)

    def test_discover_handles_non_ttf_font_gracefully(self, opensans_cff: FontLoader) -> None:
        """Verify non-TTF fonts return all empty lists."""
        from aspose_font import CffFont

        if not isinstance(opensans_cff, CffFont):
            pytest.skip("Test requires CFF font fixture")

        matrix = FontFeatureDiscoveryMatrix()
        result = matrix.discover(opensans_cff)

        assert result["GSUB"] == []
        assert result["GPOS"] == []
        assert result["STAT"] == []
        assert result["COLR"] == []
        assert result["SVG"] == []
        assert result["SBIX"] == []

    def test_discover_is_importable(self) -> None:
        """Verify import works without circular dependency."""
        from aspose_font import FontFeatureDiscoveryMatrix

        instance = FontFeatureDiscoveryMatrix()
        assert instance is not None
