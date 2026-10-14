"""High-level web font bundle generation helpers."""

from __future__ import annotations

import html
import json
import time
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from aspose_font._exceptions import FontNotSupportedException
from aspose_font._font_base import Font, FontType
from aspose_font.converter import FontConverter
from aspose_font.preview import FontPreviewBuilder, PreviewImage
from aspose_font.subsetter import FontSubsetter, SubsetCoverage
from aspose_font.text import TextRenderer
from aspose_font.ttf.font import TtfFont
from aspose_font.ttf.tables.stat import normalize_static_stat_policy

_DEFAULT_PREVIEW_TEXT = "Hamburgefons 0123456789"
_SPECIMEN_TEMPLATES = ("classic", "editorial", "lab")
_VARIABLE_EXPORT_MODES = ("auto", "live", "static")


@dataclass(slots=True, frozen=True)
class WebFontAsset:
    filename: str
    media_type: str
    data: bytes


@dataclass(slots=True)
class _PreparedWebFont:
    font: Font
    export_mode: str
    export_note: str | None = None
    auto_instanced_default: bool = False
    coverage: SubsetCoverage | None = None
    export_reason: str | None = None
    supported_stat_policies: tuple[str, ...] = ()
    stat_policy_recommendation: str | None = None
    stat_policy_recommendation_reasons: tuple[str, ...] = ()
    stat_policy_next_action: str | None = None
    stat_policy_override_suggestion: str | None = None
    stat_policy_override_suggestion_reasons: tuple[str, ...] = ()
    subset_time_ms: int | None = None


@dataclass(slots=True)
class _PreparedStaticInstance:
    font: Font
    supported_stat_policies: tuple[str, ...] = ()
    stat_policy_recommendation: str | None = None
    stat_policy_recommendation_reasons: tuple[str, ...] = ()
    stat_policy_next_action: str | None = None
    stat_policy_override_suggestion: str | None = None
    stat_policy_override_suggestion_reasons: tuple[str, ...] = ()


