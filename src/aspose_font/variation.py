"""User-friendly variable-font metadata objects."""

from __future__ import annotations

from dataclasses import dataclass


def _normalize_language_code(language: str) -> str:
    return language.strip().replace("_", "-").casefold()


def _language_preference_chain(preferred_languages: str | tuple[str, ...]) -> list[str]:
    raw_items = (preferred_languages,) if isinstance(preferred_languages, str) else preferred_languages
    ordered: list[str] = []
    seen: set[str] = set()
    for item in raw_items:
        if not item:
            continue
        normalized = _normalize_language_code(item)
        if normalized and normalized not in seen:
            ordered.append(normalized)
            seen.add(normalized)
        if "-" in normalized:
            base = normalized.split("-", 1)[0]
            if base and base not in seen:
                ordered.append(base)
                seen.add(base)
    if "en" not in seen:
        ordered.append("en")
    return ordered


@dataclass(slots=True, frozen=True)
class LocalizationResolution:
    requested_languages: tuple[str, ...]
    preference_chain: tuple[str, ...]
    selected_language: str | None
    selected_label: str | None
    fallback_reason: str

    @property
    def is_exact_match(self) -> bool:
        return self.fallback_reason == "exact"

    def to_dict(self) -> dict[str, object]:
        return {
            "requested_languages": list(self.requested_languages),
            "preference_chain": list(self.preference_chain),
            "selected_language": self.selected_language,
            "selected_label": self.selected_label,
            "fallback_reason": self.fallback_reason,
            "is_exact_match": self.is_exact_match,
        }


@dataclass(slots=True, frozen=True)
class LocalizationCoverage:
    requested_languages: tuple[str, ...]
    available_languages: tuple[str, ...]
    matched_languages: tuple[str, ...]
    missing_languages: tuple[str, ...]
    status: str

    @property
    def requested_count(self) -> int:
        return len(self.requested_languages)

    @property
    def available_count(self) -> int:
        return len(self.available_languages)

    @property
    def matched_count(self) -> int:
        return len(self.matched_languages)

    @property
    def missing_count(self) -> int:
        return len(self.missing_languages)

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "requested_languages": list(self.requested_languages),
            "available_languages": list(self.available_languages),
            "matched_languages": list(self.matched_languages),
            "missing_languages": list(self.missing_languages),
            "requested_count": self.requested_count,
            "available_count": self.available_count,
            "matched_count": self.matched_count,
            "missing_count": self.missing_count,
        }


@dataclass(slots=True, frozen=True)
class RequestedLanguageHint:
    requested_language: str
    status: str
    matched_language: str | None
    label: str | None

    @property
    def has_requested_language_label(self) -> bool:
        return self.status in {"exact", "base-language", "locale-variant"}

    def to_dict(self) -> dict[str, object]:
        return {
            "requested_language": self.requested_language,
            "status": self.status,
            "matched_language": self.matched_language,
            "label": self.label,
            "has_requested_language_label": self.has_requested_language_label,
        }


@dataclass(slots=True, frozen=True)
class LanguageProfile:
    requested_language: str
    display_label: str | None
    resolved_language: str | None
    fallback_reason: str
    has_requested_language_label: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "requested_language": self.requested_language,
            "display_label": self.display_label,
            "resolved_language": self.resolved_language,
            "fallback_reason": self.fallback_reason,
            "has_requested_language_label": self.has_requested_language_label,
        }


def _raw_language_items(preferred_languages: str | tuple[str, ...]) -> tuple[str, ...]:
    raw_items = (preferred_languages,) if isinstance(preferred_languages, str) else preferred_languages
    return tuple(_normalize_language_code(item) for item in raw_items if item)


