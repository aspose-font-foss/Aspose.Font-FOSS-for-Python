"""Minimal HVAR parser for horizontal metric variation."""

from __future__ import annotations

from dataclasses import dataclass

from aspose_font._exceptions import FontParseException
from aspose_font._io import BinaryReader


@dataclass(slots=True, frozen=True)
class DeltaSetIndex:
    outer: int
    inner: int


@dataclass(slots=True)
class DeltaSetIndexMap:
    entries: list[DeltaSetIndex]

    @classmethod
    def from_reader(cls, r: BinaryReader) -> "DeltaSetIndexMap":
        format_ = r.read_u8()
        entry_format = r.read_u8()
        if format_ == 0:
            map_count = r.read_u16()
        elif format_ == 1:
            map_count = r.read_u32()
        else:
            raise FontParseException(f"Unsupported DeltaSetIndexMap format: {format_}")

        entry_size = ((entry_format & 0x30) >> 4) + 1
        inner_index_bits = (entry_format & 0x0F) + 1
        inner_mask = (1 << inner_index_bits) - 1
        entries: list[DeltaSetIndex] = []
        for _ in range(map_count):
            raw_value = int.from_bytes(r.read_bytes(entry_size), "big")
            entries.append(
                DeltaSetIndex(
                    outer=raw_value >> inner_index_bits,
                    inner=raw_value & inner_mask,
                )
            )
        return cls(entries=entries)

    def get(self, gid: int) -> DeltaSetIndex:
        if not self.entries:
            return DeltaSetIndex(outer=0, inner=gid)
        if gid < len(self.entries):
            return self.entries[gid]
        return self.entries[-1]


@dataclass(slots=True, frozen=True)
class VariationRegionAxis:
    start: float
    peak: float
    end: float

    def scalar(self, coordinate: float) -> float:
        if self.peak == 0.0:
            return 1.0
        if coordinate == self.peak:
            return 1.0
        if coordinate <= min(self.start, self.end) or coordinate >= max(self.start, self.end):
            if coordinate == self.start == self.peak or coordinate == self.end == self.peak:
                return 1.0
            return 0.0
        if coordinate < self.peak:
            denom = self.peak - self.start
            if denom == 0.0:
                return 0.0
            return (coordinate - self.start) / denom
        denom = self.end - self.peak
        if denom == 0.0:
            return 0.0
        return (self.end - coordinate) / denom


@dataclass(slots=True)
class VariationRegion:
    axes: list[VariationRegionAxis]

    def scalar(self, coordinates: dict[str, float], axis_tags: list[str]) -> float:
        scalar = 1.0
        for axis_tag, axis_region in zip(axis_tags, self.axes):
            factor = axis_region.scalar(coordinates.get(axis_tag, 0.0))
            if factor == 0.0:
                return 0.0
            scalar *= factor
        return scalar


@dataclass(slots=True)
class ItemVariationData:
    region_indexes: list[int]
    delta_sets: list[list[int]]

    @classmethod
    def from_reader(cls, r: BinaryReader) -> "ItemVariationData":
        item_count = r.read_u16()
        word_delta_count_raw = r.read_u16()
        region_index_count = r.read_u16()
        long_words = bool(word_delta_count_raw & 0x8000)
        word_delta_count = word_delta_count_raw & 0x7FFF
        region_indexes = [r.read_u16() for _ in range(region_index_count)]
        delta_sets: list[list[int]] = []
        for _ in range(item_count):
            deltas: list[int] = []
            for _ in range(word_delta_count):
                deltas.append(r.read_i32() if long_words else r.read_i16())
            for _ in range(region_index_count - word_delta_count):
                deltas.append(r.read_i16() if long_words else r.read_i8())
            delta_sets.append(deltas)
        return cls(region_indexes=region_indexes, delta_sets=delta_sets)

    def evaluate(
        self,
        inner_index: int,
        *,
        regions: list[VariationRegion],
        coordinates: dict[str, float],
        axis_tags: list[str],
    ) -> float:
        if inner_index >= len(self.delta_sets):
            return 0.0
        total = 0.0
        for region_index, delta in zip(self.region_indexes, self.delta_sets[inner_index]):
            if region_index >= len(regions):
                continue
            total += delta * regions[region_index].scalar(coordinates, axis_tags)
        return total


