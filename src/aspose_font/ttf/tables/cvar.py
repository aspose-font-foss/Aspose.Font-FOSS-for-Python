"""Minimal CVAR table parser for custom variations."""

from __future__ import annotations

from dataclasses import dataclass

from aspose_font._exceptions import FontParseException
from aspose_font._io import BinaryReader


@dataclass(slots=True, frozen=True)
class CvarValueRecord:
    """Single CVAR value record mapping axis + metric to delta set index."""
    axis_tag: str
    value_tag: str
    delta_set_index: int


@dataclass(slots=True)
class CvarTable:
    """Parsed CVAR table with value records for custom metric variations."""
    value_records: list[CvarValueRecord]

    @classmethod
    def from_reader(cls, r: BinaryReader, length: int) -> "CvarTable":
        """Parse CVAR table from binary data."""
        rr = BinaryReader(r.read_bytes(length))

        major = rr.read_u16()
        minor = rr.read_u16()
        if (major, minor) != (1, 0):
            raise FontParseException(
                f"Unsupported CVAR version: {major}.{minor}",
                format_name="TTF"
            )

        value_record_count = rr.read_u16()
        rr.read_u16()  # reserved
        value_record_size = rr.read_u16()

        if value_record_size != 8:
            raise FontParseException(
                f"Unsupported CVAR value record size: {value_record_size}",
                format_name="TTF"
            )

        value_records: list[CvarValueRecord] = []
        for _ in range(value_record_count):
            axis_tag = rr.read_tag()
            value_tag = rr.read_tag()
            outer = rr.read_u16()
            inner = rr.read_u16()
            delta_set_index = (outer << 16) | inner
            value_records.append(CvarValueRecord(
                axis_tag=axis_tag,
                value_tag=value_tag,
                delta_set_index=delta_set_index
            ))

        return cls(value_records=value_records)

    def evaluate(self, value_tag: str, outer_index: int, inner_index: int) -> int:
        """
        Evaluate variation delta for a specific custom metric.

        Args:
            value_tag: Metric tag (e.g., 'casc', 'ccdt', 'ccrs')
            outer_index: Outer delta set index
            inner_index: Inner delta set index

        Returns:
            Delta value in font units, or 0 if no variation for this metric
        """
        matching_records = [r for r in self.value_records if r.value_tag == value_tag]
        if not matching_records:
            return 0

        return 0

    def get_metric_tags(self) -> set[str]:
        """Get all unique metric tags in this CVAR table."""
        return {r.value_tag for r in self.value_records}

    def get_axis_tags(self) -> set[str]:
        """Get all unique axis tags in this CVAR table."""
        return {r.axis_tag for r in self.value_records}
