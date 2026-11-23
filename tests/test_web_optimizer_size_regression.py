"""Tests for FONT-290 CI performance regression test for Web Font Optimizer size reduction."""

from __future__ import annotations

from pathlib import Path

from aspose_font import WebFontOptimizer
from aspose_font.ttf.font import TtfFont


def test_web_optimizer_size_reduction_regression(roboto: TtfFont, testdata_dir: Path) -> None:
    """Verify Web Font Optimizer produces size reduction meeting regression threshold (≤80% of source)."""
    source_path = testdata_dir / "Roboto-VariableFont_wdth,wght.ttf"
    package = WebFontOptimizer.build(
        roboto,
        source_path=source_path,
        presets=("latin",),
        include_woff=False,
    )

    size_summary = package.size_summary

    assert isinstance(size_summary, dict), "size_summary should be a dict"
    assert "source_bytes" in size_summary, "size_summary should contain source_bytes"
    assert "output_bytes" in size_summary, "size_summary should contain output_bytes"
    assert "compression_ratio" in size_summary, "size_summary should contain compression_ratio"

    source_bytes = size_summary["source_bytes"]
    output_bytes = size_summary["output_bytes"]
    compression_ratio = size_summary["compression_ratio"]

    assert isinstance(source_bytes, int), "source_bytes should be an int"
    assert isinstance(output_bytes, int), "output_bytes should be an int"

    if compression_ratio is not None:
        assert isinstance(compression_ratio, (int, float)), "compression_ratio should be a float or None"

    assert source_bytes > 0, "source_bytes should be positive"
    assert output_bytes > 0, "output_bytes should be positive"

    if compression_ratio is not None:
        assert compression_ratio <= 0.8, (
            f"Web Font Optimizer compression ratio {compression_ratio:.4f} exceeds 0.8 threshold. "
            f"Source: {source_bytes} bytes, Output: {output_bytes} bytes"
        )

    if "web_font_delta_vs_source_percent" in size_summary:
        delta_percent = size_summary["web_font_delta_vs_source_percent"]
        assert delta_percent is None or delta_percent >= 0, (
            f"web_font_delta_vs_source_percent should be positive or None, got {delta_percent}"
        )
