"""Tests for designspace coverage diagnostics with custom grid parameter."""

from __future__ import annotations

from pathlib import Path

import pytest

from aspose_font import FontLoader
from aspose_font.diagnostics.coverage import compute_designspace_coverage

_TESTDATA_DIR = Path(__file__).resolve().parents[1] / "testdata"


def test_compute_designspace_coverage_on_roboto_variable():
    """Test successful computation with a valid custom grid."""
    font_path = _TESTDATA_DIR / "Roboto-VariableFont_wdth,wght.ttf"
    font = FontLoader.open(font_path)
    assert font.is_variable, "Roboto variable font should be detected as variable."

    grid = [
        {"wght": 400.0, "wdth": 100.0},
        {"wght": 700.0, "wdth": 100.0},
        {"wght": 400.0, "wdth": 200.0},
    ]

    result = compute_designspace_coverage(font, grid)

    assert "grid" in result
    assert "covered" in result
    assert "per_axis_stats" in result
    assert "axis_order" in result
    assert "per_axis_coverage" in result
    assert "total_points" in result
    assert "covered_points" in result
    assert len(result["grid"]) == len(result["covered"])
    assert result["total_points"] == 3
    assert result["covered_points"] >= 0

    per_axis_stats = result["per_axis_stats"]
    for tag, stats in per_axis_stats.items():
        assert "min" in stats
        assert "max" in stats
        assert "default" in stats
        assert "sampled_points" in stats
        assert isinstance(stats["min"], float)
        assert isinstance(stats["max"], float)
        assert isinstance(stats["default"], float)
        assert isinstance(stats["sampled_points"], list)


def test_compute_designspace_coverage_empty_grid():
    """Test handling of empty grid (should return empty results without error)."""
    font_path = _TESTDATA_DIR / "Roboto-VariableFont_wdth,wght.ttf"
    font = FontLoader.open(font_path)

    result = compute_designspace_coverage(font, [])

    assert result["grid"] == []
    assert result["covered"] == []
    assert result["per_axis_coverage"] == {}
    assert result["total_points"] == 0
    assert result["covered_points"] == 0


def test_compute_designspace_coverage_none_grid():
    """Test handling of None grid (should return empty results without error)."""
    font_path = _TESTDATA_DIR / "Roboto-VariableFont_wdth,wght.ttf"
    font = FontLoader.open(font_path)

    result = compute_designspace_coverage(font, None)

    assert result["grid"] == []
    assert result["covered"] == []
    assert result["per_axis_coverage"] == {}
    assert result["total_points"] == 0
    assert result["covered_points"] == 0


def test_compute_designspace_coverage_static_font_raises():
    """Test that static fonts raise ValueError."""
    font_path = _TESTDATA_DIR / "TTF" / "arial.ttf"
    try:
        font = FontLoader.open(font_path)
    except Exception:
        pytest.skip("Static font fixture not found")

    if not font.is_variable:
        with pytest.raises(ValueError, match="not a variable font"):
            compute_designspace_coverage(font, [])


def test_compute_designspace_coverage_single_axis():
    """Test computation with single-axis variable font."""
    font_path = _TESTDATA_DIR / "Roboto-VariableFont_wdth,wght.ttf"
    font = FontLoader.open(font_path)

    grid = [{"wght": 400.0}]

    result = compute_designspace_coverage(font, grid)

    assert result["total_points"] == 1
    assert "per_axis_coverage" in result
    assert "wght" in result["per_axis_coverage"] or "wdth" in result["per_axis_coverage"]


def test_compute_designspace_coverage_per_axis_coverage():
    """Test verification of per-axis coverage percentages against known variable font."""
    font_path = _TESTDATA_DIR / "Roboto-VariableFont_wdth,wght.ttf"
    font = FontLoader.open(font_path)

    grid = [
        {"wght": 400.0, "wdth": 100.0},
        {"wght": 700.0, "wdth": 100.0},
    ]

    result = compute_designspace_coverage(font, grid)

    assert result["total_points"] == 2
    assert len(result["per_axis_coverage"]) >= 1
    for coverage in result["per_axis_coverage"].values():
        assert 0.0 <= coverage <= 100.0


def test_compute_designspace_coverage_grid_point_format():
    """Test that each grid point must be a dict with axis tags as keys."""
    font_path = _TESTDATA_DIR / "Roboto-VariableFont_wdth,wght.ttf"
    font = FontLoader.open(font_path)

    grid = [
        {"wght": 400.0, "wdth": 100.0},
    ]

    result = compute_designspace_coverage(font, grid)

    assert len(result["grid"]) == 1
    assert isinstance(result["grid"][0], tuple)
    assert len(result["grid"][0]) >= 2


def test_compute_designspace_coverage_per_axis_stats_structure():
    """Verify per_axis_stats contains min, max, default, sampled_points"""
    font_path = _TESTDATA_DIR / "Roboto-VariableFont_wdth,wght.ttf"
    font = FontLoader.open(font_path)

    grid = [
        {"wght": 400.0, "wdth": 100.0},
        {"wght": 700.0, "wdth": 100.0},
    ]

    result = compute_designspace_coverage(font, grid)

    assert "per_axis_stats" in result
    assert "axis_order" in result
    assert len(result["per_axis_stats"]) >= 1
    for tag, stats in result["per_axis_stats"].items():
        assert "min" in stats
        assert "max" in stats
        assert "default" in stats
        assert "sampled_points" in stats
        assert isinstance(stats["min"], (int, float))
        assert isinstance(stats["max"], (int, float))
        assert isinstance(stats["default"], (int, float))
        assert isinstance(stats["sampled_points"], list)


def test_compute_designspace_coverage_axis_values_match():
    """Verify min/max/default match font.axis.{min_value,max_value,default}"""
    font_path = _TESTDATA_DIR / "Roboto-VariableFont_wdth,wght.ttf"
    font = FontLoader.open(font_path)

    grid = [
        {"wght": 400.0, "wdth": 100.0},
    ]

    result = compute_designspace_coverage(font, grid)

    assert "per_axis_stats" in result
    assert "axis_order" in result
    for axis in font.variable_axes:
        tag = axis.tag
        if tag in result["per_axis_stats"]:
            stats = result["per_axis_stats"][tag]
            assert stats["min"] == axis.min_value
            assert stats["max"] == axis.max_value
            assert stats["default"] == axis.default_value
