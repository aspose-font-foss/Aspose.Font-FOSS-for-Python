"""Font loading facade with auto-detection and source metadata helpers."""

from __future__ import annotations

import io
import os
from dataclasses import dataclass

from aspose_font._exceptions import UnsupportedFontFormatException
from aspose_font._font_base import Font, FontType
from aspose_font._io import BinaryReader
from aspose_font.ttf.collection import is_ttc, slice_ttc_face

# Map of 4-byte (or 2-byte) magic -> FontType.
# Shorter signatures are padded to avoid ambiguity; detection reads 4 bytes.
_SIGNATURES: dict[bytes, FontType] = {
    b"\x00\x01\x00\x00": FontType.TTF,
    b"OTTO": FontType.OTF,
    b"true": FontType.TTF,   # Mac TrueType
    b"typ1": FontType.TTF,   # older Mac TrueType
    b"wOFF": FontType.WOFF,  # 0x774F4646
    b"wOF2": FontType.WOFF2, # 0x774F4632
    b"%!PS": FontType.TYPE1, # PFA: %!PS-AdobeFont-...
}

# PFB starts with 0x80 0x01 - only 2 meaningful bytes; matched separately.
_PFB_MAGIC = b"\x80\x01"
_EOT_MIN_HEADER_SIZE = 82
_EOT_MAGIC = 0x504C


@dataclass(frozen=True, slots=True)
class FontSourceInfo:
    """Describe the origin of loaded bytes."""

    kind: str
    label: str
    size: int
    path: str | None = None
    stream_name: str | None = None
    collection_index: int | None = None
    collection_size: int | None = None

    @property
    def is_path(self) -> bool:
        return self.kind == "path"

    @property
    def is_bytes(self) -> bool:
        return self.kind == "bytes"

    @property
    def is_stream(self) -> bool:
        return self.kind == "stream"


@dataclass(frozen=True, slots=True)
class LoadedFont:
    """Friendly loader result that wraps a font plus source metadata."""

    font: Font
    source: FontSourceInfo
    detected_font_type: FontType
    requested_font_type: FontType | None = None

    def __getattr__(self, name: str) -> object:
        return getattr(self.font, name)

    @property
    def is_variable(self) -> bool:
        return bool(getattr(self.font, "is_variable", False))

    @property
    def is_static(self) -> bool:
        return not self.is_variable

    def unwrap(self) -> Font:
        return self.font