def _localization_resolution(
    names_by_language: dict[str, str],
    preferred_languages: str | tuple[str, ...],
) -> LocalizationResolution:
    requested = _raw_language_items(preferred_languages)
    chain = tuple(_language_preference_chain(preferred_languages))
    normalized_map = {
        _normalize_language_code(language): value
        for language, value in names_by_language.items()
    }
    if not normalized_map:
        return LocalizationResolution(
            requested_languages=requested,
            preference_chain=chain,
            selected_language=None,
            selected_label=None,
            fallback_reason="missing",
        )
    for preferred in chain:
        exact = normalized_map.get(preferred)
        if exact:
            reason = "exact" if preferred in requested else "base-language"
            return LocalizationResolution(
                requested_languages=requested,
                preference_chain=chain,
                selected_language=preferred,
                selected_label=exact,
                fallback_reason=reason,
            )
        for language, value in normalized_map.items():
            if language.startswith(f"{preferred}-"):
                return LocalizationResolution(
                    requested_languages=requested,
                    preference_chain=chain,
                    selected_language=language,
                    selected_label=value,
                    fallback_reason="locale-variant",
                )
    selected_language = next(iter(normalized_map))
    return LocalizationResolution(
        requested_languages=requested,
        preference_chain=chain,
        selected_language=selected_language,
        selected_label=normalized_map[selected_language],
        fallback_reason="first-available",
    )


def _language_match_for_request(
    available_languages: tuple[str, ...],
    requested_language: str,
) -> str | None:
    if requested_language in available_languages:
        return requested_language
    if "-" in requested_language:
        base = requested_language.split("-", 1)[0]
        if base in available_languages:
            return base
    else:
        base = requested_language
    for language in available_languages:
        if language.startswith(f"{base}-"):
            return language
    return None


def _localization_coverage(
    names_by_language: dict[str, str],
    preferred_languages: str | tuple[str, ...],
) -> LocalizationCoverage:
    requested = _raw_language_items(preferred_languages)
    available = tuple(sorted(_normalize_language_code(language) for language in names_by_language))
    if not available:
        return LocalizationCoverage(
            requested_languages=requested,
            available_languages=(),
            matched_languages=(),
            missing_languages=requested,
            status="missing",
        )

    matched: list[str] = []
    missing: list[str] = []
    for language in requested:
        match = _language_match_for_request(available, language)
        if match is None:
            missing.append(language)
        elif match not in matched:
            matched.append(match)

    if not requested or not missing:
        status = "complete"
    elif available == ("en",):
        status = "english-only"
    elif matched:
        status = "partial"
    else:
        status = "missing"

    return LocalizationCoverage(
        requested_languages=requested,
        available_languages=available,
        matched_languages=tuple(matched),
        missing_languages=tuple(missing),
        status=status,
    )


def _requested_language_hints(
    names_by_language: dict[str, str],
    preferred_languages: str | tuple[str, ...],
) -> tuple[RequestedLanguageHint, ...]:
    requested = _raw_language_items(preferred_languages)
    normalized_map = {
        _normalize_language_code(language): value
        for language, value in names_by_language.items()
    }
    available = tuple(sorted(normalized_map))
    hints: list[RequestedLanguageHint] = []
    for requested_language in requested:
        if requested_language in normalized_map:
            hints.append(
                RequestedLanguageHint(
                    requested_language=requested_language,
                    status="exact",
                    matched_language=requested_language,
                    label=normalized_map[requested_language],
                )
            )
            continue

        base = requested_language.split("-", 1)[0]
        if base in normalized_map:
            hints.append(
                RequestedLanguageHint(
                    requested_language=requested_language,
                    status="base-language",
                    matched_language=base,
                    label=normalized_map[base],
                )
            )
            continue

        variant = next((language for language in available if language.startswith(f"{base}-")), None)
        if variant is not None:
            hints.append(
                RequestedLanguageHint(
                    requested_language=requested_language,
                    status="locale-variant",
                    matched_language=variant,
                    label=normalized_map[variant],
                )
            )
            continue

        if "en" in normalized_map:
            hints.append(
                RequestedLanguageHint(
                    requested_language=requested_language,
                    status="english-fallback",
                    matched_language="en",
                    label=normalized_map["en"],
                )
            )
            continue

        if available:
            first_available = available[0]
            hints.append(
                RequestedLanguageHint(
                    requested_language=requested_language,
                    status="first-available",
                    matched_language=first_available,
                    label=normalized_map[first_available],
                )
            )
            continue

        hints.append(
            RequestedLanguageHint(
                requested_language=requested_language,
                status="missing",
                matched_language=None,
                label=None,
            )
        )
    return tuple(hints)


