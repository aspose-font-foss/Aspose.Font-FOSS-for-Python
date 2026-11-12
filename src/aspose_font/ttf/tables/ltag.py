"""OpenType ltag (Language Tag) table parser."""

from __future__ import annotations

from dataclasses import dataclass

from aspose_font._exceptions import FontParseException
from aspose_font._io import BinaryReader


@dataclass
class LtagTable:
    """OpenType ltag table parser.

    Stores BCP-47 language tag strings used for multilingual font metadata.
    """

    major_version: int
    minor_version: int
    tags: list[str]
    _raw: bytes

    @classmethod
    def from_reader(cls, r: BinaryReader, length: int) -> "LtagTable":
        """Parse ltag table from binary reader.

        Args:
            r: BinaryReader positioned at start of ltag table.
            length: Total table length in bytes.

        Returns:
            Parsed LtagTable instance.

        Raises:
            FontParseException: If table version is unsupported or parsing fails.
        """
        raw = r.read_bytes(length)
        rr = BinaryReader(raw)

        major_version = rr.read_u16()
        minor_version = rr.read_u16()

        if (major_version, minor_version) != (1, 0):
            raise FontParseException(
                f"Unsupported ltag table version: {major_version}.{minor_version}",
                format_name="TTF",
            )

        count = rr.read_u16()

        if count == 0:
            return cls(
                major_version=major_version,
                minor_version=minor_version,
                tags=[],
                _raw=raw,
            )

        offsets: list[int] = []
        for _ in range(count):
            offsets.append(rr.read_u16())

        tags: list[str] = []
        for offset in offsets:
            rr.seek(offset)
            tag = _read_bcp47_tag(rr)
            tags.append(tag)

        return cls(
            major_version=major_version,
            minor_version=minor_version,
            tags=tags,
            _raw=raw,
        )

    def to_bytes(self) -> bytes:
        """Serialize ltag table to binary data."""
        return self._raw

    def get_language_tag(self, tag_index: int) -> str:
        """Return BCP-47 language tag for given index.

        Args:
            tag_index: Zero-based index of the language tag.

        Returns:
            BCP-47 language tag string.

        Raises:
            IndexError: If tag_index is out of range.
        """
        return self.tags[tag_index]

    def __len__(self) -> int:
        """Return number of language tags."""
        return len(self.tags)


def _read_bcp47_tag(rr: BinaryReader) -> str:
    """Read a single BCP-47 language tag (null-terminated UTF-8 string).

    Args:
        rr: BinaryReader positioned at start of string.

    Returns:
        Decoded language tag string.
    """
    parts: list[str] = []
    while True:
        byte = rr.read_u8()
        if byte == 0:
            break
        parts.append(chr(byte))
    return "".join(parts)
