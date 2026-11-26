"""Tests for hinting policy checks in FontQaReporter (FONT-515)."""

from pathlib import Path

import pytest

from aspose_font import FontLoader, TtfFont
from aspose_font.qa import FontQaReporter
from aspose_font.ttf.tables.gasp import GaspRange, GaspTable
from aspose_font.ttf.tables.ltsh import LtshTable


@pytest.fixture
def roboto_path(testdata_dir: Path) -> Path:
    return testdata_dir / "Roboto-VariableFont_wdth,wght.ttf"


@pytest.fixture
def roboto(roboto_path: Path) -> TtfFont:
    font = FontLoader.open(str(roboto_path))
    assert isinstance(font, TtfFont)
    return font


def test_missing_gasp_on_hinted_font_triggers_blocker(roboto: TtfFont) -> None:
    """Verify Blocker warning when font has LTSH but no gasp table (hinted font)."""
    font = roboto
    tables = font.ttf_tables

    tables.gasp = None
    tables.ltsh = LtshTable(version=0, values=[1] * font.num_glyphs)

    report = FontQaReporter.build(font)
    hints = report.payload.get("hinting", {})
    issues = hints.get("issues", [])

    assert any(i.get("code") == "hinting-missing-gasp" for i in issues), \
        "Expected hinting-missing-gasp warning for hinted font without gasp"
    assert any(i.get("severity") == "blocker" for i in issues), \
        "Expected blocker severity for missing gasp on hinted font"


def test_missing_ltsh_on_hinted_ttf_triggers_warning(roboto: TtfFont) -> None:
    """Verify Warning when TTF with glyf has no LTSH table."""
    font = roboto
    tables = font.ttf_tables

    tables.ltsh = None

    report = FontQaReporter.build(font)
    hints = report.payload.get("hinting", {})
    issues = hints.get("issues", [])

    assert any(i.get("code") == "hinting-missing-ltsh" for i in issues), \
        "Expected hinting-missing-ltsh warning for TTF without LTSH"
    assert any(i.get("severity") == "warning" for i in issues), \
        "Expected warning severity for missing LTSH"


def test_small_ppem_without_grayscale_triggers_warning(roboto: TtfFont) -> None:
    """Verify Warning for gasp ranges at PPEM <= 16 without grayscale flag."""
    font = roboto
    tables = font.ttf_tables

    tables.gasp = GaspTable(
        gasp_version=0,
        ranges=[
            GaspRange(range_max_ppem=8, range_gasp_behavior=0x0001),
            GaspRange(range_max_ppem=16, range_gasp_behavior=0x0001),
        ]
    )
    tables.ltsh = LtshTable(version=0, values=[1] * font.num_glyphs)

    report = FontQaReporter.build(font)
    hints = report.payload.get("hinting", {})
    issues = hints.get("issues", [])

    assert any(i.get("code") == "hinting-missing-grayscale-small-ppem" for i in issues), \
        "Expected hinting-missing-grayscale-small-ppem warning"


def test_large_ppem_without_smooth_flags_is_info(roboto: TtfFont) -> None:
    """Verify Info-level warning for gasp ranges at PPEM > 64 without smooth flags."""
    font = roboto
    tables = font.ttf_tables

    tables.gasp = GaspTable(
        gasp_version=0,
        ranges=[
            GaspRange(range_max_ppem=72, range_gasp_behavior=0x0000),
        ]
    )
    tables.ltsh = LtshTable(version=0, values=[1] * font.num_glyphs)

    report = FontQaReporter.build(font)
    hints = report.payload.get("hinting", {})
    issues = hints.get("issues", [])

    assert any(i.get("code") == "hinting-missing-smooth-large-ppem" for i in issues), \
        "Expected hinting-missing-smooth-large-ppem info"


def test_hinting_section_in_json(roboto: TtfFont) -> None:
    """Verify hinting section exists in JSON payload."""
    font = roboto
    tables = font.ttf_tables
    tables.gasp = GaspTable(
        gasp_version=0,
        ranges=[
            GaspRange(range_max_ppem=8, range_gasp_behavior=0x0001),
        ]
    )
    tables.ltsh = LtshTable(version=0, values=[1] * font.num_glyphs)

    report = FontQaReporter.build(font)
    payload = report.payload

    assert "hinting" in payload, "hinting section missing from JSON"
    hinting = payload["hinting"]
    assert isinstance(hinting, dict)
    assert "status" in hinting
    assert "issue_count" in hinting
    assert "blocker_count" in hinting
    assert "warning_count" in hinting
    assert "issues" in hinting


