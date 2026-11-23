"""Tests for FONT-213 Waterfall & Matrix Export."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from aspose_font import FontLoader, generate_waterfall_matrix
from aspose_font.preview import _decode_png_rgb

ROBOTO = str(Path(__file__).resolve().parents[1] / "testdata" / "Roboto-VariableFont_wdth,wght.ttf")
CLI = [sys.executable, "-m", "aspose_font.cli"]


def run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(CLI + list(args), capture_output=True, text=True)


def test_generate_waterfall_matrix_produces_png_with_expected_structure(roboto: FontLoader):
    bundles = [
        bundle
        for _resolved, bundle in roboto.smart_instancer.build_web_bundles(
            ["Bold", "Condensed Bold"],
            include_default=True,
            include_woff=False,
            preview_text="Hamburgefons 0123456789",
        )
    ]

    preview = generate_waterfall_matrix(
        bundles,
        preview_text="Hamburgefons 0123456789",
    )

    assert preview.filename == "waterfall-matrix.png"
    assert preview.media_type == "image/png"
    assert preview.data.startswith(b"\x89PNG\r\n\x1a\n")

    width, height, _pixels = _decode_png_rgb(preview.data)
    assert width > 0 and height > 0


def test_generate_waterfall_matrix_with_pdf_format(roboto: FontLoader):
    bundles = [
        bundle
        for _resolved, bundle in roboto.smart_instancer.build_web_bundles(
            ["Bold", "Condensed Bold"],
            include_default=True,
            include_woff=False,
            preview_text="Hamburgefons 0123456789",
        )
    ]

    preview = generate_waterfall_matrix(
        bundles,
        preview_text="Hamburgefons 0123456789",
        output_format="pdf",
    )

    assert preview.filename == "waterfall-matrix.pdf"
    assert preview.media_type == "application/pdf"
    assert preview.data.startswith(b"%PDF-")


def test_cli_preview_waterfall_matrix_writes_png(tmp_path: Path):
    out = tmp_path / "waterfall-matrix.png"
    result = run(
        "preview-waterfall-matrix",
        ROBOTO,
        str(out),
        "--instance-name",
        "Bold",
        "--instance-name",
        "Condensed Bold",
        "--include-default",
        "--text",
        "Hamburgefons 0123456789",
    )
    assert result.returncode == 0
    assert out.exists()
    assert out.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    assert "Saved:" in result.stdout


def test_cli_preview_waterfall_matrix_pdf_output(tmp_path: Path):
    out = tmp_path / "waterfall-matrix.pdf"
    result = run(
        "preview-waterfall-matrix",
        ROBOTO,
        str(out),
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


def test_cli_preview_waterfall_matrix_required_arguments_validation(roboto: FontLoader):
    result = run(
        "preview-waterfall-matrix",
        ROBOTO,
        "output.png",
    )
    assert result.returncode != 0
    assert "preview-waterfall-matrix requires --all-named, --include-default, or at least one --instance-name" in result.stderr


def test_generate_waterfall_matrix_requires_bundles():
    try:
        generate_waterfall_matrix([])
    except ValueError as exc:
        assert "Waterfall & matrix export requires at least one web font bundle" in str(exc)


def test_generate_waterfall_matrix_invalid_format():
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
        generate_waterfall_matrix(bundles, output_format="svg")
    except ValueError as exc:
        assert "Unsupported output format" in str(exc)
        assert "Supported: png, pdf" in str(exc)
