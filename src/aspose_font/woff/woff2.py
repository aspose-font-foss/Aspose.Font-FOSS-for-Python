"""WOFF v2 parser and wrapper font."""

from __future__ import annotations

import math
from dataclasses import dataclass

from aspose_font._brotli import compress as brotli_compress
from aspose_font._brotli import decompress as brotli_decompress
from aspose_font._exceptions import FontParseException
from aspose_font._font_base import Font, FontEncoding, FontType, GlyphAccessor
from aspose_font._io import BinaryReader, BinaryWriter
from aspose_font._types import FontMetrics, KernPair
from aspose_font.ttf.font import TtfFont
from aspose_font.woff.woff1 import _extract_sfnt_tables, _sfnt_checksum

_WOFF2_SIGNATURE = 0x774F4632

_KNOWN_TABLE_TAGS = (
    "cmap",
    "head",
    "hhea",
    "hmtx",
    "maxp",
    "name",
    "OS/2",
    "post",
    "cvt ",
    "fpgm",
    "glyf",
    "loca",
    "prep",
    "CFF ",
    "VORG",
    "EBDT",
    "EBLC",
    "gasp",
    "hdmx",
    "kern",
    "LTSH",
    "PCLT",
    "VDMX",
    "vhea",
    "vmtx",
    "BASE",
    "GDEF",
    "GPOS",
    "GSUB",
    "EBSC",
    "JSTF",
    "MATH",
    "CBDT",
    "CBLC",
    "COLR",
    "CPAL",
    "SVG ",
    "sbix",
    "acnt",
    "avar",
    "bdat",
    "bloc",
    "bsln",
    "cvar",
    "fdsc",
    "feat",
    "fmtx",
    "fvar",
    "gvar",
    "hsty",
    "just",
    "lcar",
    "mort",
    "morx",
    "opbd",
    "prop",
    "trak",
    "Zapf",
    "Silf",
    "Glat",
    "Gloc",
    "Feat",
    "Sill",
)
_KNOWN_TABLE_INDEX = {tag: i for i, tag in enumerate(_KNOWN_TABLE_TAGS)}

_ARG_1_AND_2_ARE_WORDS = 0x0001
_WE_HAVE_A_SCALE = 0x0008
_MORE_COMPONENTS = 0x0020
_WE_HAVE_AN_X_AND_Y_SCALE = 0x0040
_WE_HAVE_A_TWO_BY_TWO = 0x0080
_WE_HAVE_INSTRUCTIONS = 0x0100

_ON_CURVE_POINT = 0x01
_X_SHORT_VECTOR = 0x02
_Y_SHORT_VECTOR = 0x04
_X_IS_SAME_OR_POSITIVE = 0x10
_Y_IS_SAME_OR_POSITIVE = 0x20
_OVERLAP_SIMPLE = 0x40

@dataclass(slots=True)
class _Woff2TableEntry:
    flags: int
    tag: str
    orig_length: int
    transform_length: int
    transformed: bool
    transform_version: int


class _SliceReader:
    def __init__(self, data: bytes) -> None:
        self._data = data
        self._pos = 0

    def remaining(self) -> int:
        return len(self._data) - self._pos

    def tell(self) -> int:
        return self._pos

    def read_u8(self) -> int:
        return self.read_bytes(1)[0]

    def read_u16(self) -> int:
        return int.from_bytes(self.read_bytes(2), "big")

    def read_i16(self) -> int:
        return int.from_bytes(self.read_bytes(2), "big", signed=True)

    def read_u32(self) -> int:
        return int.from_bytes(self.read_bytes(4), "big")

    def read_bytes(self, n: int) -> bytes:
        if n < 0 or self._pos + n > len(self._data):
            raise FontParseException("WOFF2 glyf transform failed: malformed transformed stream")
        out = self._data[self._pos : self._pos + n]
        self._pos += n
        return out


