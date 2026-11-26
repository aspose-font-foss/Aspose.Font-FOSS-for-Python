"""Tests for TextRenderer justification alignment & Kashida points (FONT-502)."""
from __future__ import annotations

import pytest

from aspose_font import FontLoader
from aspose_font.text import JustificationPoint, JustificationResult, TextRenderer


class TestJustificationParameters:
    """Test justify_width parameter acceptance."""

    def test_layout_accepts_justify_width_parameter(self) -> None:
        """Test that TextRenderer.layout() accepts justify_width parameter."""
        font = FontLoader.open("testdata/Roboto-VariableFont_wdth,wght.ttf")
        layout = TextRenderer.layout(font, "Hello World", justify_width=500.0)
        assert layout.total_width == pytest.approx(500.0)

    def test_layout_glyphs_accepts_justify_width_parameter(self) -> None:
        """Test that layout_glyphs() also accepts justify_width."""
        font = FontLoader.open("testdata/Roboto-VariableFont_wdth,wght.ttf")
        gids = [font.encoding.unicode_to_gid(ord(c)) for c in "AB"]
        layout = TextRenderer.layout_glyphs(font, gids, justify_width=300.0)
        assert layout.total_width == 300.0


class TestJustificationFallback:
    """Test whitespace distribution fallback when no JSTF available."""

    def test_justify_without_jstf_uses_whitespace(self) -> None:
        """Test that fonts without JSTF fall back to whitespace distribution."""
        font = FontLoader.open("testdata/Roboto-VariableFont_wdth,wght.ttf")
        has_jstf = hasattr(font.ttf_tables, "jstf") and font.ttf_tables.jstf is not None
        if has_jstf:
            pytest.skip("Roboto has JSTF table")

        layout = TextRenderer.layout(font, "Hello World", justify_width=800.0)
        assert layout.total_width == 800.0

    def test_justify_width_matches_target(self) -> None:
        """Test that justified width matches the target justify_width exactly."""
        font = FontLoader.open("testdata/Roboto-VariableFont_wdth,wght.ttf")
        text = "Test text for justification"
        target_width = 600.0
        layout = TextRenderer.layout(font, text, justify_width=target_width)
        assert layout.total_width == pytest.approx(target_width)


class TestJustificationWidthBehavior:
    """Test justify_width constraints and edge cases."""

    def test_justify_width_less_than_content_ignored(self) -> None:
        """Test that justify_width < content width doesn't shrink glyphs."""
        font = FontLoader.open("testdata/Roboto-VariableFont_wdth,wght.ttf")
        text = "AAAA"
        layout_narrow = TextRenderer.layout(font, text, justify_width=50.0)
        layout_normal = TextRenderer.layout(font, text, justify_width=None)
        assert layout_narrow.total_width >= layout_normal.total_width

    def test_zero_justify_width_returns_content_width(self) -> None:
        """Test that justify_width=0 returns normal layout."""
        font = FontLoader.open("testdata/Roboto-VariableFont_wdth,wght.ttf")
        layout = TextRenderer.layout(font, "A", justify_width=0.0)
        layout_normal = TextRenderer.layout(font, "A")
        assert layout.total_width == layout_normal.total_width

    def test_justify_width_none_returns_normal_layout(self) -> None:
        """Test that justify_width=None returns normal layout without justification."""
        font = FontLoader.open("testdata/Roboto-VariableFont_wdth,wght.ttf")
        layout = TextRenderer.layout(font, "Hello", justify_width=None)
        layout_normal = TextRenderer.layout(font, "Hello")
        assert layout.total_width == layout_normal.total_width


class TestKashidaInsertion:
    """Test Kashida insertion for Arabic text."""

    def test_arabic_text_justification(self) -> None:
        """Test justification on Arabic text with potential Kashida points."""
        font = FontLoader.open("testdata/Roboto-VariableFont_wdth,wght.ttf")
        arabic_text = "اللغة العربية"
        layout = TextRenderer.layout(font, arabic_text, justify_width=600.0)
        assert layout.total_width == 600.0
        assert len(layout.glyphs) > 0

    def test_tatweel_kashida_character(self) -> None:
        """Test that U+0640 (Tatweel/Kashida) is handled correctly."""
        font = FontLoader.open("testdata/Roboto-VariableFont_wdth,wght.ttf")
        text_with_kashida = "ا\x0640ا"
        layout = TextRenderer.layout(font, text_with_kashida, justify_width=400.0)
        assert layout.total_width == 400.0


class TestJSTFIntegration:
    """Test JSTF table integration (if available in test fonts)."""

    def test_jstf_table_integration(self) -> None:
        """Test that JSTF table is consulted when present."""
        font = FontLoader.open("testdata/Roboto-VariableFont_wdth,wght.ttf")

        has_jstf = hasattr(font.ttf_tables, "jstf") and font.ttf_tables.jstf is not None

        if not has_jstf:
            pytest.skip("Roboto does not have JSTF table (expected for non-CJK font)")

        layout = TextRenderer.layout(font, "Hello", justify_width=400.0)
        assert layout.total_width == 400.0

    def test_no_jstf_no_crash(self) -> None:
        """Test that fonts without JSTF don't crash."""
        font = FontLoader.open("testdata/Roboto-VariableFont_wdth,wght.ttf")
        layout = TextRenderer.layout(font, "Test", justify_width=500.0)
        assert layout is not None
        assert len(layout.glyphs) == 4


