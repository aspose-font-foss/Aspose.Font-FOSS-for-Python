"""Binary I/O primitives. All struct.pack/unpack calls are isolated here."""

from __future__ import annotations

import io
import struct

from aspose_font._exceptions import FontParseException


class BinaryReader:
    """Wraps a byte source in seekable BytesIO for big-endian font binary parsing."""

    def __init__(self, source: bytes | io.IOBase) -> None:
        if isinstance(source, (bytes, bytearray)):
            self._buf = io.BytesIO(source)
        elif isinstance(source, io.IOBase):
            self._buf = self._wrap_stream(source)
        else:
            raise FontParseException(f"Unsupported source type: {type(source).__name__}")

    @staticmethod
    def _wrap_stream(source: io.IOBase) -> io.BytesIO | io.BufferedReader | io.BufferedRandom:
        if source.seekable():
            if isinstance(source, (io.BufferedReader, io.BufferedRandom, io.BytesIO)):
                return source
            if isinstance(source, io.RawIOBase):
                return io.BufferedReader(source)
            data = source.read()
            if isinstance(data, str):
                raise FontParseException("BinaryReader requires a binary stream, got text stream")
            return io.BytesIO(bytes(data))

        data = source.read()
        if isinstance(data, str):
            raise FontParseException("BinaryReader requires a binary stream, got text stream")
        return io.BytesIO(bytes(data))

    # ------------------------------------------------------------------
    # Position
    # ------------------------------------------------------------------

    def tell(self) -> int:
        return self._buf.tell()

    def seek(self, offset: int, whence: int = 0) -> None:
        self._buf.seek(offset, whence)

    def remaining(self) -> int:
        pos = self._buf.tell()
        self._buf.seek(0, 2)
        end = self._buf.tell()
        self._buf.seek(pos)
        return end - pos

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _unpack(self, fmt: str, size: int) -> tuple:
        data = self._buf.read(size)
        if len(data) < size:
            raise FontParseException(
                f"Unexpected end of data (expected {size} bytes, got {len(data)})",
                offset=self._buf.tell(),
            )
        try:
            return struct.unpack(fmt, data)
        except struct.error as exc:
            raise FontParseException(str(exc), offset=self._buf.tell()) from exc

    # ------------------------------------------------------------------
    # Unsigned integers — big-endian by default
    # ------------------------------------------------------------------

    def read_u8(self) -> int:
        return self._unpack(">B", 1)[0]

    def read_u16(self) -> int:
        return self._unpack(">H", 2)[0]

    def read_u16_le(self) -> int:
        return self._unpack("<H", 2)[0]

    def read_u32(self) -> int:
        return self._unpack(">I", 4)[0]

    def read_u32_le(self) -> int:
        return self._unpack("<I", 4)[0]

    def read_u64(self) -> int:
        return self._unpack(">Q", 8)[0]

    # ------------------------------------------------------------------
    # Signed integers
    # ------------------------------------------------------------------

    def read_i8(self) -> int:
        return self._unpack(">b", 1)[0]

    def read_i16(self) -> int:
        return self._unpack(">h", 2)[0]

    def read_i16_le(self) -> int:
        return self._unpack("<h", 2)[0]

    def read_i32(self) -> int:
        return self._unpack(">i", 4)[0]

    # ------------------------------------------------------------------
    # Fixed-point
    # ------------------------------------------------------------------

    def read_fixed(self) -> float:
        """16.16 fixed-point → float."""
        raw = self._unpack(">i", 4)[0]
        return raw / 65536.0

    def read_f2dot14(self) -> float:
        """2.14 fixed-point → float."""
        raw = self._unpack(">h", 2)[0]
        return raw / 16384.0

    # ------------------------------------------------------------------
    # Bytes and strings
    # ------------------------------------------------------------------

    def read_bytes(self, n: int) -> bytes:
        data = self._buf.read(n)
        if len(data) < n:
            raise FontParseException(
                f"Unexpected end of data (expected {n} bytes, got {len(data)})",
                offset=self._buf.tell(),
            )
        return data

    def read_tag(self) -> str:
        """Read a 4-byte ASCII tag (e.g. 'head', 'cmap')."""
        return self.read_bytes(4).decode("latin-1")

    def read_pascal_string(self) -> str:
        """Read a Pascal-style length-prefixed string."""
        length = self.read_u8()
        return self.read_bytes(length).decode("latin-1")

    def read_cstring(self) -> str:
        """Read a null-terminated C string."""
        chunks: list[bytes] = []
        while True:
            ch = self._buf.read(1)
            if not ch or ch == b"\x00":
                break
            chunks.append(ch)
        return b"".join(chunks).decode("latin-1")


class BinaryWriter:
    """Accumulates bytes for binary font serialization."""

    def __init__(self) -> None:
        self._buf = io.BytesIO()

    # ------------------------------------------------------------------
    # Position and output
    # ------------------------------------------------------------------

    def tell(self) -> int:
        return self._buf.tell()

    def seek(self, offset: int) -> None:
        """Seek to an absolute position for back-patching."""
        self._buf.seek(offset)

    def to_bytes(self) -> bytes:
        return self._buf.getvalue()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _pack(self, fmt: str, v: int | float) -> None:
        self._buf.write(struct.pack(fmt, v))

    # ------------------------------------------------------------------
    # Unsigned integers
    # ------------------------------------------------------------------

    def write_u8(self, v: int) -> None:
        self._pack(">B", v)

    def write_u16(self, v: int) -> None:
        self._pack(">H", v)

    def write_u16_le(self, v: int) -> None:
        self._pack("<H", v)

    def write_u32(self, v: int) -> None:
        self._pack(">I", v)

    def write_u32_le(self, v: int) -> None:
        self._pack("<I", v)

    def write_u64(self, v: int) -> None:
        self._pack(">Q", v)

    # ------------------------------------------------------------------
    # Signed integers
    # ------------------------------------------------------------------

    def write_i8(self, v: int) -> None:
        self._pack(">b", v)

    def write_i16(self, v: int) -> None:
        self._pack(">h", v)

    def write_i16_le(self, v: int) -> None:
        self._pack("<h", v)

    def write_i32(self, v: int) -> None:
        self._pack(">i", v)

    # ------------------------------------------------------------------
    # Fixed-point
    # ------------------------------------------------------------------

    def write_fixed(self, v: float) -> None:
        """16.16 fixed-point."""
        self._pack(">i", round(v * 65536))

    def write_f2dot14(self, v: float) -> None:
        """2.14 fixed-point."""
        self._pack(">h", round(v * 16384))

    # ------------------------------------------------------------------
    # Bytes and strings
    # ------------------------------------------------------------------

    def write_bytes(self, data: bytes | bytearray) -> None:
        self._buf.write(data)

    def write_tag(self, tag: str) -> None:
        """Write a 4-character ASCII tag."""
        self._buf.write(tag.encode("latin-1"))

    def write_padding(self, n: int) -> None:
        """Write n zero bytes."""
        self._buf.write(b"\x00" * n)
