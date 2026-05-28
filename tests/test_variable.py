"""Tests for variable font FVAR inspection (SPEC-017 / ADR-014 / FONT-18)."""
from __future__ import annotations

from dataclasses import fields
from pathlib import Path

import pytest

from aspose_font import (
    FamilyReviewExportPackage,
    FontLoader,
    FontPreviewBuilder,
    PreviewImage,
    TtfFont,
    VariableAxis,
    VariableInstance,
    WebFontBuilder,
    WebFontBundle,
)
from aspose_font._exceptions import FontNotSupportedException
from aspose_font._io import BinaryReader
from aspose_font.preview import _decode_png_rgb
from aspose_font.ttf.instancer import TtfInstancer, _SimpleGlyph
from aspose_font.ttf.tables.fvar import FvarTable
from aspose_font.ttf.tables.gvar import TupleVariation
from aspose_font.ttf.tables.name import NameRecord, NameTable
from aspose_font.ttf.tables.stat import build_static_stat_table, extract_stat_name_ids
from aspose_font.variation import build_language_profiles

_KNOWN_AXIS_TAGS = {"wght", "wdth", "ital", "slnt"}


def _synthetic_stat_table() -> bytes:
    def u16(value: int) -> bytes:
        return value.to_bytes(2, "big")

    def u32(value: int) -> bytes:
        return value.to_bytes(4, "big")

    axis_records = (
        b"wght" + u16(60001) + u16(0)
        + b"wdth" + u16(60002) + u16(1)
    )
    axis_value_offsets = u16(4) + u16(16)
    axis_value_records = (
        u16(1) + u16(0) + u16(0) + u16(2) + u32(400 << 16)
        + u16(1) + u16(1) + u16(0) + u16(60003) + u32(75 << 16)
    )
    return (
        u16(1)
        + u16(1)
        + u16(8)
        + u16(2)
        + u32(20)
        + u16(2)
        + u32(36)
        + u16(60004)
        + axis_records
        + axis_value_offsets
        + axis_value_records
    )


def _path_signature(path) -> list[tuple[str, tuple[tuple[str, object], ...]]]:
    return [
        (
            type(cmd).__name__,
            tuple((field.name, getattr(cmd, field.name)) for field in fields(cmd)),
        )
        for cmd in path
    ]


def test_roboto_is_variable(roboto: TtfFont) -> None:
    assert roboto.is_variable is True


def test_roboto_axes_nonempty(roboto: TtfFont) -> None:
    assert len(roboto.axes) > 0


def test_roboto_axes_tags(roboto: TtfFont) -> None:
    tags = {ax.tag for ax in roboto.axes}
    assert len(tags & _KNOWN_AXIS_TAGS) > 0


def test_roboto_axis_range_valid(roboto: TtfFont) -> None:
    for ax in roboto.axes:
        assert ax.min_value <= ax.default_value <= ax.max_value


def test_roboto_named_instances(roboto: TtfFont) -> None:
    assert len(roboto.named_instances) > 0


def test_roboto_instance_coords(roboto: TtfFont) -> None:
    axis_tags = {ax.tag for ax in roboto.axes}
    inst = roboto.named_instances[0]
    assert set(inst.coordinates.keys()) == axis_tags


def test_roboto_variable_axes_have_labels(roboto: TtfFont) -> None:
    axes = roboto.variable_axes
    assert len(axes) == len(roboto.axes)
    assert axes[0].label != ""
    assert axes[0].name("en") is not None


def test_variable_axis_name_prefers_exact_then_base_language() -> None:
    axis = VariableAxis(
        tag="opsz",
        min_value=8.0,
        default_value=12.0,
        max_value=72.0,
        flags=0,
        name_id=256,
        names_by_language={
            "en": "Optical Size",
            "fr": "Corps optique",
            "pt-br": "Tamanho optico",
        },
    )

    assert axis.name("pt_BR") == "Tamanho optico"
    assert axis.name(("es-mx", "fr-ca")) == "Corps optique"
    assert axis.available_languages == ("en", "fr", "pt-br")


def test_variable_axis_reports_localization_resolution_reasons() -> None:
    axis = VariableAxis(
        tag="opsz",
        min_value=8.0,
        default_value=12.0,
        max_value=72.0,
        flags=0,
        name_id=256,
        names_by_language={
            "en": "Optical Size",
            "fr": "Corps optique",
            "pt-br": "Tamanho optico",
        },
    )

    exact = axis.localization_resolution("pt_BR")
    assert exact.selected_language == "pt-br"
    assert exact.selected_label == "Tamanho optico"
    assert exact.fallback_reason == "exact"
    assert exact.is_exact_match is True

    base = axis.localization_resolution("fr-CA")
    assert base.selected_language == "fr"
    assert base.fallback_reason == "base-language"
    assert base.to_dict()["preference_chain"] == ["fr-ca", "fr", "en"]

    english = axis.localization_resolution("es-MX")
    assert english.selected_language == "en"
    assert english.selected_label == "Optical Size"
    assert english.fallback_reason == "base-language"


def test_variable_axis_reports_localization_coverage_statuses() -> None:
    axis = VariableAxis(
        tag="opsz",
        min_value=8.0,
        default_value=12.0,
        max_value=72.0,
        flags=0,
        name_id=256,
        names_by_language={
            "en": "Optical Size",
            "fr": "Corps optique",
            "pt-br": "Tamanho optico",
        },
    )

    complete = axis.localization_coverage(("pt-PT", "fr-CA"))
    assert complete.status == "complete"
    assert complete.matched_languages == ("pt-br", "fr")
    assert complete.missing_languages == ()

    partial = axis.localization_coverage(("pt-PT", "ja-JP"))
    assert partial.status == "partial"
    assert partial.matched_languages == ("pt-br",)
    assert partial.missing_languages == ("ja-jp",)

    english_only = VariableAxis(
        tag="wght",
        min_value=100.0,
        default_value=400.0,
        max_value=900.0,
        flags=0,
        name_id=257,
        names_by_language={"en": "Weight"},
    ).localization_coverage(("fr-FR", "ja-JP"))
    assert english_only.status == "english-only"
    assert english_only.available_languages == ("en",)

    missing = VariableAxis(
        tag="TEST",
        min_value=0.0,
        default_value=0.0,
        max_value=1.0,
        flags=0,
        name_id=258,
        names_by_language={},
    ).localization_coverage("en")
    assert missing.status == "missing"
    assert missing.missing_languages == ("en",)


def test_variable_axis_exposes_summary_metadata() -> None:
    axis = VariableAxis(
        tag="wght",
        min_value=100.0,
        default_value=400.0,
        max_value=900.0,
        flags=0,
        name_id=256,
        names_by_language={"en": "Weight"},
    )

    assert axis.span == 800.0
    assert axis.default_ratio == 0.375
    assert axis.default_preset is not None
    assert axis.default_preset.name == "Regular"
    assert axis.describe_value(700.0) == "Bold (700)"
    assert axis.range_summary == "100 -> 900 (default: Regular (400))"


def test_variable_axis_exports_presentation_snapshot() -> None:
    axis = VariableAxis(
        tag="wght",
        min_value=100.0,
        default_value=400.0,
        max_value=900.0,
        flags=0,
        name_id=256,
        names_by_language={"en": "Weight", "fr": "Poids"},
    )

    snapshot = axis.to_presentation(language=("fr-CA", "en"), suggested_values=[100.0, 400.0, 700.0])

    assert snapshot["tag"] == "wght"
    assert snapshot["label"] == "Poids"
    assert snapshot["formatted_default"] == "400"
    assert snapshot["css_axis_tag"] == "'wght'"
    assert snapshot["css_default_setting"] == "'wght' 400"
    assert snapshot["ui_control"] == {
        "type": "slider",
        "label": "Poids",
        "min": 100.0,
        "max": 900.0,
        "default": 400.0,
        "step": 50.0,
        "unit": "",
        "formatted_min": "100",
        "formatted_max": "900",
        "formatted_default": "400",
    }
    assert snapshot["default_description"] == "Regular (400)"
    assert snapshot["range_summary"] == "100 -> 900 (default: Regular (400))"
    assert snapshot["default_ratio"] == 0.375
    assert snapshot["normalized_default"] == 0.0
    assert snapshot["presentation_kind"] == "weight"
    assert snapshot["display_group"] == "style"
    assert snapshot["display_order"] == 10
    assert snapshot["is_registered_axis"] is True
    assert snapshot["localized_labels"] == [
        {"language": "fr", "label": "Poids"},
        {"language": "en", "label": "Weight"},
    ]
    assert snapshot["localization"] == {
        "requested_languages": ["fr-ca", "en"],
        "preference_chain": ["fr-ca", "fr", "en"],
        "selected_language": "fr",
        "selected_label": "Poids",
        "fallback_reason": "base-language",
        "is_exact_match": False,
    }
    assert snapshot["localization_coverage"] == {
        "status": "complete",
        "requested_languages": ["fr-ca", "en"],
        "available_languages": ["en", "fr"],
        "matched_languages": ["fr", "en"],
        "missing_languages": [],
        "requested_count": 2,
        "available_count": 2,
        "matched_count": 2,
        "missing_count": 0,
    }
    assert snapshot["requested_language_hints"] == [
        {
            "requested_language": "fr-ca",
            "status": "base-language",
            "matched_language": "fr",
            "label": "Poids",
            "has_requested_language_label": True,
        },
        {
            "requested_language": "en",
            "status": "exact",
            "matched_language": "en",
            "label": "Weight",
            "has_requested_language_label": True,
        },
    ]
    presets = snapshot["presets"]
    assert isinstance(presets, list)
    assert {"name": "Bold", "value": 700.0, "formatted_value": "700", "description": "Standard bold emphasis."} in presets
    suggested_values = snapshot["suggested_values"]
    assert isinstance(suggested_values, list)
    assert suggested_values[-1] == {
        "value": 700.0,
        "formatted_value": "700",
        "description": "Bold (700)",
        "normalized_value": 0.6,
    }


def test_variable_axis_exposes_ordered_localized_labels() -> None:
    axis = VariableAxis(
        tag="opsz",
        min_value=8.0,
        default_value=12.0,
        max_value=72.0,
        flags=0,
        name_id=256,
        names_by_language={
            "en": "Optical Size",
            "fr": "Corps optique",
            "pt-br": "Tamanho optico",
        },
    )

    assert axis.localized_labels(("pt_PT", "fr-CA")) == (
        ("pt-br", "Tamanho optico"),
        ("fr", "Corps optique"),
        ("en", "Optical Size"),
    )
    assert axis.available_languages == ("en", "fr", "pt-br")


