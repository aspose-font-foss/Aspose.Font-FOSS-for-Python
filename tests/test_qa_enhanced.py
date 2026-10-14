"""Tests for enhanced Font QA Report with compatibility and size artifacts."""

from __future__ import annotations

import json
from pathlib import Path

from aspose_font import FontQaReporter
from aspose_font.ttf.font import TtfFont


def test_font_qa_report_includes_compatibility_when_requested(roboto: TtfFont) -> None:
    """Verify compatibility field is included in payload when include_compatibility=True."""
    report = FontQaReporter.build(roboto, presets=("latin",), include_compatibility=True)
    payload = report.to_dict()

    assert "compatibility" in payload
    assert isinstance(payload["compatibility"], dict)
    assert payload["compatibility"]["before_label"] == "Original"
    assert payload["compatibility"]["after_label"] == "Original"
    assert "issues" in payload["compatibility"]
    assert isinstance(payload["compatibility"]["issues"], list)


def test_font_qa_report_excludes_compatibility_by_default(roboto: TtfFont) -> None:
    """Verify compatibility field is None when include_compatibility=False (default)."""
    report = FontQaReporter.build(roboto, presets=("latin",))
    payload = report.to_dict()

    assert "compatibility" in payload
    assert payload["compatibility"] is None


def test_font_qa_report_includes_size_artifacts_with_source(roboto: TtfFont, tmp_path: Path) -> None:
    """Verify size_artifacts is included when source_path is provided."""
    font_path = tmp_path / "roboto_test.ttf"
    font_bytes = roboto.to_bytes()
    font_path.write_bytes(font_bytes)

    report = FontQaReporter.build(roboto, source_path=font_path)
    payload = report.to_dict()

    assert "size_artifacts" in payload
    assert isinstance(payload["size_artifacts"], dict)
    assert "current_size_bytes" in payload["size_artifacts"]
    assert "source_size_bytes" in payload["size_artifacts"]
    assert "size_delta_bytes" in payload["size_artifacts"]
    assert "size_delta_percent" in payload["size_artifacts"]

    assert isinstance(payload["size_artifacts"]["current_size_bytes"], int)
    assert payload["size_artifacts"]["current_size_bytes"] > 0
    assert payload["size_artifacts"]["source_size_bytes"] == payload["size_artifacts"]["current_size_bytes"]


def test_font_qa_report_excludes_size_artifacts_without_source(roboto: TtfFont) -> None:
    """Verify size_artifacts is None when source_path is not provided."""
    report = FontQaReporter.build(roboto)
    payload = report.to_dict()

    assert "size_artifacts" in payload
    assert payload["size_artifacts"] is None


def test_font_qa_package_writes_compatibility_file(roboto: TtfFont, tmp_path: Path) -> None:
    """Verify compatibility.json is written to package when include_compatibility=True."""
    package = FontQaReporter.build_package(
        roboto,
        tmp_path / "qa-package",
        presets=("latin",),
        include_compatibility=True,
    )

    compatibility_path = package.directory / "compatibility.json"
    assert compatibility_path.is_file()

    content = json.loads(compatibility_path.read_text(encoding="utf-8"))
    assert content["before_label"] == "Original"
    assert "issues" in content


def test_font_qa_package_manifest_contains_size_fields(roboto: TtfFont, tmp_path: Path) -> None:
    """Verify qa-report.json manifest contains size_delta_bytes and size_delta_percent."""
    font_path = tmp_path / "roboto_size_test.ttf"
    font_bytes = roboto.to_bytes()
    font_path.write_bytes(font_bytes)

    package = FontQaReporter.build_package(
        roboto,
        tmp_path / "qa-package",
        source_path=font_path,
    )

    payload = json.loads(package.json_path.read_text(encoding="utf-8"))
    size_artifacts = payload.get("size_artifacts")

    assert size_artifacts is not None
    assert "size_delta_bytes" in size_artifacts
    assert "size_delta_percent" in size_artifacts
    assert isinstance(size_artifacts["size_delta_bytes"], int)
    assert isinstance(size_artifacts["size_delta_percent"], (int, float))


def test_font_qa_package_manifest_with_both_artifacts(roboto: TtfFont, tmp_path: Path) -> None:
    """Verify all artifacts are present when both options are enabled."""
    font_path = tmp_path / "roboto_both_test.ttf"
    font_bytes = roboto.to_bytes()
    font_path.write_bytes(font_bytes)

    package = FontQaReporter.build_package(
        roboto,
        tmp_path / "qa-package",
        presets=("latin",),
        include_compatibility=True,
        source_path=font_path,
    )

    payload = json.loads(package.json_path.read_text(encoding="utf-8"))

    assert payload.get("compatibility") is not None
    assert payload.get("size_artifacts") is not None

    artifacts = payload.get("artifacts", [])
    compatibility_artifact = next((a for a in artifacts if a.get("path") == "compatibility.json"), None)
    assert compatibility_artifact is not None
    assert compatibility_artifact.get("kind") == "compatibility"
    assert compatibility_artifact.get("label") == "Compatibility report"
    assert compatibility_artifact.get("media_type") == "application/json"


def test_font_qa_report_backward_compatibility(roboto: TtfFont) -> None:
    """Verify existing API still works without new parameters."""
    report = FontQaReporter.build(roboto, presets=("latin",), text="QA")
    payload = report.to_dict()

    assert payload["kind"] == "font_qa_report"
    assert payload["schema_version"] == 1
    assert "identity" in payload
    assert "metrics" in payload
    assert "variable" in payload
    assert "coverage" in payload
    assert "warnings" in payload
    assert "readiness" in payload
    assert "next_actions" in payload
    assert "compatibility" in payload
    assert "size_artifacts" in payload
