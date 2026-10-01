"""PFA parser utilities."""

from __future__ import annotations

import re

from aspose_font._exceptions import FontParseException

_HEX_RE = re.compile(rb"[0-9A-Fa-f]")


def pfa_to_ps_stream(data: bytes) -> bytes:
    """Convert PFA bytes into a PS stream with decoded eexec binary."""
    if not data.startswith(b"%!PS"):
        raise FontParseException("Not a PFA file")

    eexec_idx = data.find(b"eexec")
    if eexec_idx < 0:
        return data

    body_start = eexec_idx + len(b"eexec")
    while body_start < len(data) and data[body_start] in b" \t\r\n":
        body_start += 1

    clear_idx = data.find(b"cleartomark", body_start)
    hex_region = data[body_start: clear_idx if clear_idx >= 0 else len(data)]
    hex_only = b"".join(_HEX_RE.findall(hex_region))
    if len(hex_only) % 2 == 1:
        hex_only = hex_only[:-1]

    try:
        binary = bytes.fromhex(hex_only.decode("ascii")) if hex_only else b""
    except ValueError as exc:
        raise FontParseException("Invalid hex data in PFA eexec section") from exc

    tail = data[clear_idx:] if clear_idx >= 0 else b""
    return data[:body_start] + binary + tail