def test_variable_axis_reports_custom_display_metadata() -> None:
    axis = VariableAxis(
        tag="XPRV",
        min_value=0.0,
        default_value=0.0,
        max_value=1.0,
        flags=0,
        name_id=259,
        names_by_language={"en": "Private Axis"},
    )

    assert axis.presentation_kind == "scalar"
    assert axis.display_group == "custom"
    assert axis.display_order == 1000
    assert axis.is_registered_axis is False
    assert axis.css_axis_tag == "'XPRV'"
    assert axis.css_variation_setting(0.25) == "'XPRV' 0.25"
    assert axis.ui_control()["step"] == 1.0
    snapshot = axis.to_presentation()
    assert snapshot["presentation_kind"] == "scalar"
    assert snapshot["display_group"] == "custom"
    assert snapshot["display_order"] == 1000
    assert snapshot["is_registered_axis"] is False
    assert snapshot["css_axis_tag"] == "'XPRV'"
    assert snapshot["css_default_setting"] == "'XPRV' 0"
    assert snapshot["ui_control"]["label"] == "Private Axis"


def test_variable_axis_requested_language_hints_report_fallbacks() -> None:
    axis = VariableAxis(
        tag="opsz",
        min_value=8.0,
        default_value=12.0,
        max_value=72.0,
        flags=0,
        name_id=256,
        names_by_language={
            "en": "Optical Size",
            "fr": "Corps optique",
            "pt-br": "Tamanho optico",
        },
    )

    hints = axis.requested_language_hints(("pt-PT", "fr-CA", "ja-JP"))

    assert [hint.to_dict() for hint in hints] == [
        {
            "requested_language": "pt-pt",
            "status": "locale-variant",
            "matched_language": "pt-br",
            "label": "Tamanho optico",
            "has_requested_language_label": True,
        },
        {
            "requested_language": "fr-ca",
            "status": "base-language",
            "matched_language": "fr",
            "label": "Corps optique",
            "has_requested_language_label": True,
        },
        {
            "requested_language": "ja-jp",
            "status": "english-fallback",
            "matched_language": "en",
            "label": "Optical Size",
            "has_requested_language_label": False,
        },
    ]


def test_language_profiles_cover_complete_partial_english_and_missing_states() -> None:
    complete = build_language_profiles({"en": "Weight", "fr": "Poids"}, ("fr-FR", "en"))
    assert [profile.to_dict() for profile in complete] == [
        {
            "requested_language": "fr-fr",
            "display_label": "Poids",
            "resolved_language": "fr",
            "fallback_reason": "base-language",
            "has_requested_language_label": True,
        },
        {
            "requested_language": "en",
            "display_label": "Weight",
            "resolved_language": "en",
            "fallback_reason": "exact",
            "has_requested_language_label": True,
        },
    ]

    partial = build_language_profiles({"en": "Weight", "fr": "Poids"}, ("fr-FR", "ja-JP"))
    assert [profile.fallback_reason for profile in partial] == ["base-language", "english-fallback"]
    assert [profile.display_label for profile in partial] == ["Poids", "Weight"]

    english_only = build_language_profiles({"en": "Weight"}, ("fr-FR",))
    assert english_only[0].to_dict() == {
        "requested_language": "fr-fr",
        "display_label": "Weight",
        "resolved_language": "en",
        "fallback_reason": "english-fallback",
        "has_requested_language_label": False,
    }

    missing = build_language_profiles({}, ("ja-JP",))
    assert missing[0].to_dict() == {
        "requested_language": "ja-jp",
        "display_label": None,
        "resolved_language": None,
        "fallback_reason": "missing",
        "has_requested_language_label": False,
    }


def test_variable_instance_name_prefers_requested_language_chain() -> None:
    instance = VariableInstance(
        coordinates={"wght": 700.0},
        name_id=300,
        postscript_name_id=None,
        names_by_language={
            "en": "Bold",
            "de": "Fett",
            "zh-hans": "Cuhui",
        },
        postscript_name="Demo-Bold",
    )

    assert instance.name(("zh_CN", "de")) == "Cuhui"
    assert instance.name("de-DE") == "Fett"
    assert instance.available_languages == ("de", "en", "zh-hans")


def test_variable_instance_reports_first_available_localization_fallback() -> None:
    instance = VariableInstance(
        coordinates={"wght": 700.0},
        name_id=300,
        postscript_name_id=None,
        names_by_language={"de": "Fett", "pt-br": "Negrito"},
        postscript_name="Demo-Bold",
    )

    resolved = instance.localization_resolution("ja-JP")

    assert resolved.requested_languages == ("ja-jp",)
    assert resolved.selected_language == "de"
    assert resolved.selected_label == "Fett"
    assert resolved.fallback_reason == "first-available"


def test_variable_instance_exposes_ordered_localized_labels() -> None:
    instance = VariableInstance(
        coordinates={"wght": 700.0},
        name_id=300,
        postscript_name_id=None,
        names_by_language={
            "en": "Bold",
            "de": "Fett",
            "pt-br": "Negrito",
        },
        postscript_name="Demo-Bold",
    )

    assert instance.localized_labels(("pt-PT", "de-DE")) == (
        ("pt-br", "Negrito"),
        ("de", "Fett"),
        ("en", "Bold"),
    )
    assert instance.available_languages == ("de", "en", "pt-br")


def test_variable_instance_formats_coordinates_with_axis_labels() -> None:
    weight = VariableAxis(
        tag="wght",
        min_value=100.0,
        default_value=400.0,
        max_value=900.0,
        flags=0,
        name_id=256,
        names_by_language={"en": "Weight"},
    )
    width = VariableAxis(
        tag="wdth",
        min_value=75.0,
        default_value=100.0,
        max_value=100.0,
        flags=0,
        name_id=257,
        names_by_language={"en": "Width"},
    )
    instance = VariableInstance(
        coordinates={"wdth": 75.0, "wght": 700.0},
        name_id=300,
        postscript_name_id=None,
        names_by_language={"en": "Condensed Bold"},
        postscript_name="Demo-CondensedBold",
    )

    assert instance.format_coordinates((weight, width)) == (
        "Width=Condensed (75%)",
        "Weight=Bold (700)",
    )
    assert instance.format_coordinates((weight, width), include_tags=True) == (
        "Width [wdth]=Condensed (75%)",
        "Weight [wght]=Bold (700)",
    )
    assert instance.css_variation_settings((weight, width)) == ("'wdth' 75%", "'wght' 700")


def test_variable_instance_exports_presentation_snapshot() -> None:
    weight = VariableAxis(
        tag="wght",
        min_value=100.0,
        default_value=400.0,
        max_value=900.0,
        flags=0,
        name_id=256,
        names_by_language={"en": "Weight"},
    )
    instance = VariableInstance(
        coordinates={"wght": 700.0},
        name_id=300,
        postscript_name_id=301,
        names_by_language={"en": "Bold", "fr": "Gras"},
        postscript_name="Demo-Bold",
    )

    snapshot = instance.to_presentation((weight,), language=("fr-CA", "en"))

    assert snapshot == {
        "name_id": 300,
        "postscript_name_id": 301,
        "label": "Gras",
        "postscript_name": "Demo-Bold",
        "localization": {
            "requested_languages": ["fr-ca", "en"],
            "preference_chain": ["fr-ca", "fr", "en"],
            "selected_language": "fr",
            "selected_label": "Gras",
            "fallback_reason": "base-language",
            "is_exact_match": False,
        },
        "localization_coverage": {
            "status": "complete",
            "requested_languages": ["fr-ca", "en"],
            "available_languages": ["en", "fr"],
            "matched_languages": ["fr", "en"],
            "missing_languages": [],
            "requested_count": 2,
            "available_count": 2,
            "matched_count": 2,
            "missing_count": 0,
        },
        "available_languages": ["en", "fr"],
        "localized_labels": [
            {"language": "fr", "label": "Gras"},
            {"language": "en", "label": "Bold"},
        ],
        "requested_language_hints": [
            {
                "requested_language": "fr-ca",
                "status": "base-language",
                "matched_language": "fr",
                "label": "Gras",
                "has_requested_language_label": True,
            },
            {
                "requested_language": "en",
                "status": "exact",
                "matched_language": "en",
                "label": "Bold",
                "has_requested_language_label": True,
            },
        ],
        "language_profiles": [
            {
                "requested_language": "fr-ca",
                "display_label": "Gras",
                "resolved_language": "fr",
                "fallback_reason": "base-language",
                "has_requested_language_label": True,
            },
            {
                "requested_language": "en",
                "display_label": "Bold",
                "resolved_language": "en",
                "fallback_reason": "exact",
                "has_requested_language_label": True,
            },
        ],
        "coordinates": {"wght": 700.0},
        "formatted_coordinates": ["Weight=Bold (700)"],
        "css_variation_settings": "'wght' 700",
        "css_variation_setting_entries": ["'wght' 700"],
        "tagged_coordinates": ["Weight [wght]=Bold (700)"],
    }


def test_variable_instance_requested_language_hints_report_missing_labels() -> None:
    instance = VariableInstance(
        coordinates={"wght": 700.0},
        name_id=300,
        postscript_name_id=None,
        names_by_language={"de": "Fett"},
        postscript_name="Demo-Bold",
    )

    hints = instance.requested_language_hints(("ja-JP", "de-DE"))

    assert [hint.to_dict() for hint in hints] == [
        {
            "requested_language": "ja-jp",
            "status": "first-available",
            "matched_language": "de",
            "label": "Fett",
            "has_requested_language_label": False,
        },
        {
            "requested_language": "de-de",
            "status": "base-language",
            "matched_language": "de",
            "label": "Fett",
            "has_requested_language_label": True,
        },
    ]


