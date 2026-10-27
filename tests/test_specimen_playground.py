"""Tests for WebFontOptimizer.build_interactive_playground method (FONT-424)."""

from __future__ import annotations

from pathlib import Path

import pytest

from aspose_font import FontLoader, WebFontOptimizer
from aspose_font.ttf.font import TtfFont

ROBOTO_PATH = Path(__file__).resolve().parents[1] / "testdata" / "Roboto-VariableFont_wdth,wght.ttf"


@pytest.fixture(scope="module")
def roboto() -> TtfFont:
    font = FontLoader.open(str(ROBOTO_PATH))
    assert isinstance(font, TtfFont)
    return font


class TestInteractivePlaygroundBasic:
    """Test basic HTML generation."""

    def test_interactive_playground_returns_html_string(self, roboto: TtfFont) -> None:
        """Verify build_interactive_playground returns a standalone HTML string."""
        html = WebFontOptimizer.build_interactive_playground(
            font=roboto,
            family="Roboto",
            style="Regular",
            preview_text="Hello World",
            specimen_template="classic",
            export_mode="live",
            export_note=None,
        )

        assert isinstance(html, str)
        assert len(html) > 0
        assert "<!doctype html>" in html
        assert "<html" in html.lower()
        assert "</html>" in html.lower()

    def test_interactive_playground_contains_specimen_text(self, roboto: TtfFont) -> None:
        """Verify specimen text is present in generated HTML."""
        preview_text = "The quick brown fox"
        html = WebFontOptimizer.build_interactive_playground(
            font=roboto,
            family="Roboto",
            style="Regular",
            preview_text=preview_text,
            specimen_template="classic",
            export_mode="live",
            export_note=None,
        )

        assert preview_text in html

    def test_interactive_playground_contains_copyable_css_snippet(self, roboto: TtfFont) -> None:
        """Verify CSS snippet is present in generated HTML."""
        html = WebFontOptimizer.build_interactive_playground(
            font=roboto,
            family="Roboto",
            style="Regular",
            preview_text="Test",
            specimen_template="classic",
            export_mode="live",
            export_note=None,
        )

        assert "@font-face" in html
        assert "url('./fonts.css')" in html
        assert "woff2" in html


class TestInteractivePlaygroundAxisSliders:
    """Test variable font axis slider binding."""

    def test_interactive_playground_has_axis_sliders(self, roboto: TtfFont) -> None:
        """Verify sliders are generated for variable axes."""
        html = WebFontOptimizer.build_interactive_playground(
            font=roboto,
            family="Roboto",
            style="Regular",
            preview_text="Test",
            specimen_template="classic",
            export_mode="live",
            export_note=None,
        )

        assert 'class="axis-control"' in html
        assert 'data-axis="wght"' in html
        assert 'data-axis="wdth"' in html

    def test_interactive_playground_axis_sliders_bind_to_css(self, roboto: TtfFont) -> None:
        """Verify sliders are bound to font-variation-settings CSS property."""
        html = WebFontOptimizer.build_interactive_playground(
            font=roboto,
            family="Roboto",
            style="Regular",
            preview_text="Test",
            specimen_template="classic",
            export_mode="live",
            export_note=None,
        )

        assert "fontVariationSettings" in html
        assert "updateVariationSettings()" in html
        assert 'input.addEventListener(\'input\', updateVariationSettings)' in html

    def test_interactive_playground_axis_range_values(self, roboto: TtfFont) -> None:
        """Verify axis sliders have correct min/max/default values."""
        html = WebFontOptimizer.build_interactive_playground(
            font=roboto,
            family="Roboto",
            style="Regular",
            preview_text="Test",
            specimen_template="classic",
            export_mode="live",
            export_note=None,
        )

        assert 'min="' in html
        assert 'max="' in html
        assert 'value="' in html

    def test_interactive_playground_axis_value_display(self, roboto: TtfFont) -> None:
        """Verify axis value displays are present."""
        html = WebFontOptimizer.build_interactive_playground(
            font=roboto,
            family="Roboto",
            style="Regular",
            preview_text="Test",
            specimen_template="classic",
            export_mode="live",
            export_note=None,
        )

        assert 'data-axis-value="' in html
        assert '<span class="axis-value"' in html


