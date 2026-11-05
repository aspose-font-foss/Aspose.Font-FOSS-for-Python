"""Minimal STAT helpers for static variable-font instance metadata."""

from __future__ import annotations

from typing import TYPE_CHECKING

from aspose_font._exceptions import FontParseException
from aspose_font._io import BinaryWriter
from aspose_font.ttf.tables.fvar import AxisRecord, NamedInstance

if TYPE_CHECKING:
    from aspose_font.ttf.font import TtfFont

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


_STAT_AXIS_VALUE_FLAG_ELIDABLE = 0x0002
_STAT_AXIS_VALUE_FLAG_LINKED = 0x0001


def build_static_stat_table(
    axes: list[AxisRecord],
    coordinates: dict[str, float],
    *,
    value_name_id: int = 17,
    elided_fallback_name_id: int = 2,
    axis_value_flags: int = 0,
    preserve_from_source: tuple[int, ...] = (),
    preserve_flags_mask: int = 0x0003,
) -> bytes:
    """Build a minimal static STAT 1.1 table for resolved variable coordinates.

    Args:
        axes: Source `fvar` axes to expose as STAT design axes.
        coordinates: Resolved user-space coordinate for each axis tag.
        value_name_id: Name ID used by the generated format-4 AxisValue record.
        elided_fallback_name_id: STAT 1.1 elided fallback name ID.
        axis_value_flags: Raw uint16 flags for the generated AxisValue record.
        preserve_from_source: Tuple of source AxisValue flag integers to preserve.
        preserve_flags_mask: Bitmask of allowed flag types to preserve (default: 0x0003 = both).

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

    preserve_bitmask = 0
    if preserve_from_source:
        for flags in preserve_from_source:
            preserve_bitmask |= (flags & preserve_flags_mask)

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
    if preserve_from_source:
        effective_flags = preserve_from_source[-1] & preserve_bitmask
        axis_value_flags = effective_flags
    w.write_u16(axis_value_flags)
    w.write_u16(value_name_id)
    w.write_u16(design_axis_count)
    for axis_index, axis in enumerate(axes):
        w.write_u16(axis_index)
        _write_fixed_16_16(w, coordinates[axis.tag])

    result = w.to_bytes()
    return result


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
            value_flags = _read_u16_at(data, value_offset + 2)
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
            if value_format == 4:
                value_name_id = _read_u16_at(data, value_offset + 4)
                if value_name_id is not None:
                    name_ids.add(value_name_id)
            elif value_format in {1, 2}:
                value_name_id = _read_u16_at(data, value_offset + 10)
                if value_name_id is not None:
                    name_ids.add(value_name_id)

    elided_fallback_name_id = _read_u16_at(data, 18) if minor_version >= 1 else None
    if elided_fallback_name_id is not None:
        name_ids.add(elided_fallback_name_id)

    return tuple(sorted(name_ids))


def parse_stat_table(data: bytes) -> dict[str, object] | None:
    """Parse STAT table and return structured data for consistency validation.

    Args:
        data: Raw STAT table bytes

    Returns:
        Dictionary with parsed STAT table data, or None if parsing fails
    """
    if len(data) < 18:
        return None
    major_version = _read_u16_at(data, 0)
    if major_version != 1:
        return None

    minor_version = _read_u16_at(data, 2) or 0
    design_axis_size = _read_u16_at(data, 4) or 0
    design_axis_count = _read_u16_at(data, 6) or 0
    design_axes_offset = _read_u32_at(data, 8) or 0
    axis_value_count = _read_u16_at(data, 12) or 0
    axis_values_offset = _read_u32_at(data, 14) or 0

    if not design_axes_offset or not axis_values_offset:
        return None

    # Parse DesignAxis records
    axes: list[dict[str, object]] = []
    if design_axis_size >= 8:
        for axis_index in range(design_axis_count):
            axis_offset = design_axes_offset + axis_index * design_axis_size
            axis_tag = _read_u32_at(data, axis_offset)
            if axis_tag is None:
                continue
            # Convert 32-bit value to 4-char tag
            axis_tag_str = axis_tag.to_bytes(4, "big").decode("ascii", errors="replace")
            axis_name_id = _read_u16_at(data, axis_offset + 4) or 0
            axis_order = _read_u16_at(data, axis_offset + 6) or 0
            axes.append({
                "tag": axis_tag_str,
                "name_id": axis_name_id,
                "order": axis_order,
            })

    # Parse AxisValue records
    values: list[dict[str, object]] = []
    for value_index in range(axis_value_count):
        value_offset_delta = _read_u16_at(data, axis_values_offset + value_index * 2)
        if value_offset_delta is None:
            continue
        value_offset = axis_values_offset + value_offset_delta
        value_format = _read_u16_at(data, value_offset)
        if value_format not in {1, 2, 3, 4}:
            continue

        value_flags = _read_u16_at(data, value_offset + 2) or 0
        value_name_id = _read_u16_at(data, value_offset + 4) or 0

        value_record: dict[str, object] = {
            "format": value_format,
            "flags": value_flags,
            "name_id": value_name_id,
        }

        if value_format == 1:
            # Format 1: Single axis value
            axis_index = _read_u16_at(data, value_offset + 6) or 0
            coordinate = _read_u32_at(data, value_offset + 8)
            if coordinate is not None:
                if coordinate >= 0x80000000:
                    coordinate -= 0x100000000
                coordinate = coordinate / 65536.0
            value_record["axis_index"] = axis_index
            value_record["coordinate"] = coordinate
        elif value_format == 2:
            # Format 2: Axis value with range
            axis_index = _read_u16_at(data, value_offset + 6) or 0
            value_record["axis_index"] = axis_index
            value_record["value"] = _read_u32_at(data, value_offset + 8)
            if value_record["value"] is not None:
                if value_record["value"] >= 0x80000000:
                    value_record["value"] -= 0x100000000
                value_record["value"] = value_record["value"] / 65536.0
            value_record["min_value"] = _read_u32_at(data, value_offset + 12)
            if value_record["min_value"] is not None:
                if value_record["min_value"] >= 0x80000000:
                    value_record["min_value"] -= 0x100000000
                value_record["min_value"] = value_record["min_value"] / 65536.0
            value_record["max_value"] = _read_u32_at(data, value_offset + 16)
            if value_record["max_value"] is not None:
                if value_record["max_value"] >= 0x80000000:
                    value_record["max_value"] -= 0x100000000
                value_record["max_value"] = value_record["max_value"] / 65536.0
        elif value_format == 3:
            # Format 3: Linked axis value
            axis_index = _read_u16_at(data, value_offset + 6) or 0
            value_record["axis_index"] = axis_index
            value_record["value"] = _read_u32_at(data, value_offset + 8)
            if value_record["value"] is not None:
                if value_record["value"] >= 0x80000000:
                    value_record["value"] -= 0x100000000
                value_record["value"] = value_record["value"] / 65536.0
            value_record["linked_value"] = _read_u32_at(data, value_offset + 12)
            if value_record["linked_value"] is not None:
                if value_record["linked_value"] >= 0x80000000:
                    value_record["linked_value"] -= 0x100000000
                value_record["linked_value"] = value_record["linked_value"] / 65536.0
        elif value_format == 4:
            # Format 4: Multi-axis value (for STAT 1.1)
            axis_count = _read_u16_at(data, value_offset + 6) or 0
            axis_data: list[dict[str, object]] = []
            current_offset = value_offset + 8
            for _ in range(axis_count):
                axis_index = _read_u16_at(data, current_offset) or 0
                coordinate = _read_u32_at(data, current_offset + 2)
                if coordinate is not None:
                    if coordinate >= 0x80000000:
                        coordinate -= 0x100000000
                    coordinate = coordinate / 65536.0
                axis_data.append({
                    "axis_index": axis_index,
                    "coordinate": coordinate,
                })
                current_offset += 6
            value_record["axis_count"] = axis_count
            value_record["axis_data"] = axis_data

        values.append(value_record)

    return {
        "version": f"1.{minor_version}" if minor_version else "1.0",
        "design_axes": axes,
        "axis_values": values,
        "elided_fallback_name_id": _read_u16_at(data, 18) if minor_version >= 1 else None,
    }


def extract_stat_axis_tags(data: bytes) -> tuple[str, ...]:
    """Extract axis tags from STAT table DesignAxis records.

    Args:
        data: Raw STAT table bytes

    Returns:
        Tuple of axis tags in order, or empty tuple if parsing fails
    """
    parsed = parse_stat_table(data)
    if parsed is None:
        return ()
    return tuple(axis["tag"] for axis in parsed.get("design_axes", []))


def synthesize_stat_table(font: "TtfFont") -> bytes | None:
    """Synthesize a STAT table from fvar axes and named instances.

    Creates a STAT 1.1 table for variable fonts that lack a STAT table,
    using data from the fvar axes and named instances.

    Args:
        font: Variable TtfFont instance (must have fvar table)

    Returns:
        bytes: Serialized STAT 1.1 table, or None if font already has STAT table

    Raises:
        FontNotSupportedException: If font is not variable or lacks fvar
    """
    from aspose_font._exceptions import FontNotSupportedException

    if not hasattr(font, "fvar") or font.fvar is None:
        raise FontNotSupportedException("Font is not variable")

    raw_tables = getattr(font.ttf_tables, "_raw", {})
    if raw_tables.get("STAT") is not None:
        return None

    axes = font.axes
    instances = font.named_instances

    ordered_axes = _order_axes_standard(axes)
    design_axis_records = _build_design_axis_records(ordered_axes)
    axis_value_records = _build_axis_value_records(ordered_axes, instances)

    return _serialize_stat_table(ordered_axes, design_axis_records, axis_value_records)


def _order_axes_standard(axes: list[AxisRecord]) -> list[AxisRecord]:
    """Order axes in standard OpenType sequence.

    Standard order: opsz, wdth, wght, slnt, ital, then others alphabetically.
    Uses display_order from axis metadata, falling back to tag for ties.
    """
    ORDER_PRIORITY = {
        "opsz": 50,
        "wdth": 20,
        "wght": 10,
        "slnt": 40,
        "ital": 30,
    }

    def axis_sort_key(axis: AxisRecord) -> tuple[int, str]:
        priority = ORDER_PRIORITY.get(axis.tag, 1000)
        return (priority, axis.tag)

    return sorted(axes, key=axis_sort_key)


def _build_design_axis_records(ordered_axes: list[AxisRecord]) -> list[dict]:
    """Convert AxisRecord objects to STAT DesignAxis records."""
    records = []
    for index, axis in enumerate(ordered_axes):
        records.append({
            "axis_tag": axis.tag,
            "axis_name_id": axis.name_id,
            "axis_order": index,
        })
    return records


def _build_axis_value_records(
    ordered_axes: list[AxisRecord],
    instances: list["NamedInstance"],
    *,
    axis_value_flags: int = 0x0002,
) -> list[dict]:
    """Build AxisValue records for named instances.

    Creates Format 4 AxisValue records for each named instance,
    including all axis coordinates.

    Args:
        ordered_axes: Axes in standard order
        instances: Named instances from fvar
        axis_value_flags: Flags for AxisValue records (default: ELIDABLE_AXIS_VALUE_NAME)

    Returns:
        List of AxisValue record dictionaries
    """
    records = []
    axis_tag_to_index = {axis.tag: i for i, axis in enumerate(ordered_axes)}

    for instance in instances:
        axis_count = len(ordered_axes)
        axis_data = []
        for axis in ordered_axes:
            axis_index = axis_tag_to_index[axis.tag]
            coordinate = instance.coordinates.get(axis.tag, axis.default_value)
            axis_data.append((axis_index, coordinate))

        records.append({
            "format": 4,
            "flags": axis_value_flags,
            "value_name_id": instance.name_id,
            "axis_count": axis_count,
            "axis_data": axis_data,
        })

    return records


def _serialize_stat_table(
    ordered_axes: list[AxisRecord],
    design_axis_records: list[dict],
    axis_value_records: list[dict],
) -> bytes:
    """Serialize STAT table to bytes.

    Builds STAT 1.1 table with design axes and axis value records.
    """
    w = BinaryWriter()

    design_axis_size = 8
    design_axis_count = len(design_axis_records)
    design_axes_offset = 20
    axis_value_count = len(axis_value_records)
    axis_value_offsets_offset = design_axes_offset + (design_axis_count * design_axis_size)

    # Calculate axis value offsets (deltas from axis_value_offsets_offset)
    # Start calculating from the position right after the offset deltas array
    # Deltas array is axis_value_count * 2 bytes
    current_offset = axis_value_offsets_offset + (axis_value_count * 2)

    version_major = 1
    version_minor = 1

    w.write_u16(version_major)
    w.write_u16(version_minor)
    w.write_u16(design_axis_size)
    w.write_u16(design_axis_count)
    w.write_u32(design_axes_offset)
    w.write_u16(axis_value_count)
    w.write_u32(axis_value_offsets_offset)
    w.write_u16(2)

    for record in design_axis_records:
        w.write_bytes(record["axis_tag"].encode("ascii"))
        w.write_u16(record["axis_name_id"])
        w.write_u16(record["axis_order"])

    axis_value_offsets = []
    for record in axis_value_records:
        axis_value_offsets.append(current_offset)
        record_size = 8 + (record["axis_count"] * 6)
        current_offset += record_size

    for offset in axis_value_offsets:
        w.write_u16(offset - axis_value_offsets_offset)

    for record in axis_value_records:
        w.write_u16(record["format"])
        w.write_u16(record["flags"])
        w.write_u16(record["value_name_id"])
        w.write_u16(record["axis_count"])
        for axis_index, coordinate in record["axis_data"]:
            w.write_u16(axis_index)
            _write_fixed_16_16(w, coordinate)

    return w.to_bytes()
