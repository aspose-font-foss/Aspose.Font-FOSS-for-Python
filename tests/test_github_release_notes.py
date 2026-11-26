"""Tests for GitHub release notes extraction and body formatting."""

from __future__ import annotations

from pathlib import Path

import pytest

try:
    from scripts.publish_github_release import (
        DEFAULT_EMPTY_RELEASE_NOTES,
        extract_git_commits,
        extract_release_notes,
        find_previous_tag,
        release_body,
        resolve_changelog_path,
        resolve_release_notes,
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
    assert "### Installation from PyPI" in body
    assert "### Installation from GitHub" in body


def test_resolve_changelog_path(tmp_path: Path) -> None:
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text("# Changelog\n", encoding="utf-8")
    resolved = resolve_changelog_path(str(changelog))
    assert resolved == changelog

def test_find_previous_tag() -> None:
    tags = ["2026.5.6", "26.10.1", "26.10.2", "26.10.7", "26.10.8"]
    assert find_previous_tag("26.10.8", tags) == "26.10.7"
    assert find_previous_tag("26.10.9", tags) == "26.10.8"
    assert find_previous_tag("26.10.1", tags) == "2026.5.6"
    assert find_previous_tag("2026.5.6", tags) is None
    assert find_previous_tag("26.10.8", []) is None


def test_resolve_release_notes_prefers_explicit_tag(tmp_path: Path) -> None:
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text(
        """# Changelog

## Unreleased
- Pending feature

## 26.10.8
- Delivered FONT-475
- Delivered FONT-474
""",
        encoding="utf-8",
    )
    notes = resolve_release_notes(
        tag_name="26.10.8",
        changelog_path=changelog,
        existing_tags=["26.10.7"],
    )
    assert "- Delivered FONT-475" in notes
    assert "- Delivered FONT-474" in notes
    assert "Pending feature" not in notes


def test_resolve_release_notes_does_not_leak_unreleased_when_zero_commits(tmp_path: Path) -> None:
    # Simulates the bug case: changelog has ancient items in ## Unreleased,
    # but git has 0 commits between tag and prev_tag.
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text(
        """# Changelog

## Unreleased
- Ancient item from previous release
""",
        encoding="utf-8",
    )
    # Using real repo where 26.10.9 and 26.10.8 point to same commit (0 commits)
    notes = resolve_release_notes(
        tag_name="26.10.9",
        changelog_path=changelog,
        existing_tags=["26.10.7", "26.10.8"],
    )
    assert notes == DEFAULT_EMPTY_RELEASE_NOTES
    assert "Ancient item from previous release" not in notes


def test_extract_git_commits(monkeypatch: pytest.MonkeyPatch) -> None:
    # Test commit message extraction, formatting, and filtering independently of git clone depth
    fake_git_log = (
        "feat(FONT-475): CLI sbix Emoji Dump Command (sbix-dump)\n"
        "feat(FONT-465): Pure-Python OpenType GDEF Table Parser\n"
        "release 26.10.8\n"
        "update version to 26.10.8\n"
    )

    class FakeProcessResult:
        stdout = fake_git_log

    monkeypatch.setattr("subprocess.run", lambda *args, **kwargs: FakeProcessResult())
    commits = extract_git_commits("26.10.7", "26.10.8")
    assert any("FONT-475" in c for c in commits)
    assert any("FONT-465" in c for c in commits)
    assert not any("release" in c.lower() for c in commits)
    assert not any("update version" in c.lower() for c in commits)

    class EmptyProcessResult:
        stdout = ""

    monkeypatch.setattr("subprocess.run", lambda *args, **kwargs: EmptyProcessResult())
    empty = extract_git_commits("26.10.8", "26.10.9")
    assert empty == []


def test_extract_git_commits_real_repo_integration() -> None:
    # In real repo, 26.10.8 and 26.10.9 point to the same commit (0 commits between them)
    empty = extract_git_commits("26.10.8", "26.10.9")
    assert empty == []

def test_resolve_release_notes_falls_back_to_head_when_tag_not_yet_created(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        class FakeResult:
            pass
        res = FakeResult()
        if 'rev-parse' in cmd:
            res.returncode = 1 if '26.11.2' in cmd else 0
            res.stdout = ''
            return res
        if 'log' in cmd:
            res.returncode = 0
            res.stdout = 'feat(FONT-495): New feature\n'
            return res
        res.returncode = 0
        res.stdout = ''
        return res

    monkeypatch.setattr('subprocess.run', fake_run)
    notes = resolve_release_notes(
        tag_name='26.11.2',
        existing_tags=['26.11.1'],
    )
    assert '- feat(FONT-495): New feature' in notes
    assert any('26.11.1..HEAD' in ' '.join(c) for c in calls if 'log' in c)

def test_resolve_release_notes_prefers_unreleased_when_commits_exist(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text(
        """# Changelog

## Unreleased
- Curated feature from agent

## 26.11.1
- Previous feature
""",
        encoding="utf-8",
    )

    fake_git_log = "feat(FONT-999): Raw commit title\n"

    class FakeProcessResult:
        stdout = fake_git_log
        returncode = 0

    monkeypatch.setattr("subprocess.run", lambda *args, **kwargs: FakeProcessResult())

    notes = resolve_release_notes(
        tag_name="26.11.2",
        changelog_path=changelog,
        existing_tags=["26.11.1"],
    )
    assert "- Curated feature from agent" in notes
    assert "Raw commit title" not in notes


def test_resolve_release_notes_falls_back_to_commits_when_unreleased_empty(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text(
        """# Changelog

## Unreleased
<!-- no changes -->

## 26.11.1
- Previous feature
""",
        encoding="utf-8",
    )

    fake_git_log = "feat(FONT-999): Raw commit title\n"

    class FakeProcessResult:
        stdout = fake_git_log
        returncode = 0

    monkeypatch.setattr("subprocess.run", lambda *args, **kwargs: FakeProcessResult())

    notes = resolve_release_notes(
        tag_name="26.11.2",
        changelog_path=changelog,
        existing_tags=["26.11.1"],
    )
    assert "- feat(FONT-999): Raw commit title" in notes