class FontLoader:
    @staticmethod
    def open(
        source: str | os.PathLike[str] | bytes | io.IOBase,
        font_type: FontType | None = None,
        *,
        collection_index: int | None = None,
    ) -> Font:
        """Load a font from a file path, raw bytes, or stream."""
        return FontLoader.load(source, font_type=font_type, collection_index=collection_index).font

    @staticmethod
    def load(
        source: str | os.PathLike[str] | bytes | io.IOBase,
        font_type: FontType | None = None,
        *,
        collection_index: int | None = None,
    ) -> LoadedFont:
        """Load a font and keep friendly metadata about where it came from."""
        data = FontLoader._to_bytes(source)
        font_data = data
        resolved_collection_index: int | None = None
        collection_size: int | None = None

        if is_ttc(data):
            resolved_collection_index = 0 if collection_index is None else collection_index
            font_data, collection_size = slice_ttc_face(data, resolved_collection_index)
        elif collection_index is not None:
            raise UnsupportedFontFormatException("collection_index is only supported for TTC sources")

        detected = (
            font_type
            if font_type is not None
            else FontLoader._detect_with_source(source, font_data)
        )
        font = FontLoader._dispatch(detected, font_data)
        return LoadedFont(
            font=font,
            source=FontLoader._describe_source(
                source,
                data,
                collection_index=resolved_collection_index,
                collection_size=collection_size,
            ),
            detected_font_type=detected,
            requested_font_type=font_type,
        )

    @staticmethod
    def _to_bytes(source: str | os.PathLike[str] | bytes | io.IOBase) -> bytes:
        if isinstance(source, (str, os.PathLike)):
            with open(os.fspath(source), "rb") as f:
                return f.read()
        if isinstance(source, (bytes, bytearray)):
            return bytes(source)
        if not isinstance(source, io.IOBase):
            raise UnsupportedFontFormatException(f"Unsupported source type: {type(source).__name__}")

        data = source.read()
        if not isinstance(data, (bytes, bytearray)):
            raise UnsupportedFontFormatException("Font source stream must provide bytes")
        return bytes(data)

    @staticmethod
    def _describe_source(
        source: str | os.PathLike[str] | bytes | io.IOBase,
        data: bytes,
        *,
        collection_index: int | None = None,
        collection_size: int | None = None,
    ) -> FontSourceInfo:
        if isinstance(source, (str, os.PathLike)):
            path = os.fspath(source)
            return FontSourceInfo(
                kind="path",
                label=FontLoader._with_collection_suffix(path, collection_index),
                size=len(data),
                path=path,
                collection_index=collection_index,
                collection_size=collection_size,
            )
        if isinstance(source, (bytes, bytearray)):
            label = FontLoader._with_collection_suffix(f"<bytes:{len(data)}>", collection_index)
            return FontSourceInfo(
                kind="bytes",
                label=label,
                size=len(data),
                collection_index=collection_index,
                collection_size=collection_size,
            )

        stream_name = getattr(source, "name", None)
        if not isinstance(stream_name, str):
            stream_name = None
        label = stream_name if stream_name else f"<stream:{type(source).__name__}>"
        return FontSourceInfo(
            kind="stream",
            label=FontLoader._with_collection_suffix(label, collection_index),
            size=len(data),
            stream_name=stream_name,
            collection_index=collection_index,
            collection_size=collection_size,
        )

    @staticmethod
    def _with_collection_suffix(label: str, collection_index: int | None) -> str:
        if collection_index is None:
            return label
        return f"{label}#{collection_index}"

    @staticmethod
    def _detect(data: bytes) -> FontType:
        if len(data) < 2:
            raise UnsupportedFontFormatException("Font data too short to detect format")

        magic4 = data[:4]
        magic2 = data[:2]

        if magic2 == _PFB_MAGIC:
            return FontType.TYPE1

        if magic4 in _SIGNATURES:
            return _SIGNATURES[magic4]

        if len(data) >= _EOT_MIN_HEADER_SIZE:
            eot_magic = int.from_bytes(data[34:36], "little")
            if eot_magic == _EOT_MAGIC:
                eot_size = int.from_bytes(data[0:4], "little")
                font_data_size = int.from_bytes(data[4:8], "little")
                if eot_size == len(data) and 0 < font_data_size < len(data):
                    return FontType.EOT

        # Standalone CFF: major version 1, minor version 0
        if len(data) >= 2 and magic2[0] == 1 and magic2[1] == 0:
            return FontType.CFF

        raise UnsupportedFontFormatException(
            f"Unrecognised font format (magic bytes: {data[:4].hex()})"
        )

    @staticmethod
    def _detect_with_source(
        source: str | os.PathLike[str] | bytes | io.IOBase,
        data: bytes,
    ) -> FontType:
        if isinstance(source, (str, os.PathLike)):
            source_path = os.fspath(source).lower()
            # Path-based .cff files in this project may be wrapped in a PS container.
            if source_path.endswith(".cff"):
                return FontType.CFF
            if source_path.endswith(".eot"):
                return FontType.EOT
        return FontLoader._detect(data)

    @staticmethod
    def _dispatch(font_type: FontType, data: bytes) -> Font:
        reader = BinaryReader(data)
        if font_type in (FontType.TTF, FontType.OTF):
            from aspose_font.ttf.font import TtfFont

            return TtfFont._from_reader(reader, font_type=font_type)
        if font_type == FontType.CFF:
            from aspose_font.cff.font import CffFont

            return CffFont._from_bytes(data)
        if font_type in (FontType.TYPE1, FontType.TYPE1_PFA):
            from aspose_font.type1.font import Type1Font

            return Type1Font._from_source(data)
        if font_type == FontType.WOFF:
            from aspose_font.woff.woff1 import WoffFont

            return WoffFont._from_reader(reader)
        if font_type == FontType.WOFF2:
            from aspose_font.woff.woff2 import Woff2Font

            return Woff2Font._from_reader(reader)
        if font_type == FontType.EOT:
            from aspose_font.eot.font import EotFont

            return EotFont._from_reader(reader)
        raise UnsupportedFontFormatException(f"Unsupported font type: {font_type}")
