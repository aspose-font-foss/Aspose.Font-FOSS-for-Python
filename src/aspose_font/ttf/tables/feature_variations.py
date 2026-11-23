"""Minimal FeatureVariations parser for OpenType font variations."""

from __future__ import annotations

from dataclasses import dataclass

from aspose_font._exceptions import FontParseException
from aspose_font._io import BinaryReader, BinaryWriter


@dataclass(slots=True, frozen=True)
class FeatureVariationRecord:
    trigger_axis_index: int
    trigger_axis_min: float
    trigger_axis_max: float
    feature_table_offset: int


@dataclass(slots=True)
class FeatureVariationTable:
    records: list[FeatureVariationRecord]
    feature_tags: list[str]

    @classmethod
    def from_reader(cls, r: BinaryReader, table_length: int) -> "FeatureVariationTable":
        rr = BinaryReader(r.read_bytes(table_length))
        version = rr.read_u32()
        if version != 0x00010000:
            raise FontParseException(f"Unsupported FeatureVariations version: 0x{version:08X}")

        feature_variations_count = rr.read_u16()
        feature_tags_count = rr.read_u16()
        feature_tag_list_offset = rr.read_u32()

        records: list[FeatureVariationRecord] = []
        for _ in range(feature_variations_count):
            trigger_axis_index = rr.read_u16()
            axis_min_value = rr.read_f2dot14()
            axis_max_value = rr.read_f2dot14()
            feature_table_offset = rr.read_u32()
            records.append(
                FeatureVariationRecord(
                    trigger_axis_index=trigger_axis_index,
                    trigger_axis_min=axis_min_value,
                    trigger_axis_max=axis_max_value,
                    feature_table_offset=feature_table_offset,
                )
            )

        rr.seek(feature_tag_list_offset)
        feature_tags: list[str] = []
        for _ in range(feature_tags_count):
            feature_tag = rr.read_tag()
            feature_tags.append(feature_tag)

        return cls(records=records, feature_tags=feature_tags)

    def find_applicable_records(
        self, coordinates: dict[str, float], axis_tags: list[str]
    ) -> list[FeatureVariationRecord]:
        applicable: list[FeatureVariationRecord] = []
        for record in self.records:
            if record.trigger_axis_index >= len(axis_tags):
                continue
            axis_tag = axis_tags[record.trigger_axis_index]
            coordinate = coordinates.get(axis_tag, 0.0)
            min_val = min(record.trigger_axis_min, record.trigger_axis_max)
            max_val = max(record.trigger_axis_min, record.trigger_axis_max)
            if min_val <= coordinate <= max_val:
                applicable.append(record)
        return applicable

    def to_bytes(self) -> bytes:
        writer = BinaryWriter()
        writer.write_u32(0x00010000)
        writer.write_u16(len(self.records))
        writer.write_u16(len(self.feature_tags))
        feature_tag_list_offset = 12 + len(self.records) * 12
        writer.write_u32(feature_tag_list_offset)

        for record in self.records:
            writer.write_u16(record.trigger_axis_index)
            writer.write_f2dot14(record.trigger_axis_min)
            writer.write_f2dot14(record.trigger_axis_max)
            writer.write_u32(record.feature_table_offset)

        for tag in self.feature_tags:
            writer.write_tag(tag)

        return writer.to_bytes()
