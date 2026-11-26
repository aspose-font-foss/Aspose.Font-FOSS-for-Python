"""Tests for FONT-547 Multi-Axis Variation Waterfall Specimen Generator."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from aspose_font import FontLoader, generate_multi_axis_waterfall

ROBOTO = str(Path(__file__).resolve().parents[1] / "testdata" / "Roboto-VariableFont_wdth,wght.ttf")
CLI = [sys.executable, "-m", "aspose_font.cli"]


def run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(CLI + list(args), capture_output=True, text=True)


def test_generate_multi_axis_waterfall_produces_png_for_two_axes(roboto: FontLoader):
    bundles = [
        bundle
        for _resolved, bundle in roboto.smart_instancer.build_web_bundles(
            ["Bold", "Condensed Bold"],
            include_default=True,
            include_woff=False,
            preview_text="Hamburgefons 0123456789",
        )
    ]

    preview = generate_multi_axis_waterfall(
        bundles,
        axes=["wght", "wdth"],
        preview_text="Hamburgefons 0123456789",
        font=roboto,
    )

    assert preview.filename == "multi-axis-waterfall.png"
    assert preview.media_type == "image/png"
    assert preview.data.startswith(b"\x89PNG\r\n\x1a\n")


def test_generate_multi_axis_waterfall_produces_correct_dimensions(roboto: FontLoader):
    bundles = [
        bundle
        for _resolved, bundle in roboto.smart_instancer.build_web_bundles(
            ["Bold", "Condensed Bold"],
            include_default=True,
            include_woff=False,
            preview_text="Hamburgefons 0123456789",
        )
    ]

    preview = generate_multi_axis_waterfall(
        bundles,
        axes=["wght", "wdth"],
        preview_text="Hamburgefons 0123456789",
        font=roboto,
    )

    from aspose_font.preview import _decode_png_rgb

    width, height, pixels = _decode_png_rgb(preview.data)

    assert width > 0 and height > 0
    assert len(pixels) == width * height * 3


def test_generate_multi_axis_waterfall_with_pdf_format(roboto: FontLoader):
    bundles = [
        bundle
        for _resolved, bundle in roboto.smart_instancer.build_web_bundles(
            ["Bold", "Condensed Bold"],
            include_default=True,
            include_woff=False,
            preview_text="Hamburgefons 0123456789",
        )
    ]

    preview = generate_multi_axis_waterfall(
        bundles,
        axes=["wght", "wdth"],
        preview_text="Hamburgefons 0123456789",
        output_format="pdf",
        font=roboto,
    )

    assert preview.filename == "multi-axis-waterfall.pdf"
    assert preview.media_type == "application/pdf"
    assert preview.data.startswith(b"%PDF-")


def test_generate_multi_axis_waterfall_with_pptx_format(roboto: FontLoader):
    bundles = [
        bundle
        for _resolved, bundle in roboto.smart_instancer.build_web_bundles(
            ["Bold", "Condensed Bold"],
            include_default=True,
            include_woff=False,
            preview_text="Hamburgefons 0123456789",
        )
    ]

    preview = generate_multi_axis_waterfall(
        bundles,
        axes=["wght", "wdth"],
        preview_text="Hamburgefons 0123456789",
        output_format="pptx",
        font=roboto,
    )

    assert preview.filename == "multi-axis-waterfall.pptx"
    assert preview.media_type == "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    assert preview.data.startswith(b"PK")


def test_generate_multi_axis_waterfall_requires_bundles():

    try:
        generate_multi_axis_waterfall([], axes=["wght"], font=None)
    except ValueError as exc:
        assert "Multi-axis waterfall export requires at least one web font bundle" in str(exc)


def test_generate_multi_axis_waterfall_requires_axes():
    bundles = [
        bundle
        for _resolved, bundle in FontLoader.open(ROBOTO).smart_instancer.build_web_bundles(
            ["Bold"],
            include_default=True,
            include_woff=False,
            preview_text="Hamburgefons 0123456789",
        )
    ]

    try:
        generate_multi_axis_waterfall(bundles, axes=[])
    except ValueError as exc:
        assert "Axes list cannot be empty" in str(exc)


def test_generate_multi_axis_waterfall_invalid_axis(roboto: FontLoader):
    bundles = [
        bundle
        for _resolved, bundle in roboto.smart_instancer.build_web_bundles(
            ["Bold"],
            include_default=True,
            include_woff=False,
            preview_text="Hamburgefons 0123456789",
        )
    ]

    try:
        generate_multi_axis_waterfall(bundles, axes=["nonexistent"], font=roboto)
    except ValueError as exc:
        assert "Font does not contain axis" in str(exc)
        assert "Available axes" in str(exc)


def test_generate_multi_axis_waterfall_invalid_format(roboto: FontLoader):
    bundles = [
        bundle
        for _resolved, bundle in roboto.smart_instancer.build_web_bundles(
            ["Bold"],
            include_default=True,
            include_woff=False,
            preview_text="Hamburgefons 0123456789",
        )
    ]

    try:
        generate_multi_axis_waterfall(bundles, axes=["wght"], output_format="svg", font=roboto)
    except ValueError as exc:
        assert "Unsupported output format" in str(exc)
        assert "Supported: png, pdf" in str(exc)


def test_cli_preview_multi_axis_waterfall_writes_png(tmp_path: Path):
    out = tmp_path / "multi-axis-waterfall.png"
    result = run(
        "preview-multi-axis-waterfall",
        ROBOTO,
        str(out),
        "--axes",
        "wght,wdth",
        "--instance-name",
        "Bold",
        "--include-default",
        "--text",
        "Hamburgefons 0123456789",
    )
    assert result.returncode == 0
    assert out.exists()
    assert out.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    assert "Saved:" in result.stdout


def test_cli_preview_multi_axis_waterfall_pdf_output(tmp_path: Path):
    out = tmp_path / "multi-axis-waterfall.pdf"
    result = run(
        "preview-multi-axis-waterfall",
        ROBOTO,
        str(out),
        "--axes",
        "wght,wdth",
        "--all-named",
        "--format",
        "pdf",
        "--text",
        "Hamburgefons 0123456789",
    )
    assert result.returncode == 0
    assert out.exists()
    assert out.read_bytes().startswith(b"%PDF-")
    assert "Saved:" in result.stdout


def test_cli_preview_multi_axis_waterfall_pptx_output(tmp_path: Path):
    out = tmp_path / "multi-axis-waterfall.pptx"
    result = run(
        "preview-multi-axis-waterfall",
        ROBOTO,
        str(out),
        "--axes",
        "wght,wdth",
        "--all-named",
        "--format",
        "pptx",
        "--text",
        "Hamburgefons 0123456789",
    )
    assert result.returncode == 0
    assert out.exists()
    assert out.read_bytes().startswith(b"PK")
    assert "Saved:" in result.stdout


def test_cli_preview_multi_axis_waterfall_requires_axes(roboto: FontLoader):
    result = run(
        "preview-multi-axis-waterfall",
        ROBOTO,
        "output.png",
    )
    assert result.returncode != 0
    assert "--axes" in result.stderr


def test_cli_preview_multi_axis_waterfall_requires_variable_font(tmp_path: Path):
    static_font = str(Path(__file__).resolve().parents[1] / "testdata" / "Fonts" / "Roboto-Regular.ttf")
    out = tmp_path / "multi-axis-waterfall.png"
    result = run(
        "preview-multi-axis-waterfall",
        static_font,
        str(out),
        "--axes",
        "wght,wdth",
    )
    assert result.returncode != 0
    assert "variable" in result.stderr.lower()


def test_cli_preview_multi_axis_waterfall_invalid_axis(tmp_path: Path):
    out = tmp_path / "multi-axis-waterfall.png"
    result = run(
        "preview-multi-axis-waterfall",
        ROBOTO,
        str(out),
        "--axes",
        "invalid",
        "--all-named",
    )
    assert result.returncode != 0
    assert "Font does not contain axis" in result.stderr
