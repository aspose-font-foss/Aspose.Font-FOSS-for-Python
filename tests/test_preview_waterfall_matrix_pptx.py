"""Tests for FONT-214 Waterfall & Matrix PPTX Export."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from aspose_font import FontLoader, generate_waterfall_matrix

ROBOTO = str(Path(__file__).resolve().parents[1] / "testdata" / "Roboto-VariableFont_wdth,wght.ttf")
CLI = [sys.executable, "-m", "aspose_font.cli"]


def run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(CLI + list(args), capture_output=True, text=True)


def test_generate_waterfall_matrix_pptx_format(roboto: FontLoader):
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
        output_format="pptx",
    )

    assert preview.filename == "waterfall-matrix.pptx"
    assert preview.media_type == "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    assert preview.data.startswith(b"PK\x03\x04")


def test_cli_preview_waterfall_matrix_pptx_output(tmp_path: Path):
    out = tmp_path / "waterfall-matrix.pptx"
    result = run(
        "preview-waterfall-matrix",
        ROBOTO,
        str(out),
        "--instance-name",
        "Bold",
        "--instance-name",
        "Condensed Bold",
        "--include-default",
        "--format",
        "pptx",
        "--text",
        "Hamburgefons 0123456789",
    )
    assert result.returncode == 0
    assert out.exists()
    assert out.read_bytes().startswith(b"PK\x03\x04")
    assert "Saved:" in result.stdout


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
        assert "Supported: png, pdf, pptx" in str(exc)
