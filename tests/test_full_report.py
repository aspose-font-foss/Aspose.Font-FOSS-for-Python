import subprocess
import sys
from pathlib import Path


def test_full_report(tmp_path: Path):
    # Locate a variable font testdata file
    font_path = Path("testdata") / "Roboto-VariableFont_wdth,wght.ttf"
    # Ensure the font exists relative to repository root
    assert font_path.is_file()
    # Run the CLI full-report command
    result = subprocess.run([
        sys.executable,
        "-m",
        "aspose_font.cli",
        "full-report",
        "--font",
        str(font_path),
        "--output",
        str(tmp_path),
    ], capture_output=True, text=True)
    assert result.returncode == 0, f"CLI failed: {result.stderr}"
    # Check expected manifest files exist
    assert (tmp_path / "web" / "optimizer-manifest.json").exists()
    assert (tmp_path / "qa" / "qa-report.json").exists()
    assert (tmp_path / "instance" / "instance-manifest.json").exists()
