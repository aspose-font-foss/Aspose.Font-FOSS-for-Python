"""Tests for FONT-395: HVAR table compaction during variable font subsetting."""

from __future__ import annotations

from pathlib import Path

import pytest

from aspose_font import FontLoader, TtfFont
from aspose_font._io import BinaryReader
from aspose_font.subsetter import FontSubsetter
from aspose_font.ttf.tables.hvar import HvarTable


@pytest.fixture
def roboto_variable(testdata_dir: Path) -> TtfFont:
    return FontLoader.open(str(testdata_dir / "Roboto-VariableFont_wdth,wght.ttf"))


def test_hvar_compaction_removes_mapping_for_dropped_glyphs(roboto_variable: TtfFont):
    """Verify that HVAR advance width mapping entries are reduced for subset glyphs."""
    if "HVAR" not in roboto_variable.ttf_tables._raw:
        pytest.skip("Roboto should have HVAR table for this test")

    original_hvar_size = len(roboto_variable.ttf_tables._raw.get("HVAR", b""))
    original_gid_count = roboto_variable.num_glyphs

    subsetted = FontSubsetter.subset_for_web(
        roboto_variable,
        text="He",
        preserve_variation_tables=True,
    )

    subset_hvar_size = len(subsetted.ttf_tables._raw.get("HVAR", b""))

    assert subsetted.num_glyphs < original_gid_count
    assert subset_hvar_size <= original_hvar_size


def test_hvar_compaction_preserves_variations_for_retained_glyphs(roboto_variable: TtfFont):
    """Verify that retained glyphs still have correct variation data after HVAR compaction."""
    if "HVAR" not in roboto_variable.ttf_tables._raw:
        pytest.skip("Roboto should have HVAR table for this test")

    fvar = roboto_variable.ttf_tables.fvar
    if fvar is None or len(fvar.axes) == 0:
        pytest.skip("Roboto should have fvar for this test")

    axis_tags = [ax.tag for ax in fvar.axes]

    h_gid = int(roboto_variable.encoding.unicode_to_gid(ord("H")))
    original_hvar = HvarTable.from_reader(
        BinaryReader(roboto_variable.ttf_tables._raw["HVAR"]),
        len(roboto_variable.ttf_tables._raw["HVAR"]),
        axis_tags=axis_tags,
    )

    original_delta = original_hvar.advance_width_delta(h_gid, {"wght": 0.5})

    subsetted = FontSubsetter.subset_for_web(
        roboto_variable,
        text="H",
        preserve_variation_tables=True,
    )

    subset_h_gid = int(subsetted.encoding.unicode_to_gid(ord("H")))
    subset_hvar = HvarTable.from_reader(
        BinaryReader(subsetted.ttf_tables._raw["HVAR"]),
        len(subsetted.ttf_tables._raw["HVAR"]),
        axis_tags=axis_tags,
    )

    subset_delta = subset_hvar.advance_width_delta(subset_h_gid, {"wght": 0.5})

    assert abs(original_delta - subset_delta) < 0.001


def test_hvar_compaction_reduces_table_size(roboto_variable: TtfFont):
    """Verify that HVAR table size is reduced after subsetting many glyphs."""
    if "HVAR" not in roboto_variable.ttf_tables._raw:
        pytest.skip("Roboto should have HVAR table for this test")

    original_hvar_size = len(roboto_variable.ttf_tables._raw.get("HVAR", b""))

    subsetted = FontSubsetter.subset_for_web(
        roboto_variable,
        text="H",
        preserve_variation_tables=True,
    )

    subset_hvar_size = len(subsetted.ttf_tables._raw.get("HVAR", b""))

    assert subset_hvar_size < original_hvar_size, (
        f"Subset HVAR size {subset_hvar_size} should be smaller than original {original_hvar_size}"
    )


def test_hvar_compaction_roundtrip_stable(roboto_variable: TtfFont):
    """Verify that subsetted font with compacted HVAR can be reloaded without corruption."""
    subsetted = FontSubsetter.subset_for_web(
        roboto_variable,
        text="Hello World",
        preserve_variation_tables=True,
    )

    reloaded_bytes = subsetted.to_bytes()
    reloaded = FontLoader.open(reloaded_bytes)

    assert reloaded.num_glyphs == subsetted.num_glyphs
    assert "HVAR" in reloaded.ttf_tables._raw

    fvar = reloaded.ttf_tables.fvar
    if fvar is not None:
        axis_tags = [ax.tag for ax in fvar.axes]
        hvar = HvarTable.from_reader(
            BinaryReader(reloaded.ttf_tables._raw["HVAR"]),
            len(reloaded.ttf_tables._raw["HVAR"]),
            axis_tags=axis_tags,
        )

        for gid in range(reloaded.num_glyphs):
            delta = hvar.advance_width_delta(gid, {"wght": 0.5})
            assert isinstance(delta, float)


def test_hvar_compaction_preserves_metric_values_at_coordinates(roboto_variable: TtfFont):
    """Verify that HVAR metric values are correct at various axis coordinates."""
    if "HVAR" not in roboto_variable.ttf_tables._raw:
        pytest.skip("Roboto should have HVAR table for this test")

    fvar = roboto_variable.ttf_tables.fvar
    if fvar is None or len(fvar.axes) == 0:
        pytest.skip("Roboto should have fvar for this test")

    axis_tags = [ax.tag for ax in fvar.axes]

    original_hvar = HvarTable.from_reader(
        BinaryReader(roboto_variable.ttf_tables._raw["HVAR"]),
        len(roboto_variable.ttf_tables._raw["HVAR"]),
        axis_tags=axis_tags,
    )

    subsetted = FontSubsetter.subset_for_web(
        roboto_variable,
        text="ABC",
        preserve_variation_tables=True,
    )

    subset_hvar = HvarTable.from_reader(
        BinaryReader(subsetted.ttf_tables._raw["HVAR"]),
        len(subsetted.ttf_tables._raw["HVAR"]),
        axis_tags=axis_tags,
    )

    test_coordinates = [
        {"wght": 0.0, "wdth": 0.0},
        {"wght": 1.0, "wdth": 0.0},
        {"wght": 0.0, "wdth": 1.0},
        {"wght": 0.5, "wdth": 0.5},
    ]

    for ch in "ABC":
        orig_gid = int(roboto_variable.encoding.unicode_to_gid(ord(ch)))
        subset_gid = int(subsetted.encoding.unicode_to_gid(ord(ch)))

        for coords in test_coordinates:
            orig_delta = original_hvar.advance_width_delta(orig_gid, coords)
            subset_delta = subset_hvar.advance_width_delta(subset_gid, coords)
            assert abs(orig_delta - subset_delta) < 0.001, (
                f"Character {ch} at coords {coords}: original GID {orig_gid} delta={orig_delta}, "
                f"subset GID {subset_gid} delta={subset_delta}"
            )
