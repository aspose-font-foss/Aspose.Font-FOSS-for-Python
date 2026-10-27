import zipfile
from pathlib import Path

import pytest

from aspose_font import FontLoader, WebFontOptimizer


@pytest.fixture
def roboto_path():
    # Use the testdata Roboto variable font
    return Path(__file__).resolve().parents[1] / "testdata" / "Roboto-VariableFont_wdth,wght.ttf"

def test_web_optimizer_creates_zip_package(tmp_path: Path, roboto_path: Path):
    font = FontLoader.open(str(roboto_path))
    # Build package with default settings (no decision report to keep minimal)
    package = WebFontOptimizer.build(font)
    _ = package.write_to(tmp_path)
    zip_path = tmp_path / "package.zip"
    assert zip_path.is_file(), "Package zip archive should be created"
    # Verify zip contains expected manifest file
    with zipfile.ZipFile(zip_path, "r") as zf:
        namelist = zf.namelist()
        assert package.manifest_filename in namelist, "Manifest file must be present in zip"
        # Ensure at least one font file is included (e.g., .woff2) by checking any .woff2 entry
        woff2_files = [name for name in namelist if name.lower().endswith('.woff2')]
        assert woff2_files, "Zip should contain generated .woff2 font files"
