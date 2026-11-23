"""Tests for TTC deduplication telemetry in FontQaReporter (FONT-543)."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

import pytest

from aspose_font import FontLoader, FontQaReporter
from aspose_font.ttf.collection_builder import build_ttc


def _get_test_font_paths() -> list[Path]:
    """Get paths to test font files (Roboto fonts share several tables)."""
    testdata_dir = Path(__file__).resolve().parents[1] / "testdata"
    return [
        testdata_dir / "Fonts" / "Roboto-Regular.ttf",
        testdata_dir / "Fonts" / "Roboto-Medium.ttf",
    ]


def test_qa_ttc_dedup_telemetry_with_dedup_enabled() -> None:
    """FontQaReporter should record ttc_raw_size, ttc_dedup_size, and calculate savings."""
    font_paths = _get_test_font_paths()
    if not all(p.exists() for p in font_paths):
        pytest.skip("Test fonts not available")

    with tempfile.TemporaryDirectory() as tmp_dir:
        output_path_dedup = Path(tmp_dir) / "dedup.ttc"
        output_path_no_dedup = Path(tmp_dir) / "nodeup.ttc"

        build_ttc(font_paths, output_path_dedup, dedup=True)
        build_ttc(font_paths, output_path_no_dedup, dedup=False)

        ttc_dedup_size = output_path_dedup.stat().st_size
        ttc_raw_size = output_path_no_dedup.stat().st_size

        font = FontLoader.open(output_path_dedup, collection_index=0)
        report = FontQaReporter.build(
            font,
            source_label="Roboto TTC",
            ttc_raw_size=ttc_raw_size,
            ttc_dedup_size=ttc_dedup_size,
        )

        payload = report.to_dict()
        assert "telemetry" in payload
        assert payload["telemetry"] is not None
        assert payload["telemetry"]["ttc_raw_size"] == ttc_raw_size
        assert payload["telemetry"]["ttc_dedup_size"] == ttc_dedup_size
        assert "ttc_dedup_savings_percent" in payload["telemetry"]

        expected_savings = round((ttc_raw_size - ttc_dedup_size) / ttc_raw_size * 100, 2)
        assert payload["telemetry"]["ttc_dedup_savings_percent"] == expected_savings
        assert payload["telemetry"]["ttc_dedup_savings_percent"] >= 0


def test_qa_ttc_telemetry_without_both_sizes() -> None:
    """FontQaReporter should not include telemetry when both sizes are not provided."""
    font_paths = _get_test_font_paths()
    if not all(p.exists() for p in font_paths):
        pytest.skip("Test fonts not available")

    with tempfile.TemporaryDirectory() as tmp_dir:
        output_path = Path(tmp_dir) / "font.ttf"
        shutil.copy(font_paths[0], output_path)
        font = FontLoader.open(output_path)

        report = FontQaReporter.build(
            font,
            source_label="Roboto",
            ttc_raw_size=1000,
        )

        payload = report.to_dict()
        assert payload.get("telemetry") is None or payload["telemetry"] == {}


def test_qa_ttc_telemetry_package_includes_telemetry() -> None:
    """FontQaReporter.build_package should include telemetry in the report payload."""
    font_paths = _get_test_font_paths()
    if not all(p.exists() for p in font_paths):
        pytest.skip("Test fonts not available")

    with tempfile.TemporaryDirectory() as tmp_dir:
        output_path = Path(tmp_dir) / "dedup.ttc"
        output_path_no_dedup = Path(tmp_dir) / "nodeup.ttc"

        build_ttc(font_paths, output_path, dedup=True)
        build_ttc(font_paths, output_path_no_dedup, dedup=False)

        ttc_dedup_size = output_path.stat().st_size
        ttc_raw_size = output_path_no_dedup.stat().st_size

        font = FontLoader.open(output_path, collection_index=0)
        package = FontQaReporter.build_package(
            font,
            Path(tmp_dir) / "qa-package",
            source_label="Roboto TTC",
            ttc_raw_size=ttc_raw_size,
            ttc_dedup_size=ttc_dedup_size,
        )

        payload = package.report.to_dict()
        assert "telemetry" in payload
        assert payload["telemetry"] is not None
        assert payload["telemetry"]["ttc_raw_size"] == ttc_raw_size
        assert payload["telemetry"]["ttc_dedup_size"] == ttc_dedup_size
        assert "ttc_dedup_savings_percent" in payload["telemetry"]


def test_qa_ttc_telemetry_zero_raw_size_edge_case() -> None:
    """FontQaReporter should handle zero raw size without division by zero."""
    font_paths = _get_test_font_paths()
    if not all(p.exists() for p in font_paths):
        pytest.skip("Test fonts not available")

    with tempfile.TemporaryDirectory() as tmp_dir:
        output_path = Path(tmp_dir) / "font.ttf"
        shutil.copy(font_paths[0], output_path)
        font = FontLoader.open(output_path)

        report = FontQaReporter.build(
            font,
            source_label="Roboto",
            ttc_raw_size=0,
            ttc_dedup_size=0,
        )

        payload = report.to_dict()
        assert "telemetry" in payload
        assert payload["telemetry"] is not None
        assert payload["telemetry"]["ttc_raw_size"] == 0
        assert payload["telemetry"]["ttc_dedup_size"] == 0
        assert payload["telemetry"]["ttc_dedup_savings_percent"] == 0.0


def test_qa_ttc_telemetry_negative_savings_edge_case() -> None:
    """FontQaReporter should handle case where dedup size is larger than raw size."""
    font_paths = _get_test_font_paths()
    if not all(p.exists() for p in font_paths):
        pytest.skip("Test fonts not available")

    with tempfile.TemporaryDirectory() as tmp_dir:
        output_path = Path(tmp_dir) / "font.ttf"
        shutil.copy(font_paths[0], output_path)
        font = FontLoader.open(output_path)

        raw_size = 1000
        dedup_size = 1200

        report = FontQaReporter.build(
            font,
            source_label="Roboto",
            ttc_raw_size=raw_size,
            ttc_dedup_size=dedup_size,
        )

        payload = report.to_dict()
        assert "telemetry" in payload
        assert payload["telemetry"] is not None
        assert payload["telemetry"]["ttc_raw_size"] == raw_size
        assert payload["telemetry"]["ttc_dedup_size"] == dedup_size
        expected_savings = round((raw_size - dedup_size) / raw_size * 100, 2)
        assert payload["telemetry"]["ttc_dedup_savings_percent"] == expected_savings
