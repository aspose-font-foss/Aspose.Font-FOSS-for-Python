"""Tests for FontLoader."""

from __future__ import annotations

import io
from pathlib import Path

import pytest

from aspose_font import (
    CffFont,
    EotFont,
    FontLoader,
    FontSourceInfo,
    FontType,
    LoadedFont,
    TtfFont,
    Type1Font,
    UnsupportedFontFormatException,
    Woff2Font,
    WoffFont,
)
from aspose_font._exceptions import FontParseException


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


def _build_minimal_pfb() -> bytes:
    ascii_seg = b"%!PS-AdobeFont-1.0: Test\n"
    return (
        b"\x80\x01"
        + len(ascii_seg).to_bytes(4, "little")
        + ascii_seg
        + b"\x80\x03"
    )


def _build_ttc(*sfnts: bytes) -> bytes:
    offset_table = []
    payload = bytearray()
    current_offset = 12 + len(sfnts) * 4
    for sfnt in sfnts:
        offset_table.append(current_offset)
        payload.extend(sfnt)
        current_offset += len(sfnt)
    return (
        b"ttcf"
        + (1).to_bytes(2, "big")
        + (0).to_bytes(2, "big")
        + len(sfnts).to_bytes(4, "big")
        + b"".join(offset.to_bytes(4, "big") for offset in offset_table)
        + bytes(payload)
    )


class TestLoaderMagicDetection:
    def test_unknown_magic_raises(self):
        with pytest.raises(UnsupportedFontFormatException):
            FontLoader.open(b"\xDE\xAD\xBE\xEF")

    def test_too_short_raises(self):
        with pytest.raises(UnsupportedFontFormatException):
            FontLoader.open(b"\x00")

    def test_empty_raises(self):
        with pytest.raises(UnsupportedFontFormatException):
            FontLoader.open(b"")

    def test_ttf_magic_detected(self):
        font = FontLoader.open(_build_minimal_sfnt(b"\x00\x01\x00\x00"))
        assert isinstance(font, TtfFont)
        assert font.font_type == FontType.TTF

    def test_otf_magic_detected(self):
        font = FontLoader.open(_build_minimal_sfnt(b"OTTO"))
        assert isinstance(font, TtfFont)
        assert font.font_type == FontType.OTF

    def test_woff_magic_detected(self):
        path = Path(__file__).resolve().parents[1] / "testdata" / "saira-extracondensed-semibold.woff"
        font = FontLoader.open(str(path))
        assert isinstance(font, WoffFont)

    def test_woff2_magic_detected(self):
        path = Path(__file__).resolve().parents[1] / "testdata" / "saira-extracondensed-semibold.woff2"
        font = FontLoader.open(str(path))
        assert isinstance(font, Woff2Font)

    def test_pfb_magic_detected(self):
        font = FontLoader.open(_build_minimal_pfb())
        assert isinstance(font, Type1Font)

    def test_pfa_magic_detected(self):
        font = FontLoader.open(b"%!PS-AdobeFont-1.0: Test\n")
        assert isinstance(font, Type1Font)

    def test_cff_magic_detected(self):
        cff_path = Path(__file__).resolve().parents[1] / "testdata" / "OpenSans-Regular.cff"
        font = FontLoader.open(str(cff_path))
        assert isinstance(font, CffFont)

    def test_eot_magic_detected(self):
        path = Path(__file__).resolve().parents[1] / "testdata" / "saira-extracondensed-semibold.eot"
        font = FontLoader.open(str(path))
        assert isinstance(font, EotFont)
        assert font.font_type == FontType.EOT

    def test_eot_extension_shortcut_detected(self, tmp_path: Path):
        eot_path = tmp_path / "test.eot"
        eot_path.write_bytes(_build_minimal_eot(_build_minimal_sfnt(b"\x00\x01\x00\x00")))
        font = FontLoader.open(str(eot_path))
        assert isinstance(font, EotFont)

    def test_ttc_defaults_to_first_face(self):
        ttc = _build_ttc(
            _build_minimal_sfnt(b"\x00\x01\x00\x00"),
            _build_minimal_sfnt(b"OTTO"),
        )

        font = FontLoader.open(ttc)

        assert isinstance(font, TtfFont)
        assert font.font_type == FontType.TTF

    def test_ttc_collection_index_selects_face(self):
        ttc = _build_ttc(
            _build_minimal_sfnt(b"\x00\x01\x00\x00"),
            _build_minimal_sfnt(b"OTTO"),
        )

        font = FontLoader.open(ttc, collection_index=1)

        assert isinstance(font, TtfFont)
        assert font.font_type == FontType.OTF


