"""Autonomous web font optimization decision engine (FONT-255)."""

from __future__ import annotations

import html
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from aspose_font._font_base import Font
from aspose_font.ttf.font import TtfFont
from aspose_font.web import (
    WebFontBuilder,
    WebFontBundle,
    WebFontOptimizerPackage,
)
from aspose_font.web import (
    WebFontOptimizer as WebFontOptimizerBase,
)


class WebFontOptimizer(WebFontOptimizerBase):
    """Extended WebFontOptimizer with interactive playground generation."""

    @classmethod
    def build_interactive_playground(
        cls,
        font: Font,
        family: str,
        style: str,
        preview_text: str,
        specimen_template: str,
        export_mode: str,
        export_note: str | None,
        *,
        dark_mode: bool = False,
        include_font_controls: bool = True,
    ) -> str:
        template_label = html.escape(_format_template_label(specimen_template))
        export_label = html.escape(_format_export_mode_label(export_mode))
        export_note_markup = (
            f"  <p><strong>Export Note:</strong> {html.escape(export_note)}</p>\n"
            if export_note
            else ""
        )

        axis_markup = WebFontBuilder._variable_axis_markup(font)

        css_snippet = cls._build_css_snippet(family, "fonts.css", font)

        specimen_template_normalized = _normalize_specimen_template(specimen_template)

        dark_mode_css = _playground_dark_mode_css(dark_mode)
        control_css = _playground_control_css(include_font_controls)
        playground_js = _playground_javascript(include_font_controls)

        font_controls_markup = ""
        if include_font_controls:
            font_controls_markup = (
                '  <div class="playground-controls">\n'
                "    <label>\n"
                "      <span>Sample Text</span>\n"
                '      <textarea id="specimen-text" rows="3" aria-label="Sample text input"></textarea>\n'
                "    </label>\n"
                '    <div class="control-group">\n'
                "      <span>Font Size</span>\n"
                '      <input type="range" id="font-size" min="16" max="128" value="64" step="1" aria-label="Font size">\n'
                '      <span id="font-size-value" class="control-value">64px</span>\n'
                "    </div>\n"
                '    <div class="control-group">\n'
                "      <span>Line Height</span>\n"
                '      <input type="range" id="line-height" min="0.8" max="2.0" value="1.2" step="0.05" aria-label="Line height">\n'
                '      <span id="line-height-value" class="control-value">1.2</span>\n'
                "    </div>\n"
                '    <button id="dark-mode-toggle" class="dark-mode-toggle" aria-label="Toggle dark mode">Dark Mode</button>\n'
                "  </div>\n"
            )

        return (
            "<!doctype html>\n"
            '<html lang="en">\n'
            "<head>\n"
            '  <meta charset="utf-8">\n'
            '  <meta name="viewport" content="width=device-width, initial-scale=1">\n'
            f"  <title>{html.escape(family)} Playground</title>\n"
            "  <style>\n"
            f"{cls._build_specimen_styles(family, specimen_template_normalized, 'fonts.css')}"
            f"{_specimen_template_css(specimen_template_normalized)}"
            f"{dark_mode_css}"
            f"{control_css}"
            "  </style>\n"
            "</head>\n"
            f'  <body class="specimen-template-{html.escape(specimen_template_normalized)}">\n'
            f"  <h1>{html.escape(family)}</h1>\n"
            f"  <p><strong>Style:</strong> {html.escape(style)}</p>\n"
            f"  <p><strong>Export Mode:</strong> {export_label}</p>\n"
            f"  <p><strong>Template:</strong> {template_label}</p>\n"
            f"{export_note_markup}"
            f"{font_controls_markup}"
            f'  <div class="specimen">{html.escape(preview_text)}</div>\n'
            f"{axis_markup}"
            f'  <section class="playground-section">\n'
            "    <h2>Copyable @font-face</h2>\n"
            '    <div class="css-copy-container">\n'
            f"      <pre><code id=\"css-snippet\">{html.escape(css_snippet)}</code></pre>\n"
            '      <button type="button" id="copy-css-btn" class="copy-btn" aria-label="Copy CSS snippet">Copy</button>\n'
            "    </div>\n"
            "  </section>\n"
            f"  <script>{playground_js}\n"
            "  </script>\n"
            "</body>\n"
            "</html>\n"
        )