def build_language_profiles(
    names_by_language: dict[str, str],
    preferred_languages: str | tuple[str, ...],
    *,
    fallback_label: str | None = None,
    fallback_reason: str | None = None,
) -> tuple[LanguageProfile, ...]:
    requested = _raw_language_items(preferred_languages) or ("en",)
    profiles: list[LanguageProfile] = []
    for hint in _requested_language_hints(names_by_language, requested):
        label = hint.label
        reason = hint.status
        resolved_language = hint.matched_language
        has_requested_language_label = hint.has_requested_language_label
        if label is None and fallback_label is not None:
            label = fallback_label
            reason = fallback_reason or reason
            resolved_language = None
            has_requested_language_label = False
        profiles.append(
            LanguageProfile(
                requested_language=hint.requested_language,
                display_label=label,
                resolved_language=resolved_language,
                fallback_reason=reason,
                has_requested_language_label=has_requested_language_label,
            )
        )
    return tuple(profiles)


def _best_localized_name(
    names_by_language: dict[str, str],
    preferred_languages: str | tuple[str, ...],
) -> str | None:
    return _localization_resolution(names_by_language, preferred_languages).selected_label


def _ordered_localizations(
    names_by_language: dict[str, str],
    preferred_languages: str | tuple[str, ...] = (),
) -> tuple[tuple[str, str], ...]:
    if not names_by_language:
        return ()
    raw_items = (preferred_languages,) if isinstance(preferred_languages, str) else preferred_languages
    normalized_map = {
        _normalize_language_code(language): value
        for language, value in names_by_language.items()
    }
    ordered: list[tuple[str, str]] = []
    seen: set[str] = set()
    for preferred in _language_preference_chain(raw_items):
        value = normalized_map.get(preferred)
        if value and preferred not in seen:
            ordered.append((preferred, value))
            seen.add(preferred)
        for language, language_value in normalized_map.items():
            if language in seen:
                continue
            if language.startswith(f"{preferred}-"):
                ordered.append((language, language_value))
                seen.add(language)
    for language in sorted(normalized_map):
        if language not in seen:
            ordered.append((language, normalized_map[language]))
            seen.add(language)
    return tuple(ordered)


@dataclass(slots=True, frozen=True)
class VariableAxisPreset:
    name: str
    value: float
    description: str = ""

    def to_presentation(self, axis: VariableAxis | None = None) -> dict[str, object]:
        return {
            "name": self.name,
            "value": self.value,
            "formatted_value": axis.format_value(self.value) if axis is not None else f"{self.value:g}",
            "description": self.description,
        }


