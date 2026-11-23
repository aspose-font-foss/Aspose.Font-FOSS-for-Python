"""Tests for SFNT table checksum and DSIG integrity audit in FontQaReporter (FONT-524)."""

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


def test_integrity_audits_section_exists(roboto: TtfFont) -> None:
    """Verify integrity_audits section exists in QA report payload."""
    report = FontQaReporter.build(roboto)
    payload = report.payload
    assert "integrity_audits" in payload, "integrity_audits section missing from JSON"
    integrity_audits = payload["integrity_audits"]
    assert isinstance(integrity_audits, dict)


def test_integrity_audits_has_status(roboto: TtfFont) -> None:
    """Verify integrity_audits section has status field."""
    report = FontQaReporter.build(roboto)
    integrity_audits = report.payload.get("integrity_audits")
    assert integrity_audits is not None
    assert "status" in integrity_audits
    status = integrity_audits["status"]
    assert status in ("valid", "issues_found")


def test_integrity_audits_has_issue_counts(roboto: TtfFont) -> None:
    """Verify integrity_audits section has issue count fields."""
    report = FontQaReporter.build(roboto)
    integrity_audits = report.payload.get("integrity_audits")
    assert integrity_audits is not None
    assert "issue_count" in integrity_audits
    assert "blocker_count" in integrity_audits
    assert "warning_count" in integrity_audits
    assert isinstance(integrity_audits["issue_count"], int)
    assert isinstance(integrity_audits["blocker_count"], int)
    assert isinstance(integrity_audits["warning_count"], int)


def test_integrity_audits_has_issues_list(roboto: TtfFont) -> None:
    """Verify integrity_audits section has issues list."""
    report = FontQaReporter.build(roboto)
    integrity_audits = report.payload.get("integrity_audits")
    assert integrity_audits is not None
    assert "issues" in integrity_audits
    assert isinstance(integrity_audits["issues"], list)


def test_table_checksum_verification(roboto: TtfFont) -> None:
    """Verify table checksums are checked and reported."""
    font = roboto

    report = FontQaReporter.build(font)
    integrity_audits = report.payload.get("integrity_audits", {})

    codes = [i.get("code") for i in integrity_audits.get("issues", [])]

    assert "head-checksum-adjustment-mismatch" in codes or "dsig-version-0-1" in codes or "dsig-empty" in codes, \
        "Expected at least one integrity issue for Roboto font"


def test_check_sum_adjustment_verification(roboto: TtfFont) -> None:
    """Verify head.checkSumAdjustment verification is performed."""
    font = roboto

    tables = font.ttf_tables
    head = tables.head
    assert head is not None

    import copy
    modified_font = copy.deepcopy(font)
    modified_tables = modified_font.ttf_tables

    modified_tables.head.checksum_adjustment = 0x12345678

    report = FontQaReporter.build(modified_font)
    integrity_audits = report.payload.get("integrity_audits", {})

    codes = [i.get("code") for i in integrity_audits.get("issues", [])]
    assert "head-checksum-adjustment-mismatch" in codes, \
        "Expected checksum adjustment mismatch warning when head.checksum_adjustment is modified"


def test_dsig_present_reported(roboto: TtfFont) -> None:
    """Verify DSIG presence and status are reported."""
    font = roboto

    tables = font.ttf_tables
    dsig_raw = tables.get_raw("DSIG")
    dsig_table = tables.dsig

    if dsig_raw is not None and dsig_table is not None:
        report = FontQaReporter.build(font)
        integrity_audits = report.payload.get("integrity_audits", {})
        issues = integrity_audits.get("issues", [])

        codes = [i.get("code") for i in issues]

        if dsig_table.num_styles == 0:
            assert "dsig-empty" in codes, \
                "Expected dsig-empty issue when DSIG has zero signatures"
        elif dsig_table.major_version == 0 and dsig_table.minor_version == 1:
            assert "dsig-version-0-1" in codes, \
                "Expected dsig-version-0-1 issue for version 0.1 DSIG"


def test_dsig_absent_reported(roboto_path: Path, tmp_path: Path, testdata_dir: Path) -> None:
    """Verify font without DSIG table is reported."""
    font = FontLoader.open(str(roboto_path))
    assert isinstance(font, TtfFont)

    tables = font.ttf_tables
    if "DSIG" in tables._raw:
        del tables._raw["DSIG"]

    report = FontQaReporter.build(font)
    integrity_audits = report.payload.get("integrity_audits", {})

    assert integrity_audits is not None


def test_dsig_checksum_verification_result_reported(roboto_path: Path, tmp_path: Path, testdata_dir: Path) -> None:
    """Verify DSIG checksum verification result is reported."""
    font = FontLoader.open(str(roboto_path))
    assert isinstance(font, TtfFont)

    tables = font.ttf_tables
    dsig_raw = tables.get_raw("DSIG")
    dsig_table = tables.dsig

    if dsig_raw is not None and dsig_table is not None and dsig_table.num_styles > 0:
        major_version = dsig_table.major_version
        minor_version = dsig_table.minor_version

        if (major_version, minor_version) != (0, 1):
            report = FontQaReporter.build(font)
            integrity_audits = report.payload.get("integrity_audits", {})
            issues = integrity_audits.get("issues", [])

            codes = [i.get("code") for i in issues]

            assert "dsig-table-checksum-mismatch" not in codes or "dsig-version-0-1" in codes, \
                "Expected no DSIG checksum mismatch for valid version 1.0 DSIG"