def _format_template_label(value: str) -> str:
    return value[:1].upper() + value[1:]


def _format_export_mode_label(value: str) -> str:
    return value.replace("-", " ").title()


def _normalize_specimen_template(value: str) -> str:
    normalized = value.strip().lower()
    if normalized not in ("classic", "editorial", "lab"):
        choices = "classic, editorial, lab"
        raise ValueError(f"Unknown specimen template {value!r}. Expected one of: {choices}.")
    return normalized


def _playground_dark_mode_css(dark_mode: bool) -> str:
    if not dark_mode:
        return ""
    return (
        "html.dark-mode {\n"
        "  background: #1a1a2e;\n"
        "  color: #e0e0e0;\n"
        "}\n"
        "html.dark-mode h1, html.dark-mode h2, html.dark-mode h3 {\n"
        "  color: #ffffff;\n"
        "}\n"
        "html.dark-mode .axis-control,\n"
        "html.dark-mode .playground-controls {\n"
        "  border-color: #3d3d5c;\n"
        "  background: #16213e;\n"
        "}\n"
        "html.dark-mode .axis-value,\n"
        "html.dark-mode .axis-range {\n"
        "  color: #a0a0c0;\n"
        "}\n"
        "html.dark-mode textarea {\n"
        "  background: #0f0f23;\n"
        "  color: #e0e0e0;\n"
        "  border-color: #3d3d5c;\n"
        "}\n"
        "html.dark-mode button {\n"
        "  background: #3d3d5c;\n"
        "  color: #e0e0e0;\n"
        "}\n"
        "html.dark-mode button:hover {\n"
        "  background: #5d5d7c;\n"
        "}\n"
    )


def _playground_control_css(include_font_controls: bool) -> str:
    css = (
        "\n.playground-controls {\n"
        "  display: flex;\n"
        "  gap: 1rem;\n"
        "  margin: 1.5rem 0 2rem;\n"
        "  padding: 1rem;\n"
        "  border: 1px solid #d9d1c7;\n"
        "  border-radius: 0.75rem;\n"
        "  background: #fffdf8;\n"
        "  flex-wrap: wrap;\n"
        "}\n"
        ".playground-controls label {\n"
        "  display: flex;\n"
        "  flex-direction: column;\n"
        "  gap: 0.25rem;\n"
        "  font-size: 0.9rem;\n"
        "}\n"
        '.playground-controls input[type="range"] {\n'
        "  width: 12rem;\n"
        "}\n"
        '.playground-controls input[type="text"] {\n'
        "  width: 100%;\n"
        "  padding: 0.5rem;\n"
        "  border: 1px solid #d9d1c7;\n"
        "  border-radius: 0.25rem;\n"
        "  font-size: 1rem;\n"
        "  font-family: inherit;\n"
        "}\n"
    )
    if include_font_controls:
        css += (
            ".control-group {\n"
            "  display: flex;\n"
            "  align-items: center;\n"
            "  gap: 0.5rem;\n"
            "}\n"
            ".control-group span {\n"
            "  font-weight: 600;\n"
            "  min-width: 4rem;\n"
            "}\n"
            ".control-value {\n"
            "  font-family: monospace;\n"
            "  min-width: 3rem;\n"
            "  text-align: right;\n"
            "}\n"
        )
    css += (
        ".dark-mode-toggle {\n"
        "  margin-left: auto;\n"
        "  padding: 0.5rem 1rem;\n"
        "  border: none;\n"
        "  border-radius: 0.25rem;\n"
        "  cursor: pointer;\n"
        "  font-weight: 600;\n"
        "}\n"
        ".playground-section {\n"
        "  margin-bottom: 2rem;\n"
        "}\n"
        ".playground-section pre {\n"
        "  background: #f0ede8;\n"
        "  padding: 1rem;\n"
        "  border-radius: 0.5rem;\n"
        "  overflow-x: auto;\n"
        "}\n"
        ".playground-section code {\n"
        "  font-family: monospace;\n"
        "}\n"
        ".css-copy-container {\n"
        "  position: relative;\n"
        "  display: flex;\n"
        "  gap: 0.5rem;\n"
        "}\n"
        ".css-copy-container pre {\n"
        "  flex: 1;\n"
        "  margin: 0;\n"
        "  max-height: 200px;\n"
        "}\n"
        ".css-copy-container code {\n"
        "  margin: 0;\n"
        "}\n"
        ".copy-btn {\n"
        "  padding: 0.5rem 1rem;\n"
        "  border: 1px solid #d9d1c7;\n"
        "  border-radius: 0.25rem;\n"
        "  background: #fff;\n"
        "  cursor: pointer;\n"
        "  font-weight: 600;\n"
        "  white-space: nowrap;\n"
        "}\n"
        ".copy-btn:hover {\n"
        "  background: #f5f5f5;\n"
        "}\n"
        ".copy-btn:active {\n"
        "  background: #e5e5e5;\n"
        "}\n"
        ".copy-btn.copied {\n"
        "  background: #d4edda;\n"
        "  border-color: #c3e6cb;\n"
        "  color: #155724;\n"
        "}\n"
    )
    return css


