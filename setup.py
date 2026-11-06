from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from setuptools import setup
from setuptools.command.build_py import build_py as _build_py
from setuptools.command.sdist import sdist as _sdist


def _run_site_generator() -> None:
    root = Path(__file__).resolve().parent
    script = root / "scripts" / "generate_website.py"
    roadmap = root / "backlog" / "docs" / "ROADMAP.md"
    if not script.exists() or not roadmap.exists():
        return
    env = os.environ.copy()
    status_path = root / "website" / "generated" / "status.json"
    if status_path.exists() and "ASPOSE_FONT_WEBSITE_GENERATED_AT" not in env:
        status = json.loads(status_path.read_text(encoding="utf-8"))
        generated_at = status.get("generated_at")
        if isinstance(generated_at, str):
            env["ASPOSE_FONT_WEBSITE_GENERATED_AT"] = generated_at
    subprocess.check_call([sys.executable, str(script)], cwd=root, env=env)


class build_py(_build_py):
    def run(self) -> None:
        _run_site_generator()
        super().run()


class sdist(_sdist):
    def run(self) -> None:
        _run_site_generator()
        super().run()


setup(cmdclass={"build_py": build_py, "sdist": sdist})
