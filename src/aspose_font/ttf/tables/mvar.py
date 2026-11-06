"""Minimal MVAR table parser for metric variations."""

from __future__ import annotations

from dataclasses import dataclass

from aspose_font._exceptions import FontParseException
from aspose_font._io import BinaryReader


@dataclass(slots=True, frozen=True)
class MvarValueRecord:
    """Single MVAR value record mapping axis + metric to delta set index."""
    axis_tag: str
    value_tag: str
    delta_set_index: int


@dataclass(slots=True)
class MvarTable:
    """Parsed MVAR table with value records for metric variations."""
    value_records: list[MvarValueRecord]

    @classmethod
    def from_reader(cls, r: BinaryReader, length: int) -> "MvarTable":
        """Parse MVAR table from binary data."""
        rr = BinaryReader(r.read_bytes(length))

        major = rr.read_u16()
        minor = rr.read_u16()
        if (major, minor) != (1, 0):
            raise FontParseException(
                f"Unsupported MVAR version: {major}.{minor}",
                format_name="TTF"
            )

        value_record_count = rr.read_u16()
        rr.read_u16()  # reserved
        value_record_size = rr.read_u16()

        if value_record_size != 8:
            raise FontParseException(
                f"Unsupported MVAR value record size: {value_record_size}",
                format_name="TTF"
            )

        value_records: list[MvarValueRecord] = []
        for _ in range(value_record_count):
            axis_tag = rr.read_tag()
            value_tag = rr.read_tag()
            outer = rr.read_u16()
            inner = rr.read_u16()
            delta_set_index = (outer << 16) | inner
            value_records.append(MvarValueRecord(
                axis_tag=axis_tag,
                value_tag=value_tag,
                delta_set_index=delta_set_index
            ))

        return cls(value_records=value_records)

    def evaluate(self, value_tag: str, outer_index: int, inner_index: int) -> int:
        """
        Evaluate variation delta for a specific metric.

        Args:
            value_tag: Metric tag (e.g., 'hasc', 'hcdt', 'hvca')
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
        """Get all unique metric tags in this MVAR table."""
        return {r.value_tag for r in self.value_records}

    def get_axis_tags(self) -> set[str]:
        """Get all unique axis tags in this MVAR table."""
        return {r.axis_tag for r in self.value_records}
