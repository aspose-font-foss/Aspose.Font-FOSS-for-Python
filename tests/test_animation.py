"""Tests for the Animation Engine."""

import json

import pytest

from aspose_font import FontLoader
from aspose_font.animation import (
    AnimationFramePackage,
    AnimationPreviewBuilder,
    AnimationReviewPackage,
    AnimationShowcasePackage,
    AnimationStep,
)
from aspose_font.rasterizer import encode_apng_from_rgb


def test_encode_apng_from_rgb():
    w, h = 10, 10
    frame1 = bytearray([255, 0, 0] * w * h)
    frame2 = bytearray([0, 255, 0] * w * h)

    apng = encode_apng_from_rgb([bytes(frame1), bytes(frame2)], w, h, fps=10)

    # Check signature
    assert apng.startswith(b"\x89PNG\r\n\x1a\n")
    # Verify animation chunks exist
    assert b"acTL" in apng
    assert b"fcTL" in apng
    assert b"fdAT" in apng
    # Standard PNG endings
    assert apng.endswith(b"IEND\xaeB`\x82")


def test_encode_apng_invalid_size():
    w, h = 10, 10
    frame1 = bytearray([255, 0, 0] * w * h)
    frame2 = bytearray([0, 255, 0] * (w * h - 1))  # Invalid size

    with pytest.raises(ValueError, match="buffer size mismatch"):
        encode_apng_from_rgb([bytes(frame1), bytes(frame2)], w, h, fps=10)


def test_animation_builder_sweep(testdata_dir):
    font_path = testdata_dir / "Roboto-VariableFont_wdth,wght.ttf"
    font = FontLoader.open(str(font_path))

    # Sweep wdth from 75 to 100 with bounce (3 frames -> generates 4 frames: 0, 1, 2, reversed_1)
    asset = AnimationPreviewBuilder.build_axis_sweep(
        font,
        axis_tag="wdth",
        start_val=75.0,
        end_val=100.0,
        frames=3,
        fps=10,
        text="A",
        size=10.0,
        bounce=True,
    )

    assert asset.filename == "roboto-sweep-wdth.png"
    assert asset.media_type == "image/apng"

    data = asset.data
    assert data.startswith(b"\x89PNG\r\n\x1a\n")
    assert b"acTL" in data
    assert b"fcTL" in data
    # Check there is an IDAT (first frame) and fdAT (subsequent frames)
    assert b"IDAT" in data
    assert b"fdAT" in data
    assert asset.frame_count == 4
    assert asset.fps == 10
    assert asset.frame_labels[0] == "wdth=75"
    assert asset.frame_labels[2] == "wdth=100"


def test_animation_builder_exposes_presets() -> None:
    assert AnimationPreviewBuilder.available_presets() == ("draft", "standard", "showcase")


def test_animation_builder_path_supports_multiple_steps(testdata_dir) -> None:
    font_path = testdata_dir / "Roboto-VariableFont_wdth,wght.ttf"
    font = FontLoader.open(str(font_path))

    asset = AnimationPreviewBuilder.build_path(
        font,
        [
            AnimationStep({"wght": 400.0, "wdth": 100.0}, label="Regular"),
            AnimationStep({"wght": 700.0, "wdth": 75.0}, label="Condensed Bold"),
            AnimationStep({"wght": 700.0, "wdth": 100.0}, label="Bold"),
        ],
        text="A",
        frames_per_segment=3,
        fps=12,
        preset="draft",
    )

    assert asset.filename == "roboto-animation-path.png"
    assert asset.media_type == "image/apng"
    assert asset.frame_count == 5
    assert asset.fps == 12
    assert asset.frame_labels[0] == "Regular"
    assert asset.frame_labels[-1] == "Bold"
    assert asset.data.startswith(b"\x89PNG\r\n\x1a\n")
    assert b"acTL" in asset.data


def test_animation_builder_supports_easing_and_coordinate_captions(testdata_dir) -> None:
    font_path = testdata_dir / "Roboto-VariableFont_wdth,wght.ttf"
    font = FontLoader.open(str(font_path))

    asset = AnimationPreviewBuilder.build_path(
        font,
        [
            AnimationStep({"wght": 400.0, "wdth": 100.0}, label="Regular"),
            AnimationStep({"wght": 700.0, "wdth": 75.0}, label="Condensed Bold"),
        ],
        text="A",
        frames_per_segment=3,
        preset="draft",
        easing="ease-in-out",
        caption_mode="both",
    )

    assert asset.frame_count == 3
    assert asset.frame_labels[0] == "Regular | wdth=100, wght=400"
    assert asset.frame_labels[-1] == "Condensed Bold | wdth=75, wght=700"


