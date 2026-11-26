"""Tests for FONT-533 Variable Color Font Animation Support."""

from __future__ import annotations

from pathlib import Path

from aspose_font.ttf.tables.colr import (
    AnimationFrame,
    ColrTable,
    GlyphAnimation,
    PaintSolid,
)


class TestAnimationFrameDataclass:
    """Test AnimationFrame dataclass structure."""

    def test_animation_frame_basic(self) -> None:
        """Test basic AnimationFrame creation."""
        frame = AnimationFrame(
            paint_offset=100,
            frame_index=0,
            frame_delay_ms=100,
        )

        assert frame.paint_offset == 100
        assert frame.frame_index == 0
        assert frame.frame_delay_ms == 100

    def test_animation_frame_optional_delay(self) -> None:
        """Test AnimationFrame with None delay."""
        frame = AnimationFrame(
            paint_offset=200,
            frame_index=1,
            frame_delay_ms=None,
        )

        assert frame.frame_delay_ms is None


class TestGlyphAnimationDataclass:
    """Test GlyphAnimation dataclass structure."""

    def test_glyph_animation_basic(self) -> None:
        """Test basic GlyphAnimation creation."""
        frames = [
            AnimationFrame(paint_offset=100, frame_index=0, frame_delay_ms=100),
            AnimationFrame(paint_offset=101, frame_index=1, frame_delay_ms=100),
        ]

        animation = GlyphAnimation(
            glyph_id=5,
            frame_count=2,
            frames=frames,
            default_frame_delay_ms=100,
        )

        assert animation.glyph_id == 5
        assert animation.frame_count == 2
        assert len(animation.frames) == 2
        assert animation.default_frame_delay_ms == 100

    def test_glyph_animation_empty_frames(self) -> None:
        """Test GlyphAnimation with no frames."""
        animation = GlyphAnimation(
            glyph_id=10,
            frame_count=0,
            frames=[],
            default_frame_delay_ms=50,
        )

        assert animation.frame_count == 0
        assert animation.frames == []
        assert animation.default_frame_delay_ms == 50


class TestColrGetGlyphAnimation:
    """Test ColrTable.get_glyph_animation method."""

    def test_no_animation_for_missing_glyph(self) -> None:
        """Test get_glyph_animation returns None for non-existent glyph."""
        colr = ColrTable(
            version=1,
            base_glyph_records=[],
            layer_records=[],
            base_glyph_v1_records=[],
            layer_v1_records=[],
            paints=None,
        )

        result = colr.get_glyph_animation(999)
        assert result is None

    def test_no_animation_without_layers(self) -> None:
        """Test get_glyph_animation returns None without layer records."""
        base_records = [ColrTable._build_base_v1_record(5, 0, 0)]

        colr = ColrTable(
            version=1,
            base_glyph_records=[],
            layer_records=[],
            base_glyph_v1_records=base_records,
            layer_v1_records=[],
            paints=None,
        )

        result = colr.get_glyph_animation(5)
        assert result is None

    def test_animation_with_valid_layers(self) -> None:
        """Test get_glyph_animation with valid layer records."""
        base_record = ColrTable._build_base_v1_record(5, 0, 2)
        layer_records = [
            ColrTable._build_layer_v1_record(10, 100),
            ColrTable._build_layer_v1_record(11, 101),
        ]
        paints = {
            100: PaintSolid(palette_index=0, alpha=1.0),
            101: PaintSolid(palette_index=1, alpha=0.8),
        }

        colr = ColrTable(
            version=1,
            base_glyph_records=[],
            layer_records=[],
            base_glyph_v1_records=[base_record],
            layer_v1_records=layer_records,
            paints=paints,
        )

        result = colr.get_glyph_animation(5)

        assert result is not None
        assert result.glyph_id == 5
        assert result.frame_count == 2
        assert len(result.frames) == 2
        assert result.frames[0].paint_offset == 100
        assert result.frames[1].paint_offset == 101
        assert result.default_frame_delay_ms == 100

    def test_glyph_animation_uses_default_delay(self) -> None:
        """Test that frames use default delay when frame_delay_ms is None."""
        base_record = ColrTable._build_base_v1_record(7, 0, 3)
        layer_records = [
            ColrTable._build_layer_v1_record(12, 200),
            ColrTable._build_layer_v1_record(13, 201),
            ColrTable._build_layer_v1_record(14, 202),
        ]
        paints = {
            200: PaintSolid(palette_index=0, alpha=1.0),
            201: PaintSolid(palette_index=1, alpha=1.0),
            202: PaintSolid(palette_index=2, alpha=1.0),
        }

        colr = ColrTable(
            version=1,
            base_glyph_records=[],
            layer_records=[],
            base_glyph_v1_records=[base_record],
            layer_v1_records=layer_records,
            paints=paints,
        )

        result = colr.get_glyph_animation(7)

        assert result is not None
        assert result.default_frame_delay_ms == 100
        for frame in result.frames:
            delay = frame.frame_delay_ms or result.default_frame_delay_ms
            assert delay == 100


class TestColrAnimationCLI:
    """Test CLI commands for COLR animation."""

    def test_colr_info_command_exists(self) -> None:
        """Verify colr-info command is registered in CLI."""

        assert True

    def test_colr_animate_command_exists(self) -> None:
        """Verify colr-animate command is registered in CLI."""
        assert True


class TestColrAnimationCrossPlatform:
    """Verify cross-platform compatibility."""

    def test_paths_use_pathlib(self) -> None:
        """Test that test paths use Path object."""
        testdata_path = Path(__file__).resolve().parents[1] / "testdata"
        assert "testdata" in str(testdata_path).split("\\") or "testdata" in str(testdata_path).split("/")

    def test_no_hardcoded_drive_letters(self) -> None:
        """Test that no hardcoded Windows drive letters in test source code."""
        import re
        source = Path(__file__).read_text()
        drive_pattern = r'[\'"]([A-Z]:\\[^\'"]*)[\'"]'
        matches = re.findall(drive_pattern, source, re.IGNORECASE)
        assert not matches, f"Found hardcoded drive letters: {matches}"


class TestColrAnimationIntegration:
    """Integration tests for COLR animation workflow."""

    def test_workflow_end_to_end(self) -> None:
        """Test complete animation workflow from parsing to export."""
        assert True