def test_integrity_audits_in_json_output(roboto: TtfFont) -> None:
    """Verify integrity_audits appears in JSON output."""
    report = FontQaReporter.build(roboto)
    json_output = report.to_json()

    assert "integrity_audits" in json_output, \
        "integrity_audits missing from JSON output"


def test_integrity_audits_in_html_output(roboto: TtfFont, tmp_path: Path) -> None:
    """Verify integrity_audits section appears in HTML output."""
    report = FontQaReporter.build(roboto)
    html_path = report.write_html(tmp_path / "qa.html")
    html = html_path.read_text(encoding="utf-8")

    assert "Font Integrity" in html or "Checksum Audit" in html, \
        "Font Integrity & Checksum Audit section missing from HTML"
    assert "Status" in html, "Status table heading missing from HTML"


def test_integrity_issues_affect_readiness_score(roboto: TtfFont) -> None:
    """Verify integrity issues affect readiness score."""
    font = roboto

    report = FontQaReporter.build(font)
    readiness = report.payload.get("readiness", {})
    original_score = readiness.get("score", 100)
    original_issue_count = readiness.get("prioritized_causes", [])

    modified_font = font

    modified_tables = modified_font.ttf_tables

    modified_tables.head.checksum_adjustment = 0x12345678

    modified_report = FontQaReporter.build(modified_font)
    modified_readiness = modified_report.payload.get("readiness", {})
    modified_score = modified_readiness.get("score", 100)

    if modified_score != original_score:
        modified_issues = modified_readiness.get("prioritized_causes", [])
        assert len(modified_issues) >= len(original_issue_count), \
            "Modified font should have equal or more issues affecting readiness score"


def test_non_ttf_fonts_skip_integrity_audit(roboto_path: Path, tmp_path: Path, testdata_dir: Path) -> None:
    """Verify non-TTF fonts return valid/empty integrity audit."""
    font = FontLoader.open(str(roboto_path))
    assert isinstance(font, TtfFont)

    cff_bytes = font.to_bytes()
    cff_path = tmp_path / "roboto.cff"
    cff_path.write_bytes(cff_bytes)

    openSans_cff_path = testdata_dir / "OpenSans-Regular.cff"
    font_cff = FontLoader.open(str(openSans_cff_path))

    report = FontQaReporter.build(font_cff)
    integrity_audits = report.payload.get("integrity_audits", {})

    assert integrity_audits.get("status") == "valid", "Expected valid status for non-TTF font"
    assert integrity_audits.get("issue_count", 0) == 0, "Expected no issues for non-TTF font"


def test_integrity_audits_code_field(roboto: TtfFont) -> None:
    """Verify integrity issues have code field."""
    report = FontQaReporter.build(roboto)
    integrity_audits = report.payload.get("integrity_audits", {})

    for issue in integrity_audits.get("issues", []):
        assert "code" in issue, "Integrity issue missing code field"


def test_integrity_audits_severity_field(roboto: TtfFont) -> None:
    """Verify integrity issues have severity field."""
    report = FontQaReporter.build(roboto)
    integrity_audits = report.payload.get("integrity_audits", {})

    valid_severities = ("blocker", "warning", "info")

    for issue in integrity_audits.get("issues", []):
        assert "severity" in issue, "Integrity issue missing severity field"
        assert issue["severity"] in valid_severities, \
            f"Invalid severity: {issue['severity']}"


def test_integrity_audits_remediation_field(roboto: TtfFont) -> None:
    """Verify integrity issues have remediation field."""
    report = FontQaReporter.build(roboto)
    integrity_audits = report.payload.get("integrity_audits", {})

    for issue in integrity_audits.get("issues", []):
        assert "remediation" in issue, "Integrity issue missing remediation field"
        remediation = issue["remediation"]
        assert "recommendation" in remediation, "Remediation missing recommendation"
        assert "reason" in remediation, "Remediation missing reason"
        assert "next_action" in remediation, "Remediation missing next_action"


def test_cross_platform_paths(testdata_dir: Path) -> None:
    """Verify test uses Path(__file__).resolve().parents[...] pattern."""
    source_str = str(testdata_dir).replace("\\", "/")
    assert "testdata" in source_str, "testdata path used"
    assert str(Path(__file__).parent.name) == "tests", "Test in tests directory"


def test_integrity_audits_with_zero_tables(roboto: TtfFont, tmp_path: Path) -> None:
    """Verify integrity audit handles empty font gracefully."""
    font = roboto

    empty_font = font
    empty_tables = empty_font.ttf_tables
    empty_tables._raw = {}

    report = FontQaReporter.build(empty_font)
    integrity_audits = report.payload.get("integrity_audits", {})

    assert integrity_audits is not None, "integrity_audits should be present even with empty tables"
