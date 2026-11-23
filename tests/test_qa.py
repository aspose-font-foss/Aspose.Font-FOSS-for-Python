"""Tests for product-shaped font QA reports."""

from __future__ import annotations

import json

from aspose_font import FontQaPackage, FontQaReport, FontQaReporter
from aspose_font.ttf.font import TtfFont

_PACKAGE_JSON_NAME = "qa-report.json"
_PACKAGE_HTML_NAME = "qa-report.html"
_ASSETS_DIR_NAME = "assets"


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
    assert package.preview_path.name == "preview_main.png"
    assert package.preview_path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")

    payload = json.loads(package.json_path.read_text(encoding="utf-8"))
    artifacts = payload["artifacts"]
    assert [item["kind"] for item in artifacts] == ["json", "html", "preview", "preview", "preview", "preview"]
    assert artifacts[2]["path"] == "assets/preview_main.png"
    assert artifacts[2]["media_type"] == "image/png"

    html = package.html_path.read_text(encoding="utf-8")
    assert "<h2>Artifacts</h2>" in html
    assert 'src="assets/preview_main.png"' in html
    assert 'href="qa-report.json"' in html


def test_qa_severity_scoring(roboto: TtfFont) -> None:
    report = FontQaReporter.build(roboto, presets=("latin",), text="QA")
    payload = report.to_dict()
    warnings = payload.get("warnings", [])

    assert isinstance(warnings, list)
    for warning in warnings:
        assert isinstance(warning, dict)
        assert "severity" in warning
        assert warning["severity"] in ("blocker", "warning", "info")


def test_qa_issue_categorization(roboto: TtfFont) -> None:
    report = FontQaReporter.build(roboto, presets=("latin",), text="QA")
    payload = report.to_dict()
    warnings = payload.get("warnings", [])

    warning_codes = {w.get("code") for w in warnings if isinstance(w, dict)}

    assert "missing-requested-codepoints" in warning_codes or "coverage-not-requested" in warning_codes
    for w in warnings:
        if isinstance(w, dict):
            code = w.get("code")
            severity = w.get("severity")
            if code == "missing-requested-codepoints":
                assert severity in ("warning", "blocker")
            elif code == "coverage-not-requested":
                assert severity == "info"


def test_qa_remediation_engine(roboto: TtfFont) -> None:
    report = FontQaReporter.build(roboto, presets=("latin",), text="QA")
    payload = report.to_dict()
    warnings = payload.get("warnings", [])

    for warning in warnings:
        if isinstance(warning, dict):
            remediation = warning.get("remediation")
            assert isinstance(remediation, dict)
            assert "recommendation" in remediation
            assert "reason" in remediation
            assert "next_action" in remediation


def test_qa_readiness_extension(roboto: TtfFont) -> None:
    report = FontQaReporter.build(roboto, presets=("latin",), text="QA")
    payload = report.to_dict()
    readiness = payload.get("readiness")

    assert isinstance(readiness, dict)
    assert "score" in readiness
    assert "status" in readiness
    assert "prioritized_causes" in readiness

    assert isinstance(readiness["score"], int)
    assert 0 <= readiness["score"] <= 100
    assert readiness["status"] in ("ready", "warning", "caution", "blocked")

    causes = readiness["prioritized_causes"]
    assert isinstance(causes, list)
    for cause in causes:
        assert isinstance(cause, dict)
        assert "code" in cause
        assert "severity" in cause
        assert "weight" in cause


def test_qa_cli_severity_fields(roboto: TtfFont, tmp_path) -> None:
    package = FontQaReporter.build_package(
        roboto,
        tmp_path / "qa-cli-test",
        presets=("latin",),
        text="QA",
    )

    payload = json.loads(package.json_path.read_text(encoding="utf-8"))

    assert "readiness" in payload
    assert "warnings" in payload

    for warning in payload["warnings"]:
        assert "severity" in warning
        assert "remediation" in warning