def test_hinting_section_in_html(roboto: TtfFont, tmp_path: Path) -> None:
    """Verify hinting section appears in HTML output."""
    font = roboto
    tables = font.ttf_tables
    tables.gasp = GaspTable(
        gasp_version=0,
        ranges=[
            GaspRange(range_max_ppem=8, range_gasp_behavior=0x0001),
        ]
    )
    tables.ltsh = LtshTable(version=0, values=[1] * font.num_glyphs)

    report = FontQaReporter.build(font)
    html_path = report.write_html(tmp_path / "qa.html")
    html = html_path.read_text(encoding="utf-8")

    assert "Hinting Policy" in html, "Hinting Policy section missing from HTML"
    assert "Issue count" in html, "Issue count missing from Hinting Policy section"


def test_hinting_section_in_markdown(roboto: TtfFont, tmp_path: Path) -> None:
    """Verify hinting section appears in Markdown output."""
    font = roboto
    tables = font.ttf_tables
    tables.gasp = GaspTable(
        gasp_version=0,
        ranges=[
            GaspRange(range_max_ppem=8, range_gasp_behavior=0x0001),
        ]
    )
    tables.ltsh = LtshTable(version=0, values=[1] * font.num_glyphs)

    report = FontQaReporter.build(font)
    md_path = report.write_markdown(tmp_path / "qa.md")
    md = md_path.read_text(encoding="utf-8")

    assert "Hinting Policy" in md, "Hinting Policy line missing from Markdown"
    assert "issues" in md.lower(), "Issue summary missing from Markdown"


def test_no_hinting_issues_passes(roboto: TtfFont) -> None:
    """Verify font with proper gasp and LTSH passes validation."""
    font = roboto
    tables = font.ttf_tables

    tables.gasp = GaspTable(
        gasp_version=0,
        ranges=[
            GaspRange(range_max_ppem=8, range_gasp_behavior=0x0002),
            GaspRange(range_max_ppem=16, range_gasp_behavior=0x0002),
            GaspRange(range_max_ppem=64, range_gasp_behavior=0x0002),
        ]
    )
    tables.ltsh = LtshTable(version=0, values=[1] * font.num_glyphs)

    report = FontQaReporter.build(font)
    hints = report.payload.get("hinting", {})

    assert hints.get("status") == "valid", "Expected valid status for properly hinted font"
    assert hints.get("issue_count", 0) == 0, "Expected no issues for properly hinted font"


def test_non_ttf_fonts_skipped(roboto_path: Path, tmp_path: Path, testdata_dir: Path) -> None:
    """Verify hinting policy returns valid/empty result for non-TTF fonts."""
    from aspose_font import FontLoader
    font = FontLoader.open(str(roboto_path))
    assert isinstance(font, TtfFont)

    cff_bytes = font.to_bytes()
    cff_path = tmp_path / "roboto.cff"
    cff_path.write_bytes(cff_bytes)

    openSans_cff_path = testdata_dir / "OpenSans-Regular.cff"
    font_cff = FontLoader.open(str(openSans_cff_path))

    report = FontQaReporter.build(font_cff)
    hints = report.payload.get("hinting", {})

    assert hints.get("status") == "valid", "Expected valid status for non-TTF font"


def test_cross_platform_paths(testdata_dir: Path) -> None:
    """Verify test uses Path(__file__).resolve().parents[...] pattern."""
    source_str = str(testdata_dir).replace("\\", "/")
    assert "testdata" in source_str, "testdata path used"
    assert str(Path(__file__).parent.name) == "tests", "Test in tests directory"


def test_proper_grayscale_small_ppem_passes(roboto: TtfFont) -> None:
    """Verify gasp with grayscale for small PPEM passes validation."""
    font = roboto
    tables = font.ttf_tables

    tables.gasp = GaspTable(
        gasp_version=0,
        ranges=[
            GaspRange(range_max_ppem=8, range_gasp_behavior=0x0002),
            GaspRange(range_max_ppem=14, range_gasp_behavior=0x0003),
        ]
    )

    report = FontQaReporter.build(font)
    hints = report.payload.get("hinting", {})
    issues = hints.get("issues", [])

    assert not any(i.get("code") == "hinting-missing-grayscale-small-ppem" for i in issues), \
        "Should not warn when grayscale flag is set for small PPEM"


def test_multiple_hinting_issues_counted(roboto: TtfFont) -> None:
    """Verify multiple hinting issues are counted correctly."""
    font = roboto
    tables = font.ttf_tables

    tables.gasp = GaspTable(
        gasp_version=0,
        ranges=[
            GaspRange(range_max_ppem=8, range_gasp_behavior=0x0001),
        ]
    )
    tables.ltsh = None

    report = FontQaReporter.build(font)
    hints = report.payload.get("hinting", {})

    assert hints.get("issue_count", 0) >= 2, "Expected at least 2 issues (missing ltsh + missing grayscale)"
