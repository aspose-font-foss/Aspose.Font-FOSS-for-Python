"""Tests for GitHub release notes extraction and body formatting."""

from __future__ import annotations

from pathlib import Path

import pytest

try:
    from scripts.publish_github_release import (
        DEFAULT_EMPTY_RELEASE_NOTES,
        extract_release_notes,
        release_body,
        resolve_changelog_path,
    )
except ImportError:
    pytest.skip("scripts package not available in public clean mirror", allow_module_level=True)


def test_extract_release_notes_from_unreleased(tmp_path: Path) -> None:
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text(
        """# Changelog

## Unreleased

- Feature A was added.
- Bug B was fixed.

## 2026.5.1

- Initial release.
""",
        encoding="utf-8",
    )

    notes = extract_release_notes(changelog, "26.10.1")
    assert "- Feature A was added." in notes
    assert "- Bug B was fixed." in notes
    assert "Initial release." not in notes


def test_extract_release_notes_from_matching_tag(tmp_path: Path) -> None:
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text(
        """# Changelog

## Unreleased

- Something pending.

## 26.10.1

- Released Feature X.

## 2026.5.1

- Initial release.
""",
        encoding="utf-8",
    )

    notes = extract_release_notes(changelog, "26.10.1")
    assert notes == "- Released Feature X."


def test_extract_release_notes_empty_fallback(tmp_path: Path) -> None:
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text(
        """# Changelog

## Unreleased

<!-- no changes -->

## 2026.5.1

- Old release.
""",
        encoding="utf-8",
    )

    notes = extract_release_notes(changelog, "26.10.2")
    assert notes == DEFAULT_EMPTY_RELEASE_NOTES


def test_extract_release_notes_missing_file() -> None:
    notes = extract_release_notes(None, "26.10.2")
    assert notes == DEFAULT_EMPTY_RELEASE_NOTES


def test_release_body_includes_whats_changed() -> None:
    body = release_body(
        tag_name="26.10.1",
        repository_url="https://github.com/aspose-font/aspose-font",
        notes="- New awesome feature",
    )
    assert "## Aspose.Font FOSS for Python 26.10.1" in body
    assert "### What's Changed" in body
    assert "- New awesome feature" in body
    assert "### Included" in body
    assert "### Installation from GitHub" in body


def test_resolve_changelog_path(tmp_path: Path) -> None:
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text("# Changelog\n", encoding="utf-8")
    resolved = resolve_changelog_path(str(changelog))
    assert resolved == changelog
