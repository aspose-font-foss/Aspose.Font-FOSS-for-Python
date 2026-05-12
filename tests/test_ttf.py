"""Tests for SPEC-002 TTF/OTF binary parsing."""

from __future__ import annotations

import pytest

from aspose_font import FontLoader, TtfFont
from aspose_font._exceptions import FontParseException


def test_ttf_loads(roboto):
    assert isinstance(roboto, TtfFont)


def test_ttf_font_name(roboto):
    assert isinstance(roboto.font_name, str)
    assert roboto.font_name.strip() != ""


def test_ttf_units_per_em(roboto):
    # The provided Roboto variable font test file uses UPM=2048.
    assert roboto.metrics.units_per_em == 2048


def test_ttf_num_glyphs_positive(roboto):
    assert roboto.num_glyphs > 0


def test_ttf_encoding_latin_a(roboto):
    assert roboto.encoding.unicode_to_gid(0x41).value > 0


def test_ttf_head_table_magic(roboto):
    assert roboto.ttf_tables.head is not None
    assert roboto.ttf_tables.head.magic == 0x5F0F3CF5


def test_ttf_head_to_bytes_length(roboto):
    assert roboto.ttf_tables.head is not None
    assert len(roboto.ttf_tables.head.to_bytes()) == 54


def test_ttf_get_table_bytes_cmap(roboto):
    assert roboto.get_table_bytes("cmap").startswith(b"\x00\x00")


def test_ttf_unknown_table_preserved(roboto):
    roboto.set_table_bytes("ZZZZ", b"test")
    assert roboto.get_table_bytes("ZZZZ") == b"test"


def test_ttf_corrupt_raises(roboto_path):
    data = roboto_path.read_bytes()[:128]
    with pytest.raises(FontParseException):
        FontLoader.open(data)
