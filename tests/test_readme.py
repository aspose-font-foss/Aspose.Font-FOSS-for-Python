"""Regression checks for README surface and demo-site linkage."""

from __future__ import annotations

from pathlib import Path


def _readme() -> str:
    return Path("README.md").read_text(encoding="utf-8")


def test_readme_keeps_core_public_sections() -> None:
    readme = _readme()
    assert "## Install" in readme
    assert "## Quick Start" in readme
    assert "## Development" in readme


def test_readme_highlights_variable_font_direction_and_qa() -> None:
    readme = _readme()
    assert "Variable-Font-First Workflows" in readme
    assert "CompatibilityChecker" in readme
    assert "DeltaInspector" in readme
    assert "build_web_bundle" in readme


def test_readme_embeds_generated_visual_assets() -> None:
    readme = _readme()
    assert "![Family review board](./website/generated/roboto-family-review-board.png)" in readme
    assert "![Axis grid preview](./website/generated/roboto-axis-grid.png)" in readme
    assert "![Delta comparison board](./website/generated/roboto-delta-compare.png)" in readme


def test_readme_points_to_public_github_repository() -> None:
    readme = _readme()
    url = "https://github.com/aspose-font-foss/Aspose.Font-FOSS-for-Python"
    assert url in readme
    assert "https://github.com/aspose/aspose-font" not in readme


def test_readme_links_license_file() -> None:
    readme = _readme()
    assert "## License" in readme
    assert "[MIT](./LICENSE.txt)" in readme


def test_readme_omits_internal_only_sections() -> None:
    readme = _readme()
    assert "## Live Project Surfaces" not in readme
    assert "## Internal Task Token Reporting" not in readme
    assert "## GitHub Clean Mirror" not in readme
    assert "## Demo Site and README Alignment" not in readme
    assert "## More Documentation" not in readme
    assert "GITHUB_MIRROR_TOKEN" not in readme
    assert "aspose-font-reporting" not in readme
    assert "./backlog/docs/ROADMAP.md" not in readme
    assert "./backlog/docs/PROJECT_CONTEXT.md" not in readme
