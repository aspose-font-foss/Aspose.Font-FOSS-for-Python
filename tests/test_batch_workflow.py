"""Tests for batch workflow orchestrator (FONT-220)."""
from __future__ import annotations

from pathlib import Path

TESTDATA = Path(__file__).resolve().parents[1] / "testdata"


def test_batch_workflow_processes_multiple_fonts(tmp_path: Path) -> None:
    """Test successful processing of two valid fonts."""
    import shutil

    from aspose_font.batch_workflow import process_directory

    input_dir = tmp_path / "input"
    input_dir.mkdir()

    copy1 = input_dir / "Roboto-VariableFont_wdth,wght.ttf"
    copy2 = input_dir / "OpenSans-Regular.cff"
    shutil.copy(TESTDATA / "Roboto-VariableFont_wdth,wght.ttf", copy1)
    shutil.copy(TESTDATA / "OpenSans-Regular.cff", copy2)

    output_dir = tmp_path / "output"

    summary = process_directory(
        input_directory=input_dir,
        output_directory=output_dir,
    )

    assert summary.total_count == 2
    assert summary.success_count == 2
    assert summary.failure_count == 0

    roboto_dir = output_dir / "Roboto-VariableFont_wdth,wght"
    assert (roboto_dir / "optimizer").exists()
    assert (roboto_dir / "qa-report").exists()
    assert (roboto_dir / "instances").exists()

    open_sans_dir = output_dir / "OpenSans-Regular"
    assert (open_sans_dir / "optimizer").exists()
    assert (open_sans_dir / "qa-report").exists()
    assert not (open_sans_dir / "instances").exists()

    cff_result = next(r for r in summary.results if "OpenSans" in r.source_filename)
    assert cff_result.instance_package_dir is None

    summary_json = output_dir / "batch-summary.json"
    assert summary_json.exists()

    summary_data = summary_json.read_text(encoding="utf-8")
    assert '"kind": "batch_summary"' in summary_data
    assert '"total_count": 2' in summary_data
    assert '"success_count": 2' in summary_data


def test_batch_workflow_handles_unsupported_file_gracefully(tmp_path: Path) -> None:
    """Test that unsupported files don't stop the batch."""
    import shutil

    from aspose_font.batch_workflow import process_directory

    input_dir = tmp_path / "input"
    input_dir.mkdir()

    copy = input_dir / "Roboto-VariableFont_wdth,wght.ttf"
    shutil.copy(TESTDATA / "Roboto-VariableFont_wdth,wght.ttf", copy)

    unsupported = input_dir / "readme.txt"
    unsupported.write_text("This is not a font file")

    output_dir = tmp_path / "output"

    summary = process_directory(
        input_directory=input_dir,
        output_directory=output_dir,
    )

    assert summary.total_count == 1
    assert summary.success_count == 1
    assert summary.failure_count == 0

    result = summary.results[0]
    assert result.success is True


def test_batch_workflow_creates_instance_package_for_variable_font(tmp_path: Path) -> None:
    """Test that variable fonts generate instance packages."""
    import shutil

    from aspose_font.batch_workflow import process_directory

    input_dir = tmp_path / "input"
    input_dir.mkdir()

    copy = input_dir / "Roboto-VariableFont_wdth,wght.ttf"
    shutil.copy(TESTDATA / "Roboto-VariableFont_wdth,wght.ttf", copy)

    output_dir = tmp_path / "output"

    summary = process_directory(
        input_directory=input_dir,
        output_directory=output_dir,
    )

    result = summary.results[0]
    assert result.success is True
    assert result.instance_package_dir is not None
    assert result.instance_package_dir.exists()

    instances_dir = result.instance_package_dir
    assert (instances_dir / "stat-evidence.json").exists()
    assert (instances_dir / "review-manifest.json").exists()
    assert (instances_dir / "comparison-board.png").exists()

    ttf_files = list(instances_dir.glob("*.ttf"))
    assert len(ttf_files) >= 2
