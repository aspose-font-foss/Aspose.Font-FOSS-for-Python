"""Tests for OpenType MATH table parser (FONT-485)."""

from __future__ import annotations

from io import BytesIO

from aspose_font._exceptions import FontParseException
from aspose_font._io import BinaryReader
from aspose_font.ttf.tables.math import (
    GlyphAssembly,
    GlyphPart,
    MathConstants,
    MathGlyphInfo,
    MathTable,
)


class TestMathConstantsDataclass:
    """Tests for MathConstants dataclass structure."""

    def test_constants_dataclass_structure(self):
        """Test that MathConstants has correct fields and values."""
        constants = MathConstants(
            script_fraction_scale_down=50,
            script_script_fraction_scale_down=35,
            delimited_sub_formula_min_height=200,
            accent_base_height=400,
            x_height=500,
            axis_height=250,
            default_rule_thickness=40,
            big_operator_spacing1=120,
            big_operator_spacing2=60,
            big_operator_spacing3=60,
            big_operator_spacing4=120,
            big_operator_spacing5=20,
            overscore_ascent=80,
            underscore_descent=60,
            top_accent_attachment=70,
            bottom_accent_attachment=50,
            gap_multiplier=20,
            frac_num_shift_up=300,
            frac_num_denom_shift_up=100,
            frac_denom_shift_down=200,
            frac_num_denom_gap_width=10,
            radical_degree_bottom_raise=50
        )
        assert constants.script_fraction_scale_down == 50
        assert constants.script_script_fraction_scale_down == 35
        assert constants.delimited_sub_formula_min_height == 200
        assert constants.accent_base_height == 400
        assert constants.x_height == 500
        assert constants.axis_height == 250
        assert constants.default_rule_thickness == 40
        assert constants.big_operator_spacing1 == 120
        assert constants.big_operator_spacing2 == 60
        assert constants.big_operator_spacing3 == 60
        assert constants.big_operator_spacing4 == 120
        assert constants.big_operator_spacing5 == 20
        assert constants.overscore_ascent == 80
        assert constants.underscore_descent == 60
        assert constants.top_accent_attachment == 70
        assert constants.bottom_accent_attachment == 50
        assert constants.gap_multiplier == 20
        assert constants.frac_num_shift_up == 300
        assert constants.frac_num_denom_shift_up == 100
        assert constants.frac_denom_shift_down == 200
        assert constants.frac_num_denom_gap_width == 10
        assert constants.radical_degree_bottom_raise == 50

    def test_constants_slots(self):
        """Test that MathConstants uses __slots__ for memory efficiency."""
        constants = MathConstants(
            script_fraction_scale_down=50,
            script_script_fraction_scale_down=35,
            delimited_sub_formula_min_height=200,
            accent_base_height=400,
            x_height=500,
            axis_height=250,
            default_rule_thickness=40,
            big_operator_spacing1=120,
            big_operator_spacing2=60,
            big_operator_spacing3=60,
            big_operator_spacing4=120,
            big_operator_spacing5=20,
            overscore_ascent=80,
            underscore_descent=60,
            top_accent_attachment=70,
            bottom_accent_attachment=50,
            gap_multiplier=20,
            frac_num_shift_up=300,
            frac_num_denom_shift_up=100,
            frac_denom_shift_down=200,
            frac_num_denom_gap_width=10,
            radical_degree_bottom_raise=50
        )
        assert not hasattr(constants, "__dict__")

    def test_constants_frozen(self):
        """Test that MathConstants is frozen."""
        constants = MathConstants(
            script_fraction_scale_down=50,
            script_script_fraction_scale_down=35,
            delimited_sub_formula_min_height=200,
            accent_base_height=400,
            x_height=500,
            axis_height=250,
            default_rule_thickness=40,
            big_operator_spacing1=120,
            big_operator_spacing2=60,
            big_operator_spacing3=60,
            big_operator_spacing4=120,
            big_operator_spacing5=20,
            overscore_ascent=80,
            underscore_descent=60,
            top_accent_attachment=70,
            bottom_accent_attachment=50,
            gap_multiplier=20,
            frac_num_shift_up=300,
            frac_num_denom_shift_up=100,
            frac_denom_shift_down=200,
            frac_num_denom_gap_width=10,
            radical_degree_bottom_raise=50
        )
        try:
            constants.script_fraction_scale_down = 100
            assert False, "Should have raised FrozenInstanceError"
        except Exception:
            pass


