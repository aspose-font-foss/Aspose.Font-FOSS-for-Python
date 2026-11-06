"""TTF hmtx table parser."""

from __future__ import annotations

from dataclasses import dataclass

from aspose_font._io import BinaryReader, BinaryWriter


@dataclass(slots=True)
class HMetric:
    advance_width: int
    lsb: int


@dataclass
class HmtxTable:
    metrics: list[HMetric]

    @classmethod
    def from_reader(
        cls,
        r: BinaryReader,
        num_glyphs: int,
        number_of_hmetrics: int,
        table_length: int,
    ) -> "HmtxTable":
        rr = BinaryReader(r.read_bytes(table_length))
        metrics: list[HMetric] = []
        for _ in range(number_of_hmetrics):
            metrics.append(HMetric(advance_width=rr.read_u16(), lsb=rr.read_i16()))

        last_aw = metrics[-1].advance_width if metrics else 0
        for _ in range(num_glyphs - number_of_hmetrics):
            metrics.append(HMetric(advance_width=last_aw, lsb=rr.read_i16()))

        return cls(metrics=metrics)

    def to_bytes(self, number_of_hmetrics: int) -> bytes:
        w = BinaryWriter()
        for metric in self.metrics[:number_of_hmetrics]:
            w.write_u16(metric.advance_width)
            w.write_i16(metric.lsb)
        for metric in self.metrics[number_of_hmetrics:]:
            w.write_i16(metric.lsb)
        return w.to_bytes()

    def get_metric(self, gid: int) -> HMetric:
        return self.metrics[gid]
