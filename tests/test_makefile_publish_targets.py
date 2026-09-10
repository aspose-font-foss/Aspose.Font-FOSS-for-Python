from pathlib import Path


def _target_command(makefile_text: str, target: str) -> str:
    lines = makefile_text.splitlines()
    header = f"{target}:"
    for index, line in enumerate(lines):
        if line.startswith(header):
            for candidate in lines[index + 1 :]:
                if not candidate.strip():
                    continue
                if candidate.startswith("\t"):
                    return candidate.strip()
                break
    raise AssertionError(f"Target '{target}' not found or missing recipe command")


def test_publish_targets_use_self_contained_twine():
    makefile_text = Path("Makefile").read_text(encoding="utf-8")
    publish = _target_command(makefile_text, "publish")
    publish_test = _target_command(makefile_text, "publish-test")

    expected_prefix = "uv run --with twine python -m twine upload"
    assert publish.startswith(expected_prefix)
    assert publish_test.startswith(expected_prefix)
    assert publish.endswith("dist/*")
    assert "--repository testpypi" in publish_test


def test_publish_help_mentions_build_precondition():
    makefile_text = Path("Makefile").read_text(encoding="utf-8")
    assert "publish-test: ## Publish to TestPyPI (requires dist/* from `make build`)" in makefile_text
    assert "publish: ## Publish to PyPI (requires dist/* from `make build`)" in makefile_text
