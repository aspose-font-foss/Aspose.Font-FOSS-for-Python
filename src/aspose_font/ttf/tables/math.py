"""OpenType MATH table parser for mathematical typesetting."""

from __future__ import annotations

from dataclasses import dataclass, field

from aspose_font._exceptions import FontParseException
from aspose_font._io import BinaryReader


@dataclass(slots=True)
class CoverageTable:
    """OpenType Coverage Table (Format 1 or 2)."""
    format: int
    glyph_indices: list[int] = field(default_factory=list)
    range_records: list[tuple[int, int, int]] = field(default_factory=list)

    def get_index(self, glyph_id: int) -> int | None:
        """Return coverage index of the glyph, or None if not covered."""
        if self.format == 1:
            try:
                return self.glyph_indices.index(glyph_id)
            except ValueError:
                return None
        elif self.format == 2:
            for start, end, start_index in self.range_records:
                if start <= glyph_id <= end:
                    return start_index + (glyph_id - start)
            return None
        return None

    def contains(self, glyph_id: int) -> bool:
        """Check if glyph is covered."""
        return self.get_index(glyph_id) is not None


def _parse_coverage(r: BinaryReader, offset: int) -> CoverageTable:
    """Parse OpenType coverage table at given offset."""
    pos = r.tell()
    try:
        r.seek(offset)
        fmt = r.read_u16()
        if fmt == 1:
            count = r.read_u16()
            glyph_indices = [r.read_u16() for _ in range(count)]
            return CoverageTable(format=fmt, glyph_indices=glyph_indices)
        elif fmt == 2:
            count = r.read_u16()
            range_records = []
            for _ in range(count):
                start = r.read_u16()
                end = r.read_u16()
                start_index = r.read_u16()
                range_records.append((start, end, start_index))
            return CoverageTable(format=fmt, range_records=range_records)
        raise ValueError(f"Unknown coverage table format: {fmt}")
    finally:
        r.seek(pos)


@dataclass(slots=True, frozen=True)
class MathConstants:
    """MathConstants table for mathematical layout parameters."""
    script_fraction_scale_down: int
    script_script_fraction_scale_down: int
    delimited_sub_formula_min_height: int
    accent_base_height: int
    x_height: int
    axis_height: int
    default_rule_thickness: int
    big_operator_spacing1: int
    big_operator_spacing2: int
    big_operator_spacing3: int
    big_operator_spacing4: int
    big_operator_spacing5: int
    overscore_ascent: int
    underscore_descent: int
    top_accent_attachment: int
    bottom_accent_attachment: int
    gap_multiplier: int
    frac_num_shift_up: int
    frac_num_denom_shift_up: int
    frac_denom_shift_down: int
    frac_num_denom_gap_width: int
    radical_degree_bottom_raise: int


@dataclass(slots=True, frozen=True)
class GlyphPart:
    """Single part of a glyph assembly (used for stretchy symbols)."""
    glyph_id: int
    start_connector_length: int
    end_connector_length: int
    full_advance_width: int
    full_advance_height: int
    part_flags: int = 0


@dataclass(slots=True, frozen=True)
class GlyphAssembly:
    """Glyph assembly for stretchy glyphs (parentheses, brackets, etc.)."""
    parts: list[GlyphPart]
    italics_correction: int


@dataclass(slots=True, frozen=True)
class MathGlyphVariantRecord:
    """MathGlyphVariantRecord representing a sized variant of a math glyph."""
    variant_glyph: int
    advance_measurement: int


@dataclass(slots=True)
class MathGlyphConstruction:
    """MathGlyphConstruction subtable for glyph expansion."""
    glyph_assembly: GlyphAssembly | None
    variants: list[MathGlyphVariantRecord] = field(default_factory=list)


@dataclass(slots=True)
class MathGlyphInfo:
    """MathGlyphInfo table for glyph-level mathematical properties."""
    italics_correction_info_offset: int
    top_accent_attachment_offset: int
    extended_shape_coverage_offset: int
    math_kerning_info_offset: int
    italic_corrections: dict[int, int] = field(default_factory=dict)
    top_accent_attachments: dict[int, int] = field(default_factory=dict)
    extended_shapes: set[int] = field(default_factory=set)

    def get_italic_correction(self, glyph_id: int) -> int | None:
        """Get italics correction for a glyph ID, or None if not set."""
        return self.italic_corrections.get(glyph_id)

    def get_top_accent_attachment(self, glyph_id: int) -> int | None:
        """Get top accent attachment for a glyph ID, or None if not set."""
        return self.top_accent_attachments.get(glyph_id)

    def is_extended_shape(self, glyph_id: int) -> bool:
        """Check if glyph is an extended shape."""
        return glyph_id in self.extended_shapes


