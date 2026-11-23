"""Tests for FontFeatureDiscoveryMatrix integration in WebFontOptimizer and FontQaReporter."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from aspose_font import FontFeatureDiscoveryMatrix, FontLoader, WebFontOptimizer
from aspose_font.qa import FontQaReporter
from aspose_font.ttf.font import TtfFont

src_dir = Path(__file__).resolve().parents[1] / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))


class TestFeatureMatrixIntegration:
    """Test suite for FontFeatureDiscoveryMatrix integration."""

    def test_web_optimizer_manifest_includes_features(self, roboto: TtfFont, tmp_path: Path) -> None:
        """Verify WebFontOptimizer manifest includes features field with correct structure."""
        package = WebFontOptimizer.build(
            roboto,
            source_path=Path("testdata/Roboto-VariableFont_wdth,wght.ttf"),
            presets=("latin",),
            text="Aspose Web",
            include_woff=False,
        )

        manifest = package.manifest
        bundle_manifest = manifest.get("bundle", {})

        assert "features" in bundle_manifest
        features = bundle_manifest["features"]
        assert isinstance(features, dict)
        assert set(features.keys()) == {"GSUB", "GPOS", "STAT", "COLR", "SVG", "SBIX"}
        assert all(isinstance(v, list) for v in features.values())

    def test_qa_report_json_includes_features(self, roboto: TtfFont, tmp_path: Path) -> None:
        """Verify FontQaReporter JSON report includes features field."""
        report = FontQaReporter.build(roboto, presets=("latin",), text="QA")
        payload = report.to_dict()

        assert "features" in payload
        features = payload["features"]
        assert isinstance(features, dict)
        assert set(features.keys()) == {"GSUB", "GPOS", "STAT", "COLR", "SVG", "SBIX"}

    def test_qa_report_html_includes_features_table(self, roboto: TtfFont, tmp_path: Path) -> None:
        """Verify FontQaReporter HTML includes OpenType Feature Matrix table."""
        report = FontQaReporter.build(roboto, presets=("latin",), text="QA")
        html_path = report.write_html(tmp_path / "qa.html")
        html_content = html_path.read_text(encoding="utf-8")

        assert "OpenType Feature Matrix" in html_content
        assert "<th>GSUB</th>" in html_content
        assert "<th>GPOS</th>" in html_content
        assert "<th>STAT</th>" in html_content

    def test_features_matrix_structure_matches_discover(self, roboto: TtfFont) -> None:
        """Verify features in reports match FontFeatureDiscoveryMatrix.discover() output."""
        expected = FontFeatureDiscoveryMatrix().discover(roboto)

        report = FontQaReporter.build(roboto, presets=("latin",), text="QA")
        actual = report.to_dict()["features"]

        assert actual == expected

    def test_features_present_in_static_font(self, tmp_path: Path) -> None:
        """Verify features appear in static font export."""
        test_fonts_dir = Path(__file__).resolve().parents[0] / "fonts"
        if not test_fonts_dir.exists():
            pytest.skip("Test fonts directory not available")

        font_files = list(test_fonts_dir.glob("*.ttf"))
        if not font_files:
            pytest.skip("No test fonts available")

        font_file = font_files[0]
        font = FontLoader.load_from_file(str(font_file))

        if not isinstance(font, TtfFont):
            pytest.skip("Test requires TTF font")

        package = WebFontOptimizer.build(
            font,
            source_path=font_file,
            presets=("latin",),
            include_woff=False,
            variable_mode="static",
        )

        bundle_manifest = package.manifest.get("bundle", {})
        assert "features" in bundle_manifest
        features = bundle_manifest["features"]
        assert isinstance(features, dict)
        assert set(features.keys()) == {"GSUB", "GPOS", "STAT", "COLR", "SVG", "SBIX"}
