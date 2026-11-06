"""Type 1 eexec and charstring cipher helpers."""

from __future__ import annotations

import os


def eexec_decrypt(data: bytes, key: int = 55665) -> bytes:
    """Decrypt eexec stream and drop the default 4-byte random prefix."""
    r = key
    out = bytearray()
    for i, c in enumerate(data):
        plain = (c ^ (r >> 8)) & 0xFF
        r = ((c + r) * 52845 + 22719) & 0xFFFF
        if i >= 4:
            out.append(plain)
    return bytes(out)


def eexec_encrypt(
    data: bytes,
    key: int = 55665,
    len_iv: int = 4,
    prefix: bytes | None = None,
) -> bytes:
    """Encrypt bytes using the Type 1 cipher with random lenIV prefix."""
    if prefix is not None and len(prefix) != len_iv:
        raise ValueError("Type 1 encryption prefix length must match lenIV")

    r = key
    out = bytearray()
    iv = os.urandom(len_iv) if prefix is None else prefix
    for c in iv:
        enc = (c ^ (r >> 8)) & 0xFF
        r = ((enc + r) * 52845 + 22719) & 0xFFFF
        out.append(enc)
    for c in data:
        enc = (c ^ (r >> 8)) & 0xFF
        r = ((enc + r) * 52845 + 22719) & 0xFFFF
        out.append(enc)
    return bytes(out)


def charstring_decrypt_full(data: bytes, len_iv: int = 4) -> bytes:
    """Decrypt a single Type 1 charstring with key 4330 and configurable lenIV."""
    r = 4330
    out = bytearray()
    skip = len_iv if len_iv > 0 else 0
    for i, c in enumerate(data):
        plain = (c ^ (r >> 8)) & 0xFF
        r = ((c + r) * 52845 + 22719) & 0xFFFF
        if i >= skip:
            out.append(plain)
    return bytes(out)