def _playground_javascript(include_font_controls: bool) -> str:
    js = (
        "\n  const specimen = document.querySelector('.specimen');\n"
        "  const axisInputs = document.querySelectorAll('.axis-control input');\n"
        "  const axisValues = document.querySelectorAll('[data-axis-value]');\n"
        "  const formatAxisValue = (value) => {\n"
        "    const numeric = Number(value);\n"
        "    return Number.isInteger(numeric) ? String(numeric) : numeric.toFixed(2).replace(/0+$/, '').replace(/\\.$/, '');\n"
        "  };\n"
        "  const updateVariationSettings = () => {\n"
        "    const settings = [];\n"
        "    for (const input of axisInputs) {\n"
        "      const axisTag = input.dataset.axis || '';\n"
        '      settings.push(`"${axisTag}" ${input.value}`);\n'
        "    }\n"
        "    if (specimen) {\n"
        "      specimen.style.fontVariationSettings = settings.join(', ');\n"
        "    }\n"
        "    for (const output of axisValues) {\n"
        "      const axisTag = output.dataset.axisValue || '';\n"
        '      const source = document.querySelector(`.axis-control input[data-axis="${axisTag}"]`);\n'
        "      if (source) {\n"
        "        output.textContent = formatAxisValue(source.value);\n"
        "      }\n"
        "    }\n"
        "  };\n"
        "  for (const input of axisInputs) {\n"
        "    input.addEventListener('input', updateVariationSettings);\n"
        "  }\n"
        "  updateVariationSettings();\n"
    )
    if include_font_controls:
        js += (
            "  const fontSizeInput = document.querySelector('#font-size');\n"
            "  const fontSizeValue = document.querySelector('#font-size-value');\n"
            "  const lineHeightInput = document.querySelector('#line-height');\n"
            "  const lineHeightValue = document.querySelector('#line-height-value');\n"
            "  const specimenText = document.querySelector('#specimen-text');\n"
            "  if (fontSizeInput && fontSizeValue) {\n"
            "    fontSizeInput.addEventListener('input', () => {\n"
            "      fontSizeValue.textContent = fontSizeInput.value + 'px';\n"
            "      if (specimen) {\n"
            "        specimen.style.fontSize = fontSizeInput.value + 'px';\n"
            "      }\n"
            "    });\n"
            "    fontSizeInput.dispatchEvent(new Event('input'));\n"
            "  }\n"
            "  if (lineHeightInput && lineHeightValue) {\n"
            "    lineHeightInput.addEventListener('input', () => {\n"
            "      lineHeightValue.textContent = lineHeightInput.value;\n"
            "      if (specimen) {\n"
            "        specimen.style.lineHeight = lineHeightInput.value;\n"
            "      }\n"
            "    });\n"
            "    lineHeightInput.dispatchEvent(new Event('input'));\n"
            "  }\n"
        "  if (specimenText) {\n"
        "    specimenText.addEventListener('input', () => {\n"
        "      if (specimen) {\n"
        "        specimen.textContent = specimenText.value;\n"
        "      }\n"
        "    });\n"
        "  }\n"
        "  const copyBtn = document.querySelector('#copy-css-btn');\n"
        "  const cssSnippet = document.querySelector('#css-snippet');\n"
        "  if (copyBtn && cssSnippet) {\n"
        "    copyBtn.addEventListener('click', () => {\n"
        "      const cssText = cssSnippet.textContent;\n"
        "      navigator.clipboard.writeText(cssText).then(() => {\n"
        "        const originalText = copyBtn.textContent;\n"
        "        copyBtn.textContent = 'Copied!';\n"
        "        copyBtn.classList.add('copied');\n"
        "        setTimeout(() => {\n"
        "          copyBtn.textContent = originalText;\n"
        "          copyBtn.classList.remove('copied');\n"
        "        }, 2000);\n"
        "      }).catch(() => {\n"
        "        copyBtn.textContent = 'Failed';\n"
        "        setTimeout(() => {\n"
        "          copyBtn.textContent = 'Copy';\n"
        "        }, 2000);\n"
        "      });\n"
        "    });\n"
        "  }\n"
        )
    js += (
        "  const darkModeToggle = document.querySelector('#dark-mode-toggle');\n"
        "  if (darkModeToggle) {\n"
        "    darkModeToggle.addEventListener('click', () => {\n"
        "      document.documentElement.classList.toggle('dark-mode');\n"
        "    });\n"
        "  }\n"
    )
    return js


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
    return "\nbody.specimen-template-classic {\n  background: #faf8f2;\n  color: #111;\n}\n"


