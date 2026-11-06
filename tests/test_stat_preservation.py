"""Tests for enhanced STAT preservation with elidable and linked AxisValue flags."""

from pathlib import Path

import pytest

from aspose_font import FontLoader, TtfFont
from aspose_font.ttf.instancer import TtfInstancer
from aspose_font.ttf.tables.stat import (
    build_static_stat_table,
    extract_stat_axis_value_flags,
)


@pytest.fixture
def roboto_path(testdata_dir: Path) -> Path:
    return testdata_dir / "Roboto-VariableFont_wdth,wght.ttf"


@pytest.fixture
def roboto(roboto_path: Path) -> TtfFont:
    font = FontLoader.open(str(roboto_path))
    assert isinstance(font, TtfFont)
    return font


class TestEnhancedStatPreservation:
    """Test enhanced STAT AxisValue flag preservation with elidable/linked flags."""

    def test_default_preserve_both_elidable_and_linked(self, roboto: TtfFont) -> None:
        """Test that default preserve (no CLI flag, or preserve=True) preserves all flags."""
        source_flags = extract_stat_axis_value_flags(roboto.ttf_tables._raw.get("STAT", b""))
        if len(source_flags) == 0:
            pytest.skip("Source font has no STAT flags")

        instantiated = TtfInstancer.instantiate(
            roboto,
            {"wght": 700.0, "wdth": 75.0},
            stat_policy="static",
            preserve_source_stat_flags=True,
        )

        generated_flags = extract_stat_axis_value_flags(instantiated.ttf_tables._raw["STAT"])
        assert len(generated_flags) == 1
        assert generated_flags[0] == source_flags[-1]

    def test_preserve_elidable_only(self, roboto: TtfFont) -> None:
        """Test that only elidable flag (0x0002) is preserved when 'elidable' is selected."""
        source_flags = extract_stat_axis_value_flags(roboto.ttf_tables._raw.get("STAT", b""))
        if len(source_flags) == 0:
            pytest.skip("Source font has no STAT flags")

        instantiated = TtfInstancer.instantiate(
            roboto,
            {"wght": 700.0, "wdth": 75.0},
            stat_policy="static",
            preserve_source_stat_flags="elidable",
        )

        generated_flags = extract_stat_axis_value_flags(instantiated.ttf_tables._raw["STAT"])
        assert len(generated_flags) == 1
        expected_flags = source_flags[-1] & 0x0002
        assert generated_flags[0] == expected_flags

    def test_preserve_linked_only(self, roboto: TtfFont) -> None:
        """Test that only linked flag (0x0001) is preserved when 'linked' is selected."""
        source_flags = extract_stat_axis_value_flags(roboto.ttf_tables._raw.get("STAT", b""))
        if len(source_flags) == 0:
            pytest.skip("Source font has no STAT flags")

        instantiated = TtfInstancer.instantiate(
            roboto,
            {"wght": 700.0, "wdth": 75.0},
            stat_policy="static",
            preserve_source_stat_flags="linked",
        )

        generated_flags = extract_stat_axis_value_flags(instantiated.ttf_tables._raw["STAT"])
        assert len(generated_flags) == 1
        expected_flags = source_flags[-1] & 0x0001
        assert generated_flags[0] == expected_flags

    def test_preserve_no_flags(self, roboto: TtfFont) -> None:
        """Test that no flags are preserved when preserve flag is not set."""
        source_flags = extract_stat_axis_value_flags(roboto.ttf_tables._raw.get("STAT", b""))
        if len(source_flags) == 0:
            pytest.skip("Source font has no STAT flags")

        instantiated = TtfInstancer.instantiate(
            roboto,
            {"wght": 700.0, "wdth": 75.0},
            stat_policy="static",
            preserve_source_stat_flags=False,
        )

        generated_flags = extract_stat_axis_value_flags(instantiated.ttf_tables._raw["STAT"])
        assert len(generated_flags) == 1
        assert generated_flags[0] == 0

    def test_cli_flag_format_elidable_comma_linked(self, roboto: TtfFont) -> None:
        """Test that 'elidable,linked' preserves both flags."""
        source_flags = extract_stat_axis_value_flags(roboto.ttf_tables._raw.get("STAT", b""))
        if len(source_flags) == 0:
            pytest.skip("Source font has no STAT flags")

        instantiated = TtfInstancer.instantiate(
            roboto,
            {"wght": 700.0, "wdth": 75.0},
            stat_policy="static",
            preserve_source_stat_flags="elidable,linked",
        )

        generated_flags = extract_stat_axis_value_flags(instantiated.ttf_tables._raw["STAT"])
        assert len(generated_flags) == 1
        expected_flags = source_flags[-1] & (0x0002 | 0x0001)
        assert generated_flags[0] == expected_flags

    def test_cli_flag_format_linked_comma_elidable(self, roboto: TtfFont) -> None:
        """Test that 'linked,elidable' preserves both flags (same as elidable,linked)."""
        source_flags = extract_stat_axis_value_flags(roboto.ttf_tables._raw.get("STAT", b""))
        if len(source_flags) == 0:
            pytest.skip("Source font has no STAT flags")

        instantiated = TtfInstancer.instantiate(
            roboto,
            {"wght": 700.0, "wdth": 75.0},
            stat_policy="static",
            preserve_source_stat_flags="linked,elidable",
        )

        generated_flags = extract_stat_axis_value_flags(instantiated.ttf_tables._raw["STAT"])
        assert len(generated_flags) == 1
        expected_flags = source_flags[-1] & (0x0002 | 0x0001)
        assert generated_flags[0] == expected_flags

    def test_preserve_elidable_flag_only_source_has_both(self, roboto: TtfFont) -> None:
        """Test elidable-only when source has both elidable and linked flags."""
        source_flags = extract_stat_axis_value_flags(roboto.ttf_tables._raw.get("STAT", b""))
        if len(source_flags) == 0:
            pytest.skip("Source font has no STAT flags")

        source_flag = source_flags[-1]
        has_both_flags = bool(source_flag & 0x0002) and bool(source_flag & 0x0001)
        if not has_both_flags:
            pytest.skip("Source font doesn't have both elidable and linked flags")

        instantiated = TtfInstancer.instantiate(
            roboto,
            {"wght": 700.0, "wdth": 75.0},
            stat_policy="static",
            preserve_source_stat_flags="elidable",
        )

        generated_flags = extract_stat_axis_value_flags(instantiated.ttf_tables._raw["STAT"])
        assert len(generated_flags) == 1
        assert generated_flags[0] == source_flag & 0x0002

    def test_preserve_linked_flag_only_source_has_both(self, roboto: TtfFont) -> None:
        """Test linked-only when source has both elidable and linked flags."""
        source_flags = extract_stat_axis_value_flags(roboto.ttf_tables._raw.get("STAT", b""))
        if len(source_flags) == 0:
            pytest.skip("Source font has no STAT flags")

        source_flag = source_flags[-1]
        has_both_flags = bool(source_flag & 0x0002) and bool(source_flag & 0x0001)
        if not has_both_flags:
            pytest.skip("Source font doesn't have both elidable and linked flags")

        instantiated = TtfInstancer.instantiate(
            roboto,
            {"wght": 700.0, "wdth": 75.0},
            stat_policy="static",
            preserve_source_stat_flags="linked",
        )

        generated_flags = extract_stat_axis_value_flags(instantiated.ttf_tables._raw["STAT"])
        assert len(generated_flags) == 1
        assert generated_flags[0] == source_flag & 0x0001

    def test_build_static_stat_table_with_mask(self) -> None:
        """Test build_static_stat_table with preserve_from_source and preserve_flags_mask."""
        from aspose_font.ttf.tables.fvar import AxisRecord

        axes = [
            AxisRecord(tag="wght", name_id=258, min_value=100, default_value=400, max_value=900, flags=0),
        ]
        coordinates = {"wght": 700.0}

        source_flags = (0x0003,)  # Both elidable (0x0002) and linked (0x0001)

        stat_data = build_static_stat_table(
            axes,
            coordinates,
            value_name_id=17,
            elided_fallback_name_id=2,
            preserve_from_source=source_flags,
            preserve_flags_mask=0x0002,
        )

        generated_flags = extract_stat_axis_value_flags(stat_data)
        assert len(generated_flags) == 1
        assert generated_flags[0] == 0x0002

    def test_build_static_stat_table_linked_only(self) -> None:
        """Test build_static_stat_table preserves only linked flag."""
        from aspose_font.ttf.tables.fvar import AxisRecord

        axes = [
            AxisRecord(tag="wght", name_id=258, min_value=100, default_value=400, max_value=900, flags=0),
        ]
        coordinates = {"wght": 700.0}

        source_flags = (0x0003,)  # Both elidable (0x0002) and linked (0x0001)

        stat_data = build_static_stat_table(
            axes,
            coordinates,
            value_name_id=17,
            elided_fallback_name_id=2,
            preserve_from_source=source_flags,
            preserve_flags_mask=0x0001,
        )

        generated_flags = extract_stat_axis_value_flags(stat_data)
        assert len(generated_flags) == 1
        assert generated_flags[0] == 0x0001
