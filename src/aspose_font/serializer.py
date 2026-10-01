"""Font format serializers (SPEC-008 / ADR-009)."""

from __future__ import annotations

import math
from dataclasses import dataclass

from aspose_font._exceptions import FontParseException
from aspose_font._io import BinaryWriter
from aspose_font.cff.charset import resolve_sid
from aspose_font.cff.dict_ import CffDict, PrivateDictOp, TopDictOp
from aspose_font.cff.index import CffIndex

_TTF_MAGIC_CHECKSUM_ADJUSTMENT = 0xB1B0AFBA
_TYPE1_PFB_ASCII = 1
_TYPE1_PFB_BINARY = 2
_TYPE1_PFB_EOF = 3


@dataclass(slots=True)
class _TableEntry:
    tag: str
    checksum: int
    offset: int
    length: int


class TtfSerializer:
    @staticmethod
    def serialize(font: object, sfnt_version: int | None = None) -> bytes:
        from aspose_font.ttf.font import TtfFont

        if not isinstance(font, TtfFont):
            raise FontParseException("TtfSerializer expects TtfFont")

        tables = font.ttf_tables
        if tables.head is None:
            raise FontParseException("Cannot serialize TtfFont without head table")

        table_data = dict(tables._raw)
        if tables.head is not None:
            table_data["head"] = tables.head.to_bytes()
        if tables.hhea is not None:
            table_data["hhea"] = tables.hhea.to_bytes()
        if tables.maxp is not None:
            table_data["maxp"] = tables.maxp.to_bytes()
        if tables.os2 is not None:
            table_data["OS/2"] = tables.os2.to_bytes()
        if tables.name is not None:
            table_data["name"] = tables.name.to_bytes()
        if tables.post is not None:
            table_data["post"] = tables.post.to_bytes()
        if tables.cmap is not None:
            table_data["cmap"] = tables.cmap.to_bytes()
        if tables.loca is not None:
            table_data["loca"] = tables.loca.to_bytes(tables.head.index_to_loc_format)
        if tables.hmtx is not None and tables.hhea is not None:
            table_data["hmtx"] = tables.hmtx.to_bytes(tables.hhea.number_of_hmetrics)
        if tables.kern is not None:
            table_data["kern"] = tables.kern.to_bytes()
        if tables.glyf is not None:
            table_data["glyf"] = tables.glyf.to_bytes()

        if not table_data:
            raise FontParseException("Cannot serialize TtfFont without tables")

        tags = sorted(table_data.keys())
        num_tables = len(tags)

        sfnt = font._sfnt_version if sfnt_version is None else sfnt_version
        max_power = 1 << (num_tables.bit_length() - 1)
        search_range = max_power * 16
        entry_selector = int(math.log2(max_power))
        range_shift = num_tables * 16 - search_range

        # `head.checkSumAdjustment` must be zeroed during checksum computation.
        for_head = dict(table_data)
        if "head" in for_head and len(for_head["head"]) >= 12:
            mutable = bytearray(for_head["head"])
            mutable[8:12] = b"\x00\x00\x00\x00"
            for_head["head"] = bytes(mutable)

        w = BinaryWriter()
        w.write_u32(sfnt)
        w.write_u16(num_tables)
        w.write_u16(search_range)
        w.write_u16(entry_selector)
        w.write_u16(range_shift)

        entries: list[_TableEntry] = []
        data_start = 12 + num_tables * 16
        cursor = data_start
        for tag in tags:
            blob = for_head[tag]
            cursor = (cursor + 3) & ~3
            entries.append(
                _TableEntry(
                    tag=tag,
                    checksum=TtfSerializer._compute_table_checksum(blob),
                    offset=cursor,
                    length=len(blob),
                )
            )
            cursor += len(blob)

        for entry in entries:
            w.write_tag(entry.tag)
            w.write_u32(entry.checksum)
            w.write_u32(entry.offset)
            w.write_u32(entry.length)

        for entry in entries:
            while w.tell() < entry.offset:
                w.write_u8(0)
            w.write_bytes(for_head[entry.tag])

        out = bytearray(w.to_bytes())
        head_entry = next((e for e in entries if e.tag == "head"), None)
        if head_entry is not None and head_entry.length >= 12:
            adjustment = TtfSerializer._compute_head_checksum_adjustment(bytes(out))
            out[head_entry.offset + 8 : head_entry.offset + 12] = adjustment.to_bytes(4, "big")
        return bytes(out)

    @staticmethod
    def _compute_table_checksum(data: bytes) -> int:
        padded = data + (b"\x00" * ((4 - (len(data) % 4)) % 4))
        total = 0
        for i in range(0, len(padded), 4):
            total = (total + int.from_bytes(padded[i : i + 4], "big")) & 0xFFFFFFFF
        return total

    @staticmethod
    def _compute_head_checksum_adjustment(sfnt_bytes: bytes) -> int:
        checksum = TtfSerializer._compute_table_checksum(sfnt_bytes)
        return (_TTF_MAGIC_CHECKSUM_ADJUSTMENT - checksum) & 0xFFFFFFFF


