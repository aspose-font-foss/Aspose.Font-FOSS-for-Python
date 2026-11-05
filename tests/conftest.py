"""Shared pytest fixtures for the font library test suite."""
# ruff: noqa: I001, E402

from __future__ import annotations
import sys
import pathlib
from pathlib import Path

src_dir = pathlib.Path(__file__).resolve().parents[1] / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

import pytest

from aspose_font import CffFont, EotFont, FontLoader, TtfFont, Woff2Font, WoffFont
from aspose_font.performance import PerformanceBenchmark


def pytest_configure(config: pytest.Config) -> None:
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "performance: mark as performance benchmark test"
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


@pytest.fixture(scope="session")
def benchmark(request: pytest.FixtureRequest) -> PerformanceBenchmark:
    """Performance benchmark fixture for timing measurements."""
    fixture_root = Path("testdata")
    return PerformanceBenchmark(fixture_root)
