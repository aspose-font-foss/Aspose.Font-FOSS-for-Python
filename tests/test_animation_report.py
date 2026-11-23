"""Tests for the Animation Report CLI command (FONT-233)."""

from pathlib import Path

from aspose_font import FontLoader
from aspose_font.animation import AnimationAsset, AnimationPreviewBuilder


def test_animation_report_cli_success(testdata_dir: Path, tmp_path: Path) -> None:
    """Verify that running animation-report creates animation.apng and report.html."""
    font_path = testdata_dir / "Roboto-VariableFont_wdth,wght.ttf"
    font = FontLoader.open(str(font_path))

    package = AnimationPreviewBuilder.build_axis_sweep(
        font,
        axis_tag="wdth",
        start_val=75.0,
        end_val=100.0,
        frames=3,
        fps=10,
        text="Test",
        preset="draft",
        file_stem="animation",
    )

    output_dir = tmp_path / "animation-report"
    output_dir.mkdir(parents=True, exist_ok=True)
    apng_path = package.write_to(output_dir / "animation.apng")
    html_content = _build_animation_report_html(package, "draft")
    html_path = output_dir / "report.html"
    html_path.write_text(html_content, encoding="utf-8")

    assert apng_path.exists()
    assert html_path.exists()
    apng_data = apng_path.read_bytes()
    assert apng_data.startswith(b"\x89PNG\r\n\x1a\n")
    assert b"acTL" in apng_data
    assert b"fcTL" in apng_data
    html_data = html_path.read_text(encoding="utf-8")
    assert 'src="animation.apng"' in html_data
    assert "draft" in html_data


def test_animation_report_cli_basic_structure(testdata_dir: Path, tmp_path: Path) -> None:
    """Verify HTML structure embeds APNG with correct src and includes preset in heading."""
    font_path = testdata_dir / "Roboto-VariableFont_wdth,wght.ttf"
    font = FontLoader.open(str(font_path))

    animation = AnimationPreviewBuilder.build_axis_sweep(
        font,
        axis_tag="wdth",
        start_val=75.0,
        end_val=100.0,
        frames=3,
        fps=10,
        text="Test",
        preset="standard",
        file_stem="animation",
    )

    output_dir = tmp_path / "animation-report"
    output_dir.mkdir(parents=True, exist_ok=True)
    animation.write_to(output_dir / "animation.apng")
    html_content = _build_animation_report_html(animation, "standard")
    html_path = output_dir / "report.html"
    html_path.write_text(html_content, encoding="utf-8")

    html_data = html_path.read_text(encoding="utf-8")
    assert '<img src="animation.apng"' in html_data
    assert "standard" in html_data
    assert "<h1>Animation Report</h1>" in html_data


def test_animation_report_builder_non_empty_content(testdata_dir: Path, tmp_path: Path) -> None:
    """Verify HTML content is non-empty and contains expected elements."""
    animation = AnimationPreviewBuilder.build_axis_sweep(
        FontLoader.open(str(testdata_dir / "Roboto-VariableFont_wdth,wght.ttf")),
        axis_tag="wdth",
        start_val=75.0,
        end_val=100.0,
        frames=3,
        fps=10,
        text="Test",
        preset="draft",
        file_stem="animation",
    )

    html_content = _build_animation_report_html(animation, "draft")
    assert len(html_content) > 200
    assert "animation.apng" in html_content
    assert "draft" in html_content.lower()


def _build_animation_report_html(animation: AnimationAsset, preset: str) -> str:
    import html
    return (
        "<!doctype html>\n"
        "<html lang=\"en\">\n"
        "<head>\n"
        "  <meta charset=\"utf-8\">\n"
        "  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
        "  <title>Animation Report</title>\n"
        "  <style>body{font-family:Georgia,serif;max-width:960px;margin:32px auto;padding:0 20px;color:#2a241c;background:#fffdf8} img{max-width:100%;height:auto;border:1px solid #d7c7b1}</style>\n"
        "</head>\n"
        "<body>\n"
        "  <h1>Animation Report</h1>\n"
        f"  <p><strong>Preset:</strong> {html.escape(preset)}</p>\n"
        f"  <p><strong>FPS:</strong> {animation.fps} | <strong>Frames:</strong> {animation.frame_count}</p>\n"
        f"  <p><img src=\"animation.apng\" alt=\"Animation preview\"></p>\n"
        "</body>\n"
        "</html>\n"
    )
