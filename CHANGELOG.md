# Changelog

All notable public changes to Aspose.Font FOSS for Python are recorded here.

## Unreleased



- Interactive specimen playground HTML template with live slider controls.
- Added self-contained interactive HTML specimen for variable fonts.
- Implement interactive specimen HTML template with live slider controls.
- Delivered interactive specimen HTML template with live slider controls.
- Added STAT consistency validator to FontQaReporter to detect missing or inconsistent STAT tables for improved quality assurance

- Added visual decision report and playground integration test suite
- Added autonomous workflow command (`aspose-font autonomous`) for automatic font analysis and processing
- Added `aspose-font specimen-playground` CLI command for generating self-contained interactive HTML specimens


- [BUG] Pre-Push test failed: test_web_optimizer_performance_benchmark.
- Add STAT consistency validator to FontQaReporter.
- Add interactive specimen playground HTML generator.
- Add interactive specimen HTML template with live slider controls.
- Added parsing of COLRv1 and CPAL tables with variable paint transforms.



- Add stat-fix CLI command to repair or synthesize STAT tables.
- Add STAT consistency validator to FontQaReporter.
- Automatic synthesis of missing STAT tables for variable fonts.
- Add edge case tests for STAT table synthesis
- Added STAT consistency validator to FontQaReporter.





- Parse COLRv1 and CPAL tables with variable paint transforms.
- Generate composite @font-face CSS for chunked variable web fonts.
- Implement Unicode-range chunking for variable WOFF2 exports.
- Add --split-ranges flag to WebFontOptimizer CLI (FONT-402)
- Add Unicode-range chunking for variable WOFF2 exports
- Implement composite @font-face CSS generation for chunked variable web fonts
- Add color glyph rasterization preview support to FontPreviewBuilder (FONT-413)
- Add color font inspection diagnostics to var-info CLI command (FONT-405)
- Added interactive variable font specimen HTML template with live slider controls
- Added standalone specimen-playground CLI command for self-contained web exports (FONT-407)
- Completed Interactive Web Playground Specimen with live slider controls and CLI export
- Added interactive specimen playground HTML generator
- [BUG] Pre-Push test failed: test_preview_naming_policy_reports_source_stat_name_id_coverage.
- Expose supported STAT policies in Auto-Naming previews (FONT-191)
- Added parsing of COLRv1 and CPAL tables with variable paint transforms.
















- [BUG] Pre-Push test failed: test_default_behavior_no_preserve.
- Synthesize missing STAT table from fvar axes and named instances.
- Add CLI --prune-deltas flag to subset command.
- Added `stat-fix` CLI command to repair or synthesize STAT tables.
- Compact HVAR horizontal metrics variation store for subsetted glyphs.
- Added automated synthesis of missing STAT tables from fvar axes and named instances.
- Added '--prune-deltas' flag to the subset CLI for delta pruning and size reporting.
- [BUG] Pre-Push test failed: test_version.
- Implemented gvar tuple delta pruning during variable font subsetting (FONT-394).
- Implemented HVAR horizontal metrics variation store compaction during variable font subsetting.
- Add One-Command Web Font Optimizer README Example.
- Add STAT Table Checks to Font QA Report.
- Variable Font Visual Diff Overlay.
- Added STAT table validation to Font QA Report, providing blocker warnings for missing or mismatched STAT metadata.
- Autonomous development deliverable.
- Add full pipeline report CLI command to generate combined web optimizer, QA, and instance package.
- Add STAT policy decision summary to VariableInstancePackage.
- [BUG] =================================== FAILURES ===================================.
- Add custom specimen board caption option.
- Introduce autonomous workflow command (`aspose-font autonomous`) for one-call font analysis and processing.
- Add Specimen Board Export for Variable Instance Package.
- Add specimen board export to Variable Instance Package (PNG visual proof).
- Added custom caption option for specimen board in variable instance packages.
- [BUG] Pre-Push test failed: test_ci_benchmarks_executes_successfully.
- Add PDF output support for specimen-board CLI.
- Add CI performance regression test for CFF2 variable font subsetting
- Add CI performance regression test for autonomous workflow
- Fixed CI performance regression test for CI benchmarks
- Add Partial Instance Web Export CLI command
- Add One-Command Web Font Optimizer CLI
- Add `--specimen-board` flag to `aspose-font var-package` CLI for PNG specimen board generation.
- Add Web Font Optimizer Decision Report (export mode decision).
- Add WebFontOptimizer README showcase via CLI flag
- Add Variable Font Decision Report CLI Flag.
- Add Decision Report CLI flag to Web Font Optimizer.
- Add autonomous workflow command for automatic font analysis and processing.
- Add STAT policy decision summary JSON file to VariableInstancePackage (stat_policy_summary.json)
- Add Partial Instancing Performance Test
- Fixed CLI performance command failures for one-command-regress and perf-var-package (FONT-272)
- Fixed Web Font Optimizer performance benchmark to stay under 2000 ms (test_web_optimizer_performance_benchmark)
- Add copyable CSS snippet to One-Command Web Font Optimizer CLI (FONT-380)
- Add visual decision report artifact to One-Command Web Font Optimizer
- Fixed CLI `--version` output to correctly report package version.
- Fixed STAT source flag preservation bug (test_default_behavior_no_preserve).




- [BUG] Pre-Push test failed: test_full_pipeline_completes_within_performance_threshold.
- Add specimen board to Variable Instance Package.
- Added build duration tracking for VariableInstancePackage and exposed the `--performance-report` option on the `var-package` CLI command.
- Documented the variable presentation snapshot schema contract and added fixture-backed regression checks for stable public fields.
- Added requested-language profile payloads to Axes Explorer presentation snapshots for axes, axis groups, named instances, and `var-info --json-output`.
- Added opt-in `stat_policy="static"` support for generated static variable-font instances, including Python, CLI, web manifest, and MCP web export surfaces.
- Added reviewer-facing repository hygiene artifacts: security policy, ownership metadata, Docker verification, GitHub Actions CI, and environment variable examples.
- Removed the hardcoded task reporting token fallback so reporting credentials must be supplied through environment configuration.
- Documented the agentic development workflow and reviewer evidence map for repository assessment.
- Added specimen board PNG generation to Variable Instance Package workflow.
- Fixed full pipeline performance regression test to meet CI threshold.

- Add visual diff overlay feature for variable font instance comparison
- Add a README example showcasing the Web Font Optimizer output, including generated fonts, CSS, specimen HTML, manifest, and size summary

## 2026.5.1

- Published the first calendar-versioned GitHub clean mirror release.
- Added generated README visual assets for variable-font and workflow previews.
- Added release automation that creates `YEAR.MONTH.ITERATION` tags and GitHub Releases from GitLab scheduled deployments.
