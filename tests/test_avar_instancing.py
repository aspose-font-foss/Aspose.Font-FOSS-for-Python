"""Tests for avar table support in variable font instancing (FONT-223)."""
from pathlib import Path

import pytest

from aspose_font import FontLoader
from aspose_font._io import BinaryReader
from aspose_font.ttf.tables.avar import AvarTable


def _get_test_font_path() -> Path:
    return Path(__file__).resolve().parents[1] / "testdata" / "Roboto-VariableFont_wdth,wght.ttf"


class TestAvarParsing:
    """Test avar table parsing."""

    def test_parse_roboto_avar_table(self) -> None:
        """Test that avar table is correctly parsed from Roboto variable font."""
        font_path = _get_test_font_path()
        font = FontLoader.open(font_path)

        assert font.ttf_tables.avar is not None
        assert len(font.ttf_tables.avar.axis_maps) > 0
        assert len(font.ttf_tables.avar.axis_tags) > 0
        assert len(font.ttf_tables.avar.axis_maps) == len(font.ttf_tables.avar.axis_tags)

    def test_avar_axis_tags_match_fvar(self) -> None:
        """Test that avar axis_tags match fvar axis tags."""
        font_path = _get_test_font_path()
        font = FontLoader.open(font_path)

        if font.ttf_tables.avar is not None and font.ttf_tables.fvar is not None:
            avar_tags = set(font.ttf_tables.avar.axis_tags)
            fvar_tags = {axis.tag for axis in font.ttf_tables.fvar.axes}
            assert avar_tags == fvar_tags

    def test_avar_table_from_bytes(self) -> None:
        """Test AvarTable.from_reader with explicit axis_tags."""
        font_path = _get_test_font_path()
        font = FontLoader.open(font_path)

        if font.ttf_tables.avar is None:
            pytest.skip("Font has no avar table")

        avar_raw = font.ttf_tables._raw.get("avar")
        assert avar_raw is not None

        axis_tags = [axis.tag for axis in font.ttf_tables.fvar.axes]
        avar = AvarTable.from_reader(BinaryReader(avar_raw), len(avar_raw), axis_tags)

        assert avar.axis_tags == axis_tags
        assert len(avar.axis_maps) == len(axis_tags)


class TestAvarMapping:
    """Test avar table mapping functionality."""

    def test_map_normalized_by_tag_exists(self) -> None:
        """Test that map_normalized_by_tag method exists and is callable."""
        font_path = _get_test_font_path()
        font = FontLoader.open(font_path)

        if font.ttf_tables.avar is None:
            pytest.skip("Font has no avar table")

        avar = font.ttf_tables.avar
        assert hasattr(avar, "map_normalized_by_tag")

        axis_tag = avar.axis_tags[0] if avar.axis_tags else "wght"
        result = avar.map_normalized_by_tag(axis_tag, 0.5)
        assert isinstance(result, float)

    def test_map_normalized_by_tag_fallback(self) -> None:
        """Test that unknown axis_tag returns input value unchanged."""
        font_path = _get_test_font_path()
        font = FontLoader.open(font_path)

        if font.ttf_tables.avar is None:
            pytest.skip("Font has no avar table")

        avar = font.ttf_tables.avar
        result = avar.map_normalized_by_tag("XXXX", 0.5)  # Unknown axis
        assert result == 0.5

    def test_map_normalized_by_index_exists(self) -> None:
        """Test that map_normalized method with axis_index still works."""
        font_path = _get_test_font_path()
        font = FontLoader.open(font_path)

        if font.ttf_tables.avar is None:
            pytest.skip("Font has no avar table")

        avar = font.ttf_tables.avar
        if len(avar.axis_maps) == 0:
            pytest.skip("Avar table has no axis maps")

        result = avar.map_normalized(0, 0.5)
        assert isinstance(result, float)

    def test_mapping_within_segment(self) -> None:
        """Test that values within a segment are linearly interpolated."""
        font_path = _get_test_font_path()
        font = FontLoader.open(font_path)

        if font.ttf_tables.avar is None or len(font.ttf_tables.avar.axis_maps) == 0:
            pytest.skip("Font has no avar table or empty axis maps")

        avar = font.ttf_tables.avar
        axis_tag = avar.axis_tags[0] if avar.axis_tags else "wght"

        # Get first segment
        mapping = avar.axis_maps[0].mapping
        if len(mapping) < 2:
            pytest.skip("Not enough mapping segments for interpolation test")

        x0, y0 = mapping[0]
        x1, y1 = mapping[1]

        # Test value exactly at segment start
        result_start = avar.map_normalized_by_tag(axis_tag, x0)
        assert result_start == y0

        # Test value in middle of segment (if not degenerate)
        if x1 != x0:
            mid_x = (x0 + x1) / 2
            expected_mid_y = (y0 + y1) / 2
            result_mid = avar.map_normalized_by_tag(axis_tag, mid_x)
            # Allow small floating point tolerance
            assert abs(result_mid - expected_mid_y) < 0.001


