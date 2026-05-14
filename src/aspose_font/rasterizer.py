"""Pure-Python glyph path rasterization and PNG encoding."""

from __future__ import annotations

import math
import struct
import zlib
from dataclasses import dataclass

from aspose_font._types import ClosePath, CurveTo, GlyphPath, LineTo, MoveTo, QuadraticTo

_Affine = tuple[float, float, float, float, float, float]


@dataclass(slots=True)
class _Edge:
    y0: float
    y1: float
    x0: float
    dxdy: float
    winding: int


class Rasterizer:
    """Scanline rasterizer for GlyphPath outlines with pure-Python PNG export."""

    curve_tolerance: float = 0.5

    def __init__(
        self,
        width: int,
        height: int,
        background: tuple[int, int, int] = (255, 255, 255),
    ) -> None:
        if width < 1 or height < 1:
            raise ValueError("Rasterizer width and height must be >= 1")
        self.width = width
        self.height = height
        self._bg = _clamp_color(background)
        self._buf = bytearray(width * height * 3)
        self.clear()

    def clear(self, color: tuple[int, int, int] | None = None) -> None:
        """Fill entire buffer with background (or provided) color."""
        fill = _clamp_color(self._bg if color is None else color)
        row = bytes(fill) * self.width
        for y in range(self.height):
            start = y * self.width * 3
            self._buf[start:start + self.width * 3] = row

    def draw_path(
        self,
        path: GlyphPath,
        color: tuple[int, int, int] = (0, 0, 0),
        transform: tuple[float, ...] | None = None,
    ) -> None:
        """Rasterize one path into the current RGB buffer."""
        if len(path) == 0:
            return

        affine: _Affine
        if transform is None:
            affine = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
        else:
            if len(transform) != 6:
                raise ValueError("transform must be a 6-element affine tuple")
            affine = (
                float(transform[0]),
                float(transform[1]),
                float(transform[2]),
                float(transform[3]),
                float(transform[4]),
                float(transform[5]),
            )

        edges = self._flatten_to_edges(path, affine)
        if not edges:
            return

        rgb = _clamp_color(color)
        self._fill_edges_non_zero(edges, rgb)

    def to_png(self) -> bytes:
        """Encode current RGB buffer as 8-bit PNG (IHDR+IDAT+IEND)."""
        png_sig = b"\x89PNG\r\n\x1a\n"

        ihdr = _png_chunk(
            b"IHDR",
            struct.pack(">IIBBBBB", self.width, self.height, 8, 2, 0, 0, 0),
        )

        raw = bytearray()
        stride = self.width * 3
        for y in range(self.height):
            raw.append(0)  # filter = None
            start = y * stride
            raw.extend(self._buf[start:start + stride])

        idat = _png_chunk(b"IDAT", zlib.compress(bytes(raw), 6))
        iend = _png_chunk(b"IEND", b"")
        return png_sig + ihdr + idat + iend

    def _flatten_to_edges(self, path: GlyphPath, affine: _Affine) -> list[_Edge]:
        segments: list[tuple[float, float, float, float]] = []
        start_pt: tuple[float, float] | None = None
        cur_pt: tuple[float, float] | None = None

        def close_contour() -> None:
            nonlocal cur_pt, start_pt
            if cur_pt is None or start_pt is None:
                return
            if cur_pt != start_pt:
                segments.append((cur_pt[0], cur_pt[1], start_pt[0], start_pt[1]))
            cur_pt = None
            start_pt = None

        for cmd in path:
            if isinstance(cmd, MoveTo):
                close_contour()
                p = _apply_affine(cmd.x, cmd.y, affine)
                start_pt = p
                cur_pt = p
            elif isinstance(cmd, LineTo):
                if cur_pt is None:
                    continue
                p1 = _apply_affine(cmd.x, cmd.y, affine)
                segments.append((cur_pt[0], cur_pt[1], p1[0], p1[1]))
                cur_pt = p1
            elif isinstance(cmd, QuadraticTo):
                if cur_pt is None:
                    continue
                p1 = _apply_affine(cmd.x1, cmd.y1, affine)
                p2 = _apply_affine(cmd.x, cmd.y, affine)
                _flatten_quadratic(cur_pt, p1, p2, self.curve_tolerance, segments, 0)
                cur_pt = p2
            elif isinstance(cmd, CurveTo):
                if cur_pt is None:
                    continue
                p1 = _apply_affine(cmd.x1, cmd.y1, affine)
                p2 = _apply_affine(cmd.x2, cmd.y2, affine)
                p3 = _apply_affine(cmd.x, cmd.y, affine)
                _flatten_cubic(cur_pt, p1, p2, p3, self.curve_tolerance, segments, 0)
                cur_pt = p3
            elif isinstance(cmd, ClosePath):
                close_contour()

        close_contour()
        if not segments:
            return []

        edges: list[_Edge] = []
        for x0, y0, x1, y1 in segments:
            if y0 == y1:
                continue
            if y0 < y1:
                ymin, ymax = y0, y1
                x_at_ymin = x0
                winding = 1
            else:
                ymin, ymax = y1, y0
                x_at_ymin = x1
                winding = -1
            dxdy = (x1 - x0) / (y1 - y0)
            edges.append(_Edge(y0=ymin, y1=ymax, x0=x_at_ymin, dxdy=dxdy, winding=winding))

        return edges

    def _fill_edges_non_zero(
        self,
        edges: list[_Edge],
        color: tuple[int, int, int],
    ) -> None:
        if not edges:
            return

        y_min = max(0, int(math.floor(min(e.y0 for e in edges))))
        y_max = min(self.height - 1, int(math.ceil(max(e.y1 for e in edges)) - 1))
        if y_max < y_min:
            return

        for y in range(y_min, y_max + 1):
            scan_y = y + 0.5
            crossings: list[tuple[float, int]] = []
            for e in edges:
                if e.y0 <= scan_y < e.y1:
                    x = e.x0 + (scan_y - e.y0) * e.dxdy
                    crossings.append((x, e.winding))
            if not crossings:
                continue
            crossings.sort(key=lambda it: it[0])

            winding = 0
            x_start = 0.0
            for x, delta in crossings:
                prev = winding
                winding += delta
                if prev == 0 and winding != 0:
                    x_start = x
                elif prev != 0 and winding == 0:
                    self._fill_span(y, x_start, x, color)

    def _fill_span(
        self,
        y: int,
        x0: float,
        x1: float,
        color: tuple[int, int, int],
    ) -> None:
        if x1 <= x0:
            return
        left = int(math.ceil(x0 - 0.5))
        right = int(math.floor(x1 - 0.5))
        if right < left:
            return
        left = max(0, left)
        right = min(self.width - 1, right)
        if right < left:
            return
        r, g, b = color
        for x in range(left, right + 1):
            self._set_pixel(x, y, r, g, b)

    def _set_pixel(self, x: int, y: int, r: int, g: int, b: int) -> None:
        idx = (y * self.width + x) * 3
        self._buf[idx] = r
        self._buf[idx + 1] = g
        self._buf[idx + 2] = b