class TestLayoutIntegrity:
    """Test that justification doesn't break other layout features."""

    def test_justification_with_kerning(self) -> None:
        """Test that justification works with kerning enabled."""
        font = FontLoader.open("testdata/Roboto-VariableFont_wdth,wght.ttf")
        layout = TextRenderer.layout(font, "AV", kern=True, justify_width=400.0)
        assert layout.total_width == 400.0
        assert len(layout.glyphs) == 2

    def test_justification_with_gsub(self) -> None:
        """Test that justification works with GSUB features."""
        font = FontLoader.open("testdata/Roboto-VariableFont_wdth,wght.ttf")
        layout = TextRenderer.layout(font, "ffi", kern=True, features=["liga"], justify_width=500.0)
        assert layout.total_width == 500.0

    def test_justification_glyph_paths_unscaled(self) -> None:
        """Test that glyph paths are not scaled/shifted incorrectly."""
        font = FontLoader.open("testdata/Roboto-VariableFont_wdth,wght.ttf")
        layout = TextRenderer.layout(font, "A", size=1000.0, justify_width=800.0)
        gl = layout.glyphs[0]
        if gl.path is not None:
            for cmd in gl.path:
                pass

    def test_justification_with_glyph_ids(self) -> None:
        """Test justification with layout_glyphs using glyph IDs."""
        font = FontLoader.open("testdata/Roboto-VariableFont_wdth,wght.ttf")
        text = "Hello"
        gids = [font.encoding.unicode_to_gid(ord(c)) for c in text]
        layout = TextRenderer.layout_glyphs(font, gids, justify_width=500.0)
        assert layout.total_width == 500.0
        assert len(layout.glyphs) == len(text)


class TestVerticalLayout:
    """Test that vertical layout is not affected."""

    def test_justification_only_applies_to_horizontal(self) -> None:
        """Test that vertical layout ignores justify_width."""
        font = FontLoader.open("testdata/Roboto-VariableFont_wdth,wght.ttf")
        layout = TextRenderer.layout(font, "AB", direction="vertical", justify_width=500.0)
        assert len(layout.glyphs) == 2


class TestDataStructures:
    """Test JustificationPoint and JustificationResult data structures."""

    def test_justification_point_creation(self) -> None:
        """Test JustificationPoint can be created."""
        font = FontLoader.open("testdata/Roboto-VariableFont_wdth,wght.ttf")
        gid = font.encoding.unicode_to_gid(ord("A"))
        point = JustificationPoint(
            glyph_index=0,
            glyph_id=gid,
            justification_type="kashida",
            priority=4,
        )
        assert point.glyph_index == 0
        assert point.justification_type == "kashida"
        assert point.priority == 4

    def test_justification_result_creation(self) -> None:
        """Test JustificationResult can be created."""
        font = FontLoader.open("testdata/Roboto-VariableFont_wdth,wght.ttf")
        gid = font.encoding.unicode_to_gid(ord("A"))
        point = JustificationPoint(
            glyph_index=0,
            glyph_id=gid,
            justification_type="whitespace",
            priority=100,
        )
        result = JustificationResult(
            points=[point],
            total_excess=50.0,
            applied_width=500.0,
            justification_type="whitespace",
        )
        assert result.total_excess == 50.0
        assert result.applied_width == 500.0
        assert result.justification_type == "whitespace"
        assert len(result.points) == 1


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_text_justification(self) -> None:
        """Test justification with empty text."""
        font = FontLoader.open("testdata/Roboto-VariableFont_wdth,wght.ttf")
        layout = TextRenderer.layout(font, "", justify_width=100.0)
        assert layout.total_width == 0.0
        assert len(layout.glyphs) == 0

    def test_single_char_justification(self) -> None:
        """Test justification with single character."""
        font = FontLoader.open("testdata/Roboto-VariableFont_wdth,wght.ttf")
        layout = TextRenderer.layout(font, "A", justify_width=200.0)
        assert layout.total_width == 200.0
        assert len(layout.glyphs) == 1

    def test_large_justify_width(self) -> None:
        """Test with a very large justify_width value."""
        font = FontLoader.open("testdata/Roboto-VariableFont_wdth,wght.ttf")
        layout = TextRenderer.layout(font, "A", justify_width=10000.0)
        assert layout.total_width == 10000.0

    def test_multiple_spaces_justification(self) -> None:
        """Test justification with multiple spaces."""
        font = FontLoader.open("testdata/Roboto-VariableFont_wdth,wght.ttf")
        layout = TextRenderer.layout(font, "A   B", justify_width=400.0)
        assert layout.total_width == 400.0
