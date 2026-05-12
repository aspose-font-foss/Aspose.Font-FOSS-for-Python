"""Tests for aspose_font.cli (SPEC-012 / FONT-13)."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from aspose_font import (
    ActiveTupleSummary,
    EotFont,
    FontLoader,
    GlyphCompatibilityIssue,
    GlyphInterpolationIssue,
    GlyphOutlineStats,
    TupleScalarDelta,
)
from aspose_font.cli import _format_compat_issue, _format_interpolation_issue
from aspose_font.preview import _decode_png_rgb
from aspose_font.ttf.tables.name import NameRecord

ROBOTO = str(Path(__file__).resolve().parents[1] / "testdata" / "Roboto-VariableFont_wdth,wght.ttf")
CLI = [sys.executable, "-m", "aspose_font.cli"]


def run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        CLI + list(args),
        capture_output=True,
        text=True,
    )


def _build_minimal_sfnt(version: bytes) -> bytes:
    head = bytes(12) + (0x5F0F3CF5).to_bytes(4, "big") + bytes(54 - 16)
    maxp = (0x00010000).to_bytes(4, "big") + (1).to_bytes(2, "big") + bytes(26)
    num_tables = 2
    offset_table = (
        version
        + num_tables.to_bytes(2, "big")
        + (0).to_bytes(2, "big")
        + (0).to_bytes(2, "big")
        + (0).to_bytes(2, "big")
    )
    head_offset = 12 + num_tables * 16
    maxp_offset = head_offset + len(head)
    directory = (
        b"head"
        + (0).to_bytes(4, "big")
        + head_offset.to_bytes(4, "big")
        + len(head).to_bytes(4, "big")
        + b"maxp"
        + (0).to_bytes(4, "big")
        + maxp_offset.to_bytes(4, "big")
        + len(maxp).to_bytes(4, "big")
    )
    return offset_table + directory + head + maxp


def _build_ttc(*sfnts: bytes) -> bytes:
    offsets: list[int] = []
    payload = bytearray()
    current_offset = 12 + len(sfnts) * 4
    for sfnt in sfnts:
        offsets.append(current_offset)
        payload.extend(sfnt)
        current_offset += len(sfnt)
    return (
        b"ttcf"
        + (1).to_bytes(2, "big")
        + (0).to_bytes(2, "big")
        + len(sfnts).to_bytes(4, "big")
        + b"".join(offset.to_bytes(4, "big") for offset in offsets)
        + bytes(payload)
    )


def test_version():
    result = run("--version")
    assert result.returncode == 0
    assert "aspose-font" in result.stdout
    assert "1.0.0" in result.stdout


def test_info_prints_metadata():
    result = run("info", ROBOTO)
    assert result.returncode == 0
    out = result.stdout
    assert "TTF" in out
    assert "Roboto" in out
    assert "Glyphs:" in out
    assert "Units/EM:" in out


def test_info_accepts_collection_index_for_ttc(tmp_path: Path):
    ttc_path = tmp_path / "sample.ttc"
    ttc_path.write_bytes(
        _build_ttc(
            _build_minimal_sfnt(b"\x00\x01\x00\x00"),
            _build_minimal_sfnt(b"OTTO"),
        )
    )

    result = run("info", str(ttc_path), "--collection-index", "1")

    assert result.returncode == 0
    assert "Format:      OTF" in result.stdout
    assert "Collection:  1/1" in result.stdout


def test_info_rejects_collection_index_for_non_ttc():
    result = run("info", ROBOTO, "--collection-index", "1")
    assert result.returncode == 1
    assert "collection_index is only supported for TTC sources" in result.stderr


def test_metrics_accepts_collection_index_for_ttc(tmp_path: Path):
    ttc_path = tmp_path / "sample.ttc"
    ttc_path.write_bytes(
        _build_ttc(
            _build_minimal_sfnt(b"\x00\x01\x00\x00"),
            _build_minimal_sfnt(b"OTTO"),
        )
    )

    result = run("metrics", str(ttc_path), "--collection-index", "1")

    assert result.returncode == 0
    assert "units_per_em:" in result.stdout
    assert "ascender:" in result.stdout


def test_info_nonexistent_exits_1():
    result = run("info", "/nonexistent_font_file.ttf")
    assert result.returncode == 1
    assert result.stderr.strip() != ""


def test_glyphs_limit():
    result = run("glyphs", ROBOTO, "--limit", "5")
    assert result.returncode == 0
    lines = [ln for ln in result.stdout.splitlines() if ln.strip()]
    # Header + 5 data rows
    assert len(lines) == 6


def test_glyphs_default_limit():
    result = run("glyphs", ROBOTO)
    assert result.returncode == 0
    lines = [ln for ln in result.stdout.splitlines() if ln.strip()]
    # Header + up to 50 data rows
    assert len(lines) <= 51
    assert len(lines) >= 2  # at least header + 1 glyph


def test_convert_ttf_to_woff(tmp_path: Path):
    out = str(tmp_path / "out.woff")
    result = run("convert", ROBOTO, out, "--to", "woff")
    assert result.returncode == 0
    assert "Saved:" in result.stdout
    assert Path(out).exists()
    assert Path(out).stat().st_size > 0


def test_convert_bad_format(tmp_path: Path):
    out = str(tmp_path / "out.xyz")
    result = run("convert", ROBOTO, out, "--to", "xyz")
    assert result.returncode == 1
    assert result.stderr.strip() != ""


def test_convert_ttf_to_eot(tmp_path: Path):
    out = str(tmp_path / "out.eot")
    result = run("convert", ROBOTO, out, "--to", "eot")
    assert result.returncode == 0
    assert Path(out).exists()
    loaded = FontLoader.open(out)
    assert isinstance(loaded, EotFont)


def test_metrics_output():
    result = run("metrics", ROBOTO)
    assert result.returncode == 0
    out = result.stdout
    assert "units_per_em:" in out
    assert "ascender:" in out
    assert "descender:" in out


def test_meta_clean_writes_cleaned_font(tmp_path: Path):
    from aspose_font.ttf.tables.name import NameRecord

    source = FontLoader.open(ROBOTO)
    assert source.ttf_tables.name is not None
    source.set_table_bytes("DSIG", b"signature")
    source.set_table_bytes("FFTM", b"fontforge")
    source.set_table_bytes("meta", b"metadata")
    source.ttf_tables.name.records.append(
        NameRecord(
            platform_id=1,
            encoding_id=0,
            language_id=0,
            name_id=1,
            value="Roboto Mac",
        )
    )
    dirty = tmp_path / "dirty.ttf"
    dirty.write_bytes(source.to_bytes())

    out = tmp_path / "cleaned.ttf"
    result = run("meta-clean", str(dirty), str(out))

    assert result.returncode == 0
    assert out.exists()
    assert "Saved:" in result.stdout

    cleaned = FontLoader.open(str(out))
    assert "DSIG" not in cleaned.ttf_tables._raw
    assert "FFTM" not in cleaned.ttf_tables._raw
    assert "meta" not in cleaned.ttf_tables._raw
    assert cleaned.ttf_tables.name is not None
    assert all(record.platform_id != 1 for record in cleaned.ttf_tables.name.records)


def test_preview_writes_png_for_static_variable_font(tmp_path: Path):
    out = tmp_path / "preview.png"
    result = run("preview", ROBOTO, str(out), "--text", "CLI Preview")
    assert result.returncode == 0
    assert out.exists()
    assert out.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    assert "Saved:" in result.stdout


def test_preview_accepts_instance_name(tmp_path: Path):
    out = tmp_path / "bold-preview.png"
    result = run("preview", ROBOTO, str(out), "--instance-name", "Bold")
    assert result.returncode == 0
    assert out.exists()
    assert out.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")


def test_preview_animation_writes_apng(tmp_path: Path):
    out = tmp_path / "animation.png"
    result = run(
        "preview-animation",
        ROBOTO,
        str(out),
        "--axis",
        "wdth",
        "--start",
        "75",
        "--end",
        "100",
        "--frames",
        "4",
        "--preset",
        "draft",
        "--easing",
        "ease-out",
        "--caption-mode",
        "coordinates",
        "--text",
        "Anim",
    )
    assert result.returncode == 0
    assert out.exists()
    data = out.read_bytes()
    assert data.startswith(b"\x89PNG\r\n\x1a\n")
    assert b"acTL" in data
    assert "Saved:" in result.stdout


def test_preview_animation_path_writes_apng(tmp_path: Path):
    out = tmp_path / "animation-path.png"
    result = run(
        "preview-animation-path",
        ROBOTO,
        str(out),
        "--state",
        "Regular",
        "--state",
        "wght=700,wdth=75",
        "--state",
        "Bold",
        "--frames-per-segment",
        "3",
        "--preset",
        "draft",
        "--easing",
        "ease-in-out",
        "--caption-mode",
        "both",
        "--text",
        "Anim Path",
    )
    assert result.returncode == 0
    assert out.exists()
    data = out.read_bytes()
    assert data.startswith(b"\x89PNG\r\n\x1a\n")
    assert b"acTL" in data


def test_preview_animation_path_requires_two_states(tmp_path: Path):
    out = tmp_path / "bad-animation-path.png"
    result = run(
        "preview-animation-path",
        ROBOTO,
        str(out),
        "--state",
        "Bold",
    )
    assert result.returncode == 1
    assert "at least two steps" in result.stderr


def test_preview_animation_path_package_writes_assets(tmp_path: Path):
    out = tmp_path / "animation-package"
    result = run(
        "preview-animation-path-package",
        ROBOTO,
        str(out),
        "--state",
        "Regular",
        "--state",
        "wght=700,wdth=75",
        "--state",
        "Bold",
        "--frames-per-segment",
        "3",
        "--preset",
        "draft",
        "--easing",
        "ease-in-out",
        "--caption-mode",
        "both",
        "--text",
        "Anim Package",
    )
    assert result.returncode == 0
    assert (out / "manifest.json").exists()
    assert (out / "roboto-animation-path-storyboard.png").exists()
    assert (out / "frame-001.png").exists()
    payload = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert payload["frame_count"] >= 3
    assert payload["frames"][0]["filename"] == "frame-001.png"
    assert "Saved:" in result.stdout


def test_preview_animation_path_review_writes_assets(tmp_path: Path):
    out = tmp_path / "animation-review"
    result = run(
        "preview-animation-path-review",
        ROBOTO,
        str(out),
        "--state",
        "Regular",
        "--state",
        "wght=700,wdth=75",
        "--state",
        "Bold",
        "--frames-per-segment",
        "3",
        "--preset",
        "draft",
        "--caption-mode",
        "both",
        "--text",
        "Anim Review",
    )
    assert result.returncode == 0
    assert (out / "roboto-animation-path-storyboard.md").exists()
    assert (out / "roboto-animation-path-storyboard.html").exists()
    assert (out / "roboto-animation-path-storyboard-manifest.json").exists()
    payload = json.loads((out / "roboto-animation-path-storyboard-manifest.json").read_text(encoding="utf-8"))
    assert payload["type"] == "animation-review-package"
    assert "Saved:" in result.stdout


def test_preview_animation_path_showcase_writes_assets(tmp_path: Path):
    out = tmp_path / "animation-showcase"
    result = run(
        "preview-animation-path-showcase",
        ROBOTO,
        str(out),
        "--state",
        "Regular",
        "--state",
        "wght=700,wdth=75",
        "--state",
        "Bold",
        "--frames-per-segment",
        "3",
        "--preset",
        "draft",
        "--caption-mode",
        "both",
        "--text",
        "Anim Showcase",
    )
    assert result.returncode == 0
    assert (out / "roboto-animation-path.png").exists()
    assert (out / "roboto-animation-path-showcase.html").exists()
    assert (out / "roboto-animation-path-showcase-manifest.json").exists()
    assert (out / "roboto-animation-path-storyboard.html").exists()
    payload = json.loads((out / "roboto-animation-path-showcase-manifest.json").read_text(encoding="utf-8"))
    assert payload["type"] == "animation-showcase-package"
    assert payload["animation"]["filename"] == "roboto-animation-path.png"
    assert "Saved:" in result.stdout


def test_preview_writes_svg_when_requested(tmp_path: Path):
    out = tmp_path / "bold-preview.svg"
    result = run("preview", ROBOTO, str(out), "--instance-name", "Bold", "--format", "svg")
    assert result.returncode == 0
    assert out.exists()
    data = out.read_bytes()
    assert data.startswith(b'<?xml version="1.0" encoding="UTF-8"?>')
    assert b"<svg " in data
    assert b"<path d=" in data


def test_preview_accepts_named_instance_plus_override(tmp_path: Path):
    out = tmp_path / "condensed-bold-preview.png"
    result = run(
        "preview",
        ROBOTO,
        str(out),
        "--instance-name",
        "Bold",
        "--instance",
        "wdth=75",
    )
    assert result.returncode == 0
    assert out.exists()
    assert out.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")


def test_preview_accepts_symbolic_axis_presets(tmp_path: Path):
    out = tmp_path / "preset-preview.png"
    result = run(
        "preview",
        ROBOTO,
        str(out),
        "--instance",
        "wght=Bold",
        "--instance",
        "wdth=Condensed",
    )
    assert result.returncode == 0
    assert out.exists()
    assert out.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")


def test_preview_invalid_axis_exits_1(tmp_path: Path):
    out = tmp_path / "bad-preview.png"
    result = run("preview", ROBOTO, str(out), "--instance", "opsz=12")
    assert result.returncode == 1
    assert "Unknown variable axis" in result.stderr


def test_preview_batch_all_named_writes_multiple_pngs(tmp_path: Path):
    out_dir = tmp_path / "preview-batch-all"
    result = run("preview-batch", ROBOTO, str(out_dir), "--all-named", "--text", "Batch CLI Preview")
    assert result.returncode == 0
    files = sorted(path.name for path in out_dir.glob("*.png"))
    source = FontLoader.open(ROBOTO)
    assert len(files) == len(source.variable_instances)
    assert "roboto-instance-bold.png" in files
    assert "Written:" in result.stdout


def test_preview_batch_selected_names_and_default(tmp_path: Path):
    out_dir = tmp_path / "preview-batch-selected"
    result = run(
        "preview-batch",
        ROBOTO,
        str(out_dir),
        "--instance-name",
        "Bold",
        "--include-default",
    )
    assert result.returncode == 0
    files = sorted(path.name for path in out_dir.glob("*.png"))
    assert files == ["roboto-instance-bold.png", "roboto-instance-regular.png"]


def test_preview_batch_can_write_svg_files(tmp_path: Path):
    out_dir = tmp_path / "preview-batch-svg"
    result = run(
        "preview-batch",
        ROBOTO,
        str(out_dir),
        "--instance-name",
        "Bold",
        "--format",
        "svg",
    )
    assert result.returncode == 0
    files = sorted(path.name for path in out_dir.glob("*.svg"))
    assert files == ["roboto-instance-bold.svg"]
    assert (out_dir / "roboto-instance-bold.svg").read_bytes().startswith(
        b'<?xml version="1.0" encoding="UTF-8"?>'
    )


def test_preview_batch_requires_selection(tmp_path: Path):
    out_dir = tmp_path / "preview-batch-none"
    result = run("preview-batch", ROBOTO, str(out_dir))
    assert result.returncode == 1
    assert "requires --all-named or at least one --instance-name" in result.stderr


def test_preview_grid_writes_axis_sweep_pngs(tmp_path: Path):
    out_dir = tmp_path / "preview-grid"
    result = run(
        "preview-grid",
        ROBOTO,
        str(out_dir),
        "--axis",
        "wght",
        "--value",
        "400",
        "--value",
        "700",
        "--axis2",
        "wdth",
        "--value2",
        "75",
        "--value2",
        "100",
    )
    assert result.returncode == 0
    files = sorted(path.name for path in out_dir.glob("*.png"))
    assert len(files) == 4
    assert "roboto-instance-bold.png" in files
    assert any("condensed" in name for name in files)


def test_preview_grid_requires_primary_values(tmp_path: Path):
    out_dir = tmp_path / "preview-grid-none"
    result = run("preview-grid", ROBOTO, str(out_dir), "--axis", "wght")
    assert result.returncode == 1
    assert "requires at least one value" in result.stderr


def test_preview_grid_can_write_svg_files(tmp_path: Path):
    out_dir = tmp_path / "preview-grid-svg"
    result = run(
        "preview-grid",
        ROBOTO,
        str(out_dir),
        "--axis",
        "wght",
        "--value",
        "400",
        "--value",
        "700",
        "--format",
        "svg",
    )
    assert result.returncode == 0
    files = sorted(path.name for path in out_dir.glob("*.svg"))
    assert len(files) == 2
    assert any(name.endswith(".svg") for name in files)


def test_preview_grid_accepts_primary_axis_presets(tmp_path: Path):
    out_dir = tmp_path / "preview-grid-presets"
    result = run(
        "preview-grid",
        ROBOTO,
        str(out_dir),
        "--axis",
        "wght",
        "--use-presets",
    )
    assert result.returncode == 0
    files = sorted(path.name for path in out_dir.glob("*.png"))
    assert len(files) == 9
    assert "roboto-instance-bold.png" in files


def test_preview_grid_sheet_accepts_preset_driven_two_axis_grid(tmp_path: Path):
    out = tmp_path / "grid-sheet-presets.png"
    result = run(
        "preview-grid-sheet",
        ROBOTO,
        str(out),
        "--axis",
        "wght",
        "--use-presets",
        "--axis2",
        "wdth",
        "--use-secondary-presets",
    )
    assert result.returncode == 0
    assert out.exists()
    assert out.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")


def test_preview_grid_sheet_writes_composite_png(tmp_path: Path):
    out = tmp_path / "grid-sheet.png"
    result = run(
        "preview-grid-sheet",
        ROBOTO,
        str(out),
        "--axis",
        "wght",
        "--value",
        "400",
        "--value",
        "700",
        "--axis2",
        "wdth",
        "--value2",
        "75",
        "--value2",
        "100",
    )
    assert result.returncode == 0
    assert out.exists()
    assert out.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    assert "Saved:" in result.stdout


def test_preview_compare_writes_comparison_png(tmp_path: Path):
    out = tmp_path / "compare-sheet.png"
    result = run(
        "preview-compare",
        ROBOTO,
        str(out),
        "--before-instance-name",
        "Regular",
        "--after-instance-name",
        "Condensed Bold",
    )
    assert result.returncode == 0
    assert out.exists()
    assert out.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    assert "Saved:" in result.stdout


def test_preview_compare_includes_diff_panel_colors(tmp_path: Path):
    out = tmp_path / "compare-sheet.png"
    result = run(
        "preview-compare",
        ROBOTO,
        str(out),
        "--before-instance-name",
        "Regular",
        "--after-instance-name",
        "Condensed Bold",
    )
    assert result.returncode == 0
    _width, _height, pixels = _decode_png_rgb(out.read_bytes())
    triplets = {
        tuple(pixels[index:index + 3])
        for index in range(0, len(pixels), 3)
    }
    assert (198, 109, 42) in triplets
    assert (71, 126, 199) in triplets
    assert (126, 94, 156) in triplets


def test_preview_compare_invalid_axis_exits_1(tmp_path: Path):
    out = tmp_path / "bad-compare-sheet.png"
    result = run(
        "preview-compare",
        ROBOTO,
        str(out),
        "--after-instance",
        "opsz=12",
    )
    assert result.returncode == 1
    assert "Unknown variable axis" in result.stderr


def test_preview_waterfall_writes_png(tmp_path: Path):
    out = tmp_path / "waterfall.png"
    result = run(
        "preview-waterfall",
        ROBOTO,
        str(out),
        "--instance-name",
        "Bold",
        "--instance-name",
        "Condensed Bold",
        "--include-default",
        "--text",
        "Waterfall QA",
    )
    assert result.returncode == 0
    assert out.exists()
    assert out.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    assert "Saved:" in result.stdout


def test_preview_matrix_writes_png(tmp_path: Path):
    out = tmp_path / "matrix.png"
    result = run(
        "preview-matrix",
        ROBOTO,
        str(out),
        "--all-named",
        "--text",
        "Matrix QA",
    )
    assert result.returncode == 0
    assert out.exists()
    assert out.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    assert "Saved:" in result.stdout


def test_preview_family_board_writes_png(tmp_path: Path):
    out = tmp_path / "family-review-board.png"
    result = run(
        "preview-family-board",
        ROBOTO,
        str(out),
        "--instance-name",
        "Bold",
        "--instance-name",
        "Condensed Bold",
        "--include-default",
        "--family-name",
        "Roboto Review",
        "--text",
        "Review Board",
    )
    assert result.returncode == 0
    assert out.exists()
    assert out.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    assert "Saved:" in result.stdout


def test_preview_family_export_writes_review_pack(tmp_path: Path):
    out_dir = tmp_path / "family-export"
    result = run(
        "preview-family-export",
        ROBOTO,
        str(out_dir),
        "--instance-name",
        "Bold",
        "--include-default",
        "--family-name",
        "Roboto Release",
        "--text",
        "Release Notes",
    )
    assert result.returncode == 0
    assert (out_dir / "family-review-board.png").exists()
    assert (out_dir / "family-waterfall.png").exists()
    assert (out_dir / "family-matrix.png").exists()
    assert (out_dir / "family-review-board.md").exists()
    assert (out_dir / "family-review-board.html").exists()
    manifest = json.loads((out_dir / "family-review-board-manifest.json").read_text(encoding="utf-8"))
    assert manifest["kind"] == "family_review_export"
    assert manifest["family_name"] == "Roboto Release"
    assert manifest["bundle_count"] == 2
    assert "Family review export: Roboto Release" in result.stdout


def test_preview_waterfall_requires_instance_selection(tmp_path: Path):
    out = tmp_path / "waterfall.png"
    result = run("preview-waterfall", ROBOTO, str(out))
    assert result.returncode == 1
    assert "requires --all-named, --include-default, or at least one --instance-name" in result.stderr


def test_preview_family_board_requires_instance_selection(tmp_path: Path):
    out = tmp_path / "family-review-board.png"
    result = run("preview-family-board", ROBOTO, str(out))
    assert result.returncode == 1
    assert "requires --all-named, --include-default, or at least one --instance-name" in result.stderr


def test_preview_family_export_requires_instance_selection(tmp_path: Path):
    out_dir = tmp_path / "family-export"
    result = run("preview-family-export", ROBOTO, str(out_dir))
    assert result.returncode == 1
    assert "requires --all-named, --include-default, or at least one --instance-name" in result.stderr


def test_var_compat_prints_compatibility_summary():
    result = run(
        "var-compat",
        ROBOTO,
        "--before-instance-name",
        "Regular",
        "--after-instance-name",
        "Condensed Bold",
        "--text",
        "Aspose",
    )
    assert result.returncode == 0
    assert "Before:" in result.stdout
    assert "After:" in result.stdout
    assert "Compatible:" in result.stdout
    assert "yes" in result.stdout
    assert "Interpolation diagnostics:" in result.stdout


def test_var_compat_json_output():
    result = run(
        "var-compat",
        ROBOTO,
        "--before-instance-name",
        "Regular",
        "--after-instance-name",
        "Condensed Bold",
        "--text",
        "Aspose",
        "--json",
    )
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["before_label"] == "Regular"
    assert payload["after_label"] == "Condensed Bold"
    assert payload["is_compatible"] is True
    assert payload["issues"] == []
    assert payload["interpolation_issue_count"] >= 1
    assert payload["interpolation_issues"][0]["reason"] == "variation tuples became active"


def test_var_compat_json_output_file(tmp_path: Path):
    out = tmp_path / "compat.json"
    result = run(
        "var-compat",
        ROBOTO,
        "--before-instance-name",
        "Regular",
        "--after-instance-name",
        "Condensed Bold",
        "--text",
        "Aspose",
        "--json-output",
        str(out),
    )
    assert result.returncode == 0
    assert "Compatible:" in result.stdout
    assert "Saved JSON:" in result.stdout
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["before_label"] == "Regular"
    assert payload["after_label"] == "Condensed Bold"
    assert payload["is_compatible"] is True


def test_var_compat_json_stdout_and_output_file(tmp_path: Path):
    out = tmp_path / "compat.json"
    result = run(
        "var-compat",
        ROBOTO,
        "--before-instance-name",
        "Regular",
        "--after-instance-name",
        "Condensed Bold",
        "--text",
        "Aspose",
        "--json",
        "--json-output",
        str(out),
    )
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["is_compatible"] is True
    assert "Saved JSON:" not in result.stdout
    file_payload = json.loads(out.read_text(encoding="utf-8"))
    assert file_payload == payload


def test_format_compat_issue_includes_geometry_notes() -> None:
    issue = GlyphCompatibilityIssue(
        codepoint=ord("A"),
        character="A",
        reason="point count differs",
        geometry_notes=("line segments 0->1", "quadratic segments 1->0"),
        before_signature=("M", "Q"),
        after_signature=("M", "L"),
        before_stats=GlyphOutlineStats(
            command_count=2,
            point_count=3,
            contour_count=1,
            advance_width=500,
            line_count=0,
            quadratic_count=1,
            cubic_count=0,
            control_point_count=1,
            closed_contour_count=0,
            open_contour_count=1,
            start_point=(0.0, 0.0),
            end_point=(30.0, 40.0),
            bbox=(0.0, 0.0, 30.0, 40.0),
        ),
        after_stats=GlyphOutlineStats(
            command_count=2,
            point_count=2,
            contour_count=1,
            advance_width=500,
            line_count=1,
            quadratic_count=0,
            cubic_count=0,
            control_point_count=0,
            closed_contour_count=0,
            open_contour_count=1,
            start_point=(0.0, 0.0),
            end_point=(30.0, 40.0),
            bbox=(0.0, 0.0, 30.0, 40.0),
        ),
    )

    line = _format_compat_issue(issue)

    assert "U+0041 (A): point count differs" in line
    assert "geometry_notes=line segments 0->1; quadratic segments 1->0" in line


def test_format_interpolation_issue_includes_tuple_transitions() -> None:
    issue = GlyphInterpolationIssue(
        codepoint=ord("A"),
        character="A",
        reason="active variation tuples changed",
        before_active=(
            ActiveTupleSummary(
                tuple_index=1,
                scalar=0.5,
                peak_coords={"wght": 1.0},
                start_coords=None,
                end_coords=None,
            ),
        ),
        after_active=(
            ActiveTupleSummary(
                tuple_index=1,
                scalar=0.75,
                peak_coords={"wght": 1.0},
                start_coords=None,
                end_coords=None,
            ),
            ActiveTupleSummary(
                tuple_index=2,
                scalar=1.0,
                peak_coords={"wdth": -1.0},
                start_coords=None,
                end_coords=None,
            ),
        ),
        entered_tuple_indices=(2,),
        exited_tuple_indices=(),
        retuned_tuples=(
            TupleScalarDelta(tuple_index=1, before_scalar=0.5, after_scalar=0.75),
        ),
    )

    line = _format_interpolation_issue(issue)

    assert "U+0041 (A): active variation tuples changed" in line
    assert "before_active=1:0.5 after_active=1:0.75,2:1" in line
    assert "entered=2 exited=-" in line
    assert "retuned=1:0.5->0.75" in line


def test_var_delta_prints_active_tuple_summary():
    result = run(
        "var-delta",
        ROBOTO,
        "--instance-name",
        "Bold",
        "--char",
        "A",
        "--top-points",
        "2",
    )
    assert result.returncode == 0
    assert "Glyph:" in result.stdout
    assert "Instance:" in result.stdout
    assert "Active tuples:" in result.stdout
    assert "Strongest points:" in result.stdout
    assert "outline=" in result.stdout
    assert "phantom=" in result.stdout
    assert "Tuple #" in result.stdout


def test_var_delta_json_output():
    result = run(
        "var-delta",
        ROBOTO,
        "--instance-name",
        "Condensed Bold",
        "--codepoint",
        "0x41",
        "--top-points",
        "1",
        "--json",
    )
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["codepoint"] == 0x41
    assert payload["instance_label"] == "Condensed Bold"
    assert payload["active_tuple_count"] >= 1
    assert payload["strongest_points"]
    assert "referenced_outline_points" in payload["active_tuples"][0]
    assert "referenced_phantom_points" in payload["active_tuples"][0]
    assert len(payload["active_tuples"][0]["top_points"]) <= 1


def test_var_delta_supports_composite_glyph():
    result = run(
        "var-delta",
        ROBOTO,
        "--instance-name",
        "Bold",
        "--char",
        "Á",
        "--top-points",
        "2",
    )
    assert result.returncode == 0
    assert "Outline support:   composite outline-derived" in result.stdout
    assert "Components:" in result.stdout
    assert "Component motion:" in result.stdout
    assert "GID " in result.stdout
    assert "local=" in result.stdout
    assert "child glyph delta analysis" in result.stdout


def test_var_delta_requires_target():
    result = run(
        "var-delta",
        ROBOTO,
        "--instance-name",
        "Bold",
    )
    assert result.returncode == 1
    assert "requires glyph_id or codepoint" in result.stderr


def test_var_delta_board_writes_png(tmp_path: Path):
    out = tmp_path / "delta-board.png"
    result = run(
        "var-delta-board",
        ROBOTO,
        str(out),
        "--instance-name",
        "Bold",
        "--char",
        "A",
        "--top-points",
        "3",
    )
    assert result.returncode == 0
    assert out.exists()
    assert out.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    _width, _height, pixels = _decode_png_rgb(out.read_bytes())
    triplets = {
        tuple(pixels[index:index + 3])
        for index in range(0, len(pixels), 3)
    }
    assert (198, 109, 42) in triplets
    assert (71, 126, 199) in triplets
    assert (214, 207, 194) in triplets
    assert "Saved:" in result.stdout


def test_var_delta_text_prints_summary():
    result = run(
        "var-delta-text",
        ROBOTO,
        "--instance-name",
        "Bold",
        "--text",
        "ABA",
    )
    assert result.returncode == 0
    assert "Text:" in result.stdout
    assert "Glyphs:" in result.stdout
    assert "Active glyphs:" in result.stdout
    assert "U+0041 'A':" in result.stdout


def test_var_delta_text_json_output():
    result = run(
        "var-delta-text",
        ROBOTO,
        "--instance-name",
        "Condensed Bold",
        "--text",
        "AB",
        "--json",
    )
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["text"] == "AB"
    assert payload["instance_label"] == "Condensed Bold"
    assert payload["glyph_count"] == 2
    assert payload["active_glyph_count"] >= 1


def test_var_delta_text_compare_prints_summary():
    result = run(
        "var-delta-text-compare",
        ROBOTO,
        "--before-instance-name",
        "Regular",
        "--after-instance-name",
        "Condensed Bold",
        "--text",
        "ABA",
    )
    assert result.returncode == 0
    assert "Text:" in result.stdout
    assert "Before:" in result.stdout
    assert "After:" in result.stdout
    assert "Comparable glyphs:" in result.stdout
    assert "Moved glyphs:" in result.stdout
    assert "U+0041 'A':" in result.stdout


def test_var_delta_text_compare_json_output():
    result = run(
        "var-delta-text-compare",
        ROBOTO,
        "--before-instance-name",
        "Regular",
        "--after-instance-name",
        "Condensed Bold",
        "--text",
        "AB",
        "--json",
    )
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["text"] == "AB"
    assert payload["before_label"] == "Regular"
    assert payload["after_label"] == "Condensed Bold"
    assert payload["glyph_count"] == 2
    assert payload["moved_glyph_count"] >= 1


def test_var_delta_text_board_writes_png(tmp_path: Path):
    out = tmp_path / "delta-text-board.png"
    result = run(
        "var-delta-text-board",
        ROBOTO,
        str(out),
        "--instance-name",
        "Bold",
        "--text",
        "ABA",
        "--columns",
        "2",
    )
    assert result.returncode == 0
    assert out.exists()
    assert out.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    _width, _height, pixels = _decode_png_rgb(out.read_bytes())
    triplets = {
        tuple(pixels[index:index + 3])
        for index in range(0, len(pixels), 3)
    }
    assert (198, 109, 42) in triplets
    assert (71, 126, 199) in triplets
    assert "Saved:" in result.stdout


def test_var_delta_text_compare_board_writes_png(tmp_path: Path):
    out = tmp_path / "delta-text-compare-board.png"
    result = run(
        "var-delta-text-compare-board",
        ROBOTO,
        str(out),
        "--before-instance-name",
        "Regular",
        "--after-instance-name",
        "Condensed Bold",
        "--text",
        "ABA",
        "--columns",
        "2",
    )
    assert result.returncode == 0
    assert out.exists()
    assert out.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    _width, _height, pixels = _decode_png_rgb(out.read_bytes())
    triplets = {
        tuple(pixels[index:index + 3])
        for index in range(0, len(pixels), 3)
    }
    assert (198, 109, 42) in triplets
    assert (71, 126, 199) in triplets
    assert (184, 66, 53) in triplets
    assert (214, 207, 194) in triplets
    assert (232, 170, 116) in triplets
    assert (146, 180, 230) in triplets
    assert "Saved:" in result.stdout


def test_var_delta_compare_board_writes_png(tmp_path: Path):
    out = tmp_path / "delta-compare-board.png"
    result = run(
        "var-delta-compare-board",
        ROBOTO,
        str(out),
        "--before-instance-name",
        "Regular",
        "--after-instance-name",
        "Condensed Bold",
        "--char",
        "A",
        "--top-points",
        "3",
    )
    assert result.returncode == 0
    assert out.exists()
    assert out.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    _width, _height, pixels = _decode_png_rgb(out.read_bytes())
    triplets = {
        tuple(pixels[index:index + 3])
        for index in range(0, len(pixels), 3)
    }
    assert (198, 109, 42) in triplets
    assert (71, 126, 199) in triplets
    assert (214, 207, 194) in triplets
    assert "Saved:" in result.stdout


def test_var_delta_compare_prints_summary():
    result = run(
        "var-delta-compare",
        ROBOTO,
        "--before-instance-name",
        "Regular",
        "--after-instance-name",
        "Condensed Bold",
        "--char",
        "A",
        "--top-points",
        "3",
    )
    assert result.returncode == 0
    assert "Glyph:" in result.stdout
    assert "Before:" in result.stdout
    assert "After:" in result.stdout
    assert "Comparable:" in result.stdout
    assert "Moved points:" in result.stdout
    assert "Net movement:" in result.stdout


def test_var_delta_compare_json_output():
    result = run(
        "var-delta-compare",
        ROBOTO,
        "--before-instance-name",
        "Regular",
        "--after-instance-name",
        "Condensed Bold",
        "--char",
        "A",
        "--json",
    )
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["codepoint"] == 0x41
    assert payload["before"]["instance_label"] == "Regular"
    assert payload["after"]["instance_label"] == "Condensed Bold"
    assert payload["is_comparable"] is True
    assert payload["moved_point_count"] >= 1


def test_web_build_writes_bundle(tmp_path: Path):
    out_dir = tmp_path / "web"
    result = run(
        "web-build",
        ROBOTO,
        str(out_dir),
        "--instance",
        "wght=700",
        "--preset",
        "latin",
        "--no-woff",
    )
    assert result.returncode == 0
    assert (out_dir / "roboto-instance-bold.woff2").exists()
    assert (out_dir / "roboto-instance-bold.css").exists()
    assert (out_dir / "roboto-instance-bold.html").exists()
    assert (out_dir / "web-manifest.json").exists()
    assert "Export mode: static-subset-from-instance" in result.stdout
    assert "Written:" in result.stdout


def test_web_build_accepts_instance_name(tmp_path: Path):
    out_dir = tmp_path / "web-by-name"
    result = run(
        "web-build",
        ROBOTO,
        str(out_dir),
        "--instance-name",
        "Bold",
        "--no-woff",
    )
    assert result.returncode == 0
    assert (out_dir / "roboto-instance-bold.woff2").exists()


def test_web_build_accepts_naming_strategy(tmp_path: Path):
    out_dir = tmp_path / "web-preserve-name"
    result = run(
        "web-build",
        ROBOTO,
        str(out_dir),
        "--instance-name",
        "Bold",
        "--naming-strategy",
        "preserve-family",
        "--no-woff",
    )
    assert result.returncode == 0
    assert (out_dir / "roboto-bold.woff2").exists()
    manifest = json.loads((out_dir / "web-manifest.json").read_text(encoding="utf-8"))
    assert manifest["requested_naming_strategy"] == "preserve-family"
    assert manifest["family"] == "Roboto"


def test_web_build_variable_metadata_bundle(tmp_path: Path):
    out_dir = tmp_path / "variable-web"
    result = run("web-build", ROBOTO, str(out_dir), "--no-woff")
    assert result.returncode == 0
    assert (out_dir / "roboto-regular.woff2").exists()
    css = (out_dir / "roboto-regular.css").read_text(encoding="utf-8")
    html = (out_dir / "roboto-regular.html").read_text(encoding="utf-8")
    manifest = json.loads((out_dir / "web-manifest.json").read_text(encoding="utf-8"))
    assert "font-weight: 100 900;" in css
    assert "Variable Axes" in html
    assert manifest["export_mode"] == "variable-live"
    assert "Export mode: variable-live" in result.stdout


def test_web_build_accepts_explicit_live_variable_mode(tmp_path: Path):
    out_dir = tmp_path / "variable-web-live"
    result = run("web-build", ROBOTO, str(out_dir), "--no-woff", "--variable-mode", "live")
    assert result.returncode == 0
    manifest = json.loads((out_dir / "web-manifest.json").read_text(encoding="utf-8"))
    assert manifest["requested_variable_mode"] == "live"
    assert manifest["export_mode"] == "variable-live"
    assert "Export mode: variable-live" in result.stdout


def test_web_build_accepts_explicit_static_mode(tmp_path: Path):
    out_dir = tmp_path / "variable-web-static"
    result = run("web-build", ROBOTO, str(out_dir), "--no-woff", "--variable-mode", "static")
    assert result.returncode == 0
    assert (out_dir / "roboto-instance-regular.woff2").exists()
    manifest = json.loads((out_dir / "web-manifest.json").read_text(encoding="utf-8"))
    assert manifest["requested_variable_mode"] == "static"
    assert manifest["export_mode"] == "static-instance"
    assert "Export mode: static-instance" in result.stdout


def test_web_build_accepts_specimen_template(tmp_path: Path):
    out_dir = tmp_path / "template-web"
    result = run("web-build", ROBOTO, str(out_dir), "--no-woff", "--template", "editorial")
    assert result.returncode == 0
    css = (out_dir / "roboto-regular.css").read_text(encoding="utf-8")
    html = (out_dir / "roboto-regular.html").read_text(encoding="utf-8")
    assert 'body class="specimen-template-editorial"' in html
    assert "<strong>Template:</strong> Editorial" in html
    assert "body.specimen-template-editorial" in css


def test_web_build_invalid_range_exits_1(tmp_path: Path):
    out_dir = tmp_path / "bad-range"
    result = run("web-build", ROBOTO, str(out_dir), "--range", "0x0410-0x03FF")
    assert result.returncode == 1
    assert "Invalid range" in result.stderr


def test_web_build_variable_subsetting_auto_instantiates_default_instance(tmp_path: Path):
    out_dir = tmp_path / "auto-variable-subset"
    result = run("web-build", ROBOTO, str(out_dir), "--preset", "latin", "--no-woff")
    assert result.returncode == 0
    assert (out_dir / "roboto-instance-regular.woff2").exists()
    html = (out_dir / "roboto-instance-regular.html").read_text(encoding="utf-8")
    manifest = json.loads((out_dir / "web-manifest.json").read_text(encoding="utf-8"))
    assert "Export Mode:</strong> Static Subset From Variable Default" in html
    assert "auto-instantiated at the default coordinates" in html
    assert manifest["export_mode"] == "static-subset-from-variable-default"
    assert manifest["auto_instanced_default"] is True
    assert "Export mode: static-subset-from-variable-default" in result.stdout
    assert "Export reason: variable-font subsetting requires static output" in result.stdout
    assert "Coverage:" in result.stdout


def test_web_build_prints_missing_coverage_summary(tmp_path: Path):
    out_dir = tmp_path / "missing-coverage"
    result = run(
        "web-build",
        ROBOTO,
        str(out_dir),
        "--variable-mode",
        "static",
        "--text",
        "A",
        "--codepoint",
        "0x10FFFF",
        "--no-woff",
    )

    assert result.returncode == 0
    manifest = json.loads((out_dir / "web-manifest.json").read_text(encoding="utf-8"))
    assert manifest["subset"]["coverage"]["missing_codepoints"] == [0x10FFFF]
    assert "Coverage: 1/2 requested codepoints covered" in result.stdout
    assert "Missing: U+10FFFF" in result.stdout
    assert "Missing in codepoints codepoints: U+10FFFF" in result.stdout


def test_web_build_live_variable_mode_with_subsetting_exits_1(tmp_path: Path):
    out_dir = tmp_path / "bad-live-subset"
    result = run(
        "web-build",
        ROBOTO,
        str(out_dir),
        "--variable-mode",
        "live",
        "--preset",
        "latin",
    )
    assert result.returncode == 1
    assert "does not support subsetting" in result.stderr


def test_var_info_prints_axes_and_named_instances():
    result = run("var-info", ROBOTO)
    assert result.returncode == 0
    assert "Axes:" in result.stdout
    assert "wght" in result.stdout
    assert "Languages:" in result.stdout
    assert "Range:" in result.stdout
    assert "Default position:" in result.stdout
    assert "Presets:" in result.stdout
    assert "Suggested grid:" in result.stdout
    assert "Bold=700" in result.stdout
    assert "Named Instances:" in result.stdout
    assert "Bold" in result.stdout
    assert "Weight [wght]=Bold (700)" in result.stdout


def test_var_info_accepts_preferred_language_order():
    result = run("var-info", ROBOTO, "--language", "fr-CA", "--language", "en")
    assert result.returncode == 0
    assert "Axes:" in result.stdout
    assert "Languages:" in result.stdout
    assert "Weight" in result.stdout
    assert "Width [wdth]=" in result.stdout


def test_var_info_prints_localized_label_inventory_when_available(tmp_path: Path):
    font = FontLoader.open(ROBOTO)
    name_table = font.ttf_tables.name
    assert name_table is not None
    weight_axis = font.axes[0]
    bold_instance = next(instance for instance in font.named_instances if instance.coordinates["wght"] == 700.0)
    name_table.records.append(NameRecord(3, 1, 0x040C, weight_axis.name_id, "Poids"))
    name_table.records.append(NameRecord(3, 1, 0x0416, weight_axis.name_id, "Peso"))
    name_table.records.append(NameRecord(3, 1, 0x040C, bold_instance.name_id, "Gras"))
    name_table.records.append(NameRecord(3, 1, 0x0416, bold_instance.name_id, "Negrito"))
    localized = tmp_path / "localized.ttf"
    localized.write_bytes(font.to_bytes())

    result = run("var-info", str(localized), "--language", "pt-PT", "--language", "fr-CA")
    assert result.returncode == 0
    assert "Localized labels: pt-br=Peso, fr=Poids, en=Weight" in result.stdout
    assert "Localized labels: pt-br=Negrito, fr=Gras, en=Bold" in result.stdout


def test_var_info_writes_presentation_json(tmp_path: Path):
    output = tmp_path / "var-info.json"

    result = run("var-info", ROBOTO, "--language", "en", "--json-output", str(output))

    assert result.returncode == 0
    assert output.exists()
    assert f"Saved JSON: {output}" in result.stdout
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["font_family"] == "Roboto"
    assert payload["preferred_languages"] == ["en"]
    weight = next(axis for axis in payload["axes"] if axis["tag"] == "wght")
    assert weight["label"] == "Weight"
    assert weight["range_summary"] == "100 -> 900 (default: Regular (400))"
    assert weight["suggested_values"]
    assert any(
        "Weight [wght]=Bold (700)" in instance["tagged_coordinates"]
        for instance in payload["named_instances"]
    )


def test_var_instance_writes_named_instance(tmp_path: Path):
    out = tmp_path / "bold-instance.ttf"
    result = run("var-instance", ROBOTO, str(out), "--instance-name", "Bold")
    assert result.returncode == 0
    assert out.exists()
    loaded = FontLoader.open(str(out))
    assert loaded.font_style == "Bold"


def test_var_instance_named_instance_plus_override(tmp_path: Path):
    out = tmp_path / "condensed-bold-instance.ttf"
    result = run(
        "var-instance",
        ROBOTO,
        str(out),
        "--instance-name",
        "Bold",
        "--instance",
        "wdth=75",
    )
    assert result.returncode == 0
    loaded = FontLoader.open(str(out))
    assert loaded.font_style == "Condensed Bold"


def test_var_instance_accepts_symbolic_axis_presets(tmp_path: Path):
    out = tmp_path / "preset-instance.ttf"
    result = run(
        "var-instance",
        ROBOTO,
        str(out),
        "--instance",
        "wght=Bold",
        "--instance",
        "wdth=Condensed",
    )
    assert result.returncode == 0
    loaded = FontLoader.open(str(out))
    assert loaded.font_style == "Condensed Bold"


def test_var_instance_accepts_unique_partial_instance_name(tmp_path: Path):
    out = tmp_path / "partial-instance.ttf"
    result = run("var-instance", ROBOTO, str(out), "--instance-name", "condensedbold")
    assert result.returncode == 0
    loaded = FontLoader.open(str(out))
    assert loaded.font_style == "Condensed Bold"


def test_var_instance_accepts_preserve_family_naming_strategy(tmp_path: Path):
    out = tmp_path / "preserve-family.ttf"
    result = run(
        "var-instance",
        ROBOTO,
        str(out),
        "--instance-name",
        "Bold",
        "--naming-strategy",
        "preserve-family",
    )
    assert result.returncode == 0
    loaded = FontLoader.open(str(out))
    assert loaded.font_family == "Roboto"
    assert loaded.font_name == "Roboto Bold"


def test_var_batch_accepts_qa_tagged_naming_strategy(tmp_path: Path):
    out_dir = tmp_path / "batch-qa"
    result = run(
        "var-batch",
        ROBOTO,
        str(out_dir),
        "--instance-name",
        "Bold",
        "--naming-strategy",
        "qa-tagged",
    )
    assert result.returncode == 0
    files = sorted(path.name for path in out_dir.glob("*.ttf"))
    assert files == ["roboto-qa-bold.ttf"]


def test_var_instance_accepts_menu_safe_naming_strategy(tmp_path: Path):
    out = tmp_path / "menu-safe.ttf"
    result = run(
        "var-instance",
        ROBOTO,
        str(out),
        "--instance-name",
        "Bold",
        "--naming-strategy",
        "menu-safe",
    )
    assert result.returncode == 0
    loaded = FontLoader.open(str(out))
    assert loaded.font_family == "Roboto Instance"
    assert loaded.ttf_tables.name.get(16) == "Roboto"


def test_var_instance_accepts_ribbi_safe_naming_strategy(tmp_path: Path):
    out = tmp_path / "ribbi-safe.ttf"
    result = run(
        "var-instance",
        ROBOTO,
        str(out),
        "--instance-name",
        "Condensed Bold",
        "--naming-strategy",
        "ribbi-safe",
    )
    assert result.returncode == 0
    loaded = FontLoader.open(str(out))
    assert loaded.font_family == "Roboto Instance"
    assert loaded.font_style == "Bold"
    assert loaded.ttf_tables.name.get(17) == "Condensed Bold"


def test_var_instance_accepts_custom_family_suffix(tmp_path: Path):
    out = tmp_path / "beta-bold.ttf"
    result = run(
        "var-instance",
        ROBOTO,
        str(out),
        "--instance-name",
        "Bold",
        "--family-suffix",
        "Beta",
    )
    assert result.returncode == 0
    loaded = FontLoader.open(str(out))
    assert loaded.font_family == "Roboto Beta"
    assert loaded.font_name == "Roboto Beta Bold"


def test_var_instance_accepts_family_name_overrides(tmp_path: Path):
    out = tmp_path / "family-overrides.ttf"
    result = run(
        "var-instance",
        ROBOTO,
        str(out),
        "--instance-name",
        "Condensed Bold",
        "--naming-strategy",
        "ribbi-safe",
        "--legacy-family-name",
        "Acme Sans Menu",
        "--typographic-family-name",
        "Acme Sans Pro",
    )
    assert result.returncode == 0
    loaded = FontLoader.open(str(out))
    assert loaded.font_family == "Acme Sans Menu"
    assert loaded.font_style == "Bold"
    assert loaded.font_name == "Acme Sans Menu Condensed Bold"
    assert loaded.ttf_tables.name.get(16) == "Acme Sans Pro"
    assert loaded.ttf_tables.name.get(21) == "Acme Sans Pro"
    assert loaded.ttf_tables.name.get(25) == "Acme Sans Pro"


def test_var_instance_accepts_style_name_overrides(tmp_path: Path):
    out = tmp_path / "style-overrides.ttf"
    result = run(
        "var-instance",
        ROBOTO,
        str(out),
        "--instance-name",
        "Condensed Bold",
        "--naming-strategy",
        "ribbi-safe",
        "--legacy-family-name",
        "Acme Sans Menu",
        "--typographic-family-name",
        "Acme Sans Pro",
        "--legacy-style-name",
        "Bold",
        "--typographic-style-name",
        "Condensed Display Bold",
    )
    assert result.returncode == 0
    loaded = FontLoader.open(str(out))
    assert loaded.font_family == "Acme Sans Menu"
    assert loaded.font_style == "Bold"
    assert loaded.font_name == "Acme Sans Menu Condensed Display Bold"
    assert loaded.ttf_tables.name.get(2) == "Bold"
    assert loaded.ttf_tables.name.get(17) == "Condensed Display Bold"
    assert loaded.ttf_tables.name.get(22) == "Condensed Display Bold"
    assert loaded.ttf_tables.name.get(6) == "AcmeSansMenu-CondensedDisplayBold"


def test_var_instance_rejects_blank_family_name_override(tmp_path: Path):
    out = tmp_path / "blank-family.ttf"
    result = run(
        "var-instance",
        ROBOTO,
        str(out),
        "--instance-name",
        "Bold",
        "--legacy-family-name",
        "   ",
    )
    assert result.returncode == 1
    assert "legacy_family_name must not be blank" in result.stderr


def test_var_instance_rejects_blank_style_name_override(tmp_path: Path):
    out = tmp_path / "blank-style.ttf"
    result = run(
        "var-instance",
        ROBOTO,
        str(out),
        "--instance-name",
        "Bold",
        "--typographic-style-name",
        "   ",
    )
    assert result.returncode == 1
    assert "typographic_style_name must not be blank" in result.stderr


def test_var_instance_rejects_ambiguous_partial_instance_name(tmp_path: Path):
    out = tmp_path / "ambiguous-instance.ttf"
    result = run("var-instance", ROBOTO, str(out), "--instance-name", "r")
    assert result.returncode == 1
    assert "Ambiguous named instance" in result.stderr


def test_var_info_non_variable_font_exits_1(tmp_path: Path):
    static_out = tmp_path / "static.ttf"
    create = run("var-instance", ROBOTO, str(static_out), "--instance-name", "Bold")
    assert create.returncode == 0
    result = run("var-info", str(static_out))
    assert result.returncode == 1
    assert "requires a variable TTF font" in result.stderr


def test_var_instance_invalid_axis_exits_1(tmp_path: Path):
    out = tmp_path / "bad-instance.ttf"
    result = run("var-instance", ROBOTO, str(out), "--instance", "opsz=12")
    assert result.returncode == 1
    assert "Unknown variable axis" in result.stderr


def test_var_batch_all_named_writes_multiple_files(tmp_path: Path):
    out_dir = tmp_path / "batch-all"
    result = run("var-batch", ROBOTO, str(out_dir), "--all-named")
    assert result.returncode == 0
    files = sorted(path.name for path in out_dir.glob("*.ttf"))
    source = FontLoader.open(ROBOTO)
    assert len(files) == len(source.variable_instances)
    assert any("bold" in name for name in files)
    assert "Written:" in result.stdout


def test_var_batch_selected_names_and_default(tmp_path: Path):
    out_dir = tmp_path / "batch-selected"
    result = run(
        "var-batch",
        ROBOTO,
        str(out_dir),
        "--instance-name",
        "Bold",
        "--include-default",
    )
    assert result.returncode == 0
    files = sorted(path.name for path in out_dir.glob("*.ttf"))
    assert files == ["roboto-instance-bold.ttf", "roboto-instance.ttf"]


def test_var_batch_requires_selection(tmp_path: Path):
    out_dir = tmp_path / "batch-none"
    result = run("var-batch", ROBOTO, str(out_dir))
    assert result.returncode == 1
    assert "requires --all-named or at least one --instance-name" in result.stderr


def test_web_batch_all_named_writes_multiple_bundle_dirs(tmp_path: Path):
    out_dir = tmp_path / "web-batch-all"
    result = run("web-batch", ROBOTO, str(out_dir), "--all-named", "--no-woff")
    assert result.returncode == 0
    bundle_dirs = [path for path in out_dir.iterdir() if path.is_dir()]
    source = FontLoader.open(ROBOTO)
    assert len(bundle_dirs) == len(source.variable_instances)
    assert any((path / f"{path.name}.woff2").exists() for path in bundle_dirs)


def test_web_batch_selected_names_and_subset(tmp_path: Path):
    out_dir = tmp_path / "web-batch-selected"
    result = run(
        "web-batch",
        ROBOTO,
        str(out_dir),
        "--instance-name",
        "Bold",
        "--preset",
        "latin",
        "--preview-text",
        "Batch Preview",
        "--no-woff",
    )
    assert result.returncode == 0
    bundle_dir = out_dir / "roboto-instance-bold"
    assert (bundle_dir / "roboto-instance-bold.woff2").exists()
    html = (bundle_dir / "roboto-instance-bold.html").read_text(encoding="utf-8")
    assert "Batch Preview" in html
    assert "Bundle: Roboto Instance / Bold | export mode: static-subset-from-instance" in result.stdout


def test_web_batch_accepts_naming_strategy(tmp_path: Path):
    out_dir = tmp_path / "web-batch-qa"
    result = run(
        "web-batch",
        ROBOTO,
        str(out_dir),
        "--instance-name",
        "Bold",
        "--naming-strategy",
        "qa-tagged",
        "--no-woff",
    )
    assert result.returncode == 0
    bundle_dir = out_dir / "roboto-qa-bold"
    assert (bundle_dir / "roboto-qa-bold.woff2").exists()
    manifest = json.loads((bundle_dir / "web-manifest.json").read_text(encoding="utf-8"))
    assert manifest["requested_naming_strategy"] == "qa-tagged"
    assert manifest["family"] == "Roboto QA"


def test_web_build_accepts_menu_safe_naming_strategy(tmp_path: Path):
    out_dir = tmp_path / "web-menu-safe"
    result = run(
        "web-build",
        ROBOTO,
        str(out_dir),
        "--instance-name",
        "Bold",
        "--naming-strategy",
        "menu-safe",
        "--no-woff",
    )
    assert result.returncode == 0
    manifest = json.loads((out_dir / "web-manifest.json").read_text(encoding="utf-8"))
    assert manifest["requested_naming_strategy"] == "menu-safe"
    assert manifest["family"] == "Roboto Instance"


def test_web_build_accepts_ribbi_safe_naming_strategy(tmp_path: Path):
    out_dir = tmp_path / "web-ribbi-safe"
    result = run(
        "web-build",
        ROBOTO,
        str(out_dir),
        "--instance-name",
        "Condensed Bold",
        "--naming-strategy",
        "ribbi-safe",
        "--no-woff",
    )
    assert result.returncode == 0
    manifest = json.loads((out_dir / "web-manifest.json").read_text(encoding="utf-8"))
    assert manifest["requested_naming_strategy"] == "ribbi-safe"
    assert manifest["family"] == "Roboto Instance"
    assert manifest["style"] == "Bold"


def test_web_build_accepts_custom_family_suffix(tmp_path: Path):
    out_dir = tmp_path / "web-beta"
    result = run(
        "web-build",
        ROBOTO,
        str(out_dir),
        "--instance-name",
        "Bold",
        "--family-suffix",
        "Beta",
        "--no-woff",
    )
    assert result.returncode == 0
    manifest = json.loads((out_dir / "web-manifest.json").read_text(encoding="utf-8"))
    assert manifest["requested_family_suffix"] == "Beta"
    assert manifest["family"] == "Roboto Beta"


def test_web_batch_requires_selection(tmp_path: Path):
    out_dir = tmp_path / "web-batch-none"
    result = run("web-batch", ROBOTO, str(out_dir))
    assert result.returncode == 1
    assert "requires --all-named or at least one --instance-name" in result.stderr


def test_web_grid_writes_axis_sweep_bundle_dirs(tmp_path: Path):
    out_dir = tmp_path / "web-grid"
    result = run(
        "web-grid",
        ROBOTO,
        str(out_dir),
        "--axis",
        "wght",
        "--value",
        "400",
        "--value",
        "700",
        "--naming-strategy",
        "preserve-family",
        "--preview-text",
        "Grid Preview",
        "--no-woff",
    )

    assert result.returncode == 0
    regular_dir = out_dir / "roboto-regular"
    bold_dir = out_dir / "roboto-bold"
    assert (regular_dir / "roboto-regular.woff2").exists()
    assert (bold_dir / "roboto-bold.woff2").exists()
    manifest = json.loads((bold_dir / "web-manifest.json").read_text(encoding="utf-8"))
    assert manifest["family"] == "Roboto"
    assert manifest["style"] == "Bold"
    assert manifest["requested_naming_strategy"] == "preserve-family"
    assert manifest["instance_coordinates"]["wght"] == 700.0
    assert "Grid Preview" in (bold_dir / "roboto-bold.html").read_text(encoding="utf-8")
    assert "Bundle: wdth=100 wght=700 | Roboto / Bold | export mode: static-instance" in result.stdout


def test_web_grid_supports_two_axis_sweep(tmp_path: Path):
    out_dir = tmp_path / "web-grid-two-axis"
    result = run(
        "web-grid",
        ROBOTO,
        str(out_dir),
        "--axis",
        "wght",
        "--value",
        "700",
        "--axis2",
        "wdth",
        "--value2",
        "75",
        "--value2",
        "100",
        "--no-woff",
    )

    assert result.returncode == 0
    assert (out_dir / "roboto-instance-condensed-bold" / "roboto-instance-condensed-bold.woff2").exists()
    assert (out_dir / "roboto-instance-bold" / "roboto-instance-bold.woff2").exists()


def test_web_grid_accepts_primary_axis_presets(tmp_path: Path):
    out_dir = tmp_path / "web-grid-presets"
    result = run(
        "web-grid",
        ROBOTO,
        str(out_dir),
        "--axis",
        "wght",
        "--use-presets",
        "--no-woff",
    )
    assert result.returncode == 0
    assert (out_dir / "roboto-instance-bold" / "roboto-instance-bold.woff2").exists()
    assert (out_dir / "roboto-instance-black" / "roboto-instance-black.woff2").exists()


def test_web_grid_family_accepts_preset_driven_two_axis_grid(tmp_path: Path):
    out_dir = tmp_path / "web-grid-family-presets"
    result = run(
        "web-grid-family",
        ROBOTO,
        str(out_dir),
        "--axis",
        "wght",
        "--use-presets",
        "--axis2",
        "wdth",
        "--use-secondary-presets",
        "--family-name",
        "Roboto Guided Grid",
        "--no-woff",
    )
    assert result.returncode == 0
    manifest = json.loads((out_dir / "family-manifest.json").read_text(encoding="utf-8"))
    assert manifest["bundle_count"] == 27
    assert "Grid family package: Roboto Guided Grid" in result.stdout


def test_web_grid_requires_primary_values(tmp_path: Path):
    out_dir = tmp_path / "web-grid-none"
    result = run("web-grid", ROBOTO, str(out_dir), "--axis", "wght")
    assert result.returncode == 1
    assert "requires at least one value" in result.stderr


def test_web_grid_family_writes_shared_package(tmp_path: Path):
    out_dir = tmp_path / "web-grid-family"
    result = run(
        "web-grid-family",
        ROBOTO,
        str(out_dir),
        "--axis",
        "wght",
        "--value",
        "400",
        "--value",
        "700",
        "--family-name",
        "Roboto Grid",
        "--preview-text",
        "Grid Family",
        "--naming-strategy",
        "preserve-family",
        "--no-woff",
    )

    assert result.returncode == 0
    assert (out_dir / "family.css").exists()
    assert (out_dir / "family.html").exists()
    assert (out_dir / "family-manifest.json").exists()
    assert (out_dir / "family-waterfall.png").exists()
    assert (out_dir / "family-matrix.png").exists()
    assert (out_dir / "roboto-bold" / "roboto-bold.woff2").exists()
    html = (out_dir / "family.html").read_text(encoding="utf-8")
    manifest = json.loads((out_dir / "family-manifest.json").read_text(encoding="utf-8"))
    assert "Grid Family" in html
    assert "<strong>Coordinates:</strong> wdth=100 wght=700" in html
    assert "<h3>wdth=100 wght=700</h3>" in html
    assert manifest["family_name"] == "Roboto Grid"
    assert manifest["bundle_count"] == 2
    assert manifest["bundles"][1]["requested_naming_strategy"] == "preserve-family"
    assert manifest["bundles"][1]["review_label"] == "wdth=100 wght=700"
    assert manifest["bundles"][1]["instance_coordinates"] == {"wdth": 100.0, "wght": 700.0}
    assert "Grid family package: Roboto Grid" in result.stdout
    assert "Bundle: Roboto / Bold | export mode: static-instance" in result.stdout


def test_web_grid_family_two_axis_matrix_preview_uses_sheet_layout(tmp_path: Path):
    out_dir = tmp_path / "web-grid-family-two-axis"
    result = run(
        "web-grid-family",
        ROBOTO,
        str(out_dir),
        "--axis",
        "wght",
        "--value",
        "400",
        "--value",
        "700",
        "--axis2",
        "wdth",
        "--value2",
        "75",
        "--value2",
        "100",
        "--family-name",
        "Roboto Grid",
        "--preview-text",
        "Grid Family",
        "--no-woff",
    )

    assert result.returncode == 0
    width, height, _pixels = _decode_png_rgb((out_dir / "family-matrix.png").read_bytes())
    assert width > height


def test_web_grid_family_requires_primary_values(tmp_path: Path):
    out_dir = tmp_path / "web-grid-family-none"
    result = run("web-grid-family", ROBOTO, str(out_dir), "--axis", "wght")
    assert result.returncode == 1
    assert "requires at least one value" in result.stderr


def test_web_family_writes_shared_package(tmp_path: Path):
    out_dir = tmp_path / "web-family"
    result = run(
        "web-family",
        ROBOTO,
        str(out_dir),
        "--instance-name",
        "Bold",
        "--instance-name",
        "Condensed Bold",
        "--preview-text",
        "Family Preview",
        "--no-woff",
    )
    assert result.returncode == 0
    assert (out_dir / "family.css").exists()
    assert (out_dir / "family.html").exists()
    assert (out_dir / "family-manifest.json").exists()
    assert (out_dir / "family-waterfall.png").exists()
    assert (out_dir / "family-matrix.png").exists()
    html = (out_dir / "family.html").read_text(encoding="utf-8")
    css = (out_dir / "family.css").read_text(encoding="utf-8")
    assert "Family Preview" in html
    assert "Condensed Bold" in html
    assert "Waterfall" in html
    assert "Matrix" in html
    assert "family-waterfall.png" in html
    assert "family-matrix.png" in html
    assert css.count("@font-face") == 2
    assert "Family package: Roboto Instance" in result.stdout
    assert "Bundle: Roboto Instance / Bold | export mode: static-instance" in result.stdout


def test_web_family_accepts_specimen_template(tmp_path: Path):
    out_dir = tmp_path / "web-family-template"
    result = run(
        "web-family",
        ROBOTO,
        str(out_dir),
        "--instance-name",
        "Bold",
        "--instance-name",
        "Condensed Bold",
        "--template",
        "lab",
        "--no-woff",
    )
    assert result.returncode == 0
    css = (out_dir / "family.css").read_text(encoding="utf-8")
    html = (out_dir / "family.html").read_text(encoding="utf-8")
    assert 'body class="specimen-template-lab"' in html
    assert "<strong>Template:</strong> Lab" in html
    assert "body.specimen-template-lab" in css


def test_web_family_accepts_naming_strategy(tmp_path: Path):
    out_dir = tmp_path / "web-family-preserve-name"
    result = run(
        "web-family",
        ROBOTO,
        str(out_dir),
        "--instance-name",
        "Bold",
        "--naming-strategy",
        "preserve-family",
        "--no-woff",
    )
    assert result.returncode == 0
    manifest = json.loads((out_dir / "family-manifest.json").read_text(encoding="utf-8"))
    assert manifest["family_name"] == "Roboto"
    assert manifest["bundles"][0]["requested_naming_strategy"] == "preserve-family"
    assert "Family package: Roboto" in result.stdout


def test_web_family_prints_coverage_summary(tmp_path: Path):
    out_dir = tmp_path / "web-family-coverage"
    result = run(
        "web-family",
        ROBOTO,
        str(out_dir),
        "--instance-name",
        "Bold",
        "--text",
        "A",
        "--codepoint",
        "0x10FFFF",
        "--no-woff",
    )

    assert result.returncode == 0
    manifest = json.loads((out_dir / "family-manifest.json").read_text(encoding="utf-8"))
    assert manifest["bundles"][0]["coverage"]["missing_codepoints_sample"] == [0x10FFFF]
    assert "Coverage: 1/2 requested codepoints covered" in result.stdout
    assert "Export reason: subsetting requested after static instance selection" in result.stdout


def test_web_family_requires_selection(tmp_path: Path):
    out_dir = tmp_path / "web-family-none"
    result = run("web-family", ROBOTO, str(out_dir))
    assert result.returncode == 1
    assert "requires --all-named or at least one --instance-name" in result.stderr


def test_no_command_exits_0():
    result = run()
    assert result.returncode == 0
    assert "usage" in result.stdout.lower() or "aspose-font" in result.stdout.lower()
