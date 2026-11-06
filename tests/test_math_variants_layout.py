"""Tests for Math Glyph Variant Selection & Assembly (FONT-486)."""
from __future__ import annotations

import pytest

from aspose_font import CffFont, TtfFont
from aspose_font._types import GlyphId
from aspose_font.text import get_math_variants


def test_get_math_variants_importable() -> None:
    from aspose_font.text import get_math_variants

    assert callable(get_math_variants)


def test_get_math_variants_returns_list_of_tuples(roboto: TtfFont) -> None:
    result = get_math_variants(roboto, 5, 100.0)
    assert isinstance(result, list)
    for item in result:
        assert isinstance(item, tuple)
        assert len(item) == 2
        assert isinstance(item[0], GlyphId)
        assert isinstance(item[1], float)


def test_get_math_variants_fallback_without_math_table(opensans_cff: CffFont) -> None:
    gid = 5
    result = get_math_variants(opensans_cff, gid, 100.0)
    assert result == [(GlyphId(gid), 0.0)]


def test_get_math_variants_selects_sufficient_variant(roboto: TtfFont) -> None:
    if not hasattr(roboto, "ttf_tables") or not hasattr(roboto.ttf_tables, "math"):
        pytest.skip("Roboto has no MATH table")
    if roboto.ttf_tables.math is None:
        pytest.skip("Roboto MATH table is None")

    math_table = roboto.ttf_tables.math
    if not math_table.get_glyph_variants(5, "vertical"):
        pytest.skip("No variants available for glyph 5")

    result = get_math_variants(roboto, 5, 100.0)
    assert len(result) == 1
    variant_gid, advance = result[0]
    assert isinstance(variant_gid, GlyphId)
    assert isinstance(advance, float)
    assert advance >= 100.0


def test_get_math_variants_returns_assembly_for_delimiter(roboto: TtfFont) -> None:
    if not hasattr(roboto, "ttf_tables") or not hasattr(roboto.ttf_tables, "math"):
        pytest.skip("Roboto has no MATH table")
    if roboto.ttf_tables.math is None:
        pytest.skip("Roboto MATH table is None")

    math_table = roboto.ttf_tables.math
    assembly = math_table.get_glyph_assembly(5, "vertical")
    if assembly is None:
        pytest.skip("No assembly available for glyph 5")

    result = get_math_variants(roboto, 5, 1000.0)
    assert isinstance(result, list)
    assert len(result) > 1
    for item in result:
        assert isinstance(item, tuple)
        assert isinstance(item[0], GlyphId)
        assert isinstance(item[1], float)


def test_get_math_variants_direction_parameter(roboto: TtfFont) -> None:
    result_v = get_math_variants(roboto, 5, 100.0, direction="vertical")
    result_h = get_math_variants(roboto, 5, 100.0, direction="horizontal")
    assert isinstance(result_v, list)
    assert isinstance(result_h, list)


def test_get_math_variants_uses_first_sufficient_variant(roboto: TtfFont) -> None:
    if not hasattr(roboto, "ttf_tables") or not hasattr(roboto.ttf_tables, "math"):
        pytest.skip("Roboto has no MATH table")
    if roboto.ttf_tables.math is None:
        pytest.skip("Roboto MATH table is None")

    math_table = roboto.ttf_tables.math
    variants = math_table.get_glyph_variants(5, "vertical")
    if len(variants) < 2:
        pytest.skip("Not enough variants to test selection")

    small_target = variants[0].advance_measurement + 1
    result = get_math_variants(roboto, 5, float(small_target))
    assert len(result) == 1
    variant_gid, advance = result[0]
    assert variant_gid.value == variants[1].variant_glyph


def test_get_math_variants_empty_target_size(roboto: TtfFont) -> None:
    result = get_math_variants(roboto, 5, 0.0)
    assert isinstance(result, list)


def test_get_math_variants_large_target_size(roboto: TtfFont) -> None:
    result = get_math_variants(roboto, 5, 10000.0)
    assert isinstance(result, list)
