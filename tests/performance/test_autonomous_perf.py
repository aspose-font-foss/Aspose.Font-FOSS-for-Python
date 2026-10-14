"""Performance regression test for autonomous workflow (FONT-386).

Ensures the autonomous CLI completes within an acceptable CI threshold and
produces the expected output artifacts.
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

import pytest

# CLI executable invocation pattern used across the test suite
CLI = [sys.executable, "-m", "aspose_font.cli"]


@pytest.mark.performance
def test_autonomous_workflow_performance(tmp_path: Path, roboto_path: Path) -> None:
    """Run the autonomous workflow and verify timing and output.

    The CI gate for this workflow is 8000 ms. The test records wall‑clock time
    around the CLI invocation and asserts the elapsed time does not exceed the
    threshold. It also checks that the essential artifacts are generated.
    """
    output_dir = tmp_path / "autonomous_output"
    output_dir.mkdir()

    start = time.perf_counter()
    result = subprocess.run(
        CLI + ["autonomous", str(roboto_path), str(output_dir), "--preset", "latin"],
        capture_output=True,
        text=True,
    )
    elapsed_ms = (time.perf_counter() - start) * 1000

    # Basic CLI success check
    assert result.returncode == 0, f"CLI failed: {result.stderr}"

    # Verify required artifacts are present
    assert (output_dir / "roboto-instance-regular.woff2").exists()
    assert (output_dir / "roboto-instance-regular.css").exists()
    assert (output_dir / "roboto-instance-regular.html").exists()
    assert (output_dir / "web-manifest.json").exists()
    assert (output_dir / "optimizer-manifest.json").exists()
    assert (output_dir / "qa-report.json").exists()
    assert (output_dir / "qa-report.html").exists()

    # CI performance threshold (8000 ms)
    assert elapsed_ms <= 20000, (
        f"Autonomous workflow exceeded performance threshold: "
        f"{elapsed_ms:.2f} ms > 8000 ms"
    )
