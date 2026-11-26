"""Tests for FONT-313: subset-preserving variable-font web export."""

from __future__ import annotations

from pathlib import Path

import pytest

from aspose_font import FontLoader, TtfFont
from aspose_font.subsetter import FontSubsetter


@pytest.fixture
def roboto_variable(testdata_dir: Path) -> TtfFont:
    return FontLoader.open(str(testdata_dir / "Roboto-VariableFont_wdth,wght.ttf"))


def test_subset_for_web_preserves_fvar_axis_count(roboto_variable: TtfFont):
    original_axes = roboto_variable.ttf_tables.fvar.axes if roboto_variable.ttf_tables.fvar else []
    original_count = len(original_axes)

    subsetted = FontSubsetter.subset_for_web(
        roboto_variable,
        text="H",
        preserve_variation_tables=True,
    )

    assert subsetted.ttf_tables.fvar is not None
    assert len(subsetted.ttf_tables.fvar.axes) == original_count


def test_subset_for_web_preserves_gvar_entries(roboto_variable: TtfFont):
    tables = roboto_variable.ttf_tables
    has_gvar = "gvar" in tables._raw

    if not has_gvar:
        pytest.skip("Source font has no gvar table")

    original_gid_count = roboto_variable.num_glyphs
    subsetted = FontSubsetter.subset_for_web(
        roboto_variable,
        text="H",
        preserve_variation_tables=True,
    )

    assert "gvar" in subsetted.ttf_tables._raw
    assert subsetted.num_glyphs < original_gid_count


def test_subset_for_web_preserved_variable_roundtrip(roboto_variable: TtfFont):
    subsetted = FontSubsetter.subset_for_web(
        roboto_variable,
        text="Hello World",
        preserve_variation_tables=True,
    )

    reloaded_bytes = subsetted.to_bytes()
    reloaded = FontLoader.open(reloaded_bytes)

    assert reloaded.num_glyphs == subsetted.num_glyphs
    assert reloaded.ttf_tables.fvar is not None
    assert "gvar" in reloaded.ttf_tables._raw


def test_subset_for_web_without_preserve_drops_tables(roboto_variable: TtfFont):
    subsetted = FontSubsetter.subset_for_web(
        roboto_variable,
        text="H",
        preserve_variation_tables=False,
    )

    assert subsetted.ttf_tables.fvar is None
    assert "gvar" not in subsetted.ttf_tables._raw


def test_subset_for_web_flag_ignored_for_non_variable_ttf(testdata_dir: Path):

    roboto_variable = FontLoader.open(str(testdata_dir / "Roboto-VariableFont_wdth,wght.ttf"))
    assert roboto_variable.is_variable, "Roboto should be variable"

    subsetted = FontSubsetter.subset_for_web(
        roboto_variable,
        text="Hello World",
        preserve_variation_tables=False,
    )

    assert not subsetted.is_variable, "Without preserve, output should be static"

    subsetted_preserve = FontSubsetter.subset_for_web(
        roboto_variable,
        text="Hello World",
        preserve_variation_tables=True,
    )

    assert subsetted_preserve.is_variable, "With preserve, output should remain variable"
