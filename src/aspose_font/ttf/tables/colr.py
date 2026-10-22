"""COLR table parser for both COLR v0 and v1."""

from __future__ import annotations

from dataclasses import dataclass

from aspose_font._exceptions import FontParseException
from aspose_font._io import BinaryReader


@dataclass(slots=True)
class BaseGlyphRecord:
    glyph_id: int
    layer_offset: int


@dataclass(slots=True)
class LayerRecord:
    glyph_id: int
    color_index: int


@dataclass(slots=True)
class PaintSolid:
    palette_index: int
    alpha: float


@dataclass(slots=True)
class PaintLinearGradient:
    color_line_offset: int
    p0: tuple[float, float]
    p1: tuple[float, float]
    p2: tuple[float, float] | None = None
    paint: object | None = None


@dataclass(slots=True)
class PaintRadialGradient:
    color_line_offset: int
    circle_0_offset: tuple[float, float, float]
    circle_1_offset: tuple[float, float, float]
    paint: object | None = None


@dataclass(slots=True)
class PaintGlyph:
    glyph_id: int
    paint: object


@dataclass(slots=True)
class PaintColrLayers:
    start_layer_index: int
    num_layers: int


@dataclass(slots=True)
class PaintTransform:
    transform: tuple[float, float, float, float, float, float]
    paint: object


@dataclass(slots=True)
class PaintTranslate:
    dx: float
    dy: float
    paint: object


@dataclass(slots=True)
class PaintScale:
    scale_x: float
    scale_y: float
    paint: object
    center_x: float = 0.0
    center_y: float = 0.0


@dataclass(slots=True)
class PaintRotate:
    angle: float
    paint: object
    center_x: float = 0.0
    center_y: float = 0.0


@dataclass(slots=True)
class PaintSkew:
    x_skew_angle: float
    y_skew_angle: float
    paint: object
    center_x: float = 0.0
    center_y: float = 0.0


@dataclass(slots=True)
class BaseGlyphV1Record:
    glyph_id: int
    start_layer_index: int
    num_layers: int


@dataclass(slots=True)
class LayerV1Record:
    glyph_id: int
    paint_offset: int