@dataclass(frozen=True)
class WebFontOptimizerDecision:
    """Automated decision result for web export mode."""

    mode: str
    reason: str
    confidence: float
    affected_axes: list[str]
    recommended_presets: list[str]


@dataclass(slots=True)
class _PreparedFontWithDecision:
    font: Font
    export_mode: str
    decision: WebFontOptimizerDecision


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
class WebFontOptimizerPackageWithDecision:
    """Enhanced web package that includes optimization decision metadata."""

    bundle: WebFontBundle
    decision: WebFontOptimizerDecision
    size_summary: dict[str, Any]
    readiness: dict[str, Any]
    notes: list[dict[str, str]]
    manifest: dict[str, Any]
    css: str = ""
    specimen_html: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    decision_report: dict[str, Any] | None = None
    cdn_manifest: dict[str, Any] | None = None

    def write_to(
        self, directory: str | Path, *, decision_report_pdf: str | Path | None = None
    ) -> list[Path]:
        """Write the package to a directory.

        Args:
            directory: Output directory path
            decision_report_pdf: Optional path to write PDF decision report

        Returns:
            List of written file paths
        """
        output_dir = Path(directory)
        written = self.bundle.write_to(output_dir)

        manifest_path = output_dir / "optimizer-manifest.json"
        manifest_path.write_text(
            json.dumps(self.manifest, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        written.append(manifest_path)

        if self.decision_report is not None:
            decision_path = output_dir / "decision_report.json"
            decision_path.write_text(
                json.dumps(self.decision_report, indent=2, sort_keys=True),
                encoding="utf-8",
            )
            written.append(decision_path)
            if decision_report_pdf is not None:
                from aspose_font.web import DecisionReport

                pdf_path = Path(decision_report_pdf)
                if not pdf_path.is_absolute():
                    pdf_path = output_dir / pdf_path
                pdf_path.parent.mkdir(parents=True, exist_ok=True)
                report = DecisionReport(
                    mode=self.decision_report.get("mode", "unknown"),
                    reasons=self.decision_report.get("reasons", []),
                    summary=self.decision_report.get("summary", ""),
                    remediation=self.decision_report.get("remediation", []),
                )
                pdf_data = DecisionReport._build_decision_pdf(report)
                pdf_path.write_bytes(pdf_data)
                written.append(pdf_path)

        if self.cdn_manifest is not None:
            cdn_manifest_path = output_dir / "cdn-manifest.json"
            cdn_manifest_path.write_text(
                json.dumps(self.cdn_manifest, indent=2, sort_keys=True),
                encoding="utf-8",
            )
            written.append(cdn_manifest_path)

        return written


def analyze_font_for_web_optimization(font: Font) -> WebFontOptimizerDecision:
    """
    Analyze a font and make an automated decision about optimal web export mode.

    Decision criteria:
    - Variable fonts with >1 axis and meaningful interpolation: "live"
    - Variable fonts with single axis or minimal deltas: "static-fallback"
    - Static fonts: "static"
    - Fonts with unsupported variation tables: "static-fallback"

    Args:
        font: The font to analyze

    Returns:
        WebFontOptimizerDecision with mode, reason, confidence, affected_axes, and recommended_presets
    """
    mode: str
    reason: str
    confidence: float = 0.0
    affected_axes: list[str] = []
    recommended_presets: list[str] = []

    source_is_variable = isinstance(font, TtfFont) and font.is_variable

    if source_is_variable:
        ttf_font = font
        axes = ttf_font.variable_axes
        axis_count = len(axes) if axes else 0

        if axis_count > 1:
            mode = "live"
            confidence = 0.95
            affected_axes = [ax.tag for ax in axes] if axes else []
            recommended_presets = _suggest_presets_for_axes(axes)
            reason = (
                f"Variable font with {axis_count} axes and meaningful interpolation. "
                "Output supports variable axes."
            )
        elif axis_count == 1:
            mode = "static-fallback"
            confidence = 0.85
            affected_axes = [axes[0].tag] if axes else []
            recommended_presets = _suggest_presets_for_axes(axes)
            reason = (
                "Variable font with single axis or minimal deltas. "
                "Recommended fallback to static export for simpler delivery."
            )
        else:
            mode = "static-fallback"
            confidence = 0.80
            reason = "Variable font with no variable axes detected. Fallback to static export."
    else:
        mode = "static"
        confidence = 1.0
        recommended_presets = _suggest_presets_for_static(font)
        reason = "Font is not variable. Static export is appropriate."

    return WebFontOptimizerDecision(
        mode=mode,
        reason=reason,
        confidence=confidence,
        affected_axes=affected_axes,
        recommended_presets=recommended_presets,
    )


def _suggest_presets_for_axes(axes: list[Any] | None) -> list[str]:
    """Suggest subset presets based on available axes."""
    if not axes:
        return []
    presets = []
    for ax in axes:
        if hasattr(ax, "tag"):
            tag = ax.tag
            if tag in ("wght", "wdth", "slnt", "ital", "opsz"):
                presets.append("latin")
                if tag in ("wght", "wdth"):
                    presets.append("latin-ext")
                break
    if not presets:
        presets.append("latin")
    return list(dict.fromkeys(presets))


def _suggest_presets_for_static(font: Font) -> list[str]:
    """Suggest subset presets for static fonts."""
    presets = ["latin"]
    font_name = (font.font_name or "").lower()
    if "cyrillic" in font_name or "russian" in font_name:
        presets.append("cyrillic")
    if "greek" in font_name:
        presets.append("greek")
    if "hebrew" in font_name:
        presets.append("hebrew")
    if "arabic" in font_name:
        presets.append("arabic")
    return presets


def build_web_optimizer_package(
    font: Font,
    *,
    source_path: str | None = None,
    file_stem: str | None = None,
    include_woff: bool = True,
    font_display: str = "swap",
    preview_text: str = "Hamburgefons 0123456789",
    instance_coordinates: dict[str, float] | None = None,
    instance_name: str | None = None,
    presets: str | tuple[str, ...] = (),
    text: str = "",
    codepoints: tuple[int, ...] = (),
    ranges: tuple[tuple[int, int], ...] = (),
    specimen_template: str = "classic",
    variable_mode: str = "auto",
    naming_strategy: str = "instance-family",
    family_suffix: str | None = None,
    legacy_family_name: str | None = None,
    typographic_family_name: str | None = None,
    legacy_style_name: str | None = None,
    typographic_style_name: str | None = None,
    stat_policy: str = "drop",
    decision: WebFontOptimizerDecision | None = None,
    detailed_reporting: bool = False,
    decision_report: bool = True,
    cdn_base_url: str = "https://cdn.example.com",
    feature_variation_tag: str | None = None,
    **kwargs: Any,
) -> WebFontOptimizerPackageWithDecision:
    """
    One-call web font optimization with automated decision-making.

    This function wraps existing WebFontOptimizer functionality but adds:
    - Automated export mode detection and decision logging
    - Decision-based STAT preservation vs. static synthesis logic
    - Enhanced manifest with decision metadata

    Args:
        font: The font to optimize
        source_path: Optional path to source file for size comparison
        file_stem: Optional filename stem for output assets
        include_woff: Include WOFF format alongside WOFF2
        font_display: Font-display value for @font-face
        preview_text: Preview text for specimen HTML
        instance_coordinates: Explicit coordinate values for instance selection
        instance_name: Named instance to instantiate
        presets: Unicode preset names for subsetting
        text: Text content for subsetting
        codepoints: Individual codepoints for subsetting
        ranges: Codepoint ranges for subsetting
        specimen_template: Specimen template style
        variable_mode: Variable export mode ("auto", "live", "static")
        naming_strategy: Font naming strategy
        family_suffix: Custom family suffix
        legacy_family_name: Explicit legacy family name
        typographic_family_name: Explicit typographic family name
        legacy_style_name: Explicit legacy style name
        typographic_style_name: Explicit typographic style name
        stat_policy: STAT metadata policy
        decision: Optional pre-computed decision to use
        detailed_reporting: Enable detailed performance timing profiling
        decision_report: Generate decision report
        cdn_base_url: Base URL for CDN paths in generated manifest
        feature_variation_tag: Feature variation tag to apply (requires FeatureVariations table)
        **kwargs: Additional keyword arguments

    Returns:
        WebFontOptimizerPackageWithDecision containing bundle, decision, and metadata
    """
    if decision is None:
        decision = analyze_font_for_web_optimization(font)

    effective_variable_mode = _resolve_variable_mode(
        variable_mode,
        decision.mode,
        font,
        presets=presets,
        text=text,
        codepoints=codepoints,
        ranges=ranges,
    )

    package: WebFontOptimizerPackage = WebFontOptimizer.build(
        font,
        source_path=source_path,
        file_stem=file_stem,
        include_woff=include_woff,
        font_display=font_display,
        preview_text=preview_text,
        instance_coordinates=instance_coordinates,
        instance_name=instance_name,
        presets=presets,
        text=text,
        codepoints=codepoints,
        ranges=ranges,
        specimen_template=specimen_template,
        variable_mode=effective_variable_mode,
        naming_strategy=naming_strategy,
        family_suffix=family_suffix,
        legacy_family_name=legacy_family_name,
        typographic_family_name=typographic_family_name,
        legacy_style_name=legacy_style_name,
        typographic_style_name=typographic_style_name,
        stat_policy=stat_policy,
        detailed_reporting=detailed_reporting,
        decision_report=decision_report,
        cdn_base_url=cdn_base_url,
        feature_variation_tag=feature_variation_tag,
        **kwargs,
    )

    size_summary = package.size_summary
    readiness = package.readiness
    notes = package.notes

    metadata = {
        "decision_applied": decision.mode,
        "confidence": decision.confidence,
        "affected_axes": decision.affected_axes,
        "recommended_presets": decision.recommended_presets,
        "decision_reason": decision.reason,
    }

    enhanced_manifest = dict(package.manifest)
    enhanced_manifest["decision"] = decision.mode
    enhanced_manifest["decision_confidence"] = decision.confidence
    enhanced_manifest["decision_metadata"] = metadata
    if feature_variation_tag is not None:
        enhanced_manifest["selected_feature_variation"] = feature_variation_tag

    bundle = package.bundle
    bundle.manifest = enhanced_manifest

    decision_report = package.decision_report
    if decision_report is not None:
        decision_report_dict = {
            "mode": decision_report.mode,
            "decision": decision_report.mode,
            "reasons": decision_report.reasons,
            "reason": decision_report.reason,
            "summary": decision_report.summary,
            "remediation": decision_report.remediation,
            "export_mode": decision.mode,
            "font_path": str(source_path) if source_path else None,
            "confidence": decision.confidence,
            "affected_axes": decision.affected_axes,
        }
    else:
        decision_report_dict = None

    return WebFontOptimizerPackageWithDecision(
        bundle=bundle,
        css=package.css,
        specimen_html=package.specimen_html,
        decision=decision,
        size_summary=size_summary,
        readiness=readiness,
        notes=notes,
        manifest=enhanced_manifest,
        metadata=metadata,
        decision_report=decision_report_dict,
        cdn_manifest=package.cdn_manifest,
    )


def _resolve_variable_mode(
    requested_mode: str,
    analyzed_mode: str,
    font: Font,
    *,
    presets: str | tuple[str, ...] = (),
    text: str = "",
    codepoints: tuple[int, ...] = (),
    ranges: tuple[tuple[int, int], ...] = (),
) -> str:
    """Resolve the effective variable mode based on user request and analysis.

    When subsetting is requested (text, codepoints, ranges, or presets), live variable
    export mode is not supported. In auto mode, this returns "auto" so that WebFontOptimizer
    can handle the subsetting by instantiating the font at default coordinates.
    """
    if requested_mode != "auto":
        return requested_mode

    should_subset = bool(text or codepoints or ranges or presets)
    source_is_variable = isinstance(font, TtfFont) and font.is_variable

    if analyzed_mode == "live":
        if should_subset:
            return "auto"
        return "live" if source_is_variable else "static"
    elif analyzed_mode == "static-fallback":
        return "static"
    else:
        return "auto"


def build_web_optimizer_package_with_plan(
    font: Font,
    decision: WebFontOptimizerDecision,
    *,
    source_path: str | None = None,
    file_stem: str | None = None,
    include_woff: bool = True,
    font_display: str = "swap",
    preview_text: str = "Hamburgefons 0123456789",
    instance_coordinates: dict[str, float] | None = None,
    instance_name: str | None = None,
    presets: str | tuple[str, ...] = (),
    text: str = "",
    codepoints: tuple[int, ...] = (),
    ranges: tuple[tuple[int, int], ...] = (),
    specimen_template: str = "classic",
    variable_mode: str = "auto",
    naming_strategy: str = "instance-family",
    family_suffix: str | None = None,
    legacy_family_name: str | None = None,
    typographic_family_name: str | None = None,
    legacy_style_name: str | None = None,
    typographic_style_name: str | None = None,
    stat_policy: str = "drop",
    cdn_base_url: str = "https://cdn.example.com",
    **kwargs: Any,
) -> WebFontOptimizerPackageWithDecision:
    """
    Enhanced version that accepts a pre-computed decision for deterministic workflows.

    Useful for batch processing or when decisions are made externally.

    Args:
        font: The font to optimize
        decision: Pre-computed optimization decision
        source_path: Optional path to source file for size comparison
        file_stem: Optional filename stem for output assets
        include_woff: Include WOFF format alongside WOFF2
        font_display: Font-display value for @font-face
        preview_text: Preview text for specimen HTML
        instance_coordinates: Explicit coordinate values for instance selection
        instance_name: Named instance to instantiate
        presets: Unicode preset names for subsetting
        text: Text content for subsetting
        codepoints: Individual codepoints for subsetting
        ranges: Codepoint ranges for subsetting
        specimen_template: Specimen template style
        variable_mode: Variable export mode ("auto", "live", "static")
        naming_strategy: Font naming strategy
        family_suffix: Custom family suffix
        legacy_family_name: Explicit legacy family name
        typographic_family_name: Explicit typographic family name
        legacy_style_name: Explicit legacy style name
        typographic_style_name: Explicit typographic style name
        stat_policy: STAT metadata policy
        cdn_base_url: Base URL for CDN paths in generated manifest
        **kwargs: Additional keyword arguments

    Returns:
        WebFontOptimizerPackageWithDecision containing bundle, decision, and metadata
    """
    return build_web_optimizer_package(
        font,
        source_path=source_path,
        file_stem=file_stem,
        include_woff=include_woff,
        font_display=font_display,
        preview_text=preview_text,
        instance_coordinates=instance_coordinates,
        instance_name=instance_name,
        presets=presets,
        text=text,
        codepoints=codepoints,
        ranges=ranges,
        specimen_template=specimen_template,
        variable_mode=variable_mode,
        naming_strategy=naming_strategy,
        family_suffix=family_suffix,
        legacy_family_name=legacy_family_name,
        typographic_family_name=typographic_family_name,
        legacy_style_name=legacy_style_name,
        typographic_style_name=typographic_style_name,
        stat_policy=stat_policy,
        decision=decision,
        cdn_base_url=cdn_base_url,
        **kwargs,
    )