def test_name_table_best_name_uses_locale_fallback_chain() -> None:
    table = NameTable(
        records=[
            NameRecord(3, 1, 0x0416, 256, "Tamanho optico"),
            NameRecord(3, 1, 0x040C, 256, "Corps optique"),
            NameRecord(3, 1, 0x0409, 256, "Optical Size"),
        ],
        _raw=b"",
    )

    assert NameTable.language_key(3, 0x0416) == "pt-br"
    assert NameTable.language_key(3, 0x0809) == "en-gb"
    assert NameTable.language_key(1, 8) == "pt"
    assert table.best_name(256, ("pt_PT", "fr-CA")) == "Tamanho optico"


def test_roboto_get_axis_by_tag(roboto: TtfFont) -> None:
    axis = roboto.get_axis("wght")
    assert axis is not None
    assert axis.tag == "wght"
    assert axis.label == "Weight"
    assert axis.normalize(axis.default_value) == 0.0


def test_roboto_axis_includes_standard_metadata_and_presets(roboto: TtfFont) -> None:
    axis = roboto.get_axis("wght")
    assert axis is not None
    assert axis.description is not None
    assert axis.presentation_kind == "weight"
    assert axis.display_group == "style"
    assert axis.display_order == 10
    assert axis.is_registered_axis is True
    assert axis.recommended_step == 50.0
    preset_names = [preset.name for preset in axis.presets]
    assert "Regular" in preset_names
    assert "Bold" in preset_names
    bold = axis.get_preset("Bold")
    assert bold is not None
    assert bold.value == 700.0


def test_roboto_width_axis_presets_are_filtered_to_supported_range(roboto: TtfFont) -> None:
    axis = roboto.get_axis("wdth")
    assert axis is not None
    assert axis.unit_label == "%"
    assert axis.presentation_kind == "width"
    preset_names = [preset.name for preset in axis.presets]
    assert "Condensed" in preset_names
    assert "Normal" in preset_names
    assert "Expanded" not in preset_names
    assert axis.format_value(100.0) == "100%"


def test_roboto_exports_variable_presentation_snapshot(roboto: TtfFont) -> None:
    snapshot = roboto.variable_presentation(preferred_languages=("en",))

    assert snapshot["font_family"] == "Roboto"
    assert snapshot["is_variable"] is True
    assert snapshot["axis_groups"] == [
        {
            "group": "style",
            "label": "Style",
            "display_order": 10,
            "axis_tags": ["wght"],
            "axis_count": 1,
            "language_profiles": [
                {
                    "requested_language": "en",
                    "display_label": "Style",
                    "resolved_language": None,
                    "fallback_reason": "metadata-default",
                    "has_requested_language_label": False,
                }
            ],
        },
        {
            "group": "layout",
            "label": "Layout",
            "display_order": 20,
            "axis_tags": ["wdth"],
            "axis_count": 1,
            "language_profiles": [
                {
                    "requested_language": "en",
                    "display_label": "Layout",
                    "resolved_language": None,
                    "fallback_reason": "metadata-default",
                    "has_requested_language_label": False,
                }
            ],
        },
    ]
    assert snapshot["language_profiles"][0]["requested_language"] == "en"
    assert snapshot["language_profiles"][0]["axis_groups"]["style"]["display_label"] == "Style"
    assert snapshot["language_profiles"][0]["axes"]["wght"]["display_label"] == "Weight"
    axes = snapshot["axes"]
    assert isinstance(axes, list)
    weight = next(axis for axis in axes if axis["tag"] == "wght")
    assert weight["label"] == "Weight"
    assert weight["language_profiles"] == [
        {
            "requested_language": "en",
            "display_label": "Weight",
            "resolved_language": "en",
            "fallback_reason": "exact",
            "has_requested_language_label": True,
        }
    ]
    assert weight["css_axis_tag"] == "'wght'"
    assert weight["css_default_setting"] == "'wght' 400"
    assert weight["ui_control"]["type"] == "slider"
    assert weight["ui_control"]["step"] == 50.0
    assert weight["suggested_values"]
    instances = snapshot["named_instances"]
    assert isinstance(instances, list)
    assert any(
        "Weight [wght]=Bold (700)" in instance["tagged_coordinates"]
        for instance in instances
    )
    bold_instance = next(instance for instance in instances if instance["label"] == "Bold")
    assert bold_instance["css_variation_settings"] == "'wdth' 100%, 'wght' 700"
    assert bold_instance["css_variation_setting_entries"] == ["'wdth' 100%", "'wght' 700"]


def test_variable_presentation_groups_custom_axes() -> None:
    class DummyFont:
        font_name = "Demo"
        font_family = "Demo"
        font_style = "Regular"
        is_variable = True
        variable_axes = [
            VariableAxis(
                tag="XPRV",
                min_value=0.0,
                default_value=0.0,
                max_value=1.0,
                flags=0,
                name_id=260,
                names_by_language={"en": "Private Axis"},
            ),
            VariableAxis(
                tag="wght",
                min_value=100.0,
                default_value=400.0,
                max_value=900.0,
                flags=0,
                name_id=256,
                names_by_language={"en": "Weight"},
            ),
        ]
        variable_instances = []

    snapshot = TtfFont.variable_presentation(DummyFont(), include_suggested_values=False)

    assert snapshot["axis_groups"] == [
        {
            "group": "style",
            "label": "Style",
            "display_order": 10,
            "axis_tags": ["wght"],
            "axis_count": 1,
            "language_profiles": [
                {
                    "requested_language": "en",
                    "display_label": "Style",
                    "resolved_language": None,
                    "fallback_reason": "metadata-default",
                    "has_requested_language_label": False,
                }
            ],
        },
        {
            "group": "custom",
            "label": "Custom",
            "display_order": 1000,
            "axis_tags": ["XPRV"],
            "axis_count": 1,
            "language_profiles": [
                {
                    "requested_language": "en",
                    "display_label": "Custom",
                    "resolved_language": None,
                    "fallback_reason": "metadata-default",
                    "has_requested_language_label": False,
                }
            ],
        },
    ]


def test_roboto_variable_instances_have_labels(roboto: TtfFont) -> None:
    instances = roboto.variable_instances
    assert len(instances) == len(roboto.named_instances)
    assert instances[0].label != ""
    assert instances[0].postscript_name is not None


def test_roboto_get_named_instance(roboto: TtfFont) -> None:
    instance = roboto.get_named_instance("Bold")
    assert instance is not None
    assert instance.coordinates["wght"] == 700.0
    assert instance.postscript_name == "Roboto-Bold"


def test_cff_not_variable(opensans_cff) -> None:
    # CFF fonts are non-variable for this API surface.
    assert not hasattr(opensans_cff, "is_variable") or opensans_cff.is_variable is False
    assert not hasattr(opensans_cff, "axes") or opensans_cff.axes == []


def test_ttf_without_fvar_is_not_variable(roboto: TtfFont) -> None:
    tables = roboto.ttf_tables
    original_raw = tables._raw.pop("fvar", None)
    original_parsed = tables.fvar
    tables.fvar = None
    try:
        assert roboto.is_variable is False
        assert roboto.axes == []
        assert roboto.named_instances == []
    finally:
        if original_raw is not None:
            tables._raw["fvar"] = original_raw
        tables.fvar = original_parsed


def test_fvar_roundtrip(roboto: TtfFont) -> None:
    raw = roboto._tables._raw.get("fvar")
    assert raw is not None, "Roboto must have raw fvar bytes"
    table = FvarTable.from_reader(BinaryReader(raw), len(raw))
    assert table.to_bytes() == raw


def test_instantiate_returns_static_ttf(roboto: TtfFont) -> None:
    static = roboto.instantiate({"wght": 700.0})
    assert isinstance(static, TtfFont)
    assert static.is_variable is False
    assert static.axes == []
    assert static.named_instances == []
    assert "fvar" not in static.ttf_tables._raw
    assert "gvar" not in static.ttf_tables._raw
    assert "avar" not in static.ttf_tables._raw
    assert static.font_family == "Roboto Instance"
    assert static.font_style == "Bold"
    assert static.font_name == "Roboto Instance Bold"


def test_instantiate_changes_representative_outline(roboto: TtfFont) -> None:
    default_glyph = roboto.instantiate({}).glyph_accessor.get_glyph_by_unicode(ord("A"))
    bold_glyph = roboto.instantiate({"wght": 700.0}).glyph_accessor.get_glyph_by_unicode(ord("A"))
    assert default_glyph.path is not None
    assert bold_glyph.path is not None
    default_points = _path_signature(default_glyph.path)
    bold_points = _path_signature(bold_glyph.path)
    assert default_points != bold_points


def test_interpolate_untouched_points_fills_sparse_simple_tuple_run() -> None:
    values = TtfInstancer._interpolate_untouched_points(
        [3],
        [0, 10, 20, 30],
        [0.0, None, None, 30.0],
    )
    assert values == [0.0, 10.0, 20.0, 30.0]


def test_expand_simple_deltas_keeps_phantom_points_separate() -> None:
    simple = _SimpleGlyph(
        contour_ends=[3],
        xs=[0, 10, 20, 30],
        ys=[0, 0, 0, 0],
        on_curve=[True, True, True, True],
        instructions=b"",
    )
    variation = TupleVariation(
        peak_coords={"wght": 1.0},
        start_coords=None,
        end_coords=None,
        points=[0, 3, 4, 5],
        deltas=[(0, 0), (30, 0), (12, 0), (24, 0)],
    )

    outline_dx, outline_dy, phantom_dx, phantom_dy = TtfInstancer._expand_simple_deltas(
        simple,
        variation,
    )
    assert outline_dx == [0.0, 10.0, 20.0, 30.0]
    assert outline_dy == [0.0, 0.0, 0.0, 0.0]
    assert phantom_dx == [12.0, 24.0, 0.0, 0.0]
    assert phantom_dy == [0.0, 0.0, 0.0, 0.0]


def test_instantiate_applies_hvar_advance_widths(roboto: TtfFont) -> None:
    hvar_aware = roboto.instantiate({"wdth": 75.0})
    tables = roboto.ttf_tables
    original_raw = tables._raw.pop("HVAR", None)
    original_parsed = tables.hvar
    tables.hvar = None
    try:
        without_hvar = roboto.instantiate({"wdth": 75.0})
    finally:
        if original_raw is not None:
            tables._raw["HVAR"] = original_raw
        tables.hvar = original_parsed

    differing_gid = next(
        (
            gid
            for gid, (aware_metric, fallback_metric) in enumerate(
                zip(hvar_aware.ttf_tables.hmtx.metrics, without_hvar.ttf_tables.hmtx.metrics)
            )
            if aware_metric.advance_width != fallback_metric.advance_width
        ),
        None,
    )
    assert differing_gid is not None
    assert (
        hvar_aware.ttf_tables.hmtx.get_metric(differing_gid).advance_width
        != without_hvar.ttf_tables.hmtx.get_metric(differing_gid).advance_width
    )