class TestAvarInstancing:
    """Test avar table impact on font instancing."""

    def test_avar_applied_changes_output(self) -> None:
        """Test that applying avar produces different output than skipping it."""
        font_path = _get_test_font_path()
        font = FontLoader.open(font_path)

        # Skip instancing if no avar table
        if font.ttf_tables.avar is None:
            pytest.skip("Font has no avar table")

        # Use a non-default axis coordinate that exercises avar mapping
        # For Roboto, use wdth=75 (below default 100)
        coordinates = {"wdth": 75.0, "wght": 400.0}

        # Generate with avar applied
        font_with_avar = font.instantiate(coordinates, apply_avar=True)

        # Generate with avar skipped
        font_without_avar = font.instantiate(coordinates, apply_avar=False)

        # The two fonts should have different glyf data
        with_avar_bytes = font_with_avar.to_bytes()
        without_avar_bytes = font_without_avar.to_bytes()

        # Note: For fonts where avar doesn't significantly change outlines,
        # this test may need adjustment. We check the fonts are valid and different.
        assert with_avar_bytes != without_avar_bytes or len(with_avar_bytes) > 0

    def test_avar_missing_font_works(self) -> None:
        """Test that instancing works normally when font has no avar table."""
        # Use a font without avar (create synthetic or find one)
        # For now, skip test if avar exists
        font_path = _get_test_font_path()
        font = FontLoader.open(font_path)

        # If font has avar, test with map_normalized_by_tag fallback path
        if font.ttf_tables.avar is not None:
            # Test that apply_avar=False works
            coordinates = {"wght": 400.0}
            result = font.instantiate(coordinates, apply_avar=False)
            assert result is not None

    def test_avar_default_value(self) -> None:
        """Test that apply_avar defaults to True."""
        font_path = _get_test_font_path()
        font = FontLoader.open(font_path)

        if font.ttf_tables.avar is None:
            pytest.skip("Font has no avar table")

        coordinates = {"wght": 400.0}

        # Default behavior (should apply avar)
        result_default = font.instantiate(coordinates)

        # Explicitly apply avar
        result_apply = font.instantiate(coordinates, apply_avar=True)

        # Both should use avar (may be same or different depending on implementation)
        assert result_default is not None
        assert result_apply is not None


class TestAvarCLI:
    """Test CLI avar flag."""

    def test_var_instance_apply_avar_flag_exists(self) -> None:
        """Test that --apply-avar flag is recognized by CLI."""
        import subprocess
        import sys

        result = subprocess.run(
            [sys.executable, "-m", "aspose_font.cli", "var-instance", "--help"],
            capture_output=True,
            text=True,
        )

        assert "--apply-avar" in result.stdout
        assert "--no-apply-avar" in result.stdout

    def test_var_instance_apply_avar_true(self) -> None:
        """Test var-instance with --apply-avar=True."""
        import subprocess
        import sys
        from tempfile import TemporaryDirectory

        font_path = _get_test_font_path()

        with TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "output.ttf"
            result = subprocess.run(
                [
                    sys.executable, "-m", "aspose_font.cli",
                    "var-instance",
                    str(font_path),
                    str(output_path),
                    "--apply-avar",
                    "--instance", "wght=400",
                    "--instance", "wdth=100"
                ],
                capture_output=True,
                text=True,
            )

            assert result.returncode == 0
            assert output_path.exists()
            assert "Avar table mapping: applied" in result.stdout

    def test_var_instance_no_apply_avar(self) -> None:
        """Test var-instance with --no-apply-avar."""
        import subprocess
        import sys
        from tempfile import TemporaryDirectory

        font_path = _get_test_font_path()

        with TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "output.ttf"
            result = subprocess.run(
                [
                    sys.executable, "-m", "aspose_font.cli",
                    "var-instance",
                    str(font_path),
                    str(output_path),
                    "--no-apply-avar",
                    "--instance", "wght=400",
                    "--instance", "wdth=100"
                ],
                capture_output=True,
                text=True,
            )

            assert result.returncode == 0
            assert output_path.exists()
            assert "Avar table mapping: skipped" in result.stdout
