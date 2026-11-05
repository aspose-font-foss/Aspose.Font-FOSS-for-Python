"""Public value types for the font library API."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator

# ---------------------------------------------------------------------------
# Path commands
# ---------------------------------------------------------------------------

class PathCommand:
    """Abstract marker for all path command types."""
    __slots__ = ()


@dataclass(slots=True)
class MoveTo(PathCommand):
    x: float
    y: float


@dataclass(slots=True)
class LineTo(PathCommand):
    x: float
    y: float


@dataclass(slots=True)
class QuadraticTo(PathCommand):
    x1: float
    y1: float
    x: float
    y: float


@dataclass(slots=True)
class CurveTo(PathCommand):
    x1: float
    y1: float
    x2: float
    y2: float
    x: float
    y: float


@dataclass(slots=True)
class ClosePath(PathCommand):
    pass


# ---------------------------------------------------------------------------
# GlyphPath
# ---------------------------------------------------------------------------

class GlyphPath:
    """Ordered sequence of PathCommand objects representing one glyph's outline."""

    __slots__ = ("_commands",)

    def __init__(self, commands: list[PathCommand] | None = None) -> None:
        self._commands: list[PathCommand] = commands if commands is not None else []

    def append(self, cmd: PathCommand) -> None:
        self._commands.append(cmd)

    def extend(self, cmds: list[PathCommand]) -> None:
        self._commands.extend(cmds)

    def __iter__(self) -> Iterator[PathCommand]:
        return iter(self._commands)

    def __len__(self) -> int:
        return len(self._commands)

    def __repr__(self) -> str:
        return f"GlyphPath({self._commands!r})"


# ---------------------------------------------------------------------------
# GlyphId
# ---------------------------------------------------------------------------

@dataclass(slots=True, frozen=True)
class GlyphId:
    value: int

    def __post_init__(self) -> None:
        if self.value < 0:
            raise ValueError(f"GlyphId value must be >= 0, got {self.value}")

    def __index__(self) -> int:
        return self.value

    def __int__(self) -> int:
        return self.value


# ---------------------------------------------------------------------------
# Glyph
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class Glyph:
    glyph_id: GlyphId
    glyph_name: str | None
    path: GlyphPath | None
    advance_width: int = 0
    lsb: int = 0


# ---------------------------------------------------------------------------
# KernPair
# ---------------------------------------------------------------------------

@dataclass(slots=True, frozen=True)
class KernPair:
    left: GlyphId
    right: GlyphId
    value: int  # kern adjustment in font units (positive = wider, negative = tighter)


# ---------------------------------------------------------------------------
# FontMetrics
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class FontMetrics:
    units_per_em: int
    ascender: int
    descender: int
    line_gap: int
    advance_width_max: int
    underline_position: int
    underline_thickness: int
