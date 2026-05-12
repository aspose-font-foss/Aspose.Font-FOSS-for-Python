from __future__ import annotations

import json
from pathlib import Path

from aspose_font import reporting


def test_record_task_token_estimate_roundtrip(tmp_path: Path) -> None:
    store_path = tmp_path / "token-usage.json"

    record = reporting.record_task_token_estimate(
        "font-999",
        12345,
        task_title="Example Task",
        run_id="font-999_run",
        notes="assistant estimate",
        path=store_path,
    )

    assert record.task_id == "FONT-999"
    assert record.estimated_token_usage == 12345
    assert store_path.exists()

    loaded = reporting.get_task_token_estimate("FONT-999", store_path)
    assert loaded is not None
    assert loaded.task_title == "Example Task"
    assert loaded.run_id == "font-999_run"


def test_record_task_token_estimate_keeps_stage_estimates_separate(tmp_path: Path) -> None:
    store_path = tmp_path / "token-usage.json"

    completion = reporting.record_task_token_estimate(
        "FONT-999",
        1000,
        task_title="Example Task",
        run_id="font-999_completion",
        path=store_path,
    )
    to_code = reporting.record_task_token_estimate(
        "FONT-999",
        2500,
        task_title="Example Task",
        task_stage="To Code",
        run_id="font-999_to_code",
        path=store_path,
    )

    assert completion.task_stage == "completion"
    assert to_code.task_stage == "to-code"
    assert reporting.get_task_token_estimate("FONT-999", store_path).estimated_token_usage == 1000
    assert (
        reporting.get_task_token_estimate(
            "FONT-999", store_path, task_stage="to-code"
        ).estimated_token_usage
        == 2500
    )


def test_build_task_completion_payload_uses_configured_defaults() -> None:
    payload = reporting.build_task_completion_payload(
        task_id="FONT-123",
        task_title="Standards WOFF2 compatibility",
        estimated_token_usage=4567,
        run_id="font-123_run",
        status="success",
        run_duration_ms=987,
        items_discovered=5,
        items_failed=0,
        items_succeeded=5,
    )

    assert payload["agent_name"] == "AI Agent For Aspose Font FOSS"
    assert payload["agent_owner"] == "Maksym Kavun"
    assert payload["product"] == "Aspose.Font"
    assert payload["platform"] == "Python"
    assert payload["job_type"] == "Standards WOFF2 compatibility"
    assert payload["item_name"] == "Task Completion"
    assert payload["token_usage"] == 4567
    assert payload["token_usage_source"] == "assistant_estimate"
    assert payload["task_stage"] == "completion"


def test_build_task_stage_payload_swaps_item_name_and_job_type() -> None:
    payload = reporting.build_task_completion_payload(
        task_id="FONT-123",
        task_title="Standards WOFF2 compatibility",
        estimated_token_usage=4567,
        run_id="font-123_to_code",
        status="success",
        run_duration_ms=987,
        items_discovered=5,
        items_failed=0,
        items_succeeded=5,
        task_stage="To Code",
    )

    assert payload["job_type"] == "Standards WOFF2 compatibility"
    assert payload["item_name"] == "Task Stage"
    assert payload["task_stage"] == "to-code"


def test_build_task_payload_uses_custom_item_name_as_swapped_job_type() -> None:
    payload = reporting.build_task_completion_payload(
        task_id="FONT-123",
        task_title="Standards WOFF2 compatibility",
        estimated_token_usage=4567,
        run_id="font-123_custom",
        status="success",
        run_duration_ms=987,
        items_discovered=5,
        items_failed=0,
        items_succeeded=5,
        item_name="Custom Item",
        task_stage="documentation",
    )

    assert payload["job_type"] == "Custom Item"
    assert payload["item_name"] == "Task Stage"


