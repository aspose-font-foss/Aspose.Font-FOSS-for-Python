"""Pure-Python OpenType Font Feature Baker Core Engine (FONT-569)."""
from __future__ import annotations

from dataclasses import dataclass

from aspose_font._font_base import Font
from aspose_font.ttf.font import TtfFont

__all__ = ["OpenTypeFeatureBaker", "BakedFeatureResult"]


@dataclass(slots=True)
class BakedFeatureResult:
    """Result of baking features into a font."""
    remapped_codepoints: int
    feature_tags_baked: list[str]
    substitution_rules_applied: int


class OpenTypeFeatureBaker:
    """Core engine for baking OpenType GSUB features into static cmap mappings."""

    def __init__(self) -> None:
        pass

    def bake(
        self,
        font: Font,
        features: list[str] | None = None,
    ) -> BakedFeatureResult:
        """
        Bake specified GSUB features into the font's cmap and hmtx tables.

        Args:
            font: TtfFont instance with GSUB table available
            features: List of feature tags to bake (e.g., ["smcp", "onum"]).
                     If None or empty, uses all available features.

        Returns:
            BakedFeatureResult with statistics about the bake operation.

        Raises:
            ValueError: If font is not a TtfFont or GSUB table is missing
            NotImplementedError: If feature tags are not supported
        """
        if not isinstance(font, TtfFont):
            raise ValueError("OpenTypeFeatureBaker only supports TtfFont (TTF/OTF)")

        if font.ttf_tables.gsub is None:
            raise ValueError("Font has no GSUB table; cannot bake features")

        gsub = font.ttf_tables.gsub

        if features is None or len(features) == 0:
            available_features = gsub.list_all_features()
            if not available_features:
                return BakedFeatureResult(
                    remapped_codepoints=0,
                    feature_tags_baked=[],
                    substitution_rules_applied=0
                )
            features = available_features
        else:
            available = set(gsub.list_all_features())
            for tag in features:
                if tag not in available:
                    raise NotImplementedError(f"Feature '{tag}' not found in GSUB table")

        substitution_map: dict[int, int] = {}
        ligature_rules: dict[tuple[int, ...], int] = {}

        for feature_tag in features:
            single_subs = gsub.get_single_substitutions(feature_tag)
            for old_gid, new_gid in single_subs.items():
                if old_gid.value not in substitution_map:
                    substitution_map[old_gid.value] = new_gid.value

            ligatures = gsub.get_ligatures(feature_tag)
            for input_seq, ligature_gid in ligatures.items():
                ligature_rules[tuple(gid.value for gid in input_seq)] = ligature_gid.value

        substitution_rules_count = len(substitution_map) + len(ligature_rules)

        cmap_subtable = font.ttf_tables.cmap.best_subtable()
        mapping: dict[int, int] = cmap_subtable._mapping.copy()
        remapped_count = 0

        for codepoint, old_gid in mapping.items():
            if old_gid in substitution_map:
                new_gid = substitution_map[old_gid]
                mapping[codepoint] = new_gid
                remapped_count += 1

        cmap_subtable._mapping = mapping

        hmtx = font.ttf_tables.hmtx
        if hmtx is not None:
            for old_gid, new_gid in substitution_map.items():
                if old_gid < len(hmtx.metrics) and new_gid < len(hmtx.metrics):
                    new_metric = hmtx.metrics[new_gid]
                    hmtx.metrics[old_gid] = new_metric

        return BakedFeatureResult(
            remapped_codepoints=remapped_count,
            feature_tags_baked=features,
            substitution_rules_applied=substitution_rules_count
        )
