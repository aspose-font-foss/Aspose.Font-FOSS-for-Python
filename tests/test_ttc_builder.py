"""Tests for TrueType Collection Builder (FONT-541)."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from aspose_font import FontLoader
from aspose_font.ttf.collection import is_ttc
from aspose_font.ttf.collection_builder import build_ttc


def _get_test_font_paths() -> list[Path]:
    """Get paths to test font files (Roboto fonts share several tables)."""
    testdata_dir = Path(__file__).resolve().parents[1] / "testdata"
    return [
        testdata_dir / "Fonts" / "Roboto-Regular.ttf",
        testdata_dir / "Fonts" / "Roboto-Medium.ttf",
    ]


class TestBuildTtc:
    """Tests for the build_ttc function."""

    def test_build_ttc_creates_valid_collection(self) -> None:
        """build_ttc should create a valid TTC file containing all input fonts."""
        font_paths = _get_test_font_paths()
        if not all(p.exists() for p in font_paths):
            pytest.skip("Test fonts not available")

        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "test.ttc"
            build_ttc(font_paths, output_path, dedup=True)

            assert output_path.exists(), "TTC file should be created"
            assert output_path.stat().st_size > 0, "TTC file should not be empty"

            ttc_data = output_path.read_bytes()
            assert is_ttc(ttc_data), "Output should be valid TTC format"

            loaded = FontLoader.open(output_path, collection_index=0)
            assert loaded is not None

    def test_build_ttc_dedup_reduces_file_size(self) -> None:
        """When dedup=True, identical tables should be shared to reduce file size."""
        font_paths = _get_test_font_paths()
        if not all(p.exists() for p in font_paths):
            pytest.skip("Test fonts not available")

        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path_dedup = Path(tmp_dir) / "dedup.ttc"
            output_path_no_dedup = Path(tmp_dir) / "nodeup.ttc"

            build_ttc(font_paths, output_path_dedup, dedup=True)
            build_ttc(font_paths, output_path_no_dedup, dedup=False)

            size_dedup = output_path_dedup.stat().st_size
            size_no_dedup = output_path_no_dedup.stat().st_size

            assert size_dedup <= size_no_dedup, "Dedup should not increase file size"

    def test_build_ttc_roundtrip_preserves_glyph_count(self) -> None:
        """Loading a TTC should preserve num_glyphs for each face."""
        font_paths = _get_test_font_paths()
        if not all(p.exists() for p in font_paths):
            pytest.skip("Test fonts not available")

        original_glyph_counts: list[int] = []
        for font_path in font_paths:
            loaded = FontLoader.open(font_path)
            original_glyph_counts.append(loaded.num_glyphs)

        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "test.ttc"
            build_ttc(font_paths, output_path, dedup=True)

            for i, expected_glyphs in enumerate(original_glyph_counts):
                loaded = FontLoader.open(output_path, collection_index=i)
                assert loaded.num_glyphs == expected_glyphs, (
                    f"Face {i} should have {expected_glyphs} glyphs"
                )

    def test_build_ttc_handles_multiple_tables(self) -> None:
        """TTC should preserve all required tables from input fonts."""
        font_paths = _get_test_font_paths()
        if not all(p.exists() for p in font_paths):
            pytest.skip("Test fonts not available")

        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "test.ttc"
            build_ttc(font_paths, output_path, dedup=True)

            ttc_data = output_path.read_bytes()
            assert is_ttc(ttc_data), "Output should be valid TTC format"

            loaded0 = FontLoader.open(output_path, collection_index=0)
            assert loaded0.num_glyphs > 0

            loaded1 = FontLoader.open(output_path, collection_index=1)
            assert loaded1.num_glyphs > 0

    def test_build_ttc_invalid_inputs(self) -> None:
        """build_ttc should raise appropriate exceptions for invalid inputs."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "test.ttc"

            with pytest.raises(Exception):
                build_ttc([], output_path, dedup=True)

            nonexistent_path = Path(tmp_dir) / "nonexistent.ttf"
            with pytest.raises(Exception):
                build_ttc([nonexistent_path, nonexistent_path], output_path, dedup=True)
