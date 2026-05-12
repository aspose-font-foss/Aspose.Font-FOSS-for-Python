"""Task token estimate storage and Google Sheets reporting helpers."""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

DEFAULT_REPORT_ENDPOINT = (
    "https://script.google.com/macros/s/"
    "AKfycbyCHwElrM6RcYLi0JNQAkJmzGrBjAhf28mKXVyub_6SdaZ2ITvzCwfM5xCLE7rmuxio/exec"
)
DEFAULT_REPORT_TOKEN = "lM6iU2mW0gV1eZ"
DEFAULT_AGENT_NAME = "AI Agent For Aspose Font FOSS"
DEFAULT_AGENT_OWNER = "Maksym Kavun"
DEFAULT_PRODUCT = "Aspose.Font"
DEFAULT_PLATFORM = "Python"
DEFAULT_WEBSITE = "gitlab.recruitize.ai"
DEFAULT_WEBSITE_SECTION = "Font FOSS Internal Site"
DEFAULT_TASK_STAGE = "completion"
STAGE_HELP = (
    "Task stage, for example to-architect, to-code, in-review, "
    "integration, documentation, or completion."
)


@dataclass(slots=True)
class TaskTokenEstimate:
    task_id: str
    task_title: str
    estimated_token_usage: int
    updated_at: str
    run_id: str
    notes: str = ""
    task_stage: str = DEFAULT_TASK_STAGE


@dataclass(slots=True)
class TaskCompletionReceipt:
    task_id: str
    task_title: str
    run_id: str
    reported_at: str
    status: str
    response_code: int
    response_body: str
    run_duration_ms: int
    items_discovered: int
    items_failed: int
    items_succeeded: int
    api_calls_count: int
    task_stage: str = DEFAULT_TASK_STAGE


@dataclass(slots=True)
class CompletedTaskRecord:
    task_id: str
    task_title: str
    path: str


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def repository_root() -> Path:
    return Path(__file__).resolve().parents[2]


def normalize_task_stage(task_stage: str | None = None) -> str:
    stage = (task_stage or DEFAULT_TASK_STAGE).strip().lower()
    if not stage:
        return DEFAULT_TASK_STAGE
    return stage.replace(" ", "-").replace("_", "-")


def token_usage_record_key(task_id: str, task_stage: str | None = None) -> str:
    normalized_task_id = task_id.strip().upper()
    stage = normalize_task_stage(task_stage)
    if stage == DEFAULT_TASK_STAGE:
        return normalized_task_id
    return f"{normalized_task_id}:{stage}"


def token_usage_store_path() -> Path:
    override = os.environ.get("ASPOSE_FONT_TOKEN_USAGE_STORE")
    if override:
        return Path(override)
    return repository_root() / "backlog" / "runtime" / "token_usage_estimates.json"


def completion_receipts_store_path() -> Path:
    override = os.environ.get("ASPOSE_FONT_TOKEN_REPORT_RECEIPTS_STORE")
    if override:
        return Path(override)
    return repository_root() / "backlog" / "runtime" / "token_usage_reports.json"


def completed_tasks_dir_path() -> Path:
    override = os.environ.get("ASPOSE_FONT_COMPLETED_TASKS_DIR")
    if override:
        return Path(override)
    return repository_root() / "backlog" / "completed"


def load_token_usage_store(path: Path | None = None) -> dict[str, TaskTokenEstimate]:
    path = path or token_usage_store_path()
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {task_id: TaskTokenEstimate(**item) for task_id, item in payload.items()}


def save_token_usage_store(store: dict[str, TaskTokenEstimate], path: Path | None = None) -> None:
    path = path or token_usage_store_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {task_id: asdict(item) for task_id, item in sorted(store.items())}
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def load_completion_receipts_store(path: Path | None = None) -> dict[str, TaskCompletionReceipt]:
    path = path or completion_receipts_store_path()
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {task_id: TaskCompletionReceipt(**item) for task_id, item in payload.items()}


