"""Tests for FONT-555 Web Font Preload & Performance Budget Generator Engine."""

from __future__ import annotations

from aspose_font.web import (
    WebFontAsset,
    WebFontPerformanceAdvisor,
)


class TestWebFontPerformanceAdvisorGeneratePreloadTags:
    """Tests for WebFontPerformanceAdvisor.generate_preload_tags()."""

    def test_generate_preload_tags_single_woff2(self):
        """Single WOFF2 font produces valid preload tag with crossorigin."""
        asset = WebFontAsset("font.woff2", "font/woff2", b"font-data")
        tags = WebFontPerformanceAdvisor.generate_preload_tags([asset])

        assert len(tags) == 1
        tag = tags[0]
        assert 'rel="preload"' in tag
        assert 'as="font"' in tag
        assert 'type="font/woff2"' in tag
        assert 'crossorigin' in tag
        assert 'href="/fonts/font.woff2"' in tag

    def test_generate_preload_tags_custom_base_url(self):
        """Custom base_url is applied to href attribute."""
        asset = WebFontAsset("font.woff2", "font/woff2", b"")
        tags = WebFontPerformanceAdvisor.generate_preload_tags([asset], base_url="https://cdn.example.com/fonts/")

        assert 'href="https://cdn.example.com/fonts/font.woff2"' in tags[0]

    def test_generate_preload_tags_different_font_formats(self):
        """Different font formats generate correct type attributes."""
        assets = [
            WebFontAsset("font.woff2", "font/woff2", b""),
            WebFontAsset("font.woff", "font/woff", b""),
            WebFontAsset("font.ttf", "font/ttf", b""),
            WebFontAsset("font.otf", "font/otf", b""),
        ]
        tags = WebFontPerformanceAdvisor.generate_preload_tags(assets)

        assert 'type="font/woff2"' in tags[0]
        assert 'type="font/woff"' in tags[1]
        assert 'type="font/ttf"' in tags[2]
        assert 'type="font/otf"' in tags[3]

    def test_generate_preload_tags_auto_detect_media_type(self):
        """Media type is auto-detected from filename extension."""
        asset = WebFontAsset("font.woff2", "", b"")
        tags = WebFontPerformanceAdvisor.generate_preload_tags([asset])

        assert 'type="font/woff2"' in tags[0]

    def test_generate_preload_tags_with_dict_input(self):
        """Accepts dict input with filename, size, and optional media_type."""
        fonts = [
            {"filename": "font.woff2", "size": 50_000, "media_type": "font/woff2"},
        ]
        tags = WebFontPerformanceAdvisor.generate_preload_tags(fonts)

        assert 'href="/fonts/font.woff2"' in tags[0]

    def test_generate_preload_tags_empty_list(self):
        """Empty input returns empty list."""
        tags = WebFontPerformanceAdvisor.generate_preload_tags([])
        assert tags == []


class TestWebFontPerformanceAdvisorEvaluateBudget:
    """Tests for WebFontPerformanceAdvisor.evaluate_budget()."""

    def test_evaluate_budget_single_font_pass(self):
        """Font within 80% of budget returns pass status."""
        asset = WebFontAsset("font.woff2", "font/woff2", b"x" * 80_000)
        summary = WebFontPerformanceAdvisor.evaluate_budget([asset], per_font_budget_bytes=100_000)

        assert summary.total_size_bytes == 80_000
        assert summary.is_within_budget is True
        assert summary.status == "pass"
        assert len(summary.font_status) == 1
        assert summary.font_status[0].status == "pass"
        assert summary.font_status[0].is_within_budget is True

    def test_evaluate_budget_single_font_warning(self):
        """Font between 80-100% of budget returns warning status."""
        asset = WebFontAsset("font.woff2", "font/woff2", b"x" * 90_000)
        summary = WebFontPerformanceAdvisor.evaluate_budget([asset], per_font_budget_bytes=100_000)

        assert summary.font_status[0].status == "warning"

    def test_evaluate_budget_single_font_exceeded(self):
        """Font exceeding budget returns exceeded status."""
        asset = WebFontAsset("font.woff2", "font/woff2", b"x" * 110_000)
        summary = WebFontPerformanceAdvisor.evaluate_budget([asset], per_font_budget_bytes=100_000)

        assert summary.font_status[0].status == "exceeded"
        assert summary.font_status[0].is_within_budget is False

    def test_evaluate_budget_family_with_total_budget(self):
        """Family budget is evaluated against total size."""
        assets = [
            WebFontAsset("font1.woff2", "font/woff2", b"x" * 60_000),
            WebFontAsset("font2.woff2", "font/woff2", b"x" * 70_000),
        ]
        summary = WebFontPerformanceAdvisor.evaluate_budget(
            assets,
            per_font_budget_bytes=100_000,
            total_family_budget_bytes=150_000,
        )

        assert summary.total_size_bytes == 130_000
        assert summary.is_within_budget is True
        assert summary.status == "warning"

    def test_evaluate_budget_family_exceeds_total_budget(self):
        """Family exceeding total budget returns exceeded status."""
        assets = [
            WebFontAsset("font1.woff2", "font/woff2", b"x" * 80_000),
            WebFontAsset("font2.woff2", "font/woff2", b"x" * 90_000),
        ]
        summary = WebFontPerformanceAdvisor.evaluate_budget(
            assets,
            per_font_budget_bytes=100_000,
            total_family_budget_bytes=150_000,
        )

        assert summary.is_within_budget is False
        assert summary.status == "exceeded"

    def test_evaluate_budget_default_budget_values(self):
        """Default budget values are applied when not specified."""
        asset = WebFontAsset("font.woff2", "font/woff2", b"x" * 50_000)
        summary = WebFontPerformanceAdvisor.evaluate_budget([asset])

        assert summary.total_size_bytes == 50_000
        assert summary.is_within_budget is True
        assert summary.status == "pass"

    def test_evaluate_budget_size_ratio_calculation(self):
        """Size ratio is correctly calculated."""
        asset = WebFontAsset("font.woff2", "font/woff2", b"x" * 75_000)
        summary = WebFontPerformanceAdvisor.evaluate_budget([asset], per_font_budget_bytes=100_000)

        assert summary.font_status[0].size_ratio == 0.75

    def test_evaluate_budget_dict_input(self):
        """Accepts dict input with filename and size."""
        fonts = [
            {"filename": "font.woff2", "size": 60_000},
        ]
        summary = WebFontPerformanceAdvisor.evaluate_budget(fonts, per_font_budget_bytes=100_000)

        assert summary.font_status[0].size_bytes == 60_000
        assert summary.font_status[0].status == "pass"


