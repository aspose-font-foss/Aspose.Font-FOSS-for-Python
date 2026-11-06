"""Tests for Web Font Optimizer decision report (FONT-277)."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from aspose_font import FontLoader
from aspose_font.web import WebFontOptimizer


@pytest.fixture
def variable_font_path() -> Path:
    """Path to variable font fixture."""
    return Path(__file__).resolve().parents[1] / "testdata" / "Roboto-VariableFont_wdth,wght.ttf"


@pytest.fixture
def static_font_path() -> Path:
    """Path to static font fixture."""
    return Path(__file__).resolve().parents[1] / "testdata" / "OpenSans-Regular.cff"


class TestWebFontOptimizerDecisionReport:
    """Tests for decision report generation in WebFontOptimizer."""

    def test_decision_report_live_mode_variable_font(self, variable_font_path: Path) -> None:
        """Decision report for variable font with live mode should be 'live'."""
        font = FontLoader.open(variable_font_path)
        package = WebFontOptimizer.build(font, variable_mode="live", decision_report=True)

        assert package.decision_report is not None
        assert package.decision_report.mode == "live"
        assert "Variable font" in package.decision_report.reason
        assert "supports variable axes" in package.decision_report.reason.lower()

        # Check package manifest contains decision_report
        manifest_dr = package.manifest.get("decision_report")
        assert manifest_dr is not None
        assert manifest_dr["mode"] == "live"
        assert manifest_dr["decision"] == "live"

    def test_decision_report_static_mode_variable_font(self, variable_font_path: Path) -> None:
        """Decision report for variable font with static mode should be 'static'."""
        font = FontLoader.open(variable_font_path)
        package = WebFontOptimizer.build(font, variable_mode="static", decision_report=True)

        assert package.decision_report is not None
        assert package.decision_report.mode == "static"
        assert "static instance" in package.decision_report.reason.lower()

        manifest_dr = package.manifest.get("decision_report")
        assert manifest_dr is not None
        assert manifest_dr["mode"] == "static"
        assert manifest_dr["decision"] == "static"

    def test_decision_report_static_fallback_static_font(self, static_font_path: Path) -> None:
        """Decision report for static font should be 'static_fallback'."""
        font = FontLoader.open(static_font_path)
        package = WebFontOptimizer.build(font, variable_mode="auto", decision_report=True)

        assert package.decision_report is not None
        # Static fonts should get "static_fallback" mode
        assert package.decision_report.mode == "static_fallback"
        assert "not variable" in package.decision_report.reason.lower()

        manifest_dr = package.manifest.get("decision_report")
        assert manifest_dr is not None
        assert manifest_dr["mode"] == "static_fallback"
        assert manifest_dr["decision"] == "static_fallback"

    def test_decision_report_json_serialization(self, variable_font_path: Path) -> None:
        """Decision report should be JSON-serializable in package manifest."""
        font = FontLoader.open(variable_font_path)
        package = WebFontOptimizer.build(font, variable_mode="live", decision_report=True)

        # Verify manifest can be serialized
        manifest_json = json.dumps(package.manifest, indent=2)
        manifest = json.loads(manifest_json)

        assert "decision_report" in manifest
        assert manifest["decision_report"]["mode"] == "live"
        assert "reasons" in manifest["decision_report"]
        assert isinstance(manifest["decision_report"]["reasons"], list)

    def test_decision_report_missing_when_disabled(self, variable_font_path: Path) -> None:
        """Decision report should be None when decision_report=False."""
        font = FontLoader.open(variable_font_path)
        package = WebFontOptimizer.build(font, variable_mode="live", decision_report=False)

        assert package.decision_report is None
        assert package.manifest.get("decision_report") is None

    def test_cli_decision_report_custom_path(self, variable_font_path: Path, tmp_path: Path) -> None:
        """CLI --decision-report <path> should write decision report to custom location."""
        import subprocess

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        custom_report_path = "custom-decision.json"

        result = subprocess.run(
            [sys.executable, "-m", "aspose_font.cli", "web-optimize", str(variable_font_path),
             str(output_dir),
             "--decision-report", custom_report_path,
             "--preset", "latin"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0

        custom_full_path = output_dir / custom_report_path
        assert custom_full_path.exists()

        data = json.loads(custom_full_path.read_text(encoding="utf-8"))
        assert "mode" in data
        assert "decision" in data
        assert "reasons" in data
        assert isinstance(data["reasons"], list)

        default_path = output_dir / "decision-report.json"
        assert not default_path.exists()

    def test_export_mode_decision_in_manifest(self, variable_font_path: Path) -> None:
        """Top-level export_mode_decision field present in optimizer manifest."""
        font = FontLoader.open(variable_font_path)
        package = WebFontOptimizer.build(font, variable_mode="live", decision_report=True)

        assert "export_mode_decision" in package.manifest
        assert package.manifest["export_mode_decision"] == "live"

    def test_cli_verbose_outputs_decision_report(
        self, variable_font_path: Path, tmp_path: Path
    ) -> None:
        """CLI --verbose flag triggers decision report output to stdout."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "aspose_font.cli",
                "web-optimize",
                str(variable_font_path),
                str(output_dir),
                "--preset",
                "latin",
                "--verbose",
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert "Export mode decision:" in result.stdout
        assert "Decision summary:" in result.stdout
        assert "Remediation suggestions:" in result.stdout
        assert "Decision reason:" in result.stdout

        result_silent = subprocess.run(
            [
                sys.executable,
                "-m",
                "aspose_font.cli",
                "web-optimize",
                str(variable_font_path),
                str(output_dir / "silent"),
                "--preset",
                "latin",
            ],
            capture_output=True,
            text=True,
        )

        assert result_silent.returncode == 0
        assert "Export mode decision:" not in result_silent.stdout
        assert "Decision summary:" not in result_silent.stdout
