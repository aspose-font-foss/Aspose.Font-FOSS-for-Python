"""Tests for SPEC-096 meta cleaner behavior."""

from __future__ import annotations

from pathlib import Path

import pytest

from aspose_font import FontCleaner, FontLoader, FontNotSupportedException, FontType, WoffFont
from aspose_font._exceptions import FontParseException
from aspose_font.converter import FontConverter
from aspose_font.ttf.tables.name import NameRecord


def _font_with_extra_metadata(roboto_path: Path):
    font = FontLoader.open(str(roboto_path))
    assert font.ttf_tables.name is not None
    font.set_table_bytes("DSIG", b"signature")
    font.set_table_bytes("FFTM", b"fontforge")
    font.set_table_bytes("meta", b"metadata")
    font.ttf_tables.name.records.append(
        NameRecord(
            platform_id=1,
            encoding_id=0,
            language_id=0,
            name_id=1,
            value="Roboto Mac",
        )
    )
    return font


def test_clean_for_web_strips_tables_and_mac_names(roboto_path: Path):
    font = _font_with_extra_metadata(roboto_path)

    cleaned = FontCleaner.clean_for_web(font)

    assert cleaned.font_type is FontType.TTF
    assert "DSIG" not in cleaned.ttf_tables._raw
    assert "FFTM" not in cleaned.ttf_tables._raw
    assert "meta" not in cleaned.ttf_tables._raw
    assert cleaned.ttf_tables.name is not None
    assert all(record.platform_id != 1 for record in cleaned.ttf_tables.name.records)


def test_clean_for_web_keep_flags_preserve_requested_metadata(roboto_path: Path):
    font = _font_with_extra_metadata(roboto_path)

    cleaned = FontCleaner.clean_for_web(
        font,
        drop_mac_names=False,
        drop_legacy_tables=False,
        drop_metadata_tables=False,
    )

    assert "DSIG" in cleaned.ttf_tables._raw
    assert "FFTM" in cleaned.ttf_tables._raw
    assert "meta" in cleaned.ttf_tables._raw
    assert cleaned.ttf_tables.name is not None
    assert any(record.platform_id == 1 for record in cleaned.ttf_tables.name.records)


def test_clean_for_web_supports_wrapper_fonts(roboto_path: Path):
    font = _font_with_extra_metadata(roboto_path)
    wrapped = FontConverter.convert(font, FontType.WOFF)
    assert isinstance(wrapped, WoffFont)

    cleaned = FontCleaner.clean_for_web(wrapped)

    assert isinstance(cleaned, WoffFont)
    assert "DSIG" not in cleaned.inner_font.ttf_tables._raw
    assert "FFTM" not in cleaned.inner_font.ttf_tables._raw
    assert "meta" not in cleaned.inner_font.ttf_tables._raw
    assert cleaned.inner_font.ttf_tables.name is not None
    assert all(record.platform_id != 1 for record in cleaned.inner_font.ttf_tables.name.records)


def test_clean_for_web_rejects_non_sfnt_fonts(opensans_cff_path: Path):
    font = FontLoader.open(str(opensans_cff_path))

    with pytest.raises(FontNotSupportedException):
        FontCleaner.clean_for_web(font)


def test_cleaned_font_round_trips_without_removed_tables(roboto_path: Path, tmp_path: Path):
    font = _font_with_extra_metadata(roboto_path)
    out_path = tmp_path / "cleaned.ttf"
    out_path.write_bytes(FontCleaner.clean_for_web(font).to_bytes())

    loaded = FontLoader.open(str(out_path))

    assert "DSIG" not in loaded.ttf_tables._raw
    assert "FFTM" not in loaded.ttf_tables._raw
    assert "meta" not in loaded.ttf_tables._raw
    assert loaded.ttf_tables.name is not None
    assert all(record.platform_id != 1 for record in loaded.ttf_tables.name.records)

    with pytest.raises(FontParseException):
        loaded.get_table_bytes("DSIG")
