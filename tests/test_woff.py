"""Tests for WOFF/WOFF2 loading and round-trips."""

from __future__ import annotations

from pathlib import Path
from time import perf_counter

import pytest

import aspose_font.woff.woff2 as woff2
from aspose_font import FontLoader, FontType, Woff2Font, WoffFont
from aspose_font._brotli import compress as brotli_compress
from aspose_font._brotli import decompress as brotli_decompress
from aspose_font._io import BinaryReader
from aspose_font.converter import FontConverter
from aspose_font.woff.woff2 import _parse_woff2_directory

_STANDARDS_WOFF2 = (
    "lora-v16-latin-regular.woff2",
    "merriweather-v22-latin-regular.woff2",
    "roboto-v20-latin_cyrillic-regular.woff2",
)


def _extract_woff2_compressed_block(blob: bytes) -> bytes:
    r = BinaryReader(blob)
    r.read_u32()  # signature
    r.read_u32()  # flavor
    r.read_u32()  # length
    num_tables = r.read_u16()
    r.read_u16()  # reserved
    r.read_u32()  # totalSfntSize
    total_compressed_size = r.read_u32()
    r.read_u16()  # majorVersion
    r.read_u16()  # minorVersion
    r.read_u32()  # metaOffset
    r.read_u32()  # metaLength
    r.read_u32()  # metaOrigLength
    r.read_u32()  # privOffset
    r.read_u32()  # privLength
    _parse_woff2_directory(r, num_tables)
    return r.read_bytes(total_compressed_size)


def _parse_woff2_fixture_parts(blob: bytes) -> tuple[list[woff2._Woff2TableEntry], bytes]:
    r = BinaryReader(blob)
    r.read_u32()  # signature
    r.read_u32()  # flavor
    r.read_u32()  # length
    num_tables = r.read_u16()
    r.read_u16()  # reserved
    r.read_u32()  # totalSfntSize
    total_compressed_size = r.read_u32()
    r.read_u16()  # majorVersion
    r.read_u16()  # minorVersion
    r.read_u32()  # metaOffset
    r.read_u32()  # metaLength
    r.read_u32()  # metaOrigLength
    r.read_u32()  # privOffset
    r.read_u32()  # privLength
    entries = _parse_woff2_directory(r, num_tables)
    compressed = r.read_bytes(total_compressed_size)
    return entries, brotli_decompress(compressed)


def _mutate_transformed_glyf_payload(payload: bytes, entries: list[woff2._Woff2TableEntry]) -> bytes:
    pos = 0
    mutated = bytearray(payload)
    for entry in entries:
        length = entry.transform_length if entry.transformed else entry.orig_length
        end = pos + length
        if entry.tag == "glyf" and entry.transformed:
            mutated[pos + 5] ^= 0x01  # corrupt numGlyphs field in transformed header
            return bytes(mutated)
        pos = end
    raise AssertionError("No transformed glyf table found")


def test_woff_loads(saira_woff):
    assert isinstance(saira_woff, WoffFont)


def test_woff_font_name_nonempty(saira_woff):
    assert saira_woff.font_name != ""


def test_woff_font_type(saira_woff):
    assert saira_woff.font_type == FontType.WOFF


def test_woff_to_bytes_signature(saira_woff):
    assert saira_woff.to_bytes().startswith(b"wOFF")


def test_woff_roundtrip(saira_woff):
    blob = saira_woff.to_bytes()
    rt = FontLoader.open(blob)
    assert isinstance(rt, WoffFont)
    assert rt.font_name == saira_woff.font_name


def test_woff2_loads(saira_woff2):
    assert isinstance(saira_woff2, Woff2Font)


def test_woff2_font_name_nonempty(saira_woff2):
    assert saira_woff2.font_name != ""


def test_woff2_font_type(saira_woff2):
    assert saira_woff2.font_type == FontType.WOFF2


@pytest.mark.parametrize("fixture_name", _STANDARDS_WOFF2)
def test_woff2_standards_fixtures_load(fixture_name: str):
    font = FontLoader.open(str(Path("testdata/Woff/Standards") / fixture_name))
    assert isinstance(font, Woff2Font)
    assert font.font_name
    assert font.num_glyphs > 0


def test_woff2_brotli_decompresses(saira_woff2_path):
    comp = _extract_woff2_compressed_block(saira_woff2_path.read_bytes())
    payload = brotli_decompress(comp)
    assert len(payload) > 12
    assert int.from_bytes(payload[4:6], "big") > 0


def test_woff2_roundtrip(saira_woff2):
    blob = saira_woff2.to_bytes()
    rt = FontLoader.open(blob)
    assert isinstance(rt, Woff2Font)
    assert rt.font_name == saira_woff2.font_name


def test_woff2_standards_fixture_roundtrip():
    source = FontLoader.open("testdata/Woff/Standards/roboto-v20-latin_cyrillic-regular.woff2")
    blob = source.to_bytes()
    rt = FontLoader.open(blob)
    assert isinstance(rt, Woff2Font)
    assert rt.font_name == source.font_name
    assert rt.num_glyphs == source.num_glyphs


def test_woff2_project_generated_roundtrip():
    source = FontLoader.open("testdata/Fonts/Roboto-Regular.ttf")
    converted = FontConverter.convert(source, FontType.WOFF2)
    blob = converted.to_bytes()
    rt = FontLoader.open(blob)
    assert isinstance(rt, Woff2Font)
    assert rt.font_name == source.font_name
    assert rt.num_glyphs == source.num_glyphs


def test_brotli_decompress_empty():
    assert brotli_decompress(b"") == b""


def test_brotli_roundtrip():
    payload = b"font-roundtrip-test" * 5
    assert brotli_decompress(brotli_compress(payload)) == payload


def test_woff2_rejects_malformed_brotli_stream():
    with pytest.raises(woff2.FontParseException, match="WOFF2 Brotli decompression failed"):
        brotli_decompress(b"\xff")


def test_woff2_rejects_malformed_transformed_glyf_stream():
    blob = Path("testdata/Woff/Standards/merriweather-v22-latin-regular.woff2").read_bytes()
    entries, payload = _parse_woff2_fixture_parts(blob)
    with pytest.raises(woff2.FontParseException, match="WOFF2 glyf transform failed: malformed transformed stream"):
        woff2._split_woff2_table_payload(_mutate_transformed_glyf_payload(payload, entries), entries)


def test_woff2_standards_decode_encode_performance_smoke():
    start = perf_counter()
    for fixture_name in _STANDARDS_WOFF2:
        FontLoader.open(str(Path("testdata/Woff/Standards") / fixture_name))
    decode_elapsed = perf_counter() - start

    source = FontLoader.open("testdata/Fonts/Roboto-Regular.ttf")
    start = perf_counter()
    converted = FontConverter.convert(source, FontType.WOFF2)
    converted.to_bytes()
    encode_elapsed = perf_counter() - start

    assert decode_elapsed < 5.0
    assert encode_elapsed < 2.0
