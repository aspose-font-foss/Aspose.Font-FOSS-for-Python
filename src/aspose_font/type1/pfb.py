"""PFB parser utilities."""

from __future__ import annotations

from dataclasses import dataclass

from aspose_font._exceptions import FontParseException

PFB_ASCII = 1
PFB_BINARY = 2
PFB_EOF = 3


@dataclass(slots=True)
class PfbSegment:
    seg_type: int
    data: bytes


def parse_pfb(data: bytes) -> list[PfbSegment]:
    """Parse PFB segments from raw bytes."""
    if len(data) < 2 or data[0] != 0x80 or data[1] != PFB_ASCII:
        raise FontParseException("Not a PFB file")

    pos = 0
    segments: list[PfbSegment] = []
    size = len(data)
    while pos < size:
        if pos + 2 > size or data[pos] != 0x80:
            raise FontParseException("Invalid PFB segment header")
        seg_type = data[pos + 1]
        pos += 2
        if seg_type == PFB_EOF:
            segments.append(PfbSegment(seg_type=seg_type, data=b""))
            break
        if seg_type not in (PFB_ASCII, PFB_BINARY):
            raise FontParseException(f"Unsupported PFB segment type: {seg_type}")
        if pos + 4 > size:
            raise FontParseException("Truncated PFB segment length")
        length = int.from_bytes(data[pos : pos + 4], "little")
        pos += 4
        end = pos + length
        if end > size:
            raise FontParseException("PFB segment exceeds file size")
        segments.append(PfbSegment(seg_type=seg_type, data=data[pos:end]))
        pos = end
    return segments


def pfb_to_ps_stream(segments: list[PfbSegment]) -> bytes:
    """Concatenate PFB ASCII and binary segments into one PS stream."""
    return b"".join(seg.data for seg in segments if seg.seg_type in (PFB_ASCII, PFB_BINARY))