def test_instantiate_without_hvar_remains_supported(roboto: TtfFont) -> None:
    tables = roboto.ttf_tables
    original_raw = tables._raw.pop("HVAR", None)
    original_parsed = tables.hvar
    tables.hvar = None
    try:
        instantiated = roboto.instantiate({"wdth": 75.0})
    finally:
        if original_raw is not None:
            tables._raw["HVAR"] = original_raw
        tables.hvar = original_parsed

    assert isinstance(instantiated, TtfFont)
    assert instantiated.is_variable is False
    assert instantiated.glyph_accessor.get_glyph_by_unicode(ord("A")).path is not None


def test_instantiate_clamps_out_of_range_coordinates(roboto: TtfFont) -> None:
    clamped = roboto.instantiate({"wght": 9999.0})
    at_max = roboto.instantiate({"wght": max(axis.max_value for axis in roboto.axes if axis.tag == "wght")})
    clamped_glyph = clamped.glyph_accessor.get_glyph_by_unicode(ord("A"))
    max_glyph = at_max.glyph_accessor.get_glyph_by_unicode(ord("A"))
    assert clamped_glyph.path is not None
    assert max_glyph.path is not None
    assert _path_signature(clamped_glyph.path) == _path_signature(max_glyph.path)


def test_instantiate_serialized_output_reloads(roboto: TtfFont, tmp_path: Path) -> None:
    instantiated = roboto.instantiate({"wght": 700.0, "wdth": 75.0})
    out = tmp_path / "instance.ttf"
    out.write_bytes(instantiated.to_bytes())
    reloaded = TtfFont._from_reader(BinaryReader(out.read_bytes()))
    assert reloaded.is_variable is False
    assert reloaded.font_family == "Roboto Instance"
    assert reloaded.glyph_accessor.get_glyph_by_unicode(ord("A")).path is not None


def test_instantiate_composite_glyph_updates_raw_bounds_to_match_instantiated_children(roboto: TtfFont) -> None:
    instantiated = roboto.instantiate({"wght": 700.0, "wdth": 75.0})
    gid = int(instantiated.encoding.unicode_to_gid(ord("Á")))
    offset = instantiated.ttf_tables.loca.glyph_offset(gid)
    length = instantiated.ttf_tables.loca.glyph_length(gid)
    raw = instantiated.ttf_tables.glyf.get_glyph_bytes(offset, length)
    raw_bounds = (
        int.from_bytes(raw[2:4], "big", signed=True),
        int.from_bytes(raw[4:6], "big", signed=True),
        int.from_bytes(raw[6:8], "big", signed=True),
        int.from_bytes(raw[8:10], "big", signed=True),
    )
    glyph = instantiated.glyph_accessor.get_glyph_by_unicode(ord("Á"))
    assert glyph.path is not None

    xs: list[float] = []
    ys: list[float] = []
    for command in glyph.path:
        for field in fields(command):
            if field.name.startswith("x"):
                xs.append(float(getattr(command, field.name)))
            elif field.name.startswith("y"):
                ys.append(float(getattr(command, field.name)))
    assert xs and ys
    path_bounds = (
        int(min(xs)),
        int(min(ys)),
        int(max(xs)),
        int(max(ys)),
    )
    assert raw_bounds == path_bounds


def test_instantiate_composite_glyph_applies_root_component_translation_deltas(roboto: TtfFont) -> None:
    source_gid = int(roboto.encoding.unicode_to_gid(ord("Á")))
    source_offset = roboto.ttf_tables.loca.glyph_offset(source_gid)
    source_length = roboto.ttf_tables.loca.glyph_length(source_gid)
    source_raw = roboto.ttf_tables.glyf.get_glyph_bytes(source_offset, source_length)
    source_components = TtfInstancer._parse_composite_glyph(source_raw).components

    instantiated = roboto.instantiate({"wght": 700.0, "wdth": 75.0})
    instantiated_gid = int(instantiated.encoding.unicode_to_gid(ord("Á")))
    offset = instantiated.ttf_tables.loca.glyph_offset(instantiated_gid)
    length = instantiated.ttf_tables.loca.glyph_length(instantiated_gid)
    raw = instantiated.ttf_tables.glyf.get_glyph_bytes(offset, length)
    instantiated_components = TtfInstancer._parse_composite_glyph(raw).components

    assert len(source_components) == len(instantiated_components) == 2
    assert (source_components[1].arg1, source_components[1].arg2) != (
        instantiated_components[1].arg1,
        instantiated_components[1].arg2,
    )


def test_composite_bounds_reject_non_xy_component_arguments(roboto: TtfFont) -> None:
    gid = int(roboto.encoding.unicode_to_gid(ord("Á")))
    offset = roboto.ttf_tables.loca.glyph_offset(gid)
    length = roboto.ttf_tables.loca.glyph_length(gid)
    raw = roboto.ttf_tables.glyf.get_glyph_bytes(offset, length)
    composite = TtfInstancer._parse_composite_glyph(raw)
    composite.components[0].args_are_xy_values = False

    with pytest.raises(FontNotSupportedException, match="Unsupported composite glyph arguments for instancing"):
        TtfInstancer._composite_bounds(composite, lambda _gid: None)


def test_apply_composite_variations_rejects_out_of_range_root_point_indices(roboto: TtfFont) -> None:
    gid = int(roboto.encoding.unicode_to_gid(ord("Á")))
    offset = roboto.ttf_tables.loca.glyph_offset(gid)
    length = roboto.ttf_tables.loca.glyph_length(gid)
    raw = roboto.ttf_tables.glyf.get_glyph_bytes(offset, length)
    composite = TtfInstancer._parse_composite_glyph(raw)

    class _FakeGvar:
        def glyph_variations(self, _gid: int, _point_count: int):
            return [
                TupleVariation(
                    peak_coords={"wght": 1.0},
                    start_coords=None,
                    end_coords=None,
                    points=[len(composite.components) + 4],
                    deltas=[(10, 0)],
                )
            ]

    with pytest.raises(FontNotSupportedException, match="Unsupported composite gvar variation"):
        TtfInstancer._apply_composite_variations(
            composite,
            _FakeGvar(),
            gid,
            {"wght": 1.0, "wdth": 0.0},
        )


def test_instantiate_custom_coordinates_get_descriptive_name(roboto: TtfFont) -> None:
    instantiated = roboto.instantiate({"wght": 725.0, "wdth": 82.5})
    assert instantiated.font_family == "Roboto Instance"
    assert instantiated.font_style == "Weight 725 Width 82.5"
    assert instantiated.font_name == "Roboto Instance Weight 725 Width 82.5"
    assert instantiated.ttf_tables.name.get(6) == "RobotoInstance-Weight725Width825"


def test_available_naming_strategies_are_exposed(roboto: TtfFont) -> None:
    assert roboto.available_naming_strategies() == (
        "instance-family",
        "preserve-family",
        "qa-tagged",
        "menu-safe",
        "ribbi-safe",
    )


def test_instantiate_preserve_family_strategy_keeps_source_family(roboto: TtfFont) -> None:
    instantiated = roboto.instantiate(
        {"wght": 700.0},
        naming_strategy="preserve-family",
    )
    assert instantiated.font_family == "Roboto"
    assert instantiated.font_style == "Bold"
    assert instantiated.font_name == "Roboto Bold"
    assert instantiated.ttf_tables.name.get(6) == "Roboto-Bold"


def test_instantiate_qa_tagged_strategy_produces_distinct_family(roboto: TtfFont) -> None:
    instantiated = roboto.instantiate(
        {"wght": 700.0},
        naming_strategy="qa-tagged",
    )
    assert instantiated.font_family == "Roboto QA"
    assert instantiated.font_style == "Bold"
    assert instantiated.font_name == "Roboto QA Bold"
    assert instantiated.ttf_tables.name.get(6) == "RobotoQA-Bold"


def test_instantiate_menu_safe_strategy_separates_legacy_and_typographic_family(roboto: TtfFont) -> None:
    instantiated = roboto.instantiate(
        {"wght": 700.0},
        naming_strategy="menu-safe",
    )
    assert instantiated.font_family == "Roboto Instance"
    assert instantiated.font_style == "Bold"
    assert instantiated.font_name == "Roboto Instance Bold"
    assert instantiated.ttf_tables.name.get(1) == "Roboto Instance"
    assert instantiated.ttf_tables.name.get(16) == "Roboto"
    assert instantiated.ttf_tables.name.get(21) == "Roboto"
    assert instantiated.ttf_tables.name.get(25) == "Roboto"
    assert instantiated.ttf_tables.name.get(6) == "RobotoInstance-Bold"


def test_instantiate_ribbi_safe_strategy_uses_legacy_ribbi_subfamily(roboto: TtfFont) -> None:
    instantiated = roboto.instantiate(
        {"wght": 700.0, "wdth": 75.0},
        naming_strategy="ribbi-safe",
    )
    assert instantiated.font_family == "Roboto Instance"
    assert instantiated.font_style == "Bold"
    assert instantiated.font_name == "Roboto Instance Condensed Bold"
    assert instantiated.ttf_tables.name.get(1) == "Roboto Instance"
    assert instantiated.ttf_tables.name.get(2) == "Bold"
    assert instantiated.ttf_tables.name.get(16) == "Roboto"
    assert instantiated.ttf_tables.name.get(17) == "Condensed Bold"
    assert instantiated.ttf_tables.name.get(22) == "Condensed Bold"
    assert instantiated.ttf_tables.name.get(6) == "RobotoInstance-CondensedBold"


def test_instantiate_accepts_custom_family_suffix(roboto: TtfFont) -> None:
    instantiated = roboto.instantiate(
        {"wght": 700.0},
        naming_strategy="instance-family",
        family_suffix="Beta",
    )
    assert instantiated.font_family == "Roboto Beta"
    assert instantiated.font_style == "Bold"
    assert instantiated.font_name == "Roboto Beta Bold"
    assert instantiated.ttf_tables.name.get(6) == "RobotoBeta-Bold"


