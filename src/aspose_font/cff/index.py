"""CFF INDEX structure parser/serializer."""

from __future__ import annotations

from typing import Iterator

from aspose_font._exceptions import FontParseException
from aspose_font._io import BinaryReader, BinaryWriter


class CffIndex:
    def __init__(self, items: list[bytes]) -> None:
        self._items = tuple(items)

    def __len__(self) -> int:
        return len(self._items)

    def __getitem__(self, i: int) -> bytes:
        return self._items[i]

    def __iter__(self) -> Iterator[bytes]:
        return iter(self._items)

    @classmethod
    def from_reader(cls, r: BinaryReader) -> "CffIndex":
        count = r.read_u16()
        if count == 0:
            return cls([])

        off_size = r.read_u8()
        if off_size not in (1, 2, 3, 4):
            raise FontParseException(f"Invalid CFF offSize: {off_size}")

        offsets = [int.from_bytes(r.read_bytes(off_size), "big") for _ in range(count + 1)]
        data_len = offsets[-1] - 1
        if data_len < 0:
            raise FontParseException("CFF INDEX offset out of range")

        data = r.read_bytes(data_len)
        items: list[bytes] = []
        for i in range(count):
            start = offsets[i] - 1
            end = offsets[i + 1] - 1
            if start < 0 or end < start or end > len(data):
                raise FontParseException("CFF INDEX offset out of range")
            items.append(data[start:end])
        return cls(items)

    def to_bytes(self) -> bytes:
        w = BinaryWriter()
        count = len(self._items)
        w.write_u16(count)
        if count == 0:
            return w.to_bytes()

        payload = b"".join(self._items)
        max_offset = len(payload) + 1
        if max_offset <= 0xFF:
            off_size = 1
        elif max_offset <= 0xFFFF:
            off_size = 2
        elif max_offset <= 0xFFFFFF:
            off_size = 3
        else:
            off_size = 4

        w.write_u8(off_size)
        offset = 1
        for item in self._items:
            w.write_bytes(offset.to_bytes(off_size, "big"))
            offset += len(item)
        w.write_bytes(offset.to_bytes(off_size, "big"))
        w.write_bytes(payload)
        return w.to_bytes()
