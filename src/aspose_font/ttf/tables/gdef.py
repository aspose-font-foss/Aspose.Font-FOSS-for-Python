"""TTF GDEF table parser (Glyph Definition)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from aspose_font._io import BinaryReader


@dataclass(slots=True)
class _ClassDefinitionTable:
    format: int
    glyph_indices: list[int]
    range_records: Optional[list[tuple[int, int, int]]] = None

    def get_class(self, glyph_id: int) -> int:
        """Return the class value for a glyph ID."""
        gid = int(glyph_id)
        if self.format == 1:
            if gid < len(self.glyph_indices):
                return self.glyph_indices[gid]
            return 0
        elif self.format == 2:
            if self.range_records is not None:
                for start, end, class_value in self.range_records:
                    if start <= gid <= end:
                        return class_value
            return 0
        return 0


@dataclass(slots=True)
class _AttachmentPointList:
    attachment_point_count: int
    attachment_points: list[tuple[int, list[int]]]


@dataclass(slots=True)
class _CaretValue:
    format: int
    value: int
    contour_point: Optional[int] = None
    device_table_offset: Optional[int] = None


@dataclass(slots=True)
class _LigatureCaretList:
    caret_count: int
    caret_values: list[_CaretValue]


@dataclass
class GdefTable:
    version: int
    glyph_class_def_offset: int
    attachment_point_list_offset: int
    ligature_caret_list_offset: int
    mark_attachment_class_def_offset: int
    glyph_class_def: Optional[_ClassDefinitionTable] = None
    attachment_point_list: Optional[_AttachmentPointList] = None
    ligature_caret_list: Optional[_LigatureCaretList] = None
    mark_attachment_class_def: Optional[_ClassDefinitionTable] = None
    _raw: bytes = field(default_factory=bytes)

    @classmethod
    def from_reader(cls, r: BinaryReader, table_length: int) -> "GdefTable":
        raw = r.read_bytes(table_length)
        rr = BinaryReader(raw)
        version = rr.read_u32()

        glyph_class_def_offset = rr.read_u16()
        attachment_point_list_offset = rr.read_u16()
        ligature_caret_list_offset = rr.read_u16()
        mark_attachment_class_def_offset = rr.read_u16()

        glyph_class_def = None
        if glyph_class_def_offset > 0:
            glyph_class_def = _parse_class_definition(rr, glyph_class_def_offset, raw)

        attachment_point_list = None
        if attachment_point_list_offset > 0:
            attachment_point_list = _parse_attachment_point_list(rr, attachment_point_list_offset, raw)

        ligature_caret_list = None
        if ligature_caret_list_offset > 0:
            ligature_caret_list = _parse_ligature_caret_list(rr, ligature_caret_list_offset, raw)

        mark_attachment_class_def = None
        if mark_attachment_class_def_offset > 0:
            mark_attachment_class_def = _parse_class_definition(
                rr, mark_attachment_class_def_offset, raw
            )

        return cls(
            version=version,
            glyph_class_def_offset=glyph_class_def_offset,
            attachment_point_list_offset=attachment_point_list_offset,
            ligature_caret_list_offset=ligature_caret_list_offset,
            mark_attachment_class_def_offset=mark_attachment_class_def_offset,
            glyph_class_def=glyph_class_def,
            attachment_point_list=attachment_point_list,
            ligature_caret_list=ligature_caret_list,
            mark_attachment_class_def=mark_attachment_class_def,
            _raw=raw,
        )

    def to_bytes(self) -> bytes:
        return self._raw

    def get_glyph_class(self, glyph_id: int) -> int:
        """Return glyph class (1=Base, 2=Ligature, 3=Mark, 4=Component, 0=Unassigned)."""
        if self.glyph_class_def is not None:
            return self.glyph_class_def.get_class(glyph_id)
        return 0

    def get_ligature_carets(self, glyph_id: int) -> list[int]:
        """Return list of caret coordinates for a ligature glyph."""
        if self.ligature_caret_list is None:
            return []

        gid = int(glyph_id)
        if gid < 0 or gid >= len(self.ligature_caret_list.caret_values):
            return []

        caret = self.ligature_caret_list.caret_values[gid]
        return self._parse_caret_value(caret)

    def get_attachment_points(self, glyph_id: int) -> list[int]:
        """Return list of attachment point indices for a glyph."""
        if self.attachment_point_list is None:
            return []

        for gp_glyph_index, gp_point_indices in self.attachment_point_list.attachment_points:
            if gp_glyph_index == glyph_id:
                return gp_point_indices
        return []

    def get_mark_attachment_class(self, glyph_id: int) -> int:
        """Return mark attachment class for a glyph."""
        if self.mark_attachment_class_def is not None:
            return self.mark_attachment_class_def.get_class(glyph_id)
        return 0

    def _parse_caret_value(self, caret: _CaretValue) -> list[int]:
        """Parse a CaretValue and return coordinate offsets."""
        if caret.format == 1:
            return [caret.value]
        elif caret.format == 2:
            return [caret.contour_point if caret.contour_point is not None else 0]
        elif caret.format == 3:
            if caret.device_table_offset is not None:
                device_data = self._raw[caret.device_table_offset:]
                if len(device_data) >= 6:
                    br = BinaryReader(device_data)
                    br.read_u16()  # start_size
                    br.read_u16()  # end_size
                    coord_count = br.read_u16()
                    coords = []
                    for _ in range(coord_count):
                        coords.append(br.read_u16())
                    return coords
            raise ValueError(f"Unknown CaretValue format: {caret.format}")
        else:
            raise ValueError(f"Unknown CaretValue format: {caret.format}")


def _parse_class_definition(
    r: BinaryReader, offset: int, raw: bytes
) -> _ClassDefinitionTable | None:
    pos = r.tell()
    r.seek(offset)

    if offset < 0 or offset + 2 > len(raw):
        r.seek(pos)
        return None

    try:
        fmt = r.read_u16()
        if fmt == 1:
            glyph_count = r.read_u16()
            if offset + 4 + glyph_count * 2 > len(raw):
                r.seek(pos)
                return None
            class_values = [r.read_u16() for _ in range(glyph_count)]
            r.seek(pos)
            return _ClassDefinitionTable(format=fmt, glyph_indices=class_values)
        elif fmt == 2:
            if offset + 4 > len(raw):
                r.seek(pos)
                return None
            range_count = r.read_u16()
            if offset + 4 + range_count * 6 > len(raw):
                r.seek(pos)
                return None
            range_records: list[tuple[int, int, int]] = []
            for _ in range(range_count):
                start = r.read_u16()
                end = r.read_u16()
                class_value = r.read_u16()
                range_records.append((start, end, class_value))
            r.seek(pos)
            return _ClassDefinitionTable(
                format=fmt, glyph_indices=[], range_records=range_records
            )
        else:
            r.seek(pos)
            return None
    except Exception:
        r.seek(pos)
        return None


def _parse_attachment_point_list(
    r: BinaryReader, offset: int, raw: bytes
) -> _AttachmentPointList | None:
    pos = r.tell()
    r.seek(offset)

    if offset < 0 or offset + 2 > len(raw):
        r.seek(pos)
        return None

    try:
        attachment_point_count = r.read_u16()

        if offset + 2 + attachment_point_count * 4 > len(raw):
            r.seek(pos)
            return None

        attachment_points: list[tuple[int, list[int]]] = []
        for _ in range(attachment_point_count):
            glyph_index = r.read_u16()
            point_count = r.read_u16()
            if offset + 4 + (len(attachment_points) * 4) + point_count * 2 > len(raw):
                r.seek(pos)
                return None
            point_indices = [r.read_u16() for _ in range(point_count)]
            attachment_points.append((glyph_index, point_indices))

        r.seek(pos)
        return _AttachmentPointList(
            attachment_point_count=attachment_point_count, attachment_points=attachment_points
        )
    except Exception:
        r.seek(pos)
        return None


def _parse_ligature_caret_list(
    r: BinaryReader, offset: int, raw: bytes
) -> _LigatureCaretList | None:
    pos = r.tell()
    r.seek(offset)

    if offset < 0 or offset + 2 > len(raw):
        r.seek(pos)
        return None

    try:
        caret_count = r.read_u16()

        if offset + 2 + caret_count * 2 > len(raw):
            r.seek(pos)
            return None

        caret_offsets = [r.read_u16() for _ in range(caret_count)]

        caret_values: list[_CaretValue] = []
        for caret_offset in caret_offsets:
            if caret_offset == 0:
                continue
            caret_abs = offset + caret_offset
            if caret_abs >= len(raw):
                continue

            try:
                caret_r = BinaryReader(raw)
                caret_r.seek(caret_abs)
                caret_fmt = caret_r.read_u16()

                if caret_fmt == 1:
                    value = caret_r.read_u16()
                    caret_values.append(_CaretValue(format=1, value=value))
                elif caret_fmt == 2:
                    contour_point = caret_r.read_u16()
                    caret_values.append(
                        _CaretValue(format=2, value=0, contour_point=contour_point)
                    )
                elif caret_fmt == 3:
                    value = caret_r.read_u16()
                    device_table_offset = caret_r.read_u16()
                    caret_values.append(
                        _CaretValue(
                            format=3, value=value, device_table_offset=device_table_offset
                        )
                    )
                else:
                    caret_values.append(_CaretValue(format=caret_fmt, value=0))
            except Exception:
                continue

        r.seek(pos)
        return _LigatureCaretList(caret_count=caret_count, caret_values=caret_values)
    except Exception:
        r.seek(pos)
        return None
