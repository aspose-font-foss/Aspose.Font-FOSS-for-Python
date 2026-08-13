"""Minimal STAT helpers for static variable-font instance metadata."""

from __future__ import annotations

from aspose_font._exceptions import FontParseException
from aspose_font._io import BinaryWriter
from aspose_font.ttf.tables.fvar import AxisRecord

STATIC_STAT_POLICIES = ("drop", "static")
STAT_AXIS_VALUE_FLAG_MEANINGS = {
    0x0001: "older-sibling",
    0x0002: "elidable-axis-value-name",
}


def normalize_static_stat_policy(value: str) -> str:
    policy = value.strip().casefold()
    if policy not in STATIC_STAT_POLICIES:
        raise ValueError(
            "Unknown STAT policy "
            f"{value!r}; expected one of {', '.join(STATIC_STAT_POLICIES)}"
        )
    return policy


def _read_u16_at(data: bytes, offset: int) -> int | None:
    if offset < 0 or offset + 2 > len(data):
        return None
    return int.from_bytes(data[offset : offset + 2], "big")


def _read_u32_at(data: bytes, offset: int) -> int | None:
    if offset < 0 or offset + 4 > len(data):
        return None
    return int.from_bytes(data[offset : offset + 4], "big")


def _write_fixed_16_16(writer: BinaryWriter, value: float) -> None:
    fixed = int(round(value * 65536.0))
    if not (-0x80000000 <= fixed <= 0x7FFFFFFF):
        raise FontParseException("STAT coordinate is outside Fixed16.16 range", format_name="TTF")
    writer.write_i32(fixed)


def build_static_stat_table(
    axes: list[AxisRecord],
    coordinates: dict[str, float],
    *,
    value_name_id: int = 17,
    elided_fallback_name_id: int = 2,
    axis_value_flags: int = 0,
) -> bytes:
    """Build a minimal static STAT 1.1 table for resolved variable coordinates.

    Args:
        axes: Source `fvar` axes to expose as STAT design axes.
        coordinates: Resolved user-space coordinate for each axis tag.
        value_name_id: Name ID used by the generated format-4 AxisValue record.
        elided_fallback_name_id: STAT 1.1 elided fallback name ID.
        axis_value_flags: Raw uint16 flags for the generated AxisValue record.

    Returns:
        Serialized STAT table bytes.
    """

    if not (0 <= axis_value_flags <= 0xFFFF):
        raise FontParseException("STAT AxisValue flags are outside uint16 range", format_name="TTF")
    design_axis_size = 8
    design_axis_count = len(axes)
    design_axes_offset = 20
    axis_value_offsets_offset = design_axes_offset + (design_axis_count * design_axis_size)
    axis_value_table_offset = axis_value_offsets_offset + 2

    w = BinaryWriter()
    w.write_u16(1)
    w.write_u16(1)
    w.write_u16(design_axis_size)
    w.write_u16(design_axis_count)
    w.write_u32(design_axes_offset)
    w.write_u16(1)
    w.write_u32(axis_value_offsets_offset)
    w.write_u16(elided_fallback_name_id)

    for axis_index, axis in enumerate(axes):
        if len(axis.tag) != 4:
            raise FontParseException(f"Invalid STAT axis tag {axis.tag!r}", format_name="TTF")
        if axis.tag not in coordinates:
            raise FontParseException(f"Missing STAT coordinate for axis {axis.tag!r}", format_name="TTF")
        w.write_tag(axis.tag)
        w.write_u16(axis.name_id)
        w.write_u16(axis_index)

    w.write_u16(axis_value_table_offset - axis_value_offsets_offset)
    w.write_u16(4)
    w.write_u16(design_axis_count)
    w.write_u16(axis_value_flags)
    w.write_u16(value_name_id)
    for axis_index, axis in enumerate(axes):
        w.write_u16(axis_index)
        _write_fixed_16_16(w, coordinates[axis.tag])

    return w.to_bytes()