def test_instantiate_menu_safe_strategy_preserves_typographic_family_with_custom_suffix(
    roboto: TtfFont,
) -> None:
    instantiated = roboto.instantiate(
        {"wght": 700.0, "wdth": 75.0},
        naming_strategy="menu-safe",
        family_suffix="Beta",
    )
    assert instantiated.font_family == "Roboto Beta"
    assert instantiated.font_style == "Condensed Bold"
    assert instantiated.ttf_tables.name.get(1) == "Roboto Beta"
    assert instantiated.ttf_tables.name.get(16) == "Roboto"
    assert instantiated.ttf_tables.name.get(21) == "Roboto"
    assert instantiated.ttf_tables.name.get(25) == "Roboto"


def test_instantiate_accepts_explicit_family_name_overrides(roboto: TtfFont) -> None:
    instantiated = roboto.instantiate(
        {"wght": 700.0, "wdth": 75.0},
        naming_strategy="ribbi-safe",
        legacy_family_name="Acme Sans Menu",
        typographic_family_name="Acme Sans Pro",
    )

    assert instantiated.font_family == "Acme Sans Menu"
    assert instantiated.font_style == "Bold"
    assert instantiated.font_name == "Acme Sans Menu Condensed Bold"
    assert instantiated.ttf_tables.name.get(1) == "Acme Sans Menu"
    assert instantiated.ttf_tables.name.get(2) == "Bold"
    assert instantiated.ttf_tables.name.get(16) == "Acme Sans Pro"
    assert instantiated.ttf_tables.name.get(17) == "Condensed Bold"
    assert instantiated.ttf_tables.name.get(21) == "Acme Sans Pro"
    assert instantiated.ttf_tables.name.get(22) == "Condensed Bold"
    assert instantiated.ttf_tables.name.get(25) == "Acme Sans Pro"
    assert instantiated.ttf_tables.name.get(6) == "AcmeSansMenu-CondensedBold"


def test_instantiate_accepts_explicit_style_name_overrides(roboto: TtfFont) -> None:
    instantiated = roboto.instantiate(
        {"wght": 700.0, "wdth": 75.0},
        naming_strategy="ribbi-safe",
        legacy_family_name="Acme Sans Menu",
        typographic_family_name="Acme Sans Pro",
        legacy_style_name="Bold",
        typographic_style_name="Condensed Display Bold",
    )

    assert instantiated.font_family == "Acme Sans Menu"
    assert instantiated.font_style == "Bold"
    assert instantiated.font_name == "Acme Sans Menu Condensed Display Bold"
    assert instantiated.ttf_tables.name.get(1) == "Acme Sans Menu"
    assert instantiated.ttf_tables.name.get(2) == "Bold"
    assert instantiated.ttf_tables.name.get(16) == "Acme Sans Pro"
    assert instantiated.ttf_tables.name.get(17) == "Condensed Display Bold"
    assert instantiated.ttf_tables.name.get(21) == "Acme Sans Pro"
    assert instantiated.ttf_tables.name.get(22) == "Condensed Display Bold"
    assert instantiated.ttf_tables.name.get(25) == "Acme Sans Pro"
    assert instantiated.ttf_tables.name.get(6) == "AcmeSansMenu-CondensedDisplayBold"


def test_preview_naming_policy_matches_generated_name_records(roboto: TtfFont) -> None:
    preview = roboto.preview_naming_policy(
        {"wght": 700.0, "wdth": 75.0},
        naming_strategy="ribbi-safe",
        legacy_family_name="Acme Sans Menu",
        typographic_family_name="Acme Sans Pro",
        typographic_style_name="Condensed Display Bold",
    )
    instantiated = roboto.instantiate(
        {"wght": 700.0, "wdth": 75.0},
        naming_strategy="ribbi-safe",
        legacy_family_name="Acme Sans Menu",
        typographic_family_name="Acme Sans Pro",
        typographic_style_name="Condensed Display Bold",
    )

    assert preview.source_instance_name == "Condensed Bold"
    assert preview.name_ids == {
        1: "Acme Sans Menu",
        2: "Bold",
        4: "Acme Sans Menu Condensed Display Bold",
        6: "AcmeSansMenu-CondensedDisplayBold",
        16: "Acme Sans Pro",
        17: "Condensed Display Bold",
        21: "Acme Sans Pro",
        22: "Condensed Display Bold",
        25: "Acme Sans Pro",
    }
    for name_id, value in preview.name_ids.items():
        assert instantiated.ttf_tables.name.get(name_id) == value


def test_instantiate_emits_windows_and_mac_english_name_records(roboto: TtfFont) -> None:
    instantiated = roboto.instantiate(
        {"wght": 700.0, "wdth": 75.0},
        naming_strategy="ribbi-safe",
        typographic_family_name="Acme Sans Pro",
        typographic_style_name="Condensed Display Bold",
    )
    name_table = instantiated.ttf_tables.name

    expected = {
        1: "Roboto Instance",
        2: "Bold",
        4: "Roboto Instance Condensed Display Bold",
        6: "RobotoInstance-CondensedDisplayBold",
        16: "Acme Sans Pro",
        17: "Condensed Display Bold",
        21: "Acme Sans Pro",
        22: "Condensed Display Bold",
        25: "Acme Sans Pro",
    }
    for name_id, value in expected.items():
        assert any(
            record.platform_id == 3
            and record.encoding_id == 1
            and record.language_id == 0x0409
            and record.value == value
            for record in name_table.records_for(name_id)
        )
        assert any(
            record.platform_id == 1
            and record.encoding_id == 0
            and record.language_id == 0
            and record.value == value
            for record in name_table.records_for(name_id)
        )

    preview = roboto.preview_naming_policy(
        {"wght": 700.0, "wdth": 75.0},
        naming_strategy="ribbi-safe",
        typographic_family_name="Acme Sans Pro",
        typographic_style_name="Condensed Display Bold",
    )
    assert preview.platform_diagnostics is not None
    assert preview.platform_diagnostics.macos_typographic_names_present is True


def test_instantiate_updates_existing_localized_name_records(roboto: TtfFont) -> None:
    original_records = list(roboto.ttf_tables.name.records)
    roboto.ttf_tables.name.records.append(NameRecord(3, 1, 0x040C, 1, "Roboto Ancien"))
    roboto.ttf_tables.name.records.append(NameRecord(3, 1, 0x0409, 16, "Roboto"))
    roboto.ttf_tables.name.records.append(NameRecord(3, 1, 0x040C, 16, "Roboto Texte"))

    try:
        instantiated = roboto.instantiate(
            {"wght": 700.0},
            naming_strategy="menu-safe",
            typographic_family_name="Acme Sans Pro",
        )
    finally:
        roboto.ttf_tables.name.records = original_records

    french_family = [
        record
        for record in instantiated.ttf_tables.name.records_for(1)
        if record.platform_id == 3 and record.encoding_id == 1 and record.language_id == 0x040C
    ]
    french_typographic_family = [
        record
        for record in instantiated.ttf_tables.name.records_for(16)
        if record.platform_id == 3 and record.encoding_id == 1 and record.language_id == 0x040C
    ]
    assert [record.value for record in french_family] == ["Roboto Instance"]
    assert [record.value for record in french_typographic_family] == ["Acme Sans Pro"]


def test_preview_naming_policy_reports_stat_diagnostics_without_source_stat(roboto: TtfFont) -> None:
    original_stat = roboto.ttf_tables._raw.pop("STAT", None)
    try:
        preview = roboto.preview_naming_policy({"wght": 700.0})
    finally:
        if original_stat is not None:
            roboto.ttf_tables._raw["STAT"] = original_stat

    assert preview.stat_diagnostics is not None
    assert preview.stat_diagnostics.source_has_stat is False
    assert preview.stat_diagnostics.static_export_action == "none"
    assert preview.stat_diagnostics.typographic_family_ids_emitted == (16, 21, 25)
    assert preview.stat_diagnostics.typographic_style_ids_emitted == (17, 22)
    assert preview.stat_diagnostics.warnings == ()


def test_preview_naming_policy_tolerates_malformed_source_stat(roboto: TtfFont) -> None:
    original_stat = roboto.ttf_tables._raw.get("STAT")
    roboto.ttf_tables._raw["STAT"] = b"\x00\x01\x00"
    try:
        preview = roboto.preview_naming_policy({"wght": 700.0})
    finally:
        if original_stat is None:
            roboto.ttf_tables._raw.pop("STAT", None)
        else:
            roboto.ttf_tables._raw["STAT"] = original_stat

    assert preview.stat_diagnostics is not None
    assert preview.stat_diagnostics.source_has_stat is True
    assert preview.stat_diagnostics.source_stat_name_ids == ()
    assert preview.stat_diagnostics.static_export_action == "drop-source-stat"
    assert any("stat-dropped" in warning for warning in preview.warnings)


def test_preview_naming_policy_reports_source_stat_drop_and_name_divergence(roboto: TtfFont) -> None:
    preview = roboto.preview_naming_policy(
        {"wght": 700.0, "wdth": 75.0},
        naming_strategy="ribbi-safe",
    )

    assert preview.stat_diagnostics is not None
    assert preview.stat_diagnostics.source_has_stat is True
    assert preview.stat_diagnostics.static_export_action == "drop-source-stat"
    assert preview.stat_diagnostics.legacy_typographic_family_diverges is True
    assert preview.stat_diagnostics.legacy_typographic_style_diverges is True
    assert any("stat-dropped" in warning for warning in preview.stat_diagnostics.warnings)
    assert any("stat-dropped" in warning for warning in preview.warnings)
    payload = preview.to_dict()
    assert payload["stat_diagnostics"]["source_has_stat"] is True
    assert payload["stat_diagnostics"]["typographic_family_ids_emitted"] == [16, 21, 25]


