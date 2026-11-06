"""Tests for FONT-394: gvar delta pruning during variable font subsetting."""

from __future__ import annotations

from pathlib import Path

import pytest

from aspose_font import FontLoader, TtfFont
from aspose_font.subsetter import FontSubsetter
from aspose_font.ttf.instancer import TtfInstancer


@pytest.fixture
def roboto_variable(testdata_dir: Path) -> TtfFont:
    return FontLoader.open(str(testdata_dir / "Roboto-VariableFont_wdth,wght.ttf"))


def _get_point_count(font: TtfFont, gid: int) -> int:
    loca = font.ttf_tables.loca
    offset = loca.glyph_offset(gid)
    length = loca.glyph_length(gid)
    if length <= 0:
        return 0
    raw = font.ttf_tables.glyf.get_glyph_bytes(offset, length)
    if len(raw) < 10:
        return 0
    contour_count = int.from_bytes(raw[:2], "big", signed=True)
    if contour_count > 0:
        try:
            simple = TtfInstancer._parse_simple_glyph(raw)
            return len(simple.xs)
        except Exception:
            return 0
    return 0


def test_subset_prunes_gvar_for_removed_glyphs(roboto_variable: TtfFont):
    """Verify that gvar tuple variations are removed for glyphs not in subset."""
    if "gvar" not in roboto_variable.ttf_tables._raw:
        pytest.skip("Roboto should have gvar table for this test")

    original_gvar_size = len(roboto_variable.ttf_tables._raw.get("gvar", b""))
    original_gid_count = roboto_variable.num_glyphs

    subsetted = FontSubsetter.subset_for_web(
        roboto_variable,
        text="He",
        preserve_variation_tables=True,
    )

    subset_gvar_size = len(subsetted.ttf_tables._raw.get("gvar", b""))

    assert subsetted.num_glyphs < original_gid_count
    assert subset_gvar_size < original_gvar_size, (
        f"Subset gvar size {subset_gvar_size} should be smaller than original {original_gvar_size}"
    )


def test_subset_preserves_gvar_for_retained_glyphs(roboto_variable: TtfFont):
    """Verify that retained glyphs still have correct variation data."""
    if "gvar" not in roboto_variable.ttf_tables._raw:
        pytest.skip("Roboto should have gvar table for this test")

    h_gid = int(roboto_variable.encoding.unicode_to_gid(ord("H")))
    pt_orig = _get_point_count(roboto_variable, h_gid)
    original_variations = roboto_variable.ttf_tables.gvar.glyph_variations(h_gid, pt_orig)

    subsetted = FontSubsetter.subset_for_web(
        roboto_variable,
        text="H",
        preserve_variation_tables=True,
    )

    h_after_gid = int(subsetted.encoding.unicode_to_gid(ord("H")))
    pt_after = _get_point_count(subsetted, h_after_gid)
    after_variations = subsetted.ttf_tables.gvar.glyph_variations(h_after_gid, pt_after)

    assert len(after_variations) == len(original_variations)
    for orig_var, after_var in zip(original_variations, after_variations):
        assert orig_var.peak_coords == after_var.peak_coords
        assert len(orig_var.deltas) == len(after_var.deltas)
        assert orig_var.deltas == after_var.deltas


def test_subset_gvar_roundtrip_stable(roboto_variable: TtfFont):
    """Verify that subsetted font with pruned gvar can be reloaded without corruption."""
    subsetted = FontSubsetter.subset_for_web(
        roboto_variable,
        text="Hello World",
        preserve_variation_tables=True,
    )

    reloaded_bytes = subsetted.to_bytes()
    reloaded = FontLoader.open(reloaded_bytes)

    assert reloaded.num_glyphs == subsetted.num_glyphs
    assert "gvar" in reloaded.ttf_tables._raw

    for gid in range(reloaded.num_glyphs):
        pt_count = _get_point_count(reloaded, gid)
        _ = reloaded.ttf_tables.gvar.glyph_variations(gid, pt_count)

    instanced = reloaded.smart_instancer.instantiate({"wght": 700})
    assert instanced is not None
    assert instanced.num_glyphs == subsetted.num_glyphs


def test_subset_without_preserve_drops_gvar(roboto_variable: TtfFont):
    """Verify that preserve_variation_tables=False still drops gvar."""
    subsetted = FontSubsetter.subset_for_web(
        roboto_variable,
        text="H",
        preserve_variation_tables=False,
    )

    assert "gvar" not in subsetted.ttf_tables._raw
    assert subsetted.ttf_tables.fvar is None


def test_subset_gvar_offsets_contiguous(roboto_variable: TtfFont):
    """Verify that glyph_offsets are contiguous and correctly re-indexed."""
    if "gvar" not in roboto_variable.ttf_tables._raw:
        pytest.skip("Roboto should have gvar table for this test")

    subsetted = FontSubsetter.subset_for_web(
        roboto_variable,
        text="ABC",
        preserve_variation_tables=True,
    )

    gvar_data = subsetted.ttf_tables._raw.get("gvar")
    assert gvar_data is not None

    from aspose_font._io import BinaryReader
    from aspose_font.ttf.tables.gvar import GvarTable

    gvar_table = GvarTable.from_reader(
        BinaryReader(gvar_data),
        len(gvar_data),
        axis_tags=["wdth", "wght"],
    )

    offsets = gvar_table.glyph_offsets
    assert len(offsets) == subsetted.num_glyphs + 1

    for i in range(len(offsets) - 1):
        assert offsets[i] <= offsets[i + 1], "Offsets should be non-decreasing"