@dataclass(slots=True)
class MathVariants:
    """MathVariants table for vertical and horizontal glyph constructions."""
    min_connector_overlap: int
    vert_glyph_coverage_offset: int
    horiz_glyph_coverage_offset: int
    vert_constructions: dict[int, MathGlyphConstruction] = field(default_factory=dict)
    horiz_constructions: dict[int, MathGlyphConstruction] = field(default_factory=dict)

    def get_glyph_assembly(self, glyph_id: int, direction: str = "vertical") -> GlyphAssembly | None:
        """Get glyph assembly for a glyph ID."""
        constructions = self.vert_constructions if direction == "vertical" else self.horiz_constructions
        construction = constructions.get(glyph_id)
        return construction.glyph_assembly if construction else None

    def get_variants(self, glyph_id: int, direction: str = "vertical") -> list[MathGlyphVariantRecord]:
        """Get glyph variants for a glyph ID."""
        constructions = self.vert_constructions if direction == "vertical" else self.horiz_constructions
        construction = constructions.get(glyph_id)
        return construction.variants if construction else []


@dataclass(slots=True)
class MathTable:
    """OpenType MATH table parser for mathematical typesetting."""
    version: int
    math_constants: MathConstants | None
    math_glyph_info_offset: int
    math_variants_offset: int
    math_glyph_info: MathGlyphInfo | None = None
    math_variants: MathVariants | None = None

    @classmethod
    def from_reader(cls, r: BinaryReader, length: int) -> "MathTable":
        """Parse MATH table from binary reader."""
        raw = r.read_bytes(length)
        rr = BinaryReader(raw)

        version = rr.read_u32()
        if version != 0x00010000:
            raise FontParseException(
                f"Unsupported MATH table version: 0x{version:08X}",
                format_name="TTF",
            )

        math_constants_offset = rr.read_u16()
        math_glyph_info_offset = rr.read_u16()
        math_variants_offset = rr.read_u16()
        rr.read_u16()

        math_constants = None
        if math_constants_offset > 0 and math_constants_offset < length:
            try:
                rr.seek(math_constants_offset)
                math_constants = cls._parse_math_constants(rr)
            except Exception:
                pass

        math_glyph_info = None
        if math_glyph_info_offset > 0 and math_glyph_info_offset < length:
            try:
                rr.seek(math_glyph_info_offset)
                math_glyph_info = cls._parse_math_glyph_info(rr, math_glyph_info_offset, raw)
            except Exception:
                pass

        math_variants = None
        if math_variants_offset > 0 and math_variants_offset < length:
            try:
                rr.seek(math_variants_offset)
                math_variants = cls._parse_math_variants(rr, math_variants_offset, raw)
            except Exception:
                pass

        return cls(
            version=version,
            math_constants=math_constants,
            math_glyph_info_offset=math_glyph_info_offset,
            math_variants_offset=math_variants_offset,
            math_glyph_info=math_glyph_info,
            math_variants=math_variants,
        )

    @staticmethod
    def _parse_math_constants(rr: BinaryReader) -> MathConstants:
        """Parse MathConstants structure (22 INT16 values)."""
        return MathConstants(
            script_fraction_scale_down=rr.read_i16(),
            script_script_fraction_scale_down=rr.read_i16(),
            delimited_sub_formula_min_height=rr.read_i16(),
            accent_base_height=rr.read_i16(),
            x_height=rr.read_i16(),
            axis_height=rr.read_i16(),
            default_rule_thickness=rr.read_i16(),
            big_operator_spacing1=rr.read_i16(),
            big_operator_spacing2=rr.read_i16(),
            big_operator_spacing3=rr.read_i16(),
            big_operator_spacing4=rr.read_i16(),
            big_operator_spacing5=rr.read_i16(),
            overscore_ascent=rr.read_i16(),
            underscore_descent=rr.read_i16(),
            top_accent_attachment=rr.read_i16(),
            bottom_accent_attachment=rr.read_i16(),
            gap_multiplier=rr.read_i16(),
            frac_num_shift_up=rr.read_i16(),
            frac_num_denom_shift_up=rr.read_i16(),
            frac_denom_shift_down=rr.read_i16(),
            frac_num_denom_gap_width=rr.read_i16(),
            radical_degree_bottom_raise=rr.read_i16(),
        )

    @classmethod
    def _parse_math_glyph_info(cls, rr: BinaryReader, base_offset: int, raw: bytes) -> MathGlyphInfo:
        """Parse MathGlyphInfo table."""
        italics_correction_info_offset = rr.read_u16()
        top_accent_attachment_offset = rr.read_u16()
        extended_shape_coverage_offset = rr.read_u16()
        math_kerning_info_offset = rr.read_u16()

        info = MathGlyphInfo(
            italics_correction_info_offset=italics_correction_info_offset,
            top_accent_attachment_offset=top_accent_attachment_offset,
            extended_shape_coverage_offset=extended_shape_coverage_offset,
            math_kerning_info_offset=math_kerning_info_offset,
        )

        # Parse italics correction info if present
        if italics_correction_info_offset > 0:
            abs_offset = base_offset + italics_correction_info_offset
            if abs_offset < len(raw):
                try:
                    sub_r = BinaryReader(raw)
                    sub_r.seek(abs_offset)
                    cov_offset = sub_r.read_u16()
                    count = sub_r.read_u16()
                    corr_values = []
                    for _ in range(count):
                        val = sub_r.read_i16()
                        sub_r.read_u16()  # device offset
                        corr_values.append(val)
                    if cov_offset > 0:
                        cov = _parse_coverage(BinaryReader(raw), abs_offset + cov_offset)
                        for gid in cov.glyph_indices:
                            idx = cov.get_index(gid)
                            if idx is not None and idx < len(corr_values):
                                info.italic_corrections[gid] = corr_values[idx]
                except Exception:
                    pass

        # Parse top accent attachment info if present
        if top_accent_attachment_offset > 0:
            abs_offset = base_offset + top_accent_attachment_offset
            if abs_offset < len(raw):
                try:
                    sub_r = BinaryReader(raw)
                    sub_r.seek(abs_offset)
                    cov_offset = sub_r.read_u16()
                    count = sub_r.read_u16()
                    top_values = []
                    for _ in range(count):
                        val = sub_r.read_i16()
                        sub_r.read_u16()  # device offset
                        top_values.append(val)
                    if cov_offset > 0:
                        cov = _parse_coverage(BinaryReader(raw), abs_offset + cov_offset)
                        for gid in cov.glyph_indices:
                            idx = cov.get_index(gid)
                            if idx is not None and idx < len(top_values):
                                info.top_accent_attachments[gid] = top_values[idx]
                except Exception:
                    pass

        # Parse extended shape coverage if present
        if extended_shape_coverage_offset > 0:
            abs_offset = base_offset + extended_shape_coverage_offset
            if abs_offset < len(raw):
                try:
                    cov = _parse_coverage(BinaryReader(raw), abs_offset)
                    info.extended_shapes.update(cov.glyph_indices)
                except Exception:
                    pass

        return info

    @classmethod
    def _parse_math_variants(cls, rr: BinaryReader, base_offset: int, raw: bytes) -> MathVariants:
        """Parse MathVariants table."""
        min_connector_overlap = rr.read_u16()
        vert_glyph_coverage_offset = rr.read_u16()
        horiz_glyph_coverage_offset = rr.read_u16()
        vert_glyph_count = rr.read_u16()
        horiz_glyph_count = rr.read_u16()

        vert_construction_offsets = [rr.read_u16() for _ in range(vert_glyph_count)]
        horiz_construction_offsets = [rr.read_u16() for _ in range(horiz_glyph_count)]

        variants = MathVariants(
            min_connector_overlap=min_connector_overlap,
            vert_glyph_coverage_offset=vert_glyph_coverage_offset,
            horiz_glyph_coverage_offset=horiz_glyph_coverage_offset,
        )

        # Parse vertical glyph constructions
        if vert_glyph_coverage_offset > 0 and vert_construction_offsets:
            abs_cov_offset = base_offset + vert_glyph_coverage_offset
            if abs_cov_offset < len(raw):
                try:
                    cov = _parse_coverage(BinaryReader(raw), abs_cov_offset)
                    for i, constr_offset in enumerate(vert_construction_offsets):
                        if i < len(cov.glyph_indices) and constr_offset > 0:
                            gid = cov.glyph_indices[i]
                            construction = cls._parse_glyph_construction(
                                raw, base_offset + constr_offset, is_vertical=True
                            )
                            variants.vert_constructions[gid] = construction
                except Exception:
                    pass

        # Parse horizontal glyph constructions
        if horiz_glyph_coverage_offset > 0 and horiz_construction_offsets:
            abs_cov_offset = base_offset + horiz_glyph_coverage_offset
            if abs_cov_offset < len(raw):
                try:
                    cov = _parse_coverage(BinaryReader(raw), abs_cov_offset)
                    for i, constr_offset in enumerate(horiz_construction_offsets):
                        if i < len(cov.glyph_indices) and constr_offset > 0:
                            gid = cov.glyph_indices[i]
                            construction = cls._parse_glyph_construction(
                                raw, base_offset + constr_offset, is_vertical=False
                            )
                            variants.horiz_constructions[gid] = construction
                except Exception:
                    pass

        return variants

    @classmethod
    def _parse_glyph_construction(cls, raw: bytes, constr_offset: int, is_vertical: bool) -> MathGlyphConstruction:
        """Parse MathGlyphConstruction subtable."""
        r = BinaryReader(raw)
        r.seek(constr_offset)
        assembly_offset = r.read_u16()
        variant_count = r.read_u16()

        variants: list[MathGlyphVariantRecord] = []
        for _ in range(variant_count):
            vg = r.read_u16()
            adv = r.read_u16()
            variants.append(MathGlyphVariantRecord(variant_glyph=vg, advance_measurement=adv))

        assembly = None
        if assembly_offset > 0:
            abs_assembly_offset = constr_offset + assembly_offset
            if abs_assembly_offset < len(raw):
                r.seek(abs_assembly_offset)
                italic_corr = r.read_i16()
                r.read_u16()  # device offset
                part_count = r.read_u16()
                parts: list[GlyphPart] = []
                for _ in range(part_count):
                    gid = r.read_u16()
                    start_len = r.read_u16()
                    end_len = r.read_u16()
                    full_adv = r.read_u16()
                    part_flags = r.read_u16()
                    parts.append(GlyphPart(
                        glyph_id=gid,
                        start_connector_length=start_len,
                        end_connector_length=end_len,
                        full_advance_width=0 if is_vertical else full_adv,
                        full_advance_height=full_adv if is_vertical else 0,
                        part_flags=part_flags,
                    ))
                assembly = GlyphAssembly(parts=parts, italics_correction=italic_corr)

        return MathGlyphConstruction(glyph_assembly=assembly, variants=variants)

    def get_glyph_assembly(self, glyph_id: int, direction: str = "vertical") -> GlyphAssembly | None:
        """Return glyph assembly for a glyph ID, or None if not stretchy."""
        if self.math_variants is not None:
            assembly = self.math_variants.get_glyph_assembly(glyph_id, direction)
            if assembly is not None:
                return assembly
        return None

    def get_italic_correction(self, glyph_id: int) -> int | None:
        """Get italics correction for a glyph ID, or None if not set."""
        if self.math_glyph_info is not None:
            return self.math_glyph_info.get_italic_correction(glyph_id)
        return None

    def get_top_accent_attachment(self, glyph_id: int) -> int | None:
        """Get top accent attachment for a glyph ID, or None if not set."""
        if self.math_glyph_info is not None:
            return self.math_glyph_info.get_top_accent_attachment(glyph_id)
        return None

    def is_extended_shape(self, glyph_id: int) -> bool:
        """Check if glyph is an extended shape."""
        if self.math_glyph_info is not None:
            return self.math_glyph_info.is_extended_shape(glyph_id)
        return False

    def get_glyph_variants(self, glyph_id: int, direction: str = "vertical") -> list[MathGlyphVariantRecord]:
        """Get glyph variants for a glyph ID."""
        if self.math_variants is not None:
            return self.math_variants.get_variants(glyph_id, direction)
        return []

    def get_constant(self, name: str) -> int | None:
        """Get a MathConstants value by attribute name, or None if not present."""
        if self.math_constants is None:
            return None
        return getattr(self.math_constants, name, None)
