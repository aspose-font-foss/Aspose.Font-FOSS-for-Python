"""Tests for Web Font Optimizer decision report functionality."""

import json
import subprocess
import sys
from pathlib import Path

from aspose_font import FontLoader
from aspose_font.web import WebFontOptimizer

_TESTDATA_DIR = Path(__file__).resolve().parents[1] / "testdata"


class TestWebFontOptimizerDecisionReport:
    def test_decide_output_returns_dict(self):
        font = FontLoader.open(_TESTDATA_DIR / "Roboto-VariableFont_wdth,wght.ttf")
        result = WebFontOptimizer.decide_output(font)
        assert isinstance(result, dict)
        assert "decision" in result
        assert "reasons" in result
        assert isinstance(result["reasons"], list)
        assert result["decision"] in ("live", "static", "static_fallback")

    def test_decide_output_variable_font_live_mode(self):
        font = FontLoader.open(_TESTDATA_DIR / "Roboto-VariableFont_wdth,wght.ttf")
        result = WebFontOptimizer.decide_output(font, variable_mode="live")
        assert result["decision"] == "live"
        assert len(result["reasons"]) > 0

    def test_decide_output_variable_font_auto_mode(self):
        font = FontLoader.open(_TESTDATA_DIR / "Roboto-VariableFont_wdth,wght.ttf")
        result = WebFontOptimizer.decide_output(font, variable_mode="auto")
        assert result["decision"] == "live"
        assert len(result["reasons"]) > 0

    def test_decide_output_static_font(self):
        font = FontLoader.open(_TESTDATA_DIR / "Arial.pfa")
        result = WebFontOptimizer.decide_output(font)
        assert result["decision"] in ("static", "static_fallback")

    def test_cli_command_variable_font(self):
        font_path = _TESTDATA_DIR / "Roboto-VariableFont_wdth,wght.ttf"
        result = subprocess.run(
            [sys.executable, "-m", "aspose_font.cli", "decision-report", str(font_path)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        report = json.loads(result.stdout)
        assert "decision" in report
        assert "reasons" in report

    def test_cli_command_static_font(self):
        font_path = _TESTDATA_DIR / "Arial.pfa"
        result = subprocess.run(
            [sys.executable, "-m", "aspose_font.cli", "decision-report", str(font_path)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        report = json.loads(result.stdout)
        assert "decision" in report
        assert "reasons" in report

    def test_cli_command_with_explicit_variable_mode(self):
        font_path = _TESTDATA_DIR / "Roboto-VariableFont_wdth,wght.ttf"
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "aspose_font.cli",
                "decision-report",
                "--variable-mode",
                "live",
                str(font_path),
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        report = json.loads(result.stdout)
        assert report["decision"] == "live"
