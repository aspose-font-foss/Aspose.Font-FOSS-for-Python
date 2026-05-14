"""Bundled pure-Python Brotli facade."""

from __future__ import annotations

from aspose_font._brotli._decode import BrotliDecoder
from aspose_font._brotli._encode import BrotliEncoder


def decompress(data: bytes) -> bytes:
    """Decompress Brotli-compressed data."""
    return BrotliDecoder().decode(data)


def compress(data: bytes, quality: int = 6) -> bytes:
    """Compress bytes with bundled Brotli encoder."""
    return BrotliEncoder(quality=quality).encode(data)