def save_completion_receipts_store(
    store: dict[str, TaskCompletionReceipt], path: Path | None = None
) -> None:
    path = path or completion_receipts_store_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {task_id: asdict(item) for task_id, item in sorted(store.items())}
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def record_task_token_estimate(
    task_id: str,
    estimated_token_usage: int,
    *,
    task_title: str = "",
    task_stage: str | None = None,
    run_id: str | None = None,
    notes: str = "",
    path: Path | None = None,
) -> TaskTokenEstimate:
    if estimated_token_usage < 0:
        raise ValueError("estimated_token_usage must be non-negative")
    normalized_task_id = task_id.strip().upper()
    if not normalized_task_id:
        raise ValueError("task_id is required")
    normalized_stage = normalize_task_stage(task_stage)
    record_key = token_usage_record_key(normalized_task_id, normalized_stage)
    store = load_token_usage_store(path)
    previous = store.get(record_key)
    record = TaskTokenEstimate(
        task_id=normalized_task_id,
        task_title=task_title.strip() or (previous.task_title if previous else ""),
        estimated_token_usage=estimated_token_usage,
        updated_at=_utc_now_iso(),
        run_id=run_id
        or (
            previous.run_id
            if previous
            else f"{record_key.lower().replace(':', '_')}_{int(datetime.now().timestamp())}"
        ),
        notes=notes.strip() or (previous.notes if previous else ""),
        task_stage=normalized_stage,
    )
    store[record_key] = record
    save_token_usage_store(store, path)
    return record


def get_task_token_estimate(
    task_id: str, path: Path | None = None, task_stage: str | None = None
) -> TaskTokenEstimate | None:
    return load_token_usage_store(path).get(token_usage_record_key(task_id, task_stage))


def get_task_completion_receipt(
    task_id: str, path: Path | None = None, task_stage: str | None = None
) -> TaskCompletionReceipt | None:
    return load_completion_receipts_store(path).get(token_usage_record_key(task_id, task_stage))


def build_task_completion_payload(
    *,
    task_id: str,
    task_title: str,
    estimated_token_usage: int,
    run_id: str,
    status: str,
    run_duration_ms: int,
    items_discovered: int,
    items_failed: int,
    items_succeeded: int,
    api_calls_count: int = 0,
    website: str = DEFAULT_WEBSITE,
    website_section: str = DEFAULT_WEBSITE_SECTION,
    item_name: str | None = None,
    task_stage: str | None = None,
    timestamp: str | None = None,
) -> dict[str, Any]:
    normalized_stage = normalize_task_stage(task_stage)
    job_type = (
        "Task Completion"
        if normalized_stage == DEFAULT_TASK_STAGE
        else "Task Stage"
    )
    item_name_value = item_name or task_title or task_id
    return {
        "timestamp": timestamp or _utc_now_iso(),
        "agent_name": DEFAULT_AGENT_NAME,
        "agent_owner": DEFAULT_AGENT_OWNER,
        "job_type": item_name_value,
        "run_id": run_id,
        "status": status,
        "product": DEFAULT_PRODUCT,
        "platform": DEFAULT_PLATFORM,
        "website": website,
        "website_section": website_section,
        "item_name": job_type,
        "task_id": task_id,
        "task_title": task_title,
        "task_stage": normalized_stage,
        "items_discovered": items_discovered,
        "items_failed": items_failed,
        "items_succeeded": items_succeeded,
        "run_duration_ms": run_duration_ms,
        "token_usage": estimated_token_usage,
        "token_usage_source": "assistant_estimate",
        "api_calls_count": api_calls_count,
    }