class TestGlyphPartDataclass:
    """Tests for GlyphPart dataclass structure."""

    def test_glyph_part_structure(self):
        """Test that GlyphPart has correct fields."""
        part = GlyphPart(
            glyph_id=5,
            start_connector_length=20,
            end_connector_length=30,
            full_advance_width=500,
            full_advance_height=800
        )
        assert part.glyph_id == 5
        assert part.start_connector_length == 20
        assert part.end_connector_length == 30
        assert part.full_advance_width == 500
        assert part.full_advance_height == 800

    def test_glyph_part_slots(self):
        """Test that GlyphPart uses __slots__."""
        part = GlyphPart(
            glyph_id=1,
            start_connector_length=10,
            end_connector_length=15,
            full_advance_width=400,
            full_advance_height=600
        )
        assert not hasattr(part, "__dict__")


class TestGlyphAssemblyDataclass:
    """Tests for GlyphAssembly dataclass structure."""

    def test_glyph_assembly_structure(self):
        """Test that GlyphAssembly has correct fields."""
        parts = [
            GlyphPart(glyph_id=1, start_connector_length=10, end_connector_length=20, full_advance_width=100, full_advance_height=200),
            GlyphPart(glyph_id=2, start_connector_length=15, end_connector_length=25, full_advance_width=150, full_advance_height=250),
        ]
        assembly = GlyphAssembly(
            parts=parts,
            italics_correction=50
        )
        assert len(assembly.parts) == 2
        assert assembly.parts[0].glyph_id == 1
        assert assembly.parts[1].glyph_id == 2
        assert assembly.italics_correction == 50

    def test_glyph_assembly_slots(self):
        """Test that GlyphAssembly uses __slots__."""
        parts = [
            GlyphPart(glyph_id=1, start_connector_length=10, end_connector_length=20, full_advance_width=100, full_advance_height=200),
        ]
        assembly = GlyphAssembly(
            parts=parts,
            italics_correction=50
        )
        assert not hasattr(assembly, "__dict__")


class TestMathGlyphInfoDataclass:
    """Tests for MathGlyphInfo dataclass structure."""

    def test_glyph_info_structure(self):
        """Test that MathGlyphInfo has correct fields."""
        info = MathGlyphInfo(
            italics_correction_info_offset=128,
            top_accent_attachment_offset=256,
            extended_shape_coverage_offset=384,
            math_kerning_info_offset=512
        )
        assert info.italics_correction_info_offset == 128
        assert info.top_accent_attachment_offset == 256
        assert info.extended_shape_coverage_offset == 384
        assert info.math_kerning_info_offset == 512


