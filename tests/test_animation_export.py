"""Tests for the Animation Engine export surfaces (CLI)."""

import json
from pathlib import Path

import pytest

from aspose_font import FontLoader
from aspose_font.animation import AnimationPreviewBuilder


def test_animation_export_cli_success(testdata_dir, tmp_path):
    """Verify that running animation-export creates both animation.apng and manifest.json."""
    font_path = testdata_dir / "Roboto-VariableFont_wdth,wght.ttf"
    font = FontLoader.open(str(font_path))

    package = AnimationPreviewBuilder.build_export_package(
        font,
        axis_tag="wdth",
        start_val=75.0,
        end_val=100.0,
        frames=3,
        fps=10,
        text="Test",
        preset="draft",
    )

    output_dir = package.write_to(tmp_path)

    assert output_dir.is_dir()
    apng_path = output_dir / package.animation.filename
    manifest_path = output_dir / package.manifest_name

    assert apng_path.exists()
    assert manifest_path.exists()

    apng_data = apng_path.read_bytes()
    assert apng_data.startswith(b"\x89PNG\r\n\x1a\n")
    assert b"acTL" in apng_data
    assert b"fcTL" in apng_data

    manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest_data["version"] == "1.0"
    assert manifest_data["type"] == "animation-export-package"
    assert "animation" in manifest_data
    assert "parameters" in manifest_data
    assert manifest_data["parameters"]["axis_tag"] == "wdth"
    assert manifest_data["parameters"]["start_val"] == 75.0
    assert manifest_data["parameters"]["end_val"] == 100.0


def test_animation_export_cli_missing_output():
    """Verify proper error handling when required arguments are missing."""
    font_path = Path("testdata/Roboto-VariableFont_wdth,wght.ttf")
    font = FontLoader.open(str(font_path))

    with pytest.raises(TypeError, match="required positional argument: 'axis_tag'"):
        AnimationPreviewBuilder.build_export_package(
            font,
            start_val=75.0,
            end_val=100.0,
        )
