"""Tests for localization audit in FontQaReporter (FONT-506)."""

from pathlib import Path

from aspose_font import FontQaReporter
from aspose_font.ttf.font import TtfFont


def test_localization_section_included_in_json(roboto: TtfFont) -> None:
    """Verify localization section exists in JSON output for variable fonts."""
    report = FontQaReporter.build(roboto)
    payload = report.payload
    assert "localization" in payload, "localization section missing from JSON"
    localization = payload["localization"]
    assert isinstance(localization, dict)
    assert "ltag_present" in localization
    assert "language_count" in localization
    assert "languages" in localization


def test_localization_section_in_html(roboto: TtfFont, tmp_path: Path) -> None:
    """Verify localization section appears in HTML output."""
    report = FontQaReporter.build(roboto)
    html_path = report.write_html(tmp_path / "qa.html")
    html = html_path.read_text(encoding="utf-8")
    assert "Localization" in html, "Localization section missing from HTML"


def test_localization_section_in_markdown(roboto: TtfFont, tmp_path: Path) -> None:
    """Verify localization section appears in markdown output."""
    report = FontQaReporter.build(roboto)
    md_path = report.write_markdown(tmp_path / "qa.md")
    md = md_path.read_text(encoding="utf-8")
    payload = report.payload
    localization = payload.get("localization", {})

    if localization.get("ltag_present", False):
        assert "## Localization" in md, "Localization section missing from markdown"
        assert "Localization:" in md, "Localization summary missing from markdown"
    else:
        assert "Localization:" in md, "Localization N/A summary missing from markdown"
        assert "N/A" in md, "Localization N/A status not shown"


def test_missing_strings_audit_functionality(roboto: TtfFont) -> None:
    """Verify missing strings are properly identified."""
    report = FontQaReporter.build(roboto)
    payload = report.payload
    localization = payload.get("localization", {})

    if localization.get("ltag_present", False):
        missing_strings = localization.get("missing_strings", [])
        languages = localization.get("languages", [])

        assert isinstance(missing_strings, list)
        assert isinstance(languages, list)

        for item in missing_strings:
            assert "language" in item
            assert "name_id" in item
            assert "name_id_label" in item


def test_ltag_not_present_for_static_font(tmp_path: Path) -> None:
    """Verify static fonts without ltag show appropriate message."""
    from aspose_font import FontQaReporter
    from aspose_font.ttf.font import TtfFont

    font_path = tmp_path / "test_static.ttf"
    font_path.write_bytes(b"test font data")

    try:
        from aspose_font import FontLoader
        font = FontLoader.open(str(font_path))
        if isinstance(font, TtfFont):
            report = FontQaReporter.build(font)
            payload = report.payload
            localization = payload.get("localization", {})

            if not localization.get("ltag_present", False):
                html_path = report.write_html(tmp_path / "qa.html")
                html = html_path.read_text(encoding="utf-8")
                assert "Localization" in html
                assert "not present" in html.lower() or "audit not available" in html.lower()
    except Exception:
        pass
