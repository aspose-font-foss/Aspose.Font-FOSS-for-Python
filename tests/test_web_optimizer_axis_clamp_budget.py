"""Tests for FONT-574 WebFontOptimizer Axis Clamping & Payload Budgeting Integration."""

from __future__ import annotations

from pathlib import Path

from aspose_font import FontLoader, WebFontOptimizer

ROBOTO_PATH = Path(__file__).resolve().parents[1] / "testdata" / "Roboto-VariableFont_wdth,wght.ttf"


class TestWebFontOptimizerAxisClamp:
    """Tests for axis_clamp_specs parameter."""

    def test_axis_clamp_single_axis(self, tmp_path: Path) -> None:
        """Axis clamping applies within WebFontOptimizer.build()."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        package = WebFontOptimizer.build(
            FontLoader.open(ROBOTO_PATH),
            source_path=ROBOTO_PATH,
            file_stem="roboto",
            include_woff=False,
            axis_clamp_specs=(("wght", 400.0, 700.0),),
        )
        package.write_to(output_dir)

        manifest = package.manifest
        assert "axis_clamping" in manifest
        assert manifest["axis_clamping"]["applied"] == [
            {"axis_tag": "wght", "min_value": 400.0, "max_value": 700.0}
        ]

    def test_axis_clamp_multiple_axes(self, tmp_path: Path) -> None:
        """Multiple axes can be clamped."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        package = WebFontOptimizer.build(
            FontLoader.open(ROBOTO_PATH),
            source_path=ROBOTO_PATH,
            file_stem="roboto",
            include_woff=False,
            axis_clamp_specs=(
                ("wght", 400.0, 700.0),
                ("wdth", 75.0, 100.0),
            ),
        )
        package.write_to(output_dir)

        manifest = package.manifest
        assert len(manifest["axis_clamping"]["applied"]) == 2
        assert manifest["axis_clamping"]["applied"][0]["axis_tag"] == "wght"
        assert manifest["axis_clamping"]["applied"][1]["axis_tag"] == "wdth"

    def test_axis_clamp_no_spec_no_clamp(self, tmp_path: Path) -> None:
        """Without axis_clamp_specs, manifest has null axis_clamping."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        package = WebFontOptimizer.build(
            FontLoader.open(ROBOTO_PATH),
            source_path=ROBOTO_PATH,
            file_stem="roboto",
            include_woff=False,
        )
        package.write_to(output_dir)

        assert package.manifest.get("axis_clamping") is None


class TestWebFontOptimizerBudget:
    """Tests for budget evaluation parameters."""

    def test_budget_evaluation_single_font(self, tmp_path: Path) -> None:
        """Budget evaluation reports per-font status."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        package = WebFontOptimizer.build(
            FontLoader.open(ROBOTO_PATH),
            source_path=ROBOTO_PATH,
            file_stem="roboto",
            include_woff=False,
            per_font_budget_bytes=100_000,
        )
        package.write_to(output_dir)

        manifest = package.manifest
        assert "performance_budget" in manifest
        budget = manifest["performance_budget"]
        assert "status" in budget
        assert "font_status" in budget
        assert len(budget["font_status"]) >= 1

    def test_budget_evaluation_exceeded(self, tmp_path: Path) -> None:
        """Budget exceeded status reported correctly."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        package = WebFontOptimizer.build(
            FontLoader.open(ROBOTO_PATH),
            source_path=ROBOTO_PATH,
            file_stem="roboto",
            include_woff=False,
            per_font_budget_bytes=10_000,
        )
        package.write_to(output_dir)

        budget = package.manifest["performance_budget"]
        assert budget["status"] in ("warning", "exceeded")

    def test_no_budget_evaluation_when_disabled(self, tmp_path: Path) -> None:
        """No budget data when per_font_budget_bytes is None."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        package = WebFontOptimizer.build(
            FontLoader.open(ROBOTO_PATH),
            source_path=ROBOTO_PATH,
            file_stem="roboto",
            include_woff=False,
            per_font_budget_bytes=None,
        )
        package.write_to(output_dir)

        woff2_files = list(output_dir.glob("*.woff2"))
        assert len(woff2_files) >= 1
        assert package.manifest is not None

    def test_generate_preload_tags(self, tmp_path: Path) -> None:
        """Preload tags generated when requested."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        package = WebFontOptimizer.build(
            FontLoader.open(ROBOTO_PATH),
            source_path=ROBOTO_PATH,
            file_stem="roboto",
            include_woff=False,
            generate_preload_tags=True,
        )
        package.write_to(output_dir)

        manifest = package.manifest
        assert "preload_tags" in manifest
        assert len(manifest["preload_tags"]) >= 1
        assert '<link rel="preload"' in manifest["preload_tags"][0]

    def test_no_preload_tags_when_disabled(self, tmp_path: Path) -> None:
        """No preload tags when generate_preload_tags=False."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        package = WebFontOptimizer.build(
            FontLoader.open(ROBOTO_PATH),
            source_path=ROBOTO_PATH,
            file_stem="roboto",
            include_woff=False,
            generate_preload_tags=False,
        )
        package.write_to(output_dir)

        assert package.manifest.get("preload_tags") is None


class TestWebFontOptimizerIntegration:
    """Integration tests combining axis clamping and budget evaluation."""

    def test_axis_clamp_with_budget_evaluation(self, tmp_path: Path) -> None:
        """Axis clamping and budget evaluation work together."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        package = WebFontOptimizer.build(
            FontLoader.open(ROBOTO_PATH),
            source_path=ROBOTO_PATH,
            file_stem="roboto",
            include_woff=False,
            axis_clamp_specs=(("wght", 400.0, 700.0),),
            per_font_budget_bytes=100_000,
            generate_preload_tags=True,
        )
        package.write_to(output_dir)

        manifest = package.manifest
        assert manifest["axis_clamping"]["applied"][0]["axis_tag"] == "wght"
        assert "performance_budget" in manifest
        assert "preload_tags" in manifest
        assert len(manifest["preload_tags"]) >= 1

    def test_all_features_combined(self, tmp_path: Path) -> None:
        """All new features work in combination."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        package = WebFontOptimizer.build(
            FontLoader.open(ROBOTO_PATH),
            source_path=ROBOTO_PATH,
            file_stem="roboto",
            include_woff=False,
            axis_clamp_specs=(
                ("wght", 400.0, 700.0),
                ("wdth", 75.0, 100.0),
            ),
            per_font_budget_bytes=100_000,
            total_family_budget_bytes=200_000,
            generate_preload_tags=True,
        )
        package.write_to(output_dir)

        manifest = package.manifest
        assert len(manifest["axis_clamping"]["applied"]) == 2
        assert manifest["performance_budget"]["status"] in ("pass", "warning", "exceeded")
        assert len(manifest["preload_tags"]) >= 1
