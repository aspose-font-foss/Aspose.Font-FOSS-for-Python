"""Tests for variable instance release package workflow."""

from __future__ import annotations

import json
from pathlib import Path

from aspose_font import PreviewImage, TtfFont, VariableInstanceBuilder, VariableInstancePackage


def test_variable_instance_package_builds_with_all_instances(roboto: TtfFont, tmp_path: Path) -> None:
    builder = VariableInstanceBuilder(roboto)
    package = builder.build_package()

    assert isinstance(package, VariableInstancePackage)
    assert len(package.instances) >= 2
    assert len(package.fonts) == len(package.instances)
    assert package.preview_text == "Hamburgefons 0123456789"


def test_variable_instance_package_builds_selected_instances(roboto: TtfFont, tmp_path: Path) -> None:
    builder = VariableInstanceBuilder(roboto)
    package = builder.build_package(names=["Regular", "Bold"], include_default=False)

    assert len(package.instances) == 2
    labels = [inst.label for inst in package.instances]
    assert "Regular" in labels
    assert "Bold" in labels


def test_variable_instance_package_writes_all_artifacts(roboto: TtfFont, tmp_path: Path) -> None:
    builder = VariableInstanceBuilder(roboto)
    package = builder.build_package(names=["Regular"], include_default=False)

    package_dir = tmp_path / "package"
    written = package.write_to(
        package_dir,
        font_filename="instance.ttf",
        stat_evidence_filename="stat-evidence.json",
        preview_filename="comparison-board.png",
        manifest_filename="review-manifest.json",
    )

    assert len(written) >= 4

    ttf_files = list(package_dir.glob("*.ttf"))
    assert len(ttf_files) >= 1

    stat_file = package_dir / "stat-evidence.json"
    assert stat_file.exists()
    stat_data = json.loads(stat_file.read_text(encoding="utf-8"))
    assert stat_data["policy"] == "drop"
    assert "instances" in stat_data

    manifest_file = package_dir / "review-manifest.json"
    assert manifest_file.exists()
    manifest_data = json.loads(manifest_file.read_text(encoding="utf-8"))
    assert manifest_data["kind"] == "variable_instance_release_package"
    assert manifest_data["version"] == 1
    assert manifest_data["instance_count"] >= 1

    board_file = package_dir / "comparison-board.png"
    assert board_file.exists()
    assert board_file.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")


def test_variable_instance_package_stat_evidence_structure(roboto: TtfFont, tmp_path: Path) -> None:
    builder = VariableInstanceBuilder(roboto)
    package = builder.build_package(names=["Regular"], include_default=False)

    stat_evidence = package.stat_evidence
    assert stat_evidence["policy"] == "drop"
    assert isinstance(stat_evidence["instances"], list)

    if len(stat_evidence["instances"]) > 0:
        first_instance = stat_evidence["instances"][0]
        assert "label" in first_instance
        assert "coordinates" in first_instance
        assert "source_instance" in first_instance


def test_variable_instance_package_review_manifest_structure(roboto: TtfFont, tmp_path: Path) -> None:
    builder = VariableInstanceBuilder(roboto)
    package = builder.build_package(names=["Regular"], include_default=False)

    manifest = package.review_manifest
    assert manifest["kind"] == "variable_instance_release_package"
    assert manifest["version"] == 1
    assert "artifacts" in manifest
    manifest_artifact_kinds = [a["kind"] for a in manifest["artifacts"]]
    assert "font" in manifest_artifact_kinds
    assert "json" in manifest_artifact_kinds
    assert "image" in manifest_artifact_kinds


def test_variable_instance_compare_axes_filters_output(roboto: TtfFont, tmp_path: Path) -> None:
    builder = VariableInstanceBuilder(roboto)
    package = builder.build_package(
        names=["Regular", "Bold"],
        include_default=False,
        compare_axes=["wght"],
    )

    board_file = tmp_path / "comparison-board.png"
    package.comparison_board.write_to(board_file)
    assert board_file.exists()

    board_data = board_file.read_bytes()
    assert board_data.startswith(b"\x89PNG\r\n\x1a\n")

    assert len(package.instances) == 2
    coordinates = package.instances[0].coordinates
    assert "wght" in coordinates


def test_variable_instance_package_specimen_board(roboto: TtfFont, tmp_path: Path) -> None:
    builder = VariableInstanceBuilder(roboto)
    package = builder.build_package(names=["Regular"], include_default=False)
    package_dir = tmp_path / "package"
    package.write_to(package_dir)
    specimen_path = package_dir / "specimen_board.png"
    assert specimen_path.exists()
    assert specimen_path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")


def test_variable_instance_package_custom_specimen_caption(roboto: TtfFont, tmp_path: Path) -> None:
    builder = VariableInstanceBuilder(roboto)
    custom_caption = "Custom Caption Test"
    package = builder.build_package(names=["Regular"], include_default=False, specimen_caption=custom_caption)
    # Ensure specimen board generated without error
    assert isinstance(package.specimen_board, PreviewImage)
    # Write and verify file exists
    package_dir = tmp_path / "custom_caption_pkg"
    package.write_to(package_dir)
    specimen_path = package_dir / "specimen_board.png"
    assert specimen_path.exists()
    assert specimen_path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
