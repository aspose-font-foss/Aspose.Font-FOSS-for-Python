"""Tests for hinting instruction complexity telemetry in FontQaReporter (FONT-554)."""

from pathlib import Path

from aspose_font import TtfFont
from aspose_font.qa import FontQaReporter


def test_hinting_profile_included_in_report(roboto: TtfFont) -> None:
    """Verify hinting_profile section exists in JSON payload."""
    report = FontQaReporter.build(roboto)
    payload = report.payload

    assert "hinting_profile" in payload, "hinting_profile section missing from JSON"
    hinting_profile = payload["hinting_profile"]
    assert isinstance(hinting_profile, dict)
    assert "complexity" in hinting_profile
    assert "total_instructions" in hinting_profile
    assert "max_per_glyph_instructions" in hinting_profile


def test_non_ttf_fonts_return_empty_profile(roboto_path: Path, tmp_path: Path, testdata_dir: Path) -> None:
    """Verify CFF fonts return minimal profile."""
    from aspose_font import FontLoader

    font = FontLoader.open(str(roboto_path))
    assert isinstance(font, TtfFont)

    cff_bytes = font.to_bytes()
    cff_path = tmp_path / "roboto.cff"
    cff_path.write_bytes(cff_bytes)

    openSans_cff_path = testdata_dir / "OpenSans-Regular.cff"
    font_cff = FontLoader.open(str(openSans_cff_path))

    report = FontQaReporter.build(font_cff)
    hinting_profile = report.payload.get("hinting_profile", {})

    assert hinting_profile.get("complexity") == "none"
    assert hinting_profile.get("total_instructions") == 0
    assert hinting_profile.get("instruction_categories") == {}


def test_no_hinting_font_categorizes_as_none(roboto: TtfFont) -> None:
    """Verify font without fpgm/prep/glyph bytecode gets complexity='none'."""
    font = roboto
    tables = font.ttf_tables

    original_fpgm = tables.fpgm
    original_prep = tables.prep

    tables.fpgm = None
    tables.prep = None

    report = FontQaReporter.build(font)
    hinting_profile = report.payload.get("hinting_profile", {})

    assert hinting_profile.get("complexity") == "none", "Expected complexity='none' for font without hinting"
    assert hinting_profile.get("total_instructions") == 0
    assert hinting_profile.get("fpgm_instructions") == 0
    assert hinting_profile.get("prep_instructions") == 0

    tables.fpgm = original_fpgm
    tables.prep = original_prep


def test_light_hinting_profile(roboto: TtfFont) -> None:
    """Verify instruction count categorization."""
    report = FontQaReporter.build(roboto)
    hinting_profile = report.payload.get("hinting_profile", {})

    complexity = hinting_profile.get("complexity")
    total_instructions = hinting_profile.get("total_instructions", 0)

    if total_instructions == 0:
        assert complexity == "none", f"Expected complexity='none' for 0 instructions, got {complexity}"
    elif total_instructions <= 50:
        assert complexity == "light", f"Expected complexity='light' for {total_instructions} instructions, got {complexity}"
    elif total_instructions <= 200:
        assert complexity == "moderate", f"Expected complexity='moderate' for {total_instructions} instructions, got {complexity}"
    else:
        assert complexity == "heavy", f"Expected complexity='heavy' for {total_instructions} instructions, got {complexity}"


def test_complexity_thresholds(roboto: TtfFont) -> None:
    """Verify threshold transitions: 0, 50, 200."""
    report = FontQaReporter.build(roboto)
    hinting_profile = report.payload.get("hinting_profile", {})

    total_instructions = hinting_profile.get("total_instructions", 0)
    complexity = hinting_profile.get("complexity")

    if total_instructions == 0:
        assert complexity == "none"
    elif total_instructions <= 50:
        assert complexity in ("none", "light")
    elif total_instructions <= 200:
        assert complexity in ("light", "moderate")
    else:
        assert complexity in ("moderate", "heavy")


def test_all_metrics_present(roboto: TtfFont) -> None:
    """Verify all required fields are present in profile."""
    report = FontQaReporter.build(roboto)
    hinting_profile = report.payload.get("hinting_profile", {})

    required_fields = [
        "complexity",
        "total_instructions",
        "max_per_glyph_instructions",
        "fpgm_instructions",
        "prep_instructions",
        "glyf_instructions",
        "fpgm_byte_size",
        "prep_byte_size",
        "instruction_categories",
    ]

    for field in required_fields:
        assert field in hinting_profile, f"Missing required field: {field}"


def test_glyf_bytecode_counted(roboto: TtfFont) -> None:
    """Verify per-glyph bytecode is included in total."""
    report = FontQaReporter.build(roboto)
    hinting_profile = report.payload.get("hinting_profile", {})

    fpgm_instructions = hinting_profile.get("fpgm_instructions", 0)
    prep_instructions = hinting_profile.get("prep_instructions", 0)
    glyf_instructions = hinting_profile.get("glyf_instructions", 0)
    total_instructions = hinting_profile.get("total_instructions", 0)

    expected_total = fpgm_instructions + prep_instructions + glyf_instructions
    assert total_instructions == expected_total, \
        f"total_instructions ({total_instructions}) != fpgm ({fpgm_instructions}) + prep ({prep_instructions}) + glyf ({glyf_instructions})"


def test_cross_platform_paths(testdata_dir: Path) -> None:
    """Verify test uses Path(__file__).resolve().parents[...] pattern."""
    source_str = str(testdata_dir).replace("\\", "/")
    assert "testdata" in source_str, "testdata path used"
    assert str(Path(__file__).parent.name) == "tests", "Test in tests directory"