class Woff2Font(Font):
    def __init__(self, inner: TtfFont, metadata_xml: str = "") -> None:
        self._inner = inner
        self._metadata_xml = metadata_xml

    @classmethod
    def _from_reader(cls, reader: BinaryReader) -> "Woff2Font":
        data = reader.read_bytes(reader.remaining())
        rr = BinaryReader(data)

        signature = rr.read_u32()
        if signature != _WOFF2_SIGNATURE:
            raise FontParseException("Invalid WOFF2 signature")
        flavor = rr.read_u32()
        length = rr.read_u32()
        num_tables = rr.read_u16()
        rr.read_u16()  # reserved
        rr.read_u32()  # totalSfntSize
        total_compressed_size = rr.read_u32()
        rr.read_u16()  # majorVersion
        rr.read_u16()  # minorVersion
        meta_offset = rr.read_u32()
        meta_length = rr.read_u32()
        rr.read_u32()  # metaOrigLength
        rr.read_u32()  # privOffset
        rr.read_u32()  # privLength

        if length > len(data):
            raise FontParseException("Invalid WOFF2 length")

        entries = _parse_woff2_directory(rr, num_tables)
        compressed_offset = rr.tell()
        compressed_end = compressed_offset + total_compressed_size
        if compressed_end > len(data):
            raise FontParseException("WOFF2 compressed stream out of bounds")
        compressed = data[compressed_offset:compressed_end]

        try:
            payload = brotli_decompress(compressed)
        except FontParseException:
            raise
        except Exception as exc:  # pragma: no cover - defensive
            raise FontParseException("WOFF2 Brotli decompression failed") from exc

        metadata_xml = _decode_metadata_xml(data, meta_offset, meta_length)
        tables = _split_woff2_table_payload(payload, entries)
        sfnt = _build_sfnt_from_tables(flavor, tables)

        inner = TtfFont._from_reader(BinaryReader(sfnt))
        return cls(inner=inner, metadata_xml=metadata_xml)

    @property
    def font_type(self) -> FontType:
        return FontType.WOFF2

    @property
    def font_name(self) -> str:
        return self._inner.font_name

    @property
    def font_family(self) -> str:
        return self._inner.font_family

    @property
    def font_style(self) -> str:
        return self._inner.font_style

    @property
    def num_glyphs(self) -> int:
        return self._inner.num_glyphs

    @property
    def metrics(self) -> FontMetrics:
        return self._inner.metrics

    @property
    def encoding(self) -> FontEncoding:
        return self._inner.encoding

    @property
    def glyph_accessor(self) -> GlyphAccessor:
        return self._inner.glyph_accessor

    @property
    def metadata_xml(self) -> str:
        return self._metadata_xml

    @property
    def inner_font(self) -> TtfFont:
        return self._inner

    def get_kern_pairs(self) -> list[KernPair]:
        return self._inner.get_kern_pairs()


    def to_bytes(self, font_type: FontType | None = None) -> bytes:
        if font_type is not None and font_type != self.font_type:
            return super().to_bytes(font_type)

        sfnt = self._inner.to_bytes()
        flavor, tables = _extract_sfnt_tables(sfnt)
        ordered_tags = sorted(tables.keys())

        payload_writer = BinaryWriter()
        entries: list[_Woff2TableEntry] = []
        directory = BinaryWriter()
        for tag in ordered_tags:
            table_data = tables[tag]
            tag_index = _KNOWN_TABLE_INDEX.get(tag, 63)
            transform_version = 1 if tag in {"glyf", "loca"} else 0
            flags = (transform_version << 6) | tag_index
            directory.write_u8(flags)
            if tag_index == 63:
                directory.write_tag(tag)
            _write_uint_base128(directory, len(table_data))
            payload_writer.write_bytes(table_data)
            entries.append(
                _Woff2TableEntry(
                    flags=flags,
                    tag=tag,
                    orig_length=len(table_data),
                    transform_length=0,
                    transformed=False,
                    transform_version=transform_version,
                )
            )

        payload = payload_writer.to_bytes()
        compressed = brotli_compress(payload)
        directory_bytes = directory.to_bytes()
        length = 48 + len(directory_bytes) + len(compressed)

        w = BinaryWriter()
        w.write_u32(_WOFF2_SIGNATURE)
        w.write_u32(flavor)
        w.write_u32(length)
        w.write_u16(len(entries))
        w.write_u16(0)
        w.write_u32(len(sfnt))
        w.write_u32(len(compressed))
        w.write_u16(1)
        w.write_u16(0)
        w.write_u32(0)  # metaOffset
        w.write_u32(0)  # metaLength
        w.write_u32(0)  # metaOrigLength
        w.write_u32(0)  # privOffset
        w.write_u32(0)  # privLength
        w.write_bytes(directory_bytes)
        w.write_bytes(compressed)
        return w.to_bytes()


