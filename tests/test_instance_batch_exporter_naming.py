"""Tests for custom naming pattern support in NamedInstanceBatchExporter."""

from __future__ import annotations

from pathlib import Path

import pytest

from aspose_font import TtfFont


def test_batch_exporter_default_naming_unchanged(roboto: TtfFont, tmp_path: Path) -> None:
    """Verify default naming works when name_format is not provided."""
    from aspose_font.instancing import NamedInstanceBatchExporter

    out_dir = tmp_path / "exports_default"
    result = NamedInstanceBatchExporter.export_all(roboto, out_dir, format="woff2")

    assert result.format_data is None

    assert len(result.output_files) >= 2
    for file_path in result.output_files:
        assert file_path.exists()
        assert ".woff2" in file_path.name


def test_batch_exporter_custom_format_with_placeholders(roboto: TtfFont, tmp_path: Path) -> None:
    """Verify custom pattern correctly substitutes placeholders."""
    from aspose_font.instancing import NamedInstanceBatchExporter

    out_dir = tmp_path / "exports_custom"
    result = NamedInstanceBatchExporter.export_all(
        roboto, out_dir, format="woff2", name_format="{family}-{weight}"
    )

    assert result.format_data is not None
    assert len(result.format_data) == len(result.output_files)

    for data in result.format_data:
        assert "family" in data
        assert "style" in data
        assert "weight" in data
        assert "width" in data
        assert "italic" in data
        assert "filename" in data

    assert len(result.output_files) >= 2
    for file_path in result.output_files:
        assert file_path.exists()
        assert "-" in file_path.stem


def test_batch_exporter_format_with_width_placeholder(roboto: TtfFont, tmp_path: Path) -> None:
    """Verify width placeholder substitution (if width axis exists)."""
    from aspose_font.instancing import NamedInstanceBatchExporter

    out_dir = tmp_path / "exports_width"
    result = NamedInstanceBatchExporter.export_all(
        roboto, out_dir, format="woff2", name_format="{family}-{width}"
    )

    assert result.format_data is not None
    for data, file_path in zip(result.format_data, result.output_files):
        width_value = data["width"]
        assert width_value is None or isinstance(width_value, int)
        if width_value is not None:
            assert str(width_value) in file_path.stem


def test_batch_exporter_format_with_italic_placeholder(roboto: TtfFont, tmp_path: Path) -> None:
    """Verify italic placeholder substitutes to 'italic' or 'regular'."""
    from aspose_font.instancing import NamedInstanceBatchExporter

    out_dir = tmp_path / "exports_italic"
    result = NamedInstanceBatchExporter.export_all(
        roboto, out_dir, format="woff2", name_format="{family}-{italic}"
    )

    assert result.format_data is not None
    expected_values = {"italic", "regular"}
    for data, file_path in zip(result.format_data, result.output_files):
        italic_value = data["italic"]
        assert italic_value in expected_values
        assert italic_value in file_path.stem


def test_batch_exporter_invalid_placeholder_raises(roboto: TtfFont, tmp_path: Path) -> None:
    """Verify unknown placeholder raises ValueError."""
    from aspose_font.instancing import NamedInstanceBatchExporter

    out_dir = tmp_path / "exports_invalid"

    with pytest.raises(ValueError, match="Unknown placeholder"):
        NamedInstanceBatchExporter.export_all(
            roboto, out_dir, format="woff2", name_format="{family}-{unknown}"
        )


def test_batch_exporter_empty_width_handled(roboto: TtfFont, tmp_path: Path) -> None:
    """Verify empty width value handled gracefully."""
    from aspose_font.instancing import NamedInstanceBatchExporter

    out_dir = tmp_path / "exports_empty_width"
    result = NamedInstanceBatchExporter.export_all(
        roboto, out_dir, format="woff2", name_format="{family}-Weight{weight}-Width{width}-Style{style}"
    )

    assert result.format_data is not None
    for file_path in result.output_files:
        assert file_path.exists()
        assert "WidthNone" not in file_path.name


def test_batch_exporter_format_data_structure(roboto: TtfFont, tmp_path: Path) -> None:
    """Verify format_data structure matches specification."""
    from aspose_font.instancing import NamedInstanceBatchExporter

    out_dir = tmp_path / "exports_structure"
    result = NamedInstanceBatchExporter.export_all(
        roboto, out_dir, format="ttf", name_format="{family}_{style}_{weight}"
    )

    assert result.format_data is not None
    assert isinstance(result.format_data, list)

    for data in result.format_data:
        assert isinstance(data, dict)
        assert isinstance(data["family"], str)
        assert isinstance(data["style"], str)
        assert isinstance(data["weight"], int)
        assert data["width"] is None or isinstance(data["width"], int)
        assert isinstance(data["italic"], str)
        assert data["italic"] in ("italic", "regular")
        assert isinstance(data["filename"], str)


def test_batch_exporter_format_with_all_placeholders(roboto: TtfFont, tmp_path: Path) -> None:
    """Verify pattern with all supported placeholders."""
    from aspose_font.instancing import NamedInstanceBatchExporter

    out_dir = tmp_path / "exports_all"
    pattern = "{family}-{weight}-{width}-{italic}-{style}"
    result = NamedInstanceBatchExporter.export_all(
        roboto, out_dir, format="woff2", name_format=pattern
    )

    assert result.format_data is not None
    for data, file_path in zip(result.format_data, result.output_files):
        filename_base = file_path.stem
        assert "{family}" not in filename_base
        assert "{weight}" not in filename_base
        assert "{width}" not in filename_base
        assert "{italic}" not in filename_base
        assert "{style}" not in filename_base


def test_batch_exporter_preserves_css_generation(roboto: TtfFont, tmp_path: Path) -> None:
    """Verify CSS generation still works with custom naming."""
    from aspose_font.instancing import NamedInstanceBatchExporter

    out_dir = tmp_path / "exports_css"
    result = NamedInstanceBatchExporter.export_all(
        roboto, out_dir, format="woff2", name_format="{family}-{weight}"
    )

    assert "@font-face" in result.css_content
    assert "src:" in result.css_content

    for file_path in result.output_files:
        assert file_path.name in result.css_content


def test_batch_exporter_cli_integration(roboto: TtfFont, tmp_path: Path) -> None:
    """Verify CLI integration via subprocess call."""
    import subprocess
    import sys

    font_path = Path(__file__).resolve().parents[1] / "testdata" / "Roboto-VariableFont_wdth,wght.ttf"
    out_dir = tmp_path / "cli_exports"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "aspose_font.cli",
            "instance-export",
            str(font_path),
            str(out_dir),
            "--name-format",
            "{family}-{weight}-{style}",
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    woff2_files = list(out_dir.glob("*.woff2"))
    assert len(woff2_files) >= 2
    for f in woff2_files:
        assert "-" in f.stem
