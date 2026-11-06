"""Tests for the font exception hierarchy."""



class TestExceptionImportability:
    def test_all_importable_from_font(self):
        from aspose_font import (
            FontConversionException,
            FontException,
            FontNotSupportedException,
            FontParseException,
            GlyphNotFoundException,
            UnsupportedFontFormatException,
        )
        assert issubclass(FontParseException, FontException)
        assert issubclass(FontConversionException, FontException)
        assert issubclass(FontNotSupportedException, FontException)
        assert issubclass(GlyphNotFoundException, FontException)
        assert issubclass(UnsupportedFontFormatException, FontException)

    def test_font_exception_is_exception(self):
        from aspose_font import FontException
        assert issubclass(FontException, Exception)


class TestFontParseException:
    def test_message_only(self):
        from aspose_font import FontParseException
        exc = FontParseException("bad data")
        assert "bad data" in str(exc)
        assert exc.offset == -1
        assert exc.format_name == ""

    def test_with_offset(self):
        from aspose_font import FontParseException
        exc = FontParseException("unexpected EOF", offset=42)
        assert "42" in str(exc)
        assert exc.offset == 42

    def test_with_format_name(self):
        from aspose_font import FontParseException
        exc = FontParseException("bad table", format_name="TTF")
        assert "TTF" in str(exc)
        assert exc.format_name == "TTF"

    def test_full_message(self):
        from aspose_font import FontParseException
        exc = FontParseException("bad table", offset=10, format_name="CFF")
        msg = str(exc)
        assert "bad table" in msg
        assert "CFF" in msg
        assert "10" in msg


class TestGlyphNotFoundException:
    def test_message_contains_glyph_id(self):
        from aspose_font import GlyphNotFoundException
        exc = GlyphNotFoundException(glyph_id=99)
        assert "99" in str(exc)
        assert exc.glyph_id == 99

    def test_is_font_exception(self):
        from aspose_font import FontException, GlyphNotFoundException
        exc = GlyphNotFoundException(glyph_id=0)
        assert isinstance(exc, FontException)
