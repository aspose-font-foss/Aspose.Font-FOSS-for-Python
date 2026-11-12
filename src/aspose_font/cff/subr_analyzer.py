"""CFF/CFF2 subroutine structure analyzer (FONT-520).

Analyzes CFF and CFF2 fonts to inspect subroutine usage, call depth,
and identify unused subroutines.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aspose_font.cff.font import CffFont
    from aspose_font.cff.index import CffIndex
    from aspose_font.cff2 import Cff2Font


@dataclass
class SubroutineInfo:
    """Statistics for a single subroutine."""
    index: int
    byte_size: int
    call_count: int
    max_nesting_depth: int


@dataclass
class SubroutineAnalysis:
    """Complete analysis result for a CFF/CFF2 font."""
    font_name: str
    font_type: str
    num_glyphs: int

    global_subrs_count: int
    global_subrs_total_bytes: int
    global_subrs_in_use: list[int]
    global_subrs_unused: list[int]
    global_subrs_info: list[SubroutineInfo]

    local_subrs_count: int
    local_subrs_total_bytes: int
    local_subrs_in_use: list[int]
    local_subrs_unused: list[int]
    local_subrs_info: list[SubroutineInfo]

    max_nesting_depth: int
    charstrings_analyzed: int

    def to_dict(self) -> dict:
        """Return JSON-serializable dict."""
        return {
            "font_name": self.font_name,
            "font_type": self.font_type,
            "num_glyphs": self.num_glyphs,
            "global_subrs": {
                "count": self.global_subrs_count,
                "total_bytes": self.global_subrs_total_bytes,
                "in_use": self.global_subrs_in_use,
                "unused": self.global_subrs_unused,
                "subrs": [self._subr_info_to_dict(s) for s in self.global_subrs_info],
            },
            "local_subrs": {
                "count": self.local_subrs_count,
                "total_bytes": self.local_subrs_total_bytes,
                "in_use": self.local_subrs_in_use,
                "unused": self.local_subrs_unused,
                "subrs": [self._subr_info_to_dict(s) for s in self.local_subrs_info],
            },
            "max_nesting_depth": self.max_nesting_depth,
            "charstrings_analyzed": self.charstrings_analyzed,
        }

    @staticmethod
    def _subr_info_to_dict(info: SubroutineInfo) -> dict:
        return {
            "index": info.index,
            "byte_size": info.byte_size,
            "call_count": info.call_count,
            "max_nesting_depth": info.max_nesting_depth,
        }


class _SubrCallCounter:
    """Type2 interpreter-like walker that counts subroutine calls."""

    def __init__(
        self,
        global_subrs: CffIndex,
        local_subrs: CffIndex,
    ) -> None:
        self._global_subrs = global_subrs
        self._local_subrs = local_subrs
        self.global_call_counts: dict[int, int] = {}
        self.local_call_counts: dict[int, int] = {}
        self.max_nesting_depth: int = 0
        self._current_depth: int = 0
        self._depth_limit: int = 10

    def analyze_charstring(self, data: bytes) -> None:
        self._walk_charstring(data)

    def _walk_charstring(self, data: bytes) -> None:
        """Recursively walk a charstring, tracking call depth."""
        pos = 0
        size = len(data)

        while pos < size:
            b0 = data[pos]
            pos += 1

            if b0 == 10:
                self._handle_callsubr(data, pos)
            elif b0 == 29:
                self._handle_callgsubr(data, pos)
            elif b0 == 11:
                return
            elif b0 == 14:
                return

            if 32 <= b0 <= 246:
                pos += 0
            elif 247 <= b0 <= 250:
                pos += 1
            elif 251 <= b0 <= 254:
                pos += 1
            elif b0 == 28:
                pos += 2
            elif b0 == 255:
                pos += 4
            elif b0 == 1:
                pass
            elif b0 == 3:
                pass
            elif b0 == 4:
                pass
            elif b0 == 5:
                pass
            elif b0 == 6:
                pass
            elif b0 == 7:
                pass
            elif b0 == 8:
                pass
            elif b0 == 12:
                pos += 1
            elif b0 == 16:
                pass
            elif b0 == 18:
                pass
            elif b0 == 19:
                pos = self._skip_hintmask(data, pos)
            elif b0 == 20:
                pos = self._skip_hintmask(data, pos)
            elif b0 == 21:
                pass
            elif b0 == 22:
                pass
            elif b0 == 23:
                pass
            elif b0 == 24:
                pass
            elif b0 == 25:
                pass
            elif b0 == 26:
                pass
            elif b0 == 27:
                pass
            elif b0 == 30:
                pass
            elif b0 == 31:
                pass
            else:
                pass

    def _skip_hintmask(self, data: bytes, pos: int) -> int:
        mask_bytes = 0
        return pos + mask_bytes

    def _handle_callsubr(self, data: bytes, pos: int) -> None:
        """Handle callsubr operator (byte 10)."""
        if self._current_depth >= self._depth_limit:
            return

        if pos + 1 > len(data):
            return

        idx_byte = data[pos]
        bias = self._subr_bias(len(self._local_subrs))
        subr_idx = idx_byte + bias

        if 0 <= subr_idx < len(self._local_subrs):
            self.local_call_counts[subr_idx] = self.local_call_counts.get(subr_idx, 0) + 1
            self.max_nesting_depth = max(self.max_nesting_depth, self._current_depth + 1)

            self._current_depth += 1
            self._walk_charstring(self._local_subrs[subr_idx])
            self._current_depth -= 1

    def _handle_callgsubr(self, data: bytes, pos: int) -> None:
        """Handle callgsubr operator (byte 29)."""
        if self._current_depth >= self._depth_limit:
            return

        if pos + 1 > len(data):
            return

        idx_byte = data[pos]
        bias = self._subr_bias(len(self._global_subrs))
        subr_idx = idx_byte + bias

        if 0 <= subr_idx < len(self._global_subrs):
            self.global_call_counts[subr_idx] = self.global_call_counts.get(subr_idx, 0) + 1
            self.max_nesting_depth = max(self.max_nesting_depth, self._current_depth + 1)

            self._current_depth += 1
            self._walk_charstring(self._global_subrs[subr_idx])
            self._current_depth -= 1

    def _subr_bias(self, count: int) -> int:
        if count < 1240:
            return 107
        if count < 33900:
            return 1131
        return 32768


def analyze_cff_font(font: CffFont | Cff2Font) -> SubroutineAnalysis:
    """Analyze subroutine structure of a CFF or CFF2 font.

    Args:
        font: CffFont or Cff2Font instance

    Returns:
        SubroutineAnalysis with complete subroutine statistics
    """
    from aspose_font.cff.font import CffFont as CffFontType

    if isinstance(font, CffFontType):
        font_type = "CFF"
    else:
        font_type = "CFF2"

    global_subrs = font.global_subrs
    local_subrs = font.local_subrs

    if global_subrs is None:
        from aspose_font.cff.index import CffIndex
        global_subrs = CffIndex([])
    if local_subrs is None:
        from aspose_font.cff.index import CffIndex
        local_subrs = CffIndex([])

    counter = _SubrCallCounter(global_subrs, local_subrs)

    num_glyphs = font.num_glyphs
    for i in range(num_glyphs):
        try:
            charstring = font.charstrings[i]
            counter.analyze_charstring(charstring)
        except (IndexError, TypeError):
            continue

    global_called = set(counter.global_call_counts.keys())
    global_total = set(range(len(global_subrs)))
    global_in_use = sorted(global_called & global_total)
    global_unused = sorted(global_total - global_called)

    local_called = set(counter.local_call_counts.keys())
    local_total = set(range(len(local_subrs)))
    local_in_use = sorted(local_called & local_total)
    local_unused = sorted(local_total - local_called)

    global_subrs_info = []
    for i in range(len(global_subrs)):
        byte_size = len(global_subrs[i])
        call_count = counter.global_call_counts.get(i, 0)
        subr_info = SubroutineInfo(index=i, byte_size=byte_size, call_count=call_count, max_nesting_depth=0)
        global_subrs_info.append(subr_info)

    local_subrs_info = []
    for i in range(len(local_subrs)):
        byte_size = len(local_subrs[i])
        call_count = counter.local_call_counts.get(i, 0)
        subr_info = SubroutineInfo(index=i, byte_size=byte_size, call_count=call_count, max_nesting_depth=0)
        local_subrs_info.append(subr_info)

    global_total_bytes = sum(len(subr) for subr in global_subrs)
    local_total_bytes = sum(len(subr) for subr in local_subrs)

    return SubroutineAnalysis(
        font_name=font.font_name or "",
        font_type=font_type,
        num_glyphs=num_glyphs,
        global_subrs_count=len(global_subrs),
        global_subrs_total_bytes=global_total_bytes,
        global_subrs_in_use=global_in_use,
        global_subrs_unused=global_unused,
        global_subrs_info=global_subrs_info,
        local_subrs_count=len(local_subrs),
        local_subrs_total_bytes=local_total_bytes,
        local_subrs_in_use=local_in_use,
        local_subrs_unused=local_unused,
        local_subrs_info=local_subrs_info,
        max_nesting_depth=counter.max_nesting_depth,
        charstrings_analyzed=num_glyphs,
    )
