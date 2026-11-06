"""Internal helpers for TrueType Collection (TTC) parsing."""

from __future__ import annotations

from dataclasses import dataclass

from aspose_font._exceptions import FontParseException

_TTC_MAGIC = b"ttcf"
_SFNT_HEADER_SIZE = 12
_TABLE_RECORD_SIZE = 16
_SUPPORTED_SFNT_VERSIONS = {
    b"\x00\x01\x00\x00",
    b"OTTO",
    b"true",
    b"typ1",
}


@dataclass(frozen=True, slots=True)
class TtcFaceRecord:
    offset: int
    sfnt_version: bytes
    num_tables: int


def is_ttc(data: bytes) -> bool:
    return len(data) >= 4 and data[:4] == _TTC_MAGIC


def parse_ttc_faces(data: bytes) -> list[TtcFaceRecord]:
    if not is_ttc(data):
        raise FontParseException("Invalid TTC header", format_name="TTC")
    if len(data) < 12:
        raise FontParseException("Invalid TTC header", format_name="TTC")

    num_fonts = int.from_bytes(data[8:12], "big")
    offsets_end = 12 + num_fonts * 4
    if num_fonts <= 0 or offsets_end > len(data):
        raise FontParseException("Invalid TTC header", format_name="TTC")

    faces: list[TtcFaceRecord] = []
    for index in range(num_fonts):
        offset = int.from_bytes(data[12 + index * 4:16 + index * 4], "big")
        if offset < 0 or offset + _SFNT_HEADER_SIZE > len(data):
            raise FontParseException(
                f"Invalid TTC face offset {offset} for index {index}",
                format_name="TTC",
            )
        sfnt_version = data[offset:offset + 4]
        if sfnt_version not in _SUPPORTED_SFNT_VERSIONS:
            raise FontParseException(
                f"Invalid TTC face sfnt version for index {index}",
                offset=offset,
                format_name="TTC",
            )
        num_tables = int.from_bytes(data[offset + 4:offset + 6], "big")
        directory_end = offset + _SFNT_HEADER_SIZE + num_tables * _TABLE_RECORD_SIZE
        if num_tables <= 0 or directory_end > len(data):
            raise FontParseException(
                f"Invalid TTC table directory for index {index}",
                offset=offset,
                format_name="TTC",
            )
        faces.append(TtcFaceRecord(offset=offset, sfnt_version=sfnt_version, num_tables=num_tables))
    return faces


def slice_ttc_face(data: bytes, index: int) -> tuple[bytes, int]:
    faces = parse_ttc_faces(data)
    if index < 0 or index >= len(faces):
        raise FontParseException(
            f"TTC collection index {index} out of range (available: 0-{len(faces) - 1})",
            format_name="TTC",
        )

    face = faces[index]
    header_size = _SFNT_HEADER_SIZE + face.num_tables * _TABLE_RECORD_SIZE
    records: list[tuple[bytes, int, int]] = []
    data_chunks: list[bytes] = []
    current_offset = header_size

    for table_index in range(face.num_tables):
        record_offset = face.offset + _SFNT_HEADER_SIZE + table_index * _TABLE_RECORD_SIZE
        tag = data[record_offset:record_offset + 4]
        checksum = int.from_bytes(data[record_offset + 4:record_offset + 8], "big")
        table_offset = int.from_bytes(data[record_offset + 8:record_offset + 12], "big")
        table_length = int.from_bytes(data[record_offset + 12:record_offset + 16], "big")
        table_end = table_offset + table_length
        if table_offset < 0 or table_length < 0 or table_end > len(data):
            raise FontParseException(
                f"Invalid TTC table record {tag.decode('latin-1', errors='ignore')!r} for index {index}",
                offset=record_offset,
                format_name="TTC",
            )

        chunk = data[table_offset:table_end]
        records.append((tag, checksum, current_offset))
        data_chunks.append(chunk)
        current_offset += len(chunk)
        padding = (-len(chunk)) % 4
        if padding:
            current_offset += padding

    search_range, entry_selector, range_shift = _sfnt_search_params(face.num_tables)
    parts = [
        face.sfnt_version,
        face.num_tables.to_bytes(2, "big"),
        search_range.to_bytes(2, "big"),
        entry_selector.to_bytes(2, "big"),
        range_shift.to_bytes(2, "big"),
    ]
    for (tag, checksum, offset), chunk in zip(records, data_chunks, strict=True):
        parts.append(tag)
        parts.append(checksum.to_bytes(4, "big"))
        parts.append(offset.to_bytes(4, "big"))
        parts.append(len(chunk).to_bytes(4, "big"))
    for chunk in data_chunks:
        parts.append(chunk)
        padding = (-len(chunk)) % 4
        if padding:
            parts.append(b"\x00" * padding)

    return b"".join(parts), len(faces)


def _sfnt_search_params(num_tables: int) -> tuple[int, int, int]:
    max_power = 1
    entry_selector = 0
    while max_power * 2 <= num_tables:
        max_power *= 2
        entry_selector += 1
    search_range = max_power * 16
    range_shift = num_tables * 16 - search_range
    return search_range, entry_selector, range_shift