_STANDARD_AXIS_METADATA: dict[str, dict[str, object]] = {
    "wght": {
        "default_label": "Weight",
        "description": "Controls typographic stroke weight from lighter to heavier styles.",
        "unit_label": "",
        "presentation_kind": "weight",
        "display_group": "style",
        "display_order": 10,
        "recommended_step": 50.0,
        "presets": (
            ("Thin", 100.0, "Hairline or very light display weight."),
            ("ExtraLight", 200.0, "Very light text and display weight."),
            ("Light", 300.0, "Light reading weight."),
            ("Regular", 400.0, "Default reading weight."),
            ("Medium", 500.0, "Slightly stronger than regular."),
            ("SemiBold", 600.0, "Moderately bold emphasis."),
            ("Bold", 700.0, "Standard bold emphasis."),
            ("ExtraBold", 800.0, "Strong bold emphasis."),
            ("Black", 900.0, "Heaviest common weight."),
        ),
    },
    "wdth": {
        "default_label": "Width",
        "description": "Controls horizontal proportion from condensed to expanded styles.",
        "unit_label": "%",
        "presentation_kind": "width",
        "display_group": "layout",
        "display_order": 20,
        "recommended_step": 5.0,
        "presets": (
            ("UltraCondensed", 50.0, "Very narrow horizontal proportion."),
            ("ExtraCondensed", 62.5, "Clearly condensed width."),
            ("Condensed", 75.0, "Compact width for tighter fit."),
            ("SemiCondensed", 87.5, "Slightly narrower than normal."),
            ("Normal", 100.0, "Default horizontal proportion."),
            ("SemiExpanded", 112.5, "Slightly wider than normal."),
            ("Expanded", 125.0, "Comfortably expanded width."),
            ("ExtraExpanded", 150.0, "Very wide display width."),
        ),
    },
    "ital": {
        "default_label": "Italic",
        "description": "Controls the upright versus italic style state.",
        "unit_label": "",
        "presentation_kind": "toggle",
        "display_group": "style",
        "display_order": 30,
        "recommended_step": 1.0,
        "presets": (
            ("Roman", 0.0, "Default upright posture."),
            ("Italic", 1.0, "Italic posture."),
        ),
    },
    "slnt": {
        "default_label": "Slant",
        "description": "Controls the slant angle for upright or oblique styles.",
        "unit_label": "deg",
        "presentation_kind": "angle",
        "display_group": "style",
        "display_order": 40,
        "recommended_step": 1.0,
        "presets": (
            ("Upright", 0.0, "No slant applied."),
            ("Backslant", 10.0, "Positive slant angle when supported."),
            ("Oblique", -10.0, "Common negative slant angle for oblique styles."),
        ),
    },
    "opsz": {
        "default_label": "Optical Size",
        "description": "Optimizes drawing for intended point size or viewing size.",
        "unit_label": "pt",
        "presentation_kind": "size",
        "display_group": "optical",
        "display_order": 50,
        "recommended_step": 1.0,
        "presets": (
            ("Caption", 8.0, "Small caption and UI sizes."),
            ("Text", 12.0, "Default reading size."),
            ("Subhead", 18.0, "Intermediate editorial sizes."),
            ("Display", 72.0, "Large headline or display size."),
        ),
    },
}


def _axis_metadata(tag: str) -> dict[str, object]:
    return _STANDARD_AXIS_METADATA.get(tag, {})