def test_preview_naming_policy_reports_source_stat_name_id_coverage(roboto: TtfFont) -> None:
    original_stat = roboto.ttf_tables._raw.get("STAT")
    original_records = list(roboto.ttf_tables.name.records)
    roboto.ttf_tables._raw["STAT"] = _synthetic_stat_table()
    roboto.ttf_tables.name.records.append(NameRecord(3, 1, 0x0409, 60001, "Weight Axis"))
    roboto.ttf_tables.name.records.append(NameRecord(3, 1, 0x0409, 60002, "Width Axis"))
    roboto.ttf_tables.name.records.append(NameRecord(3, 1, 0x0409, 60004, "Regular Fallback"))
    try:
        preview = roboto.preview_naming_policy(
            {"wght": 700.0, "wdth": 75.0},
            naming_strategy="ribbi-safe",
        )
    finally:
        if original_stat is None:
            roboto.ttf_tables._raw.pop("STAT", None)
        else:
            roboto.ttf_tables._raw["STAT"] = original_stat
        roboto.ttf_tables.name.records = original_records

    assert preview.stat_diagnostics is not None
    assert preview.stat_diagnostics.source_stat_name_ids == (2, 60001, 60002, 60003, 60004)
    assert preview.stat_diagnostics.covered_source_stat_name_ids == (2,)
    assert preview.stat_diagnostics.uncovered_source_stat_name_ids == (60001, 60002, 60003, 60004)
    assert preview.stat_diagnostics.source_stat_name_labels == (
        (2, "Regular", True),
        (60001, "Weight Axis", False),
        (60002, "Width Axis", False),
        (60003, None, False),
        (60004, "Regular Fallback", False),
    )
    payload = preview.to_dict()
    assert payload["stat_diagnostics"]["source_stat_name_ids"] == [2, 60001, 60002, 60003, 60004]
    assert payload["stat_diagnostics"]["covered_source_stat_name_ids"] == [2]
    assert payload["stat_diagnostics"]["uncovered_source_stat_name_ids"] == [
        60001,
        60002,
        60003,
        60004,
    ]
    assert payload["stat_diagnostics"]["source_stat_name_labels"] == [
        {"name_id": 2, "label": "Regular", "covered": True},
        {"name_id": 60001, "label": "Weight Axis", "covered": False},
        {"name_id": 60002, "label": "Width Axis", "covered": False},
        {"name_id": 60003, "label": None, "covered": False},
        {"name_id": 60004, "label": "Regular Fallback", "covered": False},
    ]


def test_build_static_stat_table_references_axis_and_generated_name_ids(roboto: TtfFont) -> None:
    data = build_static_stat_table(
        roboto.axes,
        {"wght": 700.0, "wdth": 75.0},
        value_name_id=17,
        elided_fallback_name_id=2,
    )

    expected_ids = tuple(sorted({2, 17, *(axis.name_id for axis in roboto.axes)}))
    assert extract_stat_name_ids(data) == expected_ids


def test_preview_naming_policy_reports_static_stat_generation(roboto: TtfFont) -> None:
    preview = roboto.preview_naming_policy(
        {"wght": 700.0, "wdth": 75.0},
        stat_policy="static",
    )

    assert preview.stat_diagnostics is not None
    assert preview.stat_diagnostics.stat_policy == "static"
    assert preview.stat_diagnostics.static_export_action == "synthesize-static-stat"
    assert preview.stat_diagnostics.generated_stat_axis_tags == tuple(axis.tag for axis in roboto.axes)
    assert preview.stat_diagnostics.generated_stat_name_ids == tuple(
        sorted({2, 17, *(axis.name_id for axis in roboto.axes)})
    )
    assert not any("stat-dropped" in warning for warning in preview.warnings)


def test_instantiate_static_stat_policy_emits_stat_table(roboto: TtfFont) -> None:
    instantiated = roboto.instantiate({"wght": 700.0, "wdth": 75.0}, stat_policy="static")

    assert instantiated.is_variable is False
    assert "STAT" in instantiated.ttf_tables._raw
    assert "fvar" not in instantiated.ttf_tables._raw
    assert "gvar" not in instantiated.ttf_tables._raw
    assert "HVAR" not in instantiated.ttf_tables._raw
    assert extract_stat_name_ids(instantiated.ttf_tables._raw["STAT"]) == tuple(
        sorted({2, 17, *(axis.name_id for axis in roboto.axes)})
    )


def test_instantiate_default_stat_policy_preserves_drop_behavior(roboto: TtfFont) -> None:
    instantiated = roboto.instantiate({"wght": 700.0, "wdth": 75.0})

    assert "STAT" not in instantiated.ttf_tables._raw


def test_instantiate_rejects_unknown_stat_policy(roboto: TtfFont) -> None:
    with pytest.raises(ValueError, match="Unknown STAT policy"):
        roboto.instantiate({"wght": 700.0}, stat_policy="copy")


def test_smart_instancer_preview_naming_policy_normalizes_symbolic_values(roboto: TtfFont) -> None:
    preview = roboto.smart_instancer.preview_naming_policy(
        {"wght": "bold"},
        family_suffix="  Web   QA  ",
    )

    assert preview.family_suffix == "Web QA"
    assert preview.coordinates == {"wdth": 100.0, "wght": 700.0}
    assert preview.legacy_family_name == "Roboto Web QA"
    assert preview.legacy_style_name == "Bold"
    assert preview.to_dict()["name_ids"]["6"] == "RobotoWebQA-Bold"


def test_preview_naming_policy_reports_collision_warnings(roboto: TtfFont) -> None:
    preview = roboto.preview_naming_policy(
        {"wght": 400.0, "wdth": 100.0},
        naming_strategy="preserve-family",
    )

    assert preview.legacy_family_name == "Roboto"
    assert preview.legacy_style_name == "Regular"
    assert any("legacy-menu-collision" in warning for warning in preview.warnings)
    assert any("postscript-collision" in warning for warning in preview.warnings)


def test_preview_naming_policy_reports_platform_diagnostics_for_collisions(
    roboto: TtfFont,
) -> None:
    preview = roboto.preview_naming_policy(
        {"wght": 400.0, "wdth": 100.0},
        naming_strategy="preserve-family",
    )

    assert preview.platform_diagnostics is not None
    assert preview.platform_diagnostics.windows_legacy_menu_safe is False
    assert preview.platform_diagnostics.windows_legacy_style_ribbi is True
    assert preview.platform_diagnostics.macos_typographic_names_present is True
    assert preview.platform_diagnostics.postscript_name_safe is False
    assert preview.platform_diagnostics.postscript_name_length == len(preview.postscript_name)
    assert any("windows-menu-collision" in warning for warning in preview.warnings)
    assert any("postscript-platform-collision" in warning for warning in preview.warnings)
    payload = preview.to_dict()
    assert payload["platform_diagnostics"]["windows_legacy_menu_safe"] is False
    assert payload["platform_diagnostics"]["postscript_name_safe"] is False


def test_preview_naming_policy_reports_safe_platform_diagnostics(roboto: TtfFont) -> None:
    preview = roboto.preview_naming_policy(
        {"wght": 700.0, "wdth": 75.0},
        naming_strategy="ribbi-safe",
        legacy_family_name="Acme Sans Menu",
        typographic_family_name="Acme Sans Pro",
        typographic_style_name="Condensed Display Bold",
    )

    assert preview.platform_diagnostics is not None
    assert preview.platform_diagnostics.windows_legacy_menu_safe is True
    assert preview.platform_diagnostics.windows_legacy_style_ribbi is True
    assert preview.platform_diagnostics.macos_typographic_names_present is True
    assert preview.platform_diagnostics.macos_typographic_names_diverge is True
    assert preview.platform_diagnostics.postscript_name_safe is True
    assert not any("windows-menu-collision" in warning for warning in preview.warnings)
    assert not any("postscript-platform-collision" in warning for warning in preview.warnings)


def test_preview_naming_policy_reports_postscript_name_sanitization(roboto: TtfFont) -> None:
    preview = roboto.preview_naming_policy(
        {"wght": 700.0},
        legacy_family_name="Acme Sans/Menu",
        typographic_style_name="Display Bold+QA",
    )

    assert preview.postscript_name == "AcmeSansMenu-DisplayBoldQA"
    assert preview.platform_diagnostics is not None
    assert preview.platform_diagnostics.postscript_name_sanitized is True
    assert any("postscript-name-sanitized" in warning for warning in preview.platform_diagnostics.warnings)
    assert any("postscript-name-sanitized" in warning for warning in preview.warnings)
    assert preview.to_dict()["platform_diagnostics"]["postscript_name_sanitized"] is True


def test_instantiate_normalizes_explicit_family_name_overrides(roboto: TtfFont) -> None:
    instantiated = roboto.instantiate(
        {"wght": 700.0},
        legacy_family_name="  Acme   Menu  ",
        typographic_family_name="  Acme   Text  ",
    )

    assert instantiated.ttf_tables.name.get(1) == "Acme Menu"
    assert instantiated.ttf_tables.name.get(16) == "Acme Text"


def test_instantiate_normalizes_explicit_style_name_overrides(roboto: TtfFont) -> None:
    instantiated = roboto.instantiate(
        {"wght": 700.0},
        legacy_style_name="  Menu   Bold  ",
        typographic_style_name="  Text   Bold  ",
    )

    assert instantiated.ttf_tables.name.get(2) == "Menu Bold"
    assert instantiated.ttf_tables.name.get(17) == "Text Bold"
    assert instantiated.ttf_tables.name.get(22) == "Text Bold"


def test_instantiate_rejects_blank_family_name_overrides(roboto: TtfFont) -> None:
    with pytest.raises(ValueError, match="legacy_family_name must not be blank"):
        roboto.instantiate({"wght": 700.0}, legacy_family_name="   ")
    with pytest.raises(ValueError, match="typographic_family_name must not be blank"):
        roboto.instantiate({"wght": 700.0}, typographic_family_name="   ")


def test_instantiate_rejects_blank_style_name_overrides(roboto: TtfFont) -> None:
    with pytest.raises(ValueError, match="legacy_style_name must not be blank"):
        roboto.instantiate({"wght": 700.0}, legacy_style_name="   ")
    with pytest.raises(ValueError, match="typographic_style_name must not be blank"):
        roboto.instantiate({"wght": 700.0}, typographic_style_name="   ")


def test_instantiate_rejects_unknown_naming_strategy(roboto: TtfFont) -> None:
    with pytest.raises(ValueError, match="Unknown naming strategy"):
        roboto.instantiate({"wght": 700.0}, naming_strategy="custom")


def test_instantiate_requires_variable_font(roboto: TtfFont) -> None:
    tables = roboto.ttf_tables
    original_raw = tables._raw.pop("fvar", None)
    original_parsed = tables.fvar
    tables.fvar = None
    try:
        with pytest.raises(FontNotSupportedException, match="Font is not variable"):
            roboto.instantiate({"wght": 700.0})
    finally:
        if original_raw is not None:
            tables._raw["fvar"] = original_raw
        tables.fvar = original_parsed


