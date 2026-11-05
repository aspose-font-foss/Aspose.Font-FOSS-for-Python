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
    _reserved: int = 0

    @classmethod
    def from_reader(cls, r: BinaryReader, length: int) -> "FvarTable":
        raw = r.read_bytes(length)
        rr = BinaryReader(raw)
        rr.read_u16()  # majorVersion
        rr.read_u16()  # minorVersion
        axis_array_offset = rr.read_u16()
        reserved = rr.read_u16()  # reserved
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

        return cls(axes=axes, instances=instances, _raw=raw, _reserved=reserved)

    def to_bytes(self) -> bytes:
        """Serialize FVAR table to bytes."""
        from aspose_font._io import BinaryWriter

        w = BinaryWriter()

        # Header (16 bytes)
        w.write_u16(1)  # majorVersion
        w.write_u16(0)  # minorVersion
        w.write_u16(16)  # axisArrayOffset - starts at byte 16 (header end)
        w.write_u16(self._reserved)  # reserved
        w.write_u16(len(self.axes))  # axisCount
        w.write_u16(20)  # axisSize (20 bytes per axis record)
        w.write_u16(len(self.instances))  # instanceCount
        if self.instances:
            instance_size = 4 + len(self.axes) * 4 + 2  # name_id(2) + flags(2) + coords(axis_count*4) + ps_name_id(2)
        else:
            instance_size = 0
        w.write_u16(instance_size)  # instanceSize

        # Write axis records (each 20 bytes)
        for axis in self.axes:
            w.write_bytes(axis.tag.encode("ascii"))
            # Write Fixed16.16 values
            w.write_u32(int(axis.min_value * 65536))
            w.write_u32(int(axis.default_value * 65536))
            w.write_u32(int(axis.max_value * 65536))
            w.write_u16(axis.flags)
            w.write_u16(axis.name_id)

        # Write instance records
        for instance in self.instances:
            w.write_u16(instance.name_id)
            w.write_u16(0)  # flags
            for axis in self.axes:
                w.write_u32(int(instance.coordinates.get(axis.tag, axis.default_value) * 65536))
            if instance.postscript_name_id is not None:
                w.write_u16(instance.postscript_name_id)

        return w.to_bytes()
