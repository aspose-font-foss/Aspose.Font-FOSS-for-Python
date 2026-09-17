"""Tests for product-shaped font QA reports."""

from __future__ import annotations

import json

from aspose_font import FontQaPackage, FontQaReport, FontQaReporter
from aspose_font.ttf.font import TtfFont


def test_font_qa_report_builds_variable_coverage_summary(roboto: TtfFont) -> None:
    report = FontQaReporter.build(
        roboto,
        source_label="Roboto",
        presets=("latin",),
        text="QA",
        codepoints=(0x10FFFF,),
        preferred_languages=("en",),
    )

    payload = report.to_dict()
    assert payload["kind"] == "font_qa_report"
    assert payload["schema_version"] == 1
    assert payload["identity"]["font_family"] == "Roboto"
    assert payload["identity"]["is_variable"] is True
    assert payload["metrics"]["units_per_em"] > 0
    assert payload["variable"]["axis_count"] == 2
    assert payload["variable"]["named_instance_count"] == 18
    assert payload["coverage"]["requested_presets"] == ["latin"]
    assert payload["coverage"]["missing_count"] >= 1
    assert any(item["code"] == "missing-requested-codepoints" for item in payload["warnings"])
    assert any(item["code"] == "build-web-package" for item in payload["next_actions"])


def test_font_qa_report_writes_json_and_html(roboto: TtfFont, tmp_path) -> None:
    report = FontQaReporter.build(roboto, presets=("latin",), text="QA")

    json_path = report.write_json(tmp_path / "qa.json")
    html_path = report.write_html(tmp_path / "qa.html")

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    html = html_path.read_text(encoding="utf-8")
    assert payload["kind"] == "font_qa_report"
    assert payload["schema_version"] == 1
    assert "<!doctype html>" in html
    assert "Font QA Report" in html
    assert "Warnings" in html
    assert "Next Actions" in html
    assert "Coverage" in html


def test_font_qa_report_without_coverage_prompts_next_action(roboto: TtfFont) -> None:
    report = FontQaReporter.build(roboto)
    payload = report.to_dict()

    assert payload["coverage"] is None
    assert any(item["code"] == "coverage-not-requested" for item in payload["warnings"])
    assert any(item["code"] == "add-coverage-inputs" for item in payload["next_actions"])
    assert isinstance(report, FontQaReport)


def test_font_qa_report_package_writes_preview_artifacts(roboto: TtfFont, tmp_path) -> None:
    package = FontQaReporter.build_package(
        roboto,
        tmp_path / "qa-package",
        source_label="Roboto",
        presets=("latin",),
        text="QA",
        preview_text="Roboto QA",
        preview_instance_name="Bold",
    )

    assert isinstance(package, FontQaPackage)
    assert package.json_path.name == "qa-report.json"
    assert package.html_path.name == "qa-report.html"
    assert package.preview_path.name == "preview.png"
    assert package.preview_path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")

    payload = json.loads(package.json_path.read_text(encoding="utf-8"))
    artifacts = payload["artifacts"]
    assert [item["kind"] for item in artifacts] == ["json", "html", "preview"]
    assert artifacts[2]["path"] == "preview.png"
    assert artifacts[2]["media_type"] == "image/png"

    html = package.html_path.read_text(encoding="utf-8")
    assert "<h2>Artifacts</h2>" in html
    assert 'src="preview.png"' in html
    assert 'href="qa-report.json"' in html
