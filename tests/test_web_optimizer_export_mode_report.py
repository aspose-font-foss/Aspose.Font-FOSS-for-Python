"""Tests for Variable-Font Export Mode Decision Report (FONT-211)."""

from __future__ import annotations

from pathlib import Path

from aspose_font import WebFontOptimizer
from aspose_font.ttf.font import TtfFont


def test_web_optimizer_export_mode_live_variable_font(roboto: TtfFont):
    """Export mode 'live' when variable_mode='live' on a variable font."""
    package = WebFontOptimizer.build(roboto, variable_mode="live")

    assert package.manifest["export_mode"] == "live"
    assert package.bundle.manifest["export_mode"] == "variable-live"


def test_web_optimizer_export_mode_static_fallback(roboto: TtfFont):
    """Export mode 'static-fallback' when variable font is auto-instantiated and subsetted."""
    package = WebFontOptimizer.build(
        roboto,
        source_path=Path("testdata/Roboto-VariableFont_wdth,wght.ttf"),
        presets=("latin",),
    )

    assert package.manifest["export_mode"] == "static-fallback"
    assert package.bundle.manifest["export_mode"] == "static-subset-from-variable-default"


def test_web_optimizer_export_mode_static_instance(roboto: TtfFont):
    """Export mode 'static' when explicit instance is selected."""
    package = WebFontOptimizer.build(roboto, instance_coordinates={"wght": 700.0})

    assert package.manifest["export_mode"] == "static"
    assert package.bundle.manifest["export_mode"] == "static-instance"


def test_web_optimizer_manifest_json_contains_export_mode(roboto: TtfFont, tmp_path: Path):
    """Export mode appears in optimizer-manifest.json file."""
    package = WebFontOptimizer.build(roboto, variable_mode="live")

    assert "export_mode" in package.manifest
    assert package.manifest["export_mode"] in ("live", "static", "static-fallback")
