"""Tests for BinaryReader and BinaryWriter (_io.py)."""

import io
import struct

import pytest

from aspose_font._exceptions import FontParseException
from aspose_font._io import BinaryReader, BinaryWriter


class TestBinaryReaderIntegers:
    def test_u16_be(self):
        assert BinaryReader(b"\x00\x01").read_u16() == 1

    def test_u16_le(self):
        assert BinaryReader(b"\x01\x00").read_u16_le() == 1

    def test_i16_negative(self):
        assert BinaryReader(b"\xff\xff").read_i16() == -1

    def test_u8(self):
        assert BinaryReader(b"\xab").read_u8() == 0xAB

    def test_i8_negative(self):
        assert BinaryReader(b"\x80").read_i8() == -128

    def test_u32_be(self):
        data = struct.pack(">I", 0xDEADBEEF)
        assert BinaryReader(data).read_u32() == 0xDEADBEEF

    def test_u32_le(self):
        data = struct.pack("<I", 0xDEADBEEF)
        assert BinaryReader(data).read_u32_le() == 0xDEADBEEF

    def test_u64_be(self):
        data = struct.pack(">Q", 2**40)
        assert BinaryReader(data).read_u64() == 2**40

    def test_i32(self):
        data = struct.pack(">i", -100000)
        assert BinaryReader(data).read_i32() == -100000

    def test_i16_le(self):
        data = struct.pack("<h", -500)
        assert BinaryReader(data).read_i16_le() == -500


class TestBinaryReaderFixedPoint:
    def test_fixed_16_16(self):
        # 0x00018000 = 1.5 in 16.16 fixed point
        data = b"\x00\x01\x80\x00"
        assert BinaryReader(data).read_fixed() == pytest.approx(1.5)

    def test_fixed_negative(self):
        # -1.0 in 16.16: 0xFFFF0000
        data = struct.pack(">i", -65536)
        assert BinaryReader(data).read_fixed() == pytest.approx(-1.0)

    def test_f2dot14_one(self):
        # 0x4000 = 16384 / 16384 = 1.0
        assert BinaryReader(b"\x40\x00").read_f2dot14() == pytest.approx(1.0)

    def test_f2dot14_half(self):
        # 0x2000 = 8192 / 16384 = 0.5
        assert BinaryReader(b"\x20\x00").read_f2dot14() == pytest.approx(0.5)


class TestBinaryReaderSeekTell:
    def test_seek_tell(self):
        r = BinaryReader(b"\x00\x01\x02\x03")
        assert r.tell() == 0
        r.read_u16()
        assert r.tell() == 2
        r.seek(0)
        assert r.read_u16() == 1

    def test_remaining(self):
        r = BinaryReader(b"\x00\x01\x02\x03")
        assert r.remaining() == 4
        r.read_u16()
        assert r.remaining() == 2

    def test_seek_from_end(self):
        r = BinaryReader(b"\x00\x01\x02\x03")
        r.seek(-2, 2)
        assert r.tell() == 2


class TestBinaryReaderStrings:
    def test_read_tag(self):
        assert BinaryReader(b"head").read_tag() == "head"

    def test_read_bytes(self):
        assert BinaryReader(b"\x01\x02\x03").read_bytes(3) == b"\x01\x02\x03"

    def test_read_pascal_string(self):
        # length byte (3) + "abc"
        assert BinaryReader(b"\x03abc").read_pascal_string() == "abc"

    def test_read_cstring(self):
        assert BinaryReader(b"hello\x00rest").read_cstring() == "hello"


class TestBinaryReaderErrors:
    def test_eof_raises_parse_exception(self):
        with pytest.raises(FontParseException):
            BinaryReader(b"\x00").read_u16()

    def test_empty_raises_parse_exception(self):
        with pytest.raises(FontParseException):
            BinaryReader(b"").read_u8()

    def test_read_bytes_eof_raises(self):
        with pytest.raises(FontParseException):
            BinaryReader(b"\x01").read_bytes(4)


class TestBinaryReaderFromStream:
    def test_accepts_bytesio(self):
        stream = io.BytesIO(b"\x00\x05")
        assert BinaryReader(stream).read_u16() == 5

    def test_accepts_rawio(self):
        import os
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"\x00\x07")
            name = f.name
        try:
            with open(name, "rb") as f:
                assert BinaryReader(f).read_u16() == 7
        finally:
            os.unlink(name)

    def test_wraps_non_seekable_stream(self):
        class NonSeekableBytesIO(io.BytesIO):
            def seekable(self) -> bool:
                return False

        stream = NonSeekableBytesIO(b"\x00\x09")
        reader = BinaryReader(stream)
        assert reader.read_u16() == 9
        reader.seek(0)
        assert reader.read_u16() == 9

    def test_rejects_text_stream(self):
        with pytest.raises(FontParseException):
            BinaryReader(io.StringIO("text stream"))


class TestBinaryWriterRoundtrip:
    def test_roundtrip_i16_le(self):
        w = BinaryWriter()
        w.write_i16_le(-300)
        assert BinaryReader(w.to_bytes()).read_i16_le() == -300

    def test_roundtrip_u32(self):
        w = BinaryWriter()
        w.write_u32(0x12345678)
        assert BinaryReader(w.to_bytes()).read_u32() == 0x12345678

    def test_roundtrip_fixed(self):
        w = BinaryWriter()
        w.write_fixed(1.5)
        assert BinaryReader(w.to_bytes()).read_fixed() == pytest.approx(1.5)

    def test_roundtrip_f2dot14(self):
        w = BinaryWriter()
        w.write_f2dot14(0.5)
        assert BinaryReader(w.to_bytes()).read_f2dot14() == pytest.approx(0.5)

    def test_roundtrip_tag(self):
        w = BinaryWriter()
        w.write_tag("cmap")
        assert BinaryReader(w.to_bytes()).read_tag() == "cmap"

    def test_seek_backpatch(self):
        w = BinaryWriter()
        w.write_u32(0)       # placeholder
        w.write_u16(0x1234)
        w.seek(0)
        w.write_u32(0xDEAD)  # back-patch
        data = w.to_bytes()
        r = BinaryReader(data)
        assert r.read_u32() == 0xDEAD
        assert r.read_u16() == 0x1234

    def test_write_padding(self):
        w = BinaryWriter()
        w.write_padding(4)
        assert w.to_bytes() == b"\x00\x00\x00\x00"

    def test_tell(self):
        w = BinaryWriter()
        assert w.tell() == 0
        w.write_u32(0)
        assert w.tell() == 4
