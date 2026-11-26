"""Designspace coverage diagnostics for variable fonts.

This module provides the compute_designspace_coverage function that evaluates
designspace coverage at specific grid points, and utilities for visual diff overlays.
"""

from __future__ import annotations

import math
from typing import Any

from aspose_font.subset_presets import available_subset_presets, codepoints_for_preset
from aspose_font.subsetter import FontSubsetter

__all__ = (
    "compute_designspace_coverage",
    "generate_designspace_coverage_report",
)


def _cartesian_product(values_lists: list[list[float]]) -> list[tuple[float, ...]]:
    if not values_lists:
        return [()]
    result: list[tuple[float, ...]] = [(val,) for val in values_lists[0]]
    for values in values_lists[1:]:
        new_result: list[tuple[float, ...]] = []
        for prefix in result:
            for val in values:
                new_result.append(prefix + (val,))
        result = new_result
    return result


def _euclidean_distance(coords1: tuple[float, ...], coords2: tuple[float, ...]) -> float:
    if len(coords1) != len(coords2):
        raise ValueError("Coordinate tuples must have the same length")
    squared_sum = sum((a - b) ** 2 for a, b in zip(coords1, coords2))
    return math.sqrt(squared_sum)


def compute_designspace_coverage(
    font: Any,
    grid: list[dict[str, float]] | None = None,
) -> dict[str, Any]:
    """Compute designspace coverage for a variable font at specific grid points.

    Args:
        font: A Font instance (expected to be TtfFont with FVAR table).
        grid: List of coordinate dictionaries, e.g.,
              [{"wght": 400, "wdth": 100}, {"wght": 700, "wdth": 100}]
              If None or empty, returns empty results.

    Returns:
        dict with keys:
            - 'grid': list[tuple[float, ...]] — axis coordinate tuples at grid points
            - 'covered': list[bool] — True if named instance exists at or near grid point
            - 'per_axis_stats': dict[str, dict] — per-axis min, max, default, sampled_points
            - 'axis_order': list[str] — ordered axis tags
            - 'per_axis_coverage': dict[str, float] — coverage percentage per axis
            - 'total_points': int — total number of grid points
            - 'covered_points': int — number of covered grid points

    Raises:
        ValueError: If font is not a variable font.
    """
    if not font.is_variable:
        raise ValueError("Font is not a variable font")

    if not grid:
        return {
            "grid": [],
            "covered": [],
            "per_axis_stats": {},
            "axis_order": [],
            "per_axis_coverage": {},
            "total_points": 0,
            "covered_points": 0,
        }

    axes = font.variable_axes
    if not axes:
        return {
            "grid": [],
            "covered": [],
            "per_axis_stats": {},
            "axis_order": [],
            "per_axis_coverage": {},
            "total_points": 0,
            "covered_points": 0,
        }

    axis_order = [axis.tag for axis in axes]
    tolerance_per_axis: dict[str, float] = {}
    for axis in axes:
        span = axis.max_value - axis.min_value
        if span > 0:
            tolerance_per_axis[axis.tag] = span / 100.0
        else:
            tolerance_per_axis[axis.tag] = 0.0

    grid_tuples: list[tuple[float, ...]] = [
        tuple(point.get(tag, 0.0) for tag in axis_order) for point in grid
    ]

    instance_tuples: list[tuple[float, ...]] = []
    for instance in font.variable_instances:
        instance_tuples.append(
            tuple(instance.coordinates.get(tag, 0.0) for tag in axis_order)
        )

    covered: list[bool] = []
    for grid_point in grid_tuples:
        is_covered = False
        for inst_tuple in instance_tuples:
            distance = _euclidean_distance(grid_point, inst_tuple)
            max_tolerance = math.sqrt(
                sum(
                    tolerance_per_axis.get(tag, 0.0) ** 2
                    for tag in axis_order
                )
            )
            if distance <= max_tolerance:
                is_covered = True
                break
        covered.append(is_covered)

    per_axis_stats: dict[str, dict[str, Any]] = {}
    for axis in axes:
        tag = axis.tag
        axis_idx = axis_order.index(tag)
        axis_values: list[float] = [
            grid_tuples[i][axis_idx] for i in range(len(grid_tuples)) if covered[i]
        ]
        per_axis_stats[tag] = {
            "min": axis.min_value,
            "max": axis.max_value,
            "default": axis.default_value,
            "sampled_points": sorted(set(axis_values)),
        }

    per_axis_coverage: dict[str, float] = {}
    for axis in axes:
        tag = axis.tag
        if tag not in axis_order:
            continue

        axis_idx = axis_order.index(tag)
        axis_values: set[float] = set()
        axis_covered_count = 0

        for i, point in enumerate(grid_tuples):
            val = point[axis_idx]
            if val not in axis_values:
                axis_values.add(val)
                if covered[i]:
                    axis_covered_count += 1

        per_axis_coverage[tag] = (
            axis_covered_count / len(axis_values) * 100.0
            if axis_values
            else 0.0
        )

    covered_count = sum(1 for c in covered if c)

    return {
        "grid": grid_tuples,
        "covered": covered,
        "per_axis_stats": per_axis_stats,
        "axis_order": axis_order,
        "per_axis_coverage": per_axis_coverage,
        "total_points": len(grid),
        "covered_points": covered_count,
    }


def generate_designspace_coverage_report(font: Any, preset: str) -> dict[str, object]:
    """Compute coverage metrics for a font against a Unicode preset.

    Args:
        font: A Font instance.
        preset: Preset name (e.g., 'latin', 'cyrillic').

    Returns:
        dict with keys:
            - 'preset': str — preset name
            - 'total_codepoints': int — total codepoints in preset
            - 'covered_codepoints': int — covered codepoint count
            - 'missing_codepoints': list[int] — list of missing codepoints (sorted)

    Raises:
        ValueError: If preset is unknown or font lacks encoding support.
    """
    if preset not in available_subset_presets():
        available = ", ".join(available_subset_presets())
        raise ValueError(f"Unknown subset preset {preset!r}. Available presets: {available}")

    frozen_codepoints = frozenset(codepoints_for_preset(preset))
    covered, missing = FontSubsetter._coverage_for_codepoints(font, frozen_codepoints)[:2]

    return {
        "preset": preset,
        "total_codepoints": len(frozen_codepoints),
        "covered_codepoints": len(covered),
        "missing_codepoints": sorted(missing),
    }