def test_qa_composite_package_structure(roboto: TtfFont, tmp_path) -> None:
    package = FontQaReporter.build_package(
        roboto,
        tmp_path / "qa-composite-package",
        presets=("latin",),
        text="QA",
    )

    assert package.json_path.is_file()
    assert package.html_path.is_file()

    assets_dir = package.directory / _ASSETS_DIR_NAME
    assert assets_dir.is_dir()

    main_preview = assets_dir / "preview_main.png"
    assert main_preview.is_file()
    assert main_preview.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")

    payload = json.loads(package.json_path.read_text(encoding="utf-8"))
    artifacts = payload.get("artifacts", [])
    assert isinstance(artifacts, list)

    artifact_paths = [a.get("path") for a in artifacts]
    assert any("assets/preview_main.png" in p for p in artifact_paths)
    assert any("assets/axes_chart.png" in p for p in artifact_paths)
    assert any("assets/coverage_chart.png" in p for p in artifact_paths)


def test_qa_embedded_previews(roboto: TtfFont, tmp_path) -> None:
    package = FontQaReporter.build_package(
        roboto,
        tmp_path / "qa-embedded-previews",
        presets=("latin",),
        text="QA",
    )

    assets_dir = package.directory / _ASSETS_DIR_NAME

    expected_previews = [
        "preview_main.png",
        "axes_chart.png",
        "coverage_chart.png",
    ]

    for filename in expected_previews:
        preview_path = assets_dir / filename
        assert preview_path.is_file(), f"Missing preview: {filename}"
        bytes_data = preview_path.read_bytes()
        assert len(bytes_data) > 0, f"Empty preview file: {filename}"
        assert bytes_data.startswith(b"\x89PNG\r\n\x1a\n"), f"Not a valid PNG: {filename}"


def test_qa_self_contained_html(roboto: TtfFont, tmp_path) -> None:
    package = FontQaReporter.build_package(
        roboto,
        tmp_path / "qa-self-contained",
        presets=("latin",),
        text="QA",
    )

    html_content = package.html_path.read_text(encoding="utf-8")

    assert "assets/" in html_content, "HTML should reference assets directory"
    assert "<img" in html_content, "HTML should contain image tags"


def test_qa_manifest_artifacts(roboto: TtfFont, tmp_path) -> None:
    package = FontQaReporter.build_package(
        roboto,
        tmp_path / "qa-manifest",
        presets=("latin",),
        text="QA",
    )

    payload = json.loads(package.json_path.read_text(encoding="utf-8"))
    artifacts = payload.get("artifacts", [])

    assert isinstance(artifacts, list)
    assert len(artifacts) >= 3, "At minimum: json, html, main preview"

    for artifact in artifacts:
        assert isinstance(artifact, dict)
        assert "kind" in artifact
        assert "label" in artifact
        assert "path" in artifact
        assert "media_type" in artifact

    preview_artifacts = [a for a in artifacts if a.get("kind") == "preview"]
    assert len(preview_artifacts) >= 1, "At least one preview artifact expected"
    for preview in preview_artifacts:
        assert preview["path"].startswith("assets/"), "All preview paths should be in assets/"


def test_qa_cli_composite_package(roboto: TtfFont, tmp_path) -> None:
    import subprocess
    import sys
    from pathlib import Path

    output_dir = tmp_path / "cli-qa-package"
    package_output = output_dir / "package"
    repo_root = Path(__file__).resolve().parents[1]
    font_path = repo_root / "testdata" / "Roboto-VariableFont_wdth,wght.ttf"

    result = subprocess.run(
        [
            sys.executable, "-m", "aspose_font.cli",
            "qa-report",
            str(font_path),
            "--preset", "latin",
            "--text", "QA",
            "--package-output", str(package_output),
        ],
        capture_output=True,
        text=True,
        cwd=str(repo_root),
    )

    assert result.returncode == 0, f"CLI failed: {result.stderr}"

    assert (package_output / _PACKAGE_JSON_NAME).is_file()
    assert (package_output / _PACKAGE_HTML_NAME).is_file()
    assert (package_output / "assets" / "preview_main.png").is_file()
    assert (package_output / "assets" / "axes_chart.png").is_file()
    assert (package_output / "assets" / "coverage_chart.png").is_file()


