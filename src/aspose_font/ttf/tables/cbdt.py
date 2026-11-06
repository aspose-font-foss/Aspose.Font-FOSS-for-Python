"""OpenType CBLC (Color Bitmap Location) and CBDT (Color Bitmap Data) table parser for Android color emoji."""

from __future__ import annotations

from dataclasses import dataclass

from aspose_font._exceptions import FontParseException
from aspose_font._io import BinaryReader


@dataclass(slots=True)
class CblcStrike:
    """Represents one bitmap strike (resolution) in the CBLC table."""
    ppem: int
    max_ppem: int | None
    bit_depth: int
    flags: int
    offset_to_index_subtable: int = 0


@dataclass(slots=True)
class CblcMetricsSmall:
    """Small metrics (16-bit values) for Format 17."""
    width: int
    height: int
    bit_depth: int
    horizontal_origin_x: int
    horizontal_origin_y: int
    vertical_origin_x: int
    vertical_origin_y: int


@dataclass(slots=True)
class CblcMetricsBig:
    """Big metrics (32-bit values) for Format 18."""
    width: int
    height: int
    bit_depth: int
    horizontal_origin_x: int
    horizontal_origin_y: int
    vertical_origin_x: int
    vertical_origin_y: int
    horizontal_advance: int
    vertical_advance: int
    horizontal_bearing_x: int
    horizontal_bearing_y: int
    vertical_bearing_x: int
    vertical_bearing_y: int


class CblcIndexSubTable:
    """Base class for CBLC index subtables."""

    format: int
    first_glyph_id: int
    last_glyph_id: int
    additional_offset: int


@dataclass(slots=True)
class CblcIndexSubTableFormat17(CblcIndexSubTable):
    """Format 17: Small metrics variant."""
    format: int
    first_glyph_id: int
    last_glyph_id: int
    additional_offset: int
    data_format: int
    metrics: CblcMetricsSmall
    offsets: list[int]


@dataclass(slots=True)
class CblcIndexSubTableFormat18(CblcIndexSubTable):
    """Format 18: Big metrics variant."""
    format: int
    first_glyph_id: int
    last_glyph_id: int
    additional_offset: int
    data_format: int
    metrics: CblcMetricsBig
    offsets: list[int]


@dataclass(slots=True)
class CbdtGlyphBitmap:
    """Single bitmap glyph record from CBDT table."""
    glyph_id: int
    data_format: int
    bitmap_data: bytes
    width: int
    height: int
    bearing_x: int
    bearing_y: int
    advance: int


