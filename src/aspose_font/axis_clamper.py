"""Pure-Python Variable Font Axis Range Clamper Engine.

Provides a core engine that clamps variable-font axis values to a specified range,
returning a new Font object with the modified FVAR table.
"""

from __future__ import annotations

import copy
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aspose_font.ttf.font import TtfFont


def clamp_axis_range(
    font: "TtfFont",
    axis_tag: str,
    min_value: float,
    max_value: float,
) -> "TtfFont":
    """Return a new font with the specified axis constrained to [min_value, max_value].

    This function creates a deep copy of the input font, modifies the FVAR table entry
    for the specified axis, and returns a new TtfFont instance. All other axes remain
    unchanged. The modified font can be serialized with `font.to_bytes()` or saved
    with `font.save(path)`.

    Args:
        font: Input variable TTF font. Must have an FVAR table.
        axis_tag: 4-character axis tag (e.g., "wght", "wdth", "ital").
        min_value: New minimum value for the axis. Must be <= max_value.
        max_value: New maximum value for the axis. Must be >= min_value.

    Returns:
        New TtfFont with modified FVAR table. The returned font is independent
        of the original (no shared mutable state).

    Raises:
        ValueError: If axis_tag is not found in the font's FVAR table, or if
                   the font is not variable (no FVAR table).
        TypeError: If min_value or max_value cannot be converted to float.

    Example:
        >>> from aspose_font import FontLoader
        >>> font = FontLoader.open("example-variable.ttf")
        >>> # Clamp weight axis to 100-700 range
        >>> clamped = clamp_axis_range(font, "wght", 100.0, 700.0)
        >>> clamped.save("example-clamped.ttf")
    """
    if not font.is_variable:
        raise ValueError("Font is not variable (no FVAR table)")

    axes = font.axes
    matching_axes = [(i, ax) for i, ax in enumerate(axes) if ax.tag == axis_tag]

    if not matching_axes:
        raise ValueError(
            f"Axis '{axis_tag}' not found in font's FVAR table. "
            f"Available axes: {[ax.tag for ax in axes]}"
        )

    axis_idx, _ = matching_axes[0]

    min_val = float(min_value)
    max_val = float(max_value)

    if min_val > max_val:
        raise ValueError(
            f"min_value ({min_val}) must be <= max_value ({max_val})"
        )

    new_font = copy.deepcopy(font)

    if new_font.fvar is None:
        raise ValueError("Font reports as variable but has no FVAR table")

    axis_record = new_font.fvar.axes[axis_idx]
    axis_record.min_value = min_val
    axis_record.max_value = max_val

    new_font._variable_axes_cache = None

    return new_font