def _clamp_color(color: tuple[int, int, int]) -> tuple[int, int, int]:
    return (
        int(max(0, min(255, color[0]))),
        int(max(0, min(255, color[1]))),
        int(max(0, min(255, color[2]))),
    )


def _apply_affine(x: float, y: float, t: _Affine) -> tuple[float, float]:
    a, b, c, d, e, f = t
    return (a * x + c * y + e, b * x + d * y + f)


def _flatten_quadratic(
    p0: tuple[float, float],
    p1: tuple[float, float],
    p2: tuple[float, float],
    tolerance: float,
    out: list[tuple[float, float, float, float]],
    depth: int,
) -> None:
    if depth >= 16 or _quad_is_flat(p0, p1, p2, tolerance):
        out.append((p0[0], p0[1], p2[0], p2[1]))
        return

    p01 = _midpoint(p0, p1)
    p12 = _midpoint(p1, p2)
    p012 = _midpoint(p01, p12)
    _flatten_quadratic(p0, p01, p012, tolerance, out, depth + 1)
    _flatten_quadratic(p012, p12, p2, tolerance, out, depth + 1)


def _flatten_cubic(
    p0: tuple[float, float],
    p1: tuple[float, float],
    p2: tuple[float, float],
    p3: tuple[float, float],
    tolerance: float,
    out: list[tuple[float, float, float, float]],
    depth: int,
) -> None:
    if depth >= 16 or _cubic_is_flat(p0, p1, p2, p3, tolerance):
        out.append((p0[0], p0[1], p3[0], p3[1]))
        return

    p01 = _midpoint(p0, p1)
    p12 = _midpoint(p1, p2)
    p23 = _midpoint(p2, p3)
    p012 = _midpoint(p01, p12)
    p123 = _midpoint(p12, p23)
    p0123 = _midpoint(p012, p123)
    _flatten_cubic(p0, p01, p012, p0123, tolerance, out, depth + 1)
    _flatten_cubic(p0123, p123, p23, p3, tolerance, out, depth + 1)