class TestInteractivePlaygroundFontControls:
    """Test font size, line height, and sample text controls."""

    def test_interactive_playground_has_sample_text_control(self, roboto: TtfFont) -> None:
        """Verify sample text textarea is present."""
        html = WebFontOptimizer.build_interactive_playground(
            font=roboto,
            family="Roboto",
            style="Regular",
            preview_text="Test",
            specimen_template="classic",
            export_mode="live",
            export_note=None,
        )

        assert 'id="specimen-text"' in html
        assert '<textarea' in html

    def test_interactive_playground_has_font_size_control(self, roboto: TtfFont) -> None:
        """Verify font size slider is present."""
        html = WebFontOptimizer.build_interactive_playground(
            font=roboto,
            family="Roboto",
            style="Regular",
            preview_text="Test",
            specimen_template="classic",
            export_mode="live",
            export_note=None,
        )

        assert 'id="font-size"' in html
        assert 'type="range"' in html
        assert 'min="16"' in html
        assert 'max="128"' in html
        assert 'id="font-size-value"' in html

    def test_interactive_playground_has_line_height_control(self, roboto: TtfFont) -> None:
        """Verify line height slider is present."""
        html = WebFontOptimizer.build_interactive_playground(
            font=roboto,
            family="Roboto",
            style="Regular",
            preview_text="Test",
            specimen_template="classic",
            export_mode="live",
            export_note=None,
        )

        assert 'id="line-height"' in html
        assert 'type="range"' in html
        assert 'min="0.8"' in html
        assert 'max="2.0"' in html
        assert 'id="line-height-value"' in html

    def test_interactive_playground_font_controls_javascript(self, roboto: TtfFont) -> None:
        """Verify font control JavaScript is present."""
        html = WebFontOptimizer.build_interactive_playground(
            font=roboto,
            family="Roboto",
            style="Regular",
            preview_text="Test",
            specimen_template="classic",
            export_mode="live",
            export_note=None,
        )

        assert "fontSizeInput" in html
        assert "lineHeightInput" in html
        assert "specimenText" in html


class TestInteractivePlaygroundDarkMode:
    """Test dark mode functionality."""

    def test_interactive_playground_has_dark_mode_toggle(self, roboto: TtfFont) -> None:
        """Verify dark mode toggle button is present."""
        html = WebFontOptimizer.build_interactive_playground(
            font=roboto,
            family="Roboto",
            style="Regular",
            preview_text="Test",
            specimen_template="classic",
            export_mode="live",
            export_note=None,
        )

        assert 'id="dark-mode-toggle"' in html
        assert "Dark Mode" in html

    def test_interactive_playground_dark_mode_css_class(self, roboto: TtfFont) -> None:
        """Verify dark mode CSS class is present."""
        html = WebFontOptimizer.build_interactive_playground(
            font=roboto,
            family="Roboto",
            style="Regular",
            preview_text="Test",
            specimen_template="classic",
            export_mode="live",
            export_note=None,
            dark_mode=True,
        )

        assert "dark-mode" in html.lower()

    def test_interactive_playground_no_dark_mode_by_default(self, roboto: TtfFont) -> None:
        """Verify dark mode is not enabled by default."""
        html = WebFontOptimizer.build_interactive_playground(
            font=roboto,
            family="Roboto",
            style="Regular",
            preview_text="Test",
            specimen_template="classic",
            export_mode="live",
            export_note=None,
        )

        assert "html.dark-mode" not in html


class TestInteractivePlaygroundNoFontControls:
    """Test exclude font controls option."""

    def test_interactive_playground_no_font_controls_excludes_controls(self, roboto: TtfFont) -> None:
        """Verify font controls are excluded when include_font_controls=False."""
        html = WebFontOptimizer.build_interactive_playground(
            font=roboto,
            family="Roboto",
            style="Regular",
            preview_text="Test",
            specimen_template="classic",
            export_mode="live",
            export_note=None,
            include_font_controls=False,
        )

        assert 'id="specimen-text"' not in html
        assert 'id="font-size"' not in html
        assert 'id="line-height"' not in html
        assert 'id="dark-mode-toggle"' not in html

    def test_interactive_playground_no_font_controls_sliders_present(self, roboto: TtfFont) -> None:
        """Verify axis sliders are still present without font controls."""
        html = WebFontOptimizer.build_interactive_playground(
            font=roboto,
            family="Roboto",
            style="Regular",
            preview_text="Test",
            specimen_template="classic",
            export_mode="live",
            export_note=None,
            include_font_controls=False,
        )

        assert 'class="axis-control"' in html
        assert 'data-axis="wght"' in html


class TestInteractivePlaygroundStaticFont:
    """Test static font handling."""

    def test_interactive_playground_static_font_no_axis_controls(
        self,
        roboto: TtfFont,
    ) -> None:
        """Verify static fonts don't get axis controls."""
        from aspose_font import WebFontBuilder

        bundle = WebFontBuilder.build(
            roboto,
            instance_coordinates={"wght": 700.0},
            include_woff=False,
        )

        html = WebFontOptimizer.build_interactive_playground(
            font=bundle.preview_font,
            family=bundle.family,
            style=bundle.style,
            preview_text="Test",
            specimen_template="classic",
            export_mode="static",
            export_note=None,
        )

        assert 'class="axis-controls"' not in html
        assert 'class="axis-control"' not in html