@dataclass
class CblcTable:
    """Color Bitmap Location Table (CBLC)."""
    version: int
    strikes: list[CblcStrike]
    index_subtables: list[CblcIndexSubTable]
    _cbdtable_raw: bytes | None = None

    @classmethod
    def from_reader(cls, r: BinaryReader, table_length: int) -> "CblcTable":
        """Parse CBLC table from binary reader."""
        raw = r.read_bytes(table_length)
        rr = BinaryReader(raw)

        version = rr.read_u32()
        num_strikes = rr.read_u32()

        if version not in (0x00020000, 0x00030000):
            raise FontParseException(
                f"Unsupported CBLC table version {version:#010x}",
                format_name="TTF"
            )

        strikes: list[CblcStrike] = []
        for _ in range(num_strikes):
            ppem = rr.read_u8()
            max_ppem = rr.read_u8()
            bit_depth = rr.read_u8()
            flags = rr.read_u8()
            _offset_to_index_subtable = rr.read_u32()
            strikes.append(CblcStrike(
                ppem=ppem,
                max_ppem=max_ppem if max_ppem > 0 else None,
                bit_depth=bit_depth,
                flags=flags,
                offset_to_index_subtable=_offset_to_index_subtable
            ))

        index_subtables: list[CblcIndexSubTable] = []
        seen_offsets: set[int] = set()
        for strike in strikes:
            if strike.offset_to_index_subtable == 0:
                continue
            if strike.offset_to_index_subtable in seen_offsets:
                continue
            seen_offsets.add(strike.offset_to_index_subtable)
            rr.seek(strike.offset_to_index_subtable)
            format_num = rr.read_u16()
            first_glyph_id = rr.read_u16()
            last_glyph_id = rr.read_u16()
            additional_offset = rr.read_u32()

            if format_num == 17:
                _data_format = rr.read_u8()
                rr.seek(rr.tell() + 3)
                _width = rr.read_u16()
                _height = rr.read_u16()
                _bit_depth = rr.read_u8()
                _horizontal_origin_x = rr.read_u8()
                _horizontal_origin_y = rr.read_u8()
                _vertical_origin_x = rr.read_u8()
                _vertical_origin_y = rr.read_u8()
                metrics = CblcMetricsSmall(
                    width=_width,
                    height=_height,
                    bit_depth=_bit_depth,
                    horizontal_origin_x=_horizontal_origin_x,
                    horizontal_origin_y=_horizontal_origin_y,
                    vertical_origin_x=_vertical_origin_x,
                    vertical_origin_y=_vertical_origin_y
                )
                num_offsets = last_glyph_id - first_glyph_id + 1
                offsets = [rr.read_u32() for _ in range(num_offsets)]
                subtable = CblcIndexSubTableFormat17(
                    format=format_num,
                    first_glyph_id=first_glyph_id,
                    last_glyph_id=last_glyph_id,
                    additional_offset=additional_offset,
                    data_format=_data_format,
                    metrics=metrics,
                    offsets=offsets
                )
            elif format_num == 18:
                _data_format = rr.read_u8()
                rr.seek(rr.tell() + 3)
                _width = rr.read_u32()
                _height = rr.read_u32()
                _bit_depth = rr.read_u8()
                _horizontal_origin_x = rr.read_u8()
                _horizontal_origin_y = rr.read_u8()
                _vertical_origin_x = rr.read_u8()
                _vertical_origin_y = rr.read_u8()
                _horizontal_advance = rr.read_u32()
                _vertical_advance = rr.read_u32()
                _horizontal_bearing_x = rr.read_u32()
                _horizontal_bearing_y = rr.read_u32()
                _vertical_bearing_x = rr.read_u32()
                _vertical_bearing_y = rr.read_u32()
                metrics = CblcMetricsBig(
                    width=_width,
                    height=_height,
                    bit_depth=_bit_depth,
                    horizontal_origin_x=_horizontal_origin_x,
                    horizontal_origin_y=_horizontal_origin_y,
                    vertical_origin_x=_vertical_origin_x,
                    vertical_origin_y=_vertical_origin_y,
                    horizontal_advance=_horizontal_advance,
                    vertical_advance=_vertical_advance,
                    horizontal_bearing_x=_horizontal_bearing_x,
                    horizontal_bearing_y=_horizontal_bearing_y,
                    vertical_bearing_x=_vertical_bearing_x,
                    vertical_bearing_y=_vertical_bearing_y
                )
                num_offsets = last_glyph_id - first_glyph_id + 1
                offsets = [rr.read_u32() for _ in range(num_offsets)]
                subtable = CblcIndexSubTableFormat18(
                    format=format_num,
                    first_glyph_id=first_glyph_id,
                    last_glyph_id=last_glyph_id,
                    additional_offset=additional_offset,
                    data_format=_data_format,
                    metrics=metrics,
                    offsets=offsets
                )
            else:
                raise FontParseException(
                    f"Unsupported CBLC index subtable format {format_num}",
                    format_name="TTF"
                )

            index_subtables.append(subtable)

        return cls(
            version=version,
            strikes=strikes,
            index_subtables=index_subtables,
            _cbdtable_raw=None
        )

    def get_strikes(self) -> list[int]:
        """Return list of ppem values, sorted ascending."""
        return sorted(strike.ppem for strike in self.strikes)

    def get_glyph_bitmap(self, glyph_id: int, ppem: int | None = None) -> bytes | None:
        """Get raw bitmap data for a glyph. If ppem is None, use highest available."""
        if not self.strikes:
            return None

        if ppem is None:
            ppem = max(strike.ppem for strike in self.strikes)

        strike = next((s for s in self.strikes if s.ppem == ppem), None)
        if strike is None:
            return None

        subtable = next(
            (s for s in self.index_subtables
             if s.first_glyph_id <= glyph_id <= s.last_glyph_id),
            None
        )
        if subtable is None:
            return None

        index = glyph_id - subtable.first_glyph_id
        if index >= len(subtable.offsets):
            return None

        return self._extract_glyph_data(subtable, index)

    def _extract_glyph_data(self, subtable: CblcIndexSubTable, index: int) -> bytes | None:
        offset = subtable.offsets[index]
        if offset == 0:
            return None

        if self._cbdtable_raw is None:
            return None

        data_start = subtable.additional_offset + offset
        if data_start + 4 > len(self._cbdtable_raw):
            return None

        data_format = self._cbdtable_raw[data_start]
        rr = BinaryReader(self._cbdtable_raw[data_start:])
        rr.seek(4)

        if isinstance(subtable, CblcIndexSubTableFormat17):
            _width = subtable.metrics.width
            _height = subtable.metrics.height
            _bearing_x = subtable.metrics.horizontal_origin_x
            _bearing_y = subtable.metrics.horizontal_origin_y
            _advance = subtable.metrics.width
        elif isinstance(subtable, CblcIndexSubTableFormat18):
            _width = subtable.metrics.width
            _height = subtable.metrics.height
            _bearing_x = subtable.metrics.horizontal_origin_x
            _bearing_y = subtable.metrics.horizontal_origin_y
            _advance = subtable.metrics.horizontal_advance
        else:
            _width = 0
            _height = 0
            _bearing_x = 0
            _bearing_y = 0
            _advance = 0

        if data_format == 1:
            glyph_length = rr.read_u32()
            bitmap_data = rr.read_bytes(glyph_length)
        elif data_format == 2:
            glyph_length = rr.read_u32()
            bitmap_data = rr.read_bytes(glyph_length)
        elif data_format == 3:
            glyph_length = rr.read_u32()
            bitmap_data = rr.read_bytes(glyph_length)
        elif data_format == 4:
            glyph_length = rr.read_u32()
            bitmap_data = rr.read_bytes(glyph_length)
        else:
            glyph_length = 0
            bitmap_data = b""

        return bitmap_data

    def to_bytes(self) -> bytes:
        """Serialize CBLC table to binary."""
        raise NotImplementedError("CblcTable serialization not yet implemented")