@dataclass(slots=True)
class VariableAxis:
    tag: str
    min_value: float
    default_value: float
    max_value: float
    flags: int
    name_id: int
    names_by_language: dict[str, str]

    @property
    def available_languages(self) -> tuple[str, ...]:
        return tuple(sorted(_normalize_language_code(language) for language in self.names_by_language))

    @property
    def label(self) -> str:
        return self.name() or str(_axis_metadata(self.tag).get("default_label") or self.tag)

    @property
    def description(self) -> str | None:
        return _axis_metadata(self.tag).get("description")  # type: ignore[return-value]

    @property
    def unit_label(self) -> str:
        return str(_axis_metadata(self.tag).get("unit_label") or "")

    @property
    def presentation_kind(self) -> str:
        return str(_axis_metadata(self.tag).get("presentation_kind") or "scalar")

    @property
    def display_group(self) -> str:
        return str(_axis_metadata(self.tag).get("display_group") or "custom")

    @property
    def display_order(self) -> int:
        value = _axis_metadata(self.tag).get("display_order")
        return int(value) if value is not None else 1000

    @property
    def is_registered_axis(self) -> bool:
        return self.tag in _STANDARD_AXIS_METADATA

    @property
    def recommended_step(self) -> float:
        value = _axis_metadata(self.tag).get("recommended_step")
        return float(value) if value is not None else 1.0

    @property
    def span(self) -> float:
        return self.max_value - self.min_value

    @property
    def default_ratio(self) -> float | None:
        span = self.span
        if span == 0:
            return None
        return (self.default_value - self.min_value) / span

    @property
    def presets(self) -> list[VariableAxisPreset]:
        metadata = _axis_metadata(self.tag)
        items = metadata.get("presets")
        if not items:
            return []
        presets: list[VariableAxisPreset] = []
        seen_values: set[float] = set()
        for name, raw_value, description in items:  # type: ignore[misc]
            value = float(raw_value)
            if not (self.min_value <= value <= self.max_value):
                continue
            if value in seen_values:
                continue
            seen_values.add(value)
            presets.append(
                VariableAxisPreset(
                    name=str(name),
                    value=value,
                    description=str(description),
                )
            )
        return presets

    @property
    def is_hidden(self) -> bool:
        return bool(self.flags & 0x0001)

    @property
    def default_preset(self) -> VariableAxisPreset | None:
        for preset in self.presets:
            if preset.value == self.default_value:
                return preset
        return None

    def name(self, language: str | tuple[str, ...] = "en") -> str | None:
        return _best_localized_name(
            self.names_by_language,
            language,
        ) or str(_axis_metadata(self.tag).get("default_label"))

    def localization_resolution(
        self,
        language: str | tuple[str, ...] = "en",
    ) -> LocalizationResolution:
        resolved = _localization_resolution(self.names_by_language, language)
        if resolved.selected_label is not None:
            return resolved
        fallback_label = str(_axis_metadata(self.tag).get("default_label") or self.tag)
        return LocalizationResolution(
            requested_languages=resolved.requested_languages,
            preference_chain=resolved.preference_chain,
            selected_language=None,
            selected_label=fallback_label,
            fallback_reason="metadata-default",
        )

    def localization_coverage(
        self,
        language: str | tuple[str, ...] = "en",
    ) -> LocalizationCoverage:
        return _localization_coverage(self.names_by_language, language)

    def localized_labels(
        self,
        preferred_languages: str | tuple[str, ...] = (),
    ) -> tuple[tuple[str, str], ...]:
        return _ordered_localizations(self.names_by_language, preferred_languages)

    def requested_language_hints(
        self,
        language: str | tuple[str, ...] = "en",
    ) -> tuple[RequestedLanguageHint, ...]:
        return _requested_language_hints(self.names_by_language, language)

    def language_profiles(
        self,
        language: str | tuple[str, ...] = "en",
    ) -> tuple[LanguageProfile, ...]:
        return build_language_profiles(
            self.names_by_language,
            language,
            fallback_label=str(_axis_metadata(self.tag).get("default_label") or self.tag),
            fallback_reason="metadata-default",
        )

    def clamp(self, value: float) -> float:
        return min(max(value, self.min_value), self.max_value)

    def normalize(self, value: float) -> float:
        value = self.clamp(value)
        if value == self.default_value:
            return 0.0
        if value < self.default_value:
            denom = self.default_value - self.min_value
            return 0.0 if denom == 0 else (value - self.default_value) / denom
        denom = self.max_value - self.default_value
        return 0.0 if denom == 0 else (value - self.default_value) / denom

    def format_value(self, value: float) -> str:
        numeric = int(value) if float(value).is_integer() else value
        suffix = self.unit_label
        return f"{numeric}{suffix}" if suffix else str(numeric)

    def describe_value(self, value: float) -> str:
        preset = next((item for item in self.presets if item.value == value), None)
        formatted = self.format_value(value)
        if preset is not None:
            return f"{preset.name} ({formatted})"
        if value == self.default_value:
            return f"Default ({formatted})"
        return formatted

    @property
    def range_summary(self) -> str:
        default_text = self.describe_value(self.default_value)
        return (
            f"{self.format_value(self.min_value)} -> {self.format_value(self.max_value)} "
            f"(default: {default_text})"
        )

    @property
    def css_axis_tag(self) -> str:
        return f"'{self.tag}'"

    def css_variation_setting(self, value: float) -> str:
        return f"{self.css_axis_tag} {self.format_value(value)}"

    def ui_control(self, language: str | tuple[str, ...] = "en") -> dict[str, object]:
        return {
            "type": "slider",
            "label": self.name(language) or self.label,
            "min": self.min_value,
            "max": self.max_value,
            "default": self.default_value,
            "step": self.recommended_step,
            "unit": self.unit_label,
            "formatted_min": self.format_value(self.min_value),
            "formatted_max": self.format_value(self.max_value),
            "formatted_default": self.format_value(self.default_value),
        }

    def get_preset(self, name: str) -> VariableAxisPreset | None:
        needle = name.casefold()
        for preset in self.presets:
            if preset.name.casefold() == needle:
                return preset
        return None

    def to_presentation(
        self,
        *,
        language: str | tuple[str, ...] = "en",
        suggested_values: tuple[float, ...] | list[float] | None = None,
    ) -> dict[str, object]:
        default_preset = self.default_preset
        suggestions = tuple(suggested_values or ())
        return {
            "tag": self.tag,
            "name_id": self.name_id,
            "label": self.name(language) or self.label,
            "description": self.description,
            "localization": self.localization_resolution(language).to_dict(),
            "localization_coverage": self.localization_coverage(language).to_dict(),
            "available_languages": list(self.available_languages),
            "localized_labels": [
                {"language": item_language, "label": label}
                for item_language, label in self.localized_labels(language)
            ],
            "requested_language_hints": [
                hint.to_dict() for hint in self.requested_language_hints(language)
            ],
            "language_profiles": [
                profile.to_dict() for profile in self.language_profiles(language)
            ],
            "min_value": self.min_value,
            "default_value": self.default_value,
            "max_value": self.max_value,
            "formatted_min": self.format_value(self.min_value),
            "formatted_default": self.format_value(self.default_value),
            "formatted_max": self.format_value(self.max_value),
            "css_axis_tag": self.css_axis_tag,
            "css_default_setting": self.css_variation_setting(self.default_value),
            "ui_control": self.ui_control(language),
            "range_summary": self.range_summary,
            "default_description": self.describe_value(self.default_value),
            "default_ratio": self.default_ratio,
            "normalized_default": self.normalize(self.default_value),
            "is_hidden": self.is_hidden,
            "presentation_kind": self.presentation_kind,
            "display_group": self.display_group,
            "display_order": self.display_order,
            "is_registered_axis": self.is_registered_axis,
            "unit_label": self.unit_label,
            "recommended_step": self.recommended_step,
            "presets": [preset.to_presentation(self) for preset in self.presets],
            "default_preset": None if default_preset is None else default_preset.to_presentation(self),
            "suggested_values": [
                {
                    "value": value,
                    "formatted_value": self.format_value(value),
                    "description": self.describe_value(value),
                    "normalized_value": self.normalize(value),
                }
                for value in suggestions
            ],
        }


