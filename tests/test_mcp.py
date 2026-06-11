"""Tests for MCP server tools (SPEC-018 / ADR-016 / FONT-19)."""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

import pytest

pytest.importorskip("mcp", reason="mcp package not installed")

from aspose_font import EotFont, FontLoader, WoffFont
from aspose_font.mcp import (
    font_convert,
    font_info,
    font_subset,
    glyph_outline,
    text_layout,
    var_compat,
    web_build,
    web_family_package,
)


def test_font_info_returns_metadata(roboto_path: Path) -> None:
    result = font_info(str(roboto_path))
    assert "error" not in result
    assert result["format"] == "TTF"
    assert result["name"] != ""
    assert result["num_glyphs"] > 0


def test_mcp_module_starts() -> None:
    proc = subprocess.Popen(
        [sys.executable, "-m", "aspose_font.mcp"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        time.sleep(0.5)
        rc = proc.poll()
        if rc is not None:
            out, err = proc.communicate(timeout=2)
            # Some runtimes may exit cleanly when stdio is not attached to an MCP client.
            assert rc == 0, f"Process exited early with {rc}: {out}\n{err}"
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=3)


def test_mcp_module_import_error_without_extra() -> None:
    repo_src = Path(__file__).resolve().parents[1] / "src"
    code = (
        "import sys\n"
        f"sys.path.insert(0, {str(repo_src)!r})\n"
        "try:\n"
        "    import aspose_font.mcp  # noqa: F401\n"
        "except ImportError as exc:\n"
        "    raise SystemExit(0 if 'pip install aspose-font[mcp]' in str(exc) else 2)\n"
        "raise SystemExit(1)\n"
    )
    proc = subprocess.run([sys.executable, "-S", "-c", code], capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr + proc.stdout


def test_font_info_variable(roboto_path: Path) -> None:
    result = font_info(str(roboto_path))
    assert "error" not in result
    assert result["is_variable"] is True
    assert isinstance(result["axes"], list)
    assert len(result["axes"]) > 0


def test_font_info_nonexistent() -> None:
    result = font_info("/definitely-not-existing-font-file.ttf")
    assert "error" in result


def test_font_convert_ttf_to_woff(roboto_path: Path, tmp_path: Path) -> None:
    out = tmp_path / "out.woff"
    result = font_convert(str(roboto_path), str(out), "woff")
    assert "error" not in result
    assert result["success"] is True
    assert result["bytes_written"] > 0
    loaded = FontLoader.open(str(out))
    assert isinstance(loaded, WoffFont)


def test_font_convert_bad_format(roboto_path: Path, tmp_path: Path) -> None:
    out = tmp_path / "out.xyz"
    result = font_convert(str(roboto_path), str(out), "xyz")
    assert "error" in result


def test_font_convert_ttf_to_eot(roboto_path: Path, tmp_path: Path) -> None:
    out = tmp_path / "out.eot"
    result = font_convert(str(roboto_path), str(out), "eot")
    assert "error" not in result
    assert result["success"] is True
    loaded = FontLoader.open(str(out))
    assert isinstance(loaded, EotFont)


def test_glyph_outline_returns_commands(roboto_path: Path) -> None:
    result = glyph_outline(str(roboto_path), ord("A"))
    assert "error" not in result
    assert result["glyph_id"] >= 0
    assert isinstance(result["commands"], list)
    assert len(result["commands"]) > 0
    assert "type" in result["commands"][0]


def test_glyph_outline_nonexistent_cp(roboto_path: Path) -> None:
    result = glyph_outline(str(roboto_path), 0x10FFFF)
    assert "error" in result


def test_text_layout_returns_glyphs(roboto_path: Path) -> None:
    result = text_layout(str(roboto_path), "Hi", size=12.0, kern=True)
    assert "error" not in result
    assert "total_width" in result
    assert len(result["glyphs"]) == 2


def test_text_layout_empty(roboto_path: Path) -> None:
    result = text_layout(str(roboto_path), "", size=12.0, kern=True)
    assert "error" not in result
    assert result["glyphs"] == []


def test_font_subset_fewer_glyphs(roboto_path: Path, tmp_path: Path) -> None:
    out = tmp_path / "subset.ttf"
    result = font_subset(str(roboto_path), str(out), "AB")
    assert "error" not in result
    assert result["subset_glyphs"] < result["original_glyphs"]
    assert result["bytes_written"] > 0


def test_web_build_generates_bundle(roboto_path: Path, tmp_path: Path) -> None:
    out_dir = tmp_path / "mcp-web"
    result = web_build(
        str(roboto_path),
        str(out_dir),
        include_woff=False,
        instance_name="Bold",
        preview_text="MCP Preview",
        specimen_template="editorial",
    )
    assert "error" not in result
    assert result["family"] == "Roboto Instance"
    assert result["style"] == "Bold"
    assert result["specimen_template"] == "editorial"
    assert result["export_mode"] == "static-instance"
    assert result["stat_policy_recommendation"] == "review-before-drop"
    assert result["stat_policy_recommendation_reasons"] == [
        "source-stat-dropped-by-default",
        "source-stat-name-ids-uncovered",
    ]
    assert (out_dir / "roboto-instance-bold.woff2").exists()
    assert (out_dir / "web-manifest.json").exists()
    html = (out_dir / "roboto-instance-bold.html").read_text(encoding="utf-8")
    assert "MCP Preview" in html
    assert 'body class="specimen-template-editorial"' in html


def test_mcp_web_build_reports_live_empty_stat_recommendation(
    roboto_path: Path,
    tmp_path: Path,
) -> None:
    out_dir = tmp_path / "mcp-web-live"
    result = web_build(
        str(roboto_path),
        str(out_dir),
        include_woff=False,
        variable_mode="live",
    )

    assert "error" not in result
    assert result["export_mode"] == "variable-live"
    assert result["stat_policy_recommendation"] is None
    assert result["stat_policy_recommendation_reasons"] == []


def test_mcp_web_build_accepts_naming_strategy(roboto_path: Path, tmp_path: Path) -> None:
    out_dir = tmp_path / "mcp-web-preserve-name"
    result = web_build(
        str(roboto_path),
        str(out_dir),
        include_woff=False,
        instance_name="Bold",
        naming_strategy="preserve-family",
    )

    assert "error" not in result
    assert result["family"] == "Roboto"
    assert result["requested_naming_strategy"] == "preserve-family"
    assert (out_dir / "roboto-bold.woff2").exists()


def test_mcp_web_build_accepts_custom_family_suffix(roboto_path: Path, tmp_path: Path) -> None:
    out_dir = tmp_path / "mcp-web-beta"
    result = web_build(
        str(roboto_path),
        str(out_dir),
        include_woff=False,
        instance_name="Bold",
        family_suffix="Beta",
    )
    assert "error" not in result
    assert result["requested_family_suffix"] == "Beta"
    assert result["family"] == "Roboto Beta"
    assert (out_dir / "roboto-beta-bold.woff2").exists()


def test_mcp_web_build_accepts_name_overrides(roboto_path: Path, tmp_path: Path) -> None:
    out_dir = tmp_path / "mcp-web-overrides"
    result = web_build(
        str(roboto_path),
        str(out_dir),
        include_woff=False,
        instance_name="Condensed Bold",
        naming_strategy="ribbi-safe",
        legacy_family_name="Acme Sans Menu",
        typographic_family_name="Acme Sans Pro",
        legacy_style_name="Bold",
        typographic_style_name="Condensed Bold",
    )

    assert "error" not in result
    assert result["family"] == "Acme Sans Menu"
    assert result["style"] == "Bold"
    assert result["requested_legacy_family_name"] == "Acme Sans Menu"
    assert result["requested_typographic_family_name"] == "Acme Sans Pro"
    assert result["requested_legacy_style_name"] == "Bold"
    assert result["requested_typographic_style_name"] == "Condensed Bold"
    assert (out_dir / "acme-sans-menu-bold.woff2").exists()


def test_mcp_web_build_accepts_explicit_static_mode(roboto_path: Path, tmp_path: Path) -> None:
    out_dir = tmp_path / "mcp-web-static"
    result = web_build(
        str(roboto_path),
        str(out_dir),
        include_woff=False,
        variable_mode="static",
    )
    assert "error" not in result
    assert result["export_mode"] == "static-instance"
    assert (out_dir / "roboto-instance-regular.woff2").exists()


def test_web_build_auto_instantiates_variable_subset_request(roboto_path: Path, tmp_path: Path) -> None:
    out_dir = tmp_path / "mcp-web-subset"
    result = web_build(
        str(roboto_path),
        str(out_dir),
        include_woff=False,
        presets=["latin"],
    )
    assert "error" not in result
    assert result["export_mode"] == "static-subset-from-variable-default"
    assert "default coordinates" in (result["export_note"] or "")
    assert (out_dir / "roboto-instance-regular.woff2").exists()
    html = (out_dir / "roboto-instance-regular.html").read_text(encoding="utf-8")
    assert "Export Mode:</strong> Static Subset From Variable Default" in html


def test_mcp_web_build_rejects_live_mode_with_subsetting(roboto_path: Path, tmp_path: Path) -> None:
    result = web_build(
        str(roboto_path),
        str(tmp_path / "mcp-web-live-subset"),
        include_woff=False,
        variable_mode="live",
        presets=["latin"],
    )
    assert "error" in result
    assert "does not support subsetting" in result["error"]


def test_web_family_package_generates_shared_package(roboto_path: Path, tmp_path: Path) -> None:
    out_dir = tmp_path / "mcp-family"
    result = web_family_package(
        str(roboto_path),
        str(out_dir),
        instance_names=["Bold", "Condensed Bold"],
        include_woff=False,
        preview_text="MCP Family",
        specimen_template="lab",
    )
    assert "error" not in result
    assert result["bundle_count"] == 2
    assert result["specimen_template"] == "lab"
    assert result["bundles"][0]["stat_policy_recommendation"] == "review-before-drop"
    assert result["bundles"][0]["stat_policy_recommendation_reasons"] == [
        "source-stat-dropped-by-default",
        "source-stat-name-ids-uncovered",
    ]
    assert (out_dir / "family.css").exists()
    assert (out_dir / "family.html").exists()
    assert (out_dir / "family-manifest.json").exists()
    assert (out_dir / "family-waterfall.png").exists()
    html = (out_dir / "family.html").read_text(encoding="utf-8")
    manifest = (out_dir / "family-manifest.json").read_text(encoding="utf-8")
    assert "MCP Family" in html
    assert 'body class="specimen-template-lab"' in html
    assert "Export Mode:</strong> Static Instance" in html
    assert '"export_mode": "static-instance"' in manifest


def test_mcp_web_family_package_accepts_naming_strategy(roboto_path: Path, tmp_path: Path) -> None:
    out_dir = tmp_path / "mcp-family-qa"
    result = web_family_package(
        str(roboto_path),
        str(out_dir),
        instance_names=["Bold"],
        include_woff=False,
        naming_strategy="qa-tagged",
    )

    assert "error" not in result
    assert result["family_name"] == "Roboto QA"
    assert result["bundles"][0]["requested_naming_strategy"] == "qa-tagged"
    assert (out_dir / "roboto-qa-bold" / "roboto-qa-bold.woff2").exists()


def test_web_family_package_requires_selection(roboto_path: Path, tmp_path: Path) -> None:
    result = web_family_package(str(roboto_path), str(tmp_path / "mcp-family-none"))
    assert "error" in result
    assert "requires instance_names or all_named=True" in result["error"]


def test_var_compat_returns_machine_readable_report(roboto_path: Path) -> None:
    result = var_compat(
        str(roboto_path),
        before_instance_name="Regular",
        after_instance_name="Condensed Bold",
        text="Aspose",
    )

    assert "error" not in result
    assert result["before_label"] == "Regular"
    assert result["after_label"] == "Condensed Bold"
    assert result["is_compatible"] is True
    assert result["issue_count"] == 0
    assert result["interpolation_issue_count"] >= 1
    assert result["before_normalized_coordinates"] == {"wdth": 0.0, "wght": 0.0}
    assert result["after_normalized_coordinates"]["wdth"] < 0.0
    assert result["after_normalized_coordinates"]["wght"] > 0.0
    assert result["interpolation_issues"][0]["reason"] == "variation tuples became active"


def test_var_compat_rejects_non_variable_fonts(opensans_cff_path: Path) -> None:
    result = var_compat(str(opensans_cff_path), text="Aspose")
    assert "error" in result
    assert "requires a variable TTF font" in result["error"]
