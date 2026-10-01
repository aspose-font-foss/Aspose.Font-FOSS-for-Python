"""Shared pytest fixtures for the font library test suite."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from aspose_font import CffFont, EotFont, FontLoader, TtfFont, Woff2Font, WoffFont


def pytest_sessionstart(session) -> None:
    root = Path(__file__).resolve().parents[1]
    script = root / "scripts" / "generate_website.py"
    if not script.exists():
        return
    env = os.environ.copy()
    status_path = root / "website" / "generated" / "status.json"
    if status_path.exists() and "ASPOSE_FONT_WEBSITE_GENERATED_AT" not in env:
        status = json.loads(status_path.read_text(encoding="utf-8"))
        generated_at = status.get("generated_at")
        if isinstance(generated_at, str):
            env["ASPOSE_FONT_WEBSITE_GENERATED_AT"] = generated_at
    subprocess.run(
        [sys.executable, str(script)],
        cwd=root,
        env=env,
        check=True,
    )


@pytest.fixture(scope="session")
def testdata_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "testdata"


@pytest.fixture(scope="session")
def roboto_path(testdata_dir: Path) -> Path:
    return testdata_dir / "Roboto-VariableFont_wdth,wght.ttf"


@pytest.fixture(scope="session")
def roboto(roboto_path: Path) -> TtfFont:
    font = FontLoader.open(str(roboto_path))
    assert isinstance(font, TtfFont)
    return font


@pytest.fixture(scope="session")
def opensans_cff_path(testdata_dir: Path) -> Path:
    return testdata_dir / "OpenSans-Regular.cff"


@pytest.fixture(scope="session")
def opensans_cff(opensans_cff_path: Path) -> CffFont:
    font = FontLoader.open(str(opensans_cff_path))
    assert isinstance(font, CffFont)
    return font


@pytest.fixture(scope="session")
def saira_woff_path(testdata_dir: Path) -> Path:
    return testdata_dir / "saira-extracondensed-semibold.woff"


@pytest.fixture(scope="session")
def saira_woff2_path(testdata_dir: Path) -> Path:
    return testdata_dir / "saira-extracondensed-semibold.woff2"


@pytest.fixture(scope="session")
def saira_woff(saira_woff_path: Path) -> WoffFont:
    font = FontLoader.open(str(saira_woff_path))
    assert isinstance(font, WoffFont)
    return font


@pytest.fixture(scope="session")
def saira_woff2(saira_woff2_path: Path) -> Woff2Font:
    font = FontLoader.open(str(saira_woff2_path))
    assert isinstance(font, Woff2Font)
    return font


@pytest.fixture(scope="session")
def saira_eot_path(testdata_dir: Path) -> Path:
    return testdata_dir / "saira-extracondensed-semibold.eot"


@pytest.fixture(scope="session")
def saira_eot(saira_eot_path: Path) -> EotFont:
    font = FontLoader.open(str(saira_eot_path))
    assert isinstance(font, EotFont)
    return font
