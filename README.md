[![Aspose.Font FOSS for Python](https://raw.githubusercontent.com/aspose-font-foss/Aspose.Font-FOSS-for-Python/main/docs/images/banner.png)](https://github.com/aspose-font-foss/Aspose.Font-FOSS-for-Python)

# Aspose.Font FOSS for Python

[![PyPI version](https://img.shields.io/pypi/v/aspose-font-foss.svg)](https://pypi.org/project/aspose-font-foss/)
[![Python License](https://img.shields.io/pypi/l/aspose-font-foss.svg)](https://github.com/aspose-font-foss/Aspose.Font-FOSS-for-Python/blob/main/LICENSE.txt)
[![Contributors](https://img.shields.io/github/contributors/aspose-font-foss/Aspose.Font-FOSS-for-Python.svg)](https://github.com/aspose-font-foss/Aspose.Font-FOSS-for-Python/graphs/contributors)

**Aspose.Font FOSS for Python** is a free, open-source, pure-Python library designed for inspecting, converting, subsetting, optimizing, and instancing fonts without requiring native runtime dependencies or external toolchains.

---

## Features

* **Multi-Format Support:** Load, inspect, and convert TrueType (TTF), OpenType (OTF), CFF/CFF2, Type 1 (PFA/PFB), WOFF, WOFF2, and EOT fonts.
* **Subsetting & Compression:** Build lean web fonts from specific text, glyph IDs, unicode codepoints, or built-in script presets (Latin, Cyrillic, Greek, Hebrew, Arabic, Devanagari, Thai) with integrated WOFF2 Brotli compression.
* **Web Font Optimization:** Generate complete browser-ready packages containing optimized WOFF2/WOFF files, copyable CSS `@font-face` rules with `unicode-range`, interactive specimen HTML with axis sliders, and machine-readable JSON manifests.
* **Variable Font Instancing:** Explore axes, named instances, and coordinate spaces; resolve presets; and produce static instance fonts with horizontal metric (`HVAR`) awareness, variation delta (`gvar`) preservation, and release-safe naming strategies (`ribbi-safe`, `menu-safe`).
* **Quality Assurance & Diagnostics:** Inspect metrics, validate variable font interpolation compatibility, check contour closure and segment mixing, calculate glyph deltas, and export structured QA reports in JSON, HTML, and visual PNG formats.
* **Visual Proofing & Specimen Generation:** Render PNG and SVG previews, axis-grid sheets, before/after comparison boards with diff/overlay modes, waterfall specimens, and animated APNG sweeps.
* **Metadata Sanitization:** Strip legacy sfnt metadata tables and outdated Mac `name` records prior to public web or commercial distribution.
* **Automation & MCP:** Full-featured command-line interface (`aspose-font`) and built-in Model Context Protocol (MCP) server for seamless integration with AI agents and automated CI/CD workflows.
* **Pure Python:** 100% pure Python with zero native compilation requirements; fully compatible across Windows, Linux, and macOS.

---

## Scope

* **Intended Use Cases:** Web font packaging, variable font release pipelines, automated QA reporting, font metadata inspection, subsetting in serverless/containerized environments, and typography toolchain automation.
* **Supported Formats:** TrueType (`.ttf`), OpenType (`.otf`), Web Open Font Format (`.woff`, `.woff2`), Compact Font Format (`.cff`, `.cff2`), PostScript Type 1 (`.pfa`, `.pfb`), and Embedded OpenType (`.eot`).
* **Pure-Python Architecture:** Runs anywhere Python 3.10+ is supported without requiring FreeType, HarfBuzz, FontForge, or other native C/C++ libraries.
* **Commercial Complement:** For advanced proprietary font rasterization and enterprise-scale document layout engines, explore the commercial Aspose.Font product family.

---

## Installation

Install the package via PyPI:

```bash
pip install aspose-font-foss
```

* **Requirements:** Python 3.10 or later.
* **Core Dependencies:** Standard library foundation with bundled Brotli compressor and Pillow for raster previews.

### MCP Server (Optional)
To enable the Model Context Protocol (MCP) server for integration with AI assistants (such as Claude Desktop or Cursor):

```bash
pip install "aspose-font-foss[mcp]"
```

---

## Quick Start

### 1. Load a Font & Inspect Metrics
```python
from aspose_font import FontLoader

font = FontLoader.open("Roboto.ttf")
print(f"Family:   {font.font_family}")
print(f"Style:    {font.font_style}")
print(f"Glyphs:   {font.num_glyphs}")
print(f"Units/EM: {font.metrics.units_per_em}")
```

### 2. Convert Font Formats
```python
from aspose_font import FontLoader, FontConverter

font = FontLoader.open("Roboto.ttf")
FontConverter.convert(font, "Roboto.woff2", output_format="woff2")
```

### 3. Subset Font for Web
```python
from aspose_font import FontLoader
from aspose_font.subsetter import FontSubsetter

font = FontLoader.open("Roboto.ttf")
result = FontSubsetter.subset_for_web_with_coverage(
    font,
    presets=("latin",),
    text="Aspose Font FOSS",
)
result.font.save("Roboto-subset.woff2", format="woff2")
print(f"Retained {result.font.num_glyphs} glyphs (coverage: {result.coverage.covered_count})")
```

### 4. Variable Font Instancing
```python
from aspose_font import FontLoader

font = FontLoader.open("Roboto-VariableFont_wdth,wght.ttf")
if font.is_variable:
    print(f"Variable axes: {[axis.tag for axis in font.axes]}")
    # Create a static instance font
    static_font = font.smart_instancer.instantiate(
        {"wght": "Bold", "wdth": "Condensed"},
        naming_strategy="ribbi-safe",
        family_suffix="Beta",
    )
    static_font.save("Roboto-CondensedBold.ttf")
```

---

## Production Workflows

### 1. Web Font Optimization

Generate a production-ready web font bundle including WOFF2/WOFF files, CSS `@font-face` declarations, interactive specimen HTML, and size/coverage manifests.

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

**Generated Package Structure:**
```
demo/web_opt_demo/
├── roboto-variablefont-wdth,wght.woff2          (WOFF2 font, ~28KB)
├── roboto-variablefont-wdth,wght.woff           (WOFF fallback, ~32KB)
├── fonts.css                                    (CSS @font-face with unicode-range)
├── specimen.html                                (Interactive specimen with axis controls)
├── web-manifest.json                            (Bundle manifest)
└── optimizer-manifest.json                      (Optimizer package manifest)
```

---

### 2. Font QA Reporting

Validate font integrity, check variable font compatibility across instances, identify glyph outline issues, and generate visual inspection reports.

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
print(f"JSON Report: {package.json_path}")
print(f"HTML Report: {package.html_path}")
print(f"Visual Proof: {package.preview_path}")
```

**CLI:**
```bash
aspose-font qa-report Roboto-VariableFont_wdth,wght.ttf --preset latin --text "QA" --package-output qa-package --preview-instance-name Bold
```

**Generated Package Structure:**
```
qa-package/
├── qa-report.json                               (Diagnostic data with severity scoring)
├── qa-report.html                               (Self-contained HTML visual report)
└── preview.png                                  (Rendered proof with named instances)
```

---

### 3. Release-Safe Variable Instance Packages

Extract named static instances from variable fonts using menu-safe and RIBBI-compliant naming conventions for operating system and application compatibility.

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

**Generated Package Structure:**
```
var-package-output/
├── Roboto-Beta-Bold.ttf                         (Instanced static font)
├── stat-evidence.json                           (STAT policy decisions & diagnostics)
├── review-manifest.json                         (Release-ready review manifest)
└── comparison-board.png                         (Side-by-side visual comparison board)
```

---

## Command-Line Interface (CLI)

The package provides the `aspose-font` command-line utility for scriptable font automation:

```bash
# Web font optimization (WOFF2 + CSS + specimen + manifests)
aspose-font web-optimize input.ttf ./web-dist --preset latin --text "Sample"

# QA evidence report generation
aspose-font qa-report input.ttf --package-output ./qa-dist --preview-instance-name Bold

# Static instance extraction with safe naming
aspose-font var-package input.ttf --instance-name Bold --naming-strategy ribbi-safe --output-dir ./instances

# Compatibility check between variable instances
aspose-font var-compat input.ttf --before-instance-name Regular --after-instance-name "Condensed Bold" --text "Test"

# Delta inspection for glyph-level variations
aspose-font var-delta input.ttf --instance-name Bold --char A

# Font format conversion
aspose-font convert input.ttf output.woff2 --to woff2

# Clean legacy metadata tables
aspose-font meta-clean input.ttf output-clean.ttf

# Visual rendering preview
aspose-font preview input.ttf preview.png --instance-name Bold --text "Preview Text"
```

---

## Model Context Protocol (MCP) Server

Connect Aspose.Font directly to AI agents using the standard MCP protocol:

```bash
# Start MCP server
python -m aspose_font.mcp
```

**Claude Desktop Configuration (`claude_desktop_config.json`):**
```json
{
  "mcpServers": {
    "aspose-font": {
      "command": "python",
      "args": ["-m", "aspose_font.mcp"]
    }
  }
}
```

The MCP server exposes tools for font metadata inspection, format conversion, subsetting, variable-font compatibility checks, and automated web package generation.

---

## Development & Testing

Run tests and code linting locally:

```bash
# Run test suite
pytest tests/

# Run linter
ruff check src/ tests/

# Build package distributions
python package.py build
```

---

## License

This project is licensed under the [MIT License](https://github.com/aspose-font-foss/Aspose.Font-FOSS-for-Python/blob/main/LICENSE.txt).