class TestInteractivePlaygroundCSSStyles:
    """Test CSS styles in generated HTML."""

    def test_interactive_playground_contains_specimen_template_css(self, roboto: TtfFont) -> None:
        """Verify specimen template CSS is included."""
        html = WebFontOptimizer.build_interactive_playground(
            font=roboto,
            family="Roboto",
            style="Regular",
            preview_text="Test",
            specimen_template="editorial",
            export_mode="live",
            export_note=None,
        )

        assert "specimen-template-editorial" in html
        assert "body.specimen-template-editorial" in html

    def test_interactive_playground_contains_playground_control_css(self, roboto: TtfFont) -> None:
        """Verify playground control CSS is included."""
        html = WebFontOptimizer.build_interactive_playground(
            font=roboto,
            family="Roboto",
            style="Regular",
            preview_text="Test",
            specimen_template="classic",
            export_mode="live",
            export_note=None,
        )

        assert ".playground-controls" in html
        assert ".axis-control" in html

    def test_interactive_playground_contains_playground_javascript(self, roboto: TtfFont) -> None:
        """Verify playground JavaScript is included."""
        html = WebFontOptimizer.build_interactive_playground(
            font=roboto,
            family="Roboto",
            style="Regular",
            preview_text="Test",
            specimen_template="classic",
            export_mode="live",
            export_note=None,
        )

        assert "<script>" in html
        assert "const specimen" in html
        assert "const axisInputs" in html


class TestInteractivePlaygroundExportNote:
    """Test export note handling."""

    def test_interactive_playground_with_export_note(self, roboto: TtfFont) -> None:
        """Verify export note is included when provided."""
        export_note = "This is a test export note"
        html = WebFontOptimizer.build_interactive_playground(
            font=roboto,
            family="Roboto",
            style="Regular",
            preview_text="Test",
            specimen_template="classic",
            export_mode="live",
            export_note=export_note,
        )

        assert export_note in html

    def test_interactive_playground_without_export_note(self, roboto: TtfFont) -> None:
        """Verify export note section is omitted when None."""
        html = WebFontOptimizer.build_interactive_playground(
            font=roboto,
            family="Roboto",
            style="Regular",
            preview_text="Test",
            specimen_template="classic",
            export_mode="live",
            export_note=None,
        )

        assert "Export Note" not in html


class TestInteractivePlaygroundTemplates:
    """Test different specimen templates."""

    @pytest.mark.parametrize("template", ("classic", "editorial", "lab"))
    def test_interactive_playground_different_templates(
        self,
        roboto: TtfFont,
        template: str,
    ) -> None:
        """Verify different specimen templates are applied."""
        html = WebFontOptimizer.build_interactive_playground(
            font=roboto,
            family="Roboto",
            style="Regular",
            preview_text="Test",
            specimen_template=template,
            export_mode="live",
            export_note=None,
        )

        assert f"specimen-template-{template}" in html


class TestInteractivePlaygroundHTMLStructure:
    """Test HTML document structure."""

    def test_interactive_playground_proper_html_structure(self, roboto: TtfFont) -> None:
        """Verify HTML has proper structure with head and body."""
        html = WebFontOptimizer.build_interactive_playground(
            font=roboto,
            family="Roboto",
            style="Regular",
            preview_text="Test",
            specimen_template="classic",
            export_mode="live",
            export_note=None,
        )

        assert "<!doctype html>" in html
        assert "<html" in html.lower()
        assert "</html>" in html.lower()
        assert "<head>" in html.lower()
        assert "</head>" in html.lower()
        assert "<body" in html.lower()
        assert "</body>" in html.lower()

    def test_interactive_playground_contains_title(self, roboto: TtfFont) -> None:
        """Verify HTML has proper title."""
        html = WebFontOptimizer.build_interactive_playground(
            font=roboto,
            family="Roboto",
            style="Regular",
            preview_text="Test",
            specimen_template="classic",
            export_mode="live",
            export_note=None,
        )

        assert "<title>" in html
        assert "Roboto Playground" in html

    def test_interactive_playground_contains_meta_tags(self, roboto: TtfFont) -> None:
        """Verify HTML has proper meta tags."""
        html = WebFontOptimizer.build_interactive_playground(
            font=roboto,
            family="Roboto",
            style="Regular",
            preview_text="Test",
            specimen_template="classic",
            export_mode="live",
            export_note=None,
        )

        assert '<meta charset="utf-8">' in html
        assert '<meta name="viewport"' in html

    def test_interactive_playground_contains_section_elements(self, roboto: TtfFont) -> None:
        """Verify HTML has proper section elements."""
        html = WebFontOptimizer.build_interactive_playground(
            font=roboto,
            family="Roboto",
            style="Regular",
            preview_text="Test",
            specimen_template="classic",
            export_mode="live",
            export_note=None,
        )

        assert "<h1>" in html
        assert "<h2>" in html
        assert "<section" in html

    def test_interactive_playground_contains_code_block(self, roboto: TtfFont) -> None:
        """Verify CSS snippet is in code block."""
        html = WebFontOptimizer.build_interactive_playground(
            font=roboto,
            family="Roboto",
            style="Regular",
            preview_text="Test",
            specimen_template="classic",
            export_mode="live",
            export_note=None,
        )

        assert "<pre>" in html
        assert "<code" in html
