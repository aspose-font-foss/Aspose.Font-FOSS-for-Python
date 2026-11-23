"""Tests for NamedInstanceBatchExporter batch export workflow."""

from __future__ import annotations

from pathlib import Path

import pytest

from aspose_font import TtfFont


def test_batch_exporter_exports_all_named_instances(roboto: TtfFont, tmp_path: Path) -> None:
    """Export all named instances and verify files are created."""
    from aspose_font.instancing import NamedInstanceBatchExporter

    out_dir = tmp_path / "exports"
    result = NamedInstanceBatchExporter.export_all(roboto, out_dir, format="woff2")

    assert len(result.output_files) >= 2
    assert len(result.css_content) > 0
    assert result.format == "woff2"

    for file_path in result.output_files:
        assert file_path.exists()
        assert file_path.suffix == ".woff2"
        assert file_path.read_bytes()[:4] == b"wOF2"


def test_batch_exporter_ttf_format(roboto: TtfFont, tmp_path: Path) -> None:
    """Export in TTF format and verify files."""
    from aspose_font.instancing import NamedInstanceBatchExporter

    out_dir = tmp_path / "exports_ttf"
    result = NamedInstanceBatchExporter.export_all(roboto, out_dir, format="ttf")

    assert len(result.output_files) >= 2
    assert result.format == "ttf"

    for file_path in result.output_files:
        assert file_path.exists()
        assert file_path.suffix == ".ttf"
        header = file_path.read_bytes()[:4]
        assert header in (b"typ1", b"\x00\x01\x00\x00", b"OTTO")


def test_batch_exporter_css_generation(roboto: TtfFont, tmp_path: Path) -> None:
    """Verify CSS contains valid @font-face blocks."""
    from aspose_font.instancing import NamedInstanceBatchExporter

    out_dir = tmp_path / "exports_css"
    result = NamedInstanceBatchExporter.export_all(roboto, out_dir, format="woff2")

    assert "@font-face" in result.css_content
    assert "src:" in result.css_content
    assert "font-display: swap" in result.css_content

    for file_path in result.output_files:
        filename = file_path.name
        assert filename in result.css_content


def test_batch_exporter_include_default(roboto: TtfFont, tmp_path: Path) -> None:
    """Include default instance when requested."""
    from aspose_font.instancing import NamedInstanceBatchExporter

    out_dir = tmp_path / "exports_default"
    result = NamedInstanceBatchExporter.export_all(
        roboto, out_dir, format="woff2", include_default=True
    )

    out_dir_without = tmp_path / "exports_no_default"
    result_no_default = NamedInstanceBatchExporter.export_all(
        roboto, out_dir_without, format="woff2", include_default=False
    )

    assert len(result.output_files) >= len(result_no_default.output_files)


def test_batch_exporter_custom_naming(roboto: TtfFont, tmp_path: Path) -> None:
    """Verify custom naming strategy works."""
    from aspose_font.instancing import NamedInstanceBatchExporter

    out_dir = tmp_path / "exports_custom"
    result = NamedInstanceBatchExporter.export_all(
        roboto,
        out_dir,
        format="woff2",
        naming_strategy="ribbi-safe",
        family_suffix="-Web",
    )

    assert len(result.output_files) >= 2
    for file_path in result.output_files:
        assert file_path.name in result.css_content


def test_batch_exporter_non_variable_font_raises(testdata_dir: Path, tmp_path: Path) -> None:
    """Verify non-variable fonts raise appropriate exception."""
    from aspose_font import FontLoader
    from aspose_font._exceptions import FontNotSupportedException
    from aspose_font.instancing import NamedInstanceBatchExporter

    static_font_path = testdata_dir / "Fonts" / "Roboto-Regular.ttf"
    static_font = FontLoader.open(str(static_font_path))

    with pytest.raises(FontNotSupportedException):
        NamedInstanceBatchExporter.export_all(
            static_font,
            tmp_path / "outputs",
            format="woff2",
        )


def test_batch_exporter_output_directory_created(testdata_dir: Path, tmp_path: Path) -> None:
    """Verify output directory is created if it doesn't exist."""
    from aspose_font.instancing import NamedInstanceBatchExporter

    out_dir = tmp_path / "new" / "subdir" / "exports"

    result = NamedInstanceBatchExporter.export_all(
        str(testdata_dir / "Roboto-VariableFont_wdth,wght.ttf"),
        out_dir,
        format="woff2",
    )

    assert out_dir.exists()
    assert len(result.output_files) >= 1


def test_batch_exporter_result_structure(roboto: TtfFont, tmp_path: Path) -> None:
    """Verify BatchExportResult has all expected attributes."""
    from aspose_font.instancing import BatchExportResult, NamedInstanceBatchExporter

    out_dir = tmp_path / "exports"
    result = NamedInstanceBatchExporter.export_all(
        roboto, out_dir, format="woff2", include_default=True
    )

    assert isinstance(result, BatchExportResult)
    assert isinstance(result.instances, list)
    assert isinstance(result.output_files, list)
    assert isinstance(result.css_content, str)
    assert result.css_filename == "instances.css"
    assert result.format == "woff2"

    for file_path in result.output_files:
        assert isinstance(file_path, Path)


def test_batch_exporter_preserves_file_order(roboto: TtfFont, tmp_path: Path) -> None:
    """Verify exported files are in consistent order."""
    from aspose_font.instancing import NamedInstanceBatchExporter

    out_dir = tmp_path / "exports"

    result1 = NamedInstanceBatchExporter.export_all(roboto, out_dir / "run1", format="woff2")
    result2 = NamedInstanceBatchExporter.export_all(roboto, out_dir / "run2", format="woff2")

    filenames1 = [f.name for f in result1.output_files]
    filenames2 = [f.name for f in result2.output_files]

    assert len(filenames1) == len(filenames2)
    assert filenames1 == filenames2
