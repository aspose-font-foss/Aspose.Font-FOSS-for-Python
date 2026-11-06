"""Tests for SPEC-004 CFF parsing."""

from __future__ import annotations

from pathlib import Path

import pytest

from aspose_font import CffFont, FontLoader, FontType, TtfFont
from aspose_font._exceptions import FontParseException
from aspose_font._io import BinaryReader
from aspose_font.cff.charset import CffCharset, resolve_sid
from aspose_font.cff.dict_ import CffDict, TopDictOp
from aspose_font.cff.encoding import CffEncoding
from aspose_font.cff.index import CffIndex


def test_cff_loads(opensans_cff):
    assert isinstance(opensans_cff, CffFont)


def test_cff_font_name_nonempty(opensans_cff):
    assert opensans_cff.font_name.strip() != ""


def test_cff_num_glyphs_positive(opensans_cff):
    assert opensans_cff.num_glyphs > 0


def test_cff_charstring_zero_is_bytes(opensans_cff):
    assert isinstance(opensans_cff.charstrings[0], bytes)


def test_cff_charset_resolves_gid1(opensans_cff):
    name = opensans_cff.charset.name_for(1)
    assert isinstance(name, str)
    assert name.strip() != ""


def _wrap_otf_with_cff(cff_data: bytes) -> bytes:
    head = bytes(12) + (0x5F0F3CF5).to_bytes(4, "big") + bytes(54 - 16)
    maxp = (0x00010000).to_bytes(4, "big") + (1).to_bytes(2, "big") + bytes(26)

    tables = [
        (b"CFF ", cff_data),
        (b"head", head),
        (b"maxp", maxp),
    ]

    num_tables = len(tables)
    offset_table = (
        b"OTTO"
        + num_tables.to_bytes(2, "big")
        + (0).to_bytes(2, "big")
        + (0).to_bytes(2, "big")
        + (0).to_bytes(2, "big")
    )

    directory = bytearray()
    payload = bytearray()
    offset = 12 + 16 * num_tables
    for tag, blob in tables:
        directory.extend(tag)
        directory.extend((0).to_bytes(4, "big"))
        directory.extend(offset.to_bytes(4, "big"))
        directory.extend(len(blob).to_bytes(4, "big"))
        payload.extend(blob)
        offset += len(blob)

    return bytes(offset_table + directory + payload)


def _extract_embedded_cff(cff_wrapper: bytes) -> bytes:
    marker = b"StartData\n"
    pos = cff_wrapper.find(marker)
    if pos < 0:
        return cff_wrapper
    return cff_wrapper[pos + len(marker) :]


def test_otf_embedded_cff_available(opensans_cff_path: Path):
    otf_data = _wrap_otf_with_cff(opensans_cff_path.read_bytes())
    font = FontLoader.open(otf_data)
    assert isinstance(font, TtfFont)
    assert font.cff_font is not None
    assert isinstance(font.cff_font, CffFont)


def test_cff_truncated_raises(opensans_cff_path: Path):
    payload = _extract_embedded_cff(opensans_cff_path.read_bytes())
    with pytest.raises(FontParseException):
        FontLoader.open(payload[:40], font_type=FontType.CFF)


def test_cff_index_empty():
    empty = CffIndex.from_reader(BinaryReader(b"\x00\x00"))
    assert len(empty) == 0


def test_dict_integer_encoding():
    # 139 -> 0, 140 -> 1, 21 -> operator, thus op 21 has [0, 1]
    d = CffDict.from_bytes(bytes([139, 140, 21]))
    assert d.get(21) == [0, 1]


def test_dict_real_encoding():
    # 30 1.5F then operator 21
    d = CffDict.from_bytes(bytes([30, 0x1A, 0x5F, 21]))
    vals = d.get(21)
    assert vals is not None
    assert vals[0] == pytest.approx(1.5)


def test_sid_resolution_standard():
    assert resolve_sid(1, CffIndex([])) == "space"
    assert resolve_sid(228, CffIndex([])) == "zcaron"
    assert resolve_sid(390, CffIndex([])) == "Semibold"


def test_sid_resolution_custom():
    idx = CffIndex([b"custom-name"])
    assert resolve_sid(391, idx) == "custom-name"


def test_builtin_standard_encoding_uses_standard_table():
    charset = CffCharset([".notdef", "A", "space", "germandbls"])
    enc = CffEncoding.standard(charset)
    assert int(enc.unicode_to_gid(65)) == 1
    assert int(enc.unicode_to_gid(32)) == 2
    assert int(enc.unicode_to_gid(249)) == 3


def test_builtin_expert_encoding_uses_expert_table():
    charset = CffCharset([".notdef", "oneoldstyle", "Thornsmall"])
    enc = CffEncoding.expert(charset)
    assert int(enc.unicode_to_gid(49)) == 1
    assert int(enc.unicode_to_gid(251)) == 2


def test_supplemental_encoding_resolves_custom_sid():
    # format 0 + supplemental: code 65 -> SID 391 (first entry in String INDEX)
    data = bytes([0x80, 0x00, 0x01, 65, 0x01, 0x87])
    r = BinaryReader(data)
    charset = CffCharset([".notdef", "custom-name"])
    string_index = CffIndex([b"custom-name"])
    enc = CffEncoding.from_reader(r, num_glyphs=2, charset=charset, string_index=string_index)
    assert int(enc.unicode_to_gid(65)) == 1


def test_dict_to_bytes_roundtrip_preserves_unknown_ops():
    raw = bytes([139, 247, 92, 21, 141, 12, 34])
    d = CffDict.from_bytes(raw)
    out = d.to_bytes()
    parsed = CffDict.from_bytes(out)
    assert parsed.get(21) == [0, 200]
    assert parsed.get((12, 34)) == [2]


def test_dict_to_bytes_serializes_top_dict_operator():
    d = CffDict()
    d.set(TopDictOp.CHARSTRINGS, [1234])
    out = d.to_bytes()
    parsed = CffDict.from_bytes(out)
    assert parsed.get(TopDictOp.CHARSTRINGS) == [1234]