class TestWebFontPerformanceAdvisorHelperMethods:
    """Tests for internal helper methods."""

    def test_determine_media_type_woff2(self):
        """WOFF2 extension returns correct MIME type."""
        assert WebFontPerformanceAdvisor._determine_media_type("font.woff2") == "font/woff2"

    def test_determine_media_type_woff(self):
        """WOFF extension returns correct MIME type."""
        assert WebFontPerformanceAdvisor._determine_media_type("font.woff") == "font/woff"

    def test_determine_media_type_ttf(self):
        """TTF extension returns correct MIME type."""
        assert WebFontPerformanceAdvisor._determine_media_type("font.ttf") == "font/ttf"

    def test_determine_media_type_otf(self):
        """OTF extension returns correct MIME type."""
        assert WebFontPerformanceAdvisor._determine_media_type("font.otf") == "font/otf"

    def test_determine_media_type_eot(self):
        """EOT extension returns correct MIME type."""
        assert WebFontPerformanceAdvisor._determine_media_type("font.eot") == "font/eot"

    def test_determine_media_type_unknown_returns_default(self):
        """Unknown extension returns font/woff2 as fallback."""
        assert WebFontPerformanceAdvisor._determine_media_type("font.unknown") == "font/woff2"

    def test_determine_size_from_webfont_asset(self):
        """Extracts size from WebFontAsset.data."""
        asset = WebFontAsset("font.woff2", "font/woff2", b"x" * 12345)
        assert WebFontPerformanceAdvisor._determine_size(asset) == 12345

    def test_determine_size_from_dict_with_size(self):
        """Extracts size from dict['size']."""
        assert WebFontPerformanceAdvisor._determine_size({"filename": "font.woff2", "size": 54321}) == 54321

    def test_determine_size_from_dict_with_data(self):
        """Extracts size from dict['data']."""
        assert WebFontPerformanceAdvisor._determine_size({"filename": "font.woff2", "data": b"x" * 99999}) == 99999


class TestWebFontPerformanceAdvisorIntegration:
    """Integration tests for real-world usage scenarios."""

    def test_generate_preload_tags_with_budget_summary(self):
        """Preload tags and budget summary can be correlated."""
        assets = [
            WebFontAsset("font-light.woff2", "font/woff2", b"x" * 60_000),
            WebFontAsset("font-bold.woff2", "font/woff2", b"x" * 90_000),
        ]
        tags = WebFontPerformanceAdvisor.generate_preload_tags(assets)
        summary = WebFontPerformanceAdvisor.evaluate_budget(assets)

        assert len(tags) == 2
        assert 'font-light.woff2' in tags[0]
        assert 'font-bold.woff2' in tags[1]
        assert summary.total_size_bytes == 150_000
        assert summary.font_status[0].filename == "font-light.woff2"
        assert summary.font_status[1].filename == "font-bold.woff2"

    def test_real_world_font_collection_evaluation(self):
        """Evaluate a realistic font collection with various sizes."""
        assets = [
            WebFontAsset("latin.woff2", "font/woff2", b"x" * 45_000),
            WebFontAsset("latin-ext.woff2", "font/woff2", b"x" * 85_000),
            WebFontAsset("cyrillic.woff2", "font/woff2", b"x" * 78_000),
        ]
        summary = WebFontPerformanceAdvisor.evaluate_budget(
            assets,
            per_font_budget_bytes=100_000,
        )

        assert summary.total_size_bytes == 208_000
        assert summary.font_status[0].status == "pass"
        assert summary.font_status[1].status == "warning"
        assert summary.font_status[2].status == "pass"
        assert summary.is_within_budget is True
        assert summary.performance_note is not None
        assert "budget" in summary.performance_note.lower() or "warning" in summary.performance_note.lower() or "pass" in summary.performance_note.lower()
