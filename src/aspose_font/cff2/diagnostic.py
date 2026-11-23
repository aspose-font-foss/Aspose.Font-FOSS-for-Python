"""CFF2 variable font diagnostics."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class Cff2DiagnosticAxis:
    """Single axis diagnostic record."""
    tag: str
    min_value: float
    default_value: float
    max_value: float
    name_id: int


@dataclass
class Cff2Diagnostic:
    """JSON-serializable CFF2 font diagnostic report."""
    font_name: str
    num_glyphs: int
    axes: list[Cff2DiagnosticAxis] = field(default_factory=list)
    has_fvar: bool = False
    sample_blend_result: float | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return dict suitable for JSON serialization."""
        return {
            "font_name": self.font_name,
            "num_glyphs": self.num_glyphs,
            "axes": [a.__dict__ for a in self.axes],
            "has_fvar": self.has_fvar,
            "sample_blend_result": self.sample_blend_result,
        }

    def to_json(self, path: str | Path) -> None:
        """Write diagnostic to JSON file."""
        import json
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)