@dataclass(slots=True)
class VariableInstance:
    coordinates: dict[str, float]
    name_id: int
    postscript_name_id: int | None
    names_by_language: dict[str, str]
    postscript_name: str | None

    @property
    def available_languages(self) -> tuple[str, ...]:
        return tuple(sorted(_normalize_language_code(language) for language in self.names_by_language))

    @property
    def label(self) -> str:
        return self.name() or self.postscript_name or "Unnamed Instance"

    def name(self, language: str | tuple[str, ...] = "en") -> str | None:
        return _best_localized_name(self.names_by_language, language)

    def localization_resolution(
        self,
        language: str | tuple[str, ...] = "en",
    ) -> LocalizationResolution:
        resolved = _localization_resolution(self.names_by_language, language)
        if resolved.selected_label is not None:
            return resolved
        fallback_label = self.postscript_name or "Unnamed Instance"
        return LocalizationResolution(
            requested_languages=resolved.requested_languages,
            preference_chain=resolved.preference_chain,
            selected_language=None,
            selected_label=fallback_label,
            fallback_reason="postscript-or-default",
        )

    def localization_coverage(
        self,
        language: str | tuple[str, ...] = "en",
    ) -> LocalizationCoverage:
        return _localization_coverage(self.names_by_language, language)

    def localized_labels(
        self,
        preferred_languages: str | tuple[str, ...] = (),
    ) -> tuple[tuple[str, str], ...]:
        return _ordered_localizations(self.names_by_language, preferred_languages)

    def requested_language_hints(
        self,
        language: str | tuple[str, ...] = "en",
    ) -> tuple[RequestedLanguageHint, ...]:
        return _requested_language_hints(self.names_by_language, language)

    def language_profiles(
        self,
        language: str | tuple[str, ...] = "en",
    ) -> tuple[LanguageProfile, ...]:
        return build_language_profiles(
            self.names_by_language,
            language,
            fallback_label=self.postscript_name or "Unnamed Instance",
            fallback_reason="postscript-or-default",
        )

    def format_coordinates(
        self,
        axes: dict[str, VariableAxis] | tuple[VariableAxis, ...] | list[VariableAxis],
        *,
        language: str | tuple[str, ...] = "en",
        include_tags: bool = False,
    ) -> tuple[str, ...]:
        axis_map = axes if isinstance(axes, dict) else {axis.tag: axis for axis in axes}
        items: list[str] = []
        for tag, value in sorted(self.coordinates.items()):
            axis = axis_map.get(tag)
            if axis is None:
                items.append(f"{tag}={value:g}")
                continue
            label = axis.name(language) or axis.label
            prefix = f"{label} [{tag}]" if include_tags else label
            items.append(f"{prefix}={axis.describe_value(value)}")
        return tuple(items)

    def css_variation_settings(
        self,
        axes: dict[str, VariableAxis] | tuple[VariableAxis, ...] | list[VariableAxis],
    ) -> tuple[str, ...]:
        axis_map = axes if isinstance(axes, dict) else {axis.tag: axis for axis in axes}
        settings: list[str] = []
        for tag, value in sorted(self.coordinates.items()):
            axis = axis_map.get(tag)
            if axis is None:
                numeric = int(value) if float(value).is_integer() else value
                settings.append(f"'{tag}' {numeric}")
                continue
            settings.append(axis.css_variation_setting(value))
        return tuple(settings)

    def to_presentation(
        self,
        axes: dict[str, VariableAxis] | tuple[VariableAxis, ...] | list[VariableAxis],
        *,
        language: str | tuple[str, ...] = "en",
        include_tags: bool = True,
    ) -> dict[str, object]:
        formatted_coordinates = self.format_coordinates(
            axes,
            language=language,
            include_tags=False,
        )
        css_settings = self.css_variation_settings(axes)
        presentation: dict[str, object] = {
            "name_id": self.name_id,
            "postscript_name_id": self.postscript_name_id,
            "label": self.name(language) or self.label,
            "postscript_name": self.postscript_name,
            "localization": self.localization_resolution(language).to_dict(),
            "localization_coverage": self.localization_coverage(language).to_dict(),
            "available_languages": list(self.available_languages),
            "localized_labels": [
                {"language": item_language, "label": label}
                for item_language, label in self.localized_labels(language)
            ],
            "requested_language_hints": [
                hint.to_dict() for hint in self.requested_language_hints(language)
            ],
            "language_profiles": [
                profile.to_dict() for profile in self.language_profiles(language)
            ],
            "coordinates": dict(sorted(self.coordinates.items())),
            "formatted_coordinates": list(formatted_coordinates),
            "css_variation_settings": ", ".join(css_settings),
            "css_variation_setting_entries": list(css_settings),
        }
        if include_tags:
            presentation["tagged_coordinates"] = list(
                self.format_coordinates(
                    axes,
                    language=language,
                    include_tags=True,
                )
            )
        return presentation
