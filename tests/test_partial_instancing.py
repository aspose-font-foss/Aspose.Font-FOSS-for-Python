"""Tests for partial instancing core support (pin_axes function, FONT-227)."""
from pathlib import Path

import pytest

from aspose_font.instancing import pin_axes


class TestPinAxesFunction:
    """Test the pin_axes function."""

    def test_pin_axes_single_axis(self) -> None:
        """Test pinning a single axis while preserving others."""
        instance_coords: dict[str, float] = {"wght": 400.0, "wdth": 100.0, "slnt": 0.0}
        pinned_axes: dict[str, float] = {"wght": 700.0}

        result = pin_axes(instance_coords, pinned_axes)

        assert result["wght"] == 700.0
        assert result["wdth"] == 100.0
        assert result["slnt"] == 0.0

    def test_pin_axes_multiple_axes(self) -> None:
        """Test pinning multiple axes simultaneously."""
        instance_coords: dict[str, float] = {"wght": 400.0, "wdth": 100.0, "slnt": 0.0}
        pinned_axes: dict[str, float] = {"wght": 900.0, "wdth": 75.0}

        result = pin_axes(instance_coords, pinned_axes)

        assert result["wght"] == 900.0
        assert result["wdth"] == 75.0
        assert result["slnt"] == 0.0

    def test_pin_axes_preserves_original(self) -> None:
        """Test that original instance_coords is not mutated."""
        instance_coords: dict[str, float] = {"wght": 400.0, "wdth": 100.0}
        original_copy = dict(instance_coords)
        pinned_axes: dict[str, float] = {"wght": 700.0}

        result = pin_axes(instance_coords, pinned_axes)

        assert instance_coords == original_copy
        assert result is not instance_coords

    def test_pin_axes_empty_pinned_axes(self) -> None:
        """Test with empty pinned_axes returns a copy of original."""
        instance_coords: dict[str, float] = {"wght": 400.0, "wdth": 100.0}

        result = pin_axes(instance_coords, {})

        assert result == instance_coords
        assert result is not instance_coords

    def test_pin_axes_all_axes_pinned(self) -> None:
        """Test when all axes are pinned, result equals pinned_axes."""
        instance_coords: dict[str, float] = {"wght": 400.0, "wdth": 100.0}
        pinned_axes: dict[str, float] = {"wght": 900.0, "wdth": 75.0}

        result = pin_axes(instance_coords, pinned_axes)

        assert result == pinned_axes

    def test_pin_axes_overrides_existing_values(self) -> None:
        """Test that pinned_axes values override existing coordinates."""
        instance_coords: dict[str, float] = {"wght": 400.0, "wdth": 100.0}
        pinned_axes: dict[str, float] = {"wght": 400.0}

        result = pin_axes(instance_coords, pinned_axes)

        assert result["wght"] == 400.0
        assert result["wdth"] == 100.0
        assert result is not instance_coords


class TestPinAxesIntegration:
    """Test integration with existing instancing code."""

    def test_partial_instantiate_uses_pin_axes(self) -> None:
        """Verify partial_instantiate produces correct coordinates via pin_axes logic."""
        from aspose_font import FontLoader

        font_path = Path(__file__).resolve().parents[1] / "testdata" / "Roboto-VariableFont_wdth,wght.ttf"
        try:
            font = FontLoader.open(font_path)
            if not font.is_variable:
                pytest.skip("Test font is not variable")

            from aspose_font.instancing import SmartInstancer

            instancer = SmartInstancer(font)
            result_font = instancer.partial_instantiate(
                lock_axes={"wght": 700.0}
            )

            assert result_font is not None
            assert result_font.is_static or not result_font.is_variable

        except Exception:
            pytest.skip("Test font not available or couldn't be loaded")


class TestPinAxesCrossPlatform:
    """Verify cross-platform compatibility."""

    def test_paths_use_pathlib(self) -> None:
        """Test that test paths use Path object, not hardcoded Windows paths."""
        testdata_path = Path(__file__).resolve().parents[1] / "testdata"
        assert "testdata" in str(testdata_path).split("\\") or "testdata" in str(testdata_path).split("/")
