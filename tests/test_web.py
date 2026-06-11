"""Tests for SPEC-032 web font bundle generation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from aspose_font import (
    FamilyReviewExportPackage,
    FontLoader,
    WebFontBuilder,
    WebFontFamilyPackage,
    Woff2Font,
)
from aspose_font._exceptions import FontNotSupportedException
from aspose_font.preview import _decode_png_rgb
from aspose_font.ttf.font import TtfFont


def test_web_bundle_static_instance_contains_font_assets_css_and_html(roboto: TtfFont):
    bundle = WebFontBuilder.build(
        roboto,
        instance_coordinates={"wght": 700.0},
        presets=("latin",),
        preview_text="Hello Web",
    )

    assert bundle.family == "Roboto Instance"
    assert bundle.style == "Bold"
    assert bundle.css_filename.endswith(".css")
    assert bundle.html_filename.endswith(".html")
    assert [asset.filename for asset in bundle.font_assets] == [
        "roboto-instance-bold.woff2",
        "roboto-instance-bold.woff",
    ]
    assert "@font-face" in bundle.css
    assert "font-display: swap;" in bundle.css
    assert "Hello Web" in bundle.html

    woff2_asset = bundle.font_assets[0]
    reloaded = FontLoader.open(woff2_asset.data)
    assert isinstance(reloaded, Woff2Font)


def test_web_bundle_preserve_family_naming_strategy(roboto: TtfFont):
    bundle = WebFontBuilder.build(
        roboto,
        instance_name="Bold",
        include_woff=False,
        naming_strategy="preserve-family",
    )

    assert bundle.family == "Roboto"
    assert bundle.style == "Bold"
    assert [asset.filename for asset in bundle.font_assets] == ["roboto-bold.woff2"]
    assert bundle.manifest["requested_naming_strategy"] == "preserve-family"
    assert bundle.manifest["export_mode"] == "static-instance"


def test_web_bundle_menu_safe_naming_strategy(roboto: TtfFont):
    bundle = WebFontBuilder.build(
        roboto,
        instance_name="Bold",
        include_woff=False,
        naming_strategy="menu-safe",
    )

    assert bundle.family == "Roboto Instance"
    assert bundle.style == "Bold"
    assert [asset.filename for asset in bundle.font_assets] == ["roboto-instance-bold.woff2"]
    assert bundle.manifest["requested_naming_strategy"] == "menu-safe"
    assert bundle.preview_font is not None
    assert bundle.preview_font.ttf_tables.name.get(16) == "Roboto"


def test_web_bundle_ribbi_safe_naming_strategy(roboto: TtfFont):
    bundle = WebFontBuilder.build(
        roboto,
        instance_name="Condensed Bold",
        include_woff=False,
        naming_strategy="ribbi-safe",
    )

    assert bundle.family == "Roboto Instance"
    assert bundle.style == "Bold"
    assert [asset.filename for asset in bundle.font_assets] == ["roboto-instance-bold.woff2"]
    assert bundle.manifest["requested_naming_strategy"] == "ribbi-safe"
    assert bundle.preview_font is not None
    assert bundle.preview_font.ttf_tables.name.get(17) == "Condensed Bold"


def test_web_bundle_manifest_includes_stat_policy_recommendation(roboto: TtfFont):
    bundle = WebFontBuilder.build(
        roboto,
        instance_name="Bold",
        include_woff=False,
        naming_strategy="ribbi-safe",
        stat_policy="static",
    )

    assert bundle.manifest["requested_stat_policy"] == "static"
    assert bundle.manifest["stat_policy_recommendation"] == "use-requested-static"
    assert bundle.manifest["stat_policy_recommendation_reasons"] == [
        "static-policy-requested",
        "generated-static-stat-synthesized",
        "generated-axis-value-flags-nonzero",
    ]
    assert bundle.manifest["stat_policy_override_suggestion"] is None
    assert bundle.manifest["stat_policy_override_suggestion_reasons"] == [
        "requested-static-policy-already-applied"
    ]


def test_web_bundle_accepts_custom_family_suffix(roboto: TtfFont):
    bundle = WebFontBuilder.build(
        roboto,
        instance_name="Bold",
        include_woff=False,
        naming_strategy="instance-family",
        family_suffix="Beta",
    )

    assert bundle.family == "Roboto Beta"
    assert bundle.style == "Bold"
    assert bundle.manifest["requested_naming_strategy"] == "instance-family"
    assert bundle.manifest["requested_family_suffix"] == "Beta"
    assert bundle.preview_font is not None
    assert bundle.preview_font.font_family == "Roboto Beta"


def test_web_bundle_accepts_name_overrides(roboto: TtfFont):
    bundle = WebFontBuilder.build(
        roboto,
        instance_name="Condensed Bold",
        include_woff=False,
        naming_strategy="ribbi-safe",
        legacy_family_name="Acme Sans Menu",
        typographic_family_name="Acme Sans Pro",
        legacy_style_name="Bold",
        typographic_style_name="Condensed Bold",
    )

    assert bundle.family == "Acme Sans Menu"
    assert bundle.style == "Bold"
    assert [asset.filename for asset in bundle.font_assets] == ["acme-sans-menu-bold.woff2"]
    assert bundle.manifest["requested_legacy_family_name"] == "Acme Sans Menu"
    assert bundle.manifest["requested_typographic_family_name"] == "Acme Sans Pro"
    assert bundle.manifest["requested_legacy_style_name"] == "Bold"
    assert bundle.manifest["requested_typographic_style_name"] == "Condensed Bold"
    assert bundle.preview_font is not None
    assert bundle.preview_font.ttf_tables.name.get(16) == "Acme Sans Pro"
    assert bundle.preview_font.ttf_tables.name.get(17) == "Condensed Bold"


def test_web_bundle_variable_export_surfaces_axis_metadata(roboto: TtfFont):
    bundle = WebFontBuilder.build(roboto, include_woff=False)

    assert [asset.filename for asset in bundle.font_assets] == [
        "roboto-regular.woff2",
    ]
    assert bundle.manifest["export_mode"] == "variable-live"
    assert bundle.manifest["output_is_variable"] is True
    assert bundle.manifest["stat_policy_recommendation"] is None
    assert bundle.manifest["stat_policy_recommendation_reasons"] == []
    assert bundle.manifest["stat_policy_override_suggestion"] is None
    assert bundle.manifest["stat_policy_override_suggestion_reasons"] == []
    assert "font-weight: 100 900;" in bundle.css
    assert "font-stretch: 75% 100%;" in bundle.css
    assert "Variable Axes" in bundle.html
    assert "Weight" in bundle.html
    assert "<strong>Export Mode:</strong> Variable Live" in bundle.html
    assert 'class="axis-controls"' in bundle.html
    assert 'data-axis="wght"' in bundle.html
    assert 'data-axis="wdth"' in bundle.html
    assert 'data-axis-value="wght"' in bundle.html
    assert "fontVariationSettings" in bundle.html
    assert "updateVariationSettings();" in bundle.html
    assert ".axis-controls" in bundle.css
    assert ".axis-control" in bundle.css
    assert ".axis-range" in bundle.css


def test_web_bundle_accepts_explicit_live_variable_mode(roboto: TtfFont):
    bundle = WebFontBuilder.build(roboto, include_woff=False, variable_mode="live")

    assert bundle.manifest["requested_variable_mode"] == "live"
    assert bundle.manifest["export_mode"] == "variable-live"
    assert bundle.manifest["output_is_variable"] is True
    assert "Variable Axes" in bundle.html


def test_web_bundle_accepts_editorial_template(roboto: TtfFont):
    bundle = WebFontBuilder.build(roboto, include_woff=False, specimen_template="editorial")

    assert 'body class="specimen-template-editorial"' in bundle.html
    assert "<strong>Template:</strong> Editorial" in bundle.html
    assert "body.specimen-template-editorial" in bundle.css
    assert "font-family: Georgia, serif;" in bundle.css


def test_web_bundle_static_instance_does_not_emit_variable_axis_controls(roboto: TtfFont):
    bundle = WebFontBuilder.build(
        roboto,
        instance_coordinates={"wght": 700.0},
        include_woff=False,
    )

    assert bundle.manifest["export_mode"] == "static-instance"
    assert 'class="axis-controls"' not in bundle.html
    assert "fontVariationSettings" not in bundle.html


def test_web_bundle_variable_subsetting_auto_instantiates_default_instance(roboto: TtfFont):
    bundle = WebFontBuilder.build(
        roboto,
        presets=("latin",),
        codepoints=[0x10FFFF],
        include_woff=False,
    )

    assert bundle.style == "Regular"
    assert bundle.manifest["export_mode"] == "static-subset-from-variable-default"
    assert "default instance was generated before subsetting" in bundle.manifest["export_reason"]
    assert bundle.manifest["source_is_variable"] is True
    assert bundle.manifest["output_is_variable"] is False
    assert bundle.manifest["auto_instanced_default"] is True
    assert "auto-instantiated at the default coordinates" in bundle.manifest["export_note"]
    coverage = bundle.manifest["subset"]["coverage"]
    assert 0x10FFFF in coverage["missing_codepoints"]
    assert coverage["groups"][0]["kind"] == "preset"
    assert coverage["groups"][1]["kind"] == "codepoints"
    assert coverage["groups"][1]["missing_codepoints"] == [0x10FFFF]
    assert 'class="axis-controls"' not in bundle.html
    assert "fontVariationSettings" not in bundle.html
    assert "Subset requests on variable fonts currently export a static bundle" in bundle.html


def test_web_bundle_manifest_records_subset_coverage_groups(roboto: TtfFont):
    bundle = WebFontBuilder.build(
        roboto,
        include_woff=False,
        text="A",
        codepoints=[0x10FFFF],
        ranges=[(ord("B"), ord("B"))],
        variable_mode="static",
    )

    coverage = bundle.manifest["subset"]["coverage"]
    assert coverage["requested_count"] == 3
    assert coverage["covered_codepoints"] == [ord("A"), ord("B")]
    assert coverage["missing_codepoints"] == [0x10FFFF]
    assert coverage["fully_covered"] is False
    assert [group["kind"] for group in coverage["groups"]] == ["text", "codepoints", "range"]


def test_web_bundle_manifest_records_empty_subset_coverage_when_no_subset(roboto: TtfFont):
    bundle = WebFontBuilder.build(roboto, include_woff=False, variable_mode="static")

    assert bundle.manifest["subset"]["applied"] is False
    assert bundle.manifest["subset"]["coverage"] is None
    assert bundle.manifest["export_reason"] == "explicit static mode or instance selection requested"


def test_web_bundle_accepts_explicit_static_mode_without_instance_selection(roboto: TtfFont):
    bundle = WebFontBuilder.build(
        roboto,
        include_woff=False,
        variable_mode="static",
    )

    assert bundle.family == "Roboto Instance"
    assert bundle.style == "Regular"
    assert bundle.manifest["requested_variable_mode"] == "static"
    assert bundle.manifest["export_mode"] == "static-instance"
    assert bundle.manifest["requested_naming_strategy"] == "instance-family"
    assert bundle.manifest["output_is_variable"] is False
    assert 'class="axis-controls"' not in bundle.html


def test_web_bundle_rejects_live_variable_mode_with_subsetting(roboto: TtfFont):
    with pytest.raises(
        FontNotSupportedException,
        match="does not support subsetting",
    ):
        WebFontBuilder.build(
            roboto,
            include_woff=False,
            variable_mode="live",
            presets=("latin",),
        )


def test_web_bundle_write_to_outputs_all_files(roboto: TtfFont, tmp_path: Path):
    bundle = WebFontBuilder.build(
        roboto,
        instance_coordinates={"wght": 700.0},
        presets=("latin",),
        include_woff=False,
    )

    written = bundle.write_to(tmp_path)
    assert {path.name for path in written} == {
        "roboto-instance-bold.woff2",
        "roboto-instance-bold.css",
        "roboto-instance-bold.html",
        "web-manifest.json",
    }
    assert (tmp_path / bundle.css_filename).read_text(encoding="utf-8") == bundle.css
    assert (tmp_path / bundle.html_filename).read_text(encoding="utf-8") == bundle.html
    manifest = json.loads((tmp_path / "web-manifest.json").read_text(encoding="utf-8"))
    assert manifest["kind"] == "web_bundle"
    assert manifest["style"] == "Bold"
    assert manifest["source_is_variable"] is True
    assert manifest["output_is_variable"] is False


def test_smart_instancer_builds_multiple_web_bundles(roboto: TtfFont):
    bundles = roboto.smart_instancer.build_web_bundles(["Bold", "Condensed Bold"], include_woff=False)
    assert len(bundles) == 2
    assert bundles[0][1].font_assets[0].filename == "roboto-instance-bold.woff2"
    assert bundles[1][1].font_assets[0].filename == "roboto-instance-condensed-bold.woff2"


def test_smart_instancer_web_bundles_accept_naming_strategy(roboto: TtfFont):
    bundles = roboto.smart_instancer.build_web_bundles(
        ["Bold"],
        include_woff=False,
        naming_strategy="qa-tagged",
    )

    assert bundles[0][1].family == "Roboto QA"
    assert bundles[0][1].font_assets[0].filename == "roboto-qa-bold.woff2"
    assert bundles[0][1].manifest["requested_naming_strategy"] == "qa-tagged"


def test_smart_instancer_builds_axis_grid_web_bundles(roboto: TtfFont):
    bundles = roboto.smart_instancer.build_axis_grid_web_bundles(
        "wght",
        [400.0, 700.0],
        include_woff=False,
        preview_text="Grid Web",
        naming_strategy="preserve-family",
    )

    assert [resolved.coordinates["wght"] for resolved, _bundle in bundles] == [400.0, 700.0]
    assert [bundle.family for _resolved, bundle in bundles] == ["Roboto", "Roboto"]
    assert [bundle.style for _resolved, bundle in bundles] == ["Regular", "Bold"]
    assert bundles[0][1].font_assets[0].filename == "roboto-regular.woff2"
    assert bundles[1][1].font_assets[0].filename == "roboto-bold.woff2"
    assert bundles[1][1].manifest["requested_naming_strategy"] == "preserve-family"
    assert "Grid Web" in bundles[1][1].html


def test_smart_instancer_axis_grid_web_bundles_support_two_axes(roboto: TtfFont):
    bundles = roboto.smart_instancer.build_axis_grid_web_bundles(
        "wght",
        [400.0, 700.0],
        secondary_axis_tag="wdth",
        secondary_values=[75.0, 100.0],
        include_woff=False,
    )

    assert len(bundles) == 4
    assert bundles[0][0].coordinates["wdth"] == 75.0
    assert bundles[-1][0].coordinates["wght"] == 700.0
    assert any(bundle.style == "Condensed Bold" for _resolved, bundle in bundles)


def test_smart_instancer_axis_grid_web_bundles_require_values(roboto: TtfFont):
    with pytest.raises(ValueError, match="requires at least one value"):
        roboto.smart_instancer.build_axis_grid_web_bundles("wght", [], include_woff=False)


def test_smart_instancer_builds_axis_grid_web_family_package(roboto: TtfFont):
    package = roboto.smart_instancer.build_axis_grid_web_family_package(
        "wght",
        [400.0, 700.0],
        family_name="Roboto Grid",
        include_woff=False,
        preview_text="Grid Family",
        naming_strategy="preserve-family",
    )

    assert isinstance(package, WebFontFamilyPackage)
    assert package.family_name == "Roboto Grid"
    assert len(package.bundles) == 2
    assert package.css.count("@font-face") == 2
    assert "Grid Family" in package.html
    assert "Waterfall" in package.html
    assert "Matrix" in package.html
    assert "<strong>Coordinates:</strong> wdth=100 wght=700" in package.html
    assert "<h3>wdth=100 wght=700</h3>" in package.html
    assert package.manifest["bundle_count"] == 2
    assert package.manifest["bundles"][0]["requested_naming_strategy"] == "preserve-family"
    assert package.manifest["bundles"][1]["review_label"] == "wdth=100 wght=700"
    assert package.manifest["bundles"][1]["instance_coordinates"] == {"wdth": 100.0, "wght": 700.0}
    assert package.manifest["bundles"][1]["stat_policy_recommendation"] == "review-before-drop"
    assert package.manifest["bundles"][1]["stat_policy_recommendation_reasons"] == [
        "source-stat-dropped-by-default",
        "source-stat-name-ids-uncovered",
    ]
    assert package.manifest["bundles"][1]["stat_policy_override_suggestion"] is None
    assert package.manifest["bundles"][1]["stat_policy_override_suggestion_reasons"] == [
        "manual-review-required"
    ]
    assert [asset.filename for asset in package.assets] == [
        "family-waterfall.png",
        "family-matrix.png",
    ]


def test_family_manifest_includes_nested_coverage_summary(roboto: TtfFont):
    package = roboto.smart_instancer.build_web_family_package(
        ["Bold"],
        include_woff=False,
        text="A",
        codepoints=[0x10FFFF],
    )

    summary = package.manifest["bundles"][0]["coverage"]
    assert summary["requested_count"] == 2
    assert summary["covered_count"] == 1
    assert summary["missing_count"] == 1
    assert summary["missing_codepoints_sample"] == [0x10FFFF]


def test_axis_grid_family_matrix_preview_uses_sheet_layout(roboto: TtfFont):
    package = roboto.smart_instancer.build_axis_grid_web_family_package(
        "wght",
        [400.0, 700.0],
        secondary_axis_tag="wdth",
        secondary_values=[75.0, 100.0],
        family_name="Roboto Grid",
        include_woff=False,
        preview_text="Grid Family",
        naming_strategy="preserve-family",
    )

    matrix_asset = next(asset for asset in package.assets if asset.filename == "family-matrix.png")
    width, height, _pixels = _decode_png_rgb(matrix_asset.data)

    assert width > height


def test_smart_instancer_builds_family_package(roboto: TtfFont):
    package = roboto.smart_instancer.build_web_family_package(
        ["Bold", "Condensed Bold"],
        include_woff=False,
        preview_text="Family Preview",
    )
    assert isinstance(package, WebFontFamilyPackage)
    assert len(package.bundles) == 2
    assert package.css.count("@font-face") == 2
    assert "Condensed Bold" in package.html
    assert "Family Preview" in package.html
    assert "Waterfall" in package.html
    assert "Matrix" in package.html
    assert "<strong>Export Mode:</strong> Static Instance" in package.html
    assert "family-waterfall.png" in package.html
    assert "family-matrix.png" in package.html


def test_webfontbuilder_builds_standalone_family_waterfall_preview(roboto: TtfFont):
    bundles = [
        bundle
        for _resolved, bundle in roboto.smart_instancer.build_web_bundles(
            ["Bold", "Condensed Bold"],
            include_woff=False,
            preview_text="Standalone Waterfall",
        )
    ]

    preview = WebFontBuilder.build_family_waterfall_preview(
        bundles,
        preview_text="Standalone Waterfall",
    )

    assert preview.filename == "family-waterfall.png"
    assert preview.media_type == "image/png"
    assert preview.data.startswith(b"\x89PNG\r\n\x1a\n")


def test_webfontbuilder_builds_family_review_export_package(roboto: TtfFont):
    bundles = [
        bundle
        for _resolved, bundle in roboto.smart_instancer.build_web_bundles(
            ["Bold", "Condensed Bold"],
            include_default=True,
            include_woff=False,
            preview_text="Marketing Board",
        )
    ]

    package = WebFontBuilder.build_family_review_export_package(
        bundles,
        family_name="Roboto Marketing",
        preview_text="Marketing Board",
    )

    assert isinstance(package, FamilyReviewExportPackage)
    assert package.family_name == "Roboto Marketing"
    assert package.board.filename == "family-review-board.png"
    assert package.board.data.startswith(b"\x89PNG\r\n\x1a\n")
    assert [asset.filename for asset in package.assets] == [
        "family-waterfall.png",
        "family-matrix.png",
    ]
    assert "![Roboto Marketing family review board preview](family-review-board.png)" in package.markdown
    assert '<figure class="family-review-export">' in package.html
    assert package.manifest["kind"] == "family_review_export"
    assert package.manifest["family_name"] == "Roboto Marketing"
    assert package.manifest["board_filename"] == "family-review-board.png"
    assert package.manifest["asset_filenames"] == ["family-waterfall.png", "family-matrix.png"]
    assert package.manifest["bundle_count"] == 3


def test_family_review_export_package_write_to_outputs_all_files(roboto: TtfFont, tmp_path: Path):
    bundles = [
        bundle
        for _resolved, bundle in roboto.smart_instancer.build_web_bundles(
            ["Bold"],
            include_default=True,
            include_woff=False,
            preview_text="Release Kit",
        )
    ]
    package = WebFontBuilder.build_family_review_export_package(
        bundles,
        family_name="Roboto Release",
        preview_text="Release Kit",
    )

    written = package.write_to(tmp_path)

    assert {path.name for path in written} == {
        "family-review-board.png",
        "family-waterfall.png",
        "family-matrix.png",
        "family-review-board.md",
        "family-review-board.html",
        "family-review-board-manifest.json",
    }
    manifest = json.loads((tmp_path / "family-review-board-manifest.json").read_text(encoding="utf-8"))
    assert manifest["kind"] == "family_review_export"
    assert manifest["family_name"] == "Roboto Release"
    assert (tmp_path / "family-review-board.md").read_text(encoding="utf-8") == package.markdown
    assert (tmp_path / "family-review-board.html").read_text(encoding="utf-8") == package.html


def test_webfontbuilder_builds_standalone_family_matrix_preview(roboto: TtfFont):
    bundles = [
        bundle
        for _resolved, bundle in roboto.smart_instancer.build_axis_grid_web_bundles(
            "wght",
            [400.0, 700.0],
            secondary_axis_tag="wdth",
            secondary_values=[75.0, 100.0],
            include_woff=False,
            preview_text="Standalone Matrix",
        )
    ]

    preview = WebFontBuilder.build_family_matrix_preview(
        bundles,
        preview_text="Standalone Matrix",
    )

    assert preview.filename == "family-matrix.png"
    assert preview.media_type == "image/png"
    assert preview.data.startswith(b"\x89PNG\r\n\x1a\n")
    width, height, _pixels = _decode_png_rgb(preview.data)
    assert width > height


def test_webfontbuilder_builds_family_review_board(roboto: TtfFont):
    bundles = [
        bundle
        for _resolved, bundle in roboto.smart_instancer.build_web_bundles(
            ["Bold", "Condensed Bold"],
            include_woff=False,
            preview_text="Review Board",
        )
    ]

    preview = WebFontBuilder.build_family_review_board(
        bundles,
        family_name="Roboto Review",
        preview_text="Review Board",
    )

    assert preview.filename == "family-review-board.png"
    assert preview.media_type == "image/png"
    assert preview.data.startswith(b"\x89PNG\r\n\x1a\n")


def test_family_package_manifest_includes_bundle_naming_strategy(roboto: TtfFont):
    package = roboto.smart_instancer.build_web_family_package(
        ["Bold"],
        include_woff=False,
        naming_strategy="preserve-family",
    )

    assert package.family_name == "Roboto"
    assert package.manifest["bundles"][0]["requested_naming_strategy"] == "preserve-family"
    assert package.bundles[0].manifest["requested_naming_strategy"] == "preserve-family"


def test_family_package_manifest_includes_bundle_name_overrides(roboto: TtfFont):
    package = roboto.smart_instancer.build_web_family_package(
        ["Condensed Bold"],
        include_woff=False,
        naming_strategy="ribbi-safe",
        legacy_family_name="Acme Sans Menu",
        typographic_family_name="Acme Sans Pro",
        legacy_style_name="Bold",
        typographic_style_name="Condensed Bold",
    )

    bundle_manifest = package.manifest["bundles"][0]
    assert package.family_name == "Acme Sans Menu"
    assert bundle_manifest["requested_legacy_family_name"] == "Acme Sans Menu"
    assert bundle_manifest["requested_typographic_family_name"] == "Acme Sans Pro"
    assert bundle_manifest["requested_legacy_style_name"] == "Bold"
    assert bundle_manifest["requested_typographic_style_name"] == "Condensed Bold"


def test_family_package_accepts_lab_template(roboto: TtfFont):
    package = roboto.smart_instancer.build_web_family_package(
        ["Bold", "Condensed Bold"],
        include_woff=False,
        preview_text="Family Preview",
        specimen_template="lab",
    )

    assert 'body class="specimen-template-lab"' in package.html
    assert "<strong>Template:</strong> Lab" in package.html
    assert "body.specimen-template-lab" in package.css
    assert "font-family: 'Courier New', monospace;" in package.css


def test_family_package_write_to_outputs_image_assets(roboto: TtfFont, tmp_path: Path):
    package = roboto.smart_instancer.build_web_family_package(
        ["Bold", "Condensed Bold"],
        include_woff=False,
        preview_text="Family Preview",
    )

    written = package.write_to(tmp_path)
    names = {path.name for path in written}
    assert "family.css" in names
    assert "family.html" in names
    assert "family-manifest.json" in names
    assert "family-waterfall.png" in names
    assert "family-matrix.png" in names
    assert (tmp_path / "family-waterfall.png").read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    assert (tmp_path / "family-matrix.png").read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    manifest = json.loads((tmp_path / "family-manifest.json").read_text(encoding="utf-8"))
    assert manifest["kind"] == "web_family_package"
    assert manifest["bundle_count"] == 2
    assert manifest["bundles"][0]["manifest_filename"] == "web-manifest.json"
    assert manifest["bundles"][0]["export_mode"] == "static-instance"
