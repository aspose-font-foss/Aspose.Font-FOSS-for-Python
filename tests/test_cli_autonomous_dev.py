"""Tests for autonomous-dev CLI command JSON summary output (FONT-381)."""

import json


def test_autonomous_dev_json_summary(tmp_path, monkeypatch):
    """Verify that the --json-summary flag writes the expected JSON file.

    The run_autonomous_development function is monkey‑patched to avoid the heavy
    workflow and return a minimal result with a ``summary`` attribute.
    """
    # Prepare a dummy font file – the stub will not read it.
    dummy_font = tmp_path / "dummy.ttf"
    dummy_font.touch()

    # Expected summary data returned by the stub.
    expected_summary = {"kind": "autonomous_workflow_result", "details": {}}

    class DummyResult:
        def __init__(self, summary):
            self.summary = summary

    def fake_run_autonomous_development(*_args, **_kwargs):
        return DummyResult(expected_summary)

    monkeypatch.setattr(
        "aspose_font.cli.run_autonomous_development",
        fake_run_autonomous_development,
    )

    json_path = tmp_path / "summary.json"

    # Invoke the CLI directly.
    import argparse

    import aspose_font.cli as cli
    args = argparse.Namespace(
        font_path=str(dummy_font),
        output_dir='.',
        no_qa=False,
        no_instances=False,
        include_woff=False,
        preset=None,
        naming_strategy=None,
        custom_family_suffix=None,
        legacy_family=None,
        legacy_style=None,
        typographic_family=None,
        typographic_style=None,
        stat_policy=None,
        font_display='swap',
        cdn_manifest=False,
        cdn_base='https://cdn.example.com',
        json_summary=str(json_path),
    )
    try:
        cli._cmd_autonomous_dev(args)
        class Result:
            returncode = 0
        result = Result()
    except Exception as exc:
        class Result:
            returncode = 1
            stderr = str(exc)
        result = Result()


    assert result.returncode == 0, f"CLI failed: {result.stderr}"
    assert json_path.exists(), "JSON summary file was not created"
    loaded = json.loads(json_path.read_text())
    assert loaded == expected_summary, "JSON content does not match expected summary"
