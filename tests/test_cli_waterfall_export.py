"""Tests for FONT-548 CLI waterfall-export subcommand."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from aspose_font import FontLoader

ROBOTO = str(Path(__file__).resolve().parents[1] / "testdata" / "Roboto-VariableFont_wdth,wght.ttf")


def run(*args: str) -> subprocess.CompletedProcess[str]:
    import subprocess
    return subprocess.run(
        [sys.executable, "-m", "aspose_font.cli"] + list(args),
        capture_output=True,
        text=True,
    )


class TestWaterfallExportCommand:
    """Test waterfall-export CLI command."""

    def test_waterfall_export_writes_png_specimens_to_directory(
        self, tmp_path: Path
    ) -> None:
        """Test that waterfall-export generates PNG files for each coordinate."""
        out_dir = tmp_path / "output"

        result = run(
            "waterfall-export",
            ROBOTO,
            str(out_dir),
            "--steps", "3",
        )

        assert result.returncode == 0
        # Roboto wdth axis: min=75, max=100; wght axis: min=100, max=900
        # With 3 steps, we get: 75, 87.5, 100 for wdth and 100, 500, 900 for wght
        assert (out_dir / "specimen-wdth75.0-wght100.0.png").exists()
        assert (out_dir / "specimen-wdth75.0-wght500.0.png").exists()
        assert (out_dir / "specimen-wdth75.0-wght900.0.png").exists()
        assert (out_dir / "specimen-wdth87.5-wght100.0.png").exists()
        assert (out_dir / "specimen-wdth87.5-wght500.0.png").exists()
        assert (out_dir / "specimen-wdth87.5-wght900.0.png").exists()
        assert (out_dir / "specimen-wdth100.0-wght100.0.png").exists()
        assert (out_dir / "specimen-wdth100.0-wght500.0.png").exists()
        assert (out_dir / "specimen-wdth100.0-wght900.0.png").exists()

    def test_waterfall_export_creates_json_manifest_when_requested(
        self, tmp_path: Path
    ) -> None:
        """Test that --json generates a manifest file with coordinates."""
        out_dir = tmp_path / "output"

        result = run(
            "waterfall-export",
            ROBOTO,
            str(out_dir),
            "--steps", "2",
            "--json",
        )

        assert result.returncode == 0
        manifest_path = out_dir / "waterfall-matrix-manifest.json"
        assert manifest_path.exists()

        manifest = json.loads(manifest_path.read_text())
        assert manifest["command"] == "waterfall-export"
        assert set(manifest["axes"]) == {"wdth", "wght"}
        assert manifest["steps"] == 2
        assert len(manifest["matrix"]) == 4

    def test_waterfall_export_validates_steps_minimum(self, tmp_path: Path) -> None:
        """Test that steps < 2 raises an error."""
        out_dir = tmp_path / "output"

        result = run(
            "waterfall-export",
            ROBOTO,
            str(out_dir),
            "--steps", "1",
        )

        assert result.returncode != 0
        assert "steps must be an integer >= 2" in result.stderr

    def test_waterfall_export_requires_variable_font(self, tmp_path: Path) -> None:
        """Test that static fonts are rejected."""
        out_dir = tmp_path / "output"
        # Use a static font file (Arial.pfa or OpenSans-Regular.cff)
        static_font = Path(__file__).resolve().parents[1] / "testdata" / "Arial.pfa"

        result = run(
            "waterfall-export",
            str(static_font),
            str(out_dir),
        )

        assert result.returncode != 0
        assert "variable" in result.stderr.lower()

    def test_waterfall_export_with_custom_axes(self, tmp_path: Path) -> None:
        """Test filtering to specific axes."""
        out_dir = tmp_path / "output"

        result = run(
            "waterfall-export",
            ROBOTO,
            str(out_dir),
            "--steps", "2",
            "--axes", "wght",
        )

        assert result.returncode == 0
        # Should only have wght coordinates, no wdth
        assert (out_dir / "specimen-wght100.0.png").exists()
        assert (out_dir / "specimen-wght900.0.png").exists()
        assert not any(f.name.startswith("specimen-wdth") for f in out_dir.glob("specimen-*.png"))

    def test_waterfall_export_pdf_format(self, tmp_path: Path) -> None:
        """Test PDF output format."""
        out_dir = tmp_path / "output"

        result = run(
            "waterfall-export",
            ROBOTO,
            str(out_dir),
            "--steps", "2",
            "--format", "pdf",
        )

        assert result.returncode == 0
        assert len(list(out_dir.glob("specimen-*.pdf"))) > 0


def test_cli_waterfall_export_integration(roboto: FontLoader, tmp_path: Path) -> None:
    """Integration test for waterfall-export command."""
    steps = 3
    available_axes = {axis.tag.lower(): axis for axis in roboto.variable_axes}

    values = [
        available_axes["wght"].min_value + (available_axes["wght"].max_value - available_axes["wght"].min_value) * i / (steps - 1)
        for i in range(steps)
    ]

    assert len(values) == 3
    assert pytest.approx(values[0], abs=0.01) == 100
    assert pytest.approx(values[1], abs=0.01) == 500
    assert pytest.approx(values[2], abs=0.01) == 900
