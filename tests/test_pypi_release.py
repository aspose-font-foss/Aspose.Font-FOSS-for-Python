"""Unit tests for scripts/publish_pypi_release.py."""

from __future__ import annotations

import urllib.error
from pathlib import Path
from unittest.mock import patch

import pytest

try:
    from scripts.publish_pypi_release import (
        check_version_exists,
        is_valid_pep440,
        main,
        set_version_in_tree,
    )
except ImportError:
    pytest.skip("scripts package not available in public clean mirror", allow_module_level=True)


def test_is_valid_pep440() -> None:
    assert is_valid_pep440("26.10.1")
    assert is_valid_pep440("26.5.2")
    assert is_valid_pep440("1.0.0")
    assert is_valid_pep440("2026.5.1")
    assert not is_valid_pep440("v26.10.1")
    assert not is_valid_pep440("invalid-version")
    assert not is_valid_pep440("")


def test_set_version_in_tree(tmp_path: Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """[project]
name = "aspose-font"
version = "1.0.0"
description = "demo"
""",
        encoding="utf-8",
    )

    init_dir = tmp_path / "src" / "aspose_font"
    init_dir.mkdir(parents=True)
    init_file = init_dir / "__init__.py"
    init_file.write_text('__version__ = "1.0.0"\n', encoding="utf-8")

    set_version_in_tree(tmp_path, "26.10.1")

    assert 'version = "26.10.1"' in pyproject.read_text(encoding="utf-8")
    assert '__version__ = "26.10.1"' in init_file.read_text(encoding="utf-8")


def test_set_version_invalid_pep440(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="not a valid PEP 440"):
        set_version_in_tree(tmp_path, "not-a-valid-tag")


def test_check_version_exists_not_found() -> None:
    # A definitely non-existent version of aspose-font-foss
    try:
        assert check_version_exists("aspose-font-foss", "9999.99.99") is False
    except (urllib.error.URLError, TimeoutError, OSError):
        pytest.skip("Network connection to PyPI not available in this environment")


def test_publish_pypi_dry_run_success(tmp_path: Path) -> None:
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    whl_file = dist_dir / "aspose_font-26.10.1-py3-none-any.whl"
    whl_file.write_bytes(b"dummy")

    with patch("scripts.publish_pypi_release.run_twine_check"):
        exit_code = main(
            [
                "--tag",
                "26.10.1",
                "--dist-dir",
                str(dist_dir),
                "--dry-run",
            ]
        )
        assert exit_code == 0
