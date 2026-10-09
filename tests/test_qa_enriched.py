"""Tests for enriched Font QA Report payloads with compatibility, delta, and size data."""

from __future__ import annotations

from pathlib import Path

import pytest

from aspose_font import FontLoader
from aspose_font.qa import FontQaReporter


@pytest.fixture(scope="module")
def variable_font() -> FontLoader:
    """Load Roboto Variable font once per module."""
    return FontLoader.open(
        Path(__file__).resolve().parents[1] / "testdata" / "Roboto-VariableFont_wdth,wght.ttf"
    )


class TestEnrichedFontQaReport:
    """Test enriched QA report fields via --include-extras flag."""

    def test_enriched_json_contains_delta_summary(self, variable_font: FontLoader) -> None:
        """When include_extras=True, JSON payload includes delta_summary key."""
        report = FontQaReporter.build(variable_font, include_extras=True)
        assert "delta_summary" in report.payload
        delta_summary = report.payload["delta_summary"]
        assert isinstance(delta_summary, dict)
        assert "glyph_count" in delta_summary

    def test_enriched_json_contains_size_summary(self, variable_font: FontLoader, tmp_path: Path) -> None:
        """When source_path is provided, JSON payload includes size_summary key."""
        json_path = tmp_path / "temp.ttf"
        font_bytes = variable_font.to_bytes()
        json_path.write_bytes(font_bytes)
        report = FontQaReporter.build(variable_font, source_path=json_path, current_size=len(font_bytes))
        assert "size_summary" in report.payload
        size_summary = report.payload["size_summary"]
        assert isinstance(size_summary, dict)
        assert "current_size_bytes" in size_summary

    def test_enriched_package_contains_delta_summary(self, variable_font: FontLoader, tmp_path: Path) -> None:
        """When include_extras=True, package includes delta_summary field."""
        package = FontQaReporter.build_package(variable_font, tmp_path / "qa-package", include_extras=True)
        assert package.delta_summary is not None
        assert isinstance(package.delta_summary, dict)

    def test_enriched_package_contains_size_summary(self, variable_font: FontLoader, tmp_path: Path) -> None:
        """When source_path is provided, package includes size_summary field."""
        json_path = tmp_path / "temp.ttf"
        font_bytes = variable_font.to_bytes()
        json_path.write_bytes(font_bytes)
        package = FontQaReporter.build_package(
            variable_font,
            tmp_path / "qa-package",
            source_path=json_path,
            current_size=len(font_bytes)
        )
        assert package.size_summary is not None
        assert isinstance(package.size_summary, dict)

    def test_cli_include_extras_flag_generates_enriched_json(self, variable_font: FontLoader, tmp_path: Path) -> None:
        """CLI flag --include-extras produces JSON with enriched fields."""
        json_path = tmp_path / "qa-report.json"
        report = FontQaReporter.build(variable_font, include_extras=True)
        report.write_json(json_path)
        json_content = json_path.read_text(encoding="utf-8")
        assert '"delta_summary"' in json_content
        assert '"size_summary"' in json_content
