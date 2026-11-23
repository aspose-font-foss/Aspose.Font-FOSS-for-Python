"""Minimal MVAR table parser for metric variations."""

from __future__ import annotations

from dataclasses import dataclass

from aspose_font._exceptions import FontParseException
from aspose_font._io import BinaryReader

from .hvar import DeltaSetIndex, ItemVariationStore


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
    item_variation_store: ItemVariationStore | None = None

    @classmethod
    def from_reader(cls, r: BinaryReader, length: int, *, axis_tags: list[str] | None = None) -> "MvarTable":
        """Parse MVAR table from binary data.
        Args:
            r: BinaryReader for the MVAR table data
            length: Total length of the MVAR table
            axis_tags: List of axis tags (from fvar table) for variation region evaluation.
                      If None, defaults to ["wght", "wdth"].
        """
        if axis_tags is None:
            axis_tags = ["wght", "wdth"]

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

        item_variation_store: ItemVariationStore | None = None
        remaining_bytes = length - rr.tell()
        if remaining_bytes > 0:
            try:
                store_data = rr.read_bytes(remaining_bytes)
                if store_data:
                    store_reader = BinaryReader(store_data)
                    item_variation_store = ItemVariationStore.from_reader(
                        store_reader,
                        axis_tags=axis_tags,
                    )
            except Exception:
                item_variation_store = None

        return cls(value_records=value_records, item_variation_store=item_variation_store)

    def evaluate(
        self,
        value_tag: str,
        outer_index: int = 0,
        inner_index: int = 0,
        *,
        axis_tag: str | None = None,
        coordinates: dict[str, float] | None = None,
    ) -> int:
        """
        Evaluate variation delta for a specific metric.

        Args:
            value_tag: Metric tag (e.g., 'hasc', 'hcdt', 'hvca' for horizontal;
                      'vasc', 'vcdt', 'vcrs' for vertical)
            outer_index: Outer delta set index
            inner_index: Inner delta set index
            axis_tag: Optional axis tag filter (e.g., 'wght')
            coordinates: Normalized variation coordinates. If None, uses neutral (0) coordinates.

        Returns:
            Delta value in font units, or 0 if no matching record or no variation data
        """
        if coordinates is None:
            coordinates = {}

        target_delta_index = (outer_index << 16) | (inner_index & 0xFFFF)
        matching_records = [
            r for r in self.value_records
            if r.value_tag == value_tag and r.delta_set_index == target_delta_index
        ]
        if axis_tag is not None:
            matching_records = [r for r in matching_records if r.axis_tag == axis_tag]

        if not matching_records:
            return 0

        if self.item_variation_store is None:
            return 0

        delta_set_index = DeltaSetIndex(outer=outer_index, inner=inner_index)
        delta = self.item_variation_store.evaluate(delta_set_index, coordinates)
        return int(delta)

    def get_metric_tags(self) -> set[str]:
        """Get all unique metric tags in this MVAR table."""
        return {r.value_tag for r in self.value_records}

    def get_axis_tags(self) -> set[str]:
        """Get all unique axis tags in this MVAR table."""
        return {r.axis_tag for r in self.value_records}
