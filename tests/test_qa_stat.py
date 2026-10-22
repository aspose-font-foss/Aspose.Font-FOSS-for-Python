"""Tests for STAT table checks in QA reports."""

from pathlib import Path

import pytest

from aspose_font import FontLoader, TtfFont
from aspose_font.qa import FontQaReporter
from aspose_font.ttf.tables.fvar import AxisRecord
from aspose_font.ttf.tables.stat import build_static_stat_table


@pytest.fixture
def roboto_path(testdata_dir: Path) -> Path:
    return testdata_dir / "Roboto-VariableFont_wdth,wght.ttf"


@pytest.fixture
def roboto(roboto_path: Path) -> TtfFont:
    font = FontLoader.open(str(roboto_path))
    assert isinstance(font, TtfFont)
    return font


def test_missing_stat_table_warning(roboto: TtfFont) -> None:
    """Verify blocker warning when STAT table is absent."""
    # Remove STAT table if present
    if hasattr(roboto.ttf_tables, "_raw") and "STAT" in roboto.ttf_tables._raw:
        del roboto.ttf_tables._raw["STAT"]
    report = FontQaReporter.build(roboto)
    warnings = report.payload.get("warnings", [])
    # Expect a warning with code "missing-stat-table" and severity blocker
    matches = [w for w in warnings if isinstance(w, dict) and w.get("code") == "missing-stat-table"]
    assert matches, "Missing STAT table warning not found"
    assert matches[0].get("severity") == "blocker"


def test_axis_value_flags_warning(roboto: TtfFont) -> None:
    """Verify blocker warning when STAT AxisValue flags are non-zero."""
    # Construct a synthetic STAT table with non-zero flags (0x0003)
    axes = [AxisRecord(tag="wght", name_id=258, min_value=100, default_value=400, max_value=900, flags=0)]
    coordinates = {"wght": 700.0}
    stat_data = build_static_stat_table(
        axes,
        coordinates,
        preserve_from_source=(0x0003,),
        preserve_flags_mask=0xFFFF,
    )
    # Inject synthetic STAT table into the font
    if not hasattr(roboto.ttf_tables, "_raw"):
        raise AssertionError("Font tables do not expose raw dict")
    roboto.ttf_tables._raw["STAT"] = stat_data
    report = FontQaReporter.build(roboto)
    warnings = report.payload.get("warnings", [])
    matches = [w for w in warnings if isinstance(w, dict) and w.get("code") == "stat-axis-value-flags-nonzero"]
    assert matches, "STAT AxisValue flags warning not found"
    assert matches[0].get("severity") == "blocker"
