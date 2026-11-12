"""Unit tests for FeatureVariations table parsing."""

from __future__ import annotations

from pathlib import Path

import pytest

from aspose_font import FontLoader

FIXTURE_PATH = Path(__file__).resolve().parents[1] / "testdata" / "FeatureVarFont.ttf"


def test_parse_feature_variations_table():
    """Test that FeatureVariations table is correctly parsed."""

    if not FIXTURE_PATH.exists():
        pytest.skip("FeatureVarFont.ttf fixture not found")

    loaded = FontLoader.open(FIXTURE_PATH)
    assert loaded.is_variable

    records = loaded.feature_variations
    assert records is not None
    assert len(records) > 0

    for record in records:
        assert hasattr(record, "trigger_axis_index")
        assert hasattr(record, "trigger_axis_min")
        assert hasattr(record, "trigger_axis_max")
        assert hasattr(record, "feature_table_offset")


def test_feature_variations_api_access():
    """Test that feature_variations property is accessible on TtfFont."""
    if not FIXTURE_PATH.exists():
        pytest.skip("FeatureVarFont.ttf fixture not found")

    loaded = FontLoader.open(FIXTURE_PATH)
    font = loaded.font

    records = font.feature_variations
    if records is not None:
        assert len(records) > 0
        assert isinstance(records[0].trigger_axis_index, int)
        assert isinstance(records[0].trigger_axis_min, float)
        assert isinstance(records[0].trigger_axis_max, float)
        assert isinstance(records[0].feature_table_offset, int)
    else:
        pytest.skip("No FeatureVariations table in fixture")


def test_feature_variations_cli_integration(tmp_path):
    """Test --feature-variation flag acceptance and manifest storage."""
    import json
    import subprocess
    import sys

    if not FIXTURE_PATH.exists():
        pytest.skip("FeatureVarFont.ttf fixture not found")

    output_dir = tmp_path / "output"
    output_dir.mkdir()

    result = subprocess.run(
        [sys.executable, "-m", "aspose_font.cli", "web-optimize",
         str(FIXTURE_PATH), str(output_dir),
         "--feature-variation", "FW01"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, f"CLI failed: {result.stderr}"

    manifest_path = output_dir / "optimizer-manifest.json"
    assert manifest_path.exists()

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest.get("selected_feature_variation") == "FW01"


def test_feature_variations_none_if_not_present(roboto):
    """Test that feature_varations returns None for fonts without the table."""
    if roboto.ttf_tables.feature_variations is None:
        records = roboto.feature_variations
        assert records is None
