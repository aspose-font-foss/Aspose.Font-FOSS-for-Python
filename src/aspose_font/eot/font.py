"""Embedded OpenType (EOT) parser and wrapper font type."""

from __future__ import annotations

from dataclasses import dataclass

from aspose_font._exceptions import FontParseException
from aspose_font._font_base import Font, FontEncoding, FontType, GlyphAccessor
from aspose_font._io import BinaryReader
from aspose_font._types import FontMetrics, KernPair
from aspose_font.ttf.font import TtfFont

_EOT_MIN_HEADER_SIZE = 82
_EOT_MAGIC = 0x504C


@dataclass(slots=True)
class EotHeader:
    eot_size: int
    font_data_size: int
    version: int
    flags: int
    magic: int
    charset: int
    italic: int
    weight: int
    fs_type: int
    payload_offset: int


def _parse_eot_header(data: bytes) -> EotHeader:
    if len(data) < _EOT_MIN_HEADER_SIZE:
        raise FontParseException("Invalid EOT header")

    eot_size = int.from_bytes(data[0:4], "little")
    font_data_size = int.from_bytes(data[4:8], "little")
    version = int.from_bytes(data[8:12], "little")
    flags = int.from_bytes(data[12:16], "little")
    charset = data[26]
    italic = data[27]
    weight = int.from_bytes(data[28:32], "little")
    fs_type = int.from_bytes(data[32:34], "little")
    magic = int.from_bytes(data[34:36], "little")
    payload_offset = _EOT_MIN_HEADER_SIZE

    if magic != _EOT_MAGIC:
        raise FontParseException("Invalid EOT magic")

    if eot_size != len(data):
        raise FontParseException("Invalid EOT size fields")
    if font_data_size <= 0:
        raise FontParseException("Invalid EOT size fields")
    if payload_offset + font_data_size > len(data):
        raise FontParseException("Invalid EOT size fields")

    return EotHeader(
        eot_size=eot_size,
        font_data_size=font_data_size,
        version=version,
        flags=flags,
        magic=magic,
        charset=charset,
        italic=italic,
        weight=weight,
        fs_type=fs_type,
        payload_offset=payload_offset,
    )


class EotFont(Font):
    """Embedded OpenType (EOT) wrapper over an inner TrueType/OpenType font.

    This class exposes the standard :class:`~aspose_font._font_base.Font` interface by
    delegating metadata, encoding, glyph access, and metrics to the embedded sfnt payload.

    Example:
        >>> from aspose_font import FontLoader, FontType
        >>> font = FontLoader.open("testdata/saira-extracondensed-semibold.eot")
        >>> font.font_type == FontType.EOT
        True
    """

    def __init__(
        self,
        inner: TtfFont,
        *,
        eot_version: int = 0x00020001,
        flags: int = 0,
        charset: int = 1,
        italic: int = 0,
        weight: int = 400,
        fs_type: int = 0,
    ) -> None:
        """Create an EOT wrapper around an inner sfnt font.

        Args:
            inner: Parsed inner sfnt font payload.
            eot_version: EOT header version field.
            flags: EOT header flags.
            charset: EOT charset byte.
            italic: EOT italic byte.
            weight: EOT weight field.
            fs_type: EOT fsType field.
        """
        self._inner = inner
        self._eot_version = int(eot_version) & 0xFFFFFFFF
        self._flags = int(flags) & 0xFFFFFFFF
        self._charset = int(charset) & 0xFF
        self._italic = int(italic) & 0xFF
        self._weight = int(weight) & 0xFFFFFFFF
        self._fs_type = int(fs_type) & 0xFFFF

    @classmethod
    def _from_reader(cls, r: BinaryReader) -> "EotFont":
        """Parse an EOT font from a binary reader.

        Raises:
            FontParseException: If the EOT header or embedded sfnt payload is invalid.
        """
        data = r.read_bytes(r.remaining())
        header = _parse_eot_header(data)
        sfnt = data[header.payload_offset : header.payload_offset + header.font_data_size]
        try:
            inner = TtfFont._from_reader(BinaryReader(sfnt))
        except FontParseException as exc:
            raise FontParseException("Invalid EOT embedded sfnt") from exc
        except Exception as exc:  # pragma: no cover - defensive guard
            raise FontParseException("Invalid EOT embedded sfnt") from exc
        return cls(
            inner=inner,
            eot_version=header.version,
            flags=header.flags,
            charset=header.charset,
            italic=header.italic,
            weight=header.weight,
            fs_type=header.fs_type,
        )

    @property
    def font_type(self) -> FontType:
        return FontType.EOT

    @property
    def inner_font(self) -> TtfFont:
        return self._inner

    @property
    def font_name(self) -> str:
        return self._inner.font_name

    @property
    def font_family(self) -> str:
        return self._inner.font_family

    @property
    def font_style(self) -> str:
        return self._inner.font_style

    @property
    def num_glyphs(self) -> int:
        return self._inner.num_glyphs

    @property
    def metrics(self) -> FontMetrics:
        return self._inner.metrics

    @property
    def encoding(self) -> FontEncoding:
        return self._inner.encoding

    @property
    def glyph_accessor(self) -> GlyphAccessor:
        return self._inner.glyph_accessor

    @property
    def eot_version(self) -> int:
        return self._eot_version

    @property
    def flags(self) -> int:
        return self._flags

    @property
    def charset(self) -> int:
        return self._charset

    @property
    def italic(self) -> int:
        return self._italic

    @property
    def weight(self) -> int:
        return self._weight

    @property
    def fs_type(self) -> int:
        return self._fs_type

    def get_kern_pairs(self) -> list[KernPair]:
        return self._inner.get_kern_pairs()

    def to_bytes(self, font_type: FontType | None = None) -> bytes:
        """Serialize this font as EOT bytes or delegate cross-format conversion.

        Args:
            font_type: Optional target format. If provided and not EOT, conversion is delegated
                to the base ``Font`` implementation.
        """
        if font_type is not None and font_type != self.font_type:
            return super().to_bytes(font_type)
        from aspose_font.serializer import EotSerializer

        return EotSerializer.serialize(self)