@dataclass
class CbdtTable:
    """Color Bitmap Data Table (CBDT)."""
    version: int
    strikes: list[CblcStrike]
    bitmaps: list[CbdtGlyphBitmap]

    @classmethod
    def from_reader(cls, r: BinaryReader, table_length: int) -> "CbdtTable":
        """Parse CBDT table from binary reader."""
        raw = r.read_bytes(table_length)
        rr = BinaryReader(raw)

        version = rr.read_u32()
        num_strikes = rr.read_u32()

        if version not in (0x00020000, 0x00030000):
            raise FontParseException(
                f"Unsupported CBDT table version {version:#010x}",
                format_name="TTF"
            )

        strikes: list[CblcStrike] = []
        for _ in range(num_strikes):
            ppem = rr.read_u8()
            max_ppem = rr.read_u8()
            bit_depth = rr.read_u8()
            flags = rr.read_u8()
            _offset_to_index_subtable = rr.read_u32()
            strikes.append(CblcStrike(
                ppem=ppem,
                max_ppem=max_ppem if max_ppem > 0 else None,
                bit_depth=bit_depth,
                flags=flags,
                offset_to_index_subtable=_offset_to_index_subtable
            ))

        bitmaps: list[CbdtGlyphBitmap] = []
        for strike_index, strike in enumerate(strikes):
            if strike.offset_to_index_subtable == 0:
                continue
            rr.seek(strike.offset_to_index_subtable)
            format_num = rr.read_u16()
            first_glyph_id = rr.read_u16()
            last_glyph_id = rr.read_u16()
            additional_offset = rr.read_u32()

            num_glyphs = last_glyph_id - first_glyph_id + 1

            if format_num == 17:
                _data_format = rr.read_u8()
                rr.seek(rr.tell() + 3)
                _width = rr.read_u16()
                _height = rr.read_u16()
                _bit_depth = rr.read_u8()
                _horizontal_origin_x = rr.read_u8()
                _horizontal_origin_y = rr.read_u8()
                _vertical_origin_x = rr.read_u8()
                _vertical_origin_y = rr.read_u8()
                metrics = CblcMetricsSmall(
                    width=_width,
                    height=_height,
                    bit_depth=_bit_depth,
                    horizontal_origin_x=_horizontal_origin_x,
                    horizontal_origin_y=_horizontal_origin_y,
                    vertical_origin_x=_vertical_origin_x,
                    vertical_origin_y=_vertical_origin_y
                )
                offsets = [rr.read_u32() for _ in range(num_glyphs)]

                for i in range(num_glyphs):
                    glyph_id = first_glyph_id + i
                    offset = offsets[i]
                    data_start = additional_offset + offset
                    if data_start + 4 > len(raw):
                        continue
                    data_format_byte = raw[data_start]
                    data_rr = BinaryReader(raw[data_start:])
                    data_rr.seek(4)
                    if data_format_byte == 1:
                        glyph_length = data_rr.read_u32()
                        bitmap_data = data_rr.read_bytes(glyph_length)
                    elif data_format_byte == 2:
                        glyph_length = data_rr.read_u32()
                        bitmap_data = data_rr.read_bytes(glyph_length)
                    elif data_format_byte == 3:
                        glyph_length = data_rr.read_u32()
                        bitmap_data = data_rr.read_bytes(glyph_length)
                    elif data_format_byte == 4:
                        glyph_length = data_rr.read_u32()
                        bitmap_data = data_rr.read_bytes(glyph_length)
                    else:
                        bitmap_data = b""
                    bitmaps.append(CbdtGlyphBitmap(
                        glyph_id=glyph_id,
                        data_format=data_format_byte,
                        bitmap_data=bitmap_data,
                        width=metrics.width,
                        height=metrics.height,
                        bearing_x=metrics.horizontal_origin_x,
                        bearing_y=metrics.horizontal_origin_y,
                        advance=metrics.width
                    ))

            elif format_num == 18:
                _data_format = rr.read_u8()
                rr.seek(rr.tell() + 3)
                _width = rr.read_u32()
                _height = rr.read_u32()
                _bit_depth = rr.read_u8()
                _horizontal_origin_x = rr.read_u8()
                _horizontal_origin_y = rr.read_u8()
                _vertical_origin_x = rr.read_u8()
                _vertical_origin_y = rr.read_u8()
                _horizontal_advance = rr.read_u32()
                _vertical_advance = rr.read_u32()
                _horizontal_bearing_x = rr.read_u32()
                _horizontal_bearing_y = rr.read_u32()
                _vertical_bearing_x = rr.read_u32()
                _vertical_bearing_y = rr.read_u32()
                metrics = CblcMetricsBig(
                    width=_width,
                    height=_height,
                    bit_depth=_bit_depth,
                    horizontal_origin_x=_horizontal_origin_x,
                    horizontal_origin_y=_horizontal_origin_y,
                    vertical_origin_x=_vertical_origin_x,
                    vertical_origin_y=_vertical_origin_y,
                    horizontal_advance=_horizontal_advance,
                    vertical_advance=_vertical_advance,
                    horizontal_bearing_x=_horizontal_bearing_x,
                    horizontal_bearing_y=_horizontal_bearing_y,
                    vertical_bearing_x=_vertical_bearing_x,
                    vertical_bearing_y=_vertical_bearing_y
                )
                offsets = [rr.read_u32() for _ in range(num_glyphs)]

                for i in range(num_glyphs):
                    glyph_id = first_glyph_id + i
                    offset = offsets[i]
                    data_start = additional_offset + offset
                    if data_start + 4 > len(raw):
                        continue
                    data_format_byte = raw[data_start]
                    data_rr = BinaryReader(raw[data_start:])
                    data_rr.seek(4)
                    if data_format_byte == 1:
                        glyph_length = data_rr.read_u32()
                        bitmap_data = data_rr.read_bytes(glyph_length)
                    elif data_format_byte == 2:
                        glyph_length = data_rr.read_u32()
                        bitmap_data = data_rr.read_bytes(glyph_length)
                    elif data_format_byte == 3:
                        glyph_length = data_rr.read_u32()
                        bitmap_data = data_rr.read_bytes(glyph_length)
                    elif data_format_byte == 4:
                        glyph_length = data_rr.read_u32()
                        bitmap_data = data_rr.read_bytes(glyph_length)
                    else:
                        bitmap_data = b""
                    bitmaps.append(CbdtGlyphBitmap(
                        glyph_id=glyph_id,
                        data_format=data_format_byte,
                        bitmap_data=bitmap_data,
                        width=metrics.width,
                        height=metrics.height,
                        bearing_x=metrics.horizontal_origin_x,
                        bearing_y=metrics.horizontal_origin_y,
                        advance=metrics.horizontal_advance
                    ))

        return cls(
            version=version,
            strikes=strikes,
            bitmaps=bitmaps
        )

    def to_bytes(self) -> bytes:
        """Serialize CBDT table to binary."""
        raise NotImplementedError("CbdtTable serialization not yet implemented")
