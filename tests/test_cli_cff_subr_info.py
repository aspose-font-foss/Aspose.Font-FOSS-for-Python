"""Tests for CLI cff-subr-info command (FONT-521)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

CLI = [sys.executable, "-m", "aspose_font.cli"]


def run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        CLI + list(args),
        capture_output=True,
        text=True,
    )


class TestCffSubrInfoCommand:
    """Tests for the cff-subr-info CLI command."""

    def test_cli_cff_subr_info_prints_summary(self, opensans_cff_path: Path) -> None:
        """Normal CFF font prints expected summary lines."""
        result = run("cff-subr-info", str(opensans_cff_path))

        assert result.returncode == 0
        assert "Font:" in result.stdout
        assert "Format:" in result.stdout
        assert "Global Subroutines:" in result.stdout
        assert "Local Subroutines:" in result.stdout
        assert "Maximum call depth:" in result.stdout

    def test_cli_cff_subr_info_json_output(
        self, opensans_cff_path: Path, tmp_path: Path
    ) -> None:
        """JSON output creates file with required keys."""
        json_path = tmp_path / "output.json"

        result = run(
            "cff-subr-info",
            "--json-output",
            str(json_path),
            str(opensans_cff_path),
        )

        assert result.returncode == 0
        assert json_path.exists()

        with open(json_path) as f:
            data = json.load(f)

        assert "font_name" in data
        assert "global_subrs" in data
        assert "local_subrs" in data
        assert "max_nesting_depth" in data

    def test_cli_cff_subr_info_saves_message(
        self, opensans_cff_path: Path, tmp_path: Path
    ) -> None:
        """JSON output prints save confirmation."""
        json_path = tmp_path / "output.json"

        result = run(
            "cff-subr-info",
            "--json-output",
            str(json_path),
            str(opensans_cff_path),
        )

        assert result.returncode == 0
        assert "Saved:" in result.stdout

    def test_cli_cff_subr_info_ttf_font_no_cff(self, roboto_path: Path) -> None:
        """TTF font without CFF prints notice and exits 0."""
        result = run("cff-subr-info", str(roboto_path))

        assert result.returncode == 0
        assert "CFF/CFF2 data:" in result.stdout
        assert "Not present" in result.stdout

    def test_cli_cff_subr_info_help(self) -> None:
        """CLI help displays command description."""
        result = run("cff-subr-info", "--help")

        assert result.returncode == 0
        assert "CFF/CFF2 subroutine" in result.stdout.lower() or "subroutine" in result.stdout.lower()