class TestMathTableParsing:
    """Tests for MathTable parsing."""

    def test_parse_math_table_with_constants(self):
        """Test parsing MathTable with MathConstants."""
        stream = BytesIO()
        stream.write(b"\x00\x01\x00\x00")  # version = 1.0
        stream.write(b"\x00\x0C")  # math_constants_offset = 12
        stream.write(b"\x00\x18")  # math_glyph_info_offset = 24
        stream.write(b"\x00\x24")  # math_variants_offset = 36
        stream.write(b"\x00\x00")  # reserved = 0

        stream.write(b"\x00\x32")  # scriptFractionScaleDown = 50
        stream.write(b"\x00\x23")  # scriptScriptFractionScaleDown = 35
        stream.write(b"\x00\xC8")  # delimitedSubFormulaMinHeight = 200
        stream.write(b"\x01\x90")  # accentBaseHeight = 400
        stream.write(b"\x01\xF4")  # xHeight = 500
        stream.write(b"\x00\xFA")  # axisHeight = 250
        stream.write(b"\x00\x28")  # defaultRuleThickness = 40
        stream.write(b"\x00\x78")  # bigOperatorSpacing1 = 120
        stream.write(b"\x00\x3C")  # bigOperatorSpacing2 = 60
        stream.write(b"\x00\x3C")  # bigOperatorSpacing3 = 60
        stream.write(b"\x00\x78")  # bigOperatorSpacing4 = 120
        stream.write(b"\x00\x14")  # bigOperatorSpacing5 = 20
        stream.write(b"\x00\x50")  # overscoreAscent = 80
        stream.write(b"\x00\x3C")  # underscoreDescent = 60
        stream.write(b"\x00\x46")  # topAccentAttachment = 70
        stream.write(b"\x00\x32")  # bottomAccentAttachment = 50
        stream.write(b"\x00\x14")  # gapMultiplier = 20
        stream.write(b"\x01\x2C")  # fracNumShiftUp = 300
        stream.write(b"\x00\x64")  # fracNumDenomShiftUp = 100
        stream.write(b"\x00\xC8")  # fracDenomShiftDown = 200
        stream.write(b"\x00\x0A")  # fracNumDenomGapWidth = 10
        stream.write(b"\x00\x32")  # radicalDegreeBottomRaise = 50

        stream.write(b"\x00\x01\x00\x02\x00\x03\x00\x04")  # mathGlyphInfo placeholder

        stream.write(b"\x00\x05\x00\x06\x00\x07\x00\x08")  # mathVariants placeholder

        rr = BinaryReader(stream.getvalue())
        table = MathTable.from_reader(rr, len(stream.getvalue()))

        assert table.version == 0x00010000
        assert table.math_constants is not None
        assert table.math_constants.script_fraction_scale_down == 50
        assert table.math_constants.script_script_fraction_scale_down == 35
        assert table.math_constants.delimited_sub_formula_min_height == 200
        assert table.math_constants.accent_base_height == 400
        assert table.math_constants.x_height == 500
        assert table.math_constants.axis_height == 250
        assert table.math_constants.default_rule_thickness == 40
        assert table.math_constants.big_operator_spacing1 == 120
        assert table.math_constants.big_operator_spacing2 == 60
        assert table.math_constants.big_operator_spacing3 == 60
        assert table.math_constants.big_operator_spacing4 == 120
        assert table.math_constants.big_operator_spacing5 == 20
        assert table.math_constants.overscore_ascent == 80
        assert table.math_constants.underscore_descent == 60
        assert table.math_constants.top_accent_attachment == 70
        assert table.math_constants.bottom_accent_attachment == 50
        assert table.math_constants.gap_multiplier == 20
        assert table.math_constants.frac_num_shift_up == 300
        assert table.math_constants.frac_num_denom_shift_up == 100
        assert table.math_constants.frac_denom_shift_down == 200
        assert table.math_constants.frac_num_denom_gap_width == 10
        assert table.math_constants.radical_degree_bottom_raise == 50

        assert table.math_glyph_info_offset == 24
        assert table.math_variants_offset == 36

    def test_parse_math_table_without_constants(self):
        """Test parsing MathTable without MathConstants (offset = 0)."""
        stream = BytesIO()
        stream.write(b"\x00\x01\x00\x00")  # version = 1.0
        stream.write(b"\x00\x00")  # math_constants_offset = 0 (no constants)
        stream.write(b"\x00\x10")  # math_glyph_info_offset = 16
        stream.write(b"\x00\x20")  # math_variants_offset = 32
        stream.write(b"\x00\x00")  # reserved = 0

        rr = BinaryReader(stream.getvalue())
        table = MathTable.from_reader(rr, len(stream.getvalue()))

        assert table.version == 0x00010000
        assert table.math_constants is None
        assert table.math_glyph_info_offset == 16
        assert table.math_variants_offset == 32

    def test_parse_math_table_invalid_version(self):
        """Test parsing MathTable with invalid version raises exception."""
        stream = BytesIO()
        stream.write(b"\x00\x02\x00\x00")  # version = 2.0 (unsupported)

        rr = BinaryReader(stream.getvalue())
        try:
            MathTable.from_reader(rr, len(stream.getvalue()))
            assert False, "Should have raised FontParseException"
        except FontParseException as e:
            assert "Unsupported MATH table version" in str(e)
            assert "0x00020000" in str(e)

    def test_parse_math_table_minimal(self):
        """Test parsing minimal MathTable (only version, all offsets zero)."""
        stream = BytesIO()
        stream.write(b"\x00\x01\x00\x00")  # version = 1.0
        stream.write(b"\x00\x00")  # math_constants_offset = 0
        stream.write(b"\x00\x00")  # math_glyph_info_offset = 0
        stream.write(b"\x00\x00")  # math_variants_offset = 0
        stream.write(b"\x00\x00")  # reserved = 0

        rr = BinaryReader(stream.getvalue())
        table = MathTable.from_reader(rr, len(stream.getvalue()))

        assert table.version == 0x00010000
        assert table.math_constants is None
        assert table.math_glyph_info_offset == 0
        assert table.math_variants_offset == 0


