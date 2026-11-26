import json
import subprocess
import sys
from pathlib import Path


def _run_cli(args, capture_output=False):
    cmd = [sys.executable, "-c", "import aspose_font.cli, sys; sys.argv=" + repr(['aspose-font'] + args) + "; aspose_font.cli.main()"]
    return subprocess.run(cmd, capture_output=capture_output, text=True, check=True)

def test_cli_capability_json_output(tmp_path: Path):
    # Path to a sample variable font fixture
    font_path = Path("testdata/Roboto-VariableFont_wdth,wght.ttf")
    output_path = tmp_path / "capability.json"

    _run_cli([
        "capability",
        str(font_path),
        "--json-output",
        str(output_path),
    ])

    assert output_path.is_file()
    data = json.loads(output_path.read_text())
    assert data.get("kind") == "font_capability_report"

def test_cli_capability_stdout(tmp_path: Path):
    font_path = Path("testdata/Roboto-VariableFont_wdth,wght.ttf")
    result = _run_cli([
        "capability",
        str(font_path),
    ], capture_output=True)
    assert result.stdout
    data = json.loads(result.stdout)
    assert data.get("kind") == "font_capability_report"
