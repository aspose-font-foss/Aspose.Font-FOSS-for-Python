# aspose-font

Pure-Python font workflow automation for teams that need to prepare, review, package, and explain fonts without native runtime dependencies.

[![Buyer Workflows](https://img.shields.io/badge/Workflow-Buyer_Focused-blue?logo=fontawesome&logoColor=white)](#three-buyer-workflows)

## Three Buyer Workflows

Use it when you need deployable web-font packages, visual review assets, variable-font instances, and QA evidence from scripts, CI, or local CLI workflows.

Public GitHub repository: [aspose-font-foss/Aspose.Font-FOSS-for-Python](https://github.com/aspose-font-foss/Aspose.Font-FOSS-for-Python)

## What You Get

| Workflow | Output | Why this matters |
| --- | --- | --- |
| **Optimize for web** | WOFF2/WOFF files, CSS @font-face, specimen HTML, JSON manifests, coverage diagnostics, export-mode explanations, and readiness scores. | Frontend teams ship fonts with copyable CSS, interactive specimens, and measurable byte savings. |
| **Generate QA evidence** | Font QA Reports as JSON/HTML/PNG package deliverables, severity scoring, compatibility/delta reports, and prioritized remediation recommendations. | Type designers make release decisions with actionable evidence, not just raw metrics. |
| **Create release-safe variable instances** | Static instance fonts with naming strategies, STAT metadata, custom family suffixes, review manifests, and comparison boards. | Brand teams get approval-ready fonts with documented naming decisions and visual proof. |
| **Generate visual proof** | PNG/SVG previews, axis-grid sheets, before/after comparisons, APNG animations, storyboard packages, and showcase outputs. | Developers and designers verify font behavior across axes and use cases. |
| **Automate font operations** | Python APIs, CLI commands, and optional MCP tools over the same pure-Python engine. | Automation teams run the same workflows in CI without native binary dependencies. |

## Who Is This For?

| Persona | Job To Be Done | What Works Now | Highest-Value Gap |
|---------|---------------|----------------|-------------------|
| **Frontend team** | Convert source font to web-ready package with CSS, specimen, coverage diagnostics | `WebFontOptimizer`, web-optimize, WOFF2/WOFF, CSS/specimen HTML, manifests, readiness scores | README-visible generated output with before/after size comparison and ready-for-handoff confirmation |
| **Type designer** | Review whether variable font and instances are safe to release | Preview boards, compatibility/delta reports, `FontQaReporter` JSON/HTML/package | QA report packages with severity scoring, remediation recommendations, and visual evidence |
| **Brand team** | Produce named static instances for approval | Instancing, naming strategies, review boards, axis grids | Release package with instances, naming/STAT evidence, previews, and review manifest |
| **Build/automation owner** | Run same workflow in CI without native binaries | Pure-Python, CLI, MCP, fixture-backed tests, typed exceptions | Supported/unsupported fixture matrix, performance envelope, and failure taxonomy |
| **Frontend/design reviewer** | Understand what a font can do before implementation | Axis snapshots, named-instance summaries, preview boards | Plain-language capability discovery with visual proof |

## Quick Start: Three Buyer Workflows

### 1. Web Font Optimization

**Business lens:** Frontend teams, web delivery

**Python:**
```python
from aspose_font import FontLoader, WebFontOptimizer

font = FontLoader.open("testdata/Roboto-VariableFont_wdth,wght.ttf")
package = WebFontOptimizer.build(
    font,
    presets=("latin",),
    text="Variable Font Web Demo 0123456789",
    variable_mode="auto",
    include_woff=True,
)
package.write_to("demo/web_opt_demo")
```

**CLI:**
```bash
aspose-font web-optimize testdata/Roboto-VariableFont_wdth,wght.ttf demo/web_opt_demo --preset latin --text "Variable Font Web Demo 0123456789"
```

**Generated Output:**
```
demo/web_opt_demo/
├── roboto-variablefont-wdth,wght.woff2          (WOFF2 font, ~28KB)
├── roboto-variablefont-wdth,wght.woff           (WOFF fallback, ~32KB)
├── fonts.css                                    (CSS @font-face with unicode-range)
├── specimen.html                                (Interactive specimen with axis controls)
├── web-manifest.json                            (Bundle manifest)
└── optimizer-manifest.json                      (Optimizer package manifest)
```

**Key Features:**
- **WOFF2/WOFF fonts**: Browser-optimized web font delivery
- **CSS @font-face**: Copyable CSS with `font-display: swap` and `unicode-range` rules
- **Interactive specimen HTML**: Live variable-axis controls for web preview
- **Optimizer manifest**: Size summary, readiness score, and remediation notes

> **Note**: Run `python scripts/demo_web_optimizer.py` to generate this output locally and inspect the generated package.

---

### 2. Font QA Reporting

**Business lens:** Type designers, release decisions

**Python:**
```python
from aspose_font import FontLoader, FontQaReporter

font = FontLoader.open("Roboto-VariableFont_wdth,wght.ttf")
package = FontQaReporter.build_package(
    font,
    "qa-package",
    presets=("latin",),
    text="QA",
    preview_instance_name="Bold",
)
print(package.json_path)
print(package.html_path)
print(package.preview_path)
```

**CLI:**
```bash
aspose-font qa-report Roboto-VariableFont_wdth,wght.ttf --preset latin --text "QA" --package-output qa-package --preview-instance-name Bold
```

**Generated output:**
```
qa-package/
├── qa-report.json
├── qa-report.html
└── preview.png
```

The package includes:
- **JSON diagnostics** with severity levels (Blocker/Warning/Info)
- **Self-contained HTML report** with embedded visual previews
- **Preview PNG** with variable axes and named instances
- **Review manifest** with artifact references and handoff labels
- **Readiness score** with prioritized causes and remediation recommendations

---

### 3. Release-Safe Variable Instance Packages

**Business lens:** Brand teams, design approval

**Python:**
```python
from aspose_font import FontLoader, VariableInstanceBuilder

font = FontLoader.open("Roboto-VariableFont_wdth,wght.ttf")
package = VariableInstanceBuilder.build_package(
    font,
    instance_names=["Bold"],
    naming_strategy="ribbi-safe",
    family_suffix="Beta",
    stat_policy="static",
    preview_text="Review",
    output_dir="var-package-output",
)
```

**CLI:**
```bash
aspose-font var-package Roboto-VariableFont_wdth,wght.ttf --instance-name Bold --naming-strategy ribbi-safe --family-suffix Beta --stat-policy static --preview-text "Review" --output-dir var-package-output
```

**Generated output:**
```
var-package-output/
├── Roboto-Beta-Bold.ttf
├── stat-evidence.json
├── review-manifest.json
└── comparison-board.png
```

The package includes:
- **Static instance fonts** with safe naming strategies
- **STAT evidence JSON** with policy decisions and recommendations
- **Review manifest JSON** with handoff-ready labels
- **Comparison board PNG** for approval reviews

## What Can This Font Do?

*Plain-language capability discovery*

Understanding a font's capabilities helps frontend teams, designers, and developers make confident implementation decisions.

### Variable Axes

Variable fonts expose axes that control appearance:
- **Weight (wght)**: 100–900 (Thin to Black)
- **Width (wdth)**: 25%–150% (Condensed to Expanded)
- **Italics (ital)**: 0–1 (Roman to Italic)
- **Optical size (opsz)**: 6–144 pt

Each axis has default values, preset labels (like "Bold" = 700), and customizable coordinates.

### Coverage Diagnostics

What scripts and languages does this font support?
- **Latin**: Western European languages
- **Cyrillic**: Russian, Ukrainian, Bulgarian, etc.
- **Greek**: Modern Greek
- **Hebrew**: Hebrew script
- **Arabic**: Arabic script with contextual forms
- **Devanagari**: Hindi, Sanskrit, Marathi
- **Thai**: Thai script

Coverage gaps are reported in web optimizer manifests and QA reports.

### CSS Hints

Use these `@font-face` best practices:

```css
@font-face {
  font-family: 'Roboto';
  src: url('roboto.woff2') format('woff2');
  font-weight: 400;
  font-display: swap;
  unicode-range: U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+02C6, U+02DA, U+02DC, U+2000-206F, U+2074, U+20AC, U+2122, U+2191, U+2193, U+2212, U+2215, U+FEFF, U+FFFD;
}
```

- **font-display: swap** prevents invisible text during load
- **unicode-range** subsets glyphs per language for faster loading
- **font-weight/font-style** match CSS usage patterns

### Release Risks

Before shipping, check:
1. **Name-table collisions**: Custom naming strategies prevent font menu conflicts
2. **STAT metadata**: Variable fonts benefit from STAT tables for UI rendering
3. **HVAR deltas**: Horizontal metrics variation affects spacing at different weights
4. **GVAR tuples**: Glyph variation data may not support all interpolation paths
5. **Platform naming**: Windows/macOS/PostScript naming rules differ slightly

All three buyer workflows (Web Optimizer, QA Report, Variable Instances) produce manifests and reports that surface these risks with remediation guidance.

## Capability Snapshot

| Area | What You Can Do Now |
| --- | --- |
| **Load and inspect** | Open TTF, OTF, CFF, Type 1, WOFF, WOFF2, and EOT fonts from paths, bytes, or streams; inspect names, metrics, encodings, glyphs, kerning, and loader source metadata. |
| **Convert** | Convert between desktop and web-facing formats in pure Python. |
| **Clean metadata** | Strip legacy sfnt metadata tables and old Mac `name` records before web or distribution export. |
| **Subset** | Build smaller fonts from text, glyph IDs, codepoints, or web-oriented preset groups including Latin, Cyrillic, Greek, Hebrew, Arabic, Devanagari, and Thai. |
| **Preview** | Generate PNG and SVG previews, APNG animation sweeps, scripted animation frame packages, preview batches, axis sweeps, specimen sheets, and before/after comparison boards with diff and overlay panels. |
| **Variable fonts** | Explore axes and named instances, resolve coordinates, suggest guided preset grids, instantiate static outputs with `HVAR`-aware widths, and auto-name exported instances with multiple naming policies plus optional custom family suffixes such as `Beta` or `Web`. |
| **Web packaging** | Emit WOFF2/WOFF bundles, JSON manifests, CSS, specimen HTML with reusable templates and live variable-axis sliders, navigable family packages with style filters, comparative preview artifacts, reusable family review export packs for docs and marketing handoff, variable-font subset flows that fall back to a clear static export mode when needed, explicit `auto`/`live`/`static` variable export selection, configurable naming strategies, family suffix controls, opt-in static STAT metadata, and coordinate-aware axis-grid web bundles or shared packages for custom sweeps. |
| **QA workflows** | Generate Font QA Reports as JSON/HTML deliverables, run compatibility checks with richer shape and interpolation diagnostics, and create Delta Inspector reports/boards with overlay, glyph-diagram, component-aware composite diagnostics, and richer text-level comparison review cards for variable-font review. |
| **Animation** | Export APNG sweeps and scripted paths with presets, easing controls, baked frame captions, frame-sequence packages, presentation-ready review bundles, and showcase packages that bundle APNG, storyboard, landing HTML, and manifests for downstream sharing. |
| **Automation** | Use the CLI directly or expose the library through the built-in MCP server, including machine-readable variable-font compatibility reports. |

## Variable-Font-First Workflows

The current roadmap is centered on variable fonts. The strongest surface area today is the combination of:

- `font.axes`, `font.named_instances`, and `font.smart_instancer`
- `font.variable_axes` with labels, presets, and presentation metadata for common axes
- additive axis summaries such as `axis.range_summary`, `axis.default_ratio`, and preset-aware `axis.describe_value(...)`
- locale-aware axis and named-instance labels through `axis.name(...)`, `instance.name(...)`, and `var-info --language`
- ordered localization inventory through `axis.localized_labels(...)`, `instance.localized_labels(...)`, and broader common `name`-table locale coverage
- display-ready requested-language profile payloads through `axis.language_profiles(...)`, `instance.language_profiles(...)`, and `font.variable_presentation(...)`
- axis-aware named-instance coordinate labels through `instance.format_coordinates(...)` and richer `var-info` output
- JSON-ready Axes Explorer snapshots through `axis.to_presentation(...)`, `instance.to_presentation(...)`, `font.variable_presentation(...)`, and `var-info --json-output`; see `docs/variable-presentation-schema.md` for the stable integration contract
- preset-aware coordinate selection such as `wght="Bold"` or `wdth="Condensed"`
- guided axis-grid suggestions through `SmartInstancer.suggest_axis_values(...)` and preset-driven grid exports
- `HVAR`-aware static instancing so exported widths can follow horizontal metric variation data
- configurable naming strategies for generated static instances and web handoff packages, including `menu-safe` and `ribbi-safe` policies plus optional custom family suffixes and explicit family/style overrides for safer app/menu coexistence and release-channel labeling
- high-level previews through `FontPreviewBuilder`
- web handoff packaging through `WebFontOptimizer`, `WebFontBuilder`, `SmartInstancer.build_web_bundle(...)`, axis-grid web bundles, and coordinate-aware shared family-package generation
- QA reporting through `FontQaReporter`, `CompatibilityChecker`, and `DeltaInspector`
- deeper compatibility issue notes for segment mix, control points, contour closure, and endpoint movement
- additive interpolation diagnostics for active `gvar` tuple changes between compared instance states

## Variable Font Discovery

```python
from aspose_font import FontLoader

font = FontLoader.open("Roboto-VariableFont_wdth,wght.ttf")
print(font.is_variable)
print([axis.tag for axis in font.axes])
print(len(font.named_instances))
print(font.get_axis("wght").get_preset("Bold").value)
print(font.smart_instancer.resolve({"wght": "Bold", "wdth": "Condensed"}).label)
print(font.smart_instancer.suggest_axis_values("wght", include_bounds=True))
print(font.get_axis("wght").name(("fr-CA", "en")))
print(font.get_axis("wght").range_summary)
print(font.get_named_instance("Condensed Bold").format_coordinates(font.variable_axes, include_tags=True))
print(font.get_axis("wght").localized_labels(("pt-PT", "fr-CA")))
print(font.variable_presentation(preferred_languages=("en",))["axes"][0]["range_summary"])
print(font.variable_presentation(preferred_languages=("fr-CA", "en"))["axes"][0]["language_profiles"][0])
```

```text
is_variable = True
axes = ['wght', 'wdth']
named_instances = 18
bold_preset = 700.0
preset_resolve = Condensed Bold
suggested_wght = [100.0, 200.0, 300.0, 400.0, 500.0, 600.0, 700.0, 800.0, 900.0]
localized_axis_name = Weight
weight_range_summary = 100 -> 900 (default: Regular (400))
condensed_bold_coordinates = ('Width [wdth]=Condensed (75%)', 'Weight [wght]=Bold (700)')
ordered_localizations = (('en', 'Weight'),)
presentation_snapshot_range = 100 -> 900 (default: Regular (400))
language_profile = {'requested_language': 'fr-ca', 'display_label': 'Weight', 'resolved_language': 'en', 'fallback_reason': 'english-fallback', 'has_requested_language_label': False}
```

## Python API Highlights

```python
from aspose_font import FontLoader, FontPreviewBuilder, FontQaReporter, WebFontOptimizer
from aspose_font import FontCleaner
from aspose_font.subsetter import FontSubsetter

font = FontLoader.open("Roboto-VariableFont_wdth,wght.ttf")

subset_result = FontSubsetter.subset_for_web_with_coverage(
    font,
    presets=("latin", "arabic"),
    text="Aspose مرحبا",
)
print(subset_result.font.num_glyphs)
print(subset_result.coverage.covered_count, subset_result.coverage.missing_codepoints)

preview = FontPreviewBuilder.build(font, instance_name="Bold", text="Preview")
preview.write_to("preview.png")

svg_preview = FontPreviewBuilder.build(
    font,
    instance_name="Bold",
    text="Preview",
    output_format="svg",
)
svg_preview.write_to("preview.svg")

instanced = font.smart_instancer.instantiate(
    {"wght": "Bold", "wdth": "Condensed"},
    naming_strategy="ribbi-safe",
    family_suffix="Beta",
)
print(instanced.font_family, instanced.font_style, instanced.ttf_tables.name.get(17))

menu_named = font.instantiate(
    {"wght": 700, "wdth": 75},
    naming_strategy="ribbi-safe",
    legacy_family_name="Acme Sans Menu",
    typographic_family_name="Acme Sans Pro",
    stat_policy="static",
)
print(menu_named.ttf_tables.name.get(1), menu_named.ttf_tables.name.get(16))
print("STAT" in menu_named.ttf_tables._raw)

preview = font.preview_naming_policy(
    {"wght": 700, "wdth": 75},
    naming_strategy="ribbi-safe",
    stat_policy="static",
)
print(preview.stat_diagnostics.generated_stat_axis_value_flags)

cleaned = FontCleaner.clean_for_web(font)
print("meta" in cleaned.ttf_tables._raw)

compat = font.smart_instancer.check_compatibility(
    before_instance_name="Regular",
    after_instance_name="Condensed Bold",
    text="Aspose",
)
print(compat.is_compatible, len(compat.issues))

delta = font.smart_instancer.inspect_deltas(
    instance_name="Bold",
    codepoint=ord("A"),
)
print(delta.total_tuple_count, len(delta.active_tuples))

text_compare = font.smart_instancer.compare_delta_text(
    text="Aspose",
    before_instance_name="Regular",
    after_instance_name="Condensed Bold",
)
print(text_compare.moved_glyph_count, text_compare.comparable_glyph_count)

qa_report = FontQaReporter.build(
    font,
    presets=("latin",),
    text="Aspose QA",
)
qa_report.write_html("font-qa-report.html")

bundle = font.smart_instancer.build_web_bundle(
    instance_name="Bold",
    family_suffix="Beta",
    include_woff=False,
    preview_text="Aspose Variable",
)
bundle.write_to("web-out")

subset_bundle = WebFontOptimizer.build(
    font,
    presets=("latin", "arabic"),
    text="Aspose",
    include_woff=False,
)
print(subset_bundle.manifest["export_mode"])
print(subset_bundle.manifest["subset"]["coverage"]["missing_count"])

live_bundle = WebFontOptimizer.build(
    font,
    include_woff=False,
    variable_mode="live",
)
print(live_bundle.manifest["requested_variable_mode"], live_bundle.manifest["export_mode"])

static_stat_bundle = WebFontOptimizer.build(
    font,
    include_woff=False,
    variable_mode="static",
    instance_name="Bold",
    stat_policy="static",
)
print(static_stat_bundle.manifest["requested_stat_policy"])

grid_package = font.smart_instancer.build_axis_grid_web_family_package(
    "wght",
    [400.0, 700.0],
    family_name="Roboto Grid",
    include_woff=False,
    preview_text="Grid Family",
    naming_strategy="preserve-family",
)
grid_package.write_to("web-grid-family")
print(grid_package.manifest["bundles"][1]["review_label"])
```

The generated grid-family package links back to the demo-site direction: `family.html` shows
coordinate labels like `wdth=100 wght=700`, while `family-manifest.json` exposes the same
`review_label` and `instance_coordinates` fields for automation.

## CLI Highlights

### Web Optimization

```bash
# Web package with CSS/specimen HTML and manifest
aspose-font web-optimize Roboto-VariableFont_wdth,wght.ttf web-output --preset latin --text "Aspose Web" --no-woff

# Variable-mode controls: auto, live, static
aspose-font web-optimize Roboto-VariableFont_wdth,wght.ttf web-live --variable-mode live --no-woff
aspose-font web-optimize Roboto-VariableFont_wdth,wght.ttf web-static --variable-mode static --instance-name Bold --no-woff
```

### QA Evidence

```bash
# Generate QA report package
aspose-font qa-report Roboto-VariableFont_wdth,wght.ttf --preset latin --text "Aspose QA" --package-output qa-package --preview-instance-name Bold

# Compatibility check between instances
aspose-font var-compat Roboto-VariableFont_wdth,wght.ttf --before-instance-name Regular --after-instance-name "Condensed Bold" --text Aspose --json-output compat-report.json

# Delta inspection for glyph-level variation
aspose-font var-delta Roboto-VariableFont_wdth,wght.ttf --instance-name Bold --char A
aspose-font var-delta-text Roboto-VariableFont_wdth,wght.ttf --instance-nameBold --text "Aspose"
```

### Instance Packaging

```bash
# Release-safe instance package
aspose-font var-package Roboto-VariableFont_wdth,wght.ttf --instance-nameBold --naming-strategy ribbi-safe --family-suffix Beta --stat-policy static --preview-text "Review" --output-dir var-package-output

# Batch instance generation
aspose-font var-batch Roboto-VariableFont_wdth,wght.ttf --instance-name Bold --instance-nameCondensed --naming-strategy qa-tagged --output-dir batch-instances

# Static STAT metadata
aspose-font var-package Roboto-VariableFont_wdth,wght.ttf --instance-name Bold --stat-policy static --output-dir stat-package
```

### Preview and Review

```bash
# Quick PNG/SVG preview
aspose-font preview Roboto-VariableFont_wdth,wght.ttf preview.svg --instance-name Bold --format svg

# Variable-font previews and review boards
aspose-font var-instance Roboto-VariableFont_wdth,wght.ttf bold-condensed.ttf --instance wght=Bold --instance wdth=Condensed
aspose-font var-instance Roboto-VariableFont_wdth,wght.ttf condensed-bold.ttf --instance-name condensedbold
aspose-font var-instance Roboto-VariableFont_wdth,wght.ttf qa-bold.ttf --instance-name Bold --naming-strategy qa-tagged
aspose-font var-instance Roboto-VariableFont_wdth,wght.ttf menu-safe-bold.ttf --instance-name Bold --naming-strategy menu-safe
aspose-font var-instance Roboto-VariableFont_wdth,wght.ttf ribbi-safe-bold.ttf --instance-name "Condensed Bold" --naming-strategy ribbi-safe
aspose-font var-instance Roboto-VariableFont_wdth,wght.ttf beta-bold.ttf --instance-name Bold --naming-strategy instance-family --family-suffix Beta
aspose-font var-instance Roboto-VariableFont_wdth,wght.ttf acme-bold.ttf --instance-name "Condensed Bold" --naming-strategy ribbi-safe --legacy-family-name "Acme Sans Menu" --typographic-family-name "Acme Sans Pro"
aspose-font var-instance Roboto-VariableFont_wdth,wght.ttf acme-display.ttf --instance-name "Condensed Bold" --naming-strategy ribbi-safe --legacy-style-name Bold --typographic-style-name "Condensed Display Bold"
aspose-font var-instance Roboto-VariableFont_wdth,wght.ttf bold-stat.ttf --instance-name Bold --stat-policy static
aspose-font var-naming-preview Roboto-VariableFont_wdth,wght.ttf --instance-name Bold --stat-policy static --json-output naming-preview.json
aspose-font var-info Roboto-VariableFont_wdth,wght.ttf
aspose-font var-info Roboto-VariableFont_wdth,wght.ttf --language fr-CA --language en
aspose-font var-info Roboto-VariableFont_wdth,wght.ttf --json-output variable-presentation.json
aspose-font preview-grid-sheet Roboto-VariableFont_wdth,wght.ttf grid-sheet.png --axis wght --use-presets
aspose-font preview-compare Roboto-VariableFont_wdth,wght.ttf compare.png --before-instance-name Regular --after-instance-name "Condensed Bold"
aspose-font preview-waterfall Roboto-VariableFont_wdth,wght.ttf waterfall.png --instance-name Bold --instance-name "Condensed Bold" --include-default
aspose-font preview-matrix Roboto-VariableFont_wdth,wght.ttf matrix.png --all-named
aspose-font preview-family-board Roboto-VariableFont_wdth,wght.ttf family-review-board.png --instance-name Bold --instance-name "Condensed Bold" --include-default
aspose-font preview-family-export Roboto-VariableFont_wdth,wght.ttf family-review-export --instance-name Bold --include-default --family-name "Roboto Review"
```

### Web Packaging

```bash
# Single bundle with web handoff
aspose-font web-optimize Roboto-VariableFont_wdth,wght.ttf web-beta --instance-name Bold --family-suffix Beta --no-woff
aspose-font web-optimize Roboto-VariableFont_wdth,wght.ttf web-static-stat --variable-mode static --instance-name Bold --stat-policy static --no-woff

# Family-level packaging
aspose-font web-family Roboto-VariableFont_wdth,wght.ttf family-out --instance-name Bold --naming-strategy preserve-family --no-woff
aspose-font web-grid Roboto-VariableFont_wdth,wght.ttf grid-web --axis wght --use-presets --no-woff
aspose-font web-grid-family Roboto-VariableFont_wdth,wght.ttf grid-family --axis wght --use-presets --family-name "Roboto Grid" --no-woff
```

### General Inspection and Conversion

```bash
# General inspection and conversion
aspose-font info Roboto.ttf
aspose-font convert Roboto.ttf Roboto.woff2 --to woff2
aspose-font meta-clean Roboto.ttf Roboto-clean.ttf
```

## CLI Usage

For comprehensive documentation of the `web-optimize` command, including full flag reference, example workflows, and performance metrics, see:

**[One-Command Web Font Optimizer Guide](docs/one_command_web_optimizer.md)**

### Quick Reference

```bash
# Basic usage
aspose-font web-optimize input.ttf output-dir --preset latin --text "Sample"

# Variable-mode controls
aspose-font web-optimize input.ttf output-dir --variable-mode live --no-woff
aspose-font web-optimize input.ttf output-dir --variable-mode static --instance-name Bold

# Performance timing
aspose-font web-optimize input.ttf output-dir --performance-report --decision-report
```

## MCP Server

Expose the library to AI clients and local toolchains:

```bash
pip install "aspose-font[mcp]"
python -m aspose_font.mcp
```

The MCP server now covers low-level inspection tools, machine-readable variable-font compatibility
reports through `var_compat`, and high-level web export workflows including single-bundle web
packaging and shared family-package generation.

## Development

```bash
uv run python -m pytest tests/ -q
uv run --with ruff ruff check src tests setup.py
uv run --with build python -m build
```

These verification flows also refresh the generated demo site content.

## License

[MIT](./LICENSE.txt)
