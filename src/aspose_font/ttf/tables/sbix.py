"""OpenType sbix (Standard Bitmap Graphics) table parser for color emoji extraction."""

from __future__ import annotations

from dataclasses import dataclass

from aspose_font._exceptions import FontParseException
from aspose_font._io import BinaryReader


@dataclass(slots=True)
class Strike:
    """Represents one bitmap strike (resolution) in the sbix table."""
    ppem: int
    resolution: int


@dataclass(slots=True)
class BitmapRecord:
    """Represents a single bitmap glyph record in an sbix strike."""
    glyph_id: int
    graphic_type: str
    origin_offset_x: int
    origin_offset_y: int
    bitmap_data: bytes


@dataclass
class SbixTable:
    """OpenType sbix table containing bitmap emoji images."""
    version: int
    flags: int
    strikes: list[Strike]
    bitmap_records: list[list[BitmapRecord | None]]

    @classmethod
    def from_reader(cls, r: BinaryReader, table_length: int) -> "SbixTable":
        """Parse sbix table from binary reader."""
        raw = r.read_bytes(table_length)
        rr = BinaryReader(raw)

        version = rr.read_u16()
        flags = rr.read_u16()
        num_strikes = rr.read_u32()

        if version != 0:
            raise FontParseException(
                f"Unsupported sbix table version {version}",
                format_name="TTF"
            )

        strikes: list[Strike] = []
        strike_offsets: list[int] = []

        for _ in range(num_strikes):
            ppem = rr.read_u16()
            resolution = rr.read_u16()
            offset_to_bitmap_data = rr.read_u32()
            strikes.append(Strike(ppem=ppem, resolution=resolution))
            strike_offsets.append(offset_to_bitmap_data)

        bitmap_records: list[list[BitmapRecord | None]] = []

        strikes_metadata_end = 8 + (num_strikes * 8)
        for i, (strike, offset_to_bitmap_data) in enumerate(zip(strikes, strike_offsets)):
            strike_data_start = strikes_metadata_end + offset_to_bitmap_data
            rr.seek(strike_data_start)

            num_glyphs = rr.read_u32()
            records: list[BitmapRecord | None] = []

            for j in range(num_glyphs):
                glyph_id = rr.read_u16()
                graphic_type = rr.read_tag()
                origin_offset_x = rr.read_i16()
                origin_offset_y = rr.read_i16()
                bitmap_data_length = rr.read_u32()
                bitmap_data = rr.read_bytes(bitmap_data_length)

                records.append(BitmapRecord(
                    glyph_id=glyph_id,
                    graphic_type=graphic_type,
                    origin_offset_x=origin_offset_x,
                    origin_offset_y=origin_offset_y,
                    bitmap_data=bitmap_data
                ))

            bitmap_records.append(records)

        return cls(
            version=version,
            flags=flags,
            strikes=strikes,
            bitmap_records=bitmap_records
        )

    def get_strikes(self) -> list[int]:
        """Return list of ppem values for available strikes, sorted ascending."""
        return sorted(strike.ppem for strike in self.strikes)

    def get_bitmap(self, glyph_id: int, ppem: int | None = None) -> bytes | None:
        """Get bitmap data for a glyph. If ppem is None, use highest available strike."""
        if ppem is None:
            if not self.strikes:
                return None
            ppem = max(strike.ppem for strike in self.strikes)

        strike_index = next(
            (i for i, s in enumerate(self.strikes) if s.ppem == ppem),
            None
        )
        if strike_index is None:
            return None

        records = self.bitmap_records[strike_index]
        for record in records:
            if record is not None and record.glyph_id == glyph_id:
                return record.bitmap_data
        return None

    def to_bytes(self) -> bytes:
        """Serialize sbix table to binary."""
        raise NotImplementedError("SbixTable serialization not yet implemented")