def record_task_completion_receipt(
    *,
    payload: dict[str, Any],
    response_code: int,
    response_body: str,
    path: Path | None = None,
) -> TaskCompletionReceipt:
    task_id = str(payload["task_id"]).strip().upper()
    task_stage = normalize_task_stage(str(payload.get("task_stage", DEFAULT_TASK_STAGE)))
    record_key = token_usage_record_key(task_id, task_stage)
    store = load_completion_receipts_store(path)
    receipt = TaskCompletionReceipt(
        task_id=task_id,
        task_title=str(payload.get("task_title", "")),
        run_id=str(payload.get("run_id", "")),
        reported_at=_utc_now_iso(),
        status=str(payload.get("status", "")),
        response_code=response_code,
        response_body=response_body,
        run_duration_ms=int(payload.get("run_duration_ms", 0)),
        items_discovered=int(payload.get("items_discovered", 0)),
        items_failed=int(payload.get("items_failed", 0)),
        items_succeeded=int(payload.get("items_succeeded", 0)),
        api_calls_count=int(payload.get("api_calls_count", 0)),
        task_stage=task_stage,
    )
    store[record_key] = receipt
    save_completion_receipts_store(store, path)
    return receipt


def send_task_completion_report(
    payload: dict[str, Any],
    *,
    endpoint: str | None = None,
    token: str | None = None,
    timeout_sec: float = 10.0,
) -> tuple[int, str]:
    endpoint = endpoint or os.environ.get("ASPOSE_FONT_TOKEN_REPORT_ENDPOINT") or DEFAULT_REPORT_ENDPOINT
    token = token or os.environ.get("ASPOSE_FONT_TOKEN_REPORT_TOKEN") or DEFAULT_REPORT_TOKEN
    query = urlencode({"token": token})
    url = f"{endpoint}?{query}"
    body = json.dumps(payload).encode("utf-8")
    request = Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urlopen(request, timeout=timeout_sec) as response:
            return response.getcode(), response.read().decode("utf-8", errors="replace")
    except HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", errors="replace")
    except URLError as exc:
        return 0, str(exc)


def maybe_send_task_completion_report(
    *,
    task_id: str | None,
    task_title: str,
    status: str,
    run_duration_ms: int,
    items_discovered: int,
    items_failed: int,
    items_succeeded: int,
    api_calls_count: int = 0,
    website: str = DEFAULT_WEBSITE,
    website_section: str = DEFAULT_WEBSITE_SECTION,
    task_stage: str | None = None,
    path: Path | None = None,
    receipts_path: Path | None = None,
) -> dict[str, Any] | None:
    if not task_id:
        return None
    normalized_stage = normalize_task_stage(task_stage)
    record = get_task_token_estimate(task_id, path, normalized_stage)
    if record is None:
        override = os.environ.get("ASPOSE_FONT_ESTIMATED_TOKEN_USAGE")
        if override is None:
            return None
        record = TaskTokenEstimate(
            task_id=task_id.strip().upper(),
            task_title=task_title,
            estimated_token_usage=int(override),
            updated_at=_utc_now_iso(),
            run_id=os.environ.get(
                "ASPOSE_FONT_RUN_ID",
                (
                    f"{token_usage_record_key(task_id, normalized_stage).lower().replace(':', '_')}_"
                    f"{int(datetime.now().timestamp())}"
                ),
            ),
            notes="",
            task_stage=normalized_stage,
        )
    payload = build_task_completion_payload(
        task_id=record.task_id,
        task_title=task_title or record.task_title or record.task_id,
        estimated_token_usage=record.estimated_token_usage,
        run_id=record.run_id,
        status=status,
        run_duration_ms=run_duration_ms,
        items_discovered=items_discovered,
        items_failed=items_failed,
        items_succeeded=items_succeeded,
        api_calls_count=api_calls_count,
        website=website,
        website_section=website_section,
        task_stage=normalized_stage,
    )
    response_code, response_body = send_task_completion_report(payload)
    if 200 <= response_code < 300:
        record_task_completion_receipt(
            payload=payload,
            response_code=response_code,
            response_body=response_body,
            path=receipts_path,
        )
    return {
        "payload": payload,
        "response_code": response_code,
        "response_body": response_body,
    }


def _parse_front_matter(lines: list[str]) -> dict[str, str]:
    metadata: dict[str, str] = {}
    if len(lines) < 3 or lines[0].strip() != "---":
        return metadata
    for line in lines[1:]:
        stripped = line.strip()
        if stripped == "---":
            break
        if ":" not in line:
            continue
        key, raw_value = line.split(":", 1)
        value = raw_value.strip()
        if value.startswith("'") and value.endswith("'") and len(value) >= 2:
            value = value[1:-1]
        elif value.startswith('"') and value.endswith('"') and len(value) >= 2:
            value = value[1:-1]
        metadata[key.strip()] = value
    return metadata


