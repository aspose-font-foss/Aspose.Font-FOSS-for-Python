"""Tests for CLI --prune-deltas flag (FONT-396)."""
import json
import subprocess
import sys
from pathlib import Path

ROBOTO = str(Path(__file__).resolve().parents[1] / "testdata" / "Roboto-VariableFont_wdth,wght.ttf")
CLI = [sys.executable, "-m", "aspose_font.cli"]


def run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(CLI + list(args), capture_output=True, text=True)


def test_prune_deltas_flag_parsing(tmp_path: Path):
    """Verify --prune-deltas and --no-prune-deltas flags are accepted."""
    output = tmp_path / "subset.ttf"
    result1 = run("subset", ROBOTO, str(output), "--text", "ABC", "--prune-deltas")
    assert result1.returncode == 0

    output2 = tmp_path / "subset2.ttf"
    result2 = run("subset", ROBOTO, str(output2), "--text", "ABC", "--no-prune-deltas")
    assert result2.returncode == 0


def test_prune_deltas_default_enabled(tmp_path: Path):
    """Verify pruning is enabled by default."""
    output = tmp_path / "subset.ttf"
    result = run("subset", ROBOTO, str(output), "--text", "ABC")
    assert result.returncode == 0
    assert "Delta pruning: enabled" in result.stdout


def test_prune_deltas_output_sizes(tmp_path: Path):
    """Verify output includes before/after sizes for gvar and HVAR."""
    output = tmp_path / "subset.ttf"
    result = run("subset", ROBOTO, str(output), "--text", "ABC", "--prune-deltas")
    assert result.returncode == 0
    assert "gvar:" in result.stdout
    assert "HVAR:" in result.stdout
    assert "bytes saved" in result.stdout.lower()


def test_prune_deltas_manifest_fields(tmp_path: Path):
    """Verify manifest contains pruned_tables and delta_bytes_saved."""
    output = tmp_path / "subset.ttf"
    result = run("subset", ROBOTO, str(output), "--text", "ABC", "--prune-deltas")
    assert result.returncode == 0

    manifest_path = output.with_suffix(output.suffix + ".manifest.json")
    assert manifest_path.exists()
    manifest = json.loads(manifest_path.read_text())
    assert "pruned_tables" in manifest
    assert "delta_bytes_saved" in manifest
    assert isinstance(manifest["pruned_tables"], dict)
    assert isinstance(manifest["delta_bytes_saved"], int)


def test_no_prune_deltas_disables_pruning(tmp_path: Path):
    """Verify --no-prune-deltas disables pruning and output reflects this."""
    output = tmp_path / "subset.ttf"
    result = run("subset", ROBOTO, str(output), "--text", "ABC", "--no-prune-deltas")
    assert result.returncode == 0
    assert "Delta pruning: disabled" in result.stdout
