"""Font library exception hierarchy. All exceptions importable from the top-level font package."""


class FontException(Exception):
    """Base class for all font library exceptions."""


class FontParseException(FontException):
    """Raised when binary font data cannot be parsed."""

    def __init__(self, message: str, offset: int = -1, format_name: str = "") -> None:
        self.offset = offset
        self.format_name = format_name
        location = f" at offset {offset}" if offset >= 0 else ""
        fmt = f" [{format_name}]" if format_name else ""
        super().__init__(f"{message}{fmt}{location}")


class FontConversionException(FontException):
    """Raised when font format conversion fails or is not supported."""


class FontNotSupportedException(FontException):
    """Raised for valid but unsupported font features (e.g. Multiple Master, CFF2 blends)."""


class GlyphNotFoundException(FontException):
    """Raised when a requested glyph ID or codepoint has no mapping in the font."""

    def __init__(self, glyph_id: int) -> None:
        self.glyph_id = glyph_id
        super().__init__(f"Glyph not found: GID {glyph_id}")


class UnsupportedFontFormatException(FontException):
    """Raised by FontLoader when the file magic bytes are not recognized."""
