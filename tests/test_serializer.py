"""Tests for SPEC-008 font serialization."""

from __future__ import annotations

from pathlib import Path

import pytest

from aspose_font import CffFont, EotFont, FontLoader, FontType, Type1Font
from aspose_font._io import BinaryReader
from aspose_font.converter import FontConverter
from aspose_font.serializer import CffSerializer, TtfSerializer


@pytest.fixture(scope="session")
def opensans_pfb_path(testdata_dir: Path) -> Path:
    return testdata_dir / "OpenSans-Regular.pfb"


@pytest.fixture(scope="session")
def arial_pfa_path(testdata_dir: Path) -> Path:
    return testdata_dir / "Arial.pfa"


def test_ttf_save_roundtrip(tmp_path: Path, roboto_path: Path):
    font = FontLoader.open(str(roboto_path))
    out_path = tmp_path / "out.ttf"
    font.save(str(out_path))
    loaded = FontLoader.open(str(out_path))
    assert loaded.num_glyphs == font.num_glyphs
    assert loaded.font_name == font.font_name


def test_ttf_checksum_adjustment(roboto):
    data = roboto.to_bytes()
    assert _sfnt_checksum(data) == 0xB1B0AFBA


def test_ttf_table_count_preserved(roboto):
    before = len(roboto.ttf_tables._raw)
    after = FontLoader.open(roboto.to_bytes())
    assert len(after.ttf_tables._raw) == before


def test_ttf_name_mutation_is_serialized(roboto_path: Path):
    font = FontLoader.open(str(roboto_path))
    assert font.ttf_tables.name is not None
    target = next((r for r in font.ttf_tables.name.records if r.name_id == 4), None)
    assert target is not None
    target.value = "Serializer Mutation Font"

    reloaded = FontLoader.open(font.to_bytes())
    assert reloaded.font_name == "Serializer Mutation Font"


def test_cff_save_roundtrip(opensans_cff):
    data = opensans_cff.to_bytes(FontType.CFF)
    reloaded = FontLoader.open(data, font_type=FontType.CFF)
    assert isinstance(reloaded, CffFont)
    assert reloaded.font_name == opensans_cff.font_name
    assert reloaded.num_glyphs == opensans_cff.num_glyphs


def test_cff_top_dict_mutation_is_serialized(opensans_cff_path: Path):
    font = FontLoader.open(str(opensans_cff_path))
    assert isinstance(font, CffFont)
    font._top_dict.full_name = "Changed CFF Name"
    data = font.to_bytes(FontType.CFF)
    reloaded = FontLoader.open(data, font_type=FontType.CFF)
    assert isinstance(reloaded, CffFont)
    assert reloaded.font_name == "Changed CFF Name"


def test_cff_charset_preserved_on_roundtrip(opensans_cff_path: Path):
    font = FontLoader.open(str(opensans_cff_path))
    assert isinstance(font, CffFont)
    before = [font.charset.name_for(i) for i in range(min(64, font.num_glyphs))]
    reloaded = FontLoader.open(font.to_bytes(FontType.CFF), font_type=FontType.CFF)
    assert isinstance(reloaded, CffFont)
    after = [reloaded.charset.name_for(i) for i in range(min(64, reloaded.num_glyphs))]
    assert after == before


def test_type1_pfb_roundtrip(opensans_pfb_path: Path):
    font = FontLoader.open(str(opensans_pfb_path))
    assert isinstance(font, Type1Font)
    data = font.to_bytes(FontType.TYPE1)
    reloaded = FontLoader.open(data)
    assert isinstance(reloaded, Type1Font)
    assert reloaded.num_glyphs == font.num_glyphs


def test_type1_pfb_roundtrip_is_stable(opensans_pfb_path: Path):
    font = FontLoader.open(str(opensans_pfb_path))
    assert isinstance(font, Type1Font)

    for _ in range(50):
        reloaded = FontLoader.open(font.to_bytes(FontType.TYPE1))
        assert isinstance(reloaded, Type1Font)
        assert reloaded.num_glyphs == font.num_glyphs


def test_type1_header_mutation_is_serialized(opensans_pfb_path: Path):
    font = FontLoader.open(str(opensans_pfb_path))
    assert isinstance(font, Type1Font)
    font._font_data.font_name = "ChangedType1Name"
    data = font.to_bytes(FontType.TYPE1)
    reloaded = FontLoader.open(data)
    assert isinstance(reloaded, Type1Font)
    assert reloaded.font_name == "ChangedType1Name"


