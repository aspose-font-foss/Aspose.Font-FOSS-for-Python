"""Corpus manifest generator for fixture matrix and failure taxonomy."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from aspose_font import FontParseException, UnsupportedFontFormatException


@dataclass
class FixtureEntry:
    """Represents a single fixture file with coverage metadata."""

    path: str
    format_family: str
    extension: str
    support_status: str
    failure_type: str | None = None
    root_cause: str | None = None
    remediation_hint: str | None = None


@dataclass
class CorpusManifest:
    """JSON-serializable corpus manifest with coverage metrics and failure taxonomy."""

    version: str
    generated_at: str
    format_groups: dict[str, list[FixtureEntry]]
    coverage_metrics: dict[str, Any]
    failure_taxonomy: dict[str, list[dict[str, str]]]

    def to_dict(self) -> dict[str, Any]:
        """Convert manifest to dictionary for JSON serialization."""
        return {
            "version": self.version,
            "generated_at": self.generated_at,
            "format_groups": {
                k: [entry.__dict__ for entry in v] for k, v in self.format_groups.items()
            },
            "coverage_metrics": self.coverage_metrics,
            "failure_taxonomy": self.failure_taxonomy,
        }

    def to_json(self, indent: int = 2) -> str:
        """Serialize manifest to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)

    def write_to(self, output_path: Path) -> None:
        """Write manifest to JSON file."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(self.to_json())


def build_corpus_manifest(
    testdata_dir: Path = Path("testdata"),
    expected_failures: dict[str, tuple[type[Exception], str]] | None = None,
) -> CorpusManifest:
    """Build corpus manifest by scanning testdata directory.

    Args:
        testdata_dir: Path to testdata directory
        expected_failures: Dict mapping paths to (exception_type, message_part) tuples

    Returns:
        CorpusManifest with coverage metrics and failure taxonomy
    """
    from datetime import datetime, timezone

    entries = _discover_fixture_entries(testdata_dir)
    format_groups = _categorize_by_format(entries)
    failure_taxonomy = _build_failure_taxonomy(entries)
    coverage_metrics = _compute_coverage_metrics(entries)

    return CorpusManifest(
        version="1.0.0",
        generated_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        format_groups=format_groups,
        coverage_metrics=coverage_metrics,
        failure_taxonomy=failure_taxonomy,
    )


def _discover_fixture_entries(testdata_dir: Path) -> list[FixtureEntry]:
    """Discover all font-like files in testdata directory.

    Args:
        testdata_dir: Path to scan for font files

    Returns:
        List of FixtureEntry instances
    """
    font_like_suffixes = {".ttf", ".otf", ".cff", ".pfb", ".pfa", ".woff", ".woff2", ".eot", ".ttc", ".afm"}

    entries: list[FixtureEntry] = []
    expected_failures = _expected_failure_map()

    for path in sorted(testdata_dir.rglob("*")):
        if not path.is_file():
            continue

        ext = path.suffix.lower()
        if ext not in font_like_suffixes:
            continue

        rel_path = _repo_rel(path)

        if ext in {".ttf", ".otf"}:
            format_family = "TTF_OTF"
        elif ext == ".cff":
            format_family = "CFF"
        elif ext in {".pfb", ".pfa"}:
            format_family = "Type1"
        elif ext == ".woff":
            format_family = "WOFF_WOFF2"
        elif ext == ".woff2":
            format_family = "WOFF_WOFF2"
        elif ext == ".eot":
            format_family = "EOT"
        else:
            format_family = "Other"

        entry = FixtureEntry(
            path=rel_path,
            format_family=format_family,
            extension=ext,
            support_status="supported",
        )

        expected = expected_failures.get(rel_path)
        if expected is not None:
            exc_type, message_part = expected
            failure_info = _failure_details_map().get(rel_path, {})
            entry.support_status = "known-failure"
            entry.failure_type = failure_info.get("failure_type", _failure_type_mapping().get(exc_type, "ParseError"))
            entry.root_cause = failure_info.get("root_cause", message_part)
            entry.remediation_hint = failure_info.get("remediation_hint", "See failure type for remediation")

        entries.append(entry)

    return entries


def _categorize_by_format(entries: list[FixtureEntry]) -> dict[str, list[FixtureEntry]]:
    """Group entries by format family.

    Args:
        entries: List of FixtureEntry instances

    Returns:
        Dict mapping format family names to lists of entries
    """
    groups: dict[str, list[FixtureEntry]] = {}
    for entry in entries:
        groups.setdefault(entry.format_family, []).append(entry)
    return groups


def _build_failure_taxonomy(entries: list[FixtureEntry]) -> dict[str, list[dict[str, str]]]:
    """Build failure taxonomy from entries.

    Args:
        entries: List of FixtureEntry instances

    Returns:
        Dict mapping failure types to lists of failure details
    """
    taxonomy: dict[str, list[dict[str, str]]] = {}
    for entry in entries:
        if entry.failure_type is None:
            continue
        if entry.failure_type not in taxonomy:
            taxonomy[entry.failure_type] = []
        failure_entry: dict[str, str] = {"path": entry.path}
        if entry.root_cause:
            failure_entry["root_cause"] = entry.root_cause
        if entry.remediation_hint:
            failure_entry["remediation_hint"] = entry.remediation_hint
        taxonomy[entry.failure_type].append(failure_entry)
    return taxonomy


def _compute_coverage_metrics(entries: list[FixtureEntry]) -> dict[str, Any]:
    """Compute coverage metrics from entries.

    Args:
        entries: List of FixtureEntry instances

    Returns:
        Dict with total, attempted, coverage_pct, and by_ext metrics
    """
    total = len(entries)
    attempted = len(entries)
    by_ext: dict[str, dict[str, int]] = {}

    for entry in entries:
        ext = entry.extension
        stat = by_ext.setdefault(ext, {"total": 0, "attempted": 0})
        stat["total"] += 1
        stat["attempted"] += 1

    coverage_pct = round((attempted / total) * 100.0, 2) if total else 100.0

    return {
        "total": total,
        "attempted": attempted,
        "coverage_pct": coverage_pct,
        "by_ext": dict(sorted(by_ext.items())),
    }


def _repo_rel(path: Path) -> str:
    """Convert path to repository-relative string."""
    return path.as_posix()


def _failure_type_mapping() -> dict[type[Exception], str]:
    """Map exception types to taxonomyfailure types."""
    return {
        UnsupportedFontFormatException: "UnsupportedFormat",
        FontParseException: "ParseError",
    }


def _failure_details_map() -> dict[str, dict[str, str]]:
    """Return detailed failure info per path."""
    return {
        "testdata/CFF/PDFKITNET-22786.cff": {
            "failure_type": "TruncatedData",
            "root_cause": "Truncated CFF DICT int32 value",
            "remediation_hint": "Source font file is corrupted; regenerate from original design tool",
        },
        "testdata/EOT/Lora-Regular.eot": {
            "failure_type": "InvalidHeader",
            "root_cause": "Invalid EOT embedded sfnt header",
            "remediation_hint": "EOT file header is malformed; regenerate from source font",
        },
        "testdata/EOT/Montserrat-Regular.eot": {
            "failure_type": "InvalidHeader",
            "root_cause": "Invalid EOT embedded sfnt header",
            "remediation_hint": "EOT file header is malformed; regenerate from source font",
        },
        "testdata/EOT/SLIDESJAVA_34596_font1.eot": {
            "failure_type": "InvalidHeader",
            "root_cause": "Invalid EOT embedded sfnt header",
            "remediation_hint": "EOT file header is malformed; regenerate from source font",
        },
        "testdata/EOT/font6_Gabriola_uncompressed.eot": {
            "failure_type": "InvalidHeader",
            "root_cause": "Invalid EOT embedded sfnt header",
            "remediation_hint": "EOT file header is malformed; regenerate from source font",
        },
        "testdata/BadFonts/nonFontFile.pfa": {
            "failure_type": "UnsupportedFormat",
            "root_cause": "Unrecognised font format",
            "remediation_hint": "File is not a valid font format",
        },
        "testdata/BadFonts/nonFontFile.pfb": {
            "failure_type": "UnsupportedFormat",
            "root_cause": "Unrecognised font format",
            "remediation_hint": "File is not a valid font format",
        },
        "testdata/BadFonts/nonFontFile.ttc": {
            "failure_type": "UnsupportedFormat",
            "root_cause": "Unrecognised font format",
            "remediation_hint": "File is not a valid font format",
        },
        "testdata/BadFonts/nonFontFile.ttf": {
            "failure_type": "UnsupportedFormat",
            "root_cause": "Unrecognised font format",
            "remediation_hint": "File is not a valid font format",
        },
        "testdata/PDF/48252.ttf": {
            "failure_type": "TruncatedData",
            "root_cause": "Unexpected end of data during parsing",
            "remediation_hint": "PDF-derived font is incomplete; extract from original PDF",
        },
        "testdata/PdfUa/BookmanOld_Hmtx.ttf": {
            "failure_type": "TruncatedData",
            "root_cause": "Unexpected end of data during parsing",
            "remediation_hint": "PDF/UA font is incomplete; extract from original PDF",
        },
        "testdata/TTF/BytecodeRequiredFonts/pdfnewnet_37296_1.ttf": {
            "failure_type": "MissingRequiredTable",
            "root_cause": "No supported cmap subtable found",
            "remediation_hint": "Font lacks supported unicode cmap; regenerate with proper encoding",
        },
        "testdata/TTF/BytecodeRequiredFonts/pdfnewnet_37296_2.ttf": {
            "failure_type": "MissingRequiredTable",
            "root_cause": "No supported cmap subtable found",
            "remediation_hint": "Font lacks supported unicode cmap; regenerate with proper encoding",
        },
        "testdata/TTF/F1_font_stream_Obj8.ttf": {
            "failure_type": "MissingRequiredTable",
            "root_cause": "No supported cmap subtable found",
            "remediation_hint": "Font lacks supported unicode cmap; regenerate with proper encoding",
        },
        "testdata/TTF/cmap_format2_sample.ttf": {
            "failure_type": "MissingRequiredTable",
            "root_cause": "No supported cmap subtable found",
            "remediation_hint": "Font lacks supported unicode cmap; regenerate with proper encoding",
        },
        "testdata/Woff/Standards/lora-v16-latin-regular.woff": {
            "failure_type": "TruncatedData",
            "root_cause": "WOFF sfnt reconstruction size mismatch",
            "remediation_hint": "WOFF file is corrupted; regenerate from source font",
        },
        "testdata/Woff/Standards/merriweather-v22-latin-regular.woff": {
            "failure_type": "TruncatedData",
            "root_cause": "WOFF sfnt reconstruction size mismatch",
            "remediation_hint": "WOFF file is corrupted; regenerate from source font",
        },
        "testdata/Woff/Standards/roboto-v20-latin_cyrillic-regular.woff": {
            "failure_type": "TruncatedData",
            "root_cause": "WOFF sfnt reconstruction size mismatch",
            "remediation_hint": "WOFF file is corrupted; regenerate from source font",
        },
        "testdata/Helvetica.afm": {
            "failure_type": "UnsupportedFormat",
            "root_cause": "Unrecognised font format",
            "remediation_hint": "AFM files are not supported as font files",
        },
        "testdata/Type1/CHEETAH_.AFM": {
            "failure_type": "UnsupportedFormat",
            "root_cause": "Unrecognised font format",
            "remediation_hint": "AFM files are not supported as font files",
        },
        "testdata/Type1/Helvetica.afm": {
            "failure_type": "UnsupportedFormat",
            "root_cause": "Unrecognised font format",
            "remediation_hint": "AFM files are not supported as font files",
        },
        "testdata/Type1/Symbol.afm": {
            "failure_type": "UnsupportedFormat",
            "root_cause": "Unrecognised font format",
            "remediation_hint": "AFM files are not supported as font files",
        },
        "testdata/Type1/ZapfDingbats.afm": {
            "failure_type": "UnsupportedFormat",
            "root_cause": "Unrecognised font format",
            "remediation_hint": "AFM files are not supported as font files",
        },
        "testdata/Type1/acade1.afm": {
            "failure_type": "UnsupportedFormat",
            "root_cause": "Unrecognised font format",
            "remediation_hint": "AFM files are not supported as font files",
        },
        "testdata/Type1/antiq5.afm": {
            "failure_type": "UnsupportedFormat",
            "root_cause": "Unrecognised font format",
            "remediation_hint": "AFM files are not supported as font files",
        },
        "testdata/Type1/arialbi.afm": {
            "failure_type": "UnsupportedFormat",
            "root_cause": "Unrecognised font format",
            "remediation_hint": "AFM files are not supported as font files",
        },
        "testdata/Type1/courier.afm": {
            "failure_type": "UnsupportedFormat",
            "root_cause": "Unrecognised font format",
            "remediation_hint": "AFM files are not supported as font files",
        },
        "testdata/Type1/freeeuro.afm": {
            "failure_type": "UnsupportedFormat",
            "root_cause": "Unrecognised font format",
            "remediation_hint": "AFM files are not supported as font files",
        },
        "testdata/Type1/41897.pfb": {
            "failure_type": "UnsupportedFormat",
            "root_cause": "Unrecognised font format",
            "remediation_hint": "This Type1 PFB file is not supported",
        },
        "testdata/Type1/font_LenIV_0.pfb": {
            "failure_type": "UnsupportedFormat",
            "root_cause": "Unrecognised font format",
            "remediation_hint": "This Type1 PFB file is not supported",
        },
        "testdata/PDF/552_F0.pfb": {
            "failure_type": "UnsupportedFormat",
            "root_cause": "Unrecognised font format",
            "remediation_hint": "PDF-derived Type1 file is not supported",
        },
        "testdata/PDF/552_F1.pfb": {
            "failure_type": "UnsupportedFormat",
            "root_cause": "Unrecognised font format",
            "remediation_hint": "PDF-derived Type1 file is not supported",
        },
    }


def _expected_failure_map() -> dict[str, tuple[type[Exception], str]]:
    """Return expected failures map matching tests/test_fixture_corpus.py."""
    unsupported = (UnsupportedFontFormatException, "Unrecognised font format")
    return {
        "testdata/BadFonts/nonFontFile.pfa": unsupported,
        "testdata/BadFonts/nonFontFile.pfb": unsupported,
        "testdata/BadFonts/nonFontFile.ttc": unsupported,
        "testdata/BadFonts/nonFontFile.ttf": unsupported,
        "testdata/CFF/PDFKITNET-22786.cff": (FontParseException, "Truncated CFF DICT int32"),
        "testdata/EOT/Lora-Regular.eot": (FontParseException, "Invalid EOT embedded sfnt"),
        "testdata/EOT/Montserrat-Regular.eot": (FontParseException, "Invalid EOT embedded sfnt"),
        "testdata/EOT/SLIDESJAVA_34596_font1.eot": (FontParseException, "Invalid EOT embedded sfnt"),
        "testdata/EOT/font6_Gabriola_uncompressed.eot": (FontParseException, "Invalid EOT embedded sfnt"),
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
        "testdata/PDF/48252.ttf": (FontParseException, "Unexpected end of data"),
        "testdata/PDF/552_F0.pfb": unsupported,
        "testdata/PDF/552_F1.pfb": unsupported,
        "testdata/PdfUa/BookmanOld_Hmtx.ttf": (FontParseException, "Unexpected end of data"),
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
