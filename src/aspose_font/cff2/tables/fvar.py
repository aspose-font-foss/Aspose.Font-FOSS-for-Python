from __future__ import annotations

from dataclasses import dataclass

from aspose_font._io import BinaryReader


@dataclass(slots=True)
class AxisRecord:
    tag: str
    min_value: float
    default_value: float
    max_value: float
    flags: int
    name_id: int


@dataclass(slots=True)
class NamedInstance:
    subfamily_name_id: int
    coordinates: dict[str, float]
    postscript_name_id: int | None


def _read_fixed(rr: BinaryReader) -> float:
    raw = rr.read_u32()
    signed = raw if raw < 0x80000000 else raw - 0x100000000
    return signed / 65536.0


@dataclass
class FvarTable:
    axes: list[AxisRecord]
    instances: list[NamedInstance]
    _raw: bytes = b""
    _reserved: int = 0

    @classmethod
    def from_bytes(cls, data: bytes) -> "FvarTable":
        r = BinaryReader(data)
        return cls._from_reader(r)

    @classmethod
    def _from_reader(cls, r: BinaryReader) -> "FvarTable":
        r.read_u16()
        r.read_u16()
        axis_array_offset = r.read_u16()
        reserved = r.read_u16()
        axis_count = r.read_u16()
        axis_size = r.read_u16()
        instance_count = r.read_u16()
        instance_size = r.read_u16()

        rr = BinaryReader(r._buf.getvalue())
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

        has_ps_name = instance_size == 4 + axis_count * 4 + 2
        instances: list[NamedInstance] = []
        inst_start = axis_array_offset + axis_count * axis_size
        rr.seek(inst_start)
        for _ in range(instance_count):
            subfamily_name_id = rr.read_u16()
            rr.read_u16()
            coords: dict[str, float] = {}
            for ax in axes:
                coords[ax.tag] = _read_fixed(rr)
            ps_name_id = rr.read_u16() if has_ps_name else None
            instances.append(NamedInstance(
                subfamily_name_id=subfamily_name_id,
                coordinates=coords,
                postscript_name_id=ps_name_id,
            ))

        return cls(axes=axes, instances=instances, _raw=r._buf.getvalue(), _reserved=reserved)
