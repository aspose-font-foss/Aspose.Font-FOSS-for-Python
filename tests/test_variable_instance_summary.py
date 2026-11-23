# ruff: noqa: I001
"""Test for STAT policy decision summary JSON file."""

from __future__ import annotations

import json
from pathlib import Path

from aspose_font import VariableInstanceBuilder, TtfFont


def test_variable_instance_package_stat_summary(roboto: TtfFont, tmp_path: Path) -> None:
    builder = VariableInstanceBuilder(roboto)
    # Build with static policy to trigger non-empty reason
    package = builder.build_package(stat_policy="static", names=["Regular"], include_default=False)
    package_dir = tmp_path / "summary_pkg"
    package.write_to(package_dir)
    summary_file = package_dir / "stat_policy_summary.json"
    assert summary_file.exists()
    data = json.loads(summary_file.read_text(encoding="utf-8"))
    assert data["stat_policy"] == "static"
    assert isinstance(data["reason"], str) and data["reason"]