class TestMathTableHelperMethods:
    """Tests for MathTable helper methods."""

    def test_get_constant_with_valid_name(self):
        """Test get_constant returns value for valid constant name."""
        stream = BytesIO()
        stream.write(b"\x00\x01\x00\x00")  # version = 1.0
        stream.write(b"\x00\x0C")  # math_constants_offset = 12
        stream.write(b"\x00\x00")  # math_glyph_info_offset = 0
        stream.write(b"\x00\x00")  # math_variants_offset = 0
        stream.write(b"\x00\x00")  # reserved = 0

        stream.write(b"\x00\x32")  # scriptFractionScaleDown = 50
        stream.write(b"\x00\x23")  # scriptScriptFractionScaleDown = 35
        stream.write(b"\x00\xC8")  # delimitedSubFormulaMinHeight = 200
        stream.write(b"\x01\x90")  # accentBaseHeight = 400
        stream.write(b"\x01\xF4")  # xHeight = 500
        stream.write(b"\x00\xFA")  # axisHeight = 250
        stream.write(b"\x00\x28")  # defaultRuleThickness = 40
        stream.write(b"\x00\x78")  # bigOperatorSpacing1 = 120
        stream.write(b"\x00\x3C")  # bigOperatorSpacing2 = 60
        stream.write(b"\x00\x3C")  # bigOperatorSpacing3 = 60
        stream.write(b"\x00\x78")  # bigOperatorSpacing4 = 120
        stream.write(b"\x00\x14")  # bigOperatorSpacing5 = 20
        stream.write(b"\x00\x50")  # overscoreAscent = 80
        stream.write(b"\x00\x3C")  # underscoreDescent = 60
        stream.write(b"\x00\x46")  # topAccentAttachment = 70
        stream.write(b"\x00\x32")  # bottomAccentAttachment = 50
        stream.write(b"\x00\x14")  # gapMultiplier = 20
        stream.write(b"\x01\x2C")  # fracNumShiftUp = 300
        stream.write(b"\x00\x64")  # fracNumDenomShiftUp = 100
        stream.write(b"\x00\xC8")  # fracDenomShiftDown = 200
        stream.write(b"\x00\x0A")  # fracNumDenomGapWidth = 10
        stream.write(b"\x00\x32")  # radicalDegreeBottomRaise = 50

        rr = BinaryReader(stream.getvalue())
        table = MathTable.from_reader(rr, len(stream.getvalue()))

        assert table.get_constant("script_fraction_scale_down") == 50
        assert table.get_constant("axis_height") == 250
        assert table.get_constant("accent_base_height") == 400

    def test_get_constant_with_invalid_name(self):
        """Test get_constant returns None for invalid constant name."""
        stream = BytesIO()
        stream.write(b"\x00\x01\x00\x00")  # version = 1.0
        stream.write(b"\x00\x0C")  # math_constants_offset = 12
        stream.write(b"\x00\x00")  # math_glyph_info_offset = 0
        stream.write(b"\x00\x00")  # math_variants_offset = 0
        stream.write(b"\x00\x00")  # reserved = 0

        stream.write(b"\x00\x32")  # scriptFractionScaleDown = 50
        stream.write(b"\x00\x23")  # scriptScriptFractionScaleDown = 35
        stream.write(b"\x00\xC8")  # delimitedSubFormulaMinHeight = 200
        stream.write(b"\x01\x90")  # accentBaseHeight = 400
        stream.write(b"\x01\xF4")  # xHeight = 500
        stream.write(b"\x00\xFA")  # axisHeight = 250
        stream.write(b"\x00\x28")  # defaultRuleThickness = 40
        stream.write(b"\x00\x78")  # bigOperatorSpacing1 = 120
        stream.write(b"\x00\x3C")  # bigOperatorSpacing2 = 60
        stream.write(b"\x00\x3C")  # bigOperatorSpacing3 = 60
        stream.write(b"\x00\x78")  # bigOperatorSpacing4 = 120
        stream.write(b"\x00\x14")  # bigOperatorSpacing5 = 20
        stream.write(b"\x00\x50")  # overscoreAscent = 80
        stream.write(b"\x00\x3C")  # underscoreDescent = 60
        stream.write(b"\x00\x46")  # topAccentAttachment = 70
        stream.write(b"\x00\x32")  # bottomAccentAttachment = 50
        stream.write(b"\x00\x14")  # gapMultiplier = 20
        stream.write(b"\x01\x2C")  # fracNumShiftUp = 300
        stream.write(b"\x00\x64")  # fracNumDenomShiftUp = 100
        stream.write(b"\x00\xC8")  # fracDenomShiftDown = 200
        stream.write(b"\x00\x0A")  # fracNumDenomGapWidth = 10
        stream.write(b"\x00\x32")  # radicalDegreeBottomRaise = 50

        rr = BinaryReader(stream.getvalue())
        table = MathTable.from_reader(rr, len(stream.getvalue()))

        assert table.get_constant("nonexistent_constant") is None

    def test_get_constant_without_constants(self):
        """Test get_constant returns None when math_constants is None."""
        stream = BytesIO()
        stream.write(b"\x00\x01\x00\x00")  # version = 1.0
        stream.write(b"\x00\x00")  # math_constants_offset = 0
        stream.write(b"\x00\x00")  # math_glyph_info_offset = 0
        stream.write(b"\x00\x00")  # math_variants_offset = 0
        stream.write(b"\x00\x00")  # reserved = 0

        rr = BinaryReader(stream.getvalue())
        table = MathTable.from_reader(rr, len(stream.getvalue()))

        assert table.get_constant("axis_height") is None

    def test_get_glyph_assembly_returns_none_for_no_glyph_info(self):
        """Test get_glyph_assembly returns None when math_glyph_info_offset is 0."""
        stream = BytesIO()
        stream.write(b"\x00\x01\x00\x00")  # version = 1.0
        stream.write(b"\x00\x00")  # math_constants_offset = 0
        stream.write(b"\x00\x00")  # math_glyph_info_offset = 0
        stream.write(b"\x00\x00")  # math_variants_offset = 0
        stream.write(b"\x00\x00")  # reserved = 0

        rr = BinaryReader(stream.getvalue())
        table = MathTable.from_reader(rr, len(stream.getvalue()))

        result = table.get_glyph_assembly(glyph_id=5)
        assert result is None

    def test_get_glyph_assembly_placeholder_implementation(self):
        """Test get_glyph_assembly is callable and returns None (Slice A placeholder)."""
        stream = BytesIO()
        stream.write(b"\x00\x01\x00\x00")  # version = 1.0
        stream.write(b"\x00\x0C")  # math_constants_offset = 12
        stream.write(b"\x00\x10")  # math_glyph_info_offset = 16
        stream.write(b"\x00\x20")  # math_variants_offset = 32
        stream.write(b"\x00\x00")  # reserved = 0

        stream.write(b"\x00\x32")  # scriptFractionScaleDown = 50
        stream.write(b"\x00\x23")  # scriptScriptFractionScaleDown = 35
        stream.write(b"\x00\xC8")  # delimitedSubFormulaMinHeight = 200
        stream.write(b"\x01\x90")  # accentBaseHeight = 400
        stream.write(b"\x01\xF4")  # xHeight = 500
        stream.write(b"\x00\xFA")  # axisHeight = 250
        stream.write(b"\x00\x28")  # defaultRuleThickness = 40
        stream.write(b"\x00\x78")  # bigOperatorSpacing1 = 120
        stream.write(b"\x00\x3C")  # bigOperatorSpacing2 = 60
        stream.write(b"\x00\x3C")  # bigOperatorSpacing3 = 60
        stream.write(b"\x00\x78")  # bigOperatorSpacing4 = 120
        stream.write(b"\x00\x14")  # bigOperatorSpacing5 = 20
        stream.write(b"\x00\x50")  # overscoreAscent = 80
        stream.write(b"\x00\x3C")  # underscoreDescent = 60
        stream.write(b"\x00\x46")  # topAccentAttachment = 70
        stream.write(b"\x00\x32")  # bottomAccentAttachment = 50
        stream.write(b"\x00\x14")  # gapMultiplier = 20
        stream.write(b"\x01\x2C")  # fracNumShiftUp = 300
        stream.write(b"\x00\x64")  # fracNumDenomShiftUp = 100
        stream.write(b"\x00\xC8")  # fracDenomShiftDown = 200
        stream.write(b"\x00\x0A")  # fracNumDenomGapWidth = 10
        stream.write(b"\x00\x32")  # radicalDegreeBottomRaise = 50

        rr = BinaryReader(stream.getvalue())
        table = MathTable.from_reader(rr, len(stream.getvalue()))

        result = table.get_glyph_assembly(glyph_id=5)
        assert result is None

    def test_get_glyph_assembly_with_different_glyph_ids(self):
        """Test get_glyph_assembly works with various glyph IDs."""
        stream = BytesIO()
        stream.write(b"\x00\x01\x00\x00")  # version = 1.0
        stream.write(b"\x00\x0C")  # math_constants_offset = 12
        stream.write(b"\x00\x10")  # math_glyph_info_offset = 16
        stream.write(b"\x00\x20")  # math_variants_offset = 32
        stream.write(b"\x00\x00")  # reserved = 0

        stream.write(b"\x00\x32")  # scriptFractionScaleDown = 50
        stream.write(b"\x00\x23")  # scriptScriptFractionScaleDown = 35
        stream.write(b"\x00\xC8")  # delimitedSubFormulaMinHeight = 200
        stream.write(b"\x01\x90")  # accentBaseHeight = 400
        stream.write(b"\x01\xF4")  # xHeight = 500
        stream.write(b"\x00\xFA")  # axisHeight = 250
        stream.write(b"\x00\x28")  # defaultRuleThickness = 40
        stream.write(b"\x00\x78")  # bigOperatorSpacing1 = 120
        stream.write(b"\x00\x3C")  # bigOperatorSpacing2 = 60
        stream.write(b"\x00\x3C")  # bigOperatorSpacing3 = 60
        stream.write(b"\x00\x78")  # bigOperatorSpacing4 = 120
        stream.write(b"\x00\x14")  # bigOperatorSpacing5 = 20
        stream.write(b"\x00\x50")  # overscoreAscent = 80
        stream.write(b"\x00\x3C")  # underscoreDescent = 60
        stream.write(b"\x00\x46")  # topAccentAttachment = 70
        stream.write(b"\x00\x32")  # bottomAccentAttachment = 50
        stream.write(b"\x00\x14")  # gapMultiplier = 20
        stream.write(b"\x01\x2C")  # fracNumShiftUp = 300
        stream.write(b"\x00\x64")  # fracNumDenomShiftUp = 100
        stream.write(b"\x00\xC8")  # fracDenomShiftDown = 200
        stream.write(b"\x00\x0A")  # fracNumDenomGapWidth = 10
        stream.write(b"\x00\x32")  # radicalDegreeBottomRaise = 50

        rr = BinaryReader(stream.getvalue())
        table = MathTable.from_reader(rr, len(stream.getvalue()))

        for glyph_id in [0, 1, 5, 10, 100]:
            result = table.get_glyph_assembly(glyph_id=glyph_id)
            assert result is None


