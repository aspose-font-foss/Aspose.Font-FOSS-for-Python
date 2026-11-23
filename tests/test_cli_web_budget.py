"""Tests for CLI web-budget subcommand (FONT-556)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

CLI = [sys.executable, "-m", "aspose_font.cli"]

ROBOTO = str(Path(__file__).resolve().parents[1] / "testdata" / "Roboto-VariableFont_wdth,wght.ttf")


def run(*args: str) -> subprocess.CompletedProcess:
    """Run CLI command and return result."""
    return subprocess.run(
        CLI + list(args),
        capture_output=True,
        text=True,
    )


def test_web_budget_displays_per_file_status() -> None:
    """Console output shows pass/warning/exceeded status per font file."""
    result = run("web-budget", ROBOTO)

    assert result.returncode == 0
    assert "Font Performance Budget Report" in result.stdout
    assert "[PASS]" in result.stdout or "[WARN]" in result.stdout or "[FAIL]" in result.stdout
    assert "Per-File Status:" in result.stdout


def test_web_budget_custom_max_kb() -> None:
    """--max-kb flag customizes budget threshold."""
    result = run("web-budget", ROBOTO, "--max-kb", "50")

    assert result.returncode == 0
    assert "Budget per file: 50.0 KB" in result.stdout


def test_web_budget_generate_html_stdout() -> None:
    """--generate-html writes HTML preload tags to stdout."""
    result = run("web-budget", ROBOTO, "--generate-html")

    assert result.returncode == 0
    assert '<link rel="preload"' in result.stdout
    assert 'as="font"' in result.stdout
    assert 'crossorigin="anonymous"' in result.stdout


def test_web_budget_generate_html_file(tmp_path: Path) -> None:
    """--generate-html PATH writes HTML to file."""
    html_path = str(tmp_path / "preload.html")
    result = run("web-budget", ROBOTO, "--generate-html", html_path)

    assert result.returncode == 0
    assert f"HTML preload tags saved: {html_path}" in result.stdout
    assert (tmp_path / "preload.html").exists()
    content = (tmp_path / "preload.html").read_text(encoding="utf-8")
    assert '<link rel="preload"' in content


def test_web_budget_json_output_to_stdout() -> None:
    """--json outputs budget summary as JSON to stdout."""
    result = run("web-budget", ROBOTO, "--json")

    assert result.returncode == 0
    import json
    output = json.loads(result.stdout)
    assert "total_size_bytes" in output
    assert "total_budget_bytes" in output
    assert "status" in output
    assert "fonts" in output
    assert len(output["fonts"]) > 0
    assert "filename" in output["fonts"][0]
    assert "size_bytes" in output["fonts"][0]
    assert "status" in output["fonts"][0]


def test_web_budget_json_output_to_file(tmp_path: Path) -> None:
    """--json-output writes JSON to specified file."""
    json_path = str(tmp_path / "budget.json")
    result = run("web-budget", ROBOTO, "--json-output", json_path)

    assert result.returncode == 0
    assert f"Saved: {json_path}" in result.stdout
    assert (tmp_path / "budget.json").exists()

    import json
    content = json.loads((tmp_path / "budget.json").read_text(encoding="utf-8"))
    assert "total_size_bytes" in content


def test_web_budget_multiple_fonts() -> None:
    """Multiple font files are evaluated correctly."""
    result = run("web-budget", ROBOTO, ROBOTO)

    assert result.returncode == 0
    assert "Per-File Status:" in result.stdout
    total_count = result.stdout.count("bytes /")
    assert total_count >= 2


def test_web_budget_invalid_file() -> None:
    """Non-existent file exits with error code 1."""
    result = run("web-budget", "/nonexistent_font_file.ttf")

    assert result.returncode == 1
    assert result.stderr.strip() != ""