def test_type1_pfa_roundtrip_ascii(arial_pfa_path: Path):
    font = FontLoader.open(str(arial_pfa_path))
    assert isinstance(font, Type1Font)
    data = font.to_bytes(FontType.TYPE1_PFA)
    assert data.startswith(b"%!PS")
    start = data.find(b"eexec")
    end = data.find(b"cleartomark", start + 5)
    assert start > 0 and end > start
    hex_region = data[start + 5 : end]
    filtered = b"".join(ch.to_bytes(1, "big") for ch in hex_region if ch not in b" \t\r\n")
    assert filtered
    assert all((48 <= ch <= 57) or (65 <= ch <= 70) or (97 <= ch <= 102) for ch in filtered)


def test_woff_save_roundtrip(saira_woff):
    data = saira_woff.to_bytes()
    reloaded = FontLoader.open(data, font_type=FontType.WOFF)
    assert reloaded.font_name == saira_woff.font_name


def test_woff2_save_roundtrip(saira_woff2):
    data = saira_woff2.to_bytes()
    reloaded = FontLoader.open(data, font_type=FontType.WOFF2)
    assert reloaded.font_name == saira_woff2.font_name


def test_eot_save_roundtrip(saira_eot):
    data = saira_eot.to_bytes()
    reloaded = FontLoader.open(data, font_type=FontType.EOT)
    assert isinstance(reloaded, EotFont)
    assert reloaded.font_name == saira_eot.font_name
    assert reloaded.num_glyphs > 0


def test_ttf_to_eot_to_bytes_roundtrip(roboto):
    eot = FontConverter.convert(roboto, FontType.EOT)
    assert isinstance(eot, EotFont)
    data = eot.to_bytes(FontType.EOT)
    reloaded = FontLoader.open(data, font_type=FontType.EOT)
    assert isinstance(reloaded, EotFont)
    assert reloaded.num_glyphs == roboto.num_glyphs


def test_otf_to_eot_to_bytes_roundtrip():
    otf = FontLoader.open(_build_minimal_sfnt(b"OTTO"))
    eot = FontConverter.convert(otf, FontType.EOT)
    assert isinstance(eot, EotFont)
    reloaded = FontLoader.open(eot.to_bytes(), font_type=FontType.EOT)
    assert isinstance(reloaded, EotFont)
    assert reloaded.inner_font.font_type == FontType.OTF


def test_head_to_bytes_length(roboto):
    head = roboto.ttf_tables.head
    assert head is not None
    assert len(head.to_bytes()) == 54


def test_table_checksum_known_value():
    data = b"\x00\x00\x00\x01\x00\x00\x00\x02"
    assert TtfSerializer._compute_table_checksum(data) == 3


def test_cff_encode_integer_compact():
    assert CffSerializer._encode_integer(100) == bytes([239])


def test_cff_encode_integer_two_byte():
    assert CffSerializer._encode_integer(1000) == bytes([250, 124])


def _sfnt_checksum(data: bytes) -> int:
    padded = data + (b"\x00" * ((4 - (len(data) % 4)) % 4))
    total = 0
    for i in range(0, len(padded), 4):
        total = (total + int.from_bytes(padded[i : i + 4], "big")) & 0xFFFFFFFF
    return total


def _head_checksum_adjustment(data: bytes) -> int:
    rr = BinaryReader(data)
    rr.read_u32()
    num_tables = rr.read_u16()
    rr.read_u16()
    rr.read_u16()
    rr.read_u16()
    for _ in range(num_tables):
        tag = rr.read_tag()
        rr.read_u32()
        offset = rr.read_u32()
        rr.read_u32()
        if tag == "head":
            return int.from_bytes(data[offset + 8 : offset + 12], "big")
    return 0


def _build_minimal_sfnt(version: bytes) -> bytes:
    head = bytes(12) + (0x5F0F3CF5).to_bytes(4, "big") + bytes(54 - 16)
    maxp = (0x00010000).to_bytes(4, "big") + (1).to_bytes(2, "big") + bytes(26)
    num_tables = 2
    offset_table = (
        version
        + num_tables.to_bytes(2, "big")
        + (0).to_bytes(2, "big")
        + (0).to_bytes(2, "big")
        + (0).to_bytes(2, "big")
    )
    head_offset = 12 + num_tables * 16
    maxp_offset = head_offset + len(head)
    directory = (
        b"head"
        + (0).to_bytes(4, "big")
        + head_offset.to_bytes(4, "big")
        + len(head).to_bytes(4, "big")
        + b"maxp"
        + (0).to_bytes(4, "big")
        + maxp_offset.to_bytes(4, "big")
        + len(maxp).to_bytes(4, "big")
    )
    return offset_table + directory + head + maxp
