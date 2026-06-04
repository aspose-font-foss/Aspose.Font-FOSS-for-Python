"""AFM parser for Type1 metrics."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class AfmGlyphMetric:
    name: str
    code: int
    advance_width: int
    bbox: tuple[int, int, int, int]


@dataclass(slots=True)
class AfmData:
    font_name: str = ""
    full_name: str = ""
    family_name: str = ""
    weight: str = ""
    italic_angle: float = 0.0
    is_fixed_pitch: bool = False
    font_bbox: tuple[int, int, int, int] = (0, 0, 0, 0)
    underline_position: int = 0
    underline_thickness: int = 0
    cap_height: float = 0.0
    x_height: float = 0.0
    ascender: float = 0.0
    descender: float = 0.0
    glyph_metrics: dict[str, AfmGlyphMetric] = field(default_factory=dict)
    kern_pairs: list[tuple[str, str, int]] = field(default_factory=list)


def parse_afm(path: str) -> AfmData:
    with open(path, "rb") as f:
        return parse_afm_bytes(f.read())


def parse_afm_bytes(data: bytes) -> AfmData:
    out = AfmData()
    lines = data.decode("latin-1", errors="ignore").splitlines()
    in_char_metrics = False
    in_kern_pairs = False

    for line in lines:
        s = line.strip()
        if not s:
            continue

        if s.startswith("StartCharMetrics"):
            in_char_metrics = True
            continue
        if s.startswith("EndCharMetrics"):
            in_char_metrics = False
            continue
        if s.startswith("StartKernPairs"):
            in_kern_pairs = True
            continue
        if s.startswith("EndKernPairs"):
            in_kern_pairs = False
            continue

        if in_char_metrics:
            metric = _parse_char_metric_line(s)
            if metric is not None:
                out.glyph_metrics[metric.name] = metric
            continue

        if in_kern_pairs:
            if s.startswith("KPX "):
                parts = s.split()
                if len(parts) == 4:
                    out.kern_pairs.append((parts[1], parts[2], int(parts[3])))
            continue

        if s.startswith("FontName "):
            out.font_name = s.split(" ", 1)[1]
        elif s.startswith("FullName "):
            out.full_name = s.split(" ", 1)[1]
        elif s.startswith("FamilyName "):
            out.family_name = s.split(" ", 1)[1]
        elif s.startswith("Weight "):
            out.weight = s.split(" ", 1)[1]
        elif s.startswith("ItalicAngle "):
            out.italic_angle = float(s.split(" ", 1)[1])
        elif s.startswith("IsFixedPitch "):
            out.is_fixed_pitch = s.split(" ", 1)[1].strip().lower() == "true"
        elif s.startswith("FontBBox "):
            vals = [int(v) for v in s.split()[1:5]]
            if len(vals) == 4:
                out.font_bbox = (vals[0], vals[1], vals[2], vals[3])
        elif s.startswith("UnderlinePosition "):
            out.underline_position = int(float(s.split(" ", 1)[1]))
        elif s.startswith("UnderlineThickness "):
            out.underline_thickness = int(float(s.split(" ", 1)[1]))
        elif s.startswith("CapHeight "):
            out.cap_height = float(s.split(" ", 1)[1])
        elif s.startswith("XHeight "):
            out.x_height = float(s.split(" ", 1)[1])
        elif s.startswith("Ascender "):
            out.ascender = float(s.split(" ", 1)[1])
        elif s.startswith("Descender "):
            out.descender = float(s.split(" ", 1)[1])

    return out


def _parse_char_metric_line(line: str) -> AfmGlyphMetric | None:
    code = -1
    advance_width = 0
    name = ""
    bbox = (0, 0, 0, 0)

    for raw_part in line.split(";"):
        part = raw_part.strip()
        if not part:
            continue
        if part.startswith("C "):
            code = int(part.split()[1])
        elif part.startswith("WX "):
            advance_width = int(float(part.split()[1]))
        elif part.startswith("N "):
            name = part.split()[1]
        elif part.startswith("B "):
            vals = [int(float(v)) for v in part.split()[1:5]]
            if len(vals) == 4:
                bbox = (vals[0], vals[1], vals[2], vals[3])

    if not name:
        return None
    return AfmGlyphMetric(name=name, code=code, advance_width=advance_width, bbox=bbox)
