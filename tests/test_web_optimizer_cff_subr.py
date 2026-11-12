"""Integration tests for CFF/CFF2 subroutine telemetry in WebFontOptimizer (FONT-522)."""

from __future__ import annotations

import json
from pathlib import Path

from aspose_font import WebFontOptimizer
from aspose_font.cff.font import CffFont
from aspose_font.ttf.font import TtfFont


def test_web_optimizer_includes_cff_subroutine_telemetry_for_cff_font(
    opensans_cff: CffFont, tmp_path: Path
) -> None:
    """CFF font produces cff_subroutine_telemetry in optimizer manifest."""
    package = WebFontOptimizer.build(
        opensans_cff,
        source_path=None,
        include_woff=False,
    )

    manifest = package.manifest
    assert "cff_subroutine_telemetry" in manifest

    telemetry = manifest["cff_subroutine_telemetry"]
    assert telemetry["font_type"] == "CFF"
    assert telemetry["font_name"] == opensans_cff.font_name
    assert telemetry["num_glyphs"] == opensans_cff.num_glyphs

    global_subrs = telemetry["global_subrs"]
    assert "total_count" in global_subrs
    assert "total_bytes" in global_subrs
    assert "in_use_count" in global_subrs
    assert "unused_count" in global_subrs
    assert "unused_indices" in global_subrs

    local_subrs = telemetry["local_subrs"]
    assert "total_count" in local_subrs
    assert "total_bytes" in local_subrs
    assert "in_use_count" in local_subrs
    assert "unused_count" in local_subrs
    assert "unused_indices" in local_subrs

    assert "max_nesting_depth" in telemetry
    assert "charstrings_analyzed" in telemetry


def test_web_optimizer_telemetry_omitted_for_ttf_font(roboto: TtfFont, tmp_path: Path) -> None:
    """Non-CFF fonts do not include cff_subroutine_telemetry section."""
    package = WebFontOptimizer.build(
        roboto,
        source_path=None,
        include_woff=False,
    )

    manifest = package.manifest
    assert "cff_subroutine_telemetry" not in manifest


def test_web_optimizer_telemetry_data_consistency(opensans_cff: CffFont) -> None:
    """Telemetry data is internally consistent."""
    package = WebFontOptimizer.build(
        opensans_cff,
        source_path=None,
        include_woff=False,
    )

    telemetry = package.manifest["cff_subroutine_telemetry"]
    global_info = telemetry["global_subrs"]

    assert (
        global_info["in_use_count"] + global_info["unused_count"]
        == global_info["total_count"]
    )

    local_info = telemetry["local_subrs"]
    assert (
        local_info["in_use_count"] + local_info["unused_count"]
        == local_info["total_count"]
    )

    assert len(global_info["unused_indices"]) == global_info["unused_count"]
    assert len(local_info["unused_indices"]) == local_info["unused_count"]


def test_web_optimizer_writes_telemetry_to_manifest_file(
    opensans_cff: CffFont, tmp_path: Path
) -> None:
    """Subroutine telemetry is written to optimizer-manifest.json."""
    package = WebFontOptimizer.build(
        opensans_cff,
        source_path=None,
        include_woff=False,
    )

    written = package.write_to(tmp_path)
    manifest_path = tmp_path / "optimizer-manifest.json"
    assert manifest_path in written

    manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert "cff_subroutine_telemetry" in manifest_data