def extract_stat_axis_value_flags(data: bytes) -> tuple[int, ...]:
    """Return AxisValue flags for defensively parseable STAT value records."""

    if len(data) < 18:
        return ()
    major_version = _read_u16_at(data, 0)
    if major_version != 1:
        return ()
    axis_value_count = _read_u16_at(data, 12) or 0
    axis_values_offset = _read_u32_at(data, 14) or 0
    if not axis_values_offset:
        return ()
    flags: list[int] = []
    for value_index in range(axis_value_count):
        value_offset_delta = _read_u16_at(data, axis_values_offset + value_index * 2)
        if value_offset_delta is None:
            continue
        value_offset = axis_values_offset + value_offset_delta
        value_format = _read_u16_at(data, value_offset)
        if value_format in {1, 2, 3, 4}:
            value_flags = _read_u16_at(data, value_offset + 4)
            if value_flags is not None:
                flags.append(value_flags)
    return tuple(flags)


def describe_stat_axis_value_flags(flags: int) -> tuple[str, ...]:
    """Return stable meaning labels for a raw STAT AxisValue flags value."""

    if flags < 0:
        return ()
    meanings = [
        meaning
        for bit, meaning in sorted(STAT_AXIS_VALUE_FLAG_MEANINGS.items())
        if flags & bit
    ]
    known_mask = 0
    for bit in STAT_AXIS_VALUE_FLAG_MEANINGS:
        known_mask |= bit
    unknown_flags = flags & ~known_mask
    bit = 1
    while unknown_flags:
        if unknown_flags & bit:
            meanings.append(f"unknown-0x{bit:04X}")
            unknown_flags &= ~bit
        bit <<= 1
    return tuple(meanings)


def summarize_stat_axis_value_flags(flag_values: tuple[int, ...]) -> dict[str, int]:
    """Return compact usage counts for STAT AxisValue flag values."""

    known_mask = 0
    for bit in STAT_AXIS_VALUE_FLAG_MEANINGS:
        known_mask |= bit
    return {
        "total": len(flag_values),
        "nonzero": sum(1 for flags in flag_values if flags != 0),
        "older_sibling": sum(1 for flags in flag_values if bool(flags & 0x0001)),
        "elidable_axis_value_name": sum(1 for flags in flag_values if bool(flags & 0x0002)),
        "unknown": sum(1 for flags in flag_values if bool(flags & ~known_mask)),
    }


def extract_stat_name_ids(data: bytes) -> tuple[int, ...]:
    """Return name IDs referenced by a source STAT table header, axes, and values."""

    if len(data) < 18:
        return ()
    major_version = _read_u16_at(data, 0)
    if major_version != 1:
        return ()
    minor_version = _read_u16_at(data, 2) or 0
    design_axis_size = _read_u16_at(data, 4) or 0
    design_axis_count = _read_u16_at(data, 6) or 0
    design_axes_offset = _read_u32_at(data, 8) or 0
    axis_value_count = _read_u16_at(data, 12) or 0
    axis_values_offset = _read_u32_at(data, 14) or 0
    name_ids: set[int] = set()

    if design_axis_size >= 8 and design_axes_offset:
        for axis_index in range(design_axis_count):
            axis_offset = design_axes_offset + axis_index * design_axis_size
            axis_name_id = _read_u16_at(data, axis_offset + 4)
            if axis_name_id is not None:
                name_ids.add(axis_name_id)

    if axis_values_offset:
        for value_index in range(axis_value_count):
            value_offset_delta = _read_u16_at(data, axis_values_offset + value_index * 2)
            if value_offset_delta is None:
                continue
            value_offset = axis_values_offset + value_offset_delta
            value_format = _read_u16_at(data, value_offset)
            if value_format in {1, 2, 3, 4}:
                value_name_id = _read_u16_at(data, value_offset + 6)
                if value_name_id is not None:
                    name_ids.add(value_name_id)

    elided_fallback_name_id = _read_u16_at(data, 18) if minor_version >= 1 else None
    if elided_fallback_name_id is not None:
        name_ids.add(elided_fallback_name_id)

    return tuple(sorted(name_ids))
