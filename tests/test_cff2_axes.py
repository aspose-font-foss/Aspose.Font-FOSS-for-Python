"""Tests for CFF2 variable axes listing with minimal synthetic payloads."""
from __future__ import annotations

from aspose_font import Cff2Font


class TestCff2AxesEmptyFvar:
    """Test axes listing for CFF2 stub fonts without fvar table."""

    def test_list_axes_returns_empty_list_without_fvar(self):
        """list_axes() returns empty list when font lacks fvar table."""
        data = b"CFF2" + b"\x00" * 100
        font = Cff2Font(data)
        axes = font.list_axes()
        assert axes == []

    def test_variable_axes_property_returns_empty_list_without_fvar(self):
        """variable_axes property returns empty list when font lacks fvar table."""
        data = b"CFF2" + b"\x00" * 100
        font = Cff2Font(data)
        axes = font.variable_axes
        assert axes == []

    def test_list_axes_type_is_list(self):
        """list_axes() returns list type even for empty axes."""
        data = b"CFF2" + b"\x00" * 100
        font = Cff2Font(data)
        axes = font.list_axes()
        assert isinstance(axes, list)

    def test_variable_axes_type_is_list(self):
        """variable_axes property returns list type even for empty axes."""
        data = b"CFF2" + b"\x00" * 100
        font = Cff2Font(data)
        axes = font.variable_axes
        assert isinstance(axes, list)