def test_animation_builder_named_instance_path_requires_two_steps(testdata_dir) -> None:
    font_path = testdata_dir / "Roboto-VariableFont_wdth,wght.ttf"
    font = FontLoader.open(str(font_path))

    with pytest.raises(ValueError, match="at least two steps"):
        AnimationPreviewBuilder.build_named_instance_path(font, ["Bold"])


def test_animation_builder_writes_frame_package(testdata_dir, tmp_path) -> None:
    font_path = testdata_dir / "Roboto-VariableFont_wdth,wght.ttf"
    font = FontLoader.open(str(font_path))

    package = AnimationPreviewBuilder.build_path_package(
        font,
        [
            AnimationStep({"wght": 400.0, "wdth": 100.0}, label="Regular"),
            AnimationStep({"wght": 700.0, "wdth": 75.0}, label="Condensed Bold"),
        ],
        text="A",
        frames_per_segment=3,
        preset="draft",
        easing="ease-out",
        caption_mode="both",
    )

    assert isinstance(package, AnimationFramePackage)
    assert package.storyboard.filename.endswith("-storyboard.png")
    assert len(package.frames) == 3
    written = package.write_to(tmp_path / "animation-package")
    assert (written / "manifest.json").exists()
    payload = json.loads((written / "manifest.json").read_text(encoding="utf-8"))
    assert payload["frame_count"] == 3
    assert payload["storyboard"].endswith(".png")
    assert payload["frames"][0]["filename"] == "frame-001.png"
    assert "wdth=100" in payload["frames"][0]["label"]


def test_animation_builder_writes_review_package(testdata_dir, tmp_path) -> None:
    font_path = testdata_dir / "Roboto-VariableFont_wdth,wght.ttf"
    font = FontLoader.open(str(font_path))

    package = AnimationPreviewBuilder.build_path_review_package(
        font,
        [
            AnimationStep({"wght": 400.0, "wdth": 100.0}, label="Regular"),
            AnimationStep({"wght": 700.0, "wdth": 75.0}, label="Condensed Bold"),
        ],
        text="A",
        frames_per_segment=3,
        preset="draft",
        caption_mode="both",
    )

    assert isinstance(package, AnimationReviewPackage)
    written = package.write_to(tmp_path / "animation-review")
    markdown = written / "roboto-animation-path-storyboard.md"
    html = written / "roboto-animation-path-storyboard.html"
    manifest = written / "roboto-animation-path-storyboard-manifest.json"
    assert markdown.exists()
    assert html.exists()
    assert manifest.exists()
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    assert payload["type"] == "animation-review-package"
    assert payload["storyboard"].endswith(".png")


def test_animation_builder_writes_showcase_package(testdata_dir, tmp_path) -> None:
    font_path = testdata_dir / "Roboto-VariableFont_wdth,wght.ttf"
    font = FontLoader.open(str(font_path))

    package = AnimationPreviewBuilder.build_path_showcase_package(
        font,
        [
            AnimationStep({"wght": 400.0, "wdth": 100.0}, label="Regular"),
            AnimationStep({"wght": 700.0, "wdth": 75.0}, label="Condensed Bold"),
        ],
        text="A",
        frames_per_segment=3,
        preset="draft",
        caption_mode="both",
    )

    assert isinstance(package, AnimationShowcasePackage)
    written = package.write_to(tmp_path / "animation-showcase")
    assert (written / "roboto-animation-path.png").exists()
    assert (written / "roboto-animation-path-showcase.html").exists()
    assert (written / "roboto-animation-path-showcase-manifest.json").exists()
    assert (written / "roboto-animation-path-storyboard.html").exists()
    payload = json.loads(
        (written / "roboto-animation-path-showcase-manifest.json").read_text(encoding="utf-8")
    )
    assert payload["type"] == "animation-showcase-package"
    assert payload["animation"]["filename"] == "roboto-animation-path.png"
    assert payload["storyboard"].endswith(".png")
