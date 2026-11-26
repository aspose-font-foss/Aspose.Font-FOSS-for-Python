"""Font subsetting quality auditor (FONT-507)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from aspose_font._font_base import Font

# Composite glyph flag constants (from TTF spec)
_ARG_1_AND_2_ARE_WORDS = 0x0001
_ARGS_ARE_XY_VALUES = 0x0002
_WE_HAVE_A_SCALE = 0x0008
_MORE_COMPONENTS = 0x0020
_WE_HAVE_AN_X_AND_Y_SCALE = 0x0040
_WE_HAVE_A_TWO_BY_TWO = 0x0080
_WE_HAVE_INSTRUCTIONS = 0x0100


@dataclass(slots=True, frozen=True)
class GlyphCoverageAudit:
    """Audit result for glyph/character coverage comparison."""

    kind: str
    label: str
    original_count: int
    subset_count: int
    missing_gids: tuple[int, ...]
    missing_codepoints: tuple[int, ...]

    def is_lossless(self) -> bool:
        return len(self.missing_gids) == 0 and len(self.missing_codepoints) == 0


@dataclass(slots=True, frozen=True)
class CompositeDependencyAudit:
    """Audit result for composite glyph component dependencies."""

    glyph_id: int
    glyph_name: str | None
    components_in_original: tuple[int, ...]
    components_in_subset: tuple[int, ...]
    missing_components: tuple[int, ...]
    has_missing: bool

    def is_complete(self) -> bool:
        return len(self.missing_components) == 0


@dataclass(slots=True, frozen=True)
class VariationDeltaAudit:
    """Audit result for gvar/HVAR delta consistency."""

    table_name: str
    glyph_id: int
    original_delta_count: int
    subset_delta_count: int
    deltas_lost: int
    is_consistent: bool

    def can_reconstruct(self) -> bool:
        return self.deltas_lost == 0 and self.is_consistent


@dataclass(slots=True, frozen=True)
class FeatureAudit:
    """Audit result for GSUB/GPOS feature validation."""

    table_name: str
    features_in_original: tuple[str, ...]
    features_in_subset: tuple[str, ...]
    missing_features: tuple[str, ...]
    features_preserved_pct: float

    def has_all_features(self) -> bool:
        return len(self.missing_features) == 0


@dataclass(slots=True, frozen=True)
class FontSubsettingAuditResult:
    """Complete audit result for a font subsetting operation."""

    original_glyph_count: int
    subset_glyph_count: int
    coverage: GlyphCoverageAudit
    composite_dependencies: tuple[CompositeDependencyAudit, ...]
    variation_deltas: tuple[VariationDeltaAudit, ...]
    features: tuple[FeatureAudit, ...]
    overall_passed: bool
    issues: tuple[dict[str, Any], ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": "font_subsetting_audit",
            "original_glyph_count": self.original_glyph_count,
            "subset_glyph_count": self.subset_glyph_count,
            "coverage": {
                "kind": self.coverage.kind,
                "label": self.coverage.label,
                "original_count": self.coverage.original_count,
                "subset_count": self.coverage.subset_count,
                "missing_gids": list(self.coverage.missing_gids),
                "missing_codepoints": list(self.coverage.missing_codepoints),
            },
            "composite_dependencies": [
                {
                    "glyph_id": d.glyph_id,
                    "glyph_name": d.glyph_name,
                    "components_in_original": list(d.components_in_original),
                    "components_in_subset": list(d.components_in_subset),
                    "missing_components": list(d.missing_components),
                    "has_missing": d.has_missing,
                }
                for d in self.composite_dependencies
            ],
            "variation_deltas": [
                {
                    "table_name": d.table_name,
                    "glyph_id": d.glyph_id,
                    "original_delta_count": d.original_delta_count,
                    "subset_delta_count": d.subset_delta_count,
                    "deltas_lost": d.deltas_lost,
                    "is_consistent": d.is_consistent,
                }
                for d in self.variation_deltas
            ],
            "features": [
                {
                    "table_name": f.table_name,
                    "features_in_original": list(f.features_in_original),
                    "features_in_subset": list(f.features_in_subset),
                    "missing_features": list(f.missing_features),
                    "features_preserved_pct": f.features_preserved_pct,
                }
                for f in self.features
            ],
            "overall_passed": self.overall_passed,
            "issues": list(self.issues),
        }

    def to_json(self) -> str:
        import json

        return json.dumps(self.to_dict(), indent=2, sort_keys=True)


class FontSubsettingAuditor:
    """Validates font subsetting quality and correctness."""

    def __init__(self, original_font: Font, subsetted_font: Font) -> None:
        self._original = original_font
        self._subset = subsetted_font
        self._issues: list[dict[str, Any]] = []

    def _audit_glyph_coverage(self) -> GlyphCoverageAudit:
        """Compare glyph/character coverage between original and subset."""
        original_gids = {
            int(gid) for gid in self._original.glyph_accessor.get_all_glyph_ids()
        }
        original_codepoints = set(self._original.encoding.get_all_codepoints())

        subset_gids = {
            int(gid) for gid in self._subset.glyph_accessor.get_all_glyph_ids()
        }
        subset_codepoints = set(self._subset.encoding.get_all_codepoints())

        missing_gids = tuple(sorted(original_gids - subset_gids))
        missing_codepoints = tuple(sorted(original_codepoints - subset_codepoints))

        return GlyphCoverageAudit(
            kind="glyph",
            label="subset",
            original_count=len(original_gids),
            subset_count=len(subset_gids),
            missing_gids=missing_gids,
            missing_codepoints=missing_codepoints,
        )

    def _get_component_gids_for_font(self, font: Font, gid: int) -> tuple[int, ...]:
        """Extract component GIDs from composite glyph by parsing raw glyf data.

        This parses the composite glyph structure WITHOUT applying transformations,
        extracting ONLY the component GIDs needed for dependency auditing.

        Args:
            font: Font whose glyf table to use (original or subset)
            gid: Glyph ID to inspect

        Returns:
            Sorted tuple of component GIDs, or empty tuple if not composite or on error
        """
        if font.ttf_tables.glyf is None:
            return ()

        try:
            raw = font.ttf_tables.glyf.get_glyph_bytes(
                self._get_glyph_offset_for_font(font, gid),
                self._get_glyph_length_for_font(font, gid)
            )

            if len(raw) < 10:
                return ()

            contour_count = int.from_bytes(raw[0:2], "big")
            if contour_count >= 0:
                return ()  # Not a composite glyph

            pos = 10
            components: list[int] = []
            last_flags = 0

            while pos + 4 <= len(raw):
                flags = int.from_bytes(raw[pos:pos+2], "big")
                pos += 2
                component_gid = int.from_bytes(raw[pos:pos+2], "big")
                pos += 2
                components.append(component_gid)

                if flags & _ARG_1_AND_2_ARE_WORDS:
                    pos += 4
                else:
                    pos += 2

                if flags & _WE_HAVE_A_SCALE:
                    pos += 2
                elif flags & _WE_HAVE_AN_X_AND_Y_SCALE:
                    pos += 4
                elif flags & _WE_HAVE_A_TWO_BY_TWO:
                    pos += 8

                last_flags = flags
                if not (flags & _MORE_COMPONENTS):
                    break

            if last_flags & _WE_HAVE_INSTRUCTIONS:
                instr_len = int.from_bytes(raw[pos:pos+2], "big")
                pos += 2 + instr_len

            return tuple(sorted(set(components)))

        except Exception:
            return ()

    def _get_glyph_offset_for_font(self, font: Font, gid: int) -> int:
        """Get glyf table offset for a glyph ID from the given font."""
        if font.ttf_tables.loca is None:
            return 0
        try:
            return font.ttf_tables.loca.glyph_offset(gid)
        except Exception:
            return 0

    def _get_glyph_length_for_font(self, font: Font, gid: int) -> int:
        """Get glyf table length for a glyph ID from the given font."""
        if font.ttf_tables.loca is None:
            return 0
        try:
            return font.ttf_tables.loca.glyph_length(gid)
        except Exception:
            return 0

    def _has_glyph_in_subset(self, gid: int) -> bool:
        """Check if glyph exists in subset font."""
        try:
            self._subset.glyph_accessor.get_glyph_by_id(gid)
            return True
        except Exception:
            return False

    def _get_glyph_name(self, gid: int) -> str | None:
        """Get glyph name for GID."""
        try:
            glyph = self._original.glyph_accessor.get_glyph_by_id(gid)
            return glyph.glyph_name
        except Exception:
            return None

    def _is_composite_glyph(self, gid: int) -> bool:
        """Check if glyph is composite (multi-component) by inspecting raw glyf data."""
        if self._original.ttf_tables.glyf is None:
            return False

        try:
            raw = self._original.ttf_tables.glyf.get_glyph_bytes(
                self._get_glyph_offset_for_font(self._original, gid),
                self._get_glyph_length_for_font(self._original, gid)
            )
            if len(raw) < 10:
                return False
            contour_count = int.from_bytes(raw[0:2], "big")
            return contour_count == -1  # Composite glyphs have n_contours = -1
        except Exception:
            return False

    def _audit_composite_dependencies(self) -> tuple[CompositeDependencyAudit, ...]:
        """Validate composite glyph component dependencies are retained."""
        results: list[CompositeDependencyAudit] = []

        for gid in self._original.glyph_accessor.get_all_glyph_ids():
            gid_int = int(gid)

            if not self._is_composite_glyph(gid_int):
                continue

            original_components = self._get_component_gids_for_font(self._original, gid_int)

            if not self._has_glyph_in_subset(gid_int):
                results.append(
                    CompositeDependencyAudit(
                        glyph_id=gid_int,
                        glyph_name=self._get_glyph_name(gid_int),
                        components_in_original=original_components,
                        components_in_subset=(),
                        missing_components=original_components,
                        has_missing=True,
                    )
                )
                self._issues.append({
                    "type": "composite_glyph_lost",
                    "glyph_id": gid_int,
                    "reason": "Composite glyph dropped in subset",
                })
                continue

            subset_components = self._get_component_gids_for_font(self._subset, gid_int)

            missing = tuple(sorted(set(original_components) - set(subset_components)))

            results.append(
                CompositeDependencyAudit(
                    glyph_id=gid_int,
                    glyph_name=self._get_glyph_name(gid_int),
                    components_in_original=original_components,
                    components_in_subset=subset_components,
                    missing_components=missing,
                    has_missing=bool(missing),
                )
            )

            if missing:
                self._issues.append({
                    "type": "composite_components_lost",
                    "glyph_id": gid_int,
                    "missing_components": list(missing),
                })

        return tuple(results)

    def _audit_gvar_deltas(self) -> tuple[VariationDeltaAudit, ...]:
        """Check gvar delta store consistency for subsetted glyphs."""
        results: list[VariationDeltaAudit] = []

        if "gvar" not in self._original.ttf_tables._raw:
            return tuple(results)

        if "gvar" not in self._subset.ttf_tables._raw:
            self._issues.append({
                "type": "gvar_table_missing",
                "reason": "gvar table absent in subsetted font",
            })
            return tuple(results)

        original_gvar = self._original.ttf_tables.gvar
        subset_gvar = self._subset.ttf_tables.gvar

        for gid in range(min(self._original.num_glyphs, self._subset.num_glyphs)):
            try:
                glyph = self._original.glyph_accessor.get_glyph_by_id(gid)
                point_count = 0
                if glyph.path:
                    point_count = len(glyph.path)

                if point_count == 0:
                    continue

                original_variations = original_gvar.glyph_variations(gid, point_count)
                subset_variations = subset_gvar.glyph_variations(gid, point_count)

                deltas_lost = len(original_variations) - len(subset_variations)
                is_consistent = deltas_lost == 0

                results.append(
                    VariationDeltaAudit(
                        table_name="gvar",
                        glyph_id=gid,
                        original_delta_count=len(original_variations),
                        subset_delta_count=len(subset_variations),
                        deltas_lost=deltas_lost,
                        is_consistent=is_consistent,
                    )
                )

                if deltas_lost > 0 or not is_consistent:
                    self._issues.append({
                        "type": "gvar_delta_loss",
                        "glyph_id": gid,
                        "deltas_lost": deltas_lost,
                        "is_consistent": is_consistent,
                    })
            except Exception:
                continue

        return tuple(results)

    def _audit_hvar_deltas(self) -> tuple[VariationDeltaAudit, ...]:
        """Check HVAR delta store consistency for subsetted glyphs."""
        results: list[VariationDeltaAudit] = []

        if self._original.ttf_tables.hvar is None:
            return tuple(results)

        if self._subset.ttf_tables.hvar is None:
            self._issues.append({
                "type": "hvar_table_missing",
                "reason": "HVAR table absent in subsetted font",
            })
            return tuple(results)

        original_mapping = self._original.ttf_tables.hvar.advance_width_mapping
        subset_mapping = self._subset.ttf_tables.hvar.advance_width_mapping

        if original_mapping is None or subset_mapping is None:
            return tuple(results)

        for gid in range(min(self._original.num_glyphs, self._subset.num_glyphs)):
            try:
                orig_dsi = original_mapping.get(gid)
                subset_dsi = subset_mapping.get(gid)

                is_consistent = (
                    orig_dsi.outer == subset_dsi.outer
                    and orig_dsi.inner == subset_dsi.inner
                )

                results.append(
                    VariationDeltaAudit(
                        table_name="HVAR",
                        glyph_id=gid,
                        original_delta_count=1,
                        subset_delta_count=1,
                        deltas_lost=0,
                        is_consistent=is_consistent,
                    )
                )

                if not is_consistent:
                    self._issues.append({
                        "type": "hvar_delta_mismatch",
                        "glyph_id": gid,
                        "original": (orig_dsi.outer, orig_dsi.inner),
                        "subset": (subset_dsi.outer, subset_dsi.inner),
                    })
            except Exception:
                continue

        return tuple(results)

    def _audit_gsub_features(self) -> FeatureAudit:
        """Validate GSUB feature preservation in subset."""
        if self._original.ttf_tables.gsub is None:
            return FeatureAudit(
                table_name="GSUB",
                features_in_original=(),
                features_in_subset=(),
                missing_features=(),
                features_preserved_pct=1.0
                if self._subset.ttf_tables.gsub is None
                else 0.0,
            )

        if self._subset.ttf_tables.gsub is None:
            self._issues.append({
                "type": "gsub_table_missing",
                "reason": "GSUB table absent in subsetted font",
            })
            original_features = tuple(self._original.ttf_tables.gsub.list_all_features())
            return FeatureAudit(
                table_name="GSUB",
                features_in_original=original_features,
                features_in_subset=(),
                missing_features=original_features,
                features_preserved_pct=0.0,
            )

        original_features = tuple(self._original.ttf_tables.gsub.list_all_features())
        subset_features = tuple(self._subset.ttf_tables.gsub.list_all_features())

        missing = tuple(sorted(set(original_features) - set(subset_features)))
        preserved_pct = (
            len(subset_features) / len(original_features) if original_features else 1.0
        )

        return FeatureAudit(
            table_name="GSUB",
            features_in_original=original_features,
            features_in_subset=subset_features,
            missing_features=missing,
            features_preserved_pct=preserved_pct,
        )

    def _audit_gpos_features(self) -> FeatureAudit:
        """Validate GPOS feature preservation in subset."""
        if self._original.ttf_tables.gpos is None:
            return FeatureAudit(
                table_name="GPOS",
                features_in_original=(),
                features_in_subset=(),
                missing_features=(),
                features_preserved_pct=1.0
                if self._subset.ttf_tables.gpos is None
                else 0.0,
            )

        if self._subset.ttf_tables.gpos is None:
            self._issues.append({
                "type": "gpos_table_missing",
                "reason": "GPOS table absent in subsetted font",
            })
            original_features = tuple(self._original.ttf_tables.gpos.list_all_features())
            return FeatureAudit(
                table_name="GPOS",
                features_in_original=original_features,
                features_in_subset=(),
                missing_features=original_features,
                features_preserved_pct=0.0,
            )

        original_features = tuple(self._original.ttf_tables.gpos.list_all_features())
        subset_features = tuple(self._subset.ttf_tables.gpos.list_all_features())

        missing = tuple(sorted(set(original_features) - set(subset_features)))
        preserved_pct = (
            len(subset_features) / len(original_features) if original_features else 1.0
        )

        return FeatureAudit(
            table_name="GPOS",
            features_in_original=original_features,
            features_in_subset=subset_features,
            missing_features=missing,
            features_preserved_pct=preserved_pct,
        )

    @classmethod
    def audit(
        cls,
        original_font: Font,
        subsetted_font: Font,
        *,
        check_gvar: bool = True,
        check_hvar: bool = True,
        check_gsub: bool = True,
        check_gpos: bool = True,
        check_composites: bool = True,
    ) -> FontSubsettingAuditResult:
        """Compare original and subsetted fonts for subsetting correctness.

        Args:
            original_font: Original font before subsetting
            subsetted_font: Font after subsetting
            check_gvar: Validate gvar table variations
            check_hvar: Validate HVAR table variations
            check_gsub: Validate GSUB feature table
            check_gpos: Validate GPOS feature table
            check_composites: Validate composite glyph component dependencies

        Returns:
            FontSubsettingAuditResult with complete diagnostics
        """
        auditor = cls(original_font, subsetted_font)

        coverage_audit = auditor._audit_glyph_coverage()

        composite_audits: tuple[CompositeDependencyAudit, ...] = ()
        if check_composites:
            composite_audits = auditor._audit_composite_dependencies()

        delta_audits: tuple[VariationDeltaAudit, ...] = ()
        if check_gvar:
            delta_audits += auditor._audit_gvar_deltas()
        if check_hvar:
            delta_audits += auditor._audit_hvar_deltas()

        feature_audits: tuple[FeatureAudit, ...] = ()
        if check_gsub:
            feature_audits += (auditor._audit_gsub_features(),)
        if check_gpos:
            feature_audits += (auditor._audit_gpos_features(),)

        issues = list(auditor._issues)
        overall_passed = (
            coverage_audit.is_lossless()
            and all(c.is_complete() for c in composite_audits)
            and all(d.can_reconstruct() for d in delta_audits)
            and all(f.has_all_features() for f in feature_audits)
        )

        return FontSubsettingAuditResult(
            original_glyph_count=original_font.num_glyphs,
            subset_glyph_count=subsetted_font.num_glyphs,
            coverage=coverage_audit,
            composite_dependencies=composite_audits,
            variation_deltas=delta_audits,
            features=feature_audits,
            overall_passed=overall_passed,
            issues=tuple(issues),
        )