def _parse_woff2_directory(r: BinaryReader, num_tables: int) -> list[_Woff2TableEntry]:
    entries: list[_Woff2TableEntry] = []
    for _ in range(num_tables):
        flags = r.read_u8()
        tag_index = flags & 0x3F
        transform_version = flags >> 6
        if tag_index == 63:
            tag = r.read_tag()
        else:
            if tag_index >= len(_KNOWN_TABLE_TAGS):
                raise FontParseException("Invalid WOFF2 table tag index")
            tag = _KNOWN_TABLE_TAGS[tag_index]

        orig_length = _read_uint_base128(r)
        transformed = (tag in {"glyf", "loca"} and transform_version == 0) or (
            tag not in {"glyf", "loca"} and transform_version != 0
        )
        transform_length = _read_uint_base128(r) if transformed else 0
        entries.append(
            _Woff2TableEntry(
                flags=flags,
                tag=tag,
                orig_length=orig_length,
                transform_length=transform_length,
                transformed=transformed,
                transform_version=transform_version,
            )
        )
    return entries


def _read_uint_base128(r: BinaryReader | _SliceReader) -> int:
    value = 0
    for i in range(5):
        b = r.read_u8()
        if i == 0 and b == 0x80:
            raise FontParseException("Invalid UIntBase128 encoding")
        if value & 0xFE000000:
            raise FontParseException("UIntBase128 overflow")
        value = (value << 7) | (b & 0x7F)
        if (b & 0x80) == 0:
            return value
    raise FontParseException("Invalid UIntBase128 encoding")


def _write_uint_base128(w: BinaryWriter, value: int) -> None:
    if value < 0 or value > 0xFFFFFFFF:
        raise FontParseException("UIntBase128 out of range")
    chunks = [value & 0x7F]
    value >>= 7
    while value > 0:
        chunks.append(0x80 | (value & 0x7F))
        value >>= 7
    for b in reversed(chunks):
        w.write_u8(b)


def _read_255uint16(r: BinaryReader | _SliceReader) -> int:
    code = r.read_u8()
    if code == 253:
        return r.read_u16()
    if code == 254:
        return r.read_u8() + 506
    if code == 255:
        return r.read_u8() + 253
    return code


def _decode_metadata_xml(data: bytes, meta_offset: int, meta_length: int) -> str:
    if meta_offset <= 0 or meta_length <= 0:
        return ""
    meta_end = meta_offset + meta_length
    if meta_end > len(data):
        raise FontParseException("Invalid WOFF2 metadata bounds")
    meta_blob = data[meta_offset:meta_end]
    try:
        return brotli_decompress(meta_blob).decode("utf-8", errors="replace")
    except FontParseException:
        return meta_blob.decode("utf-8", errors="replace")


def _split_woff2_table_payload(
    payload: bytes,
    entries: list[_Woff2TableEntry],
) -> dict[str, bytes]:
    pos = 0
    out: dict[str, bytes] = {}
    transformed_glyf = False
    transformed_loca = False
    glyf_payload = b""
    loca_payload = b""
    loca_orig_length = 0
    for entry in entries:
        length = entry.transform_length if entry.transformed else entry.orig_length
        end = pos + length
        if end > len(payload):
            raise FontParseException("WOFF2 table payload underflow")
        chunk = payload[pos:end]
        pos = end
        if entry.tag == "glyf" and entry.transformed:
            glyf_payload = chunk
            transformed_glyf = True
            continue
        if entry.tag == "loca" and entry.transformed:
            if entry.transform_length != 0:
                raise FontParseException("WOFF2 glyf transform failed: malformed transformed stream")
            loca_payload = chunk
            loca_orig_length = entry.orig_length
            transformed_loca = True
            continue
        if entry.transformed:
            raise FontParseException(f"WOFF2 transformed table unsupported: {entry.tag}")
        out[entry.tag] = chunk

    if transformed_glyf != transformed_loca:
        raise FontParseException("WOFF2 glyf transform failed: malformed transformed stream")

    if transformed_glyf:
        glyf, loca = _reconstruct_transformed_glyf_and_loca(glyf_payload, loca_payload, out)
        if len(loca) != loca_orig_length:
            raise FontParseException("WOFF2 glyf transform failed: malformed transformed stream")
        out["glyf"] = glyf
        out["loca"] = loca

    if pos != len(payload):
        raise FontParseException("WOFF2 table payload overflow")
    return out


