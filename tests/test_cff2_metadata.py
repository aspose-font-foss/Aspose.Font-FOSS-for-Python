from pathlib import Path

from aspose_font import FontLoader

_TESTDATA_ROOT = Path(__file__).resolve().parents[1] / "testdata"


def test_cff2_font_name():
    font = FontLoader.open(_TESTDATA_ROOT / "Roboto-VariableFont_wdth,wght.ttf")
    assert font.font_name is not None
    assert len(font.font_name) > 0
    assert font.font_name != ""


def test_cff2_font_family():
    font = FontLoader.open(_TESTDATA_ROOT / "Roboto-VariableFont_wdth,wght.ttf")
    assert font.font_family is not None
    assert len(font.font_family) > 0
    assert font.font_family != ""


def test_cff2_font_style():
    font = FontLoader.open(_TESTDATA_ROOT / "Roboto-VariableFont_wdth,wght.ttf")
    assert font.font_style is not None
    assert len(font.font_style) > 0
    assert font.font_style != ""


def test_cff2_num_glyphs():
    font = FontLoader.open(_TESTDATA_ROOT / "Roboto-VariableFont_wdth,wght.ttf")
    assert font.num_glyphs > 0


def test_cff2_metrics():
    font = FontLoader.open(_TESTDATA_ROOT / "Roboto-VariableFont_wdth,wght.ttf")
    metrics = font.metrics
    assert metrics is not None
    assert metrics.units_per_em > 0
    assert metrics.ascender >= 0
    assert metrics.descender <= 0


def test_cff2_encoding():
    font = FontLoader.open(_TESTDATA_ROOT / "Roboto-VariableFont_wdth,wght.ttf")
    encoding = font.encoding
    assert encoding is not None
    assert hasattr(encoding, "unicode_to_gid")
    assert hasattr(encoding, "get_all_codepoints")


def test_cff2_glyph_accessor():
    font = FontLoader.open(_TESTDATA_ROOT / "Roboto-VariableFont_wdth,wght.ttf")
    glyph_accessor = font.glyph_accessor
    assert glyph_accessor is not None
    glyph = glyph_accessor.get_glyph_by_id(0)
    assert glyph is not None
    assert glyph.glyph_id is not None
    assert glyph.glyph_name is not None
    assert glyph.path is not None or len(glyph.path) == 0
    assert hasattr(glyph_accessor, "get_all_glyph_ids")


def test_cff2_all_glyph_ids():
    font = FontLoader.open(_TESTDATA_ROOT / "Roboto-VariableFont_wdth,wght.ttf")
    glyph_ids = font.glyph_accessor.get_all_glyph_ids()
    assert len(glyph_ids) == font.num_glyphs
    assert all(gid.value >= 0 for gid in glyph_ids)
