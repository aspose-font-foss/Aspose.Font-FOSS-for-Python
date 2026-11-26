"""Bundled Brotli decoder for WOFF2 workflows."""

from __future__ import annotations

import contextlib
import io
from pathlib import Path
from threading import Lock

from aspose_font._exceptions import FontParseException

_VENDOR_LOCK = Lock()
_VENDOR_NS: dict[str, object] | None = None
_VENDOR_CODEC: object | None = None


class BrotliDecoder:
    """Decoder facade backed by the vendored pure-Python Brotli runtime."""

    def decode(self, data: bytes) -> bytes:
        if not data:
            return b""
        try:
            return _vendor_decompress(data)
        except FontParseException:
            raise
        except Exception as exc:  # pragma: no cover - defensive wrapper
            raise FontParseException("WOFF2 Brotli decompression failed") from exc


def _vendor_decompress(data: bytes) -> bytes:
    namespace = _load_vendor_namespace()
    decode_streams = namespace["decode_Streams"]
    decode_impl = namespace["decode_Decode"]
    decode_state = namespace["decode_state_BrotliState"]
    decode_state_init = namespace["decode_State"]

    fin = list(data)
    fout: list[int] = []
    input_stream = decode_streams.BrotliInitMemInput(fin, len(fin))
    output_stream = decode_streams.BrotliInitMemOutput(fout)
    state = decode_state()
    decode_state_init.BrotliStateInit(state)
    with contextlib.redirect_stdout(io.StringIO()):
        result = decode_impl.BrotliDecompressStreaming(input_stream, output_stream, 1, state)
    if result != 1:
        raise FontParseException("WOFF2 Brotli decompression failed")

    size = output_stream.data_.pos
    buffer = output_stream.data_.buffer
    return bytes((buffer[i] & 0xFF) for i in range(size))


def _load_vendor_namespace() -> dict[str, object]:
    global _VENDOR_NS
    global _VENDOR_CODEC

    if _VENDOR_NS is not None:
        return _VENDOR_NS

    with _VENDOR_LOCK:
        if _VENDOR_NS is not None:
            return _VENDOR_NS

        vendor_root = Path(__file__).with_name("vendor")
        vendor_code = (vendor_root / "brotlihaxe.py").read_text(encoding="utf-8")
        vendor_code = vendor_code.replace(
            "Sys._programPath = sys_FileSystem.fullPath(python_lib_Inspect.getsourcefile(Sys))\n",
            "Sys._programPath = ''\n",
        )
        vendor_code = vendor_code.replace("Main.main()", "")

        namespace: dict[str, object] = {"__name__": "aspose_font._brotli.vendor_runtime"}
        exec(compile(vendor_code, str(vendor_root / "brotlihaxe.py"), "exec"), namespace)

        data_root = vendor_root / "data"
        Brotli = namespace["Brotli"]

        def _open_input_binary(input_path: str) -> list[int]:
            path = Path(input_path)
            if not path.is_absolute():
                path = data_root / path.name
            return list(path.read_bytes())

        Brotli.OpenInputBinary = staticmethod(_open_input_binary)
        _VENDOR_CODEC = Brotli(str(data_root / "dictionary.txt"))
        _VENDOR_NS = namespace
        return namespace
