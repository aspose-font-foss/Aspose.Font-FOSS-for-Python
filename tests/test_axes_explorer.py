"""Tests for the Axes Explorer (variable axis summary)."""
from __future__ import annotations

from aspose_font import TtfFont
from aspose_font.variation import axes_summary


def test_axes_summary_returns_expected_keys(roboto: TtfFont) -> None:
    axes = axes_summary(roboto)

    assert len(axes) == 2
    for axis in axes:
        assert "name" in axis
        assert "tag" in axis
        assert "default" in axis
        assert "minValue" in axis
        assert "maxValue" in axis
        assert "localizedLabelCount" in axis
        assert isinstance(axis["name"], str)
        assert isinstance(axis["tag"], str)
        assert isinstance(axis["default"], float)
        assert isinstance(axis["minValue"], float)
        assert isinstance(axis["maxValue"], float)
        assert isinstance(axis["localizedLabelCount"], int)


def test_axes_summary_roboto_fixture(roboto: TtfFont) -> None:
    axes = axes_summary(roboto)

    assert len(axes) == 2

    tags = {axis["tag"] for axis in axes}
    assert tags == {"wght", "wdth"}

    wght_axis = next(axis for axis in axes if axis["tag"] == "wght")
    assert wght_axis["name"] == "Weight"
    assert wght_axis["default"] == 400.0
    assert wght_axis["minValue"] == 100.0
    assert wght_axis["maxValue"] == 900.0
    assert wght_axis["localizedLabelCount"] >= 1

    wdth_axis = next(axis for axis in axes if axis["tag"] == "wdth")
    assert wdth_axis["name"] == "Width"
    assert wdth_axis["default"] == 100.0
    assert wdth_axis["minValue"] == 75.0
    assert wdth_axis["maxValue"] == 100.0
    assert wdth_axis["localizedLabelCount"] >= 1
