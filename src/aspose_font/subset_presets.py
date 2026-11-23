"""Preset Unicode selections for human-friendly subsetting workflows."""

from __future__ import annotations

from types import MappingProxyType

SUBSET_PRESETS = MappingProxyType(
    {
        "latin": (
            (0x0000, 0x00FF),
        ),
        "latin-ext": (
            (0x0100, 0x024F),
            (0x1E00, 0x1EFF),
        ),
        "cyrillic": (
            (0x0400, 0x04FF),
            (0x0500, 0x052F),
            (0x2DE0, 0x2DFF),
            (0xA640, 0xA69F),
        ),
        "greek": (
            (0x0370, 0x03FF),
            (0x1F00, 0x1FFF),
        ),
        "hebrew": (
            (0x0590, 0x05FF),
            (0xFB1D, 0xFB4F),
        ),
        "arabic": (
            (0x0600, 0x06FF),
            (0x0750, 0x077F),
            (0x08A0, 0x08FF),
            (0xFB50, 0xFDFF),
            (0xFE70, 0xFEFF),
        ),
        "devanagari": (
            (0x0900, 0x097F),
            (0xA8E0, 0xA8FF),
        ),
        "thai": (
            (0x0E00, 0x0E7F),
        ),
    }
)


def available_subset_presets() -> tuple[str, ...]:
    return tuple(SUBSET_PRESETS)


def codepoints_for_preset(name: str) -> set[int]:
    try:
        ranges = SUBSET_PRESETS[name]
    except KeyError as exc:
        available = ", ".join(available_subset_presets())
        raise ValueError(f"Unknown subset preset {name!r}. Available presets: {available}") from exc
    return expand_unicode_ranges(ranges)


def codepoints_for_presets(names: str | list[str] | tuple[str, ...] | set[str]) -> set[int]:
    if isinstance(names, str):
        normalized = (names,)
    else:
        normalized = tuple(names)
    codepoints: set[int] = set()
    for name in normalized:
        codepoints.update(codepoints_for_preset(name))
    return codepoints


def expand_unicode_ranges(
    ranges: tuple[tuple[int, int], ...] | list[tuple[int, int]] | tuple[range, ...] | list[range],
) -> set[int]:
    codepoints: set[int] = set()
    for item in ranges:
        if isinstance(item, range):
            start = item.start
            stop = item.stop - 1
        else:
            start, stop = item
        if start > stop:
            raise ValueError(f"Invalid Unicode range: start {start} is greater than end {stop}")
        codepoints.update(range(start, stop + 1))
    return codepoints