def test_instantiate_requires_gvar(roboto: TtfFont) -> None:
    tables = roboto.ttf_tables
    original_raw = tables._raw.pop("gvar", None)
    try:
        with pytest.raises(FontNotSupportedException, match="requires gvar"):
            roboto.instantiate({"wght": 700.0})
    finally:
        if original_raw is not None:
            tables._raw["gvar"] = original_raw


def test_smart_instancer_default_coordinates(roboto: TtfFont) -> None:
    resolved = roboto.smart_instancer.resolve()
    assert resolved.is_default is True
    assert resolved.coordinates == {"wdth": 100.0, "wght": 400.0}
    assert resolved.label == "Regular"


def test_smart_instancer_partial_coordinates_merge_defaults(roboto: TtfFont) -> None:
    resolved = roboto.smart_instancer.resolve({"wght": 700.0})
    assert resolved.coordinates == {"wdth": 100.0, "wght": 700.0}
    assert resolved.source_instance is not None


def test_smart_instancer_builds_waterfall_sheet(roboto: TtfFont) -> None:
    preview = roboto.smart_instancer.build_waterfall_sheet(
        ["Bold", "Condensed Bold"],
        include_default=True,
        text="Waterfall QA",
    )

    assert isinstance(preview, PreviewImage)
    assert preview.filename == "family-waterfall.png"
    assert preview.data.startswith(b"\x89PNG\r\n\x1a\n")


def test_smart_instancer_builds_matrix_sheet(roboto: TtfFont) -> None:
    preview = roboto.smart_instancer.build_matrix_sheet(
        ["Bold", "Condensed Bold"],
        text="Matrix QA",
    )

    assert isinstance(preview, PreviewImage)
    assert preview.filename == "family-matrix.png"
    assert preview.data.startswith(b"\x89PNG\r\n\x1a\n")


def test_smart_instancer_builds_family_review_board(roboto: TtfFont) -> None:
    preview = roboto.smart_instancer.build_family_review_board(
        ["Bold", "Condensed Bold"],
        include_default=True,
        text="Review Board",
        family_name="Roboto Review",
    )

    assert isinstance(preview, PreviewImage)
    assert preview.filename == "family-review-board.png"
    assert preview.data.startswith(b"\x89PNG\r\n\x1a\n")


def test_smart_instancer_builds_family_review_export_package(roboto: TtfFont) -> None:
    package = roboto.smart_instancer.build_family_review_export_package(
        ["Bold", "Condensed Bold"],
        include_default=True,
        text="Release Notes",
        family_name="Roboto Release",
    )

    assert isinstance(package, FamilyReviewExportPackage)
    assert package.family_name == "Roboto Release"
    assert package.board.filename == "family-review-board.png"
    assert package.board.data.startswith(b"\x89PNG\r\n\x1a\n")
    assert package.manifest["kind"] == "family_review_export"
    assert package.manifest["bundle_count"] == 3


def test_smart_instancer_can_instantiate_named_instance(roboto: TtfFont) -> None:
    instantiated = roboto.smart_instancer.instantiate_named("Bold")
    assert instantiated.font_style == "Bold"
    assert instantiated.font_family == "Roboto Instance"


def test_smart_instancer_passes_naming_strategy_through(roboto: TtfFont) -> None:
    instantiated = roboto.smart_instancer.instantiate_named(
        "Bold",
        naming_strategy="preserve-family",
    )
    assert instantiated.font_family == "Roboto"
    assert instantiated.font_name == "Roboto Bold"


def test_smart_instancer_named_instance_plus_override(roboto: TtfFont) -> None:
    resolved = roboto.smart_instancer.resolve(instance_name="Bold", wdth=75.0)
    assert resolved.coordinates == {"wdth": 75.0, "wght": 700.0}
    assert resolved.source_instance is not None
    assert resolved.source_instance.label == "Condensed Bold"
    instantiated = roboto.smart_instancer.instantiate_named("Bold", wdth=75.0)
    assert instantiated.font_style == "Condensed Bold"


def test_smart_instancer_accepts_preset_coordinate_names(roboto: TtfFont) -> None:
    resolved = roboto.smart_instancer.resolve({"wght": "Bold", "wdth": "Condensed"})
    assert resolved.coordinates == {"wdth": 75.0, "wght": 700.0}
    assert resolved.source_instance is not None
    assert resolved.source_instance.label == "Condensed Bold"


def test_smart_instancer_accepts_symbolic_axis_bounds(roboto: TtfFont) -> None:
    resolved = roboto.smart_instancer.resolve({"wght": "max", "wdth": "default"})
    assert resolved.coordinates == {"wdth": 100.0, "wght": 900.0}
    assert resolved.source_instance is not None
    assert resolved.source_instance.label == "Black"


def test_smart_instancer_suggests_axis_values_from_presets(roboto: TtfFont) -> None:
    values = roboto.smart_instancer.suggest_axis_values("wght")
    assert values[0] == 100.0
    assert 400.0 in values
    assert values[-1] == 900.0


def test_smart_instancer_suggests_axis_values_with_bounds(roboto: TtfFont) -> None:
    values = roboto.smart_instancer.suggest_axis_values("wdth", include_bounds=True)
    assert values == [75.0, 87.5, 100.0]


def test_smart_instancer_resolves_axis_grid_from_presets(roboto: TtfFont) -> None:
    resolved = roboto.smart_instancer.resolve_axis_grid(
        "wght",
        use_axis_presets=True,
        include_bounds=True,
    )
    assert len(resolved) == 9
    assert resolved[0].coordinates["wght"] == 100.0
    assert resolved[-1].coordinates["wght"] == 900.0


def test_smart_instancer_resolves_two_axis_grid_from_presets(roboto: TtfFont) -> None:
    resolved = roboto.smart_instancer.resolve_axis_grid(
        "wght",
        use_axis_presets=True,
        secondary_axis_tag="wdth",
        use_secondary_axis_presets=True,
    )
    coordinate_sets = [item.coordinates for item in resolved]
    assert {"wdth": 75.0, "wght": 700.0} in coordinate_sets
    assert {"wdth": 100.0, "wght": 400.0} in coordinate_sets
    assert len(resolved) == 27


def test_smart_instancer_accepts_unique_partial_instance_name(roboto: TtfFont) -> None:
    resolved = roboto.smart_instancer.resolve(instance_name="condensedbold")
    assert resolved.coordinates == {"wdth": 75.0, "wght": 700.0}
    assert resolved.source_instance is not None
    assert resolved.source_instance.label == "Condensed Bold"


def test_smart_instancer_rejects_ambiguous_partial_instance_name(roboto: TtfFont) -> None:
    with pytest.raises(ValueError, match="Ambiguous named instance"):
        roboto.smart_instancer.resolve(instance_name="r")


def test_smart_instancer_builds_web_bundle(roboto: TtfFont) -> None:
    bundle = roboto.smart_instancer.build_web_bundle(
        instance_name="Bold",
        include_woff=False,
        presets=("latin",),
    )
    assert isinstance(bundle, WebFontBundle)
    assert bundle.font_assets[0].filename == "roboto-instance-bold.woff2"


def test_web_bundle_inherits_hvar_aware_widths(roboto: TtfFont) -> None:
    instantiated = roboto.instantiate({"wdth": 75.0})
    tables = roboto.ttf_tables
    original_raw = tables._raw.pop("HVAR", None)
    original_parsed = tables.hvar
    tables.hvar = None
    try:
        without_hvar = roboto.instantiate({"wdth": 75.0})
    finally:
        if original_raw is not None:
            tables._raw["HVAR"] = original_raw
        tables.hvar = original_parsed

    differing_gid = next(
        (
            gid
            for gid, (aware_metric, fallback_metric) in enumerate(
                zip(instantiated.ttf_tables.hmtx.metrics, without_hvar.ttf_tables.hmtx.metrics)
            )
            if aware_metric.advance_width != fallback_metric.advance_width
        ),
        None,
    )
    assert differing_gid is not None

    bundle = WebFontBuilder.build(
        roboto,
        instance_coordinates={"wdth": 75.0},
        include_woff=False,
    )
    bundled = FontLoader.open(bundle.font_assets[0].data)
    bundled_font = bundled.inner_font if hasattr(bundled, "inner_font") else bundled
    assert (
        bundled_font.ttf_tables.hmtx.get_metric(differing_gid).advance_width
        == instantiated.ttf_tables.hmtx.get_metric(differing_gid).advance_width
    )


def test_font_preview_builder_renders_variable_instance_preview(roboto: TtfFont) -> None:
    preview = FontPreviewBuilder.build(
        roboto,
        instance_name="Bold",
        text="Preview Bold",
    )
    assert isinstance(preview, PreviewImage)
    assert preview.filename == "roboto-instance-bold.png"
    assert preview.media_type == "image/png"
    assert preview.data.startswith(b"\x89PNG\r\n\x1a\n")


def test_font_preview_builder_renders_svg_preview(roboto: TtfFont) -> None:
    preview = FontPreviewBuilder.build(
        roboto,
        instance_name="Bold",
        text="Preview Bold",
        output_format="svg",
    )
    assert isinstance(preview, PreviewImage)
    assert preview.filename == "roboto-instance-bold.svg"
    assert preview.media_type == "image/svg+xml"
    assert preview.data.startswith(b'<?xml version="1.0" encoding="UTF-8"?>')
    assert b"<svg " in preview.data
    assert b"<path d=" in preview.data


def test_smart_instancer_builds_preview_with_override(roboto: TtfFont) -> None:
    preview = roboto.smart_instancer.build_preview(
        instance_name="Bold",
        text="Preview Condensed",
        wdth=75.0,
    )
    assert preview.filename == "roboto-instance-condensed-bold.png"
    assert preview.data.startswith(b"\x89PNG\r\n\x1a\n")


def test_smart_instancer_builds_svg_previews(roboto: TtfFont) -> None:
    previews = roboto.smart_instancer.build_previews(
        ["Bold", "Condensed Bold"],
        output_format="svg",
    )
    assert [preview.filename for _resolved, preview in previews] == [
        "roboto-instance-bold.svg",
        "roboto-instance-condensed-bold.svg",
    ]
    assert all(preview.media_type == "image/svg+xml" for _resolved, preview in previews)
    assert all(preview.data.startswith(b'<?xml version="1.0" encoding="UTF-8"?>') for _resolved, preview in previews)


