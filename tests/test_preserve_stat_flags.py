"""Tests for preserving source STAT AxisValue flags in static instance generation."""

from pathlib import Path

import pytest

from aspose_font import FontLoader, TtfFont
from aspose_font.ttf.instancer import TtfInstancer
from aspose_font.ttf.tables.stat import (
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


class TestPreserveSourceStatFlags:
    """Test STAT AxisValue flag preservation in static instance generation."""

    def test_default_behavior_no_preserve(self, roboto: TtfFont) -> None:
        """Test default behavior (preserve_source_stat_flags=False) uses generated flags."""
        instantiated = TtfInstancer.instantiate(
            roboto,
            {"wght": 700.0, "wdth": 75.0},
            stat_policy="static",
            preserve_source_stat_flags=False,
        )

        assert "STAT" in instantiated.ttf_tables._raw
        generated_flags = extract_stat_axis_value_flags(instantiated.ttf_tables._raw["STAT"])
        assert len(generated_flags) == 1
        assert generated_flags[0] == 0

    def test_preserve_mode_uses_source_flags(self, roboto: TtfFont) -> None:
        """Test preserve_source_stat_flags=True uses source AxisValue flags."""
        source_flags = extract_stat_axis_value_flags(roboto.ttf_tables._raw.get("STAT", b""))
        assert len(source_flags) > 0, "Source font must have STAT AxisValue flags"

        instantiated = TtfInstancer.instantiate(
            roboto,
            {"wght": 700.0, "wdth": 75.0},
            stat_policy="static",
            preserve_source_stat_flags=True,
        )

        assert "STAT" in instantiated.ttf_tables._raw
        generated_flags = extract_stat_axis_value_flags(instantiated.ttf_tables._raw["STAT"])
        assert len(generated_flags) == 1
        assert generated_flags[0] == source_flags[-1]

    def test_no_stat_table_uses_generated_flags(self, roboto: TtfFont) -> None:
        """Test that fonts without STAT use generated flags when preserve flag is enabled."""
        from aspose_font.ttf.tables.stat import extract_stat_axis_value_flags

        original_stat = roboto.ttf_tables._raw.pop("STAT", None)
        try:
            instantiated = TtfInstancer.instantiate(
                roboto,
                {"wght": 700.0, "wdth": 75.0},
                stat_policy="static",
                preserve_source_stat_flags=True,
            )

            assert "STAT" in instantiated.ttf_tables._raw
            generated_flags = extract_stat_axis_value_flags(instantiated.ttf_tables._raw["STAT"])
            assert len(generated_flags) == 1
            assert generated_flags[0] == 0
        finally:
            if original_stat is not None:
                roboto.ttf_tables._raw["STAT"] = original_stat

    def test_multiple_axis_values_uses_last_flag(self, roboto: TtfFont) -> None:
        """Test that when source has multiple AxisValues, the last one's flags are used."""
        source_flags = extract_stat_axis_value_flags(roboto.ttf_tables._raw.get("STAT", b""))
        assert len(source_flags) > 0, "Source font must have STAT AxisValue flags"

        instantiated = TtfInstancer.instantiate(
            roboto,
            {"wght": 700.0, "wdth": 75.0},
            stat_policy="static",
            preserve_source_stat_flags=True,
        )

        assert "STAT" in instantiated.ttf_tables._raw
        generated_flags = extract_stat_axis_value_flags(instantiated.ttf_tables._raw["STAT"])
        assert len(generated_flags) == 1
        assert generated_flags[0] == source_flags[-1]

    def test_variable_instance_builder_preserve_flag(self, roboto: TtfFont) -> None:
        """Test VariableInstanceBuilder passes preserve_source_stat_flags flag correctly."""
        source_flags = extract_stat_axis_value_flags(roboto.ttf_tables._raw.get("STAT", b""))
        assert len(source_flags) > 0, "Source font must have STAT AxisValue flags"

        from aspose_font.instances import VariableInstanceBuilder
        builder = VariableInstanceBuilder(roboto)
        package = builder.build_package(
            include_default=False,
            stat_policy="static",
            preserve_source_stat_flags=True,
        )

        assert len(package.fonts) > 0
        font = package.fonts[0]
        assert "STAT" in font.ttf_tables._raw
        generated_flags = extract_stat_axis_value_flags(font.ttf_tables._raw["STAT"])
        assert len(generated_flags) == 1
        assert generated_flags[0] == source_flags[-1]

    def test_naming_policy_preview_preserve_flag(self, roboto: TtfFont) -> None:
        """Test preview_naming_policy passes preserve_source_stat_flags correctly."""
        from aspose_font.instances import VariableInstanceBuilder
        builder = VariableInstanceBuilder(roboto)

        source_flags = extract_stat_axis_value_flags(roboto.ttf_tables._raw.get("STAT", b""))
        assert len(source_flags) > 0, "Source font must have STAT AxisValue flags"

        preview = builder._font.preview_naming_policy(
            {"wght": 700.0, "wdth": 75.0},
            stat_policy="static",
            preserve_source_stat_flags=True,
        )

        assert preview.stat_diagnostics is not None
        assert preview.stat_diagnostics.generated_stat_axis_value_flags == source_flags[-1]