@dataclass(slots=True)
class WebFontBundle:
    family: str
    style: str
    css: str
    html: str
    css_filename: str
    html_filename: str
    manifest_filename: str = "web-manifest.json"
    manifest: dict[str, object] = field(default_factory=dict)
    font_assets: list[WebFontAsset] = field(default_factory=list)
    preview_font: Font | None = None
    review_label: str | None = None

    def write_to(self, directory: str | Path) -> list[Path]:
        output_dir = Path(directory)
        output_dir.mkdir(parents=True, exist_ok=True)

        written: list[Path] = []
        for asset in self.font_assets:
            path = output_dir / asset.filename
            path.write_bytes(asset.data)
            written.append(path)

        css_path = output_dir / self.css_filename
        css_path.write_text(self.css, encoding="utf-8")
        written.append(css_path)

        html_path = output_dir / self.html_filename
        html_path.write_text(self.html, encoding="utf-8")
        written.append(html_path)

        manifest_path = output_dir / self.manifest_filename
        manifest_path.write_text(
            json.dumps(self.manifest, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        written.append(manifest_path)
        return written


@dataclass(slots=True)
class WebFontFamilyPackage:
    family_name: str
    bundles: list[WebFontBundle] = field(default_factory=list)
    css: str = ""
    html: str = ""
    css_filename: str = "family.css"
    html_filename: str = "family.html"
    manifest_filename: str = "family-manifest.json"
    manifest: dict[str, object] = field(default_factory=dict)
    assets: list[WebFontAsset] = field(default_factory=list)

    def write_to(self, directory: str | Path) -> list[Path]:
        output_dir = Path(directory)
        output_dir.mkdir(parents=True, exist_ok=True)

        written: list[Path] = []
        for bundle in self.bundles:
            bundle_dir = output_dir / _slugify_filename(f"{bundle.family} {bundle.style}")
            written.extend(bundle.write_to(bundle_dir))

        for asset in self.assets:
            path = output_dir / asset.filename
            path.write_bytes(asset.data)
            written.append(path)

        css_path = output_dir / self.css_filename
        css_path.write_text(self.css, encoding="utf-8")
        written.append(css_path)

        html_path = output_dir / self.html_filename
        html_path.write_text(self.html, encoding="utf-8")
        written.append(html_path)

        manifest_path = output_dir / self.manifest_filename
        manifest_path.write_text(
            json.dumps(self.manifest, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        written.append(manifest_path)
        return written


@dataclass(slots=True, frozen=True)
class DecisionReport:
    """Decision report for variable font export mode selection.

    This dataclass provides a comprehensive summary of the decision made by the
    WebFontOptimizer regarding whether to output a live variable font,
    a static instance, or a static fallback. It includes the chosen mode,
    human-readable reasons explaining the rationale, a concise summary, and
    remediation suggestions for improving the output.

    Attributes:
        mode: One of "live", "static", or "static_fallback" indicating
            the selected export mode.
        reasons: A list of human-readable strings explaining why this mode
            was chosen.
        summary: A concise, one-sentence summary suitable for display in
            constrained UI contexts (e.g., CLI output, manifest readmes).
        remediation: A list of actionable suggestions for users who want
            to change the export mode or improve the optimization outcome.
        reason: The primary reason as a single string (first item from reasons).
    """

    mode: str
    reasons: list[str]
    summary: str
    remediation: list[str]

    @property
    def reason(self) -> str:
        return self.reasons[0] if self.reasons else "No specific reason provided."

    @classmethod
    def _build_decision_pdf(cls, report: DecisionReport) -> bytes:
        import zlib

        content_str = (
            "Web Font Optimizer Decision Report\n"
            "=====================================\n"
            f"Mode: {report.mode}\n"
            f"Summary: {report.summary}\n"
            f"\nReasons:\n{chr(10).join(report.reasons) if report.reasons else 'N/A'}\n"
            f"\nRemediation:\n{chr(10).join(f'- {r}' for r in report.remediation) if report.remediation else 'N/A'}"
        )

        pdf_header = b"%PDF-1.4\n"

        obj1 = b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        obj2 = b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"

        media_box = b"[0 0 612 792]"
        obj3 = (
            b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox "
            + media_box
            + b" /Contents 4 0 R >>\nendobj\n"
        )

        compressed = zlib.compress(content_str.encode("latin-1", errors="replace"))
        obj4 = (
            b"4 0 obj\n<< /Filter /FlateDecode /Length "
            + str(len(compressed)).encode()
            + b" >>\nstream\n"
            + compressed
            + b"\nendstream\nendobj\n"
        )

        xref_obj_count = 5
        objects = [obj1, obj2, obj3, obj4]

        xref_start = len(pdf_header) + sum(len(obj) for obj in objects)
        xref_lines = [b"xref\n0 " + str(xref_obj_count).encode() + b"\n"]
        xref_lines.append(b"0000000000 65535 f \n")
        offset = len(pdf_header)
        for obj in objects:
            xref_lines.append(f"{offset:010d} 00000 n \n".encode("ascii"))
            offset += len(obj)

        trailer = (
            b"trailer\n<< /Size " + str(xref_obj_count).encode() + b" /Root 1 0 R >>\n"
            b"startxref\n" + str(xref_start).encode() + b"\n%%EOF\n"
        )

        return pdf_header + b"".join(objects) + b"".join(xref_lines) + trailer

    @classmethod
    def build_decision_pdf(cls, report: DecisionReport) -> bytes:
        return cls._build_decision_pdf(report)

    def __contains__(self, key: object) -> bool:
        return key in {"mode", "reasons", "summary", "remediation", "decision", "reason"}

    def __getitem__(self, key: str) -> object:
        if key == "decision":
            return self.mode
        if key == "reason":
            return self.reason
        if key == "summary":
            return self.summary
        if key == "remediation":
            return self.remediation
        return getattr(self, key)


@dataclass(slots=True)
class WebFontOptimizerPackage:
    bundle: WebFontBundle
    css: str = ""
    specimen_html: str = ""
    css_filename: str = "fonts.css"
    specimen_html_filename: str = "specimen.html"
    specimen_template: str = "classic"
    manifest: dict[str, object] = field(default_factory=dict)
    manifest_filename: str = "optimizer-manifest.json"
    detailed_timing: dict[str, int] | None = None
    decision_report: DecisionReport | None = None
    performance_available: bool = False
    cdn_manifest: dict[str, object] | None = None
    decision_artifact: PreviewImage | None = None

    @property
    def size_summary(self) -> dict[str, object]:
        summary = self.manifest.get("size_summary")
        return summary if isinstance(summary, dict) else {}

    @property
    def readiness(self) -> dict[str, object]:
        readiness = self.manifest.get("readiness")
        return readiness if isinstance(readiness, dict) else {}

    @property
    def notes(self) -> list[dict[str, str]]:
        notes = self.manifest.get("notes")
        if not isinstance(notes, list):
            return []
        return [note for note in notes if isinstance(note, dict)]

    def write_to(self, directory: str | Path, *, decision_report_pdf: str | Path | None = None) -> list[Path]:
        """Write package files to the directory and also create a zip archive of all artifacts."""
        output_dir = Path(directory)
        written = self.bundle.write_to(output_dir)
        css_path = output_dir / self.css_filename
        css_path.write_text(self.css, encoding="utf-8")
        written.append(css_path)
        specimen_path = output_dir / self.specimen_html_filename
        specimen_path.write_text(self.specimen_html, encoding="utf-8")
        written.append(specimen_path)
        manifest_path = output_dir / self.manifest_filename
        manifest_path.write_text(
            json.dumps(self.manifest, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        written.append(manifest_path)
        if self.decision_report is not None:
            # Write decision report JSON, HTML, and optional PDF as before

            if isinstance(self.decision_report, DecisionReport):
                decision_report_dict = {
                    "mode": self.decision_report.mode,
                    "reasons": self.decision_report.reasons,
                    "reason": self.decision_report.reason,
                    "summary": self.decision_report.summary,
                    "remediation": self.decision_report.remediation,
                }
                report_for_html = self.decision_report
                report_for_pdf = self.decision_report
            else:
                decision_report_dict = self.decision_report
                report_for_html = DecisionReport(
                    mode=decision_report_dict.get("mode", "unknown"),
                    reasons=decision_report_dict.get("reasons", []),
                    summary=decision_report_dict.get("summary", ""),
                    remediation=decision_report_dict.get("remediation", []),
                )
                report_for_pdf = report_for_html
            decision_report_path = output_dir / "decision_report.json"
            decision_report_path.write_text(
                json.dumps(decision_report_dict, indent=2, sort_keys=True),
                encoding="utf-8",
            )
            written.append(decision_report_path)
            html_path = output_dir / "decision_report.html"
            html_path.write_text(
                WebFontOptimizer.build_decision_html(report_for_html),
                encoding="utf-8",
            )
            written.append(html_path)
            if decision_report_pdf is not None:
                pdf_path = Path(decision_report_pdf)
                if not pdf_path.is_absolute():
                    pdf_path = output_dir / pdf_path
                pdf_path.parent.mkdir(parents=True, exist_ok=True)
                pdf_data = DecisionReport._build_decision_pdf(report_for_pdf)
                pdf_path.write_bytes(pdf_data)
                written.append(pdf_path)
        # Write visual decision artifact image if present
        if self.decision_artifact is not None:
            artifact_path = output_dir / self.decision_artifact.filename
            artifact_path.write_bytes(self.decision_artifact.data)
            written.append(artifact_path)
        if self.cdn_manifest is not None:
            cdn_manifest_path = output_dir / "cdn-manifest.json"
            cdn_manifest_path.write_text(
                json.dumps(self.cdn_manifest, indent=2, sort_keys=True),
                encoding="utf-8",
            )
            written.append(cdn_manifest_path)
        # Create a zip archive containing all written files for easy distribution
        zip_path = output_dir / "package.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for file_path in written:
                # Store files with relative paths inside the zip
                arcname = file_path.relative_to(output_dir)
                zf.write(file_path, arcname)
        written.append(zip_path)
        return written


@dataclass(slots=True)
class FamilyReviewExportPackage:
    family_name: str
    board: PreviewImage
    assets: list[WebFontAsset] = field(default_factory=list)
    markdown_filename: str = "family-review-board.md"
    html_filename: str = "family-review-board.html"
    manifest_filename: str = "family-review-board-manifest.json"
    markdown: str = ""
    html: str = ""
    manifest: dict[str, object] = field(default_factory=dict)

    def write_to(self, directory: str | Path) -> list[Path]:
        output_dir = Path(directory)
        output_dir.mkdir(parents=True, exist_ok=True)

        written: list[Path] = []
        board_path = output_dir / self.board.filename
        board_path.write_bytes(self.board.data)
        written.append(board_path)

        for asset in self.assets:
            path = output_dir / asset.filename
            path.write_bytes(asset.data)
            written.append(path)

        markdown_path = output_dir / self.markdown_filename
        markdown_path.write_text(self.markdown, encoding="utf-8")
        written.append(markdown_path)

        html_path = output_dir / self.html_filename
        html_path.write_text(self.html, encoding="utf-8")
        written.append(html_path)

        manifest_path = output_dir / self.manifest_filename
        manifest_path.write_text(
            json.dumps(self.manifest, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        written.append(manifest_path)
        return written


class WebFontOptimizer:
    def __init__(self, font_path: str | Path, output_dir: str | Path) -> None:
        """Create an optimizer helper for reading decision reports.

        Args:
            font_path: Path to the source font file (not used for report generation).
            output_dir: Directory containing the optimizer output including
                ``optimizer-manifest.json``.
        """
        self.font_path = Path(font_path)
        self.output_dir = Path(output_dir)

    def generate_decision_report(self) -> dict:
        """Read ``optimizer-manifest.json`` and build a concise decision report.

        Returns:
            dict with keys:
                "mode": Export mode string (e.g., "live", "static", "fallback").
                "css_snippet": A minimal ``@font-face`` CSS rule.
                "readiness_score": Integer readiness metric (0‑100).
        """
        manifest_path = self.output_dir / "optimizer-manifest.json"
        if not manifest_path.is_file():
            raise FileNotFoundError(f"Optimizer manifest not found: {manifest_path}")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

        mode = manifest.get("export_mode", "fallback")
        woff2_files = manifest.get("woff2_files", [])
        woff2_file = woff2_files[0] if woff2_files else ""
        family = manifest.get("family_name", "Unknown")
        css_snippet = (
            f"@font-face {{\n"
            f"    font-family: \"{family}\";\n"
            f"    src: url(\"{woff2_file}\") format('woff2');\n"
            f"    font-display: swap;\n"
            f"}}"
        )
        readiness = manifest.get("readiness", {})
        score = int(readiness.get("score", 100))
        return {"mode": mode, "css_snippet": css_snippet, "readiness_score": score}

    def build_decision_report(self) -> dict:
        """Return a concise decision report with decision and reason.

        Reads the optimizer manifest and extracts the exported decision mode and
        the human‑readable reason field (if present). If the manifest lacks a
        decision_report section, raises FileNotFoundError.
        """
        manifest_path = self.output_dir / "optimizer-manifest.json"
        if not manifest_path.is_file():
            raise FileNotFoundError(f"Optimizer manifest not found: {manifest_path}")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        dr = manifest.get("decision_report", {})
        decision = dr.get("mode") or dr.get("decision")
        reason = dr.get("reason", "")
        return {"decision": decision, "reason": reason}

    @staticmethod
    def _build_css_snippet(family: str, css_filename: str, font: Font) -> str:
        descriptors = WebFontBuilder._font_face_descriptors(font)
        descriptor_lines = "\n".join(f"  {name}: {value};" for name, value in descriptors)
        return (
            f"@font-face {{\n"
            f"  font-family: '{_escape_css_string(family)}';\n"
            f"  src: url('./{css_filename}') format('woff2');\n"
            f"{descriptor_lines}\n"
            "  font-display: swap;\n"
            "}}"
        )

    @staticmethod
    def _build_specimen_styles(family: str, specimen_template: str, css_filename: str) -> str:
        return (
            f"@import url('./{css_filename}');\n"
            f"{_specimen_template_css(specimen_template)}\n"
            "body {\n"
            "  font-family: system-ui, sans-serif;\n"
            "  margin: 2rem;\n"
            "}\n"
        )

    @staticmethod
    def _build_css_unicode_range(coverage_dict: dict[str, object] | None) -> str:
        if coverage_dict is None:
            return "U+0000-FFFD"
        groups = coverage_dict.get("groups", [])
        if not groups:
            return "U+0000-FFFD"
        range_parts = []
        for group in groups:
            if group.get("kind") == "preset":
                preset_name = group.get("label", "")
                preset_ranges = _preset_to_unicode_ranges(preset_name)
                if preset_ranges:
                    range_parts.extend(preset_ranges)
        if range_parts:
            return ", ".join(range_parts)
        coverage_data = coverage_dict.get("coverage")
        if isinstance(coverage_data, dict):
            covered = coverage_data.get("covered_codepoints", [])
            if covered:
                range_parts = WebFontOptimizer._codepoints_to_unicode_ranges(covered)
                if range_parts:
                    return ", ".join(range_parts)
        return "U+0000-FFFD"

    @staticmethod
    def _codepoints_to_unicode_ranges(codepoints: list[int]) -> list[str]:
        if not codepoints:
            return []
        sorted_cps = sorted(set(codepoints))
        ranges = []
        start = sorted_cps[0]
        end = sorted_cps[0]
        for cp in sorted_cps[1:]:
            if cp == end + 1:
                end = cp
            else:
                if start == end:
                    ranges.append(f"U+{start:04X}")
                else:
                    ranges.append(f"U+{start:04X}-{end:04X}")
                start = cp
                end = cp
        if start == end:
            ranges.append(f"U+{start:04X}")
        else:
            ranges.append(f"U+{start:04X}-{end:04X}")
        return ranges

    @staticmethod
    def _normalize_font_display(value: str) -> str:
        normalized = value.strip().lower()
        if normalized in ("optional", "swap", "fallback", "block"):
            return normalized
        return "swap"

    @staticmethod
    def build_fonts_css(
        font: Font,
        family: str,
        font_assets: list[WebFontAsset],
        font_display: str,
        specimen_template: str,
        coverage: dict[str, object] | None = None,
    ) -> str:
        descriptors = WebFontBuilder._font_face_descriptors(font)
        src_items = [
            f"url('./{asset.filename}') format('{_css_format(asset.filename)}')"
            for asset in font_assets
        ]
        descriptor_lines = "\n".join(f"  {name}: {value};" for name, value in descriptors)
        unicode_range = WebFontOptimizer._build_css_unicode_range(coverage)
        font_display_value = WebFontOptimizer._normalize_font_display(font_display)
        return (
            f"@font-face {{\n"
            f"  font-family: '{_escape_css_string(family)}';\n"
            f"  src: {', '.join(src_items)};\n"
            f"  {descriptor_lines}\n"
            f"  unicode-range: {unicode_range};\n"
            f"  font-display: {font_display_value};\n"
            "}}\n\n"
            "body {\n"
            "  font-family: system-ui, sans-serif;\n"
            "  margin: 2rem;\n"
            "  color: #111;\n"
            "  background: #faf8f2;\n"
            "}\n\n"
            ".specimen {\n"
            f"  font-family: '{_escape_css_string(family)}', sans-serif;\n"
            "  font-size: 64px;\n"
            "  line-height: 1.2;\n"
            "  margin: 1rem 0 2rem;\n"
            "}\n\n"
            ".axis-controls {\n"
            "  display: grid;\n"
            "  gap: 1rem;\n"
            "  margin: 1.5rem 0 2rem;\n"
            "  max-width: 48rem;\n"
            "}\n\n"
            ".axis-control {\n"
            "  padding: 1rem;\n"
            "  border: 1px solid #d9d1c7;\n"
            "  border-radius: 0.75rem;\n"
            "  background: #fffdf8;\n"
            "}\n\n"
            ".axis-control label {\n"
            "  display: flex;\n"
            "  justify-content: space-between;\n"
            "  gap: 1rem;\n"
            "  font-weight: 600;\n"
            "}\n\n"
            ".axis-control input {\n"
            "  width: 100%;\n"
            "  margin-top: 0.75rem;\n"
            "}\n\n"
            ".axis-range {\n"
            "  margin-top: 0.5rem;\n"
            "  color: #6f6354;\n"
            "  font-size: 0.95rem;\n"
            "}\n"
            f"{_specimen_template_css(specimen_template)}"
        )

    @staticmethod
    def build_specimen_html(
        font: Font,
        family: str,
        style: str,
        css_filename: str,
        specimen_html_filename: str,
        preview_text: str,
        specimen_template: str,
        export_mode: str,
        export_note: str | None,
    ) -> str:
        axis_markup = WebFontBuilder._variable_axis_markup(font)
        template_label = html.escape(_format_template_label(specimen_template))
        export_label = html.escape(_format_export_mode_label(export_mode))
        export_note_markup = (
            f"  <p><strong>Export Note:</strong> {html.escape(export_note)}</p>\n"
            if export_note
            else ""
        )
        css_snippet = WebFontOptimizer._build_css_snippet(family, css_filename, font)
        return (
            "<!doctype html>\n"
            "<html lang=\"en\">\n"
            "<head>\n"
            "  <meta charset=\"utf-8\">\n"
            "  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
            f"  <title>{html.escape(family)} specimen</title>\n"
            "  <style>\n"
            f"{WebFontOptimizer._build_specimen_styles(family, specimen_template, css_filename)}\n"
            "  </style>\n"
            "</head>\n"
            f"  <body class=\"specimen-template-{html.escape(specimen_template)}\">\n"
            f"  <h1>{html.escape(family)}</h1>\n"
            f"  <p><strong>Style:</strong> {html.escape(style)}</p>\n"
            f"  <p><strong>Export Mode:</strong> {export_label}</p>\n"
            f"  <p><strong>Template:</strong> {template_label}</p>\n"
            f"  <p><strong>Fonts CSS:</strong> <code>{html.escape(css_filename)}</code></p>\n"
            f"{export_note_markup}"
            f"  <div class=\"specimen\">{html.escape(preview_text)}</div>\n"
            f"{axis_markup}"
            f"  <section>\n"
            "    <h2>Copyable @font-face</h2>\n"
            "    <pre><code>"
            f"{html.escape(css_snippet)}"
            "</code></pre>\n"
            "  </section>\n"
            "</body>\n"
            "</html>\n"
        )

    @classmethod
    def build(
        cls,
        font: Font,
        *,
        source_path: str | Path | None = None,
        file_stem: str | None = None,
        include_woff: bool = True,
        font_display: str = "swap",
        preview_text: str = _DEFAULT_PREVIEW_TEXT,
        instance_coordinates: dict[str, float] | None = None,
        instance_name: str | None = None,
        presets: str | Iterable[str] = (),
        text: str = "",
        codepoints: Iterable[int] = (),
        ranges: Iterable[tuple[int, int] | range] = (),
        specimen_template: str = "classic",
        variable_mode: str = "auto",
        naming_strategy: str = "instance-family",
        family_suffix: str | None = None,
        legacy_family_name: str | None = None,
        typographic_family_name: str | None = None,
        legacy_style_name: str | None = None,
        typographic_style_name: str | None = None,
        stat_policy: str = "drop",
        detailed_reporting: bool = False,
        decision_report: bool = False,
        decision_artifact: bool = False,
        skip_diagnostics: bool = False,
        preserve_variable: bool = False,
        cdn_base_url: str = "https://cdn.example.com",
        feature_variation_tag: str | None = None,
    ) -> WebFontOptimizerPackage:
        codepoint_values = tuple(codepoints)
        range_values = tuple(ranges)
        template_name = _normalize_specimen_template(specimen_template)
        variable_mode_name = _normalize_variable_export_mode(variable_mode)
        naming_strategy_name = _normalize_naming_strategy(naming_strategy)
        stat_policy_name = normalize_static_stat_policy(stat_policy)
        codepoint_values = tuple(codepoints)
        range_values = tuple(ranges)
        start_time = time.perf_counter()
        load_start = time.perf_counter()
        detailed_timing: dict[str, int] = {}
        prepared = WebFontBuilder._prepare_font(
            font,
            instance_coordinates=instance_coordinates,
            instance_name=instance_name,
            presets=presets,
            text=text,
            codepoints=codepoint_values,
            ranges=range_values,
            variable_mode=variable_mode_name,
            naming_strategy=naming_strategy_name,
            family_suffix=family_suffix,
            legacy_family_name=legacy_family_name,
            typographic_family_name=typographic_family_name,
            legacy_style_name=legacy_style_name,
            typographic_style_name=typographic_style_name,
            stat_policy=stat_policy_name,
            preserve_variable=preserve_variable,
        )
        load_time_ms = round((time.perf_counter() - load_start) * 1000)
        if detailed_reporting:
            detailed_timing["load_time_ms"] = load_time_ms
            if prepared.subset_time_ms is not None:
                detailed_timing["subset_time_ms"] = prepared.subset_time_ms
        family = (prepared.font.font_family or prepared.font.font_name or "Web Font").strip() or "Web Font"
        style = (prepared.font.font_style or "Regular").strip() or "Regular"
        stem = file_stem or _slugify_filename(f"{family}-{style}")
        subset_start = time.perf_counter()
        font_assets = [WebFontBuilder._make_font_asset(prepared.font, stem, FontType.WOFF2)]
        if include_woff:
            font_assets.append(WebFontBuilder._make_font_asset(prepared.font, stem, FontType.WOFF))
        compress_time_ms = round((time.perf_counter() - subset_start) * 1000)
        if detailed_reporting:
            detailed_timing["compress_time_ms"] = compress_time_ms
        bundle = WebFontBuilder.build(
            font,
            file_stem=file_stem,
            include_woff=include_woff,
            font_display=font_display,
            preview_text=preview_text,
            instance_coordinates=instance_coordinates,
            instance_name=instance_name,
            presets=presets,
            text=text,
            codepoints=codepoint_values,
            ranges=range_values,
            specimen_template=specimen_template,
            variable_mode=variable_mode,
            naming_strategy=naming_strategy,
            family_suffix=family_suffix,
            legacy_family_name=legacy_family_name,
            typographic_family_name=typographic_family_name,
            legacy_style_name=legacy_style_name,
            typographic_style_name=typographic_style_name,
            stat_policy=stat_policy,
            preserve_variable=preserve_variable,
        )
        coverage = bundle.manifest.get("subset", {}).get("coverage")
        css_start = time.perf_counter()
        css = cls.build_fonts_css(
            prepared.font,
            family,
            font_assets=bundle.font_assets,
            font_display=font_display,
            specimen_template=template_name,
            coverage=coverage,
        )
        css_seconds = round(time.perf_counter() - css_start, 4)
        specimen_start = time.perf_counter()
        specimen_html = cls.build_specimen_html(
            prepared.font,
            family,
            bundle.style,
            bundle.css_filename,
            bundle.html_filename,
            preview_text,
            template_name,
            bundle.manifest.get("export_mode", "static"),
            bundle.manifest.get("export_note"),
        )
        specimen_html_seconds = round(time.perf_counter() - specimen_start, 4)
        manifest_start = time.perf_counter()
        elapsed_ms = round((time.perf_counter() - start_time) * 1000)
        elapsed_seconds = round(time.perf_counter() - start_time, 4)
        if skip_diagnostics:
            size_summary = {}
            readiness = {"score": 0, "status": "unknown", "reasons": [], "performance_note": None}
            notes = []
            size_summary_seconds = 0.0
        else:
            size_summary_start = time.perf_counter()
            size_summary = cls._build_size_summary(bundle, source_path=source_path)
            size_summary_seconds = round(time.perf_counter() - size_summary_start, 4)
            readiness = cls._build_readiness(bundle, include_woff=include_woff, elapsed_ms=elapsed_ms)
            notes = cls._build_notes(bundle, readiness=readiness, include_woff=include_woff)
        manifest_write_time_ms = round((time.perf_counter() - manifest_start) * 1000)
        if detailed_reporting:
            detailed_timing["manifest_write_time_ms"] = manifest_write_time_ms
        user_export_mode = cls._normalize_user_export_mode(bundle.manifest.get("export_mode", "static"))
        export_mode_value = bundle.manifest.get("export_mode", "static")
        source_is_variable = isinstance(font, TtfFont) and font.is_variable
        decision_report = cls._generate_decision_report(
            source_is_variable=source_is_variable,
            export_mode=export_mode_value,
            variable_mode=variable_mode_name,
            source_path=source_path,
        ) if decision_report else None
        decision_value = decision_report.mode if decision_report else None
        performance: dict[str, float | int] = {
            "elapsed_ms": elapsed_ms,
            "total_seconds": elapsed_seconds,
            "size_summary_seconds": size_summary_seconds,
            "css_generation_seconds": css_seconds,
            "specimen_html_seconds": specimen_html_seconds,
        }
        if detailed_reporting:
            performance.update(detailed_timing)
        size_comparison: dict[str, int | float | None] = {
            "source_bytes": size_summary.get("source_bytes") if isinstance(size_summary, dict) else None,
            "output_bytes": size_summary.get("output_bytes") if isinstance(size_summary, dict) else None,
            "compression_ratio": size_summary.get("compression_ratio") if isinstance(size_summary, dict) else None,
            "elapsed_ms": elapsed_ms,
        }
        manifest = {
            "kind": "web_optimizer_package",
            "bundle_manifest_filename": bundle.manifest_filename,
            "family": bundle.family,
            "style": bundle.style,
            "export_mode": user_export_mode,
            "decision": decision_value,
            "export_mode_decision": decision_value,
            "source_path": str(source_path) if source_path is not None else None,
            "local_processing": True,
            "privacy_note": "Fonts are processed locally by the Python workflow; no upload is required.",
            "performance": performance,
            "size_summary": size_summary,
            "size_comparison": size_comparison,
            "readiness": readiness,
            "notes": notes,
            "bundle": bundle.manifest,
            "decision_report": {
                "mode": decision_report.mode if decision_report else None,
                "decision": decision_report.mode if decision_report else None,
                "reasons": decision_report.reasons if decision_report else None,
                "reason": decision_report.reason if decision_report else None,
                "summary": decision_report.summary if decision_report else None,
                "remediation": decision_report.remediation if decision_report else None,
            } if decision_report else None,
            "performance_available": True,
        }
        if feature_variation_tag is not None:
            manifest["selected_feature_variation"] = feature_variation_tag
        cdn_manifest_entries: list[dict[str, str]] = []
        if cdn_base_url:
            for asset in bundle.font_assets:
                filename = asset.filename
                cdn_path = f"{cdn_base_url.rstrip('/')}/{filename}"
                entry: dict[str, str] = {
                    "font_url": cdn_path,
                    "cache_control": "max-age=31536000",
                }
                cdn_manifest_entries.append(entry)

        cdn_manifest: dict[str, object] | None = None
        if cdn_manifest_entries:
            cdn_manifest = {"entries": cdn_manifest_entries}

        # Optional visual decision artifact generation
        decision_artifact_img: PreviewImage | None = None
        if decision_artifact:
            # Build simple textual summary for the artifact
            summary_lines = [
                f"Decision: {decision_report.mode if decision_report else 'N/A'}",
                f"Readiness: {readiness.get('score', 0)} ({readiness.get('status', 'unknown')})",
                f"Output size: {size_summary.get('output_bytes', 0)} bytes",
            ]
            summary_text = "\n".join(summary_lines)
            # Use FontPreviewBuilder to render the summary text onto a PNG
            decision_artifact_img = FontPreviewBuilder.build(
                font=prepared.font,
                text=summary_text,
                size=72.0,
                background=(255, 253, 248),
                output_format="png",
                file_stem="decision-artifact",
            )

        return WebFontOptimizerPackage(
            bundle=bundle,
            css=css,
            css_filename="fonts.css",
            specimen_html=specimen_html,
            specimen_html_filename="specimen.html",
            specimen_template=template_name,
            manifest=manifest,
            detailed_timing=detailed_timing if detailed_reporting else None,
            decision_report=decision_report,
            performance_available=True,
            cdn_manifest=cdn_manifest,
            decision_artifact=decision_artifact_img,
        )

    @staticmethod
    def _generate_decision_report(
        source_is_variable: bool,
        export_mode: str,
        variable_mode: str,
        source_path: str | Path | None,
    ) -> DecisionReport:
        """Generate a decision report explaining the chosen export mode.

        Args:
            source_is_variable: True if source font is variable (TTF with gvar/HVAR tables)
            export_mode: Internal export mode from WebFontBuilder (e.g., "variable-live", "static-instance")
            variable_mode: User-requested variable mode ("live", "static", "auto")
            source_path: Path to source font file

        Returns:
            DecisionReport with keys:
                - mode: One of "live", "static", "static_fallback"
                - reasons: A list of human-readable explanation strings
                - summary: A concise one-sentence summary
                - remediation: A list of actionable suggestions
        """
        decision: str
        reasons: list[str] = []
        remediation: list[str] = []

        if export_mode in (
            "static-subset",
            "static-subset-from-variable-default",
            "static-subset-from-instance",
        ):
            decision = "static"
            reasons.append("Subset request produced a static instance from variable source.")
            remediation.append(
                "To preserve variable font functionality, use --variable-mode live or avoid subsetting."
            )
            remediation.append(
                "If variable axes are required, instantiate specific named instances instead of subsetting."
            )
        elif (variable_mode == "live" or export_mode == "variable-live") and source_is_variable:
            decision = "live"
            reasons.append("Variable font with variable export mode enabled. Output supports variable axes.")
            remediation.append(
                "Variable font ready for web use. Consider adding unicode-range subsetting to reduce payload size."
            )
        elif variable_mode in ("auto", "static") and source_is_variable:
            decision = "static"
            reasons.append("Static instance created via explicit coordinates or named instance selection.")
            remediation.append(
                "To export live variable font, use --variable-mode live or omit --instance/--instance-name."
            )
        else:
            decision = "static_fallback"
            reasons.append("Font is not variable or variable font instancing not applicable. Fallback to static export.")
            remediation.append(
                "For variable font support, use a variable font source (TTF/OTF with fvar/gvar tables)."
            )

        summary = WebFontOptimizer._build_decision_summary(
            decision, reasons, source_is_variable, export_mode, variable_mode
        )

        return DecisionReport(mode=decision, reasons=reasons, summary=summary, remediation=remediation)

    @staticmethod
    def _build_decision_summary(
        mode: str,
        reasons: list[str],
        source_is_variable: bool,
        export_mode: str,
        variable_mode: str,
    ) -> str:
        """Build a concise, one-sentence summary of the decision."""
        if mode == "live":
            return "Exporting live variable font with full axis support."
        if mode == "static":
            if export_mode.startswith("static-subset"):
                return "Exporting static instance from subset operation."
            return "Exporting static instance via explicit coordinates or named instance selection."
        if mode == "static_fallback":
            if source_is_variable:
                return "Variable font detected but output limited to static due to subset or configuration."
            return "Static font or non-variable source; static export is appropriate."
        return "Export mode determined based on font characteristics and user configuration."

    @staticmethod
    def decide_output(
        font: Font,
        variable_mode: str = "auto",
    ) -> dict[str, object]:
        """Generate a decision report for variable font export mode.

        Args:
            font: The font to analyze
            variable_mode: User-requested variable mode ("live", "static", "auto")

        Returns:
            Dict with keys:
                - decision: One of "live", "static", "static_fallback"
                - reasons: List of human-readable explanation strings
        """
        source_is_variable = isinstance(font, TtfFont) and getattr(font, "is_variable", False)
        decision_report = WebFontOptimizer._generate_decision_report(
            source_is_variable=source_is_variable,
            export_mode="variable-live",
            variable_mode=variable_mode,
            source_path=None,
        )
        return {
            "decision": decision_report.mode,
            "reasons": decision_report.reasons,
        }

    @staticmethod
    def _build_size_summary(
        bundle: WebFontBundle,
        *,
        source_path: str | Path | None,
    ) -> dict[str, object]:
        source_size: int | None = None
        if source_path is not None:
            path = Path(source_path)
            if path.exists():
                source_size = path.stat().st_size

        font_assets = [
            {
                "filename": asset.filename,
                "media_type": asset.media_type,
                "bytes": len(asset.data),
            }
            for asset in bundle.font_assets
        ]
        css_bytes = len(bundle.css.encode("utf-8"))
        html_bytes = len(bundle.html.encode("utf-8"))
        base_manifest_bytes = len(
            json.dumps(bundle.manifest, indent=2, sort_keys=True).encode("utf-8")
        )
        total_web_font_bytes = sum(int(asset["bytes"]) for asset in font_assets)
        total_package_bytes = total_web_font_bytes + css_bytes + html_bytes + base_manifest_bytes
        reduction = None
        reduction_percent = None
        if source_size:
            reduction = source_size - total_web_font_bytes
            reduction_percent = round((reduction / source_size) * 100, 2)
        woff2_bytes = 0
        woff_bytes = 0
        for asset in font_assets:
            if asset["media_type"] == "font/woff2":
                woff2_bytes = int(asset["bytes"])
            elif asset["media_type"] == "font/woff":
                woff_bytes = int(asset["bytes"])
        compression_ratio = None
        if source_size and woff2_bytes:
            compression_ratio = round(woff2_bytes / source_size, 4)
        return {
            "source_bytes": source_size,
            "output_bytes": total_web_font_bytes,
            "woff2_bytes": woff2_bytes,
            "woff_bytes": woff_bytes,
            "compression_ratio": compression_ratio,
            "font_assets": font_assets,
            "css_bytes": css_bytes,
            "html_bytes": html_bytes,
            "bundle_manifest_bytes": base_manifest_bytes,
            "total_web_font_bytes": total_web_font_bytes,
            "total_package_bytes": total_package_bytes,
            "web_font_delta_vs_source_bytes": reduction,
            "web_font_delta_vs_source_percent": reduction_percent,
        }

    @staticmethod
    def _build_readiness(
        bundle: WebFontBundle, *, include_woff: bool, elapsed_ms: int | None = None
    ) -> dict[str, object]:
        score = 100
        reasons: list[str] = []
        manifest = bundle.manifest
        export_mode = str(manifest.get("export_mode") or "")
        subset = manifest.get("subset")
        coverage = subset.get("coverage") if isinstance(subset, dict) else None

        if isinstance(coverage, dict):
            missing_count = int(coverage.get("missing_count", 0))
            requested_count = int(coverage.get("requested_count", 0))
            if missing_count:
                penalty = 15
                score -= penalty
                reasons.append("subset-missing-codepoints")
            elif requested_count:
                reasons.append("subset-fully-covered")

        if export_mode == "static-subset-from-variable-default":
            score -= 15
            reasons.append("variable-subset-static-fallback")
        elif export_mode in {"static-instance", "static-subset-from-instance"} and manifest.get(
            "source_is_variable"
        ):
            score -= 8
            reasons.append("variable-export-static")

        if not include_woff:
            score -= 5
            reasons.append("woff-fallback-disabled")

        score = max(0, min(100, score))
        if score >= 90:
            status = "ready"
        elif score >= 75:
            status = "caution"
        elif score >= 60:
            status = "warning"
        else:
            status = "blocked"
        performance_note = None
        if elapsed_ms is not None:
            performance_note = f"Processed in {elapsed_ms} ms"
        return {
            "score": score,
            "status": status,
            "reasons": reasons,
            "performance_note": performance_note,
        }

    @staticmethod
    def _normalize_user_export_mode(internal_mode: str) -> str:
        if internal_mode == "variable-live":
            return "live"
        if internal_mode == "static-subset-from-variable-default":
            return "static-fallback"
        return "static"

    @staticmethod
    def _build_notes(
        bundle: WebFontBundle,
        *,
        readiness: dict[str, object],
        include_woff: bool,
    ) -> list[dict[str, str]]:
        notes: list[dict[str, str]] = []
        manifest = bundle.manifest
        subset = manifest.get("subset")
        coverage = subset.get("coverage") if isinstance(subset, dict) else None
        if isinstance(coverage, dict) and int(coverage.get("missing_count", 0)):
            notes.append(
                {
                    "code": "subset-missing-codepoints",
                    "severity": "warning",
                    "message": "Some requested characters are not covered by the optimized font.",
                }
            )
        export_mode = str(manifest.get("export_mode") or "")
        if export_mode == "static-subset-from-variable-default":
            notes.append(
                {
                    "code": "variable-subset-static-fallback",
                    "severity": "info",
                    "message": (
                        "Variable-font subsetting produced a static default instance; review "
                        "whether live axes are required for this handoff."
                    ),
                }
            )
        elif export_mode in {"static-instance", "static-subset-from-instance"} and manifest.get(
            "source_is_variable"
        ):
            notes.append(
                {
                    "code": "variable-export-static",
                    "severity": "info",
                    "message": "The source is variable, but this web package exports static files.",
                }
            )
        if not include_woff:
            notes.append(
                {
                    "code": "woff-fallback-disabled",
                    "severity": "info",
                    "message": "Only WOFF2 font output was requested; add WOFF if legacy fallback is needed.",
                }
            )
        readiness_status = readiness.get("status", "")
        readiness_reasons = readiness.get("reasons", [])
        if readiness_status in ("caution", "warning"):
            notes.append(
                {
                    "code": "readiness_diagnostics",
                    "severity": "info",
                    "message": f"Readiness status: {readiness_status}. Reason: {', '.join(readiness_reasons)}.",
                }
            )
        optimization_suggestions: list[str] = []
        if "subset-missing-codepoints" in readiness_reasons:
            optimization_suggestions.append("Consider expanding the subset coverage to include missing characters.")
        if "variable-subset-static-fallback" in readiness_reasons:
            optimization_suggestions.append("For variable font support, consider using live variable mode instead of static subset.")
        if "variable-export-static" in readiness_reasons:
            optimization_suggestions.append("To preserve variable font functionality, use variable-live export mode.")
        if "woff-fallback-disabled" in readiness_reasons:
            optimization_suggestions.append("Enable WOFF output for broader browser compatibility as fallback to WOFF2.")
        if optimization_suggestions:
            notes.append(
                {
                    "code": "optimization_suggestions",
                    "severity": "info",
                    "message": " ".join(optimization_suggestions),
                }
            )
        if not notes and readiness_status == "ready":
            notes.append(
                {
                    "code": "ready-for-handoff",
                    "severity": "info",
                    "message": "The generated web font package is ready for frontend handoff.",
                }
            )
        return notes

    @staticmethod
    def generate_summary(package: WebFontOptimizerPackage) -> str:
        """Generate a markdown summary string for README visibility."""
        size_summary = package.size_summary
        readiness = package.readiness
        coverage = package.bundle.manifest.get("subset", {}).get("coverage", {})

        source_bytes = size_summary.get("source_bytes")
        total_web_font_bytes = size_summary.get("total_web_font_bytes", 0)
        compression_ratio = size_summary.get("compression_ratio")
        reduction_percent = size_summary.get("web_font_delta_vs_source_percent")

        score = readiness.get("score", 0)
        status = readiness.get("status", "unknown")

        covered_count = coverage.get("covered_count", 0) if isinstance(coverage, dict) else 0
        requested_count = coverage.get("requested_count", 0) if isinstance(coverage, dict) else 0

        source_str = f"{source_bytes}" if source_bytes is not None else "N/A"
        ratio_str = f"{compression_ratio}" if compression_ratio is not None else "N/A"
        reduction_str = f"{abs(reduction_percent)}" if reduction_percent is not None else "N/A"

        return (
            "### Web Font Optimizer Summary\n\n"
            f"- **Source size:** {source_str} bytes\n"
            f"- **Output size:** {total_web_font_bytes} bytes\n"
            f"- **Compression ratio:** {ratio_str} ({reduction_str}%)\n"
            f"- **Readiness score:** {score} ({status})\n"
            f"- **Coverage:** {covered_count}/{requested_count} codepoints"
        )

    @staticmethod
    def generate_readme_example(output_dir: str | Path, package: WebFontOptimizerPackage) -> None:
        """Write example.html and README_EXAMPLE.md to output directory.
        The README_EXAMPLE.md provides a markdown summary of the generated artifacts.
        """
        # Write HTML example (retain for backward compatibility)
        html_path = Path(output_dir) / "example.html"
        html_content = WebFontOptimizer._build_readme_example(package)
        html_path.write_text(html_content, encoding="utf-8")
        # Write README_EXAMPLE.md with markdown summary
        readme_path = Path(output_dir) / "README_EXAMPLE.md"
        # Use the existing generate_summary method for concise markdown
        markdown_summary = WebFontOptimizer.generate_summary(package)
        # Append links to generated files for completeness
        markdown_extra = "\n\n**Generated Files**\n\n" + "\n".join(
            f"- `{name}`" for name in [
                "fonts.css",
                "specimen.html",
                "optimizer-manifest.json",
            ]
        )
        readme_content = markdown_summary + markdown_extra
        readme_path.write_text(readme_content, encoding="utf-8")

    @staticmethod
    def _build_readme_example(package: WebFontOptimizerPackage) -> str:
        """Build HTML string with optimizer summary and specimen embed."""
        size_summary = package.size_summary
        readiness = package.readiness
        coverage = package.bundle.manifest.get("subset", {}).get("coverage", {})
        performance = package.manifest.get("performance", {})

        source_bytes = size_summary.get("source_bytes")
        total_web_font_bytes = size_summary.get("total_web_font_bytes", 0)
        compression_ratio = size_summary.get("compression_ratio")
        reduction_percent = size_summary.get("web_font_delta_vs_source_percent")

        score = readiness.get("score", 0)
        status = readiness.get("status", "unknown")

        elapsed_ms = performance.get("elapsed_ms", 0)

        covered_count = coverage.get("covered_count", 0) if isinstance(coverage, dict) else 0
        requested_count = coverage.get("requested_count", 0) if isinstance(coverage, dict) else 0

        source_str = f"{source_bytes}" if source_bytes is not None else "N/A"
        ratio_str = f"{compression_ratio:.2f}" if compression_ratio is not None else "N/A"
        reduction_str = f"{abs(reduction_percent):.1f}" if reduction_percent is not None else "N/A"
        elapsed_str = f"{elapsed_ms} ms" if elapsed_ms > 0 else "N/A"

        summary_html = (
            f"<h2>Web Font Optimizer Summary</h2>\n"
            f"<table>\n"
            f"  <tr><th>Source size</th><td>{source_str} bytes</td></tr>\n"
            f"  <tr><th>Output size</th><td>{total_web_font_bytes} bytes</td></tr>\n"
            f"  <tr><th>Compression ratio</th><td>{ratio_str} ({reduction_str}%)</td></tr>\n"
            f"  <tr><th>Readiness score</th><td>{score} ({status})</td></tr>\n"
            f"  <tr><th>Coverage</th><td>{covered_count}/{requested_count} codepoints</td></tr>\n"
            f"  <tr><th>Performance</th><td>{elapsed_str}</td></tr>\n"
            f"</table>"
        )

        specimen_embed = (
            f"<h2>Generated Specimen</h2>\n"
            f"<div class=\"specimen-embed\" style=\"border: 1px solid #d9d1c7; border-radius: 0.5rem; padding: 1rem; background: #fff;\">\n"
            f"  <style>{package.css}</style>\n"
            f"  {package.specimen_html}"
            f"</div>"
        )

        full_html = (
            f"<!doctype html>\n"
            f"<html lang=\"en\">\n"
            f"<head>\n"
            f"  <meta charset=\"utf-8\">\n"
            f"  <title>Web Font Optimizer Example</title>\n"
            f"  <style>\n"
            f"    body {{ font-family: system-ui, sans-serif; max-width: 960px; margin: 2rem auto; padding: 0 1rem; color: #111; background: #faf8f2; }}\n"
            f"    h1 {{ border-bottom: 1px solid #d9d1c7; padding-bottom: 0.5rem; }}\n"
            f"    h2 {{ margin-top: 2rem; border-bottom: 1px solid #d9d1c7; padding-bottom: 0.25rem; }}\n"
            f"    table {{ width: 100%; border-collapse: collapse; margin: 1rem 0; background: #fff; border: 1px solid #d9d1c7; border-radius: 0.5rem; overflow: hidden; }}\n"
            f"    th, td {{ padding: 0.75rem 1rem; border-bottom: 1px solid #d9d1c7; text-align: left; }}\n"
            f"    th {{ background: #f5f0e6; font-weight: 600; width: 150px; }}\n"
            f"    tr:last-child th, tr:last-child td {{ border-bottom: none; }}\n"
            f"    code {{ background: #f0eadd; padding: 0.125rem 0.25rem; border-radius: 0.25rem; font-family: monospace; }}\n"
            f"  </style>\n"
            f"</head>\n"
            f"<body>\n"
            f"  <h1>Web Font Optimizer Example</h1>\n"
            f"  <p>This example demonstrates the output of the <code>WebFontOptimizer.build()</code> workflow. Run the optimizer with <code>--readme-example</code> to generate this file automatically.</p>\n"
            f"{summary_html}\n"
            f"{specimen_embed}\n"
            f"</body>\n"
            f"</html>"
        )

        return full_html

    @staticmethod
    def generate_summary_markdown(output_dir: str | Path, package: WebFontOptimizerPackage) -> str:
        """Generate and write markdown summary to output directory."""
        markdown = WebFontOptimizer._build_summary_markdown(package)
        output_path = Path(output_dir) / "summary.md"
        output_path.write_text(markdown, encoding="utf-8")
        return markdown

    @staticmethod
    def _build_summary_markdown(package: WebFontOptimizerPackage) -> str:
        size_summary = package.size_summary
        readiness = package.readiness
        coverage = package.bundle.manifest.get("subset", {}).get("coverage", {})

        source_bytes = size_summary.get("source_bytes")
        total_web_font_bytes = size_summary.get("total_web_font_bytes", 0)
        compression_ratio = size_summary.get("compression_ratio")
        reduction_percent = size_summary.get("web_font_delta_vs_source_percent")

        score = readiness.get("score", 0)
        status = readiness.get("status", "unknown")

        covered_count = coverage.get("covered_count", 0) if isinstance(coverage, dict) else 0
        requested_count = coverage.get("requested_count", 0) if isinstance(coverage, dict) else 0

        source_str = f"{source_bytes}" if source_bytes is not None else "N/A"
        ratio_str = f"{compression_ratio}" if compression_ratio is not None else "N/A"
        reduction_str = f"{abs(reduction_percent)}" if reduction_percent is not None else "N/A"

        return (
            "### Web Font Optimizer Summary\n\n"
            f"- **Source size:** {source_str} bytes\n"
            f"- **Output size:** {total_web_font_bytes} bytes\n"
            f"- **Compression ratio:** {ratio_str} ({reduction_str}%)\n"
            f"- **Readiness score:** {score} ({status})\n"
            f"- **Coverage:** {covered_count}/{requested_count} codepoints"
        )

    @staticmethod
    def build_decision_html(report: DecisionReport) -> str:
        """Build an HTML page from a DecisionReport.

        Args:
            report: DecisionReport instance with mode, reasons, summary, remediation

        Returns:
            HTML string with title, table of fields, and brief description
        """
        mode = html.escape(str(report.mode if report.mode else "unknown"))
        reason = html.escape(str(report.reason if report.reason else "No reason provided."))
        summary = html.escape(str(report.summary if report.summary else "No summary available."))
        remediation_list = report.remediation if report.remediation else []
        remediation = html.escape(str(remediation_list[0] if remediation_list else "No recommendations."))

        html_content = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Decision Report</title>
  <style>
    body {
      font-family: system-ui, -apple-system, sans-serif;
      max-width: 720px;
      margin: 2rem auto;
      padding: 0 1rem;
      background: #faf8f2;
      color: #111;
    }
    h1 {
      font-size: 1.5rem;
      margin-bottom: 1.5rem;
      border-bottom: 1px solid #d9d1c7;
      padding-bottom: 0.5rem;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      background: #fff;
      border: 1px solid #d9d1c7;
      border-radius: 0.5rem;
      overflow: hidden;
    }
    th, td {
      padding: 0.75rem 1rem;
      text-align: left;
      border-bottom: 1px solid #d9d1c7;
    }
    th {
      background: #f5f0e6;
      font-weight: 600;
      width: 120px;
      vertical-align: top;
    }
    td {
      color: #2d261b;
    }
    tr:last-child th,
    tr:last-child td {
      border-bottom: none;
    }
    .label {
      font-weight: 600;
      color: #443b2f;
    }
  </style>
</head>
<body>
  <h1>Decision Report</h1>
  <table>
    <tr>
      <th class="label">Export Mode</th>
      <td id="mode">""" + mode + """</td>
    </tr>
    <tr>
      <th class="label">Primary Reason</th>
      <td id="reason">""" + reason + """</td>
    </tr>
    <tr>
      <th class="label">Summary</th>
      <td id="summary">""" + summary + """</td>
    </tr>
    <tr>
      <th class="label">Recommendation</th>
      <td id="remediation">""" + remediation + """</td>
    </tr>
  </table>
</body>
</html>"""
        return html_content


class WebFontBuilder:
    @classmethod
    def build_family_waterfall_preview(
        cls,
        bundles: list[WebFontBundle],
        *,
        preview_text: str = _DEFAULT_PREVIEW_TEXT,
        file_stem: str = "family-waterfall",
    ) -> PreviewImage:
        if not bundles:
            raise ValueError("Family waterfall preview requires at least one web font bundle")
        rendered = cls._render_waterfall_preview(bundles, preview_text=preview_text)
        if rendered is None:
            raise ValueError("Family waterfall preview requires at least one previewable bundle")
        return PreviewImage(
            filename=f"{file_stem}.png",
            media_type="image/png",
            data=rendered,
        )

    @classmethod
    def build_family_matrix_preview(
        cls,
        bundles: list[WebFontBundle],
        *,
        preview_text: str = _DEFAULT_PREVIEW_TEXT,
        file_stem: str = "family-matrix",
    ) -> PreviewImage:
        if not bundles:
            raise ValueError("Family matrix preview requires at least one web font bundle")
        rendered = cls._render_matrix_preview(bundles, preview_text=preview_text)
        if rendered is None:
            raise ValueError("Family matrix preview requires at least one previewable bundle")
        return PreviewImage(
            filename=f"{file_stem}.png",
            media_type="image/png",
            data=rendered,
        )

    @classmethod
    def _compose_family_review_board(
        cls,
        bundles: list[WebFontBundle],
        waterfall: PreviewImage,
        matrix: PreviewImage,
        *,
        family_name: str | None = None,
        preview_text: str = _DEFAULT_PREVIEW_TEXT,
        file_stem: str = "family-review-board",
    ) -> PreviewImage:
        board_family = family_name or bundles[0].family
        return FontPreviewBuilder.compose_sheet(
            [waterfall, matrix],
            columns=1,
            gap=18,
            title=f"{board_family} Review Board",
            column_headers=["Comparative Family Previews"],
            labels=["Waterfall", "Matrix"],
            footer_lines=[
                f"Preview text: {preview_text}",
                f"Included styles: {', '.join(bundle.style for bundle in bundles)}",
            ],
            file_stem=file_stem,
        )

    @classmethod
    def build_family_review_board(
        cls,
        bundles: list[WebFontBundle],
        *,
        family_name: str | None = None,
        preview_text: str = _DEFAULT_PREVIEW_TEXT,
        file_stem: str = "family-review-board",
    ) -> PreviewImage:
        if not bundles:
            raise ValueError("Family review board requires at least one web font bundle")
        waterfall = cls.build_family_waterfall_preview(
            bundles,
            preview_text=preview_text,
            file_stem="family-waterfall",
        )
        matrix = cls.build_family_matrix_preview(
            bundles,
            preview_text=preview_text,
            file_stem="family-matrix",
        )
        return cls._compose_family_review_board(
            bundles,
            waterfall,
            matrix,
            family_name=family_name,
            preview_text=preview_text,
            file_stem=file_stem,
        )

    @classmethod
    def build_family_review_export_package(
        cls,
        bundles: list[WebFontBundle],
        *,
        family_name: str | None = None,
        preview_text: str = _DEFAULT_PREVIEW_TEXT,
        file_stem: str = "family-review-board",
    ) -> FamilyReviewExportPackage:
        if not bundles:
            raise ValueError("Family review export package requires at least one web font bundle")

        waterfall = cls.build_family_waterfall_preview(
            bundles,
            preview_text=preview_text,
            file_stem="family-waterfall",
        )
        matrix = cls.build_family_matrix_preview(
            bundles,
            preview_text=preview_text,
            file_stem="family-matrix",
        )
        board = cls._compose_family_review_board(
            bundles,
            waterfall,
            matrix,
            family_name=family_name,
            preview_text=preview_text,
            file_stem=file_stem,
        )
        package_family = family_name or bundles[0].family
        context = cls._family_review_export_context(
            bundles,
            family_name=package_family,
            preview_text=preview_text,
            board_filename=board.filename,
        )
        stem = Path(board.filename).stem
        return FamilyReviewExportPackage(
            family_name=package_family,
            board=board,
            assets=[
                WebFontAsset(
                    filename=waterfall.filename,
                    media_type=waterfall.media_type,
                    data=waterfall.data,
                ),
                WebFontAsset(
                    filename=matrix.filename,
                    media_type=matrix.media_type,
                    data=matrix.data,
                ),
            ],
            markdown_filename=f"{stem}.md",
            html_filename=f"{stem}.html",
            manifest_filename=f"{stem}-manifest.json",
            markdown=cls._build_family_review_export_markdown(context),
            html=cls._build_family_review_export_html(context),
            manifest=cls._build_family_review_export_manifest(
                bundles,
                context=context,
                asset_filenames=[waterfall.filename, matrix.filename],
            ),
        )

    @classmethod
    def build_family_package(
        cls,
        bundles: list[WebFontBundle],
        *,
        family_name: str | None = None,
        css_filename: str = "family.css",
        html_filename: str = "family.html",
        preview_text: str = _DEFAULT_PREVIEW_TEXT,
        specimen_template: str = "classic",
    ) -> WebFontFamilyPackage:
        if not bundles:
            raise ValueError("Family package requires at least one web font bundle")
        template_name = _normalize_specimen_template(specimen_template)
        package_family = family_name or bundles[0].family
        css = cls._build_family_css(bundles, specimen_template=template_name)
        image_assets = cls._build_family_image_assets(bundles, preview_text=preview_text)
        html_text = cls._build_family_html(
            bundles,
            family_name=package_family,
            css_filename=css_filename,
            preview_text=preview_text,
            image_assets=image_assets,
            specimen_template=template_name,
        )
        return WebFontFamilyPackage(
            family_name=package_family,
            bundles=bundles,
            css=css,
            html=html_text,
            css_filename=css_filename,
            html_filename=html_filename,
            manifest=cls._build_family_manifest(
                bundles,
                family_name=package_family,
                css_filename=css_filename,
                html_filename=html_filename,
                specimen_template=template_name,
                asset_filenames=[asset.filename for asset in image_assets],
            ),
            assets=image_assets,
        )

    @classmethod
    def build(
        cls,
        font: Font,
        *,
        file_stem: str | None = None,
        include_woff: bool = True,
        font_display: str = "swap",
        preview_text: str = _DEFAULT_PREVIEW_TEXT,
        instance_coordinates: dict[str, float] | None = None,
        instance_name: str | None = None,
        presets: str | Iterable[str] = (),
        text: str = "",
        codepoints: Iterable[int] = (),
        ranges: Iterable[tuple[int, int] | range] = (),
        specimen_template: str = "classic",
        variable_mode: str = "auto",
        naming_strategy: str = "instance-family",
        family_suffix: str | None = None,
        legacy_family_name: str | None = None,
        typographic_family_name: str | None = None,
        legacy_style_name: str | None = None,
        typographic_style_name: str | None = None,
        stat_policy: str = "drop",
        preserve_variable: bool = False,
    ) -> WebFontBundle:
        template_name = _normalize_specimen_template(specimen_template)
        variable_mode_name = _normalize_variable_export_mode(variable_mode)
        naming_strategy_name = _normalize_naming_strategy(naming_strategy)
        stat_policy_name = normalize_static_stat_policy(stat_policy)
        codepoint_values = tuple(codepoints)
        range_values = tuple(ranges)
        prepared = cls._prepare_font(
            font,
            instance_coordinates=instance_coordinates,
            instance_name=instance_name,
            presets=presets,
            text=text,
            codepoints=codepoint_values,
            ranges=range_values,
            variable_mode=variable_mode_name,
            naming_strategy=naming_strategy_name,
            family_suffix=family_suffix,
            legacy_family_name=legacy_family_name,
            typographic_family_name=typographic_family_name,
            legacy_style_name=legacy_style_name,
            typographic_style_name=typographic_style_name,
            stat_policy=stat_policy_name,
            preserve_variable=preserve_variable,
        )

        family = (prepared.font.font_family or prepared.font.font_name or "Web Font").strip() or "Web Font"
        style = (prepared.font.font_style or "Regular").strip() or "Regular"
        stem = file_stem or _slugify_filename(f"{family}-{style}")
        css_filename = f"{stem}.css"
        html_filename = f"{stem}.html"

        font_assets = [cls._make_font_asset(prepared.font, stem, FontType.WOFF2)]
        if include_woff:
            font_assets.append(cls._make_font_asset(prepared.font, stem, FontType.WOFF))

        css = cls._build_css(
            prepared.font,
            family=family,
            font_assets=font_assets,
            font_display=font_display,
            specimen_template=template_name,
        )
        html_text = cls._build_html(
            prepared.font,
            family=family,
            style=style,
            css_filename=css_filename,
            preview_text=preview_text,
            specimen_template=template_name,
            export_mode=prepared.export_mode,
            export_note=prepared.export_note,
        )
        return WebFontBundle(
            family=family,
            style=style,
            css=css,
            html=html_text,
            css_filename=css_filename,
            html_filename=html_filename,
            manifest=cls._build_bundle_manifest(
                original_font=font,
                prepared_font=prepared.font,
                family=family,
                style=style,
                css_filename=css_filename,
                html_filename=html_filename,
                font_assets=font_assets,
                preview_text=preview_text,
                specimen_template=template_name,
                instance_name=instance_name,
                instance_coordinates=instance_coordinates,
                export_mode=prepared.export_mode,
                export_note=prepared.export_note,
                auto_instanced_default=prepared.auto_instanced_default,
                coverage=prepared.coverage,
                export_reason=prepared.export_reason,
                requested_variable_mode=variable_mode_name,
                requested_naming_strategy=naming_strategy_name,
                requested_family_suffix=family_suffix,
                requested_legacy_family_name=legacy_family_name,
                requested_typographic_family_name=typographic_family_name,
                requested_legacy_style_name=legacy_style_name,
                requested_typographic_style_name=typographic_style_name,
                requested_stat_policy=stat_policy_name,
                supported_stat_policies=prepared.supported_stat_policies,
                stat_policy_recommendation=prepared.stat_policy_recommendation,
                stat_policy_recommendation_reasons=prepared.stat_policy_recommendation_reasons,
                stat_policy_next_action=prepared.stat_policy_next_action,
                stat_policy_override_suggestion=prepared.stat_policy_override_suggestion,
                stat_policy_override_suggestion_reasons=(
                    prepared.stat_policy_override_suggestion_reasons
                ),
                presets=presets,
                text=text,
                codepoints=codepoint_values,
                ranges=range_values,
            ),
            font_assets=font_assets,
            preview_font=prepared.font,
        )

    @classmethod
    def _prepare_font(
        cls,
        font: Font,
        *,
        instance_coordinates: dict[str, float] | None,
        instance_name: str | None,
        presets: str | Iterable[str],
        text: str,
        codepoints: Iterable[int],
        ranges: Iterable[tuple[int, int] | range],
        variable_mode: str,
        naming_strategy: str,
        family_suffix: str | None,
        legacy_family_name: str | None,
        typographic_family_name: str | None,
        legacy_style_name: str | None,
        typographic_style_name: str | None,
        stat_policy: str,
        preserve_variable: bool = False,
    ) -> _PreparedWebFont:
        prepared_font: Font = font
        export_mode = "static"
        export_note: str | None = None
        export_reason: str | None = "source font is static and no variable instance selection was requested"
        auto_instanced_default = False
        coverage: SubsetCoverage | None = None
        supported_stat_policies: tuple[str, ...] = ()
        stat_policy_recommendation: str | None = None
        stat_policy_recommendation_reasons: tuple[str, ...] = ()
        stat_policy_next_action: str | None = None
        stat_policy_override_suggestion: str | None = None
        stat_policy_override_suggestion_reasons: tuple[str, ...] = ()
        source_is_variable = cls._is_variable_ttf(font)
        should_force_static = variable_mode == "static"
        should_force_live = variable_mode == "live"

        if should_force_live and not source_is_variable:
            raise FontNotSupportedException("live variable web export requires a variable TTF font")
        if should_force_live and (instance_coordinates is not None or instance_name is not None):
            raise FontNotSupportedException(
                "live variable web export does not support explicit instance selection"
            )

        if should_force_static and source_is_variable:
            prepared_instance = cls._instantiate_for_web(
                font,
                coordinates=instance_coordinates,
                instance_name=instance_name,
                naming_strategy=naming_strategy,
                family_suffix=family_suffix,
                legacy_family_name=legacy_family_name,
                typographic_family_name=typographic_family_name,
                legacy_style_name=legacy_style_name,
                typographic_style_name=typographic_style_name,
                stat_policy=stat_policy,
            )
            prepared_font = prepared_instance.font
            supported_stat_policies = prepared_instance.supported_stat_policies
            stat_policy_recommendation = prepared_instance.stat_policy_recommendation
            stat_policy_recommendation_reasons = prepared_instance.stat_policy_recommendation_reasons
            stat_policy_next_action = prepared_instance.stat_policy_next_action
            stat_policy_override_suggestion = prepared_instance.stat_policy_override_suggestion
            stat_policy_override_suggestion_reasons = (
                prepared_instance.stat_policy_override_suggestion_reasons
            )
            export_mode = "static-instance"
            export_note = (
                "This web bundle was exported in explicit static mode from a variable-font source, "
                "so the exported font files do not include live axis controls."
            )
            export_reason = "explicit static mode or instance selection requested"
        elif instance_coordinates is not None or instance_name is not None:
            prepared_instance = cls._instantiate_for_web(
                font,
                coordinates=instance_coordinates,
                instance_name=instance_name,
                naming_strategy=naming_strategy,
                family_suffix=family_suffix,
                legacy_family_name=legacy_family_name,
                typographic_family_name=typographic_family_name,
                legacy_style_name=legacy_style_name,
                typographic_style_name=typographic_style_name,
                stat_policy=stat_policy,
            )
            prepared_font = prepared_instance.font
            supported_stat_policies = prepared_instance.supported_stat_policies
            stat_policy_recommendation = prepared_instance.stat_policy_recommendation
            stat_policy_recommendation_reasons = prepared_instance.stat_policy_recommendation_reasons
            stat_policy_next_action = prepared_instance.stat_policy_next_action
            stat_policy_override_suggestion = prepared_instance.stat_policy_override_suggestion
            stat_policy_override_suggestion_reasons = (
                prepared_instance.stat_policy_override_suggestion_reasons
            )
            export_mode = "static-instance"
            export_note = (
                "This web bundle was instantiated from a variable-font source, so the exported "
                "font files are static and do not include live axis controls."
            )
            export_reason = "explicit static mode or instance selection requested"
        elif source_is_variable:
            export_mode = "variable-live"
            export_note = (
                "This web bundle preserves the variable font so the specimen page can expose live "
                "axis controls."
            )
            export_reason = "source font is variable and no static instance or subset was requested"

        codepoint_values = tuple(codepoints)
        range_values = tuple(ranges)
        should_subset = bool(text or codepoint_values or range_values or presets)
        subset_time_ms: int = 0
        if should_subset:
            if should_force_live:
                raise FontNotSupportedException(
                    "live variable web export does not support subsetting; choose static mode or auto"
                )
            preserve_variable_during_subset = preserve_variable and cls._is_variable_ttf(prepared_font)
            if preserve_variable_during_subset:
                export_mode = "variable-live"
                export_note = (
                    "Subset requests on variable fonts with preserve_variable=True preserve the variable font."
                )
                export_reason = (
                    "variable-font subsetting with preserve_variable=True keeps variable font"
                )
            elif cls._is_variable_ttf(prepared_font):
                prepared_instance = cls._instantiate_for_web(
                    font,
                    coordinates=None,
                    instance_name=None,
                    naming_strategy=naming_strategy,
                    family_suffix=family_suffix,
                    legacy_family_name=legacy_family_name,
                    typographic_family_name=typographic_family_name,
                    legacy_style_name=legacy_style_name,
                    typographic_style_name=typographic_style_name,
                    stat_policy=stat_policy,
                )
                prepared_font = prepared_instance.font
                supported_stat_policies = prepared_instance.supported_stat_policies
                stat_policy_recommendation = prepared_instance.stat_policy_recommendation
                stat_policy_recommendation_reasons = prepared_instance.stat_policy_recommendation_reasons
                stat_policy_next_action = prepared_instance.stat_policy_next_action
                stat_policy_override_suggestion = prepared_instance.stat_policy_override_suggestion
                stat_policy_override_suggestion_reasons = (
                    prepared_instance.stat_policy_override_suggestion_reasons
                )
                auto_instanced_default = True
                export_mode = "static-subset-from-variable-default"
                export_note = (
                    "Subset requests on variable fonts currently export a static bundle. This "
                    "bundle was auto-instantiated at the default coordinates before subsetting."
                )
                export_reason = (
                    "variable-font subsetting requires static output, so the default instance "
                    "was generated before subsetting"
                )
            subset_start = time.perf_counter()
            prepared = FontSubsetter.subset_for_web_with_coverage(
                prepared_font,
                presets=presets,
                text=text,
                codepoints=codepoint_values,
                ranges=range_values,
                preserve_variation_tables=preserve_variable_during_subset,
            )
            subset_time_ms = round((time.perf_counter() - subset_start) * 1000)
            prepared_font = prepared.font
            coverage = prepared.coverage
            if export_mode == "static-instance":
                if should_force_static:
                    export_mode = "static-subset-from-instance"
                    export_note = (
                        "This web bundle was exported in explicit static mode from a variable-font "
                        "source and then subsetted, so the exported font files are static."
                    )
                    export_reason = "subsetting requested after static instance selection"
                else:
                    export_mode = "static-subset-from-instance"
                    export_note = (
                        "This web bundle was instantiated from a variable-font source and then subsetted, "
                        "so the exported font files are static."
                    )
                    export_reason = "subsetting requested after static instance selection"
            elif export_mode == "static":
                export_mode = "static-subset"
                export_reason = "subsetting requested for a static source font"
            elif export_mode == "variable-live":
                if preserve_variable:
                    export_mode = "variable-live"
                    export_reason = "variable-font subsetting with preserve_variable=True"
                else:
                    export_mode = "static-subset-from-variable-default"
                    export_reason = (
                        "variable-font subsetting requires static output, so the default instance "
                        "was generated before subsetting"
                    )
        return _PreparedWebFont(
            font=prepared_font,
            export_mode=export_mode,
            export_note=export_note,
            auto_instanced_default=auto_instanced_default,
            coverage=coverage,
            export_reason=export_reason,
            supported_stat_policies=supported_stat_policies,
            stat_policy_recommendation=stat_policy_recommendation,
            stat_policy_recommendation_reasons=stat_policy_recommendation_reasons,
            stat_policy_next_action=stat_policy_next_action,
            stat_policy_override_suggestion=stat_policy_override_suggestion,
            stat_policy_override_suggestion_reasons=stat_policy_override_suggestion_reasons,
            subset_time_ms=subset_time_ms,
        )

    @staticmethod
    def _instantiate_for_web(
        font: Font,
        coordinates: dict[str, float] | None,
        instance_name: str | None,
        naming_strategy: str,
        family_suffix: str | None,
        legacy_family_name: str | None,
        typographic_family_name: str | None,
        legacy_style_name: str | None,
        typographic_style_name: str | None,
        stat_policy: str,
    ) -> _PreparedStaticInstance:
        if not isinstance(font, TtfFont) or not font.is_variable:
            raise FontNotSupportedException(
                "instance selection is only supported for variable TTF fonts"
            )
        preview = font.smart_instancer.preview_naming_policy(
            coordinates,
            instance_name=instance_name,
            naming_strategy=naming_strategy,
            family_suffix=family_suffix,
            legacy_family_name=legacy_family_name,
            typographic_family_name=typographic_family_name,
            legacy_style_name=legacy_style_name,
            typographic_style_name=typographic_style_name,
            stat_policy=stat_policy,
        )
        stat_recommendation = None
        stat_reasons: tuple[str, ...] = ()
        stat_next_action = None
        supported_stat_policies: tuple[str, ...] = ()
        stat_override_suggestion = None
        stat_override_reasons: tuple[str, ...] = ()
        if preview.stat_diagnostics is not None:
            supported_stat_policies = preview.stat_diagnostics.supported_stat_policies
            stat_recommendation = preview.stat_diagnostics.stat_policy_recommendation
            stat_reasons = preview.stat_diagnostics.stat_policy_recommendation_reasons
            stat_next_action = preview.stat_diagnostics.stat_policy_next_action
            stat_override_suggestion = preview.stat_diagnostics.stat_policy_override_suggestion
            stat_override_reasons = (
                preview.stat_diagnostics.stat_policy_override_suggestion_reasons
            )
        instantiated = font.smart_instancer.instantiate(
            coordinates,
            instance_name=instance_name,
            naming_strategy=naming_strategy,
            family_suffix=family_suffix,
            legacy_family_name=legacy_family_name,
            typographic_family_name=typographic_family_name,
            legacy_style_name=legacy_style_name,
            typographic_style_name=typographic_style_name,
            stat_policy=stat_policy,
        )
        return _PreparedStaticInstance(
            font=instantiated,
            supported_stat_policies=supported_stat_policies,
            stat_policy_recommendation=stat_recommendation,
            stat_policy_recommendation_reasons=stat_reasons,
            stat_policy_next_action=stat_next_action,
            stat_policy_override_suggestion=stat_override_suggestion,
            stat_policy_override_suggestion_reasons=stat_override_reasons,
        )

    @staticmethod
    def _make_font_asset(font: Font, stem: str, font_type: FontType) -> WebFontAsset:
        converted = FontConverter.convert(font, font_type)
        extension = font_type.value.lower()
        media_type = f"font/{extension}"
        return WebFontAsset(
            filename=f"{stem}.{extension}",
            media_type=media_type,
            data=converted.to_bytes(),
        )

    @classmethod
    def _build_css(
        cls,
        font: Font,
        *,
        family: str,
        font_assets: list[WebFontAsset],
        font_display: str,
        specimen_template: str,
    ) -> str:
        descriptors = cls._font_face_descriptors(font)
        src_items = [
            f"url('./{asset.filename}') format('{_css_format(asset.filename)}')"
            for asset in font_assets
        ]
        descriptor_lines = "\n".join(f"  {name}: {value};" for name, value in descriptors)
        return (
            "@font-face {\n"
            f"  font-family: '{_escape_css_string(family)}';\n"
            f"  src: {', '.join(src_items)};\n"
            f"{descriptor_lines}\n"
            f"  font-display: {font_display};\n"
            "}\n\n"
            "body {\n"
            "  font-family: system-ui, sans-serif;\n"
            "  margin: 2rem;\n"
            "  color: #111;\n"
            "  background: #faf8f2;\n"
            "}\n\n"
            ".specimen {\n"
            f"  font-family: '{_escape_css_string(family)}', sans-serif;\n"
            "  font-size: 64px;\n"
            "  line-height: 1.2;\n"
            "  margin: 1rem 0 2rem;\n"
            "}\n\n"
            ".axis-controls {\n"
            "  display: grid;\n"
            "  gap: 1rem;\n"
            "  margin: 1.5rem 0 2rem;\n"
            "  max-width: 48rem;\n"
            "}\n\n"
            ".axis-control {\n"
            "  padding: 1rem;\n"
            "  border: 1px solid #d9d1c7;\n"
            "  border-radius: 0.75rem;\n"
            "  background: #fffdf8;\n"
            "}\n\n"
            ".axis-control label {\n"
            "  display: flex;\n"
            "  justify-content: space-between;\n"
            "  gap: 1rem;\n"
            "  font-weight: 600;\n"
            "}\n\n"
            ".axis-control input {\n"
            "  width: 100%;\n"
            "  margin-top: 0.75rem;\n"
            "}\n\n"
            ".axis-range {\n"
            "  margin-top: 0.5rem;\n"
            "  color: #6f6354;\n"
            "  font-size: 0.95rem;\n"
            "}\n"
            f"{_specimen_template_css(specimen_template)}"
        )

    @classmethod
    def _build_html(
        cls,
        font: Font,
        *,
        family: str,
        style: str,
        css_filename: str,
        preview_text: str,
        specimen_template: str,
        export_mode: str,
        export_note: str | None,
    ) -> str:
        axis_markup = cls._variable_axis_markup(font)
        template_label = html.escape(_format_template_label(specimen_template))
        export_label = html.escape(_format_export_mode_label(export_mode))
        export_note_markup = (
            f"  <p><strong>Export Note:</strong> {html.escape(export_note)}</p>\n"
            if export_note
            else ""
        )
        return (
            "<!doctype html>\n"
            "<html lang=\"en\">\n"
            "<head>\n"
            "  <meta charset=\"utf-8\">\n"
            "  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
            f"  <title>{html.escape(family)} specimen</title>\n"
            f"  <link rel=\"stylesheet\" href=\"{html.escape(css_filename)}\">\n"
            "</head>\n"
            f"  <body class=\"specimen-template-{html.escape(specimen_template)}\">\n"
            f"  <h1>{html.escape(family)}</h1>\n"
            f"  <p><strong>Style:</strong> {html.escape(style)}</p>\n"
            f"  <p><strong>Export Mode:</strong> {export_label}</p>\n"
            f"  <p><strong>Template:</strong> {template_label}</p>\n"
            f"{export_note_markup}"
            f"  <div class=\"specimen\">{html.escape(preview_text)}</div>\n"
            f"{axis_markup}"
            "</body>\n"
            "</html>\n"
        )

    @classmethod
    def _build_family_css(cls, bundles: list[WebFontBundle], *, specimen_template: str) -> str:
        face_blocks: list[str] = []
        for bundle in bundles:
            for asset in bundle.font_assets:
                if asset.filename.endswith(".woff2") or asset.filename.endswith(".woff"):
                    pass
            face_blocks.append(bundle.css.split("\n\nbody {\n", 1)[0])
        return (
            "\n\n".join(face_blocks)
            + "\n\nbody {\n"
            "  margin: 2rem;\n"
            "  color: #111;\n"
            "  background: #faf8f2;\n"
            "}\n\n"
            ".family-nav {\n"
            "  display: flex;\n"
            "  flex-wrap: wrap;\n"
            "  gap: 0.75rem;\n"
            "  margin: 1rem 0 1.5rem;\n"
            "}\n\n"
            ".family-nav a,\n"
            ".family-filter button {\n"
            "  display: inline-flex;\n"
            "  align-items: center;\n"
            "  padding: 0.45rem 0.85rem;\n"
            "  border: 1px solid #d9d1c7;\n"
            "  border-radius: 999px;\n"
            "  background: #fffdf8;\n"
            "  color: #4a4034;\n"
            "  text-decoration: none;\n"
            "  font: inherit;\n"
            "  cursor: pointer;\n"
            "}\n\n"
            ".family-filter {\n"
            "  display: flex;\n"
            "  flex-wrap: wrap;\n"
            "  gap: 0.75rem;\n"
            "  margin: 0 0 2rem;\n"
            "}\n\n"
            ".family-filter button.is-active {\n"
            "  background: #4a4034;\n"
            "  border-color: #4a4034;\n"
            "  color: #faf8f2;\n"
            "}\n\n"
            ".family-specimen {\n"
            "  margin-bottom: 2rem;\n"
            "}\n\n"
            ".family-specimen.is-hidden {\n"
            "  display: none;\n"
            "}\n\n"
            ".family-specimen .sample {\n"
            "  font-size: 56px;\n"
            "  line-height: 1.2;\n"
            "}\n\n"
            ".coordinate-meta,\n"
            ".matrix-style {\n"
            "  color: #6f6354;\n"
            "  font-size: 0.95rem;\n"
            "}\n\n"
            ".family-image-panel {\n"
            "  margin: 1rem 0 1.5rem;\n"
            "}\n\n"
            ".family-image {\n"
            "  display: block;\n"
            "  width: 100%;\n"
            "  max-width: 1100px;\n"
            "  height: auto;\n"
            "  border: 1px solid #d9d1c7;\n"
            "  border-radius: 0.75rem;\n"
            "  background: #fffdf8;\n"
            "}\n\n"
            ".waterfall-row {\n"
            "  margin-bottom: 1rem;\n"
            "}\n\n"
            ".waterfall-label {\n"
            "  display: inline-block;\n"
            "  width: 4rem;\n"
            "  color: #7a6f61;\n"
            "}\n\n"
            ".matrix-grid {\n"
            "  display: grid;\n"
            "  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));\n"
            "  gap: 1rem;\n"
            "}\n\n"
            ".matrix-cell {\n"
            "  padding: 1rem;\n"
            "  border: 1px solid #d9d1c7;\n"
            "  background: #fffdf8;\n"
            "  border-radius: 0.75rem;\n"
            "}\n\n"
            ".matrix-cell .sample {\n"
            "  font-size: 40px;\n"
            "  line-height: 1.2;\n"
            "}\n"
            f"{_specimen_template_css(specimen_template)}"
        )

    @classmethod
    def _build_family_html(
        cls,
        bundles: list[WebFontBundle],
        *,
        family_name: str,
        css_filename: str,
        preview_text: str,
        image_assets: list[WebFontAsset],
        specimen_template: str,
    ) -> str:
        waterfall_sizes = [72, 48, 32, 20]
        image_filenames = {asset.filename for asset in image_assets}
        template_label = html.escape(_format_template_label(specimen_template))
        sections = []
        nav_links = [
            '  <a href="#waterfall">Waterfall</a>\n',
            '  <a href="#matrix">Matrix</a>\n',
        ]
        filter_buttons = [
            '  <button type="button" class="is-active" data-filter="all">All Styles</button>\n'
        ]
        for bundle in bundles:
            style_slug = _slugify_filename(bundle.style)
            export_mode = html.escape(_format_export_mode_label(str(bundle.manifest.get("export_mode", "static"))))
            export_note = bundle.manifest.get("export_note")
            coordinate_label = _bundle_coordinate_label(bundle)
            export_note_markup = (
                f"    <p><strong>Export Note:</strong> {html.escape(str(export_note))}</p>\n"
                if export_note
                else ""
            )
            coordinate_markup = (
                f"    <p class=\"coordinate-meta\"><strong>Coordinates:</strong> "
                f"{html.escape(coordinate_label)}</p>\n"
                if coordinate_label
                else ""
            )
            nav_links.append(
                f'  <a href="#style-{html.escape(style_slug)}">{html.escape(bundle.style)}</a>\n'
            )
            filter_buttons.append(
                "  <button "
                f'type="button" data-filter="{html.escape(style_slug)}">{html.escape(bundle.style)}</button>\n'
            )
            sections.append(
                f'  <section id="style-{html.escape(style_slug)}" class="family-specimen" '
                f'data-style="{html.escape(style_slug)}">\n'
                f"    <h2>{html.escape(bundle.style)}</h2>\n"
                f"    <p><strong>Export Mode:</strong> {export_mode}</p>\n"
                f"{export_note_markup}"
                f"{coordinate_markup}"
                f"    <div class=\"sample\" style=\"font-family: '{html.escape(bundle.family)}', sans-serif;\">"
                f"{html.escape(preview_text)}</div>\n"
                "  </section>\n"
            )
        waterfall_rows = []
        for size in waterfall_sizes:
            row_samples = []
            for bundle in bundles:
                row_samples.append(
                    f"<span style=\"font-family: '{html.escape(bundle.family)}', sans-serif; "
                    f"font-size: {size}px; margin-right: 1rem;\">{html.escape(bundle.style)}: {html.escape(preview_text)}</span>"
                )
            waterfall_rows.append(
                "  <div class=\"waterfall-row\">"
                f"<span class=\"waterfall-label\">{size}px</span>{''.join(row_samples)}</div>\n"
            )
        matrix_cells = []
        for bundle in bundles:
            coordinate_label = _bundle_coordinate_label(bundle)
            review_label = _bundle_review_label(bundle)
            coordinate_markup = (
                f"      <p class=\"coordinate-meta\">{html.escape(coordinate_label)}</p>\n"
                if coordinate_label
                else ""
            )
            matrix_cells.append(
                "    <div class=\"matrix-cell\">\n"
                f"      <h3>{html.escape(review_label)}</h3>\n"
                f"      <p class=\"matrix-style\">Style: {html.escape(bundle.style)}</p>\n"
                f"{coordinate_markup}"
                f"      <div class=\"sample\" style=\"font-family: '{html.escape(bundle.family)}', sans-serif;\">"
                f"{html.escape(preview_text)}</div>\n"
                "    </div>\n"
            )
        waterfall_image_markup = ""
        if "family-waterfall.png" in image_filenames:
            waterfall_image_markup = (
                "    <div class=\"family-image-panel\">\n"
                f"      <img class=\"family-image\" src=\"{html.escape('family-waterfall.png')}\" "
                f"alt=\"{html.escape(family_name)} waterfall preview\">\n"
                "    </div>\n"
            )
        matrix_image_markup = ""
        if "family-matrix.png" in image_filenames:
            matrix_image_markup = (
                "    <div class=\"family-image-panel\">\n"
                f"      <img class=\"family-image\" src=\"{html.escape('family-matrix.png')}\" "
                f"alt=\"{html.escape(family_name)} matrix preview\">\n"
                "    </div>\n"
            )
        return (
            "<!doctype html>\n"
            "<html lang=\"en\">\n"
            "<head>\n"
            "  <meta charset=\"utf-8\">\n"
            "  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
            f"  <title>{html.escape(family_name)} family package</title>\n"
            f"  <link rel=\"stylesheet\" href=\"{html.escape(css_filename)}\">\n"
            "</head>\n"
            f"<body class=\"specimen-template-{html.escape(specimen_template)}\">\n"
            f"  <h1>{html.escape(family_name)}</h1>\n"
            f"  <p><strong>Template:</strong> {template_label}</p>\n"
            "  <nav class=\"family-nav\" aria-label=\"Family specimen sections\">\n"
            f"{''.join(nav_links)}"
            "  </nav>\n"
            "  <div class=\"family-filter\" aria-label=\"Style filters\">\n"
            f"{''.join(filter_buttons)}"
            "  </div>\n"
            "  <section id=\"waterfall\">\n"
            "    <h2>Waterfall</h2>\n"
            f"{waterfall_image_markup}"
            f"{''.join(waterfall_rows)}"
            "  </section>\n"
            "  <section id=\"matrix\">\n"
            "    <h2>Matrix</h2>\n"
            f"{matrix_image_markup}"
            "    <div class=\"matrix-grid\">\n"
            f"{''.join(matrix_cells)}"
            "    </div>\n"
            "  </section>\n"
            f"{''.join(sections)}"
            "  <script>\n"
            "    const filterButtons = document.querySelectorAll('.family-filter button');\n"
            "    const specimenSections = document.querySelectorAll('.family-specimen');\n"
            "    for (const button of filterButtons) {\n"
            "      button.addEventListener('click', () => {\n"
            "        const selectedFilter = button.dataset.filter || 'all';\n"
            "        for (const candidate of filterButtons) {\n"
            "          candidate.classList.toggle('is-active', candidate === button);\n"
            "        }\n"
            "        for (const section of specimenSections) {\n"
            "          const matches = selectedFilter === 'all' || section.dataset.style === selectedFilter;\n"
            "          section.classList.toggle('is-hidden', !matches);\n"
            "        }\n"
            "      });\n"
            "    }\n"
            "  </script>\n"
            "</body>\n"
            "</html>\n"
        )

    @staticmethod
    def _is_variable_ttf(font: Font) -> bool:
        return isinstance(font, TtfFont) and font.is_variable

    @classmethod
    def _font_face_descriptors(cls, font: Font) -> list[tuple[str, str]]:
        if cls._is_variable_ttf(font):
            descriptors: list[tuple[str, str]] = [("font-style", "normal")]
            for axis in font.variable_axes:
                if axis.tag == "wght":
                    descriptors.append(
                        ("font-weight", f"{_format_axis_value(axis.min_value)} {_format_axis_value(axis.max_value)}")
                    )
                elif axis.tag == "wdth":
                    descriptors.append(
                        ("font-stretch", f"{_format_axis_value(axis.min_value)}% {_format_axis_value(axis.max_value)}%")
                    )
            return descriptors

        style = (font.font_style or "").lower()
        if "italic" in style:
            return [("font-style", "italic")]
        if "oblique" in style:
            return [("font-style", "oblique")]
        return [("font-style", "normal")]

    @classmethod
    def _variable_axis_markup(cls, font: Font) -> str:
        if not cls._is_variable_ttf(font):
            return ""
        items = []
        controls = []
        for axis in font.variable_axes:
            items.append(
                "<li>"
                f"<strong>{html.escape(axis.label)}</strong> "
                f"({html.escape(axis.tag)}) - "
                f"min {html.escape(_format_axis_value(axis.min_value))}, "
                f"default {html.escape(_format_axis_value(axis.default_value))}, "
                f"max {html.escape(_format_axis_value(axis.max_value))}"
                "</li>"
            )
            axis_tag = html.escape(axis.tag)
            axis_label = html.escape(axis.label)
            min_value = _format_axis_value(axis.min_value)
            default_value = _format_axis_value(axis.default_value)
            max_value = _format_axis_value(axis.max_value)
            controls.append(
                "      <div class=\"axis-control\">\n"
                f"        <label for=\"axis-{axis_tag}\"><span>{axis_label} ({axis_tag})</span>"
                f"<span class=\"axis-value\" data-axis-value=\"{axis_tag}\">{default_value}</span></label>\n"
                f"        <input id=\"axis-{axis_tag}\" type=\"range\" min=\"{html.escape(min_value)}\" "
                f"max=\"{html.escape(max_value)}\" value=\"{html.escape(default_value)}\" step=\"1\" "
                f"data-axis=\"{axis_tag}\">\n"
                f"        <div class=\"axis-range\">Range {html.escape(min_value)} to {html.escape(max_value)}</div>\n"
                "      </div>\n"
            )
        if not items:
            return ""
        joined = "\n      ".join(items)
        control_markup = "".join(controls)
        return (
            "  <section>\n"
            "    <h2>Variable Axes</h2>\n"
            "    <div class=\"axis-controls\">\n"
            f"{control_markup}"
            "    </div>\n"
            "    <ul>\n"
            f"      {joined}\n"
            "    </ul>\n"
            "    <script>\n"
            "      const specimen = document.querySelector('.specimen');\n"
            "      const axisInputs = document.querySelectorAll('.axis-control input');\n"
            "      const axisValues = document.querySelectorAll('[data-axis-value]');\n"
            "      const formatAxisValue = (value) => {\n"
            "        const numeric = Number(value);\n"
            "        return Number.isInteger(numeric) ? String(numeric) : numeric.toFixed(2).replace(/0+$/, '').replace(/\\.$/, '');\n"
            "      };\n"
            "      const updateVariationSettings = () => {\n"
            "        const settings = [];\n"
            "        for (const input of axisInputs) {\n"
            "          const axisTag = input.dataset.axis || '';\n"
            "          settings.push(`\"${axisTag}\" ${input.value}`);\n"
            "        }\n"
            "        if (specimen) {\n"
            "          specimen.style.fontVariationSettings = settings.join(', ');\n"
            "        }\n"
            "        for (const output of axisValues) {\n"
            "          const axisTag = output.dataset.axisValue || '';\n"
            "          const source = document.querySelector(`.axis-control input[data-axis=\"${axisTag}\"]`);\n"
            "          if (source) {\n"
            "            output.textContent = formatAxisValue(source.value);\n"
            "          }\n"
            "        }\n"
            "      };\n"
            "      for (const input of axisInputs) {\n"
            "        input.addEventListener('input', updateVariationSettings);\n"
            "      }\n"
            "      updateVariationSettings();\n"
            "    </script>\n"
            "  </section>\n"
        )

    @classmethod
    def _build_family_image_assets(
        cls,
        bundles: list[WebFontBundle],
        *,
        preview_text: str,
    ) -> list[WebFontAsset]:
        assets: list[WebFontAsset] = []
        if any(bundle.preview_font is not None for bundle in bundles):
            waterfall = cls.build_family_waterfall_preview(bundles, preview_text=preview_text)
            assets.append(
                WebFontAsset(
                    filename=waterfall.filename,
                    media_type=waterfall.media_type,
                    data=waterfall.data,
                )
            )
            matrix = cls.build_family_matrix_preview(bundles, preview_text=preview_text)
            assets.append(
                WebFontAsset(
                    filename=matrix.filename,
                    media_type=matrix.media_type,
                    data=matrix.data,
                )
            )
        return assets

    @classmethod
    def _build_bundle_manifest(
        cls,
        *,
        original_font: Font,
        prepared_font: Font,
        family: str,
        style: str,
        css_filename: str,
        html_filename: str,
        font_assets: list[WebFontAsset],
        preview_text: str,
        specimen_template: str,
        instance_name: str | None,
        instance_coordinates: dict[str, float] | None,
        export_mode: str,
        export_note: str | None,
        auto_instanced_default: bool,
        coverage: SubsetCoverage | None,
        export_reason: str | None,
        requested_variable_mode: str,
        requested_naming_strategy: str,
        requested_family_suffix: str | None,
        requested_legacy_family_name: str | None,
        requested_typographic_family_name: str | None,
        requested_legacy_style_name: str | None,
        requested_typographic_style_name: str | None,
        requested_stat_policy: str,
        supported_stat_policies: tuple[str, ...],
        stat_policy_recommendation: str | None,
        stat_policy_recommendation_reasons: tuple[str, ...],
        stat_policy_next_action: str | None,
        stat_policy_override_suggestion: str | None,
        stat_policy_override_suggestion_reasons: tuple[str, ...],
        presets: str | Iterable[str],
        text: str,
        codepoints: Iterable[int],
        ranges: Iterable[tuple[int, int] | range],
    ) -> dict[str, object]:
        range_items = []
        for item in ranges:
            if isinstance(item, range):
                range_items.append([item.start, item.stop - 1])
            else:
                range_items.append([int(item[0]), int(item[1])])
        preset_list = [presets] if isinstance(presets, str) else [str(value) for value in presets]
        coordinate_map = (
            {tag: float(value) for tag, value in instance_coordinates.items()}
            if instance_coordinates is not None
            else {}
        )
        return {
            "kind": "web_bundle",
            "source_font_type": original_font.font_type.value,
            "source_is_variable": cls._is_variable_ttf(original_font),
            "output_font_type": prepared_font.font_type.value,
            "output_is_variable": cls._is_variable_ttf(prepared_font),
            "requested_variable_mode": requested_variable_mode,
            "requested_naming_strategy": requested_naming_strategy,
            "requested_family_suffix": requested_family_suffix,
            "requested_legacy_family_name": requested_legacy_family_name,
            "requested_typographic_family_name": requested_typographic_family_name,
            "requested_legacy_style_name": requested_legacy_style_name,
            "requested_typographic_style_name": requested_typographic_style_name,
            "requested_stat_policy": requested_stat_policy,
            "supported_stat_policies": list(supported_stat_policies),
            "stat_policy_recommendation": stat_policy_recommendation,
            "stat_policy_recommendation_reasons": list(stat_policy_recommendation_reasons),
            "stat_policy_next_action": stat_policy_next_action,
            "stat_policy_override_suggestion": stat_policy_override_suggestion,
            "stat_policy_override_suggestion_reasons": list(
                stat_policy_override_suggestion_reasons
            ),
            "export_mode": export_mode,
            "export_note": export_note,
            "export_reason": export_reason,
            "auto_instanced_default": auto_instanced_default,
            "family": family,
            "style": style,
            "css_filename": css_filename,
            "html_filename": html_filename,
            "font_assets": [asset.filename for asset in font_assets],
            "preview_text": preview_text,
            "specimen_template": specimen_template,
            "instance_name": instance_name,
            "instance_coordinates": coordinate_map,
            "subset": {
                "presets": preset_list,
                "text": text,
                "codepoints": [int(value) for value in codepoints],
                "ranges": range_items,
                "applied": bool(preset_list or text or tuple(codepoints) or range_items),
                "coverage": coverage.to_dict() if coverage is not None else None,
            },
        }

    @classmethod
    def _build_family_manifest(
        cls,
        bundles: list[WebFontBundle],
        *,
        family_name: str,
        css_filename: str,
        html_filename: str,
        specimen_template: str,
        asset_filenames: list[str],
    ) -> dict[str, object]:
        return {
            "kind": "web_family_package",
            "family_name": family_name,
            "css_filename": css_filename,
            "html_filename": html_filename,
            "asset_filenames": asset_filenames,
            "specimen_template": specimen_template,
            "bundle_count": len(bundles),
            "bundles": [
                {
                    "family": bundle.family,
                    "style": bundle.style,
                    "css_filename": bundle.css_filename,
                    "html_filename": bundle.html_filename,
                    "manifest_filename": bundle.manifest_filename,
                    "export_mode": bundle.manifest.get("export_mode"),
                    "export_note": bundle.manifest.get("export_note"),
                    "export_reason": bundle.manifest.get("export_reason"),
                    "requested_naming_strategy": bundle.manifest.get("requested_naming_strategy"),
                    "requested_family_suffix": bundle.manifest.get("requested_family_suffix"),
                    "requested_legacy_family_name": bundle.manifest.get("requested_legacy_family_name"),
                    "requested_typographic_family_name": bundle.manifest.get("requested_typographic_family_name"),
                    "requested_legacy_style_name": bundle.manifest.get("requested_legacy_style_name"),
                    "requested_typographic_style_name": bundle.manifest.get("requested_typographic_style_name"),
                    "requested_stat_policy": bundle.manifest.get("requested_stat_policy"),
                    "supported_stat_policies": bundle.manifest.get(
                        "supported_stat_policies",
                        [],
                    ),
                    "stat_policy_recommendation": bundle.manifest.get("stat_policy_recommendation"),
                    "stat_policy_recommendation_reasons": bundle.manifest.get(
                        "stat_policy_recommendation_reasons",
                        [],
                    ),
                    "stat_policy_next_action": bundle.manifest.get("stat_policy_next_action"),
                    "stat_policy_override_suggestion": bundle.manifest.get(
                        "stat_policy_override_suggestion"
                    ),
                    "stat_policy_override_suggestion_reasons": bundle.manifest.get(
                        "stat_policy_override_suggestion_reasons",
                        [],
                    ),
                    "coverage": _coverage_summary_from_manifest(bundle.manifest),
                    "review_label": _bundle_review_label(bundle),
                    "instance_coordinates": bundle.manifest.get("instance_coordinates", {}),
                    "font_assets": [asset.filename for asset in bundle.font_assets],
                }
                for bundle in bundles
            ],
        }

    @classmethod
    def _build_family_review_export_manifest(
        cls,
        bundles: list[WebFontBundle],
        *,
        context: dict[str, object],
        asset_filenames: list[str],
    ) -> dict[str, object]:
        return {
            "kind": "family_review_export",
            "family_name": context["family_name"],
            "preview_text": context["preview_text"],
            "board_filename": context["board_filename"],
            "markdown_filename": context["markdown_filename"],
            "html_filename": context["html_filename"],
            "caption": context["caption"],
            "summary": context["summary"],
            "alt_text": context["alt_text"],
            "asset_filenames": asset_filenames,
            "bundle_count": len(bundles),
            "bundles": [
                {
                    "family": bundle.family,
                    "style": bundle.style,
                    "review_label": _bundle_review_label(bundle),
                    "instance_coordinates": bundle.manifest.get("instance_coordinates", {}),
                }
                for bundle in bundles
            ],
        }

    @classmethod
    def _build_family_review_export_markdown(cls, context: dict[str, object]) -> str:
        style_lines = "\n".join(f"- {style}" for style in context["style_labels"])
        return (
            f"# {context['family_name']} Review Board\n\n"
            f"{context['summary']}\n\n"
            f"![{context['alt_text']}]({context['board_filename']})\n\n"
            f"*{context['caption']}*\n\n"
            "Included styles:\n"
            f"{style_lines}\n"
        )

    @classmethod
    def _build_family_review_export_html(cls, context: dict[str, object]) -> str:
        style_items = "".join(
            f"  <li>{html.escape(style)}</li>\n" for style in context["style_labels"]
        )
        return (
            '<figure class="family-review-export">\n'
            f'  <img src="{html.escape(str(context["board_filename"]))}" '
            f'alt="{html.escape(str(context["alt_text"]))}">\n'
            f"  <figcaption>{html.escape(str(context['caption']))}</figcaption>\n"
            "</figure>\n"
            f"<p>{html.escape(str(context['summary']))}</p>\n"
            "<ul>\n"
            f"{style_items}"
            "</ul>\n"
        )

    @classmethod
    def _family_review_export_context(
        cls,
        bundles: list[WebFontBundle],
        *,
        family_name: str,
        preview_text: str,
        board_filename: str,
    ) -> dict[str, object]:
        style_labels = [_bundle_review_label(bundle) for bundle in bundles]
        style_summary = ", ".join(style_labels)
        alt_text = f"{family_name} family review board preview"
        caption = (
            f"{family_name} review board combining waterfall and matrix previews "
            f"for {len(bundles)} selected styles."
        )
        summary = (
            f"Ready-to-share family review board for {family_name} using preview text "
            f'"{preview_text}" across {style_summary}.'
        )
        stem = Path(board_filename).stem
        return {
            "family_name": family_name,
            "preview_text": preview_text,
            "board_filename": board_filename,
            "markdown_filename": f"{stem}.md",
            "html_filename": f"{stem}.html",
            "alt_text": alt_text,
            "caption": caption,
            "summary": summary,
            "style_labels": style_labels,
        }

    @classmethod
    def _render_waterfall_preview(
        cls,
        bundles: list[WebFontBundle],
        *,
        preview_text: str,
    ) -> bytes | None:
        line_specs: list[tuple[Font, str, float]] = []
        for bundle in bundles:
            if bundle.preview_font is None:
                continue
            for size in (72.0, 48.0, 32.0, 20.0):
                line_specs.append((bundle.preview_font, f"{bundle.style} {preview_text}", size))
        return cls._render_preview_lines(line_specs)

    @classmethod
    def _render_matrix_preview(
        cls,
        bundles: list[WebFontBundle],
        *,
        preview_text: str,
    ) -> bytes | None:
        grid_png = cls._render_matrix_grid_preview(bundles, preview_text=preview_text)
        if grid_png is not None:
            return grid_png
        line_specs = [
            (bundle.preview_font, f"{bundle.style} {preview_text}", 30.0)
            for bundle in bundles
            if bundle.preview_font is not None
        ]
        return cls._render_preview_lines(line_specs, padding=24, line_gap=16)

    @classmethod
    def _render_matrix_grid_preview(
        cls,
        bundles: list[WebFontBundle],
        *,
        preview_text: str,
    ) -> bytes | None:
        metadata = _matrix_grid_metadata(bundles)
        if metadata is None:
            return None

        ordered_bundles = metadata["bundles"]
        previews = [
            FontPreviewBuilder.build(
                bundle.preview_font,
                text=preview_text,
                size=42.0,
                padding=18,
                file_stem=_slugify_filename(_bundle_review_label(bundle)),
            )
            for bundle in ordered_bundles
            if bundle.preview_font is not None
        ]
        if len(previews) != len(ordered_bundles):
            return None

        sheet = FontPreviewBuilder.compose_sheet(
            previews,
            columns=metadata["columns"],
            gap=16,
            title=metadata["title"],
            column_headers=metadata["column_headers"],
            row_headers=metadata["row_headers"],
            file_stem="family-matrix",
        )
        return sheet.data

    @staticmethod
    def _render_preview_lines(
        line_specs: list[tuple[Font, str, float]],
        *,
        padding: int = 28,
        line_gap: int = 20,
    ) -> bytes | None:
        from aspose_font.rasterizer import Rasterizer

        layouts: list[object] = []
        max_width = 0.0
        total_height = padding

        for font, text, size in line_specs:
            layout = TextRenderer.layout(font, text, size=size, kern=True)
            layouts.append(layout)
            max_width = max(max_width, layout.total_width)
            total_height += max(1, int(round(layout.ascender - layout.descender))) + line_gap

        if not layouts:
            return None

        total_height = max(1, total_height - line_gap + padding)
        canvas_width = max(1, int(max_width + padding * 2))
        raster = Rasterizer(canvas_width, total_height, background=(255, 253, 248))

        baseline_y = float(padding)
        for layout in layouts:
            baseline_y += layout.ascender
            transform = (1.0, 0.0, 0.0, -1.0, float(padding), baseline_y)
            for glyph_layout in layout.glyphs:
                if glyph_layout.path is not None and len(glyph_layout.path) > 0:
                    raster.draw_path(glyph_layout.path, color=(17, 17, 17), transform=transform)
            baseline_y += -layout.descender + line_gap
        return raster.to_png()


def _slugify_filename(value: str) -> str:
    chars = []
    previous_dash = False
    for ch in value.lower():
        if ch.isalnum():
            chars.append(ch)
            previous_dash = False
        else:
            if not previous_dash:
                chars.append("-")
                previous_dash = True
    slug = "".join(chars).strip("-")
    return slug or "web-font"


def _css_format(filename: str) -> str:
    if filename.endswith(".woff2"):
        return "woff2"
    if filename.endswith(".woff"):
        return "woff"
    return "unknown"


def _escape_css_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "\\'")


def _format_axis_value(value: float) -> str:
    if float(value).is_integer():
        return str(int(value))
    return f"{value:.2f}".rstrip("0").rstrip(".")


def _normalize_specimen_template(value: str) -> str:
    normalized = value.strip().lower()
    if normalized not in _SPECIMEN_TEMPLATES:
        choices = ", ".join(_SPECIMEN_TEMPLATES)
        raise ValueError(f"Unknown specimen template {value!r}. Expected one of: {choices}.")
    return normalized


def _format_template_label(value: str) -> str:
    return value[:1].upper() + value[1:]


def _normalize_variable_export_mode(value: str) -> str:
    normalized = value.strip().lower()
    if normalized not in _VARIABLE_EXPORT_MODES:
        choices = ", ".join(_VARIABLE_EXPORT_MODES)
        raise ValueError(f"Unknown variable export mode {value!r}. Expected one of: {choices}.")
    return normalized


def _normalize_naming_strategy(value: str) -> str:
    normalized = value.strip().lower()
    choices = TtfFont.available_naming_strategies()
    if normalized not in choices:
        expected = ", ".join(choices)
        raise ValueError(f"Unknown naming strategy {value!r}. Expected one of: {expected}.")
    return normalized


def _format_export_mode_label(value: str) -> str:
    return value.replace("-", " ").title()


def _bundle_review_label(bundle: WebFontBundle) -> str:
    if bundle.review_label:
        return bundle.review_label
    coordinate_label = _bundle_coordinate_label(bundle)
    return coordinate_label or bundle.style


def _bundle_coordinate_label(bundle: WebFontBundle) -> str:
    coordinates = bundle.manifest.get("instance_coordinates")
    if not isinstance(coordinates, dict) or not coordinates:
        return ""
    parts: list[str] = []
    for tag in sorted(coordinates):
        value = coordinates[tag]
        try:
            numeric_value = float(value)
        except (TypeError, ValueError):
            parts.append(f"{tag}={value}")
        else:
            parts.append(f"{tag}={_format_axis_value(numeric_value)}")
    return " ".join(parts)


def _coverage_summary_from_manifest(manifest: dict[str, object]) -> dict[str, object] | None:
    subset = manifest.get("subset")
    if not isinstance(subset, dict):
        return None
    coverage = subset.get("coverage")
    if not isinstance(coverage, dict):
        return None
    missing = coverage.get("missing_codepoints")
    groups = coverage.get("groups")
    return {
        "requested_count": int(coverage.get("requested_count", 0)),
        "covered_count": int(coverage.get("covered_count", 0)),
        "missing_count": int(coverage.get("missing_count", 0)),
        "fully_covered": bool(coverage.get("fully_covered", False)),
        "missing_codepoints_sample": [
            int(value) for value in (missing if isinstance(missing, list) else [])[:12]
        ],
        "groups": [
            {
                "kind": str(group.get("kind", "")),
                "label": str(group.get("label", "")),
                "requested_count": int(group.get("requested_count", 0)),
                "covered_count": int(group.get("covered_count", 0)),
                "missing_count": int(group.get("missing_count", 0)),
                "fully_covered": bool(group.get("fully_covered", False)),
                "missing_codepoints_sample": [
                    int(value)
                    for value in (
                        group.get("missing_codepoints")
                        if isinstance(group.get("missing_codepoints"), list)
                        else []
                    )[:12]
                ],
            }
            for group in (groups if isinstance(groups, list) else [])
            if isinstance(group, dict)
        ],
    }


def _matrix_grid_metadata(bundles: list[WebFontBundle]) -> dict[str, object] | None:
    candidate_bundles = [bundle for bundle in bundles if bundle.preview_font is not None]
    if not candidate_bundles:
        return None

    coordinate_maps: list[dict[str, float]] = []
    ordered_tags: list[str] = []
    for bundle in candidate_bundles:
        coordinates = bundle.manifest.get("instance_coordinates")
        if not isinstance(coordinates, dict) or not coordinates:
            return None
        normalized: dict[str, float] = {}
        for tag, value in coordinates.items():
            try:
                normalized[tag] = float(value)
            except (TypeError, ValueError):
                return None
            if tag not in ordered_tags:
                ordered_tags.append(tag)
        coordinate_maps.append(normalized)

    varying_axes = [
        tag
        for tag in ordered_tags
        if len({_coord_key(coords[tag]) for coords in coordinate_maps if tag in coords}) > 1
    ]
    if not varying_axes or len(varying_axes) > 2:
        return None

    primary_axis = varying_axes[0]
    primary_values = sorted(
        {coords[primary_axis] for coords in coordinate_maps},
        key=_coord_key,
    )
    secondary_axis = varying_axes[1] if len(varying_axes) == 2 else None
    secondary_values = (
        sorted({coords[secondary_axis] for coords in coordinate_maps}, key=_coord_key)
        if secondary_axis is not None
        else []
    )

    bundle_lookup: dict[tuple[float, ...], WebFontBundle] = {}
    for bundle, coordinates in zip(candidate_bundles, coordinate_maps, strict=False):
        key = (coordinates[primary_axis],)
        if secondary_axis is not None:
            key = (coordinates[primary_axis], coordinates[secondary_axis])
        if key in bundle_lookup:
            return None
        bundle_lookup[key] = bundle

    expected_keys = (
        [(primary_value,) for primary_value in primary_values]
        if secondary_axis is None
        else [
            (primary_value, secondary_value)
            for primary_value in primary_values
            for secondary_value in secondary_values
        ]
    )
    if set(bundle_lookup) != set(expected_keys):
        return None

    ordered_bundles = [bundle_lookup[key] for key in expected_keys]
    if secondary_axis is None:
        title = f"Matrix Preview: {primary_axis}"
        return {
            "bundles": ordered_bundles,
            "columns": len(primary_values),
            "column_headers": [f"{primary_axis}={_format_axis_value(value)}" for value in primary_values],
            "row_headers": None,
            "title": title,
        }

    title = f"Matrix Preview: {primary_axis} x {secondary_axis}"
    return {
        "bundles": ordered_bundles,
        "columns": len(secondary_values),
        "column_headers": [f"{secondary_axis}={_format_axis_value(value)}" for value in secondary_values],
        "row_headers": [f"{primary_axis}={_format_axis_value(value)}" for value in primary_values],
        "title": title,
    }


def _preset_to_unicode_ranges(preset_name: str) -> list[str] | None:
    preset_lower = preset_name.lower()
    if preset_lower == "latin":
        return ["U+0000-00FF"]
    if preset_lower == "latin-ext":
        return ["U+0100-024F", "U+1E00-1EFF"]
    if preset_lower == "cyrillic":
        return ["U+0400-04FF", "U+0500-052F", "U+2DE0-2DFF", "U+A640-A69F"]
    if preset_lower == "greek":
        return ["U+0370-03FF", "U+1F00-1FFF"]
    if preset_lower == "hebrew":
        return ["U+0590-05FF", "U+FB1D-FB4F"]
    if preset_lower == "arabic":
        return ["U+0600-06FF", "U+0750-077F", "U+08A0-08FF", "U+FB50-FDFF", "U+FE70-FEFF"]
    if preset_lower == "devanagari":
        return ["U+0900-097F", "U+A8E0-A8FF"]
    if preset_lower == "thai":
        return ["U+0E00-0E7F"]
    return None


def _coord_key(value: float) -> float:
    return float(value)


def _specimen_template_css(template: str) -> str:
    if template == "editorial":
        return (
            "\nbody.specimen-template-editorial {\n"
            "  background: #f5efe6;\n"
            "  color: #2f2418;\n"
            "}\n\n"
            "body.specimen-template-editorial h1,\n"
            "body.specimen-template-editorial h2,\n"
            "body.specimen-template-editorial h3,\n"
            "body.specimen-template-editorial .waterfall-label {\n"
            "  font-family: Georgia, serif;\n"
            "  letter-spacing: 0.04em;\n"
            "}\n\n"
            "body.specimen-template-editorial .specimen,\n"
            "body.specimen-template-editorial .family-specimen .sample,\n"
            "body.specimen-template-editorial .matrix-cell .sample {\n"
            "  letter-spacing: 0.02em;\n"
            "}\n"
        )
    if template == "lab":
        return (
            "\nbody.specimen-template-lab {\n"
            "  background: #f3f6f8;\n"
            "  color: #10212b;\n"
            "}\n\n"
            "body.specimen-template-lab h1,\n"
            "body.specimen-template-lab h2,\n"
            "body.specimen-template-lab h3,\n"
            "body.specimen-template-lab .axis-range,\n"
            "body.specimen-template-lab .waterfall-label {\n"
            "  font-family: 'Courier New', monospace;\n"
            "}\n\n"
            "body.specimen-template-lab .axis-control,\n"
            "body.specimen-template-lab .matrix-cell,\n"
            "body.specimen-template-lab .family-nav a,\n"
            "body.specimen-template-lab .family-filter button {\n"
            "  border-color: #9eb3c2;\n"
            "  background: #fbfdff;\n"
            "}\n"
        )
    return (
        "\nbody.specimen-template-classic {\n"
        "  background: #faf8f2;\n"
        "  color: #111;\n"
        "}\n"
    )


__all__ = [
    "WebFontAsset",
    "WebFontBundle",
    "WebFontFamilyPackage",
    "WebFontOptimizer",
    "WebFontOptimizerPackage",
    "WebFontBuilder",
]