class TestLoaderSources:
    def test_loader_open_path_ttf(self, tmp_path):
        font_path = tmp_path / "test.ttf"
        font_path.write_bytes(_build_minimal_sfnt(b"\x00\x01\x00\x00"))

        font = FontLoader.open(str(font_path))
        assert isinstance(font, TtfFont)
        assert font.font_type == FontType.TTF

    def test_loader_open_bytes_woff(self):
        path = Path(__file__).resolve().parents[1] / "testdata" / "saira-extracondensed-semibold.woff"
        woff_bytes = path.read_bytes()
        font = FontLoader.open(woff_bytes)
        assert isinstance(font, WoffFont)

    def test_loader_open_stream(self):
        ttf_stream = io.BytesIO(_build_minimal_sfnt(b"\x00\x01\x00\x00"))
        font = FontLoader.open(ttf_stream)
        assert isinstance(font, TtfFont)
        assert font.font_type == FontType.TTF

    def test_loader_open_pathlike(self, tmp_path: Path):
        font_path = tmp_path / "test.ttf"
        font_path.write_bytes(_build_minimal_sfnt(b"\x00\x01\x00\x00"))

        font = FontLoader.open(font_path)

        assert isinstance(font, TtfFont)
        assert font.font_type == FontType.TTF

    def test_loader_open_text_stream_raises(self):
        with pytest.raises(UnsupportedFontFormatException):
            FontLoader.open(io.StringIO("not binary"))

    def test_loader_load_returns_metadata_for_path(self, roboto_path: Path):
        loaded = FontLoader.load(roboto_path)

        assert isinstance(loaded, LoadedFont)
        assert isinstance(loaded.source, FontSourceInfo)
        assert loaded.source.is_path is True
        assert loaded.source.path == str(roboto_path)
        assert loaded.source.size == roboto_path.stat().st_size
        assert loaded.detected_font_type == FontType.TTF
        assert loaded.is_variable is True
        assert loaded.is_static is False
        assert loaded.font.font_name == loaded.font_name

    def test_loader_load_returns_metadata_for_bytes(self, saira_woff_path: Path):
        data = saira_woff_path.read_bytes()

        loaded = FontLoader.load(data)

        assert loaded.source.is_bytes is True
        assert loaded.source.path is None
        assert loaded.source.stream_name is None
        assert loaded.source.label == f"<bytes:{len(data)}>"
        assert loaded.detected_font_type == FontType.WOFF
        assert isinstance(loaded.font, WoffFont)

    def test_loader_load_returns_metadata_for_stream(self):
        stream = io.BytesIO(_build_minimal_sfnt(b"\x00\x01\x00\x00"))
        stream.name = "memory-font.ttf"

        loaded = FontLoader.load(stream)

        assert loaded.source.is_stream is True
        assert loaded.source.stream_name == "memory-font.ttf"
        assert loaded.source.label == "memory-font.ttf"
        assert loaded.detected_font_type == FontType.TTF
        assert loaded.is_static is True
        assert isinstance(loaded.unwrap(), TtfFont)

    def test_loader_load_returns_ttc_metadata(self):
        ttc = _build_ttc(
            _build_minimal_sfnt(b"\x00\x01\x00\x00"),
            _build_minimal_sfnt(b"OTTO"),
        )

        loaded = FontLoader.load(ttc, collection_index=1)

        assert loaded.detected_font_type == FontType.OTF
        assert loaded.source.label == f"<bytes:{len(ttc)}>#1"
        assert loaded.source.collection_index == 1
        assert loaded.source.collection_size == 2

    def test_loader_collection_index_rejected_for_non_ttc(self):
        with pytest.raises(UnsupportedFontFormatException, match="collection_index"):
            FontLoader.open(_build_minimal_sfnt(b"\x00\x01\x00\x00"), collection_index=0)

    def test_loader_ttc_collection_index_out_of_range_raises(self):
        ttc = _build_ttc(_build_minimal_sfnt(b"\x00\x01\x00\x00"))

        with pytest.raises(FontParseException, match="out of range"):
            FontLoader.open(ttc, collection_index=1)


class TestEotValidation:
    def test_eot_short_header_raises(self):
        with pytest.raises(FontParseException, match="Invalid EOT header"):
            FontLoader.open(b"\x00" * 20, font_type=FontType.EOT)

    def test_eot_bad_magic_raises(self):
        payload = bytearray(_build_minimal_eot(_build_minimal_sfnt(b"\x00\x01\x00\x00")))
        payload[34:36] = (0xFFFF).to_bytes(2, "little")
        with pytest.raises(FontParseException, match="Invalid EOT magic"):
            FontLoader.open(bytes(payload), font_type=FontType.EOT)

    def test_eot_bad_sizes_raises(self):
        payload = bytearray(_build_minimal_eot(_build_minimal_sfnt(b"\x00\x01\x00\x00")))
        payload[4:8] = (len(payload) * 2).to_bytes(4, "little")
        with pytest.raises(FontParseException, match="Invalid EOT size fields"):
            FontLoader.open(bytes(payload), font_type=FontType.EOT)

    def test_eot_invalid_inner_sfnt_raises(self):
        payload = _build_minimal_eot(b"not a sfnt")
        with pytest.raises(FontParseException, match="Invalid EOT embedded sfnt"):
            FontLoader.open(payload, font_type=FontType.EOT)


def _build_minimal_eot(sfnt: bytes) -> bytes:
    header = bytearray()
    header.extend((82 + len(sfnt)).to_bytes(4, "little"))
    header.extend(len(sfnt).to_bytes(4, "little"))
    header.extend((0x00020001).to_bytes(4, "little"))
    header.extend((0).to_bytes(4, "little"))
    header.extend(b"\x00" * 10)
    header.extend((1).to_bytes(1, "little"))
    header.extend((0).to_bytes(1, "little"))
    header.extend((400).to_bytes(4, "little"))
    header.extend((0).to_bytes(2, "little"))
    header.extend((0x504C).to_bytes(2, "little"))
    header.extend(b"\x00" * 46)
    assert len(header) == 82
    return bytes(header) + sfnt
