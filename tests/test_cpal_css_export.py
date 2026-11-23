"""Tests for FONT-498 OpenType CPAL color palette CSS export."""

from __future__ import annotations

import pytest

from aspose_font._exceptions import FontNotSupportedException
from aspose_font.ttf.font import TtfFont
from aspose_font.web import WebFontOptimizer


class TestCpalCssExport:
    """Test WebFontOptimizer.generate_cpal_css function."""

    def test_generate_cpal_css_returns_css_string_with_at_font_face_and_root(
        self, cpal_v1_font: TtfFont
    ) -> None:
        """Test that generate_cpal_css returns CSS with @font-face and .my-font blocks."""
        css = WebFontOptimizer.generate_cpal_css(cpal_v1_font)

        assert "@font-face {" in css
        assert "font-family:" in css
        assert "src:" in css
        assert "font-display: swap;" in css
        assert ".my-font {" in css
        assert "--palette-0:" in css

    def test_generate_cpal_css_includes_correct_number_of_palette_variables(
        self, cpal_v1_font: TtfFont
    ) -> None:
        """Test that number of palette variables matches CPAL palettes count."""
        css = WebFontOptimizer.generate_cpal_css(cpal_v1_font)
        cpal = cpal_v1_font.ttf_tables.cpal

        palette_count = css.count("--palette-")
        assert palette_count == len(cpal.palettes)

    def test_generate_cpal_css_rgba_values_match_cpal_table(
        self, cpal_v1_font: TtfFont
    ) -> None:
        """Test that RGBA values in CSS match CPAL table colors."""
        css = WebFontOptimizer.generate_cpal_css(cpal_v1_font)
        cpal = cpal_v1_font.ttf_tables.cpal

        for palette_idx, palette in enumerate(cpal.palettes):
            palette_var = f"--palette-{palette_idx}:"
            assert palette_var in css

            for color_idx, expected_color in enumerate(palette.colors):
                r, g, b, a = expected_color
                if a == 255:
                    expected_rgba = f"rgba({r}, {g}, {b}, 1)"
                else:
                    alpha_float = a / 255.0
                    expected_rgba = f"rgba({r}, {g}, {b}, {alpha_float:.1f})"

                assert expected_rgba in css

    def test_generate_cpal_css_with_custom_selector(self, cpal_v1_font: TtfFont) -> None:
        """Test that custom selector is used instead of :root."""
        custom_selector = ".my-custom-class"
        css = WebFontOptimizer.generate_cpal_css(cpal_v1_font, selector=custom_selector)

        assert f"{custom_selector} {{" in css
        assert ":root {" not in css

    def test_generate_cpal_css_raises_exception_without_cpal(
        self, roboto: TtfFont
    ) -> None:
        """Test that FontNotSupportedException is raised for font without CPAL."""
        font_without_cpal = roboto

        with pytest.raises(FontNotSupportedException) as exc_info:
            WebFontOptimizer.generate_cpal_css(font_without_cpal)

        assert "CPAL" in str(exc_info.value)
        assert "color palette" in str(exc_info.value).lower()

    def test_generate_cpal_css_handles_alpha_channel_correctly(
        self, cpal_v1_font_with_alpha: TtfFont
    ) -> None:
        """Test that alpha channel values are correctly converted to CSS floats."""
        css = WebFontOptimizer.generate_cpal_css(cpal_v1_font_with_alpha)
        cpal = cpal_v1_font_with_alpha.ttf_tables.cpal

        for palette in cpal.palettes:
            for r, g, b, a in palette.colors:
                if a == 255:
                    assert "rgba(" in css
                    assert ", 1)" in css
                else:
                    expected_alpha = a / 255.0
                    expected_rgba = f"rgba({r}, {g}, {b}, {expected_alpha:.1f})"
                    assert expected_rgba in css

    def test_generate_cpal_css_invalid_selector_raises_error(
        self, cpal_v1_font: TtfFont
    ) -> None:
        """Test that invalid selector raises ValueError."""
        with pytest.raises(ValueError):
            WebFontOptimizer.generate_cpal_css(cpal_v1_font, selector="")

        with pytest.raises(ValueError):
            WebFontOptimizer.generate_cpal_css(cpal_v1_font, selector=" ")


class TestCpalCssExportIntegration:
    """Integration tests for CPAL CSS export with real font files."""

    def test_generate_cpal_css_with_lora_font(self, lora_font: TtfFont) -> None:
        """Test CPAL CSS export with Lora font if it has CPAL table."""
        try:
            css = WebFontOptimizer.generate_cpal_css(lora_font)

            assert "@font-face" in css
            assert ":root {" in css
            assert "--palette-" in css
        except FontNotSupportedException:
            pass
