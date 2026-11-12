# Changelog

All notable public changes to Aspose.Font FOSS for Python are recorded here.

## Unreleased






- Variable Color Font Animation Support.
- CLI palette-info Inspection & CSS @font-palette-values Generation.
- Support for variable color font animation export and inspection via CLI (COLR/CPAL).
- Font Integrity & Checksum Audit in FontQaReporter.
- OpenType DSIG Table Parser & Checksum Verifier.
- WebFontOptimizer CFF/CFF2 Subroutine Compression Telemetry.
- Added CFF/CFF2 subroutine compression telemetry to WebFontOptimizer manifest.







- CLI meta-info Inspection Diagnostics Command.
- Design & Supported Language Integration in FontCapabilityDiscovery.
- Added CLI `meta-info` inspection diagnostics command for OpenType `meta` table.
- Hinting & Rasterization Policy Advisor in FontQaReporter.
- Subset sbix and cbdt Color Bitmap Tables in Font Subsetter.
- OpenType CPAL Color Palette Management & CSS Export.
- CLI palette-info command for CPAL inspection and CSS @font-palette-values generation.
- Added pure-Python Font Subsetting Auditor for validating subsetted variable fonts.
- Integrated Font Subsetting Auditor into WebFontOptimizer manifest (FONT-509).
- Palette injection and dark/light theme CSS export via WebFontOptimizer (FONT-500)
- TextRenderer kern fallback integration.
- CLI cff-subr-info Inspection Diagnostics Command.
- Pure-Python OpenType kern Table Format 0 & Format 2 Parser.
- Integrated legacy kern table fallback kerning into TextRenderer
- Added WOFF2 metadata validation against licensing standards (FONT-494).
- Added CLI `woff2-meta` inspection and packaging command (FONT-493).
- Added metadata injection and licensing embedding in WebFontOptimizer (FONT-492).
- Added CLI `vorg-info` inspection diagnostics command for VORG table (FONT-490).
- Added OpenType Device Metrics (hdmx & vdmx) parser (FONT-526).
- Added CLI `device-metrics` inspection diagnostics command (FONT-513).
- Added vertical text layout and glyph origin offsets in TextRenderer (FONT-489).
- Added pure-Python OpenType VORG Table Parser (FONT-488).
- Added OpenType meta table parser with design and supported language extraction (FONT-517).
- Added design and supported language extraction to FontCapabilityDiscovery.
- Added CLI `gasp-info` inspection diagnostics command (FONT-516).
- Added OpenType kern table parser supporting formats 0 and 2
- OpenType ltag Table Parser
- Added CLI `jstf-info` inspection diagnostics command for JSTF table (FONT-503)
- Added CLI `kern-info` inspection diagnostics command for kern table (FONT-496)
- Added CLI `math-info` inspection diagnostics command for MATH tables (FONT-487).
- Added math glyph variant selection and stretchable delimiter assembly in TextRenderer (FONT-486).
- Added pure-Python OpenType MATH Table Parser (FONT-485).
- Added CLI `ltag-info` inspection diagnostics command (FONT-505).
- Added multilingual font metadata localization in FontQaReporter (FONT-506).
- Added CLI `feature-matrix` command (FONT-484).
- Added Feature Matrix integration in WebFontOptimizer and QA Reports (FONT-483).
- OpenType JSTF Table Parser & Layout (FONT-499).
- TextRenderer justification alignment & Kashida points support.
- Implemented pure-Python OpenType JSTF table parser for justification support.
- Added Font Feature Discovery Matrix core engine (FONT-482).
- Added CLI `base-info` inspection diagnostics (FONT-481).
- Delivered Pure-Python OpenType gasp and LTSH Table Parsers (FONT-514).
- Added Hinting & Rasterization Policy Advisor to FontQaReporter.
- Added CBDT emoji preview extraction and CLI dump command (`cbdt-dump`) (FONT-478).
- Added pure-Python OpenType CBLC & CBDT table parser for color emoji fonts (FONT-476).
- Added support for subsetting sbix and CBDT color bitmap tables.
- Delivered CFF/CFF2 Subroutine Analyzer & Call‑Depth Inspector (FONT-520)
- Added OpenType DSIG table parser and checksum verification.
- Added font integrity and checksum audit to FontQaReporter.
- Added CLI integrity-check Inspection Diagnostics Command.

