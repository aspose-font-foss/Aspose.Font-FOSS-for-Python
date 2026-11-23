"""OpenType meta (Metadata) table parser."""

from __future__ import annotations

from dataclasses import dataclass

from aspose_font._exceptions import FontParseException
from aspose_font._io import BinaryReader


@dataclass
class MetaTable:
    """OpenType meta table parser.

    Stores various metadata values identified by four-character tags.
    Supports dlng (design languages), slng (supported languages), appl, bild, and custom tags.
    """

    major_version: int
    minor_version: int
    flags: int
    data_maps: dict[str, bytes]
    _raw: bytes

    @classmethod
    def from_reader(cls, r: BinaryReader, length: int) -> "MetaTable":
        """Parse meta table from binary reader.

        Args:
            r: BinaryReader positioned at start of meta table.
            length: Total table length in bytes.

        Returns:
            Parsed MetaTable instance.

        Raises:
            FontParseException: If table version is unsupported or parsing fails.
        """
        if length < 16:
            raw = r.read_bytes(length)
            return cls(
                major_version=1,
                minor_version=0,
                flags=0,
                data_maps={},
                _raw=raw,
            )
        raw = r.read_bytes(length)
        rr = BinaryReader(raw)

        major_version = rr.read_u32()
        minor_version = rr.read_u32()
        flags = rr.read_u32()
        data_maps_count = rr.read_u32()

        if (major_version, minor_version) != (1, 0):
            raise FontParseException(
                f"Unsupported meta table version: {major_version}.{minor_version}",
                format_name="TTF",
            )

        if data_maps_count == 0:
            return cls(
                major_version=major_version,
                minor_version=minor_version,
                flags=flags,
                data_maps={},
                _raw=raw,
            )

        data_maps: dict[str, bytes] = {}
        for _ in range(data_maps_count):
            tag = rr.read_tag()
            data_offset = rr.read_u32()
            data_length = rr.read_u32()

            current_pos = rr.tell()
            rr.seek(data_offset)
            data = rr.read_bytes(data_length)
            data_maps[tag] = data
            rr.seek(current_pos)

        return cls(
            major_version=major_version,
            minor_version=minor_version,
            flags=flags,
            data_maps=data_maps,
            _raw=raw,
        )

    def to_bytes(self) -> bytes:
        """Serialize meta table to binary data."""
        return self._raw

    @property
    def design_languages(self) -> list[str]:
        """Return list of design language tags (decoded from dlng tag)."""
        dlng_data = self.data_maps.get("dlng")
        if dlng_data is None:
            return []
        try:
            text = dlng_data.decode("utf-8")
            return [tag.strip() for tag in text.split(",") if tag.strip()]
        except (UnicodeDecodeError, AttributeError):
            return []

    @property
    def supported_languages(self) -> list[str]:
        """Return list of supported language tags (decoded from slng tag)."""
        slng_data = self.data_maps.get("slng")
        if slng_data is None:
            return []
        try:
            text = slng_data.decode("utf-8")
            return [tag.strip() for tag in text.split(",") if tag.strip()]
        except (UnicodeDecodeError, AttributeError):
            return []

    def get_tag_data(self, tag: str) -> bytes | None:
        """Return raw data for given tag.

        Args:
            tag: Four-character tag name (e.g., 'dlng', 'slng', 'appl', 'bild', or custom).

        Returns:
            Raw bytes for the tag, or None if tag not found.
        """
        return self.data_maps.get(tag)

    def __len__(self) -> int:
        """Return number of data map entries."""
        return len(self.data_maps)
