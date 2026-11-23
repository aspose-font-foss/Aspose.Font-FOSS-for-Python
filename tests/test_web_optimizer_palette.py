"""Tests for FONT-500 WebFontOptimizer palette injection & dark/light theme export."""

from __future__ import annotations

from aspose_font._font_base import FontType
from aspose_font.ttf.font import TtfFont
from aspose_font.web import WebFontBuilder, WebFontOptimizer


class TestWebOptimizerPaletteInjection:
    """Test WebFontOptimizer CPAL palette detection and CSS injection."""

    def test_build_fonts_css_includes_font_palette_values_with_cpal(
        self, cpal_v1_font: TtfFont
    ) -> None:
        """Test that build_fonts_css includes @font-palette-values when font has CPAL."""
        family = "Test Font"
        font_assets = [
            WebFontBuilder._make_font_asset(cpal_v1_font, "test", FontType.WOFF2, "")
        ]

        css = WebFontOptimizer.build_fonts_css(
            font=cpal_v1_font,
            family=family,
            font_assets=font_assets,
            font_display="swap",
            specimen_template="classic",
            coverage=None,
        )

        assert "@font-palette-values {" in css

    def test_build_fonts_css_excludes_font_palette_values_without_cpal(
        self, roboto: TtfFont
    ) -> None:
        """Test that build_fonts_css doesn't include palette CSS when font has no CPAL."""
        family = "Roboto"
        font_assets = [
            WebFontBuilder._make_font_asset(roboto, "roboto", FontType.WOFF2, "")
        ]

        css = WebFontOptimizer.build_fonts_css(
            font=roboto,
            family=family,
            font_assets=font_assets,
            font_display="swap",
            specimen_template="classic",
            coverage=None,
        )

        assert "@font-palette-values" not in css
        assert "--palette-" not in css

    def test_build_fonts_css_excludes_cpal_when_include_cpal_false(
        self, cpal_v1_font: TtfFont
    ) -> None:
        """Test that include_cpal=False prevents palette CSS injection."""
        family = "Test Font"
        font_assets = [
            WebFontBuilder._make_font_asset(cpal_v1_font, "test", FontType.WOFF2, "")
        ]

        css = WebFontOptimizer.build_fonts_css(
            font=cpal_v1_font,
            family=family,
            font_assets=font_assets,
            font_display="swap",
            specimen_template="classic",
            coverage=None,
            include_cpal=False,
        )

        assert "@font-palette-values" not in css
        assert "--palette-" not in css

    def test_build_fonts_css_includes_all_palettes(self, cpal_v1_font: TtfFont) -> None:
        """Test that all palettes from CPAL table are included in CSS."""
        font_assets = [
            WebFontBuilder._make_font_asset(cpal_v1_font, "test", FontType.WOFF2, "")
        ]

        css = WebFontOptimizer.build_fonts_css(
            font=cpal_v1_font,
            family="Test Font",
            font_assets=font_assets,
            font_display="swap",
            specimen_template="classic",
            coverage=None,
        )

        cpal = cpal_v1_font.ttf_tables.cpal
        palette_count = css.count("--palette-")
        assert palette_count == len(cpal.palettes)

    def test_build_fonts_css_rgba_values_match_cpal(self, cpal_v1_font: TtfFont) -> None:
        """Test that RGBA values in CSS match CPAL table colors."""
        font_assets = [
            WebFontBuilder._make_font_asset(cpal_v1_font, "test", FontType.WOFF2, "")
        ]

        css = WebFontOptimizer.build_fonts_css(
            font=cpal_v1_font,
            family="Test Font",
            font_assets=font_assets,
            font_display="swap",
            specimen_template="classic",
            coverage=None,
        )

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


class TestWebOptimizerSpecimenHtml:
    """Test WebFontOptimizer specimen HTML with palette switcher."""

    def test_build_specimen_html_includes_palette_switcher_when_cpal_present(
        self, cpal_v1_font: TtfFont
    ) -> None:
        """Test that specimen HTML includes palette switcher UI when font has CPAL."""
        html = WebFontOptimizer.build_specimen_html(
            font=cpal_v1_font,
            family="Test Font",
            style="Regular",
            css_filename="fonts.css",
            specimen_html_filename="specimen.html",
            preview_text="Hamburgefons",
            specimen_template="classic",
            export_mode="static",
            export_note=None,
        )

        assert 'class="cpal-palette-switcher"' in html
        assert 'id="palette-select"' in html
        assert '<option value="palette-' in html

    def test_build_specimen_html_without_cpal_no_switcher(self, roboto: TtfFont) -> None:
        """Test that specimen HTML has no palette switcher when font has no CPAL."""
        html = WebFontOptimizer.build_specimen_html(
            font=roboto,
            family="Roboto",
            style="Regular",
            css_filename="fonts.css",
            specimen_html_filename="specimen.html",
            preview_text="Hamburgefons",
            specimen_template="classic",
            export_mode="static",
            export_note=None,
        )

        assert "cpal-palette-switcher" not in html
        assert "palette-select" not in html
        assert "--palette-" not in html

    def test_build_specimen_html_switcher_default_first_palette(
        self, cpal_v1_font: TtfFont
    ) -> None:
        """Test that palette switcher includes options for all palettes."""
        html = WebFontOptimizer.build_specimen_html(
            font=cpal_v1_font,
            family="Test Font",
            style="Regular",
            css_filename="fonts.css",
            specimen_html_filename="specimen.html",
            preview_text="Hamburgefons",
            specimen_template="classic",
            export_mode="static",
            export_note=None,
        )

        cpal = cpal_v1_font.ttf_tables.cpal
        for idx in range(len(cpal.palettes)):
            assert f"palette-{idx}" in html

    def test_build_specimen_html_includes_dark_mode_media_query(
        self, cpal_v1_font: TtfFont
    ) -> None:
        """Test that specimen HTML includes @media query for dark mode."""
        html = WebFontOptimizer.build_specimen_html(
            font=cpal_v1_font,
            family="Test Font",
            style="Regular",
            css_filename="fonts.css",
            specimen_html_filename="specimen.html",
            preview_text="Hamburgefons",
            specimen_template="classic",
            export_mode="static",
            export_note=None,
        )

        assert "@media (prefers-color-scheme: dark)" in html
        assert ".cpal-palette-switcher" in html


class TestWebOptimizerIntegration:
    """Integration tests for full WebFontOptimizer workflow with palette."""

    def test_build_includes_cpal_css(self, cpal_v1_font: TtfFont) -> None:
        """Test that full build() includes CPAL CSS in output."""
        package = WebFontOptimizer.build(
            font=cpal_v1_font,
            specimen_template="classic",
        )

        assert "@font-palette-values" in package.css
        assert "--palette-" in package.css
        assert 'class="cpal-palette-switcher"' in package.specimen_html

    def test_build_without_cpal_no_palette_css(self, roboto: TtfFont) -> None:
        """Test that build() without CPAL font doesn't include palette CSS."""
        package = WebFontOptimizer.build(
            font=roboto,
            specimen_template="classic",
        )

        assert "@font-palette-values" not in package.css
        assert "--palette-" not in package.css
        assert "cpal-palette-switcher" not in package.specimen_html