@dataclass(slots=True)
class ItemVariationStore:
    axis_tags: list[str]
    regions: list[VariationRegion]
    subtables: list[ItemVariationData]

    @classmethod
    def from_reader(
        cls,
        r: BinaryReader,
        *,
        axis_tags: list[str],
    ) -> "ItemVariationStore":
        store_start = r.tell()
        format_ = r.read_u16()
        if format_ != 1:
            raise FontParseException(f"Unsupported ItemVariationStore format: {format_}")
        variation_region_list_offset = r.read_u32()
        item_variation_data_count = r.read_u16()
        item_variation_data_offsets = [r.read_u32() for _ in range(item_variation_data_count)]

        r.seek(store_start + variation_region_list_offset)
        axis_count = r.read_u16()
        region_count = r.read_u16()
        if axis_count != len(axis_tags):
            raise FontParseException(
                f"ItemVariationStore axis count {axis_count} does not match fvar axis count {len(axis_tags)}"
            )
        regions: list[VariationRegion] = []
        for _ in range(region_count):
            axes = [
                VariationRegionAxis(
                    start=r.read_f2dot14(),
                    peak=r.read_f2dot14(),
                    end=r.read_f2dot14(),
                )
                for _ in range(axis_count)
            ]
            regions.append(VariationRegion(axes=axes))

        subtables: list[ItemVariationData] = []
        for offset in item_variation_data_offsets:
            r.seek(store_start + offset)
            subtables.append(ItemVariationData.from_reader(r))
        return cls(axis_tags=axis_tags, regions=regions, subtables=subtables)

    def evaluate(self, delta_set_index: DeltaSetIndex, coordinates: dict[str, float]) -> float:
        if delta_set_index.outer >= len(self.subtables):
            return 0.0
        return self.subtables[delta_set_index.outer].evaluate(
            delta_set_index.inner,
            regions=self.regions,
            coordinates=coordinates,
            axis_tags=self.axis_tags,
        )


@dataclass(slots=True)
class HvarTable:
    advance_width_mapping: DeltaSetIndexMap | None
    item_variation_store: ItemVariationStore

    @classmethod
    def from_reader(
        cls,
        r: BinaryReader,
        table_length: int,
        *,
        axis_tags: list[str],
    ) -> "HvarTable":
        rr = BinaryReader(r.read_bytes(table_length))
        major_version = rr.read_u16()
        minor_version = rr.read_u16()
        if (major_version, minor_version) != (1, 0):
            raise FontParseException(
                f"Unsupported HVAR version: {major_version}.{minor_version}"
            )
        item_variation_store_offset = rr.read_u32()
        advance_width_mapping_offset = rr.read_u32()
        rr.read_u32()  # lsbMappingOffset
        rr.read_u32()  # rsbMappingOffset

        advance_width_mapping = None
        if advance_width_mapping_offset != 0:
            rr.seek(advance_width_mapping_offset)
            advance_width_mapping = DeltaSetIndexMap.from_reader(rr)

        rr.seek(item_variation_store_offset)
        item_variation_store = ItemVariationStore.from_reader(
            rr,
            axis_tags=axis_tags,
        )
        return cls(
            advance_width_mapping=advance_width_mapping,
            item_variation_store=item_variation_store,
        )

    def advance_width_delta(self, gid: int, normalized_coordinates: dict[str, float]) -> float:
        mapping = (
            self.advance_width_mapping.get(gid)
            if self.advance_width_mapping is not None
            else DeltaSetIndex(outer=0, inner=gid)
        )
        return self.item_variation_store.evaluate(mapping, normalized_coordinates)
