"""Tests for CDN manifest generation in Web Font Optimizer."""

from pathlib import Path

import pytest

from aspose_font import FontLoader, build_web_optimizer_package


@pytest.fixture
def font_path() -> Path:
    return Path(__file__).resolve().parents[1] / "testdata" / "Roboto-VariableFont_wdth,wght.ttf"


class TestCDNManifest:
    """Test CDN manifest generation."""

    def test_cdn_manifest_generation(self, font_path: Path, tmp_path: Path) -> None:
        """Verify CDN manifest is created when flag is enabled."""
        font = FontLoader.open(font_path)
        output_dir = tmp_path / "output"

        package = build_web_optimizer_package(
            font,
            source_path=font_path,
            cdn_base_url="https://cdn.myfonts.com",
        )
        package.write_to(output_dir)

        manifest_path = output_dir / "cdn-manifest.json"
        assert manifest_path.exists()

        manifest_content = manifest_path.read_text(encoding="utf-8")
        assert '"font_url": "https://cdn.myfonts.com/' in manifest_content
        assert '"cache_control": "max-age=31536000"' in manifest_content

    def test_cdn_manifest_omitted_without_flag(self, font_path: Path, tmp_path: Path) -> None:
        """Verify CDN manifest is omitted when base_url is None."""
        font = FontLoader.open(font_path)
        output_dir = tmp_path / "output"

        package = build_web_optimizer_package(
            font,
            source_path=font_path,
            cdn_base_url=None,
        )
        package.write_to(output_dir)

        manifest_path = output_dir / "cdn-manifest.json"
        assert not manifest_path.exists()

    def test_cdn_manifest_url_construction(self, font_path: Path, tmp_path: Path) -> None:
        """Verify CDN URLs are constructed correctly."""
        font = FontLoader.open(font_path)
        output_dir = tmp_path / "output"

        package = build_web_optimizer_package(
            font,
            source_path=font_path,
            cdn_base_url="https://cdn.example.com/assets",
        )
        package.write_to(output_dir)

        manifest_path = output_dir / "cdn-manifest.json"
        import json
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

        entries = manifest.get("entries", [])
        assert len(entries) > 0

        for entry in entries:
            url = entry.get("font_url", "")
            assert url.startswith("https://cdn.example.com/assets/")
            assert ".woff2" in url or ".woff" in url
            assert entry.get("cache_control") == "max-age=31536000"
