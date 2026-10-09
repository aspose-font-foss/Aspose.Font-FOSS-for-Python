"""Test that visual proof also creates an HTML index file."""

from pathlib import Path


def test_visual_proof_creates_html_index(tmp_path: Path) -> None:
    font_path = Path(__file__).resolve().parents[1] / "testdata" / "Roboto-VariableFont_wdth,wght.ttf"
    if not font_path.exists():
        import pytest
        pytest.skip("Test font not available")

    output_dir = tmp_path / "visual-html"
    output_dir.mkdir()

    from aspose_font.visual_proof import run_visual_proof
    run_visual_proof(font_path, output_dir)

    index_file = output_dir / "index.html"
    assert index_file.exists(), "index.html not created"
    content = index_file.read_text(encoding="utf-8")
    assert "Animation (APNG)" in content
    assert "Coverage Diagram" in content
    assert "Capability Report" in content
    assert "href='animation.apng'" in content
    assert "href='coverage.png'" in content
    assert "href='capability.json'" in content
