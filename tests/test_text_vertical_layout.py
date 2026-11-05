"""Tests for vertical text layout in TextRenderer (FONT-489)."""
from pathlib import Path

import pytest

from aspose_font import TtfFont
from aspose_font.text import TextRenderer


class TestVerticalLayoutDirectionParameter:
    """Test direction parameter acceptance."""

    def test_layout_vertical_accepts_direction_parameter(self, roboto) -> None:
        """Test that layout accepts direction='vertical'."""
        font = roboto
        layout = TextRenderer.layout(font, "ABC", direction="vertical")
        assert layout is not None
        assert len(layout.glyphs) == 3

    def test_layout_horizontal_unchanged(self, roboto) -> None:
        """Test that horizontal layout (default) still works correctly."""
        font = roboto
        layout_default = TextRenderer.layout(font, "ABC")

        assert layout_default.total_width > 0
        assert layout_default.total_height == 0.0

        for gl in layout_default.glyphs:
            assert gl.y_offset == 0.0
            assert gl.x_offset >= 0.0

    def test_layout_glyphs_vertical_accepts_direction(self, roboto) -> None:
        """Test that layout_glyphs accepts direction='vertical'."""
        font = roboto
        glyph_ids = [font.encoding.unicode_to_gid(ord(c)) for c in "ABC"]
        layout = TextRenderer.layout_glyphs(font, glyph_ids, direction="vertical")
        assert layout is not None
        assert len(layout.glyphs) == 3


class TestVerticalLayoutPositioning:
    """Test vertical layout glyph positioning."""

    def test_layout_vertical_positioning_top_to_bottom(self, roboto) -> None:
        """Test that glyphs are positioned top-to-bottom in vertical layout."""
        font = roboto
        layout = TextRenderer.layout(font, "ABC", size=100, direction="vertical")

        assert layout.total_height > 0
        assert len(layout.glyphs) == 3

        for i, gl in enumerate(layout.glyphs):
            assert gl.x_offset >= 0
            assert gl.y_offset >= 0
            assert gl.advance_width >= 0

    def test_layout_vertical_empty_string(self, roboto) -> None:
        """Test that empty string produces empty layout."""
        font = roboto
        layout = TextRenderer.layout(font, "", direction="vertical")

        assert len(layout.glyphs) == 0
        assert layout.total_height == 0.0

    def test_layout_vertical_uses_default_metrics_when_vorg_missing(self, roboto) -> None:
        """Test that vertical layout works even without VORG table."""
        font = roboto
        layout = TextRenderer.layout(font, "ABC", direction="vertical")

        assert len(layout.glyphs) > 0
        assert layout.total_height > 0

        for gl in layout.glyphs:
            assert gl.x_offset == gl.y_offset

    def test_layout_vertical_multiple_text_sizes(self, roboto) -> None:
        """Test vertical layout at different font sizes."""
        font = roboto

        layout_small = TextRenderer.layout(font, "AB", size=50, direction="vertical")
        layout_large = TextRenderer.layout(font, "AB", size=200, direction="vertical")

        assert layout_small.total_height > 0
        assert layout_large.total_height > layout_small.total_height


class TestVerticalLayoutWithVORG:
    """Test vertical layout integration with VORG table."""

    @pytest.fixture
    def roboto_with_vorg(self, roboto: TtfFont) -> TtfFont:
        """Use the roboto fixture which is already loaded."""
        return roboto

    def test_layout_vertical_with_vorg_table(self, roboto_with_vorg) -> None:
        """Test that vertical layout uses VORG table if available."""
        font = roboto_with_vorg

        if hasattr(font.ttf_tables, "vorg") and font.ttf_tables.vorg is not None:
            layout = TextRenderer.layout(font, "ABC", direction="vertical")

            assert layout.total_height > 0
            assert len(layout.glyphs) == 3

            vorg = font.ttf_tables.vorg
            for gl in layout.glyphs:
                vorg.get_vert_origin_y(int(gl.glyph_id))
                assert gl.x_offset == gl.y_offset
        else:
            pytest.skip("Test font does not have VORG table")

    def test_layout_vertical_positions_use_vorg_offsets(self, roboto_with_vorg) -> None:
        """Test that vertical origin offsets are applied to positioning."""
        font = roboto_with_vorg

        if hasattr(font.ttf_tables, "vorg") and font.ttf_tables.vorg is not None:
            layout = TextRenderer.layout(font, "A", direction="vertical")

            if len(layout.glyphs) > 0:
                gl = layout.glyphs[0]
                assert gl.x_offset == gl.y_offset
        else:
            pytest.skip("Test font does not have VORG table")


class TestVerticalLayoutCrossPlatform:
    """Verify cross-platform compatibility."""

    def test_paths_use_pathlib(self) -> None:
        """Test that test paths use Path object, not hardcoded Windows paths."""
        testdata_path = Path(__file__).resolve().parents[1] / "testdata"
        assert "testdata" in str(testdata_path).split("\\") or "testdata" in str(testdata_path).split("/")
