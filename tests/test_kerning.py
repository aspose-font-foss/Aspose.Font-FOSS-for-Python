"""Tests for the kerning API (SPEC-013 / ADR-011 / FONT-14)."""
from __future__ import annotations

import struct
from pathlib import Path

import pytest

from aspose_font import FontLoader, KernPair, TtfFont, WoffFont
from aspose_font._io import BinaryReader
from aspose_font._types import GlyphId
from aspose_font.ttf.tables.kern import KernTable


def _make_kern_binary(pairs: list[tuple[int, int, int]]) -> bytes:
    """Build a minimal valid kern table binary (format 0, 1 subtable)."""
    n = len(pairs)
    # Subtable: version(2) + length(2) + coverage(2) + nPairs(2) +
    #           searchRange(2) + entrySelector(2) + rangeShift(2) + n*6
    subtable_len = 6 + 8 + n * 6
    data = struct.pack(">HH", 0, 1)  # table header: version=0, nTables=1
    data += struct.pack(">HHH", 0, subtable_len, 0x0001)  # sub: ver, length, coverage (fmt0, horiz)
    data += struct.pack(">HHHH", n, n * 6, 0, 0)  # nPairs, searchRange, entrySelector, rangeShift
    for left, right, value in pairs:
        data += struct.pack(">HHh", left, right, value)
    return data


@pytest.fixture(scope="module")
def synthetic_kern() -> KernTable:
    """KernTable built from synthetic binary data: one pair (GlyphId(1), GlyphId(2), -30)."""
    raw = _make_kern_binary([(1, 2, -30), (3, 4, 20)])
    return KernTable.from_reader(BinaryReader(raw), len(raw))


@pytest.fixture(scope="session")
def opensans_pfb_path() -> Path:
    return Path(__file__).resolve().parents[1] / "testdata" / "OpenSans-Regular.pfb"


# ---------------------------------------------------------------------------
# TtfFont kern pairs via injected KernTable
# ---------------------------------------------------------------------------

def test_ttf_get_kern_pairs_nonempty_with_synthetic_kern(roboto: TtfFont) -> None:
    """Inject synthetic kern data and verify get_kern_pairs() delegates correctly."""
    raw = _make_kern_binary([(10, 20, -15)])
    roboto._tables.kern = KernTable.from_reader(BinaryReader(raw), len(raw))
    try:
        pairs = roboto.get_kern_pairs()
        assert isinstance(pairs, list)
        assert len(pairs) == 1
        assert pairs[0].value == -15
    finally:
        roboto._tables.kern = None  # restore


def test_ttf_kern_pair_types(roboto: TtfFont) -> None:
    raw = _make_kern_binary([(5, 7, -8)])
    roboto._tables.kern = KernTable.from_reader(BinaryReader(raw), len(raw))
    try:
        pair = roboto.get_kern_pairs()[0]
        assert isinstance(pair, KernPair)
        assert isinstance(pair.left, GlyphId)
        assert isinstance(pair.right, GlyphId)
        assert isinstance(pair.value, int)
    finally:
        roboto._tables.kern = None


# ---------------------------------------------------------------------------
# KernTable unit tests with synthetic data
# ---------------------------------------------------------------------------

def test_kern_table_get_returns_nonzero(synthetic_kern: KernTable) -> None:
    result = synthetic_kern.get(GlyphId(1), GlyphId(2))
    assert result == -30


def test_kern_table_get_returns_zero_for_unknown(synthetic_kern: KernTable) -> None:
    assert synthetic_kern.get(GlyphId(0), GlyphId(0)) == 0


def test_kern_table_build_lookup(synthetic_kern: KernTable) -> None:
    lookup = synthetic_kern.build_lookup()
    assert isinstance(lookup, dict)
    assert lookup[(1, 2)] == -30
    assert lookup[(3, 4)] == 20
    assert (0, 0) not in lookup


def test_kern_table_roundtrip(synthetic_kern: KernTable) -> None:
    raw = synthetic_kern.to_bytes()
    reparsed = KernTable.from_reader(BinaryReader(raw), len(raw))
    assert len(reparsed.pairs) == len(synthetic_kern.pairs)
    assert reparsed.pairs[0].value == synthetic_kern.pairs[0].value


def test_kern_table_malformed_subtable_is_skipped() -> None:
    # Header says nPairs=2, but subtable payload contains only one pair.
    malformed = bytes.fromhex(
        "0000"  # version
        "0001"  # nTables
        "0000"  # subtable version
        "0014"  # subtable length
        "0001"  # coverage (fmt 0)
        "0002"  # nPairs
        "0000"  # searchRange
        "0000"  # entrySelector
        "0000"  # rangeShift
        "0001"  # left
        "0002"  # right
        "FFE2"  # value (-30)
    )
    table = KernTable.from_reader(BinaryReader(malformed), len(malformed))
    assert table.get(GlyphId(1), GlyphId(2)) == -30


# ---------------------------------------------------------------------------
# WoffFont delegates to inner TTF
# ---------------------------------------------------------------------------

def test_woff_kern_pairs_delegated(saira_woff: WoffFont) -> None:
    pairs = saira_woff.get_kern_pairs()
    assert isinstance(pairs, list)


# ---------------------------------------------------------------------------
# CffFont returns empty list
# ---------------------------------------------------------------------------

def test_cff_kern_pairs_empty(opensans_cff) -> None:
    assert opensans_cff.get_kern_pairs() == []


# ---------------------------------------------------------------------------
# Type1Font kern pairs
# ---------------------------------------------------------------------------

def test_type1_kern_pairs_with_afm(opensans_pfb_path: Path) -> None:
    from aspose_font.type1.afm import AfmData
    font = FontLoader.open(str(opensans_pfb_path))
    afm = AfmData()
    afm.kern_pairs = [("A", "V", -50)]
    font._afm = afm
    pairs = font.get_kern_pairs()
    assert isinstance(pairs, list)
    assert len(pairs) == 1
    assert pairs[0].value == -50


def test_type1_kern_pairs_no_afm(opensans_pfb_path: Path) -> None:
    font = FontLoader.open(str(opensans_pfb_path))
    font._afm = None
    assert font.get_kern_pairs() == []


# ---------------------------------------------------------------------------
# KernPair immutability
# ---------------------------------------------------------------------------

def test_kern_pair_immutable() -> None:
    pair = KernPair(left=GlyphId(1), right=GlyphId(2), value=-30)
    with pytest.raises((AttributeError, TypeError)):
        pair.value = 0  # type: ignore[misc]
