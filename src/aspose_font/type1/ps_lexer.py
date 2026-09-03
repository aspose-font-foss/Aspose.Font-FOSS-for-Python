"""Lightweight PostScript extractor for Type1 fonts."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from aspose_font._exceptions import FontParseException
from aspose_font.type1.eexec import eexec_decrypt

_NAME_RE = re.compile(rb"/([A-Za-z0-9_.-]+)")
_DUP_ENCODING_RE = re.compile(rb"dup\s+(\d+)\s+/([A-Za-z0-9_.-]+)\s+put")
_RD_RE = re.compile(rb"(?:RD|-\|)")


@dataclass(slots=True)
class Type1FontData:
    font_name: str = ""
    full_name: str = ""
    family_name: str = ""
    weight: str = ""
    italic_angle: float = 0.0
    is_fixed_pitch: bool = False
    font_bbox: tuple[int, int, int, int] = (0, 0, 0, 0)
    underline_position: int = -100
    underline_thickness: int = 50
    encoding: list[str] = field(default_factory=lambda: [".notdef"] * 256)
    charstrings: dict[str, bytes] = field(default_factory=dict)
    subrs: list[bytes] = field(default_factory=list)
    len_iv: int = 4


def parse_type1_ps(ps_stream: bytes) -> Type1FontData:
    """Extract known Type1 data from a PostScript stream."""
    out = Type1FontData()

    eexec_idx = ps_stream.find(b"eexec")
    header = ps_stream[:eexec_idx] if eexec_idx >= 0 else ps_stream
    _parse_header(header, out)

    if eexec_idx < 0:
        return out

    body_start = eexec_idx + len(b"eexec")
    while body_start < len(ps_stream) and ps_stream[body_start] in b" \t\r\n":
        body_start += 1
    # Use the terminal marker so encrypted payload bytes that coincidentally contain the
    # token do not truncate the eexec block during round-trip parsing.
    clear_idx = ps_stream.rfind(b"cleartomark")
    encrypted = ps_stream[body_start: clear_idx if clear_idx >= 0 else len(ps_stream)]
    if not encrypted:
        raise FontParseException("No eexec block found in Type1 font")

    decrypted = eexec_decrypt(encrypted)
    _parse_len_iv(decrypted, out)
    out.subrs = _parse_subrs(decrypted)
    out.charstrings = _parse_charstrings(decrypted)
    return out


def _parse_header(header: bytes, out: Type1FontData) -> None:
    text = header.decode("latin-1", errors="ignore")

    m = re.search(r"/FontName\s+/([A-Za-z0-9_.-]+)", text)
    if m:
        out.font_name = m.group(1)

    m = re.search(r"/FullName\s+\((.*?)\)", text, flags=re.S)
    if m:
        out.full_name = m.group(1)

    m = re.search(r"/FamilyName\s+\((.*?)\)", text, flags=re.S)
    if m:
        out.family_name = m.group(1)

    m = re.search(r"/Weight\s+\((.*?)\)", text, flags=re.S)
    if m:
        out.weight = m.group(1)

    m = re.search(r"/ItalicAngle\s+([\-0-9.]+)", text)
    if m:
        out.italic_angle = float(m.group(1))

    m = re.search(r"/isFixedPitch\s+(true|false)", text)
    if m:
        out.is_fixed_pitch = m.group(1) == "true"

    m = re.search(r"/UnderlinePosition\s+([\-0-9]+)", text)
    if m:
        out.underline_position = int(m.group(1))

    m = re.search(r"/UnderlineThickness\s+([\-0-9]+)", text)
    if m:
        out.underline_thickness = int(m.group(1))

    m = re.search(r"/FontBBox\s+[\[{]([\-0-9 ]+)[\]}]", text)
    if m:
        vals = [int(v) for v in m.group(1).split() if v]
        if len(vals) == 4:
            out.font_bbox = (vals[0], vals[1], vals[2], vals[3])

    for code_s, name_s in _DUP_ENCODING_RE.findall(header):
        code = int(code_s)
        if 0 <= code < 256:
            out.encoding[code] = name_s.decode("latin-1")


def _parse_len_iv(decrypted: bytes, out: Type1FontData) -> None:
    text = decrypted.decode("latin-1", errors="ignore")
    m = re.search(r"/lenIV\s+(-?\d+)", text)
    if m:
        out.len_iv = int(m.group(1))


def _parse_subrs(decrypted: bytes) -> list[bytes]:
    start = decrypted.find(b"/Subrs")
    if start < 0:
        return []
    end = decrypted.find(b"/CharStrings", start)
    region = decrypted[start: end if end >= 0 else len(decrypted)]

    out: list[bytes] = []
    pos = 0
    while True:
        m = re.search(rb"dup\s+(\d+)\s+(\d+)\s+", region[pos:])
        if m is None:
            break
        idx = int(m.group(1))
        n = int(m.group(2))
        abs_start = pos + m.end()
        rd = _RD_RE.match(region, abs_start)
        if rd is None:
            pos = abs_start
            continue
        data_start = rd.end()
        if data_start < len(region) and region[data_start] in b" \t\r\n":
            data_start += 1
        data_end = data_start + n
        if data_end > len(region):
            break
        while len(out) <= idx:
            out.append(b"")
        out[idx] = region[data_start:data_end]
        pos = data_end
    return out


def _parse_charstrings(decrypted: bytes) -> dict[str, bytes]:
    start = decrypted.find(b"/CharStrings")
    if start < 0:
        return {}

    out: dict[str, bytes] = {}
    pos = start
    size = len(decrypted)
    while pos < size:
        m = re.search(rb"/([A-Za-z0-9_.-]+)\s+(\d+)\s+", decrypted[pos:])
        if m is None:
            break
        name = m.group(1).decode("latin-1")
        n = int(m.group(2))
        abs_start = pos + m.end()
        rd = _RD_RE.match(decrypted, abs_start)
        if rd is None:
            pos = abs_start
            continue
        data_start = rd.end()
        if data_start < size and decrypted[data_start] in b" \t\r\n":
            data_start += 1
        data_end = data_start + n
        if data_end > size:
            break
        out[name] = decrypted[data_start:data_end]
        pos = data_end

    return out
