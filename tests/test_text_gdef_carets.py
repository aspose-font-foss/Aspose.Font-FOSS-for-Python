"""Tests for GDEF caret integration in TextRenderer (FONT-466)."""
from __future__ import annotations

import pytest

from aspose_font import FontLoader
from aspose_font._types import GlyphId
from aspose_font.text import GlyphLayout, TextRenderer


class TestGlyphLayoutCaretOffsets:
    """Test GlyphLayout.caret_offsets field."""

    def test_caret_offsets_default_empty(self) -> None:
        """Test that default GlyphLayout has empty caret_offsets list."""
        font = FontLoader.open("testdata/Roboto-VariableFont_wdth,wght.ttf")
        layout = TextRenderer.layout(font, "A", size=100.0)
        gl = layout.glyphs[0]
        assert isinstance(gl, GlyphLayout)
        assert hasattr(gl, "caret_offsets")
        assert isinstance(gl.caret_offsets, list)
        assert len(gl.caret_offsets) == 0


class TestGdefGlyphClassification:
    """Test GDEF glyph classification during layout."""

    def test_base_glyph_class_1_no_carets(self) -> None:
        """Test that base glyphs (class 1) have empty caret_offsets."""
        font = FontLoader.open("testdata/Roboto-VariableFont_wdth,wght.ttf")
        layout = TextRenderer.layout(font, "A", size=100.0)
        gl = layout.glyphs[0]
        assert gl.caret_offsets == []

    def test_ligature_carets_populated_when_gsub_applied(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that ligature glyphs from GSUB have caret offsets populated."""
        font = FontLoader.open("testdata/Roboto-VariableFont_wdth,wght.ttf")

        if font.ttf_tables.gsub is None:
            pytest.skip("Font has no GSUB table")
        if font.ttf_tables.gdef is None:
            pytest.skip("Font has no GDEF table")

        # Mock GSUB ligature substitution and GDEF ligature carets for ligature glyph
        base_glyphs = font.glyph_accessor.get_glyphs_for_text("ffi")
        seq = tuple(g.glyph_id for g in base_glyphs)
        lig_gid = GlyphId(469)  # Glyph 469 is classified as ligature (class 2) in Roboto's GDEF

        monkeypatch.setattr(
            font.ttf_tables.gsub,
            "get_ligatures",
            lambda feature_tag="liga": {seq: lig_gid},
        )
        monkeypatch.setattr(
            font.ttf_tables.gdef,
            "get_ligature_carets",
            lambda gid: [150, 300] if font.ttf_tables.gdef.get_glyph_class(int(gid)) == 2 else [],
        )

        layout = TextRenderer.layout(font, "ffi", size=100.0, features=["liga"])

        has_ligature = any(len(gl.caret_offsets) > 0 for gl in layout.glyphs)
        assert has_ligature, "Expected at least one ligature with caret offsets"
        lig_glyphs = [gl for gl in layout.glyphs if len(gl.caret_offsets) > 0]
        assert lig_glyphs[0].glyph_id == lig_gid
        assert lig_glyphs[0].caret_offsets == [150, 300]


class TestGdefMissingTableHandling:
    """Test graceful handling when GDEF table is missing."""

    def test_no_error_when_gdef_is_none(self) -> None:
        """Test that missing GDEF table does not raise errors."""
        font = FontLoader.open("testdata/Roboto-VariableFont_wdth,wght.ttf")
        layout = TextRenderer.layout(font, "test", size=100.0, features=["liga"])
        assert layout is not None
        for gl in layout.glyphs:
            assert hasattr(gl, "caret_offsets")
            assert isinstance(gl.caret_offsets, list)

    def test_empty_carets_for_non_ligature(self) -> None:
        """Test that non-ligature glyphs get empty lists even with GDEF."""
        font = FontLoader.open("testdata/Roboto-VariableFont_wdth,wght.ttf")

        if font.ttf_tables.gdef is None:
            pytest.skip("Font has no GDEF table")

        layout = TextRenderer.layout(font, "A", size=100.0)
        assert layout.glyphs[0].caret_offsets == []
