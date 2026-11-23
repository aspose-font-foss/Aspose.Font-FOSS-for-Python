"""Tests for Web Font Optimizer README summary generation."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from aspose_font import FontLoader, WebFontOptimizer


@pytest.fixture
def roboto_path(testdata_dir: Path) -> Path:
    return testdata_dir / "Roboto-VariableFont_wdth,wght.ttf"


@pytest.fixture
def roboto(roboto_path: Path) -> WebFontOptimizer:
    font = FontLoader.open(str(roboto_path))
    assert font.__class__.__name__ == "TtfFont"
    return font


def test_web_optimizer_generate_summary_contains_size_fields(roboto: WebFontOptimizer) -> None:
    """Test that the summary contains source/output size information."""
    package = WebFontOptimizer.build(
        roboto,
        source_path=Path("testdata/Roboto-VariableFont_wdth,wght.ttf"),
        presets=("latin",),
        text="Aspose Web",
        include_woff=False,
    )

    summary = WebFontOptimizer.generate_summary(package)

    assert "Source size" in summary
    assert "Output size" in summary
    assert "bytes" in summary

    lines = summary.split("\n")
    size_lines = [line for line in lines if "**Source size:**" in line]
    assert len(size_lines) >= 1

    output_lines = [line for line in lines if "**Output size:**" in line]
    assert len(output_lines) >= 1


def test_web_optimizer_generate_summary_contains_readiness(roboto: WebFontOptimizer) -> None:
    """Test that the summary contains readiness score and status."""
    package = WebFontOptimizer.build(
        roboto,
        source_path=Path("testdata/Roboto-VariableFont_wdth,wght.ttf"),
        presets=("latin",),
        text="Aspose Web",
        include_woff=False,
    )

    summary = WebFontOptimizer.generate_summary(package)

    assert "Readiness score" in summary
    assert "ready" in summary or "caution" in summary or "warning" in summary or "blocked" in summary

    lines = summary.split("\n")
    readiness_lines = [line for line in lines if "**Readiness score:**" in line]
    assert len(readiness_lines) >= 1

    for line in readiness_lines:
        parts = line.split()
        score_found = any(part.isdigit() for part in parts)
        assert score_found


def test_web_optimizer_generate_summary_contains_coverage(roboto: WebFontOptimizer) -> None:
    """Test that the summary contains coverage information."""
    package = WebFontOptimizer.build(
        roboto,
        source_path=Path("testdata/Roboto-VariableFont_wdth,wght.ttf"),
        presets=("latin",),
        text="Aspose Web",
        include_woff=False,
    )

    summary = WebFontOptimizer.generate_summary(package)

    assert "Coverage" in summary
    assert "codepoints" in summary

    lines = summary.split("\n")
    coverage_lines = [line for line in lines if "**Coverage:**" in line]
    assert len(coverage_lines) >= 1

    for line in coverage_lines:
        assert "/" in line and "codepoints" in line


def test_web_optimizer_generate_summary_cli_integration(
    roboto_path: Path,
    tmp_path: Path,
) -> None:
    """Test CLI integration for web-optim-summary command."""
    result = subprocess.run(
        [sys.executable, "-m", "aspose_font.cli", "web-optim-summary", str(roboto_path)],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "Source size" in result.stdout
    assert "Output size" in result.stdout
    assert "Readiness score" in result.stdout
    assert "Coverage" in result.stdout

    output_file = tmp_path / "summary.md"
    result = subprocess.run(
        [sys.executable, "-m", "aspose_font.cli", "web-optim-summary", str(roboto_path), "--output", str(output_file)],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert output_file.exists()
    content = output_file.read_text(encoding="utf-8")
    assert "Source size" in content
    assert "Output size" in content
    assert "Readiness score" in content
    assert "Coverage" in content


def test_web_optimizer_generate_summary_format(roboto: WebFontOptimizer) -> None:
    """Test that the summary follows the exact markdown format."""
    package = WebFontOptimizer.build(
        roboto,
        source_path=Path("testdata/Roboto-VariableFont_wdth,wght.ttf"),
        presets=("latin",),
        include_woff=False,
    )

    summary = WebFontOptimizer.generate_summary(package)

    assert summary.startswith("### Web Font Optimizer Summary")
    assert "- **Source size:**" in summary
    assert "- **Output size:**" in summary
    assert "- **Compression ratio:**" in summary
    assert "- **Readiness score:**" in summary
    assert "- **Coverage:**" in summary


def test_web_optimizer_generate_summary_markdown_with_cli_flag(
    roboto_path: Path,
    tmp_path: Path,
) -> None:
    """Test --summary flag creates summary.md in output directory."""
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    result = subprocess.run(
        [
            sys.executable, "-m", "aspose_font.cli", "web-optimize",
            str(roboto_path), str(output_dir), "--summary"
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    summary_path = output_dir / "summary.md"
    assert summary_path.exists()

    content = summary_path.read_text(encoding="utf-8")
    assert "Source size" in content
    assert "Output size" in content
    assert "Readiness score" in content
