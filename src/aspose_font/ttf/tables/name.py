"""TTF name table parser."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from aspose_font._io import BinaryReader, BinaryWriter

_WINDOWS_LANGUAGE_IDS = {
    0x0409: "en",
    0x0809: "en-gb",
    0x0419: "ru",
    0x0422: "uk",
    0x0407: "de",
    0x0413: "nl",
    0x040C: "fr",
    0x0410: "it",
    0x040A: "es",
    0x080A: "es-mx",
    0x0416: "pt-br",
    0x0816: "pt-pt",
    0x0415: "pl",
    0x0405: "cs",
    0x0406: "da",
    0x040B: "fi",
    0x041D: "sv",
    0x041F: "tr",
    0x040E: "hu",
    0x0414: "nb",
    0x0418: "ro",
    0x0411: "ja",
    0x0412: "ko",
    0x0804: "zh-hans",
    0x0404: "zh-hant",
    0x0C04: "zh-hk",
}

_MAC_LANGUAGE_IDS = {
    0: "en",
    1: "fr",
    2: "de",
    6: "es",
    8: "pt",
    9: "nb",
    10: "it",
    11: "ja",
    19: "zh-hant",
    23: "ko",
    32: "ru",
}


def _normalize_language_code(language: str) -> str:
    return language.strip().replace("_", "-").casefold()


def _language_preference_chain(preferred_languages: tuple[str, ...]) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for language in preferred_languages:
        if not language:
            continue
        normalized = _normalize_language_code(language)
        if normalized and normalized not in seen:
            ordered.append(normalized)
            seen.add(normalized)
        if "-" in normalized:
            base = normalized.split("-", 1)[0]
            if base and base not in seen:
                ordered.append(base)
                seen.add(base)
    if "en" not in seen:
        ordered.append("en")
    return ordered


@dataclass(slots=True)
class NameRecord:
    platform_id: int
    encoding_id: int
    language_id: int
    name_id: int
    value: str


@dataclass
class NameTable:
    records: list[NameRecord]
    _raw: bytes

    @staticmethod
    def language_key(platform_id: int, language_id: int) -> str:
        if platform_id == 3:
            return _WINDOWS_LANGUAGE_IDS.get(language_id, f"windows-{language_id:04x}")
        if platform_id == 1:
            return _MAC_LANGUAGE_IDS.get(language_id, f"mac-{language_id}")
        return f"platform{platform_id}-{language_id}"

    def get(self, name_id: int, platform_id: int = 3, encoding_id: int = 1) -> str | None:
        for record in self.records:
            if (
                record.name_id == name_id
                and record.platform_id == platform_id
                and record.encoding_id == encoding_id
            ):
                return record.value
        for record in self.records:
            if record.name_id == name_id:
                return record.value
        return None

    def records_for(self, name_id: int) -> list[NameRecord]:
        return [record for record in self.records if record.name_id == name_id]

    def localized_names(self, name_id: int) -> dict[str, str]:
        localized: dict[str, str] = {}
        for record in self.records_for(name_id):
            key = self.language_key(record.platform_id, record.language_id)
            localized.setdefault(key, record.value)
        return localized

    def best_name(self, name_id: int, preferred_languages: tuple[str, ...] = ("en",)) -> str | None:
        localized = self.localized_names(name_id)
        normalized = {
            _normalize_language_code(language): value
            for language, value in localized.items()
        }
        for language in _language_preference_chain(preferred_languages):
            value = normalized.get(language)
            if value:
                return value
            for candidate, candidate_value in normalized.items():
                if candidate.startswith(f"{language}-"):
                    return candidate_value
        if localized:
            return next(iter(localized.values()))
        return self.get(name_id)

    def replace_name(self, name_id: int, value: str) -> None:
        replaced = False
        for i, record in enumerate(self.records):
            if record.name_id == name_id:
                self.records[i] = NameRecord(
                    platform_id=record.platform_id,
                    encoding_id=record.encoding_id,
                    language_id=record.language_id,
                    name_id=record.name_id,
                    value=value,
                )
                replaced = True
        if not replaced:
            self.records.append(
                NameRecord(
                    platform_id=3,
                    encoding_id=1,
                    language_id=0x0409,
                    name_id=name_id,
                    value=value,
                )
            )

    def remove_name_ids(self, name_ids: Iterable[int]) -> None:
        remove_set = set(name_ids)
        self.records = [record for record in self.records if record.name_id not in remove_set]

    @classmethod
    def from_reader(cls, r: BinaryReader, table_length: int) -> "NameTable":
        raw = r.read_bytes(table_length)
        rr = BinaryReader(raw)
        rr.read_u16()  # format
        count = rr.read_u16()
        string_offset = rr.read_u16()
        rows = []
        for _ in range(count):
            rows.append(
                (
                    rr.read_u16(),
                    rr.read_u16(),
                    rr.read_u16(),
                    rr.read_u16(),
                    rr.read_u16(),
                    rr.read_u16(),
                )
            )

        records: list[NameRecord] = []
        for platform_id, encoding_id, language_id, name_id, length, offset in rows:
            start = string_offset + offset
            end = start + length
            string_bytes = raw[start:end]
            if platform_id == 3:
                value = string_bytes.decode("utf-16-be", errors="replace")
            elif platform_id == 1:
                try:
                    value = string_bytes.decode("mac_roman")
                except LookupError:
                    value = string_bytes.decode("latin-1", errors="replace")
            else:
                value = string_bytes.decode("latin-1", errors="replace")
            records.append(
                NameRecord(
                    platform_id=platform_id,
                    encoding_id=encoding_id,
                    language_id=language_id,
                    name_id=name_id,
                    value=value,
                )
            )

        return cls(records=records, _raw=raw)

    def to_bytes(self) -> bytes:
        w = BinaryWriter()
        encoded_records: list[tuple[NameRecord, bytes]] = []
        for record in self.records:
            if record.platform_id == 3:
                blob = record.value.encode("utf-16-be")
            elif record.platform_id == 1:
                blob = record.value.encode("latin-1", errors="replace")
            else:
                blob = record.value.encode("latin-1", errors="replace")
            encoded_records.append((record, blob))

        string_pool = bytearray()
        pool_offsets: dict[bytes, int] = {}
        rows: list[tuple[int, int, int, int, int, int]] = []
        for record, blob in encoded_records:
            off = pool_offsets.get(blob)
            if off is None:
                off = len(string_pool)
                string_pool.extend(blob)
                pool_offsets[blob] = off
            rows.append(
                (
                    record.platform_id,
                    record.encoding_id,
                    record.language_id,
                    record.name_id,
                    len(blob),
                    off,
                )
            )

        string_offset = 6 + len(rows) * 12
        w.write_u16(0)
        w.write_u16(len(rows))
        w.write_u16(string_offset)
        for platform_id, encoding_id, language_id, name_id, length, offset in rows:
            w.write_u16(platform_id)
            w.write_u16(encoding_id)
            w.write_u16(language_id)
            w.write_u16(name_id)
            w.write_u16(length)
            w.write_u16(offset)
        w.write_bytes(bytes(string_pool))
        return w.to_bytes()
