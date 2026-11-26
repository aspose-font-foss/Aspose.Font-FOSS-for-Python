"""Tests for axis_clamper module."""

from __future__ import annotations

from pathlib import Path

import pytest

from aspose_font import FontLoader, TtfFont, clamp_axis_range


@pytest.fixture
def roboto_variable(roboto: TtfFont) -> TtfFont:
    """Roboto variable font (already in conftest.py)."""
    return roboto


class TestClampAxisRange:
    """Tests for clamp_axis_range function."""

    def test_normal_clamping_within_range(
        self, roboto_variable: TtfFont
    ) -> None:
        """Clamp axis to a range that includes current min/max - no change expected."""
        original_axes = {ax.tag: ax for ax in roboto_variable.axes}

        clamped = clamp_axis_range(roboto_variable, "wght", 100.0, 1000.0)

        clamped_axes = {ax.tag: ax for ax in clamped.axes}
        assert clamped_axes["wght"].min_value == 100.0
        assert clamped_axes["wght"].max_value == 1000.0

        assert original_axes["wght"].min_value == 100.0
        assert original_axes["wght"].max_value == 900.0

    def test_clamp_below_minimum_value(
        self, roboto_variable: TtfFont
    ) -> None:
        """Test clamping sets min_value to the specified lower bound."""
        clamped = clamp_axis_range(roboto_variable, "wght", 200.0, 1000.0)

        clamped_axes = {ax.tag: ax for ax in clamped.axes}
        assert clamped_axes["wght"].min_value == 200.0
        assert clamped_axes["wght"].max_value == 1000.0

    def test_clamp_above_maximum_value(
        self, roboto_variable: TtfFont
    ) -> None:
        """Test clamping sets max_value to the specified upper bound."""
        clamped = clamp_axis_range(roboto_variable, "wght", 100.0, 600.0)

        clamped_axes = {ax.tag: ax for ax in clamped.axes}
        assert clamped_axes["wght"].min_value == 100.0
        assert clamped_axes["wght"].max_value == 600.0

    def test_clamp_both_min_and_max(
        self, roboto_variable: TtfFont
    ) -> None:
        """Test clamping both min and max to new values."""
        clamped = clamp_axis_range(roboto_variable, "wght", 300.0, 800.0)

        clamped_axes = {ax.tag: ax for ax in clamped.axes}
        assert clamped_axes["wght"].min_value == 300.0
        assert clamped_axes["wght"].max_value == 800.0

    def test_non_existent_axis_raises_value_error(
        self, roboto_variable: TtfFont
    ) -> None:
        """Test that clamping a non-existent axis raises ValueError."""
        with pytest.raises(ValueError, match="Axis 'XXXX' not found"):
            clamp_axis_range(roboto_variable, "XXXX", 100.0, 1000.0)

    def test_other_axes_remain_unchanged(
        self, roboto_variable: TtfFont
    ) -> None:
        """Test that only the specified axis is modified."""
        original_axes = {ax.tag: (ax.min_value, ax.max_value) for ax in roboto_variable.axes}

        clamped = clamp_axis_range(roboto_variable, "wght", 300.0, 700.0)
        clamped_axes = {ax.tag: (ax.min_value, ax.max_value) for ax in clamped.axes}

        assert clamped_axes["wght"] == (300.0, 700.0)

        for tag, (orig_min, orig_max) in original_axes.items():
            if tag != "wght":
                assert clamped_axes[tag] == (orig_min, orig_max)

    def test_returns_independent_font_object(
        self, roboto_variable: TtfFont
    ) -> None:
        """Test that modifying clamped font doesn't affect original."""
        clamped = clamp_axis_range(roboto_variable, "wght", 300.0, 700.0)

        clamp_axis_range(clamped, "wght", 400.0, 600.0)

        assert roboto_variable.axes[0].tag == "wght"

    def test_serialization_roundtrip(
        self, roboto_variable: TtfFont, tmp_path: Path
    ) -> None:
        """Test that clamped font can be serialized and reloaded."""
        clamped = clamp_axis_range(roboto_variable, "wght", 300.0, 700.0)

        output_path = tmp_path / "clamped.ttf"
        output_path.write_bytes(clamped.to_bytes())

        reloaded = FontLoader.open(str(output_path))
        assert isinstance(reloaded, TtfFont)
        assert reloaded.is_variable

        reloaded_axes = {ax.tag: ax for ax in reloaded.axes}
        assert reloaded_axes["wght"].min_value == 300.0
        assert reloaded_axes["wght"].max_value == 700.0

    def test_invalid_min_max_order_raises_value_error(
        self, roboto_variable: TtfFont
    ) -> None:
        """Test that min > max raises ValueError."""
        with pytest.raises(ValueError, match="min_value.*must be.*<=.*max_value"):
            clamp_axis_range(roboto_variable, "wght", 800.0, 300.0)

    def test_float_conversion_accepts_numeric_strings(
        self, roboto_variable: TtfFont
    ) -> None:
        """Test that string numeric values are converted to float."""
        clamped = clamp_axis_range(roboto_variable, "wght", "300", "700")

        clamped_axes = {ax.tag: ax for ax in clamped.axes}
        assert clamped_axes["wght"].min_value == 300.0
        assert clamped_axes["wght"].max_value == 700.0

    def test_clamp_wdth_axis(self, roboto_variable: TtfFont) -> None:
        """Test that clamping works for other axes like wdth."""
        original_axes = {ax.tag: ax for ax in roboto_variable.axes}
        original_wdth = original_axes["wdth"]

        clamped = clamp_axis_range(roboto_variable, "wdth", 50.0, 150.0)

        clamped_axes = {ax.tag: ax for ax in clamped.axes}
        assert clamped_axes["wdth"].min_value == 50.0
        assert clamped_axes["wdth"].max_value == 150.0

        assert original_wdth.min_value == 75.0
        assert original_wdth.max_value == 100.0
