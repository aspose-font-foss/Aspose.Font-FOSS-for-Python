"""Tests for CLI instance-export subcommand (FONT-558)."""

import subprocess
import sys
from pathlib import Path

ROBOTO = str(Path(__file__).resolve().parents[1] / "testdata" / "Roboto-VariableFont_wdth,wght.ttf")


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "aspose_font.cli"] + list(args),
        capture_output=True,
        text=True,
    )


class TestInstanceExportCommand:
    """Test instance-export CLI command."""

    def test_instance_export_writes_font_files_to_directory(self, tmp_path: Path) -> None:
        """Test that instance-export generates WOFF2 files for each named instance."""
        out_dir = tmp_path / "output"

        result = run(
            "instance-export",
            ROBOTO,
            str(out_dir),
        )

        assert result.returncode == 0
        output_files = list(out_dir.glob("*.woff2"))
        assert len(output_files) >= 2
        file_names = [f.name for f in output_files]
        assert any("Bold" in name for name in file_names)
        assert any("Regular" in name for name in file_names)

    def test_instance_export_ttf_format(self, tmp_path: Path) -> None:
        """Test TTF format output with --format ttf."""
        out_dir = tmp_path / "output"

        result = run(
            "instance-export",
            ROBOTO,
            str(out_dir),
            "--format", "ttf",
        )

        assert result.returncode == 0
        output_files = list(out_dir.glob("*.ttf"))
        assert len(output_files) >= 2
        woff2_files = list(out_dir.glob("*.woff2"))
        assert len(woff2_files) == 0

    def test_instance_export_css_generation(self, tmp_path: Path) -> None:
        """Test CSS stylesheet generation with --css flag."""
        out_dir = tmp_path / "output"

        result = run(
            "instance-export",
            ROBOTO,
            str(out_dir),
            "--css",
        )

        assert result.returncode == 0
        css_path = out_dir / "instances.css"
        assert css_path.exists()
        css_content = css_path.read_text(encoding="utf-8")
        assert "@font-face" in css_content
        assert "font-weight:" in css_content
        assert "font-style:" in css_content

    def test_instance_export_include_default(self, tmp_path: Path) -> None:
        """Test that default instance is included by default and can be excluded."""
        out_dir = tmp_path / "output"

        result_with_default = run(
            "instance-export",
            ROBOTO,
            str(out_dir / "with_default"),
        )

        assert result_with_default.returncode == 0
        default_files = len(list((out_dir / "with_default").glob("*.woff2")))

        out_dir2 = tmp_path / "output2"
        result_without_default = run(
            "instance-export",
            ROBOTO,
            str(out_dir2),
            "--no-default",
        )

        assert result_without_default.returncode == 0
        no_default_files = len(list((out_dir2).glob("*.woff2")))

        assert no_default_files < default_files

    def test_instance_export_requires_variable_font(self, tmp_path: Path) -> None:
        """Test that static fonts are rejected."""
        out_dir = tmp_path / "output"
        static_font = Path(__file__).resolve().parents[1] / "testdata" / "Arial.pfa"

        result = run(
            "instance-export",
            str(static_font),
            str(out_dir),
        )

        assert result.returncode != 0
        assert "variable" in result.stderr.lower()

    def test_instance_export_invalid_input_file(self, tmp_path: Path) -> None:
        """Test error handling for missing input file."""
        out_dir = tmp_path / "output"

        result = run(
            "instance-export",
            "nonexistent.ttf",
            str(out_dir),
        )

        assert result.returncode != 0
        assert "Error:" in result.stderr or "cannot" in result.stderr.lower()

    def test_instance_export_exit_code_success(self, tmp_path: Path) -> None:
        """Test that success returns exit code 0."""
        out_dir = tmp_path / "output"

        result = run(
            "instance-export",
            ROBOTO,
            str(out_dir),
        )

        assert result.returncode == 0

    def test_instance_export_exit_code_failure(self, tmp_path: Path) -> None:
        """Test that failure returns non-zero exit code."""
        out_dir = tmp_path / "output"

        result = run(
            "instance-export",
            "nonexistent.ttf",
            str(out_dir),
        )

        assert result.returncode != 0


def test_cli_instance_export_integration(tmp_path: Path) -> None:
    """Integration test for instance-export command."""
    out_dir = tmp_path / "output"

    result = run(
        "instance-export",
        ROBOTO,
        str(out_dir),
        "--css",
    )

    assert result.returncode == 0
    output_files = list(out_dir.glob("*.woff2"))
    assert len(output_files) > 0
    assert (out_dir / "instances.css").exists()