def test_preview_image_write_to(tmp_path: Path, roboto: TtfFont) -> None:
    preview = FontPreviewBuilder.build(roboto, instance_name="Bold")
    out = preview.write_to(tmp_path / preview.filename)
    assert out.exists()
    assert out.read_bytes() == preview.data


def test_smart_instancer_builds_many_previews(roboto: TtfFont) -> None:
    previews = roboto.smart_instancer.build_previews(
        ["Bold", "Condensed Bold"],
        include_default=True,
        text="Batch Preview",
    )
    assert len(previews) == 3
    assert previews[0][0].is_default is True
    assert previews[0][1].filename == "roboto-instance-regular.png"
    assert previews[1][1].filename == "roboto-instance-bold.png"
    assert previews[2][1].filename == "roboto-instance-condensed-bold.png"
    assert all(preview.data.startswith(b"\x89PNG\r\n\x1a\n") for _, preview in previews)


def test_smart_instancer_builds_axis_grid_previews(roboto: TtfFont) -> None:
    previews = roboto.smart_instancer.build_axis_grid_previews(
        "wght",
        [400.0, 700.0],
        secondary_axis_tag="wdth",
        secondary_values=[75.0, 100.0],
        text="Grid Preview",
    )
    assert len(previews) == 4
    coordinate_sets = [resolved.coordinates for resolved, _preview in previews]
    assert {"wdth": 75.0, "wght": 400.0} in coordinate_sets
    assert {"wdth": 100.0, "wght": 700.0} in coordinate_sets
    assert all(preview.data.startswith(b"\x89PNG\r\n\x1a\n") for _, preview in previews)


def test_smart_instancer_builds_axis_grid_previews_from_presets(roboto: TtfFont) -> None:
    previews = roboto.smart_instancer.build_axis_grid_previews(
        "wght",
        use_axis_presets=True,
        secondary_axis_tag="wdth",
        use_secondary_axis_presets=True,
        text="Preset Grid Preview",
    )
    assert len(previews) == 27
    assert previews[0][1].data.startswith(b"\x89PNG\r\n\x1a\n")


def test_axis_grid_previews_require_primary_values(roboto: TtfFont) -> None:
    with pytest.raises(ValueError, match="requires at least one value"):
        roboto.smart_instancer.build_axis_grid_previews("wght", [])


def test_smart_instancer_builds_axis_grid_sheet(roboto: TtfFont) -> None:
    preview = roboto.smart_instancer.build_axis_grid_sheet(
        "wght",
        [400.0, 700.0],
        secondary_axis_tag="wdth",
        secondary_values=[75.0, 100.0],
        text="Sheet Preview",
    )
    assert preview.filename == "preview-grid-sheet.png"
    assert preview.data.startswith(b"\x89PNG\r\n\x1a\n")
    assert len(preview.data) > 7000


def test_smart_instancer_builds_comparison_sheet(roboto: TtfFont) -> None:
    preview = roboto.smart_instancer.build_comparison_sheet(
        before_instance_name="Regular",
        after_instance_name="Condensed Bold",
        text="Compare Preview",
    )
    assert preview.filename == "preview-compare-sheet.png"
    assert preview.data.startswith(b"\x89PNG\r\n\x1a\n")
    assert len(preview.data) > 7000


def test_comparison_sheet_includes_visual_diff_tints(roboto: TtfFont) -> None:
    preview = roboto.smart_instancer.build_comparison_sheet(
        before_instance_name="Regular",
        after_instance_name="Condensed Bold",
        text="Diff Compare",
    )
    _width, _height, pixels = _decode_png_rgb(preview.data)
    triplets = {
        tuple(pixels[index:index + 3])
        for index in range(0, len(pixels), 3)
    }
    assert (198, 109, 42) in triplets
    assert (71, 126, 199) in triplets
    assert (126, 94, 156) in triplets


def test_axis_grid_sheet_includes_styled_board_panels(roboto: TtfFont) -> None:
    preview = roboto.smart_instancer.build_axis_grid_sheet(
        "wght",
        [400.0, 700.0],
        secondary_axis_tag="wdth",
        secondary_values=[75.0, 100.0],
        text="Styled Sheet",
    )
    _width, _height, pixels = _decode_png_rgb(preview.data)
    triplets = {
        tuple(pixels[index:index + 3])
        for index in range(0, len(pixels), 3)
    }
    assert (248, 242, 232) in triplets
    assert (255, 250, 244) in triplets
    assert (203, 183, 156) in triplets


def test_comparison_sheet_contains_board_text_pixels(roboto: TtfFont) -> None:
    preview = roboto.smart_instancer.build_comparison_sheet(
        before_instance_name="Regular",
        after_coordinates={"wght": 700.0, "wdth": 75.0},
        text="Styled Compare",
    )
    _width, _height, pixels = _decode_png_rgb(preview.data)
    triplets = {
        tuple(pixels[index:index + 3])
        for index in range(0, len(pixels), 3)
    }
    assert (68, 60, 50) in triplets


def test_comparison_sheet_annotation_panel_increases_canvas_height(roboto: TtfFont) -> None:
    comparison = roboto.smart_instancer.build_comparison_sheet(
        before_instance_name="Regular",
        after_instance_name="Condensed Bold",
        text="Annotation Compare",
    )
    plain_before = FontPreviewBuilder.build(roboto, instance_name="Regular", text="Annotation Compare")
    plain_after = FontPreviewBuilder.build(roboto, instance_name="Condensed Bold", text="Annotation Compare")
    base_sheet = FontPreviewBuilder.compose_sheet(
        [plain_before, plain_after],
        columns=2,
        title="Before vs After",
        column_headers=["Before", "After"],
        labels=["REGULAR", "CONDENSED BOLD"],
    )
    _base_width, base_height, _base_pixels = _decode_png_rgb(base_sheet.data)
    _comparison_width, comparison_height, _comparison_pixels = _decode_png_rgb(comparison.data)
    assert comparison_height > base_height


def test_comparison_sheet_diff_panel_increases_canvas_width(roboto: TtfFont) -> None:
    comparison = roboto.smart_instancer.build_comparison_sheet(
        before_instance_name="Regular",
        after_instance_name="Condensed Bold",
        text="Width Compare",
    )
    plain_before = FontPreviewBuilder.build(roboto, instance_name="Regular", text="Width Compare")
    plain_after = FontPreviewBuilder.build(roboto, instance_name="Condensed Bold", text="Width Compare")
    base_sheet = FontPreviewBuilder.compose_sheet(
        [plain_before, plain_after],
        columns=2,
        title="Before vs After",
        column_headers=["Before", "After"],
        labels=["REGULAR", "CONDENSED BOLD"],
    )
    base_width, _base_height, _base_pixels = _decode_png_rgb(base_sheet.data)
    comparison_width, _comparison_height, _comparison_pixels = _decode_png_rgb(comparison.data)
    assert comparison_width > base_width


def test_comparison_sheet_overlay_panel_further_increases_canvas_width(roboto: TtfFont) -> None:
    comparison = roboto.smart_instancer.build_comparison_sheet(
        before_instance_name="Regular",
        after_instance_name="Condensed Bold",
        text="Overlay Compare",
    )
    plain_before = FontPreviewBuilder.build(roboto, instance_name="Regular", text="Overlay Compare")
    plain_after = FontPreviewBuilder.build(roboto, instance_name="Condensed Bold", text="Overlay Compare")
    diff_preview = FontPreviewBuilder.compose_difference_preview(plain_before, plain_after)
    three_panel = FontPreviewBuilder.compose_sheet(
        [plain_before, diff_preview, plain_after],
        columns=3,
        title="Before vs After",
        column_headers=["Before", "Diff", "After"],
        labels=["REGULAR", "DIFF WGHT, WDTH", "CONDENSED BOLD"],
    )
    three_panel_width, _h, _p = _decode_png_rgb(three_panel.data)
    comparison_width, _comparison_height, _comparison_pixels = _decode_png_rgb(comparison.data)
    assert comparison_width > three_panel_width


def test_smart_instancer_unknown_instance_raises(roboto: TtfFont) -> None:
    with pytest.raises(ValueError, match="Unknown named instance"):
        roboto.smart_instancer.instantiate_named("UltraBlack")


def test_smart_instancer_unknown_axis_raises(roboto: TtfFont) -> None:
    with pytest.raises(ValueError, match="Unknown variable axis"):
        roboto.smart_instancer.resolve({"opsz": 12.0})


def test_smart_instancer_resolve_named_many_all_instances(roboto: TtfFont) -> None:
    resolved = roboto.smart_instancer.resolve_named_many()
    assert len(resolved) == len(roboto.variable_instances)
    assert resolved[0].source_instance is not None


def test_smart_instancer_instantiate_many_include_default(roboto: TtfFont) -> None:
    generated = roboto.smart_instancer.instantiate_many(["Bold"], include_default=True)
    assert len(generated) == 2
    assert generated[0][0].is_default is True
    assert generated[0][1].font_style == "Regular"
    assert generated[1][1].font_style == "Bold"


def test_smart_instancer_instantiate_many_supports_naming_strategy(roboto: TtfFont) -> None:
    generated = roboto.smart_instancer.instantiate_many(
        ["Bold"],
        naming_strategy="qa-tagged",
    )
    assert len(generated) == 1
    assert generated[0][1].font_family == "Roboto QA"


def test_smart_instancer_instantiate_many_supports_name_overrides(roboto: TtfFont) -> None:
    generated = roboto.smart_instancer.instantiate_many(
        ["Condensed Bold"],
        naming_strategy="ribbi-safe",
        legacy_family_name="Acme Sans Menu",
        typographic_family_name="Acme Sans Pro",
        legacy_style_name="Bold",
        typographic_style_name="Condensed Bold",
    )

    assert len(generated) == 1
    font = generated[0][1]
    assert font.font_family == "Acme Sans Menu"
    assert font.font_style == "Bold"
    assert font.font_name == "Acme Sans Menu Condensed Bold"
    assert font.ttf_tables.name.get(16) == "Acme Sans Pro"
    assert font.ttf_tables.name.get(17) == "Condensed Bold"
