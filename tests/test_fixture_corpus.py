"""Expanded fixture-corpus coverage (SPEC-024 / FONT-27)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from aspose_font import FontLoader, FontParseException, FontType, UnsupportedFontFormatException
from aspose_font.converter import FontConverter

_FONT_LIKE_SUFFIXES = {".ttf", ".otf", ".cff", ".pfb", ".pfa", ".woff", ".woff2", ".eot", ".ttc", ".afm"}


def _repo_rel(path: Path) -> str:
    return path.as_posix()


def _all_font_like_paths() -> list[Path]:
    return sorted(
        [p for p in Path("testdata").rglob("*") if p.is_file() and p.suffix.lower() in _FONT_LIKE_SUFFIXES]
    )


def _expected_failure_map() -> dict[str, tuple[type[Exception], str]]:
    # Centralized typed-failure expectations reused by both explicit failure tests and
    # full-corpus-open KPI verification. See ADR-018.
    unsupported = (UnsupportedFontFormatException, "Unrecognised font format")
    return {
        # Bad non-font files
        "testdata/BadFonts/nonFontFile.pfa": unsupported,
        "testdata/BadFonts/nonFontFile.pfb": unsupported,
        "testdata/BadFonts/nonFontFile.ttc": unsupported,
        "testdata/BadFonts/nonFontFile.ttf": unsupported,
        # CFF / EOT malformed fixtures
        "testdata/CFF/PDFKITNET-22786.cff": (FontParseException, "Truncated CFF DICT int32"),
        "testdata/EOT/Lora-Regular.eot": (FontParseException, "Invalid EOT embedded sfnt"),
        "testdata/EOT/Montserrat-Regular.eot": (FontParseException, "Invalid EOT embedded sfnt"),
        "testdata/EOT/SLIDESJAVA_34596_font1.eot": (FontParseException, "Invalid EOT embedded sfnt"),
        "testdata/EOT/font6_Gabriola_uncompressed.eot": (FontParseException, "Invalid EOT embedded sfnt"),
        # AFM and unsupported Type1 container variants for loader
        "testdata/Helvetica.afm": unsupported,
        "testdata/Type1/CHEETAH_.AFM": unsupported,
        "testdata/Type1/Helvetica.afm": unsupported,
        "testdata/Type1/Symbol.afm": unsupported,
        "testdata/Type1/ZapfDingbats.afm": unsupported,
        "testdata/Type1/acade1.afm": unsupported,
        "testdata/Type1/antiq5.afm": unsupported,
        "testdata/Type1/arialbi.afm": unsupported,
        "testdata/Type1/courier.afm": unsupported,
        "testdata/Type1/freeeuro.afm": unsupported,
        "testdata/Type1/41897.pfb": unsupported,
        "testdata/Type1/font_LenIV_0.pfb": unsupported,
        # Known problematic PDF-derived inputs
        "testdata/PDF/48252.ttf": (FontParseException, "Unexpected end of data"),
        "testdata/PDF/552_F0.pfb": unsupported,
        "testdata/PDF/552_F1.pfb": unsupported,
        "testdata/PdfUa/BookmanOld_Hmtx.ttf": (FontParseException, "Unexpected end of data"),
        # No supported cmap path
        "testdata/TTF/BytecodeRequiredFonts/pdfnewnet_37296_1.ttf": (
            FontParseException,
            "No supported cmap subtable found",
        ),
        "testdata/TTF/BytecodeRequiredFonts/pdfnewnet_37296_2.ttf": (
            FontParseException,
            "No supported cmap subtable found",
        ),
        "testdata/TTF/F1_font_stream_Obj8.ttf": (FontParseException, "No supported cmap subtable found"),
        "testdata/TTF/cmap_format2_sample.ttf": (FontParseException, "No supported cmap subtable found"),
        # WOFF/WOFF2 malformed/problem fixtures
        "testdata/Woff/Standards/lora-v16-latin-regular.woff": (
            FontParseException,
            "WOFF sfnt reconstruction size mismatch",
        ),
        "testdata/Woff/Standards/merriweather-v22-latin-regular.woff": (
            FontParseException,
            "WOFF sfnt reconstruction size mismatch",
        ),
        "testdata/Woff/Standards/roboto-v20-latin_cyrillic-regular.woff": (
            FontParseException,
            "WOFF sfnt reconstruction size mismatch",
        ),
    }


def _coverage_metrics(paths: list[Path], attempted_paths: set[str]) -> dict[str, object]:
    by_ext: dict[str, dict[str, int]] = {}
    for path in paths:
        ext = path.suffix.lower()
        stat = by_ext.setdefault(ext, {"total": 0, "attempted": 0})
        stat["total"] += 1
        if _repo_rel(path) in attempted_paths:
            stat["attempted"] += 1
    total = len(paths)
    attempted = len(attempted_paths)
    return {
        "total": total,
        "attempted": attempted,
        "coverage_pct": (round((attempted / total) * 100.0, 2) if total else 100.0),
        "by_ext": dict(sorted(by_ext.items())),
    }


def _sample_paths(pattern: str, limit: int, excluded_names: set[str] | None = None) -> list[Path]:
    excluded_names = excluded_names or set()
    paths = [p for p in sorted(Path().glob(pattern)) if p.name not in excluded_names]
    return paths[:limit]


@pytest.mark.parametrize(
    ("pattern", "expected_types", "excluded_names", "sample_limit"),
    [
        ("testdata/Fonts/*.ttf", {FontType.TTF}, set(), 8),
        ("testdata/TTF_with_CFF/*.otf", {FontType.OTF}, set(), 6),
        ("testdata/CFF/*.cff", {FontType.CFF}, {"PDFKITNET-22786.cff"}, 8),
        ("testdata/Type1/*.pfb", {FontType.TYPE1, FontType.TYPE1_PFA}, {"41897.pfb", "font_LenIV_0.pfb"}, 8),
    ],
)
def test_new_fixture_groups_open_with_metadata_sanity(
    pattern: str,
    expected_types: set[FontType],
    excluded_names: set[str],
    sample_limit: int,
) -> None:
    # Keep runtime practical while still covering broad representative slices of each new group.
    sample = _sample_paths(pattern, sample_limit, excluded_names)
    assert sample, f"No fixtures discovered for {pattern!r}"
    # Known legacy fixtures that parse successfully but expose zero CharStrings.
    zero_glyph_allowed = {"37359.pfb", "42543.pfb"}
    # These sampled CFF fixtures intentionally ship without embedded naming fields.
    name_optional_types = {FontType.CFF}
    for path in sample:
        font = FontLoader.open(str(path))
        assert font.font_type in expected_types

        # FR-2 metadata sanity: require a usable naming field except for known nameless CFF corpus.
        if font.font_type not in name_optional_types:
            assert (font.font_name or "").strip() or (font.font_family or "").strip()

        if font.font_type in {FontType.TYPE1, FontType.TYPE1_PFA}:
            if path.name in zero_glyph_allowed:
                assert font.num_glyphs == 0
            else:
                assert font.num_glyphs > 0
        else:
            assert font.num_glyphs > 0
        assert font.metrics.units_per_em > 0


@pytest.mark.parametrize(
    "path",
    [
        "testdata/TTF/MingLiU/mingliu_win2003.ttc",
        "testdata/TTF/cambria.ttc",
        "testdata/TTF/msgothic.ttc",
    ],
)
def test_ttc_corpus_smoke_loads_default_face(path: str) -> None:
    loaded = FontLoader.load(path)
    assert loaded.font.font_type in {FontType.TTF, FontType.OTF}
    assert loaded.source.collection_index == 0
    assert loaded.source.collection_size is not None
    assert loaded.source.collection_size > 0
    assert loaded.font.num_glyphs > 0


@pytest.mark.parametrize(
    ("path", "expected_type"),
    [
        ("testdata/saira-extracondensed-semibold.woff", FontType.WOFF),
        ("testdata/saira-extracondensed-semibold.woff2", FontType.WOFF2),
        ("testdata/saira-extracondensed-semibold.eot", FontType.EOT),
    ],
)
def test_web_and_eot_positive_smoke_loads(path: str, expected_type: FontType) -> None:
    font = FontLoader.open(path)
    assert font.font_type == expected_type
    assert font.num_glyphs > 0


@pytest.mark.parametrize(
    ("path", "expected_exc", "message_part"),
    [
        (path, expected_exc, message_part)
        for path, (expected_exc, message_part) in sorted(_expected_failure_map().items())
    ],
)
def test_problem_and_malformed_fixtures_raise_typed_errors(
    path: str,
    expected_exc: type[Exception],
    message_part: str,
) -> None:
    with pytest.raises(expected_exc, match=message_part):
        FontLoader.open(path)


@pytest.mark.parametrize(
    ("source_path", "target_type"),
    [
        ("testdata/Fonts/OpenSans-Regular.ttf", FontType.WOFF2),
        ("testdata/Fonts/Roboto-Regular.ttf", FontType.EOT),
        ("testdata/TTF_with_CFF/CourierStd.otf", FontType.TTF),
        ("testdata/CFF/29645.cff", FontType.TTF),
        ("testdata/Type1/courier.pfb", FontType.CFF),
    ],
)
def test_conversion_smokes_for_new_fixture_sets(source_path: str, target_type: FontType) -> None:
    source = FontLoader.open(source_path)
    converted = FontConverter.convert(source, target_type)
    blob = converted.to_bytes()
    reloaded = FontLoader.open(blob, font_type=target_type)
    assert reloaded.num_glyphs > 0


def test_full_corpus_open_attempt_coverage_is_100_percent() -> None:
    expected_failures = _expected_failure_map()
    all_paths = _all_font_like_paths()
    assert all_paths, "No font-like fixtures found under testdata/"

    attempted_paths: set[str] = set()
    missing_failure_expectations: list[str] = []
    unexpected_failures: list[str] = []

    for path in all_paths:
        rel = _repo_rel(path)
        attempted_paths.add(rel)
        expected = expected_failures.get(rel)

        if expected is None:
            try:
                FontLoader.open(str(path))
            except Exception as exc:
                missing_failure_expectations.append(f"{rel} | {type(exc).__name__} | {exc}")
            continue

        expected_exc, message_part = expected
        try:
            FontLoader.open(str(path))
            unexpected_failures.append(f"{rel} | expected {expected_exc.__name__}({message_part!r})")
        except expected_exc as exc:
            if message_part not in str(exc):
                unexpected_failures.append(
                    f"{rel} | wrong message for {expected_exc.__name__}: {exc!s} (expected fragment: {message_part!r})"
                )
        except Exception as exc:
            unexpected_failures.append(
                f"{rel} | wrong exception {type(exc).__name__}: {exc!s} (expected {expected_exc.__name__})"
            )

    metrics = _coverage_metrics(all_paths, attempted_paths)
    print(
        f"Corpus-open KPI: attempted {metrics['attempted']}/{metrics['total']} "
        f"({metrics['coverage_pct']}%)"
    )
    print("CORPUS_OPEN_METRICS_JSON=" + json.dumps(metrics, sort_keys=True))

    missing_paths = sorted({_repo_rel(path) for path in all_paths} - attempted_paths)
    if missing_paths:
        pytest.fail("Missing corpus-open attempts:\n" + "\n".join(missing_paths))
    if float(metrics["coverage_pct"]) != 100.0:
        pytest.fail(f"Corpus-open coverage KPI failed: {metrics}")
    if missing_failure_expectations:
        pytest.fail(
            "Fixtures failed unexpectedly without expected-failure mapping:\n"
            + "\n".join(missing_failure_expectations)
        )
    if unexpected_failures:
        pytest.fail("Expected-failure verification issues:\n" + "\n".join(unexpected_failures))