class TestMathTableIntegration:
    """Integration tests for MathTable."""

    def test_import_math_table_from_package(self):
        """Test that MathTable can be imported from aspose_font.ttf.tables."""
        from aspose_font.ttf.tables import MathTable
        assert MathTable is not None

    def test_import_all_math_classes(self):
        """Test that all MathTable-related classes can be imported."""
        from aspose_font.ttf.tables import (
            GlyphAssembly,
            GlyphPart,
            MathConstants,
            MathGlyphInfo,
            MathTable,
        )
        assert MathConstants is not None
        assert GlyphPart is not None
        assert GlyphAssembly is not None
        assert MathGlyphInfo is not None
        assert MathTable is not None

    def test_math_table_in_ttf_table_set(self):
        """Test that MathTable can be stored in TtfTableSet."""
        from aspose_font.ttf.tables import TtfTableSet

        stream = BytesIO()
        stream.write(b"\x00\x01\x00\x00")  # version = 1.0
        stream.write(b"\x00\x0C")  # math_constants_offset = 12
        stream.write(b"\x00\x00")  # math_glyph_info_offset = 0
        stream.write(b"\x00\x00")  # math_variants_offset = 0
        stream.write(b"\x00\x00")  # reserved = 0

        stream.write(b"\x00\x32")  # scriptFractionScaleDown = 50
        stream.write(b"\x00\x23")  # scriptScriptFractionScaleDown = 35
        stream.write(b"\x00\xC8")  # delimitedSubFormulaMinHeight = 200
        stream.write(b"\x01\x90")  # accentBaseHeight = 400
        stream.write(b"\x01\xF4")  # xHeight = 500
        stream.write(b"\x00\xFA")  # axisHeight = 250
        stream.write(b"\x00\x28")  # defaultRuleThickness = 40
        stream.write(b"\x00\x78")  # bigOperatorSpacing1 = 120
        stream.write(b"\x00\x3C")  # bigOperatorSpacing2 = 60
        stream.write(b"\x00\x3C")  # bigOperatorSpacing3 = 60
        stream.write(b"\x00\x78")  # bigOperatorSpacing4 = 120
        stream.write(b"\x00\x14")  # bigOperatorSpacing5 = 20
        stream.write(b"\x00\x50")  # overscoreAscent = 80
        stream.write(b"\x00\x3C")  # underscoreDescent = 60
        stream.write(b"\x00\x46")  # topAccentAttachment = 70
        stream.write(b"\x00\x32")  # bottomAccentAttachment = 50
        stream.write(b"\x00\x14")  # gapMultiplier = 20
        stream.write(b"\x01\x2C")  # fracNumShiftUp = 300
        stream.write(b"\x00\x64")  # fracNumDenomShiftUp = 100
        stream.write(b"\x00\xC8")  # fracDenomShiftDown = 200
        stream.write(b"\x00\x0A")  # fracNumDenomGapWidth = 10
        stream.write(b"\x00\x32")  # radicalDegreeBottomRaise = 50

        rr = BinaryReader(stream.getvalue())
        math_table = MathTable.from_reader(rr, len(stream.getvalue()))

        table_set = TtfTableSet()
        table_set.math = math_table

        assert table_set.math is not None
        assert table_set.math.version == 0x00010000
        assert table_set.math.math_constants is not None
        assert table_set.math.math_constants.script_fraction_scale_down == 50


