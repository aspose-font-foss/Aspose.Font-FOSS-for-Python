"""Performance regression tests for font subsetting (FONT-269)."""

from __future__ import annotations

from pathlib import Path

import pytest

from aspose_font import FontLoader, TtfFont
from aspose_font.subsetter import FontSubsetter


@pytest.fixture(scope="module")
def medium_size_font(testdata_dir: Path) -> TtfFont:
    """Load a medium-size font for performance testing."""
    font_path = testdata_dir / "Roboto-VariableFont_wdth,wght.ttf"
    return FontLoader.open(str(font_path))  # type: ignore[return-value]


class TestFontSubsetterBenchmark:
    """Tests for FontSubsetter.benchmark_subsetting() timing helper."""

    def test_benchmark_subsetting_returns_correct_structure(
        self, medium_size_font: TtfFont
    ):
        """Verify benchmark_subsetting returns dict with all required keys."""
        codepoints = {ord("A"), ord("B"), ord("C")}
        result = FontSubsetter.benchmark_subsetting(medium_size_font, codepoints, runs=1)

        assert isinstance(result, dict)
        assert "elapsed_seconds" in result
        assert "average_seconds" in result
        assert "min_seconds" in result
        assert "max_seconds" in result
        assert "runs" in result

    def test_benchmark_subsetting_timing_values_are_non_negative(
        self, medium_size_font: TtfFont
    ):
        """Verify timing values are non-negative floats."""
        codepoints = {ord("A"), ord("B"), ord("C")}
        result = FontSubsetter.benchmark_subsetting(medium_size_font, codepoints, runs=1)

        assert result["elapsed_seconds"] >= 0.0
        assert result["average_seconds"] >= 0.0
        assert result["min_seconds"] >= 0.0
        assert result["max_seconds"] >= 0.0
        assert result["runs"] >= 1

    def test_benchmark_subsetting_runs_multiple_iterations(self, medium_size_font: TtfFont):
        """Verify runs parameter controls iteration count."""
        codepoints = {ord("A"), ord("B"), ord("C")}

        result_1 = FontSubsetter.benchmark_subsetting(medium_size_font, codepoints, runs=1)
        assert result_1["runs"] == 1

        result_3 = FontSubsetter.benchmark_subsetting(medium_size_font, codepoints, runs=3)
        assert result_3["runs"] == 3

    def test_benchmark_subsetting_raises_on_invalid_runs(self, medium_size_font: TtfFont):
        """Verify ValueError for runs < 1."""
        codepoints = {ord("A")}
        with pytest.raises(ValueError, match="runs must be"):
            FontSubsetter.benchmark_subsetting(medium_size_font, codepoints, runs=0)


class TestSubsetCommandBenchmark:
    """Tests for CLI --benchmark flag integration."""

    def test_subset_command_benchmark_flag_output(self, tmp_path: Path, roboto: TtfFont):
        """Verify CLI outputs 'Benchmark: Xs' format when --benchmark is set."""
        input_path = tmp_path / "input.ttf"
        output_path = tmp_path / "output.ttf"

        input_path.write_bytes(roboto.to_bytes())

        # Use sys.executable to invoke CLI (per CI compatibility rules)
        import subprocess
        import sys

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "aspose_font.cli",
                "subset",
                str(input_path),
                str(output_path),
                "--text", "ABC",
                "--benchmark",
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert "Benchmark:" in result.stdout
        first_line = result.stdout.strip().split("\n")[0]
        assert first_line.endswith("s")


class TestPerformanceRegression:
    """Performance regression gate tests for subsetting operations."""

    def test_medium_font_latin_preset_completes_within_threshold(
        self, medium_size_font: TtfFont
    ):
        """Verify subsetting a medium-size font with latin preset completes in ≤ 0.5s.

        Acceptance Criteria 3:
        "New test `tests/test_subsetting_performance.py` verifies that subsetting
        a medium‑size font with preset `latin` completes in ≤ 0.5 seconds on a
        typical CI runner."

        Note: Threshold is generous (0.5s) to accommodate varied CI environments.
        Actual CI gating should use stricter thresholds based on baseline metrics.
        """
        result = FontSubsetter.benchmark_subsetting(
            medium_size_font,
            codepoints=FontSubsetter._codepoints_from_presets("latin"),
            runs=1,
        )

        # Performance gate: must complete within 0.5 seconds
        # Threshold should be calibrated against CI baseline metrics
        assert result["average_seconds"] <= 0.5, (
            f"Subsetting performance degraded: {result['average_seconds']:.3f}s > 0.5s"
        )
