"""Tests for extended axes_summary with optional CSS axis tag."""
from __future__ import annotations

from aspose_font import TtfFont
from aspose_font.variation import axes_summary


def test_axes_summary_without_css_tag(roboto: TtfFont) -> None:
    axes = axes_summary(roboto, include_css_tag=False)

    assert len(axes) == 2
    for axis in axes:
        assert "css_axis_tag" not in axis
        assert "name" in axis
        assert "tag" in axis
        assert "default" in axis


def test_axes_summary_with_css_tag(roboto: TtfFont) -> None:
    axes = axes_summary(roboto, include_css_tag=True)

    assert len(axes) == 2

    wght_axis = next(axis for axis in axes if axis["tag"] == "wght")
    assert wght_axis["css_axis_tag"] == "'wght'"
    assert wght_axis["name"] == "Weight"
    assert wght_axis["default"] == 400.0

    wdth_axis = next(axis for axis in axes if axis["tag"] == "wdth")
    assert wdth_axis["css_axis_tag"] == "'wdth'"
    assert wdth_axis["name"] == "Width"
    assert wdth_axis["default"] == 100.0


def test_axes_summary_css_tag_matches_property(roboto: TtfFont) -> None:
    axes_summary_enabled = axes_summary(roboto, include_css_tag=True)
    axes_summary_disabled = axes_summary(roboto, include_css_tag=False)

    for i, axis in enumerate(axes_summary_enabled):
        expected_tag = roboto.variable_axes[i].css_axis_tag
        assert axis["css_axis_tag"] == expected_tag
        assert "css_axis_tag" not in axes_summary_disabled[i]