## 26.11.3 - 2026-11-06

- Maintenance release: mirror synchronization.

## 26.11.2 - 2026-11-06

- Maintenance release: mirror synchronization.

## 26.11.1 - 2026-11-05

- Maintenance release: mirror synchronization.

## 26.10.8 - 2026-10-28

- Added CLI `sbix-dump` command to extract embedded color bitmap emoji PNGs and generate manifest (FONT-475).
- Added color bitmap glyph extraction to `FontPreviewBuilder` for `sbix` emoji preview (FONT-474).
- Added pure-Python OpenType GDEF table parser supporting versions 1.0, 1.2, and 1.3 (FONT-473, FONT-465).
- Added GDEF inspection diagnostics CLI command (`aspose-font gdef-info`) (FONT-472).
- Added color bitmap emoji (`sbix`) table extraction and preview support (FONT-468).
- Integrated GDEF glyph classification and ligature caret positioning in `TextRenderer` (FONT-466).
- Automated end-to-end PyPI release pipeline via GitLab CI with version synchronization.

## 26.10.7 - 2026-10-27

- Adjusted WebFontOptimizer CI performance benchmark thresholds and added best-of-2 sampling to absorb cold-start overhead.

## 26.10.6 - 2026-10-27

- Added GSUB inspection diagnostics CLI command (`aspose-font gsub-info`) (FONT-464, FONT-445).
- Added SVG glyph rasterization preview to PNG via `FontPreviewBuilder.render_svg_glyph_to_png` and CLI `svg-preview` (FONT-462).
- Added CLI `svg-dump` command to extract embedded SVG glyphs from the `SVG ` table into standalone files (FONT-458, FONT-451).
- Added pure-Python OpenType SVG table parser supporting uncompressed and gzip-compressed SVG documents (FONT-453, FONT-449).
- Added GPOS inspection diagnostics CLI command (`aspose-font gpos-info`) (FONT-448).
- Added GPOS pair adjustment and kerning integration in `TextRenderer` (FONT-447).
- Added pure-Python OpenType GPOS table parser with Lookup Type 2 Pair Adjustment (FONT-454, FONT-446).
- Added ligature and feature substitution in `TextRenderer` using GSUB lookups (FONT-444).
- Added pure-Python OpenType GSUB table parser (FONT-443).

## 26.10.5 - 2026-10-22

- Added self-contained interactive HTML specimen playground for variable fonts with live slider sweeps (FONT-406, FONT-442).
- Added `aspose-font specimen-playground` CLI command for generating standalone interactive HTML specimens (FONT-407).
- Added STAT table consistency validator to `FontQaReporter` (FONT-408).
- Added `stat-fix` CLI command to repair or synthesize STAT tables from fvar axes and named instances (FONT-399, FONT-397).
- Implemented Unicode-range chunking for variable WOFF2 web font exports (FONT-400).
- Added composite `@font-face` CSS generator for chunked variable web fonts (FONT-401).
- Added `--split-ranges` flag to `WebFontOptimizer` CLI (FONT-402).
- Added color glyph rasterization preview support to `FontPreviewBuilder` (FONT-413).
- Added color font inspection diagnostics to `var-info` CLI command for COLRv1 and CPAL tables (FONT-405, FONT-404).
- Implemented `gvar` tuple delta pruning and `HVAR` horizontal metrics variation store compaction during subsetting (FONT-394, FONT-395).
- Added `--prune-deltas` flag to `subset` CLI command (FONT-396).

## 2026.5.1 - 2026-05-21

- Published the first calendar-versioned GitHub clean mirror release.
- Added generated README visual assets for variable-font and workflow previews.
- Added release automation that creates `YEAR.MONTH.ITERATION` tags and GitHub Releases from GitLab scheduled deployments.
