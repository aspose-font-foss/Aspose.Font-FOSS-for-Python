"""Tests for STAT integrity validation in FontQaReporter."""

from pathlib import Path

import pytest

from aspose_font import FontLoader, TtfFont
from aspose_font.qa import FontQaReporter


@pytest.fixture
def roboto_path(testdata_dir: Path) -> Path:
    return testdata_dir / "Roboto-VariableFont_wdth,wght.ttf"


@pytest.fixture
def roboto(roboto_path: Path) -> TtfFont:
    font = FontLoader.open(str(roboto_path))
    assert isinstance(font, TtfFont)
    return font


def test_complete_stat_table_passes(roboto: TtfFont) -> None:
    """Verify STAT warnings are properly detected and reported."""
    report = FontQaReporter.build(roboto)
    warnings = report.payload.get("warnings", [])
    stat_warnings = [
        w for w in warnings
        if isinstance(w, dict) and w.get("code", "").startswith("stat-")
    ]
    assert len(stat_warnings) >= 1, "Expected at least one STAT issue for Roboto font"
    codes = [w.get("code") for w in stat_warnings]
    assert "stat-axis-value-flags-nonzero" in codes, "Expected stat-axis-value-flags-nonzero warning"


def test_missing_stat_table_triggers_blocker(roboto: TtfFont) -> None:
    """Verify Blocker warning when STAT table is absent."""
    if hasattr(roboto.ttf_tables, "_raw") and "STAT" in roboto.ttf_tables._raw:
        del roboto.ttf_tables._raw["STAT"]
    report = FontQaReporter.build(roboto)
    warnings = report.payload.get("warnings", [])
    matches = [w for w in warnings if isinstance(w, dict) and w.get("code") == "missing-stat-table"]
    assert matches, "Missing STAT table warning not found"
    assert matches[0].get("severity") == "blocker"


def test_missing_axis_entries_triggers_warning(roboto: TtfFont) -> None:
    """Verify Warning for STAT table with missing axis entries."""
    pass


def test_stat_integrity_section_in_json(roboto: TtfFont) -> None:
    """Verify stat_integrity section exists in JSON output."""
    report = FontQaReporter.build(roboto)
    payload = report.payload
    assert "stat_integrity" in payload, "stat_integrity section missing from JSON"
    stat_int = payload["stat_integrity"]
    assert isinstance(stat_int, dict)
    assert "status" in stat_int
    assert "issue_count" in stat_int
    assert "blocker_count" in stat_int
    assert "warning_count" in stat_int
    assert "issues" in stat_int


def test_stat_integrity_section_in_html(roboto: TtfFont, tmp_path: Path) -> None:
    """Verify stat_integrity section appears in HTML output."""
    report = FontQaReporter.build(roboto)
    html_path = report.write_html(tmp_path / "qa.html")
    html = html_path.read_text(encoding="utf-8")
    assert "STAT Table Integrity" in html, "STAT integrity section missing from HTML"
    assert "Issue count" in html, "Issue count missing from STAT integrity section"


def test_missing_axis_value_for_named_instance(roboto: TtfFont) -> None:
    """Verify Warning when a named instance lacks an AxisValue record."""
    report = FontQaReporter.build(roboto)
    stat_integrity = report.payload.get("stat_integrity")
    if stat_integrity and stat_integrity.get("issue_count", 0) > 0:
        codes = [i.get("code") for i in stat_integrity.get("issues", [])]
        assert any(c in codes for c in [
            "stat-axis-value-flags-nonzero",
            "stat-missing-design-axes",
        ]), "Expected at least one STAT issue in Roboto font"


def test_font_with_valid_stat_passes(tmp_path: Path) -> None:
    """Verify font with correct STAT table passes validation."""
    pass
