"""Bundled Brotli encoder for FONT-7."""

from __future__ import annotations

from aspose_font._exceptions import FontParseException


class _BitWriter:
    """LSB-first bit writer."""

    def __init__(self) -> None:
        self._acc = 0
        self._nbits = 0
        self._buf = bytearray()

    def write_bits(self, value: int, n: int) -> None:
        mask = (1 << n) - 1
        v = value & mask
        self._acc |= v << self._nbits
        self._nbits += n
        while self._nbits >= 8:
            self._buf.append(self._acc & 0xFF)
            self._acc >>= 8
            self._nbits -= 8

    def flush(self) -> bytes:
        if self._nbits > 0:
            self._buf.append(self._acc & 0xFF)
            self._acc = 0
            self._nbits = 0
        return bytes(self._buf)

    def align_to_byte(self) -> None:
        if self._nbits == 0:
            return
        self.write_bits(0, 8 - self._nbits)

    def write_bytes(self, data: bytes) -> None:
        self.align_to_byte()
        self._buf.extend(data)


class BrotliEncoder:
    """Encoder for repository WOFF2 workflows."""

    def __init__(self, quality: int = 6) -> None:
        self._quality = max(0, min(11, int(quality)))

    def encode(self, data: bytes) -> bytes:
        if not data:
            # Empty-stream Brotli payload.
            return bytes.fromhex("a101")
        if len(data) > 0x7FFFFFFF:
            raise FontParseException("WOFF2 Brotli compression failed")

        w = _BitWriter()
        # Encode WBITS=22 (valid generic window, See ADR-008 MVP).
        w.write_bits(1, 1)
        w.write_bits(5, 3)

        pos = 0
        while pos < len(data):
            # Uncompressed meta-block max length with MNIBBLES=6.
            chunk = data[pos : pos + ((1 << 24))]
            pos += len(chunk)
            self._emit_uncompressed_metablock(w, chunk=chunk, is_last=False)

        # Terminate stream with an empty last meta-block.
        w.write_bits(1, 1)  # ISLAST
        w.write_bits(1, 1)  # ISEMPTY
        return w.flush()

    def _emit_uncompressed_metablock(self, w: _BitWriter, chunk: bytes, is_last: bool) -> None:
        if is_last:
            raise FontParseException("WOFF2 Brotli compression failed")
        if not chunk:
            return

        mlen_minus_1 = len(chunk) - 1
        mnibbles = max(4, (mlen_minus_1.bit_length() + 3) // 4)
        if mnibbles > 6:
            raise FontParseException("WOFF2 Brotli compression failed")

        # ISLAST
        w.write_bits(0, 1)
        # MNIBBLES code: 4->0, 5->1, 6->2
        w.write_bits(mnibbles - 4, 2)
        # MLEN - 1
        w.write_bits(mlen_minus_1, mnibbles * 4)
        # ISUNCOMPRESSED
        w.write_bits(1, 1)
        # Uncompressed payload is byte-aligned.
        w.write_bytes(chunk)