class CffSerializer:
    @staticmethod
    def serialize(font: object) -> bytes:
        from aspose_font.cff.font import CffFont

        if not isinstance(font, CffFont):
            raise FontParseException("CffSerializer expects CffFont")

        header = bytes([1, 0, 4, 4])
        postscript_name = (font.font_name or "Unnamed").encode("latin-1", errors="replace")
        name_index = CffIndex([postscript_name]).to_bytes()

        sid_ctx = _SidContext()
        CffSerializer._register_strings(font, sid_ctx)

        private_dict_bytes = CffSerializer._build_private_dict(font, sid_ctx)
        local_subrs_index = font.local_subrs.to_bytes() if len(font.local_subrs) > 0 else b""
        global_subrs_index = font.global_subrs.to_bytes()
        charset_bytes = CffSerializer._build_charset(font, sid_ctx)
        encoding_mode, encoding_bytes = CffSerializer._build_encoding(font)
        charstrings_index = font.charstrings.to_bytes()
        string_index = CffIndex([s.encode("latin-1", errors="replace") for s in sid_ctx.custom_strings]).to_bytes()

        top_dict_index = b""
        top_dict_bytes = b""
        for _ in range(8):
            base = len(header) + len(name_index) + len(top_dict_index) + len(string_index) + len(global_subrs_index)
            charset_offset = base if charset_bytes else 0
            if encoding_mode == "builtin":
                encoding_offset = int(getattr(font.top_dict, "encoding_offset", 0))
            else:
                encoding_offset = charset_offset + len(charset_bytes)
            charstrings_offset = charset_offset + len(charset_bytes) + len(encoding_bytes)
            private_offset = charstrings_offset + len(charstrings_index)
            top_dict_bytes = CffSerializer._build_top_dict(
                font,
                sid_ctx=sid_ctx,
                charset_offset=charset_offset,
                encoding_offset=encoding_offset,
                charstrings_offset=charstrings_offset,
                private_size=len(private_dict_bytes),
                private_offset=private_offset if private_dict_bytes else 0,
            )
            new_top_index = CffIndex([top_dict_bytes]).to_bytes()
            if new_top_index == top_dict_index:
                break
            top_dict_index = new_top_index
        else:
            top_dict_index = CffIndex([top_dict_bytes]).to_bytes()

        return b"".join(
            [
                header,
                name_index,
                top_dict_index,
                string_index,
                global_subrs_index,
                charset_bytes,
                encoding_bytes,
                charstrings_index,
                private_dict_bytes,
                local_subrs_index,
            ]
        )

    @staticmethod
    def _encode_index(items: list[bytes]) -> bytes:
        return CffIndex(items).to_bytes()

    @staticmethod
    def _encode_dict(d: CffDict) -> bytes:
        return d.to_bytes()

    @staticmethod
    def _encode_integer(v: int) -> bytes:
        w = BinaryWriter()
        if -107 <= v <= 107:
            w.write_u8(v + 139)
        elif 108 <= v <= 1131:
            n = v - 108
            w.write_u8((n // 256) + 247)
            w.write_u8(n % 256)
        elif -1131 <= v <= -108:
            n = -v - 108
            w.write_u8((n // 256) + 251)
            w.write_u8(n % 256)
        elif -32768 <= v <= 32767:
            w.write_u8(28)
            w.write_i16(v)
        else:
            w.write_u8(29)
            w.write_i32(v)
        return w.to_bytes()

    @staticmethod
    def _encode_real(v: float) -> bytes:
        if not math.isfinite(v):
            raise FontParseException("CFF real must be finite")
        s = format(v, ".12g")
        nibbles: list[int] = []
        i = 0
        while i < len(s):
            ch = s[i]
            if ch.isdigit():
                nibbles.append(int(ch))
            elif ch == ".":
                nibbles.append(0xA)
            elif ch in ("e", "E"):
                if i + 1 < len(s) and s[i + 1] == "-":
                    nibbles.append(0xC)
                    i += 1
                else:
                    nibbles.append(0xB)
            elif ch == "-":
                nibbles.append(0xE)
            else:
                raise FontParseException("Unsupported CFF real format")
            i += 1
        nibbles.append(0xF)
        if len(nibbles) % 2 != 0:
            nibbles.append(0xF)

        w = BinaryWriter()
        w.write_u8(30)
        for i in range(0, len(nibbles), 2):
            w.write_u8((nibbles[i] << 4) | nibbles[i + 1])
        return w.to_bytes()

    @staticmethod
    def _build_private_dict(font: object, sid_ctx: "_SidContext") -> bytes:
        del sid_ctx
        raw = getattr(font.private_dict, "_raw", CffDict())
        data = {op: vals.copy() for op, vals in raw._data.items()}
        if font.private_dict.default_width_x:
            data[PrivateDictOp.DEFAULT_WIDTH_X] = [int(font.private_dict.default_width_x)]
        if font.private_dict.nominal_width_x:
            data[PrivateDictOp.NOMINAL_WIDTH_X] = [int(font.private_dict.nominal_width_x)]
        if font.private_dict.std_hw:
            data[PrivateDictOp.STD_HW] = [float(font.private_dict.std_hw)]
        if font.private_dict.std_vw:
            data[PrivateDictOp.STD_VW] = [float(font.private_dict.std_vw)]

        has_subrs = len(font.local_subrs) > 0
        if not has_subrs:
            data.pop(PrivateDictOp.SUBRS, None)
            return CffDict(data).to_bytes()

        # Subrs offset is relative to Private DICT start and normally equals private DICT size.
        previous = -1
        for _ in range(8):
            data[PrivateDictOp.SUBRS] = [previous if previous >= 0 else 0]
            encoded = CffDict(data).to_bytes()
            size = len(encoded)
            if size == previous:
                return encoded
            previous = size
        data[PrivateDictOp.SUBRS] = [previous]
        return CffDict(data).to_bytes()

    @staticmethod
    def _build_top_dict(
        font: object,
        *,
        sid_ctx: "_SidContext",
        charset_offset: int,
        encoding_offset: int,
        charstrings_offset: int,
        private_size: int,
        private_offset: int,
    ) -> bytes:
        top = font.top_dict
        raw = getattr(top, "_raw", CffDict())
        data = {op: vals.copy() for op, vals in raw._data.items()}

        if top.version:
            data[TopDictOp.VERSION] = [sid_ctx.sid_for(top.version)]
        if top.full_name:
            data[TopDictOp.FULL_NAME] = [sid_ctx.sid_for(top.full_name)]
        if top.family_name:
            data[TopDictOp.FAMILY_NAME] = [sid_ctx.sid_for(top.family_name)]
        if top.weight:
            data[TopDictOp.WEIGHT] = [sid_ctx.sid_for(top.weight)]
        data[TopDictOp.FONT_BBOX] = [int(v) for v in top.font_bbox]
        data[TopDictOp.CHARSTRING_TYPE] = [int(top.charstring_type)]
        data[TopDictOp.ITALIC_ANGLE] = [float(top.italic_angle)]
        data[TopDictOp.IS_FIXED_PITCH] = [1 if top.is_fixed_pitch else 0]
        data[TopDictOp.UNDERLINE_POS] = [int(top.underline_position)]
        data[TopDictOp.UNDERLINE_THICK] = [int(top.underline_thickness)]
        data[TopDictOp.FONT_MATRIX] = [float(v) for v in top.font_matrix]

        data[TopDictOp.CHARSET] = [int(charset_offset)]
        data[TopDictOp.ENCODING] = [int(encoding_offset)]
        data[TopDictOp.CHARSTRINGS] = [int(charstrings_offset)]
        if private_size > 0:
            data[TopDictOp.PRIVATE] = [int(private_size), int(private_offset)]
        else:
            data.pop(TopDictOp.PRIVATE, None)

        return CffDict(data).to_bytes()

    @staticmethod
    def _register_strings(font: object, sid_ctx: "_SidContext") -> None:
        top = font.top_dict
        for value in (top.version, top.full_name, top.family_name, top.weight):
            if value:
                sid_ctx.sid_for(value)
        for gid in range(1, len(font.charstrings)):
            sid_ctx.sid_for(font.charset.name_for(gid))

    @staticmethod
    def _build_charset(font: object, sid_ctx: "_SidContext") -> bytes:
        w = BinaryWriter()
        w.write_u8(0)  # format 0
        for gid in range(1, len(font.charstrings)):
            sid = sid_ctx.sid_for(font.charset.name_for(gid))
            w.write_u16(sid)
        return w.to_bytes()

    @staticmethod
    def _build_encoding(font: object) -> tuple[str, bytes]:
        marker = int(getattr(font.top_dict, "encoding_offset", 0))
        if marker in (0, 1):
            return ("builtin", b"")

        code_to_gid = dict(getattr(font.encoding, "_code_to_gid", {}))
        if not code_to_gid:
            return ("custom", b"\x00\x00")

        max_gid = max(code_to_gid.values())
        if max_gid <= 0 or max_gid >= len(font.charstrings) or max_gid > 0xFF:
            raise FontParseException("CFF custom encoding is not representable for serialization")

        gid_to_code = {gid: code for code, gid in code_to_gid.items()}
        codes: list[int] = []
        for gid in range(1, max_gid + 1):
            code = gid_to_code.get(gid)
            if code is None or code < 0 or code > 0xFF:
                raise FontParseException("CFF custom encoding is not representable for serialization")
            codes.append(code)
        return ("custom", bytes([0, len(codes), *codes]))


class Type1Serializer:
    @staticmethod
    def serialize_pfb(font: object) -> bytes:
        from aspose_font.type1.eexec import eexec_encrypt

        header = Type1Serializer._build_ps_header(font)
        body = Type1Serializer._build_ps_body(font)
        encrypted = eexec_encrypt(body, prefix=b"\x00\x00\x00\x00")
        trailer = b"\ncleartomark\n"
        return Type1Serializer._pack_pfb(
            [
                (_TYPE1_PFB_ASCII, header),
                (_TYPE1_PFB_BINARY, encrypted + trailer),
            ]
        )

    @staticmethod
    def serialize_pfa(font: object) -> bytes:
        from aspose_font.type1.eexec import eexec_encrypt

        header = Type1Serializer._build_ps_header(font)
        body = Type1Serializer._build_ps_body(font)
        encrypted = eexec_encrypt(body, prefix=b"\x00\x00\x00\x00")
        hex_encoded = encrypted.hex().upper().encode("ascii")
        lines = b"\n".join(hex_encoded[i : i + 80] for i in range(0, len(hex_encoded), 80))
        return header + lines + b"\ncleartomark\n"

    @staticmethod
    def _build_ps_header(font: object) -> bytes:
        data = getattr(font, "_font_data", None)
        if data is None:
            raise FontParseException("Type1 serialization requires parsed Type1 data")

        font_name = (data.font_name or "UnknownType1").replace(" ", "")
        full_name = data.full_name or data.font_name or "Unknown Type1"
        family_name = data.family_name or full_name
        weight = data.weight or "Regular"
        bbox = data.font_bbox

        lines = [
            f"%!PS-AdobeFont-1.0: {font_name} 1.0",
            f"%%Title: {full_name}",
            f"/FontName /{font_name} def",
            f"/FullName ({full_name}) def",
            f"/FamilyName ({family_name}) def",
            f"/Weight ({weight}) def",
            f"/ItalicAngle {data.italic_angle:g} def",
            f"/isFixedPitch {'true' if data.is_fixed_pitch else 'false'} def",
            f"/UnderlinePosition {int(data.underline_position)} def",
            f"/UnderlineThickness {int(data.underline_thickness)} def",
            f"/FontBBox [{bbox[0]} {bbox[1]} {bbox[2]} {bbox[3]}] readonly def",
            "/Encoding 256 array",
            "0 1 255 {1 index exch /.notdef put} for",
        ]
        for code, name in enumerate(data.encoding):
            if name and name != ".notdef":
                lines.append(f"dup {code} /{name} put")
        lines.extend(
            [
                "readonly def",
                "currentfile eexec",
                "",
            ]
        )
        return "\n".join(lines).encode("latin-1", errors="replace")

    @staticmethod
    def _build_ps_body(font: object) -> bytes:
        from aspose_font.type1.eexec import charstring_decrypt_full, eexec_encrypt

        data = getattr(font, "_font_data", None)
        if data is None:
            raise FontParseException("Type1 serialization requires parsed Type1 data")

        len_iv = int(data.len_iv)

        def encode_charstring(blob: bytes) -> bytes:
            if len_iv < 0:
                return charstring_decrypt_full(blob, len_iv)
            plain = charstring_decrypt_full(blob, len_iv)
            return eexec_encrypt(plain, key=4330, len_iv=max(0, len_iv))

        out = bytearray()
        out.extend(b"dup /Private 20 dict dup begin\n")
        out.extend(b"/RD{string currentfile exch readstring pop}executeonly def\n")
        out.extend(b"/ND{noaccess def}executeonly def\n")
        out.extend(b"/NP{noaccess put}executeonly def\n")
        out.extend(f"/lenIV {len_iv} def\n".encode("ascii"))
        out.extend(f"/Subrs {len(data.subrs)} array\n".encode("ascii"))
        for i, subr in enumerate(data.subrs):
            payload = encode_charstring(subr)
            out.extend(f"dup {i} {len(payload)} RD ".encode("ascii"))
            out.extend(payload)
            out.extend(b" NP\n")
        out.extend(b"def\n")
        out.extend(b"end\n")
        out.extend(f"2 index /CharStrings {len(data.charstrings)} dict dup begin\n".encode("ascii"))
        for name in sorted(data.charstrings.keys()):
            payload = encode_charstring(data.charstrings[name])
            out.extend(f"/{name} {len(payload)} RD ".encode("latin-1", errors="replace"))
            out.extend(payload)
            out.extend(b" ND\n")
        out.extend(b"end\n")
        out.extend(b"put\n")
        out.extend(b"put\n")
        out.extend(b"mark currentfile closefile\n")
        return bytes(out)

    @staticmethod
    def _pack_pfb(segments: list[tuple[int, bytes]]) -> bytes:
        out = bytearray()
        for seg_type, payload in segments:
            out.append(0x80)
            out.append(seg_type & 0xFF)
            out.extend(len(payload).to_bytes(4, "little"))
            out.extend(payload)
        out.append(0x80)
        out.append(_TYPE1_PFB_EOF)
        return bytes(out)


class EotSerializer:
    @staticmethod
    def serialize(font: object) -> bytes:
        from aspose_font.eot.font import EotFont

        if not isinstance(font, EotFont):
            raise FontParseException("EotSerializer expects EotFont")

        inner_sfnt = font.inner_font.to_bytes()
        header = EotSerializer._build_header(
            inner_sfnt,
            version=font.eot_version,
            flags=font.flags,
            charset=font.charset,
            italic=font.italic,
            weight=font.weight,
            fs_type=font.fs_type,
        )
        return header + inner_sfnt

    @staticmethod
    def _build_header(
        inner_sfnt: bytes,
        *,
        version: int,
        flags: int,
        charset: int,
        italic: int,
        weight: int,
        fs_type: int,
    ) -> bytes:
        # This is the minimal interoperable EOT header for this project scope.
        w = BinaryWriter()
        header_size = 82
        eot_size = header_size + len(inner_sfnt)
        w.write_u32_le(eot_size)
        w.write_u32_le(len(inner_sfnt))
        w.write_u32_le(version & 0xFFFFFFFF)
        w.write_u32_le(flags & 0xFFFFFFFF)
        w.write_bytes(b"\x00" * 10)  # PANOSE
        w.write_u8(charset & 0xFF)
        w.write_u8(italic & 0xFF)
        w.write_u32_le(weight & 0xFFFFFFFF)
        w.write_u16_le(fs_type & 0xFFFF)
        w.write_u16_le(0x504C)
        w.write_u32_le(0)  # Unicode range 1
        w.write_u32_le(0)  # Unicode range 2
        w.write_u32_le(0)  # Unicode range 3
        w.write_u32_le(0)  # Unicode range 4
        w.write_u32_le(0)  # Codepage range 1
        w.write_u32_le(0)  # Codepage range 2
        w.write_u32_le(0)  # checkSumAdjustment
        w.write_u32_le(0)  # reserved1
        w.write_u32_le(0)  # reserved2
        w.write_u32_le(0)  # reserved3
        w.write_u32_le(0)  # reserved4
        w.write_u16_le(0)  # padding
        return w.to_bytes()


class _SidContext:
    def __init__(self) -> None:
        self._standard: dict[str, int] = {}
        # CFF standard SID table is 391 entries.
        for sid in range(391):
            name = resolve_sid(sid, CffIndex([]))
            if name.startswith("sid"):
                continue
            self._standard.setdefault(name, sid)
        self.custom_strings: list[str] = []
        self._custom_map: dict[str, int] = {}

    def sid_for(self, value: str) -> int:
        if value in self._standard:
            return self._standard[value]
        sid = self._custom_map.get(value)
        if sid is not None:
            return sid
        sid = 391 + len(self.custom_strings)
        self._custom_map[value] = sid
        self.custom_strings.append(value)
        return sid
