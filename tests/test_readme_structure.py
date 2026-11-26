from pathlib import Path


def test_readme_has_required_sections():
    root = Path(__file__).resolve().parents[1]
    readme_path = root / "README.md"
    assert readme_path.exists(), f"README.md not found at {readme_path}"

    check_script = root / "scripts" / "check_readme_structure.py"
    if check_script.exists():
        import importlib.util

        spec = importlib.util.spec_from_file_location("check_readme", check_script)
        check_module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(check_module)
        assert check_module.check_readme_sections(readme_path), "README.md missing required sections"
    else:
        required_sections = [
            "### 1. Web Font Optimization",
            "### 2. Font QA Reporting",
            "### 3. Release-Safe Variable Instance Packages",
        ]
        content = readme_path.read_text(encoding="utf-8")
        for section in required_sections:
            assert section in content, f"Missing required section in README.md: {section}"
