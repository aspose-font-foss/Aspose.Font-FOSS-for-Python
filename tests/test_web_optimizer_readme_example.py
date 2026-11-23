# ruff: noqa: I001
from pathlib import Path

from aspose_font.web import WebFontOptimizer, WebFontBundle, WebFontOptimizerPackage

def test_generate_readme_example(tmp_path: Path) -> None:
    """Test README example generation."""
    bundle = WebFontBundle(
        family="TestFont",
        style="Regular",
        css="",
        html="",
        css_filename="fonts.css",
        html_filename="specimen.html",
    )
    package = WebFontOptimizerPackage(bundle=bundle)

    WebFontOptimizer.generate_readme_example(tmp_path, package)

    example_html = tmp_path / "example.html"
    readme_md = tmp_path / "README_EXAMPLE.md"
    assert example_html.is_file()
    assert readme_md.is_file()

    readme_content = readme_md.read_text(encoding="utf-8")
    assert "Web Font Optimizer Summary" in readme_content
    for name in ["fonts.css", "specimen.html", "optimizer-manifest.json"]:
        assert f"- `{name}`" in readme_content
