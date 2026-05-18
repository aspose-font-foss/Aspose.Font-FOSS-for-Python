"""Abstract base classes and FontType enum for the font library."""

from __future__ import annotations

import enum
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from aspose_font._types import FontMetrics, Glyph, GlyphId, KernPair

if TYPE_CHECKING:
    pass


class FontType(enum.Enum):
    TTF = "TTF"
    OTF = "OTF"
    CFF = "CFF"
    TYPE1 = "TYPE1"
    TYPE1_PFA = "TYPE1_PFA"
    WOFF = "WOFF"
    WOFF2 = "WOFF2"
    EOT = "EOT"


class FontEncoding(ABC):
    """Maps Unicode codepoints to glyph IDs."""

    @abstractmethod
    def unicode_to_gid(self, codepoint: int) -> GlyphId: ...

    @abstractmethod
    def get_all_codepoints(self) -> list[int]: ...


class GlyphAccessor(ABC):
    """Retrieves glyphs by ID or Unicode codepoint."""

    def __init__(self, encoding: FontEncoding) -> None:
        self._encoding = encoding

    @abstractmethod
    def get_glyph_by_id(self, gid: GlyphId) -> Glyph: ...

    def get_glyph_by_unicode(self, codepoint: int) -> Glyph:
        gid = self._encoding.unicode_to_gid(codepoint)
        return self.get_glyph_by_id(gid)

    def get_glyphs_for_text(self, text: str) -> list[Glyph]:
        return [self.get_glyph_by_unicode(ord(ch)) for ch in text]

    @abstractmethod
    def get_all_glyph_ids(self) -> list[GlyphId]: ...


class Font(ABC):
    """Abstract base for all font format implementations."""

    @property
    @abstractmethod
    def font_type(self) -> FontType: ...

    @property
    @abstractmethod
    def font_name(self) -> str: ...

    @property
    @abstractmethod
    def font_family(self) -> str: ...

    @property
    @abstractmethod
    def font_style(self) -> str: ...

    @property
    @abstractmethod
    def num_glyphs(self) -> int: ...

    @property
    @abstractmethod
    def metrics(self) -> FontMetrics: ...

    @property
    @abstractmethod
    def encoding(self) -> FontEncoding: ...

    @property
    @abstractmethod
    def glyph_accessor(self) -> GlyphAccessor: ...

    # ------------------------------------------------------------------
    # Serialization (implemented in SPEC-008 / ADR-009)
    # ------------------------------------------------------------------

    def save(self, path: str) -> None:
        data = self.to_bytes()
        with open(path, "wb") as f:
            f.write(data)

    def to_bytes(self, font_type: FontType | None = None) -> bytes:
        if font_type is not None and font_type != self.font_type:
            return self.convert(font_type).to_bytes()
        raise NotImplementedError(f"to_bytes not implemented for {type(self).__name__}")

    def save_to_format(self, font_type: FontType, path: str) -> None:
        converted = self.convert(font_type)
        converted.save(path)

    def get_kern_pairs(self) -> list[KernPair]:
        """Return all kern pairs for this font. Default: empty list."""
        return []

    def convert(self, target: FontType) -> Font:
        # Deferred import to break circular dependency with converter.py  # See ADR-002
        from aspose_font.converter import FontConverter
        return FontConverter.convert(self, target)