def _triplet_decode(flag: int, glyph_stream: _SliceReader) -> tuple[int, int]:
    def with_sign(sig_flag: int, value: int) -> int:
        return value if (sig_flag & 1) else -value

    if flag < 10:
        b0 = glyph_stream.read_u8()
        return 0, with_sign(flag, ((flag & 14) << 7) + b0)
    if flag < 20:
        b0 = glyph_stream.read_u8()
        return with_sign(flag, (((flag - 10) & 14) << 7) + b0), 0
    if flag < 84:
        b0 = glyph_stream.read_u8()
        f = flag - 20
        dx = with_sign(flag, 1 + (f & 0x30) + (b0 >> 4))
        dy = with_sign(flag >> 1, 1 + ((f & 0x0C) << 2) + (b0 & 0x0F))
        return dx, dy
    if flag < 120:
        b0 = glyph_stream.read_u8()
        b1 = glyph_stream.read_u8()
        f = flag - 84
        dx = with_sign(flag, 1 + ((f // 12) << 8) + b0)
        dy = with_sign(flag >> 1, 1 + (((f % 12) >> 2) << 8) + b1)
        return dx, dy
    if flag < 124:
        b0 = glyph_stream.read_u8()
        b1 = glyph_stream.read_u8()
        b2 = glyph_stream.read_u8()
        dx = with_sign(flag, (b0 << 4) + (b1 >> 4))
        dy = with_sign(flag >> 1, ((b1 & 0x0F) << 8) + b2)
        return dx, dy
    b0 = glyph_stream.read_u8()
    b1 = glyph_stream.read_u8()
    b2 = glyph_stream.read_u8()
    b3 = glyph_stream.read_u8()
    dx = with_sign(flag, (b0 << 8) + b1)
    dy = with_sign(flag >> 1, (b2 << 8) + b3)
    return dx, dy


def _encode_simple_points(points: list[tuple[int, int, bool]], overlap: bool) -> tuple[bytes, bytes, bytes]:
    flags = bytearray()
    x_bytes = bytearray()
    y_bytes = bytearray()
    prev_x = 0
    prev_y = 0

    for i, (x, y, on_curve) in enumerate(points):
        dx = x - prev_x
        dy = y - prev_y
        prev_x = x
        prev_y = y

        flag = _ON_CURVE_POINT if on_curve else 0
        if overlap and i == 0:
            flag |= _OVERLAP_SIMPLE

        if dx == 0:
            flag |= _X_IS_SAME_OR_POSITIVE
        elif 0 < dx < 256:
            flag |= _X_SHORT_VECTOR | _X_IS_SAME_OR_POSITIVE
            x_bytes.append(dx)
        elif -255 <= dx < 0:
            flag |= _X_SHORT_VECTOR
            x_bytes.append(-dx)
        else:
            x_bytes.extend(int(dx).to_bytes(2, "big", signed=True))

        if dy == 0:
            flag |= _Y_IS_SAME_OR_POSITIVE
        elif 0 < dy < 256:
            flag |= _Y_SHORT_VECTOR | _Y_IS_SAME_OR_POSITIVE
            y_bytes.append(dy)
        elif -255 <= dy < 0:
            flag |= _Y_SHORT_VECTOR
            y_bytes.append(-dy)
        else:
            y_bytes.extend(int(dy).to_bytes(2, "big", signed=True))

        flags.append(flag)

    return bytes(flags), bytes(x_bytes), bytes(y_bytes)


def _bbox_from_points(points: list[tuple[int, int, bool]]) -> tuple[int, int, int, int]:
    if not points:
        return (0, 0, 0, 0)
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return (min(xs), min(ys), max(xs), max(ys))


def _reconstruct_transformed_glyf_and_loca(
    glyf_payload: bytes,
    loca_payload: bytes,
    tables: dict[str, bytes],
) -> tuple[bytes, bytes]:
    if loca_payload:
        raise FontParseException("WOFF2 glyf transform failed: malformed transformed stream")
    maxp = tables.get("maxp")
    if maxp is None or len(maxp) < 6:
        raise FontParseException("WOFF2 glyf transform failed: malformed transformed stream")

    maxp_r = BinaryReader(maxp)
    maxp_r.read_u32()
    maxp_num_glyphs = maxp_r.read_u16()

    rr = _SliceReader(glyf_payload)
    if rr.read_u16() != 0:
        raise FontParseException("WOFF2 glyf transform failed: malformed transformed stream")
    option_flags = rr.read_u16()
    if option_flags & 0xFFFE:
        raise FontParseException("WOFF2 glyf transform failed: malformed transformed stream")
    num_glyphs = rr.read_u16()
    index_format = rr.read_u16()
    if index_format not in (0, 1):
        raise FontParseException("WOFF2 glyf transform failed: malformed transformed stream")
    if num_glyphs != maxp_num_glyphs:
        raise FontParseException("WOFF2 glyf transform failed: malformed transformed stream")

    sizes = [rr.read_u32() for _ in range(7)]
    streams: list[bytes] = []
    for size in sizes:
        streams.append(rr.read_bytes(size))

    overlap_bitmap = b""
    if option_flags & 1:
        overlap_bitmap = rr.read_bytes((num_glyphs + 7) // 8)
    if rr.remaining() != 0:
        raise FontParseException("WOFF2 glyf transform failed: malformed transformed stream")

    n_contour_stream = _SliceReader(streams[0])
    n_points_stream = _SliceReader(streams[1])
    flag_stream = _SliceReader(streams[2])
    glyph_stream = _SliceReader(streams[3])
    composite_stream = _SliceReader(streams[4])
    bbox_stream = _SliceReader(streams[5])
    instruction_stream = _SliceReader(streams[6])

    bbox_bitmap_size = 4 * ((num_glyphs + 31) // 32)
    bbox_bitmap = bbox_stream.read_bytes(bbox_bitmap_size)

    def bbox_present(gid: int) -> bool:
        byte_index = gid // 8
        bit = 7 - (gid % 8)
        if byte_index >= len(bbox_bitmap):
            return False
        return ((bbox_bitmap[byte_index] >> bit) & 1) == 1

    def overlap_present(gid: int) -> bool:
        if not overlap_bitmap:
            return False
        byte_index = gid // 8
        bit = 7 - (gid % 8)
        if byte_index >= len(overlap_bitmap):
            return False
        return ((overlap_bitmap[byte_index] >> bit) & 1) == 1

    glyf_out = bytearray()
    offsets: list[int] = [0]

    for gid in range(num_glyphs):
        n_contour = n_contour_stream.read_i16()
        has_bbox = bbox_present(gid)
        glyph_bytes = bytearray()

        if n_contour == 0:
            if has_bbox:
                raise FontParseException("WOFF2 glyf transform failed: malformed transformed stream")
        elif n_contour > 0:
            contour_point_counts: list[int] = []
            total_points = 0
            for _ in range(n_contour):
                count = _read_255uint16(n_points_stream)
                contour_point_counts.append(count)
                total_points += count

            flags_raw = [flag_stream.read_u8() for _ in range(total_points)]
            points: list[tuple[int, int, bool]] = []
            x = 0
            y = 0
            for raw_flag in flags_raw:
                on_curve = (raw_flag >> 7) == 0
                flag = raw_flag & 0x7F
                dx, dy = _triplet_decode(flag, glyph_stream)
                x += dx
                y += dy
                points.append((x, y, on_curve))

            instruction_length = _read_255uint16(glyph_stream)
            instructions = instruction_stream.read_bytes(instruction_length)

            if has_bbox:
                x_min = bbox_stream.read_i16()
                y_min = bbox_stream.read_i16()
                x_max = bbox_stream.read_i16()
                y_max = bbox_stream.read_i16()
            else:
                x_min, y_min, x_max, y_max = _bbox_from_points(points)

            glyph_bytes.extend(int(n_contour).to_bytes(2, "big", signed=True))
            glyph_bytes.extend(int(x_min).to_bytes(2, "big", signed=True))
            glyph_bytes.extend(int(y_min).to_bytes(2, "big", signed=True))
            glyph_bytes.extend(int(x_max).to_bytes(2, "big", signed=True))
            glyph_bytes.extend(int(y_max).to_bytes(2, "big", signed=True))

            end_pts = []
            acc = -1
            for count in contour_point_counts:
                acc += count
                end_pts.append(acc)
            for end_pt in end_pts:
                glyph_bytes.extend(int(end_pt).to_bytes(2, "big"))

            glyph_bytes.extend(len(instructions).to_bytes(2, "big"))
            glyph_bytes.extend(instructions)

            flags_encoded, xs_encoded, ys_encoded = _encode_simple_points(points, overlap_present(gid))
            glyph_bytes.extend(flags_encoded)
            glyph_bytes.extend(xs_encoded)
            glyph_bytes.extend(ys_encoded)
        else:
            if not has_bbox:
                raise FontParseException("WOFF2 glyf transform failed: malformed transformed stream")
            x_min = bbox_stream.read_i16()
            y_min = bbox_stream.read_i16()
            x_max = bbox_stream.read_i16()
            y_max = bbox_stream.read_i16()

            component_blob = bytearray()
            last_flags = 0
            while True:
                flags = composite_stream.read_u16()
                last_flags = flags
                component_blob.extend(flags.to_bytes(2, "big"))
                component_blob.extend(composite_stream.read_bytes(2))  # glyph index
                if flags & _ARG_1_AND_2_ARE_WORDS:
                    component_blob.extend(composite_stream.read_bytes(4))
                else:
                    component_blob.extend(composite_stream.read_bytes(2))
                if flags & _WE_HAVE_A_SCALE:
                    component_blob.extend(composite_stream.read_bytes(2))
                elif flags & _WE_HAVE_AN_X_AND_Y_SCALE:
                    component_blob.extend(composite_stream.read_bytes(4))
                elif flags & _WE_HAVE_A_TWO_BY_TWO:
                    component_blob.extend(composite_stream.read_bytes(8))
                if not (flags & _MORE_COMPONENTS):
                    break

            if last_flags & _WE_HAVE_INSTRUCTIONS:
                ins_len = _read_255uint16(glyph_stream)
                ins_bytes = instruction_stream.read_bytes(ins_len)
                component_blob.extend(ins_len.to_bytes(2, "big"))
                component_blob.extend(ins_bytes)

            glyph_bytes.extend((-1).to_bytes(2, "big", signed=True))
            glyph_bytes.extend(int(x_min).to_bytes(2, "big", signed=True))
            glyph_bytes.extend(int(y_min).to_bytes(2, "big", signed=True))
            glyph_bytes.extend(int(x_max).to_bytes(2, "big", signed=True))
            glyph_bytes.extend(int(y_max).to_bytes(2, "big", signed=True))
            glyph_bytes.extend(component_blob)

        glyf_out.extend(glyph_bytes)
        if index_format == 0 and (len(glyf_out) % 2):
            glyf_out.append(0)
        offsets.append(len(glyf_out))

    if (
        n_contour_stream.remaining() != 0
        or n_points_stream.remaining() != 0
        or flag_stream.remaining() != 0
        or glyph_stream.remaining() != 0
        or composite_stream.remaining() != 0
        or bbox_stream.remaining() != 0
        or instruction_stream.remaining() != 0
    ):
        raise FontParseException("WOFF2 glyf transform failed: malformed transformed stream")

    loca_writer = BinaryWriter()
    if index_format == 0:
        for offset in offsets:
            if (offset % 2) != 0 or (offset // 2) > 0xFFFF:
                raise FontParseException("WOFF2 glyf transform failed: malformed transformed stream")
            loca_writer.write_u16(offset // 2)
    else:
        for offset in offsets:
            loca_writer.write_u32(offset)

    return bytes(glyf_out), loca_writer.to_bytes()


def _build_sfnt_from_tables(flavor: int, tables: dict[str, bytes]) -> bytes:
    tags = sorted(tables.keys())
    if not tags:
        raise FontParseException("WOFF2 contains no tables")

    num_tables = len(tags)
    max_power = 1 << (num_tables.bit_length() - 1)
    search_range = max_power * 16
    entry_selector = int(math.log2(max_power))
    range_shift = num_tables * 16 - search_range

    w = BinaryWriter()
    w.write_u32(flavor)
    w.write_u16(num_tables)
    w.write_u16(search_range)
    w.write_u16(entry_selector)
    w.write_u16(range_shift)

    offset_positions: list[int] = []
    for tag in tags:
        blob = tables[tag]
        w.write_tag(tag)
        w.write_u32(_sfnt_checksum(blob))
        offset_positions.append(w.tell())
        w.write_u32(0)
        w.write_u32(len(blob))

    for i, tag in enumerate(tags):
        blob = tables[tag]
        while w.tell() % 4 != 0:
            w.write_u8(0)
        table_offset = w.tell()
        cursor = w.tell()
        w.seek(offset_positions[i])
        w.write_u32(table_offset)
        w.seek(cursor)
        w.write_bytes(blob)

    return w.to_bytes()