def _midpoint(p0: tuple[float, float], p1: tuple[float, float]) -> tuple[float, float]:
    return ((p0[0] + p1[0]) * 0.5, (p0[1] + p1[1]) * 0.5)


def _quad_is_flat(
    p0: tuple[float, float],
    p1: tuple[float, float],
    p2: tuple[float, float],
    tolerance: float,
) -> bool:
    mid = _midpoint(p0, p2)
    dx = p1[0] - mid[0]
    dy = p1[1] - mid[1]
    return math.hypot(dx, dy) * 0.5 <= tolerance


def _cubic_is_flat(
    p0: tuple[float, float],
    p1: tuple[float, float],
    p2: tuple[float, float],
    p3: tuple[float, float],
    tolerance: float,
) -> bool:
    p13 = ((2.0 * p0[0] + p3[0]) / 3.0, (2.0 * p0[1] + p3[1]) / 3.0)
    p23 = ((p0[0] + 2.0 * p3[0]) / 3.0, (p0[1] + 2.0 * p3[1]) / 3.0)
    d1 = math.hypot(p1[0] - p13[0], p1[1] - p13[1])
    d2 = math.hypot(p2[0] - p23[0], p2[1] - p23[1])
    return max(d1, d2) <= tolerance


def _png_chunk(tag: bytes, payload: bytes) -> bytes:
    c = tag + payload
    return (
        struct.pack(">I", len(payload))
        + c
        + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)
    )


def encode_apng_from_rgb(
    frames: list[bytes | bytearray],
    width: int,
    height: int,
    fps: int = 15,
) -> bytes:
    """Encode a sequence of raw RGB buffers into an Animated PNG (APNG).

    Each buffer must be exactly `width * height * 3` bytes.
    The resulting APNG will loop infinitely and use a simple replace blending mode
    for fully opaque RGB frames.
    """
    if not frames:
        raise ValueError("Must provide at least one frame")

    png_sig = b"\x89PNG\r\n\x1a\n"

    ihdr = _png_chunk(
        b"IHDR",
        struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0),
    )

    actl = _png_chunk(
        b"acTL",
        struct.pack(">II", len(frames), 0),  # 0 plays = infinite loop
    )

    chunks = [png_sig, ihdr, actl]
    seq = 0
    stride = width * 3

    for i, rgb_buf in enumerate(frames):
        if len(rgb_buf) != width * height * 3:
            raise ValueError(f"Frame {i} buffer size mismatch: expected {width * height * 3}, got {len(rgb_buf)}")

        raw = bytearray()
        for y in range(height):
            raw.append(0)  # filter = None
            start = y * stride
            raw.extend(rgb_buf[start:start + stride])

        compressed_pixels = zlib.compress(bytes(raw), 6)

        # fcTL: (sequence_number, width, height, x_offset, y_offset, delay_num, delay_den, dispose_op, blend_op)
        # dispose_op = 0 (APNG_DISPOSE_OP_NONE), blend_op = 0 (APNG_BLEND_OP_SOURCE)
        fctl_payload = struct.pack(
            ">IIIIIHHBB",
            seq, width, height, 0, 0, 1, fps, 0, 0,
        )
        chunks.append(_png_chunk(b"fcTL", fctl_payload))
        seq += 1

        if i == 0:
            chunks.append(_png_chunk(b"IDAT", compressed_pixels))
        else:
            fdat_payload = struct.pack(">I", seq) + compressed_pixels
            chunks.append(_png_chunk(b"fdAT", fdat_payload))
            seq += 1

    chunks.append(_png_chunk(b"IEND", b""))
    return b"".join(chunks)
