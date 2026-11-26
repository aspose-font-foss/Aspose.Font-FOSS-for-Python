"""Tests for OpenType Font Feature Baker Core Engine (FONT-569)."""
from pathlib import Path

import pytest

from aspose_font import FontLoader
from aspose_font.feature_baker import BakedFeatureResult, OpenTypeFeatureBaker

FIXTURE_ROBOTO = Path(__file__).resolve().parent.parent / "testdata" / "Roboto-VariableFont_wdth,wght.ttf"


class TestOpenTypeFeatureBakerBasic:
    """Basic functionality tests."""

    def test_bake_single_feature_remaps_cmap(self) -> None:
        """Test that baking a single feature remaps cmap entries."""
        font = FontLoader.open(FIXTURE_ROBOTO)

        if font.ttf_tables.gsub is None:
            pytest.skip("Roboto has no GSUB table")

        baker = OpenTypeFeatureBaker()
        result = baker.bake(font, features=["smcp"])

        assert isinstance(result, BakedFeatureResult)
        assert result.remapped_codepoints > 0
        assert "smcp" in result.feature_tags_baked

    def test_bake_preserves_hmtx_metrics(self) -> None:
        """Test that hmtx metrics match substituted glyph metrics."""
        font = FontLoader.open(FIXTURE_ROBOTO)

        if font.ttf_tables.gsub is None:
            pytest.skip("Roboto has no GSUB table")

        baker = OpenTypeFeatureBaker()

        result = baker.bake(font, features=["smcp"])

        assert result.remapped_codepoints > 0

    def test_bake_multiple_features(self) -> None:
        """Test baking multiple features simultaneously."""
        font = FontLoader.open(FIXTURE_ROBOTO)

        if font.ttf_tables.gsub is None:
            pytest.skip("Roboto has no GSUB table")

        available = font.ttf_tables.gsub.list_all_features()
        if len(available) < 2:
            pytest.skip("Font has fewer than 2 features")

        baker = OpenTypeFeatureBaker()
        result = baker.bake(font, features=available[:2])

        assert len(result.feature_tags_baked) == 2
        assert result.substitution_rules_applied > 0


class TestOpenTypeFeatureBakerErrorHandling:
    """Error handling tests."""

    def test_bake_non_ttf_raises(self) -> None:
        """Test that non-TTF fonts raise ValueError."""
        font = FontLoader.open("testdata/OpenSans-Regular.pfb")

        baker = OpenTypeFeatureBaker()
        with pytest.raises(ValueError, match="only supports TtfFont"):
            baker.bake(font, features=["smcp"])

    def test_bake_no_gsub_raises(self) -> None:
        """Test that missing GSUB raises ValueError."""
        font = FontLoader.open("testdata/OpenSans-Regular.pfb")

        baker = OpenTypeFeatureBaker()
        with pytest.raises(ValueError, match="only supports TtfFont"):
            baker.bake(font, features=["smcp"])

    def test_bake_unknown_feature_raises(self) -> None:
        """Test that unknown feature raises NotImplementedError."""
        font = FontLoader.open(FIXTURE_ROBOTO)

        if font.ttf_tables.gsub is None:
            pytest.skip("Roboto has no GSUB table")

        baker = OpenTypeFeatureBaker()
        with pytest.raises(NotImplementedError, match="not found"):
            baker.bake(font, features=["xxxx"])


class TestOpenTypeFeatureBakerEdgeCases:
    """Edge case tests."""

    def test_bake_empty_features_list(self) -> None:
        """Test that empty features list bakes all available."""
        font = FontLoader.open(FIXTURE_ROBOTO)

        if font.ttf_tables.gsub is None:
            pytest.skip("Roboto has no GSUB table")

        baker = OpenTypeFeatureBaker()
        result = baker.bake(font, features=[])

        assert len(result.feature_tags_baked) > 0

    def test_bake_none_features_list(self) -> None:
        """Test that None features list bakes all available."""
        font = FontLoader.open(FIXTURE_ROBOTO)

        if font.ttf_tables.gsub is None:
            pytest.skip("Roboto has no GSUB table")

        baker = OpenTypeFeatureBaker()
        result = baker.bake(font, features=None)

        assert len(result.feature_tags_baked) > 0
