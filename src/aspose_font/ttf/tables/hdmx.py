"""OpenType Device Metrics (hdmx & vdmx) table parsers."""
from __future__ import annotations

from dataclasses import dataclass

from aspose_font._exceptions import FontParseException
from aspose_font._io import BinaryReader


@dataclass(slots=True)
class HdmxRecord:
    """Single hdmx device record mapping PPEM to glyph widths."""
    pixel_size: int
    widths: list[int]


@dataclass(slots=True)
class VdmxGroup:
    """Single vdmx group with vertical extents for a pixel height."""
    y_pel_height: int
    y_max: int
    y_min: int


@dataclass(slots=True)
class HdmxTable:
    """OpenType hdmx (Horizontal Device Metrics) table."""
    version: int
    num_records: int
    size_device_record: int
    records: list[HdmxRecord]

    @classmethod
    def from_reader(cls, r: BinaryReader, length: int) -> "HdmxTable":
        """Parse hdmx table from binary reader."""
        rr = BinaryReader(r.read_bytes(length))
        version = rr.read_u16()
        num_records = rr.read_u16()
        size_device_record = rr.read_u32()

        if version not in (0x0000, 0x0001):
            raise FontParseException(
                f"Unsupported hdmx table version: 0x{version:04X}",
                format_name="TTF"
            )

        if num_records < 0 or size_device_record < 4:
            raise FontParseException(
                f"Invalid hdmx record count ({num_records}) or record size ({size_device_record})",
                format_name="TTF"
            )

        if version == 0x0000:
            num_glyphs = size_device_record - 4
            records: list[HdmxRecord] = []
            for i in range(num_records):
                widths = [rr.read_i8() for _ in range(num_glyphs)]
                records.append(HdmxRecord(pixel_size=i + 1, widths=widths))
        else:
            records: list[HdmxRecord] = []
            for i in range(num_records):
                pixel_size = rr.read_u8()
                width_count = rr.read_u8()
                widths: list[int] = []
                for _ in range(width_count):
                    widths.append(rr.read_i8())
                records.append(HdmxRecord(pixel_size=pixel_size, widths=widths))

        return cls(
            version=version,
            num_records=num_records,
            size_device_record=size_device_record,
            records=records
        )

    def get_metrics(self, ppem: int) -> tuple[int, int] | None:
        """Get advance width metrics for a given PPEM.

        Args:
            ppem: Pixel per em value (0-255)

        Returns:
            Tuple of (max_width, min_width) or None if PPEM not found.
        """
        for record in self.records:
            if record.pixel_size == ppem:
                if record.widths:
                    return (max(record.widths), min(record.widths))
                return None
        return None


@dataclass(slots=True)
class VdmxTable:
    """OpenType vdmx (Vertical Device Metrics) table."""
    version: int
    num_recs: int
    num_ratios: int
    ratio_range_table: list[dict]
    groups: list[VdmxGroup]

    @classmethod
    def from_reader(cls, r: BinaryReader, length: int) -> "VdmxTable":
        """Parse vdmx table from binary reader."""
        rr = BinaryReader(r.read_bytes(length))
        version = rr.read_u16()

        if version not in (0x0000, 0x0001):
            raise FontParseException(
                f"Unsupported vdmx table version: 0x{version:04X}",
                format_name="TTF"
            )

        num_recs = rr.read_u16()
        num_ratios = rr.read_u8()
        rr.read_u8()
        rr.read_u16()
        rr.read_u16()
        rr.read_u16()

        ratio_range_table: list[dict] = []
        for _ in range(num_ratios):
            ratio_range_table.append({
                "aspect_ratio": rr.read_u8(),
                "start_ratio": rr.read_u8(),
                "end_ratio": rr.read_u8(),
                "range_start": rr.read_u8(),
                "range_end": rr.read_u8(),
            })

        groups: list[VdmxGroup] = []
        for _ in range(num_recs):
            y_pel_height = rr.read_u8()
            y_max = rr.read_i16()
            y_min = rr.read_i16()
            groups.append(VdmxGroup(y_pel_height=y_pel_height, y_max=y_max, y_min=y_min))

        return cls(
            version=version,
            num_recs=num_recs,
            num_ratios=num_ratios,
            ratio_range_table=ratio_range_table,
            groups=groups
        )

    def get_metrics(self, ppem: int) -> tuple[int, int] | None:
        """Get vertical extent metrics for a given PPEM.

        Args:
            ppem: Pixel per em value (matches yPelHeight field)

        Returns:
            Tuple of (yMax, yMin) for vertical text layout or None if PPEM not found.
        """
        for group in self.groups:
            if group.y_pel_height == ppem:
                return (group.y_max, group.y_min)
        return None