def test_send_task_completion_report_posts_json(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class _Response:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def getcode(self) -> int:
            return 200

        def read(self) -> bytes:
            return b'{"ok":true}'

    def _fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["timeout"] = timeout
        captured["headers"] = dict(request.header_items())
        captured["body"] = json.loads(request.data.decode("utf-8"))
        return _Response()

    monkeypatch.setattr(reporting, "urlopen", _fake_urlopen)

    status_code, body = reporting.send_task_completion_report(
        {"task_id": "FONT-123", "token_usage": 321},
        endpoint="https://example.invalid/exec",
        token="secret",
        timeout_sec=3.0,
    )

    assert status_code == 200
    assert body == '{"ok":true}'
    assert captured["url"] == "https://example.invalid/exec?token=secret"
    assert captured["timeout"] == 3.0
    assert captured["body"] == {"task_id": "FONT-123", "token_usage": 321}
    assert "application/json" in captured["headers"]["Content-type"]


def test_maybe_send_task_completion_report_uses_stored_estimate(tmp_path: Path, monkeypatch) -> None:
    store_path = tmp_path / "token-usage.json"
    receipts_path = tmp_path / "token-reports.json"
    reporting.record_task_token_estimate(
        "FONT-123",
        4321,
        task_title="Website Generation",
        run_id="font-123_run",
        path=store_path,
    )

    sent: dict[str, object] = {}

    def _fake_sender(payload, *, endpoint=None, token=None, timeout_sec=10.0):
        sent["payload"] = payload
        return 200, '{"ok":true}'

    monkeypatch.setattr(reporting, "send_task_completion_report", _fake_sender)

    result = reporting.maybe_send_task_completion_report(
        task_id="FONT-123",
        task_title="Website Generation",
        status="success",
        run_duration_ms=2500,
        items_discovered=3,
        items_failed=0,
        items_succeeded=3,
        path=store_path,
        receipts_path=receipts_path,
    )

    assert result is not None
    payload = sent["payload"]
    assert payload["task_id"] == "FONT-123"
    assert payload["token_usage"] == 4321
    assert payload["run_duration_ms"] == 2500
    receipt = reporting.get_task_completion_receipt("FONT-123", receipts_path)
    assert receipt is not None
    assert receipt.response_code == 200


def test_maybe_send_task_completion_report_uses_stage_receipt_key(
    tmp_path: Path, monkeypatch
) -> None:
    store_path = tmp_path / "token-usage.json"
    receipts_path = tmp_path / "token-reports.json"
    reporting.record_task_token_estimate(
        "FONT-123",
        2222,
        task_title="Website Generation",
        task_stage="To Architect",
        run_id="font-123_to_architect",
        path=store_path,
    )

    def _fake_sender(payload, *, endpoint=None, token=None, timeout_sec=10.0):
        return 200, '{"ok":true}'

    monkeypatch.setattr(reporting, "send_task_completion_report", _fake_sender)

    result = reporting.maybe_send_task_completion_report(
        task_id="FONT-123",
        task_title="Website Generation",
        task_stage="To Architect",
        status="success",
        run_duration_ms=2500,
        items_discovered=1,
        items_failed=0,
        items_succeeded=1,
        path=store_path,
        receipts_path=receipts_path,
    )

    assert result is not None
    receipt = reporting.get_task_completion_receipt(
        "FONT-123", receipts_path, task_stage="to-architect"
    )
    assert receipt is not None
    assert receipt.task_stage == "to-architect"
    assert reporting.get_task_completion_receipt("FONT-123", receipts_path) is None


def test_reporting_cli_estimate_and_report_dry_run(tmp_path: Path, monkeypatch, capsys) -> None:
    store_path = tmp_path / "token-usage.json"
    monkeypatch.setenv("ASPOSE_FONT_TOKEN_USAGE_STORE", str(store_path))

    assert reporting.main(["estimate", "FONT-555", "9876", "--title", "Dry Run Task", "--run-id", "font-555_run"]) == 0
    estimate_out = json.loads(capsys.readouterr().out)
    assert estimate_out["task_id"] == "FONT-555"
    assert estimate_out["estimated_token_usage"] == 9876

    assert (
        reporting.main(
            [
                "report",
                "FONT-555",
                "--run-duration-ms",
                "111",
                "--items-discovered",
                "2",
                "--items-succeeded",
                "2",
                "--dry-run",
            ]
        )
        == 0
    )
    report_out = json.loads(capsys.readouterr().out)
    assert report_out["mode"] == "dry-run"
    assert report_out["payload"]["task_id"] == "FONT-555"
    assert report_out["payload"]["token_usage"] == 9876


def test_reporting_cli_stage_dry_run_stores_stage_estimate(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    store_path = tmp_path / "token-usage.json"
    receipts_path = tmp_path / "token-reports.json"
    monkeypatch.setenv("ASPOSE_FONT_TOKEN_USAGE_STORE", str(store_path))
    monkeypatch.setenv("ASPOSE_FONT_TOKEN_REPORT_RECEIPTS_STORE", str(receipts_path))

    assert (
        reporting.main(
            [
                "stage",
                "FONT-556",
                "In Review",
                "3456",
                "--title",
                "Stage Task",
                "--run-id",
                "font-556_in_review",
                "--dry-run",
            ]
        )
        == 0
    )

    out = json.loads(capsys.readouterr().out)
    assert out["mode"] == "dry-run"
    assert out["payload"]["job_type"] == "Stage Task"
    assert out["payload"]["item_name"] == "Task Stage"
    assert out["payload"]["task_stage"] == "in-review"
    assert out["payload"]["token_usage"] == 3456
    assert reporting.get_task_token_estimate(
        "FONT-556", store_path, task_stage="in-review"
    ).estimated_token_usage == 3456


def test_reporting_cli_report_returns_error_without_estimate(capsys, monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("ASPOSE_FONT_TOKEN_USAGE_STORE", str(tmp_path / "missing.json"))
    assert reporting.main(["report", "FONT-404", "--dry-run"]) == 1
    out = json.loads(capsys.readouterr().out)
    assert out["error"] == "missing_estimate"


def test_report_command_persists_completion_receipt(tmp_path: Path, monkeypatch, capsys) -> None:
    store_path = tmp_path / "token-usage.json"
    receipts_path = tmp_path / "token-reports.json"
    monkeypatch.setenv("ASPOSE_FONT_TOKEN_USAGE_STORE", str(store_path))
    monkeypatch.setenv("ASPOSE_FONT_TOKEN_REPORT_RECEIPTS_STORE", str(receipts_path))
    reporting.record_task_token_estimate(
        "FONT-600",
        333,
        task_title="Receipt Task",
        run_id="font-600_run",
        path=store_path,
    )

    def _fake_sender(payload, *, endpoint=None, token=None, timeout_sec=10.0):
        return 200, '{"ok":true}'

    monkeypatch.setattr(reporting, "send_task_completion_report", _fake_sender)

    assert reporting.main(["report", "FONT-600", "--run-duration-ms", "15"]) == 0
    capsys.readouterr()

    receipt = reporting.get_task_completion_receipt("FONT-600", receipts_path)
    assert receipt is not None
    assert receipt.run_id == "font-600_run"
    assert receipt.response_code == 200


def test_report_command_persists_stage_receipt(tmp_path: Path, monkeypatch, capsys) -> None:
    store_path = tmp_path / "token-usage.json"
    receipts_path = tmp_path / "token-reports.json"
    monkeypatch.setenv("ASPOSE_FONT_TOKEN_USAGE_STORE", str(store_path))
    monkeypatch.setenv("ASPOSE_FONT_TOKEN_REPORT_RECEIPTS_STORE", str(receipts_path))
    reporting.record_task_token_estimate(
        "FONT-601",
        444,
        task_title="Stage Receipt Task",
        task_stage="Integration",
        run_id="font-601_integration",
        path=store_path,
    )

    def _fake_sender(payload, *, endpoint=None, token=None, timeout_sec=10.0):
        return 200, '{"ok":true}'

    monkeypatch.setattr(reporting, "send_task_completion_report", _fake_sender)

    assert (
        reporting.main(["report", "FONT-601", "--stage", "Integration", "--run-duration-ms", "15"])
        == 0
    )
    capsys.readouterr()

    receipt = reporting.get_task_completion_receipt(
        "FONT-601", receipts_path, task_stage="integration"
    )
    assert receipt is not None
    assert receipt.run_id == "font-601_integration"
    assert receipt.task_stage == "integration"


def test_sync_completed_task_reports_is_idempotent(tmp_path: Path, monkeypatch) -> None:
    estimates_path = tmp_path / "token-usage.json"
    receipts_path = tmp_path / "token-reports.json"
    completed_dir = tmp_path / "completed"
    completed_dir.mkdir()
    (completed_dir / "font-700.md").write_text(
        "\n".join(
            [
                "---",
                "id: FONT-700",
                "title: Completed Sync Task",
                "status: Done",
                "---",
                "",
            ]
        ),
        encoding="utf-8",
    )
    reporting.record_task_token_estimate(
        "FONT-700",
        7000,
        task_title="Completed Sync Task",
        run_id="font-700_run",
        path=estimates_path,
    )

    sent_payloads: list[dict[str, object]] = []

    def _fake_sender(payload, *, endpoint=None, token=None, timeout_sec=10.0):
        sent_payloads.append(payload)
        return 200, '{"ok":true}'

    monkeypatch.setattr(reporting, "send_task_completion_report", _fake_sender)

    first = reporting.sync_completed_task_reports(
        estimates_path=estimates_path,
        receipts_path=receipts_path,
        completed_dir=completed_dir,
        run_duration_ms=42,
    )
    second = reporting.sync_completed_task_reports(
        estimates_path=estimates_path,
        receipts_path=receipts_path,
        completed_dir=completed_dir,
        run_duration_ms=42,
    )

    assert first["sent_count"] == 1
    assert first["failed_count"] == 0
    assert second["sent_count"] == 0
    assert second["results"] == [{"task_id": "FONT-700", "status": "already-reported"}]
    assert len(sent_payloads) == 1
    assert sent_payloads[0]["task_id"] == "FONT-700"


def test_reporting_cli_sync_completed_dry_run(tmp_path: Path, monkeypatch, capsys) -> None:
    store_path = tmp_path / "token-usage.json"
    receipts_path = tmp_path / "token-reports.json"
    completed_dir = tmp_path / "completed"
    completed_dir.mkdir()
    (completed_dir / "font-701.md").write_text(
        "\n".join(
            [
                "---",
                "id: FONT-701",
                "title: Dry Run Sync Task",
                "status: Done",
                "---",
                "",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("ASPOSE_FONT_TOKEN_USAGE_STORE", str(store_path))
    monkeypatch.setenv("ASPOSE_FONT_TOKEN_REPORT_RECEIPTS_STORE", str(receipts_path))
    monkeypatch.setenv("ASPOSE_FONT_COMPLETED_TASKS_DIR", str(completed_dir))

    assert (
        reporting.main(
            ["estimate", "FONT-701", "1701", "--title", "Dry Run Sync Task", "--run-id", "font-701_run"]
        )
        == 0
    )
    capsys.readouterr()

    assert reporting.main(["sync-completed", "--dry-run"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["sent_count"] == 0
    assert out["failed_count"] == 0
    assert out["results"][0]["status"] == "dry-run"
    assert out["results"][0]["payload"]["task_id"] == "FONT-701"
