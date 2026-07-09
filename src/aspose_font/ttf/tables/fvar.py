"""FVAR (Font Variations) table parser for variable TrueType fonts."""
from __future__ import annotations

from dataclasses import dataclass

from aspose_font._io import BinaryReader


@dataclass(slots=True)
class AxisRecord:
    tag: str              # 4-char axis tag e.g. "wght"
    min_value: float      # Fixed16.16
    default_value: float  # Fixed16.16
    max_value: float      # Fixed16.16
    flags: int            # uint16 (bit 0 = HIDDEN_AXIS)
    name_id: int          # uint16, index into name table


@dataclass(slots=True)
class NamedInstance:
    name_id: int                        # uint16 subfamily name ID
    coordinates: dict[str, float]       # axis_tag → coordinate (Fixed16.16)
    postscript_name_id: int | None      # uint16 or None if not present


def _read_fixed(rr: BinaryReader) -> float:
    """Read a Fixed16.16 value as a signed float."""
    raw = rr.read_u32()
    signed = raw if raw < 0x80000000 else raw - 0x100000000
    return signed / 65536.0


@dataclass
class FvarTable:
    axes: list[AxisRecord]
    instances: list[NamedInstance]
    _raw: bytes

    @classmethod
    def from_reader(cls, r: BinaryReader, length: int) -> "FvarTable":
        raw = r.read_bytes(length)
        rr = BinaryReader(raw)
        rr.read_u16()  # majorVersion
        rr.read_u16()  # minorVersion
        axis_array_offset = rr.read_u16()
        rr.read_u16()  # reserved
        axis_count = rr.read_u16()
        axis_size = rr.read_u16()   # should be 20
        instance_count = rr.read_u16()
        instance_size = rr.read_u16()

        # Parse AxisRecords
        rr.seek(axis_array_offset)
        axes: list[AxisRecord] = []
        for _ in range(axis_count):
            tag = rr.read_bytes(4).decode("ascii", errors="replace")
            min_val = _read_fixed(rr)
            def_val = _read_fixed(rr)
            max_val = _read_fixed(rr)
            flags = rr.read_u16()
            name_id = rr.read_u16()
            axes.append(AxisRecord(
                tag=tag,
                min_value=min_val,
                default_value=def_val,
                max_value=max_val,
                flags=flags,
                name_id=name_id,
            ))

        # Parse InstanceRecords
        has_ps_name = instance_size == 4 + axis_count * 4 + 2
        instances: list[NamedInstance] = []
        inst_start = axis_array_offset + axis_count * axis_size
        rr.seek(inst_start)
        for _ in range(instance_count):
            subfamily_name_id = rr.read_u16()
            rr.read_u16()  # flags
            coords: dict[str, float] = {}
            for ax in axes:
                coords[ax.tag] = _read_fixed(rr)
            ps_name_id = rr.read_u16() if has_ps_name else None
            instances.append(NamedInstance(
                name_id=subfamily_name_id,
                coordinates=coords,
                postscript_name_id=ps_name_id,
            ))

        return cls(axes=axes, instances=instances, _raw=raw)

    def to_bytes(self) -> bytes:
        return self._raw
