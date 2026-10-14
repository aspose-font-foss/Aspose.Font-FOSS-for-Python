'''Tests for var-package --specimen-board flag (FONT-369).'''
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

# Path to variable font used in other tests
ROBOTO = str(Path(__file__).resolve().parents[1] / "testdata" / "Roboto-VariableFont_wdth,wght.ttf")
CLI = [sys.executable, "-m", "aspose_font.cli"]


def run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        CLI + list(args),
        capture_output=True,
        text=True,
    )


def test_var_package_specimen_board_flag(tmp_path: Path) -> None:
    output_dir = tmp_path / "var-package-spec"
    result = run(
        "var-package",
        ROBOTO,
        str(output_dir),
        "--specimen-board",
    )
    assert result.returncode == 0
    # Verify specimen board PNG exists and is non‑empty
    specimen_path = output_dir / "specimen_board.png"
    assert specimen_path.is_file()
    assert specimen_path.stat().st_size > 0
    # Basic sanity on output messages
    assert "Package written to" in result.stdout
