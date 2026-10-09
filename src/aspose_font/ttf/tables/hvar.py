"""Minimal HVAR parser for horizontal metric variation."""

from __future__ import annotations

from dataclasses import dataclass

from aspose_font._exceptions import FontParseException
from aspose_font._io import BinaryReader, BinaryWriter


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

    def to_bytes(self) -> bytes:
        writer = BinaryWriter()
        if not self.entries:
            writer.write_u8(0)
            writer.write_u8(0)
            writer.write_u16(0)
            return writer.to_bytes()

        format_ = 0
        if len(self.entries) > 65535:
            format_ = 1

        entry_format = 0
        max_outer = 0
        max_inner = 0
        for entry in self.entries:
            max_outer = max(max_outer, entry.outer)
            max_inner = max(max_inner, entry.inner)

        outer_bits = max_outer.bit_length()
        inner_bits = max_inner.bit_length()

        if outer_bits == 0:
            outer_bits = 1
        if inner_bits == 0:
            inner_bits = 1

        outer_size = (outer_bits + 7) // 8
        inner_size = (inner_bits + 7) // 8
        entry_size = outer_size + inner_size

        if entry_size > 4:
            entry_size = 4
        outer_size = entry_size - 1 if entry_size > 1 else 0

        entry_format = (min(3, outer_size) << 4) | (min(15, inner_bits - 1))

        writer.write_u8(format_)
        writer.write_u8(entry_format)

        if format_ == 0:
            writer.write_u16(len(self.entries))
        else:
            writer.write_u32(len(self.entries))

        inner_mask = (1 << ((entry_format & 0x0F) + 1)) - 1
        for entry in self.entries:
            raw_value = (entry.outer << ((entry_format & 0x0F) + 1)) | (entry.inner & inner_mask)
            writer.write_bytes(raw_value.to_bytes(entry_size, "big"))
        return writer.to_bytes()


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

    def to_bytes(self) -> bytes:
        writer = BinaryWriter()
        writer.write_u16(len(self.delta_sets))

        word_delta_count = len(self.region_indexes)
        word_delta_count_raw = word_delta_count & 0x7FFF
        long_words = any(abs(d) > 32767 for deltas in self.delta_sets for d in deltas)
        if long_words:
            word_delta_count_raw |= 0x8000

        writer.write_u16(word_delta_count_raw)
        writer.write_u16(len(self.region_indexes))

        for region_index in self.region_indexes:
            writer.write_u16(region_index)

        for deltas in self.delta_sets:
            for i, delta in enumerate(deltas):
                if i < word_delta_count:
                    if long_words:
                        writer.write_i32(delta)
                    else:
                        writer.write_i16(delta)
                else:
                    if long_words:
                        writer.write_i16(delta)
                    else:
                        writer.write_i8(delta)

        return writer.to_bytes()


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

    def _serialize_variation_region_list(self) -> bytes:
        writer = BinaryWriter()
        writer.write_u16(len(self.axis_tags))
        writer.write_u16(len(self.regions))

        for region in self.regions:
            for axis in region.axes:
                writer.write_f2dot14(axis.start)
                writer.write_f2dot14(axis.peak)
                writer.write_f2dot14(axis.end)

        return writer.to_bytes()

    def to_bytes(self) -> bytes:
        region_list_bytes = self._serialize_variation_region_list()

        item_variation_data_offsets = []
        item_variation_data_bytes = b""

        for subtable in self.subtables:
            item_variation_data_offsets.append(len(item_variation_data_bytes))
            item_variation_data_bytes += subtable.to_bytes()

        region_list_offset = 12
        item_variation_data_offset = region_list_offset + len(region_list_bytes)

        writer = BinaryWriter()
        writer.write_u16(1)
        writer.write_u32(region_list_offset)
        writer.write_u16(len(self.subtables))

        for offset in item_variation_data_offsets:
            writer.write_u32(item_variation_data_offset + offset)

        writer.write_bytes(region_list_bytes)
        writer.write_bytes(item_variation_data_bytes)

        return writer.to_bytes()


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

    def to_bytes(self) -> bytes:
        item_variation_store_bytes = self.item_variation_store.to_bytes()

        advance_width_mapping_bytes = b""
        advance_width_mapping_offset = 0

        if self.advance_width_mapping is not None:
            advance_width_mapping_bytes = self.advance_width_mapping.to_bytes()
            advance_width_mapping_offset = 24 + len(item_variation_store_bytes)

        writer = BinaryWriter()
        writer.write_u16(1)
        writer.write_u16(0)
        writer.write_u32(24)
        writer.write_u32(advance_width_mapping_offset)
        writer.write_u32(0)
        writer.write_u32(0)
        writer.write_bytes(item_variation_store_bytes)

        if advance_width_mapping_bytes:
            padding = (4 - (len(writer.to_bytes()) % 4)) % 4
            writer.write_bytes(b"\x00" * padding)
            writer.write_bytes(advance_width_mapping_bytes)

        return writer.to_bytes()