def test_font_qa_report_decision_analytics(roboto: TtfFont, tmp_path) -> None:
    report_no_decision = FontQaReporter.build(roboto, presets=("latin",))
    payload_no_decision = report_no_decision.to_dict()
    assert "decision" not in payload_no_decision or payload_no_decision["decision"] is None

    report_with_decision = FontQaReporter.build(roboto, presets=("latin",), include_decision=True)
    payload_with_decision = report_with_decision.to_dict()
    assert "decision" in payload_with_decision
    assert payload_with_decision["decision"] is not None
    decision = payload_with_decision["decision"]
    assert decision.get("recommended_action") in ("live", "static", "static_fallback")
    assert isinstance(decision.get("rationale"), list)
    assert len(decision["rationale"]) > 0

    package = FontQaReporter.build_package(
        roboto,
        tmp_path / "qa-decision-test",
        presets=("latin",),
        text="QA",
        include_decision=True,
    )
    payload = json.loads(package.json_path.read_text(encoding="utf-8"))
    assert "decision" in payload
    assert payload["decision"]["recommended_action"] == "live"
    assert len(payload["decision"]["rationale"]) > 0


def test_font_qa_report_build_full_report(roboto: TtfFont, tmp_path) -> None:
    package = FontQaReporter.build_full_report(
        roboto,
        tmp_path / "qa-full-report",
        source_label="Roboto",
        presets=("latin",),
        text="QA",
        preview_text="Roboto Full QA",
        preview_instance_name="Bold",
        include_decision=True,
    )

    assert isinstance(package, FontQaPackage)
    assert package.json_path.name == "qa-report.json"
    assert package.html_path.name == "qa-report.html"
    assert package.preview_path.name == "preview_main.png"
    assert package.preview_path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")

    assert package.json_path.is_file()
    assert package.html_path.is_file()

    payload = json.loads(package.json_path.read_text(encoding="utf-8"))
    artifacts = payload.get("artifacts", [])

    artifact_kinds = [item["kind"] for item in artifacts]
    assert "json" in artifact_kinds
    assert "html" in artifact_kinds

    html = package.html_path.read_text(encoding="utf-8")
    assert "<h2>Artifacts</h2>" in html
    assert 'src="assets/preview_main.png"' in html
    assert 'href="qa-report.json"' in html
    assert 'href="qa-report.html"' in html


def test_font_qa_report_cli_full_report(roboto: TtfFont, tmp_path) -> None:
    import subprocess
    import sys
    from pathlib import Path

    output_dir = tmp_path / "cli-qa-full-report"
    repo_root = Path(__file__).resolve().parents[1]
    font_path = repo_root / "testdata" / "Roboto-VariableFont_wdth,wght.ttf"

    result = subprocess.run(
        [
            sys.executable, "-m", "aspose_font.cli",
            "qa-full-report",
            str(font_path),
            "--output-dir", str(output_dir),
            "--preset", "latin",
            "--text", "QA",
            "--include-decision",
        ],
        capture_output=True,
        text=True,
        cwd=str(repo_root),
    )

    assert result.returncode == 0, f"CLI failed: {result.stderr}"

    assert (output_dir / _PACKAGE_JSON_NAME).is_file()
    assert (output_dir / _PACKAGE_HTML_NAME).is_file()
    assert (output_dir / "assets" / "preview_main.png").is_file()

    payload = json.loads((output_dir / _PACKAGE_JSON_NAME).read_text(encoding="utf-8"))
    assert "decision" in payload
    assert payload["decision"]["recommended_action"] == "live"
