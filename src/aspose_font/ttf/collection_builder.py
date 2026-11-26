"""TrueType Collection (TTC) builder.

This module provides functionality to merge multiple TTF/OTF fonts into a single
TrueType Collection (TTC) file with optional table deduplication for space efficiency.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from aspose_font._exceptions import FontParseException
from aspose_font._io import BinaryWriter
from aspose_font.loader import FontLoader
from aspose_font.ttf.collection import _sfnt_search_params
from aspose_font.ttf.font import TtfFont


def _compute_table_hash(data: bytes) -> str:
    """Return hex SHA-256 digest of table bytes (for dedup detection)."""
    return hashlib.sha256(data).hexdigest()


def _compute_table_checksum(data: bytes) -> int:
    """Compute SFNT table checksum."""
    padded = data + (b"\x00" * ((4 - (len(data) % 4)) % 4))
    total = 0
    for i in range(0, len(padded), 4):
        total = (total + int.from_bytes(padded[i : i + 4], "big")) & 0xFFFFFFFF
    return total


def _compute_head_checksum_adjustment(sfnt_bytes: bytes) -> int:
    """Compute head.checkSumAdjustment for SFNT."""
    checksum = _compute_table_checksum(sfnt_bytes)
    adjustment = (0xB1B0AFBA - checksum) & 0xFFFFFFFF
    return adjustment


def _build_sfnt_no_pool(font: TtfFont) -> tuple[dict, bytes]:
    """Build a single sfnt without using a shared table pool.

    Returns:
        Tuple of (sfnt_metadata_dict, sfnt_binary_bytes)
    """
    tables = font.ttf_tables

    raw_tables: dict[str, bytes] = {}
    if tables.head is not None:
        raw_tables["head"] = tables.head.to_bytes()
    if tables.hhea is not None:
        raw_tables["hhea"] = tables.hhea.to_bytes()
    if tables.maxp is not None:
        raw_tables["maxp"] = tables.maxp.to_bytes()
    if tables.os2 is not None:
        raw_tables["OS/2"] = tables.os2.to_bytes()
    if tables.name is not None:
        raw_tables["name"] = tables.name.to_bytes()
    if tables.post is not None:
        raw_tables["post"] = tables.post.to_bytes()
    if tables.cmap is not None:
        raw_tables["cmap"] = tables.cmap.to_bytes()
    if tables.loca is not None and tables.head is not None:
        raw_tables["loca"] = tables.loca.to_bytes(tables.head.index_to_loc_format)
    if tables.hmtx is not None and tables.hhea is not None:
        raw_tables["hmtx"] = tables.hmtx.to_bytes(tables.hhea.number_of_hmetrics)
    if tables.glyf is not None:
        raw_tables["glyf"] = tables.glyf.to_bytes()

    font_tags = sorted(raw_tables.keys())
    num_tables = len(font_tags)

    search_range, entry_selector, range_shift = _sfnt_search_params(num_tables)
    directory_size = num_tables * 16
    data_start = 12 + directory_size

    writer = BinaryWriter()
    writer.write_u32(font._sfnt_version)
    writer.write_u16(num_tables)
    writer.write_u16(search_range)
    writer.write_u16(entry_selector)
    writer.write_u16(range_shift)

    table_data_list: list[tuple[str, int, int, bytes]] = []
    data_offset = data_start

    for tag in font_tags:
        table_bytes = raw_tables[tag]
        table_offset = data_offset
        checksum = _compute_table_checksum(table_bytes)
        writer.write_tag(tag)
        writer.write_u32(checksum)
        writer.write_u32(table_offset)
        writer.write_u32(len(table_bytes))

        table_data_list.append((tag, table_offset, len(table_bytes), table_bytes))
        data_offset += len(table_bytes)
        padding = (-len(table_bytes)) % 4
        data_offset += padding

    sfnt_body = writer.to_bytes()

    for tag, table_offset, table_length, table_bytes in table_data_list:
        while len(sfnt_body) < table_offset:
            sfnt_body += b"\x00"
        sfnt_body += table_bytes
        padding = (-table_length) % 4
        if padding:
            sfnt_body += b"\x00" * padding

    head_entry = next((e for e in table_data_list if e[0] == "head"), None)
    if head_entry is not None:
        adjustment = _compute_head_checksum_adjustment(bytes(sfnt_body))
        head_offset = head_entry[1]
        sfnt_body = (
            sfnt_body[: head_offset + 8]
            + adjustment.to_bytes(4, "big")
            + sfnt_body[head_offset + 12 :]
        )

    sfnt_dict = {
        "num_tables": num_tables,
        "sfnt_version": font._sfnt_version,
    }

    return sfnt_dict, bytes(sfnt_body)


def _build_sfnt_with_pool_dedup(
    font: TtfFont,
    raw_tables: dict[str, bytes],
    shared_pool: dict[str, bytes],
    table_hashes: dict[str, str],
) -> tuple[dict, bytes]:
    """Build a single sfnt using the shared table pool for deduplication.

    The table offsets in the directory point to positions in the shared table data section
    that will be laid out after all sfnt directories in the final TTC.

    Returns:
        Tuple of (sfnt_metadata_dict, sfnt_binary_bytes)
    """
    sfnt_version = font._sfnt_version
    font_tags = sorted(raw_tables.keys())
    num_tables = len(font_tags)

    search_range, entry_selector, range_shift = _sfnt_search_params(num_tables)
    directory_size = num_tables * 16
    data_start = 12 + directory_size

    writer = BinaryWriter()
    writer.write_u32(sfnt_version)
    writer.write_u16(num_tables)
    writer.write_u16(search_range)
    writer.write_u16(entry_selector)
    writer.write_u16(range_shift)

    table_data_list: list[tuple[str, int, int, bytes]] = []
    data_offset = data_start

    for tag in font_tags:
        table_bytes = raw_tables[tag]
        table_hash = table_hashes.get(tag, _compute_table_hash(table_bytes))

        checksum = _compute_table_checksum(table_bytes)

        if table_hash in shared_pool:
            table_offset = 0
        else:
            table_offset = data_offset

        writer.write_tag(tag)
        writer.write_u32(checksum)
        writer.write_u32(table_offset)
        writer.write_u32(len(table_bytes))

        if table_hash not in shared_pool:
            table_data_list.append((tag, table_offset, len(table_bytes), table_bytes))
            data_offset += len(table_bytes)
            padding = (-len(table_bytes)) % 4
            data_offset += padding

    sfnt_body = writer.to_bytes()

    for tag, table_offset, table_length, table_bytes in table_data_list:
        while len(sfnt_body) < table_offset:
            sfnt_body += b"\x00"
        sfnt_body += table_bytes
        padding = (-table_length) % 4
        if padding:
            sfnt_body += b"\x00" * padding

    head_entry = next((e for e in table_data_list if e[0] == "head"), None)
    if head_entry is not None:
        adjustment = _compute_head_checksum_adjustment(bytes(sfnt_body))
        head_offset = head_entry[1]
        sfnt_body = (
            sfnt_body[: head_offset + 8]
            + adjustment.to_bytes(4, "big")
            + sfnt_body[head_offset + 12 :]
        )

    sfnt_dict = {
        "num_tables": num_tables,
        "sfnt_version": sfnt_version,
    }

    for tag, table_hash in table_hashes.items():
        sfnt_dict[f"table_hash_{tag}"] = table_hash

    return sfnt_dict, bytes(sfnt_body)


def _assemble_ttc(sfnt_data_list: list[dict], sfnt_binary_list: list[bytes]) -> bytes:
    """Assemble TTC header and sfnt bodies into final TTC binary.

    This is for the no-dedup case where each font's sfnt contains all its table data inline.

    Args:
        sfnt_data_list: List of dicts containing sfnt metadata.
        sfnt_binary_list: List of sfnt binary data.

    Returns:
        Complete TTC binary data.
    """
    num_fonts = len(sfnt_binary_list)

    header = BinaryWriter()
    header.write_tag("ttcf")
    header.write_u32(0x00010000)
    header.write_u32(num_fonts)

    for _ in range(num_fonts):
        header.write_u32(0)

    header_bytes = header.to_bytes()

    face_offsets: list[int] = []
    data_after_header = 12 + num_fonts * 4

    for sfnt in sfnt_binary_list:
        face_offsets.append(data_after_header)
        data_after_header += len(sfnt)

    result = bytearray(header_bytes)

    for i, offset in enumerate(face_offsets):
        result[12 + i * 4 : 16 + i * 4] = offset.to_bytes(4, "big")

    for sfnt in sfnt_binary_list:
        result.extend(sfnt)

    return bytes(result)


def _assemble_ttc_dedup(
    sfnt_data_list: list[dict],
    sfnt_binary_list: list[bytes],
    shared_pool: dict[str, bytes],
) -> bytes:
    """Assemble TTC header and sfnt bodies with shared table pool.

    For dedup case, all shared tables are stored once after all sfnt directories.
    Each sfnt's table directory contains offsets into the shared pool.

    Args:
        sfnt_data_list: List of dicts containing sfnt metadata.
        sfnt_binary_list: List of sfnt binary data.
        shared_pool: Dict mapping table hash to table bytes for all unique tables.

    Returns:
        Complete TTC binary data.
    """
    num_fonts = len(sfnt_binary_list)

    header = BinaryWriter()
    header.write_tag("ttcf")
    header.write_u32(0x00010000)
    header.write_u32(num_fonts)

    for _ in range(num_fonts):
        header.write_u32(0)

    header_bytes = header.to_bytes()

    face_offsets: list[int] = []
    data_after_header = 12 + num_fonts * 4

    for sfnt in sfnt_binary_list:
        face_offsets.append(data_after_header)
        data_after_header += len(sfnt)

    result = bytearray(header_bytes)

    for i, offset in enumerate(face_offsets):
        result[12 + i * 4 : 16 + i * 4] = offset.to_bytes(4, "big")

    for sfnt in sfnt_binary_list:
        result.extend(sfnt)

    table_data_start = len(result)

    shared_offset_map: dict[str, int] = {}
    current_offset = 0

    for table_hash, table_bytes in shared_pool.items():
        if table_hash not in shared_offset_map:
            shared_offset_map[table_hash] = table_data_start + current_offset
            current_offset += len(table_bytes)
            padding = (-len(table_bytes)) % 4
            current_offset += padding

    for table_hash, table_bytes in shared_pool.items():
        pool_offset = shared_offset_map[table_hash]
        while len(result) < pool_offset:
            result.append(0)
        result.extend(table_bytes)
        padding = (-len(table_bytes)) % 4
        if padding:
            result.extend(b"\x00" * padding)

    for font_idx, sfnt_data in enumerate(sfnt_data_list):
        num_tables = sfnt_data["num_tables"]
        sfnt_offset = face_offsets[font_idx]
        dir_start = sfnt_offset + 12

        for table_idx in range(num_tables):
            dir_entry = dir_start + table_idx * 16
            tag = result[dir_entry : dir_entry + 4].decode("latin-1", errors="ignore")

            table_hash = sfnt_data.get(f"table_hash_{tag}")
            if table_hash and table_hash in shared_offset_map:
                new_offset = shared_offset_map[table_hash]
                result[dir_entry + 8 : dir_entry + 12] = new_offset.to_bytes(4, "big")

    return bytes(result)


def build_ttc(font_paths: list[Path], output_path: Path, dedup: bool = True) -> None:
    """Merge multiple font files into a single TTC collection.

    Args:
        font_paths: List of paths to TTF/OTF font files to merge.
        output_path: Path where the resulting TTC file will be written.
        dedup: When True, share identical table data across fonts to reduce size.

    Raises:
        FontParseException: If any input font is invalid or format is unsupported.
        OSError: If output file cannot be written.
    """
    if not font_paths:
        raise FontParseException("No font paths provided", format_name="TTC")

    if len(font_paths) == 1:
        raise FontParseException("TTC requires at least 2 fonts", format_name="TTC")

    fonts: list[TtfFont] = []
    for font_path in font_paths:
        try:
            loaded = FontLoader.load(font_path)
            if not isinstance(loaded.font, TtfFont):
                raise FontParseException(
                    f"Font {font_path} is not a TTF/OTF font", format_name="TTC"
                )
            fonts.append(loaded.font)
        except Exception as e:
            if isinstance(e, FontParseException):
                raise FontParseException(
                    f"Failed to load font {font_path}: {e.message}", format_name="TTC"
                ) from e
            raise FontParseException(
                f"Failed to load font {font_path}: {type(e).__name__}", format_name="TTC"
            ) from e

    if dedup:
        ttc_data = _build_ttc_dedup(fonts)
    else:
        ttc_data = _build_ttc_no_dedup(fonts)

    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(ttc_data)
    except OSError as e:
        raise OSError(f"Failed to write TTC file {output_path}: {e}") from e


def _build_ttc_no_dedup(fonts: list[TtfFont]) -> bytes:
    """Build TTC without deduplication - each font has its own table data."""
    sfnt_data_list: list[dict] = []
    sfnt_binary_list: list[bytes] = []

    for font in fonts:
        sfnt_data, sfnt_binary = _build_sfnt_no_pool(font)
        sfnt_data_list.append(sfnt_data)
        sfnt_binary_list.append(sfnt_binary)

    return _assemble_ttc(sfnt_data_list, sfnt_binary_list)


def _build_ttc_dedup(fonts: list[TtfFont]) -> bytes:
    """Build TTC with deduplication - shared tables stored once."""
    all_table_data: list[dict[str, bytes]] = []
    all_table_hashes: list[dict[str, str]] = []

    for font in fonts:
        tables = font.ttf_tables
        raw_tables: dict[str, bytes] = {}
        table_hashes: dict[str, str] = {}

        if tables.head is not None:
            raw_tables["head"] = tables.head.to_bytes()
            table_hashes["head"] = _compute_table_hash(tables.head.to_bytes())
        if tables.hhea is not None:
            raw_tables["hhea"] = tables.hhea.to_bytes()
            table_hashes["hhea"] = _compute_table_hash(tables.hhea.to_bytes())
        if tables.maxp is not None:
            raw_tables["maxp"] = tables.maxp.to_bytes()
            table_hashes["maxp"] = _compute_table_hash(tables.maxp.to_bytes())
        if tables.os2 is not None:
            raw_tables["OS/2"] = tables.os2.to_bytes()
            table_hashes["OS/2"] = _compute_table_hash(tables.os2.to_bytes())
        if tables.name is not None:
            raw_tables["name"] = tables.name.to_bytes()
            table_hashes["name"] = _compute_table_hash(tables.name.to_bytes())
        if tables.post is not None:
            raw_tables["post"] = tables.post.to_bytes()
            table_hashes["post"] = _compute_table_hash(tables.post.to_bytes())
        if tables.cmap is not None:
            raw_tables["cmap"] = tables.cmap.to_bytes()
            table_hashes["cmap"] = _compute_table_hash(tables.cmap.to_bytes())
        if tables.loca is not None and tables.head is not None:
            raw_tables["loca"] = tables.loca.to_bytes(tables.head.index_to_loc_format)
            table_hashes["loca"] = _compute_table_hash(
                tables.loca.to_bytes(tables.head.index_to_loc_format)
            )
        if tables.hmtx is not None and tables.hhea is not None:
            raw_tables["hmtx"] = tables.hmtx.to_bytes(tables.hhea.number_of_hmetrics)
            table_hashes["hmtx"] = _compute_table_hash(
                tables.hmtx.to_bytes(tables.hhea.number_of_hmetrics)
            )
        if tables.glyf is not None:
            raw_tables["glyf"] = tables.glyf.to_bytes()
            table_hashes["glyf"] = _compute_table_hash(tables.glyf.to_bytes())

        all_table_data.append(raw_tables)
        all_table_hashes.append(table_hashes)

    shared_pool: dict[str, bytes] = {}

    for raw_tables in all_table_data:
        for tag, table_bytes in raw_tables.items():
            table_hash = _compute_table_hash(table_bytes)
            if table_hash not in shared_pool:
                shared_pool[table_hash] = table_bytes

    sfnt_data_list: list[dict] = []
    sfnt_binary_list: list[bytes] = []

    for font, raw_tables, table_hashes in zip(fonts, all_table_data, all_table_hashes, strict=True):
        sfnt_data, sfnt_binary = _build_sfnt_with_pool_dedup(
            font, raw_tables, shared_pool, table_hashes
        )
        sfnt_data_list.append(sfnt_data)
        sfnt_binary_list.append(sfnt_binary)

    return _assemble_ttc_dedup(sfnt_data_list, sfnt_binary_list, shared_pool)