@dataclass(slots=True)
class ColrTable:
    version: int
    base_glyph_records: list[BaseGlyphRecord]
    layer_records: list[LayerRecord]
    base_glyph_v1_records: list[BaseGlyphV1Record] | None = None
    layer_v1_records: list[LayerV1Record] | None = None
    paints: dict[int, object] | None = None

    @classmethod
    def from_reader(cls, r: BinaryReader, table_length: int) -> "ColrTable":
        """Parse COLR table from binary reader."""
        version = r.read_u16()
        num_base_glyph_records = r.read_u16()
        num_layer_records = r.read_u16()

        if version == 0:
            return cls._parse_colr_v0(r, table_length, version, num_base_glyph_records, num_layer_records)
        elif version == 1:
            return cls._parse_colr_v1(r, table_length, version, num_layer_records, num_base_glyph_records)
        else:
            raise FontParseException(f"Unsupported COLR version: {version}")

    @classmethod
    def _parse_colr_v0(
        cls,
        r: BinaryReader,
        table_length: int,
        version: int,
        num_base_glyph_records: int,
        num_layer_records: int,
    ) -> "ColrTable":
        base_glyph_records_offset = r.read_u32()
        layer_records_offset = r.read_u32()

        base_glyph_records: list[BaseGlyphRecord] = []
        layer_records: list[LayerRecord] = []

        if num_base_glyph_records > 0 and base_glyph_records_offset > 0 and base_glyph_records_offset <= table_length:
            original_pos = r.tell()
            r.seek(base_glyph_records_offset)
            for _ in range(num_base_glyph_records):
                glyph_id = r.read_u16()
                layer_offset = r.read_u16()
                base_glyph_records.append(BaseGlyphRecord(
                    glyph_id=glyph_id,
                    layer_offset=layer_offset
                ))
            r.seek(original_pos)

        if num_layer_records > 0 and layer_records_offset > 0 and layer_records_offset <= table_length:
            original_pos = r.tell()
            r.seek(layer_records_offset)
            for _ in range(num_layer_records):
                glyph_id = r.read_u16()
                color_index = r.read_u16()
                layer_records.append(LayerRecord(
                    glyph_id=glyph_id,
                    color_index=color_index
                ))
            r.seek(original_pos)

        return cls(
            version=version,
            base_glyph_records=base_glyph_records,
            layer_records=layer_records,
            base_glyph_v1_records=None,
            layer_v1_records=None,
            paints=None,
        )

    @classmethod
    def _parse_colr_v1(
        cls,
        r: BinaryReader,
        table_length: int,
        version: int,
        num_layer_records: int,
        num_base_glyph_records: int,
    ) -> "ColrTable":
        base_glyph_v1_offset = r.read_u32()
        layer_v1_offset = r.read_u32()

        base_glyph_v1_records: list[BaseGlyphV1Record] = []
        layer_v1_records: list[LayerV1Record] = []
        paints: dict[int, object] = {}

        if num_base_glyph_records > 0 and base_glyph_v1_offset > 0 and base_glyph_v1_offset <= table_length:
            original_pos = r.tell()
            r.seek(base_glyph_v1_offset)
            for _ in range(num_base_glyph_records):
                glyph_id = r.read_u16()
                start_layer_index = r.read_u16()
                num_layers_for_glyph = r.read_u16()
                base_glyph_v1_records.append(BaseGlyphV1Record(
                    glyph_id=glyph_id,
                    start_layer_index=start_layer_index,
                    num_layers=num_layers_for_glyph
                ))
            r.seek(original_pos)

        if num_layer_records > 0 and layer_v1_offset > 0 and layer_v1_offset <= table_length:
            original_pos = r.tell()
            r.seek(layer_v1_offset)
            for _ in range(num_layer_records):
                glyph_id = r.read_u16()
                paint_offset = r.read_u32()
                layer_v1_records.append(LayerV1Record(
                    glyph_id=glyph_id,
                    paint_offset=paint_offset
                ))
            r.seek(original_pos)

        if base_glyph_v1_offset > 0 and layer_v1_offset > 0:
            paints_start = layer_v1_offset + num_layer_records * 6
            original_pos = r.tell()
            r.seek(paints_start)
            paints = cls._parsePaintsTable(r, table_length, paints_start, layer_v1_records)
            r.seek(original_pos)
        else:
            paints = None

        return cls(
            version=version,
            base_glyph_records=[],
            layer_records=[],
            base_glyph_v1_records=base_glyph_v1_records,
            layer_v1_records=layer_v1_records,
            paints=paints if paints else None,
        )

    @classmethod
    def _parsePaintsTable(cls, r: BinaryReader, table_length: int, paints_start: int, layer_v1_records: list[LayerV1Record]) -> dict[int, object]:
        paints: dict[int, object] = {}

        # Deduplicate paint offsets to avoid parsing the same paint multiple times
        unique_paint_offsets: set[int] = set()
        for layer_record in layer_v1_records:
            paint_offset = paints_start + layer_record.paint_offset
            if paint_offset > 0 and paint_offset <= table_length:
                unique_paint_offsets.add(paint_offset)

        # Parse each unique paint offset once
        for paint_offset in sorted(unique_paint_offsets):
            r.seek(paint_offset)
            paint_type = r.read_u8()
            r.seek(paint_offset)
            paint = cls._parsePaintByType(r, paint_type, table_length, paints_start)
            if paint is not None:
                paints[paint_offset] = paint

        return paints

    @classmethod
    def _parsePaintByType(cls, r: BinaryReader, paint_type: int, table_length: int, paints_start: int) -> object | None:
        if paint_type == 0:
            return cls._parsePaintSolid(r)
        elif paint_type == 1:
            return cls._parsePaintLinearGradient(r, table_length, paints_start)
        elif paint_type == 2:
            return cls._parsePaintRadialGradient(r, table_length, paints_start)
        elif paint_type == 3:
            return cls._parsePaintGlyph(r, table_length, paints_start)
        elif paint_type == 4:
            return cls._parsePaintColrLayers(r)
        elif paint_type == 5:
            return cls._parsePaintTransform(r, table_length, paints_start)
        elif paint_type == 6:
            return cls._parsePaintTranslate(r, table_length, paints_start)
        elif paint_type == 7:
            return cls._parsePaintScale(r, table_length, paints_start)
        elif paint_type == 8:
            return cls._parsePaintRotate(r, table_length, paints_start)
        elif paint_type == 9:
            return cls._parsePaintSkew(r, table_length, paints_start)
        return None

    @classmethod
    def _parsePaintSolid(cls, r: BinaryReader) -> PaintSolid:
        r.read_u8()
        palette_index = r.read_u8()
        alpha = r.read_f2dot14()
        return PaintSolid(palette_index=palette_index, alpha=alpha)

    @classmethod
    def _parsePaintLinearGradient(cls, r: BinaryReader, table_length: int, paints_start: int) -> PaintLinearGradient | None:
        paint_type = r.read_u8()
        color_line_offset = r.read_u32()
        p0_x = r.read_fixed()
        p0_y = r.read_fixed()
        p1_x = r.read_fixed()
        p1_y = r.read_fixed()

        p2_offset = r.read_u32()
        p2 = None
        if p2_offset != 0:
            p2_x = r.read_fixed()
            p2_y = r.read_fixed()
            p2 = (p2_x, p2_y)

        paint_offset = r.read_u32()
        paint = None
        if paint_offset != 0:
            original_pos = r.tell()
            r.seek(paints_start + paint_offset)
            paint_type = r.read_u8()
            r.seek(original_pos)
            r.seek(paints_start + paint_offset)
            paint = cls._parsePaintByType(r, paint_type, table_length, paints_start)

        if p2 is None:
            return PaintLinearGradient(
                color_line_offset=color_line_offset,
                p0=(p0_x, p0_y),
                p1=(p1_x, p1_y),
                p2=None,
                paint=paint
            )
        return PaintLinearGradient(
            color_line_offset=color_line_offset,
            p0=(p0_x, p0_y),
            p1=(p1_x, p1_y),
            p2=p2,
            paint=paint
        )

    @classmethod
    def _parsePaintRadialGradient(cls, r: BinaryReader, table_length: int, paints_start: int) -> PaintRadialGradient | None:
        paint_type = r.read_u8()
        circle_0_x = r.read_fixed()
        circle_0_y = r.read_fixed()
        circle_0_radius = r.read_fixed()
        circle_1_x = r.read_fixed()
        circle_1_y = r.read_fixed()
        circle_1_radius = r.read_fixed()
        paint_offset = r.read_u32()

        paint = None
        if paint_offset != 0:
            original_pos = r.tell()
            r.seek(paints_start + paint_offset)
            paint_type = r.read_u8()
            r.seek(original_pos)
            r.seek(paints_start + paint_offset)
            paint = cls._parsePaintByType(r, paint_type, table_length, paints_start)

        return PaintRadialGradient(
            color_line_offset=0,
            circle_0_offset=(circle_0_x, circle_0_y, circle_0_radius),
            circle_1_offset=(circle_1_x, circle_1_y, circle_1_radius),
            paint=paint
        )

    @classmethod
    def _parsePaintGlyph(cls, r: BinaryReader, table_length: int, paints_start: int) -> PaintGlyph | None:
        paint_type = r.read_u8()
        glyph_id = r.read_u16()
        paint_offset = r.read_u32()

        paint = None
        if paint_offset != 0:
            original_pos = r.tell()
            r.seek(paints_start + paint_offset)
            paint_type = r.read_u8()
            r.seek(original_pos)
            r.seek(paints_start + paint_offset)
            paint = cls._parsePaintByType(r, paint_type, table_length, paints_start)

        return PaintGlyph(glyph_id=glyph_id, paint=paint)

    @classmethod
    def _parsePaintColrLayers(cls, r: BinaryReader) -> PaintColrLayers:
        r.read_u8()
        start_layer_index = r.read_u16()
        num_layers = r.read_u16()
        return PaintColrLayers(start_layer_index=start_layer_index, num_layers=num_layers)

    @classmethod
    def _parsePaintTransform(cls, r: BinaryReader, table_length: int, paints_start: int) -> PaintTransform | None:
        paint_type = r.read_u8()
        transform_scale_x = r.read_fixed()
        transform_skew_x = r.read_fixed()
        transform_skew_y = r.read_fixed()
        transform_scale_y = r.read_fixed()
        transformTranslateX = r.read_fixed()
        transformTranslateY = r.read_fixed()
        paint_offset = r.read_u32()

        paint = None
        if paint_offset != 0:
            original_pos = r.tell()
            r.seek(paints_start + paint_offset)
            paint_type = r.read_u8()
            r.seek(original_pos)
            r.seek(paints_start + paint_offset)
            paint = cls._parsePaintByType(r, paint_type, table_length, paints_start)

        return PaintTransform(
            transform=(transform_scale_x, transform_skew_x, transform_skew_y, transform_scale_y, transformTranslateX, transformTranslateY),
            paint=paint
        )

    @classmethod
    def _parsePaintTranslate(cls, r: BinaryReader, table_length: int, paints_start: int) -> PaintTranslate | None:
        paint_type = r.read_u8()
        dx = r.read_fixed()
        dy = r.read_fixed()
        paint_offset = r.read_u32()

        paint = None
        if paint_offset != 0:
            original_pos = r.tell()
            r.seek(paints_start + paint_offset)
            paint_type = r.read_u8()
            r.seek(original_pos)
            r.seek(paints_start + paint_offset)
            paint = cls._parsePaintByType(r, paint_type, table_length, paints_start)

        return PaintTranslate(dx=dx, dy=dy, paint=paint)

    @classmethod
    def _parsePaintScale(cls, r: BinaryReader, table_length: int, paints_start: int) -> PaintScale | None:
        paint_type = r.read_u8()
        scale_x = r.read_fixed()
        scale_y = r.read_fixed()
        paint_offset = r.read_u32()

        center_x = r.read_fixed()
        center_y = r.read_fixed()

        paint = None
        if paint_offset != 0:
            original_pos = r.tell()
            r.seek(paints_start + paint_offset)
            paint_type = r.read_u8()
            r.seek(original_pos)
            r.seek(paints_start + paint_offset)
            paint = cls._parsePaintByType(r, paint_type, table_length, paints_start)

        return PaintScale(scale_x=scale_x, scale_y=scale_y, paint=paint, center_x=center_x, center_y=center_y)

    @classmethod
    def _parsePaintRotate(cls, r: BinaryReader, table_length: int, paints_start: int) -> PaintRotate | None:
        paint_type = r.read_u8()
        angle = r.read_fixed()
        paint_offset = r.read_u32()

        center_x = r.read_fixed()
        center_y = r.read_fixed()

        paint = None
        if paint_offset != 0:
            original_pos = r.tell()
            r.seek(paints_start + paint_offset)
            paint_type = r.read_u8()
            r.seek(original_pos)
            r.seek(paints_start + paint_offset)
            paint = cls._parsePaintByType(r, paint_type, table_length, paints_start)

        return PaintRotate(angle=angle, paint=paint, center_x=center_x, center_y=center_y)

    @classmethod
    def _parsePaintSkew(cls, r: BinaryReader, table_length: int, paints_start: int) -> PaintSkew | None:
        paint_type = r.read_u8()
        x_skew_angle = r.read_fixed()
        y_skew_angle = r.read_fixed()
        paint_offset = r.read_u32()

        center_x = r.read_fixed()
        center_y = r.read_fixed()

        paint = None
        if paint_offset != 0:
            original_pos = r.tell()
            r.seek(paints_start + paint_offset)
            paint_type = r.read_u8()
            r.seek(original_pos)
            r.seek(paints_start + paint_offset)
            paint = cls._parsePaintByType(r, paint_type, table_length, paints_start)

        return PaintSkew(x_skew_angle=x_skew_angle, y_skew_angle=y_skew_angle, paint=paint, center_x=center_x, center_y=center_y)