class TestMathGlyphInfoAndVariantsParsing:
    """Comprehensive tests for MathGlyphInfo and MathVariants parsing."""

    def test_parse_full_math_glyph_info_and_variants(self):
        """Test parsing complete MathTable with MathGlyphInfo and MathVariants."""
        stream = BytesIO()

        # Reserve 12 bytes for table header
        stream.write(b"\x00" * 12)

        # 1. MathConstants:
        math_constants_offset = stream.tell()
        stream.write(b"\x00\x32" * 22)  # 22 i16 constants

        # 2. MathGlyphInfo:
        math_glyph_info_offset = stream.tell()
        # reserve 8 bytes for 4 offsets
        stream.write(b"\x00" * 8)

        # ItalicsCorrectionInfo:
        italics_info_offset = stream.tell() - math_glyph_info_offset
        stream.write(b"\x00\x08")          # coverage offset = 8
        stream.write(b"\x00\x01")          # count = 1
        stream.write(b"\x00\x2A\x00\x00")  # value = 42, device = 0
        # Coverage format 1:
        stream.write(b"\x00\x01\x00\x01\x00\x05")  # fmt 1, count 1, glyph 5

        # TopAccentAttachment:
        top_accent_offset = stream.tell() - math_glyph_info_offset
        stream.write(b"\x00\x08")          # coverage offset = 8
        stream.write(b"\x00\x01")          # count = 1
        stream.write(b"\x00\x55\x00\x00")  # value = 85, device = 0
        # Coverage format 1:
        stream.write(b"\x00\x01\x00\x01\x00\x05")  # fmt 1, count 1, glyph 5

        # ExtendedShapeCoverage:
        extended_shape_offset = stream.tell() - math_glyph_info_offset
        stream.write(b"\x00\x01\x00\x02\x00\x05\x00\x09")  # fmt 1, count 2, glyphs 5, 9

        # Fill MathGlyphInfo header:
        end_glyph_info = stream.tell()
        stream.seek(math_glyph_info_offset)
        stream.write(italics_info_offset.to_bytes(2, "big"))
        stream.write(top_accent_offset.to_bytes(2, "big"))
        stream.write(extended_shape_offset.to_bytes(2, "big"))
        stream.write(b"\x00\x00")  # kerning info offset = 0
        stream.seek(end_glyph_info)

        # 3. MathVariants:
        math_variants_offset = stream.tell()
        # header: min_overlap(2), vert_cov(2), horiz_cov(2), vert_count(2), horiz_count(2), vert_offsets(2)
        stream.write(b"\x00" * 12)

        # Vert Coverage:
        vert_cov_offset = stream.tell() - math_variants_offset
        stream.write(b"\x00\x01\x00\x01\x00\x28")  # fmt 1, count 1, glyph 40

        # Construction:
        constr_offset = stream.tell() - math_variants_offset
        stream.write(b"\x00\x08")          # assembly offset = 8
        stream.write(b"\x00\x01")          # variantCount = 1
        stream.write(b"\x00\x29\x02\x58")  # glyph 41, advance 600

        # Assembly:
        stream.write(b"\x00\x14\x00\x00")  # italics correction = 20, device = 0
        stream.write(b"\x00\x02")          # partCount = 2
        # part 1: gid=48, start=10, end=15, adv=400, flags=0
        stream.write(b"\x00\x30\x00\x0A\x00\x0F\x01\x90\x00\x00")
        # part 2: gid=49, start=15, end=10, adv=500, flags=1
        stream.write(b"\x00\x31\x00\x0F\x00\x0A\x01\xF4\x00\x01")

        # Fill MathVariants header:
        end_variants = stream.tell()
        stream.seek(math_variants_offset)
        stream.write((16).to_bytes(2, "big"))
        stream.write(vert_cov_offset.to_bytes(2, "big"))
        stream.write(b"\x00\x00")          # horiz_cov = 0
        stream.write((1).to_bytes(2, "big"))  # vert_count = 1
        stream.write(b"\x00\x00")          # horiz_count = 0
        stream.write(constr_offset.to_bytes(2, "big"))
        stream.seek(end_variants)

        # Fill Table header:
        stream.seek(0)
        stream.write(b"\x00\x01\x00\x00")  # version 1.0
        stream.write(math_constants_offset.to_bytes(2, "big"))
        stream.write(math_glyph_info_offset.to_bytes(2, "big"))
        stream.write(math_variants_offset.to_bytes(2, "big"))
        stream.write(b"\x00\x00")          # reserved

        raw = stream.getvalue()
        rr = BinaryReader(raw)
        table = MathTable.from_reader(rr, len(raw))

        assert table.version == 0x00010000
        assert table.math_glyph_info is not None
        assert table.math_variants is not None

        # Verify MathGlyphInfo lookups
        assert table.get_italic_correction(5) == 42
        assert table.get_italic_correction(99) is None

        assert table.get_top_accent_attachment(5) == 85
        assert table.get_top_accent_attachment(99) is None

        assert table.is_extended_shape(5) is True
        assert table.is_extended_shape(9) is True
        assert table.is_extended_shape(10) is False

        # Verify MathVariants lookups
        variants = table.get_glyph_variants(40)
        assert len(variants) == 1
        assert variants[0].variant_glyph == 41
        assert variants[0].advance_measurement == 600

        # Verify GlyphAssembly retrieval
        assembly = table.get_glyph_assembly(40)
        assert assembly is not None
        assert assembly.italics_correction == 20
        assert len(assembly.parts) == 2

        part1 = assembly.parts[0]
        assert part1.glyph_id == 48
        assert part1.start_connector_length == 10
        assert part1.end_connector_length == 15
        assert part1.full_advance_height == 400
        assert part1.part_flags == 0

        part2 = assembly.parts[1]
        assert part2.glyph_id == 49
        assert part2.start_connector_length == 15
        assert part2.end_connector_length == 10
        assert part2.full_advance_height == 500
        assert part2.part_flags == 1

        # Non-stretchy glyph returns None
        assert table.get_glyph_assembly(99) is None