def read_completed_task_record(path: Path) -> CompletedTaskRecord:
    lines = path.read_text(encoding="utf-8").splitlines()
    metadata = _parse_front_matter(lines)
    task_id = metadata.get("id", "").strip().upper()
    if not task_id:
        raise ValueError(f"Completed task file {path} does not declare an id")
    task_title = metadata.get("title", "").strip()
    if not task_title:
        raise ValueError(f"Completed task file {path} does not declare a title")
    return CompletedTaskRecord(task_id=task_id, task_title=task_title, path=str(path))


def iter_completed_task_records(path: Path | None = None) -> list[CompletedTaskRecord]:
    completed_dir = path or completed_tasks_dir_path()
    if not completed_dir.exists():
        return []
    return [read_completed_task_record(item) for item in sorted(completed_dir.glob("*.md"))]


def sync_completed_task_reports(
    *,
    estimates_path: Path | None = None,
    receipts_path: Path | None = None,
    completed_dir: Path | None = None,
    status: str = "success",
    run_duration_ms: int = 0,
    items_discovered: int = 1,
    items_failed: int = 0,
    items_succeeded: int = 1,
    api_calls_count: int = 0,
    website: str = DEFAULT_WEBSITE,
    website_section: str = DEFAULT_WEBSITE_SECTION,
    dry_run: bool = False,
) -> dict[str, Any]:
    estimates = load_token_usage_store(estimates_path)
    receipts = load_completion_receipts_store(receipts_path)
    results: list[dict[str, Any]] = []
    sent_count = 0
    skipped_count = 0
    failed_count = 0

    for completed_task in iter_completed_task_records(completed_dir):
        if completed_task.task_id in receipts:
            skipped_count += 1
            results.append({"task_id": completed_task.task_id, "status": "already-reported"})
            continue
        estimate = estimates.get(completed_task.task_id)
        if estimate is None:
            skipped_count += 1
            results.append({"task_id": completed_task.task_id, "status": "missing-estimate"})
            continue
        payload = build_task_completion_payload(
            task_id=completed_task.task_id,
            task_title=completed_task.task_title or estimate.task_title or completed_task.task_id,
            estimated_token_usage=estimate.estimated_token_usage,
            run_id=estimate.run_id,
            status=status,
            run_duration_ms=run_duration_ms,
            items_discovered=items_discovered,
            items_failed=items_failed,
            items_succeeded=items_succeeded,
            api_calls_count=api_calls_count,
            website=website,
            website_section=website_section,
            task_stage=DEFAULT_TASK_STAGE,
        )
        if dry_run:
            results.append(
                {"task_id": completed_task.task_id, "status": "dry-run", "payload": payload}
            )
            continue
        response_code, response_body = send_task_completion_report(payload)
        if 200 <= response_code < 300:
            record_task_completion_receipt(
                payload=payload,
                response_code=response_code,
                response_body=response_body,
                path=receipts_path,
            )
            sent_count += 1
            results.append(
                {
                    "task_id": completed_task.task_id,
                    "status": "sent",
                    "response_code": response_code,
                }
            )
            continue
        failed_count += 1
        results.append(
            {
                "task_id": completed_task.task_id,
                "status": "failed",
                "response_code": response_code,
                "response_body": response_body,
            }
        )

    return {
        "sent_count": sent_count,
        "skipped_count": skipped_count,
        "failed_count": failed_count,
        "results": results,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Manage assistant-estimated token usage records and completion reports."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    estimate = subparsers.add_parser(
        "estimate", help="Store an assistant-estimated token usage value for a task."
    )
    estimate.add_argument("task_id", help="Task id, for example FONT-123.")
    estimate.add_argument(
        "estimated_token_usage",
        type=int,
        help="Assistant-estimated total token usage for the task or stage.",
    )
    estimate.add_argument("--title", default="", help="Optional task title to store with the estimate.")
    estimate.add_argument("--stage", default=DEFAULT_TASK_STAGE, help=STAGE_HELP)
    estimate.add_argument("--run-id", default=None, help="Optional run identifier.")
    estimate.add_argument("--notes", default="", help="Optional free-form note.")

    report = subparsers.add_parser("report", help="Send the stored completion report for a task.")
    report.add_argument("task_id", help="Task id, for example FONT-123.")
    report.add_argument(
        "--title", default="", help="Optional task title override for the outbound payload."
    )
    report.add_argument("--stage", default=DEFAULT_TASK_STAGE, help=STAGE_HELP)
    report.add_argument(
        "--status", default="success", help="Completion status to report (default: success)."
    )
    report.add_argument("--run-duration-ms", type=int, default=0, help="Run duration in milliseconds.")
    report.add_argument(
        "--items-discovered", type=int, default=1, help="Number of items discovered in the run."
    )
    report.add_argument(
        "--items-failed", type=int, default=0, help="Number of items failed in the run."
    )
    report.add_argument(
        "--items-succeeded", type=int, default=1, help="Number of items succeeded in the run."
    )
    report.add_argument(
        "--api-calls-count", type=int, default=0, help="Optional API call count to include."
    )
    report.add_argument("--website", default=DEFAULT_WEBSITE, help="Website field for the payload.")
    report.add_argument(
        "--website-section", default=DEFAULT_WEBSITE_SECTION, help="Website section field."
    )
    report.add_argument(
        "--dry-run", action="store_true", help="Print the payload without sending the POST request."
    )

    stage = subparsers.add_parser(
        "stage",
        help="Store and send an assistant-estimated token report for a single task stage.",
    )
    stage.add_argument("task_id", help="Task id, for example FONT-123.")
    stage.add_argument("task_stage", help=STAGE_HELP)
    stage.add_argument(
        "estimated_token_usage", type=int, help="Assistant-estimated token usage for this stage."
    )
    stage.add_argument(
        "--title", default="", help="Optional task title override for the outbound payload."
    )
    stage.add_argument("--status", default="success", help="Stage status to report (default: success).")
    stage.add_argument("--run-duration-ms", type=int, default=0, help="Run duration in milliseconds.")
    stage.add_argument(
        "--items-discovered", type=int, default=1, help="Number of items discovered in the run."
    )
    stage.add_argument(
        "--items-failed", type=int, default=0, help="Number of items failed in the run."
    )
    stage.add_argument(
        "--items-succeeded", type=int, default=1, help="Number of items succeeded in the run."
    )
    stage.add_argument(
        "--api-calls-count", type=int, default=0, help="Optional API call count to include."
    )
    stage.add_argument("--website", default=DEFAULT_WEBSITE, help="Website field for the payload.")
    stage.add_argument(
        "--website-section", default=DEFAULT_WEBSITE_SECTION, help="Website section field."
    )
    stage.add_argument("--run-id", default=None, help="Optional run identifier.")
    stage.add_argument("--notes", default="", help="Optional free-form note stored with the estimate.")
    stage.add_argument(
        "--dry-run",
        action="store_true",
        help="Store the estimate and print the payload without sending the POST request.",
    )

    sync_completed = subparsers.add_parser(
        "sync-completed",
        help="Automatically send missing reports for completed backlog tasks with stored estimates.",
    )
    sync_completed.add_argument(
        "--status", default="success", help="Completion status to report (default: success)."
    )
    sync_completed.add_argument("--run-duration-ms", type=int, default=0, help="Run duration in milliseconds.")
    sync_completed.add_argument(
        "--items-discovered", type=int, default=1, help="Number of items discovered in the run."
    )
    sync_completed.add_argument(
        "--items-failed", type=int, default=0, help="Number of items failed in the run."
    )
    sync_completed.add_argument(
        "--items-succeeded", type=int, default=1, help="Number of items succeeded in the run."
    )
    sync_completed.add_argument(
        "--api-calls-count", type=int, default=0, help="Optional API call count to include."
    )
    sync_completed.add_argument("--website", default=DEFAULT_WEBSITE, help="Website field for the payload.")
    sync_completed.add_argument(
        "--website-section", default=DEFAULT_WEBSITE_SECTION, help="Website section field."
    )
    sync_completed.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview which completed tasks would be reported without sending POST requests.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command == "estimate":
        record = record_task_token_estimate(
            args.task_id,
            args.estimated_token_usage,
            task_title=args.title,
            task_stage=args.stage,
            run_id=args.run_id,
            notes=args.notes,
        )
        print(
            json.dumps(
                {
                    "task_id": record.task_id,
                    "task_title": record.task_title,
                    "estimated_token_usage": record.estimated_token_usage,
                    "task_stage": record.task_stage,
                    "updated_at": record.updated_at,
                    "run_id": record.run_id,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    if args.command == "report":
        record = get_task_token_estimate(args.task_id, task_stage=args.stage)
        if record is None:
            report_key = token_usage_record_key(args.task_id, args.stage)
            print(
                json.dumps(
                    {
                        "error": "missing_estimate",
                        "message": f"No stored estimate found for {report_key}",
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
            return 1
        payload = build_task_completion_payload(
            task_id=record.task_id,
            task_title=args.title or record.task_title or record.task_id,
            estimated_token_usage=record.estimated_token_usage,
            run_id=record.run_id,
            status=args.status,
            run_duration_ms=args.run_duration_ms,
            items_discovered=args.items_discovered,
            items_failed=args.items_failed,
            items_succeeded=args.items_succeeded,
            api_calls_count=args.api_calls_count,
            website=args.website,
            website_section=args.website_section,
            task_stage=args.stage,
        )
        if args.dry_run:
            print(json.dumps({"mode": "dry-run", "payload": payload}, indent=2, sort_keys=True))
            return 0
        response_code, response_body = send_task_completion_report(payload)
        if 200 <= response_code < 300:
            record_task_completion_receipt(
                payload=payload,
                response_code=response_code,
                response_body=response_body,
            )
        print(
            json.dumps(
                {
                    "response_body": response_body,
                    "response_code": response_code,
                    "task_id": record.task_id,
                    "task_stage": record.task_stage,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0 if 200 <= response_code < 300 else 1

    if args.command == "stage":
        record = record_task_token_estimate(
            args.task_id,
            args.estimated_token_usage,
            task_title=args.title,
            task_stage=args.task_stage,
            run_id=args.run_id,
            notes=args.notes,
        )
        payload = build_task_completion_payload(
            task_id=record.task_id,
            task_title=args.title or record.task_title or record.task_id,
            estimated_token_usage=record.estimated_token_usage,
            run_id=record.run_id,
            status=args.status,
            run_duration_ms=args.run_duration_ms,
            items_discovered=args.items_discovered,
            items_failed=args.items_failed,
            items_succeeded=args.items_succeeded,
            api_calls_count=args.api_calls_count,
            website=args.website,
            website_section=args.website_section,
            task_stage=record.task_stage,
        )
        if args.dry_run:
            print(json.dumps({"mode": "dry-run", "payload": payload}, indent=2, sort_keys=True))
            return 0
        response_code, response_body = send_task_completion_report(payload)
        if 200 <= response_code < 300:
            record_task_completion_receipt(
                payload=payload,
                response_code=response_code,
                response_body=response_body,
            )
        print(
            json.dumps(
                {
                    "response_body": response_body,
                    "response_code": response_code,
                    "task_id": record.task_id,
                    "task_stage": record.task_stage,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0 if 200 <= response_code < 300 else 1

    if args.command == "sync-completed":
        result = sync_completed_task_reports(
            status=args.status,
            run_duration_ms=args.run_duration_ms,
            items_discovered=args.items_discovered,
            items_failed=args.items_failed,
            items_succeeded=args.items_succeeded,
            api_calls_count=args.api_calls_count,
            website=args.website,
            website_section=args.website_section,
            dry_run=args.dry_run,
        )
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["failed_count"] == 0 else 1

    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
