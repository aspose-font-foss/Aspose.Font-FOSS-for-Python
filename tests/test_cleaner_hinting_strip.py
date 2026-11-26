"""Tests for hinting bytecode stripping in FontCleaner (FONT-537)."""

from __future__ import annotations

from pathlib import Path

from aspose_font import FontCleaner, FontLoader


def test_clean_for_web_strips_hinting_tables(roboto_path: Path) -> None:
    """Validate that fpgm and prep are absent after cleaning with default flags."""
    font = FontLoader.open(str(roboto_path))

    assert "fpgm" in font.ttf_tables._raw
    assert "prep" in font.ttf_tables._raw

    cleaned = FontCleaner.clean_for_web(font)

    assert "fpgm" not in cleaned.ttf_tables._raw
    assert "prep" not in cleaned.ttf_tables._raw


def test_clean_for_web_keeps_hinting_tables(roboto_path: Path) -> None:
    """Validate that setting drop_hinting_tables=False preserves those tables."""
    font = FontLoader.open(str(roboto_path))

    cleaned = FontCleaner.clean_for_web(font, drop_hinting_tables=False)

    assert "fpgm" in cleaned.ttf_tables._raw
    assert "prep" in cleaned.ttf_tables._raw
