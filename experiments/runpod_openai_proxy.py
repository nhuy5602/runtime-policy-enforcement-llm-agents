"""Bridge OpenAI Chat Completions requests to a cancellable Runpod queue job.

The vLLM endpoint's direct ``/openai/v1/chat/completions`` route can reject
AgentDojo's tool-bearing request shape. This local, dependency-free bridge
forwards the complete request body through the worker's documented
``/run`` route, polls its status, and requests remote cancellation when the
local deadline expires. A cancellation request is not a billing hard cap;
callers must reconcile the final remote status before a new batch.
"""

from __future__ import annotations

import argparse
import hashlib
import http.client
import json
import os
import threading
import time
import urllib.error
import urllib.request
from contextlib import contextmanager
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Iterator
from urllib.parse import urlparse


TERMINAL_STATUSES = frozenset({"COMPLETED", "FAILED", "CANCELLED", "TIMED_OUT"})


def _request_sha256(body: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


class JobLedger:
    """Append-only local evidence of job identities; never stores a prompt or key."""

    def __init__(self, path: Path, endpoint_id: str, run_id: str) -> None:
        self.path = path
        self.endpoint_id = endpoint_id
        self.run_id = run_id
        self._lock = threading.RLock()
        self._blocked_reason: str | None = None

    def _append(
        self,
        event: str,
        *,
        job_id: str | None,
        request_sha256: str,
        status: str,
        timeout: float,
    ) -> None:
        row = {
            "schema_version": "runpod-job-ledger/v1",
            "event": event,
            "run_id": self.run_id,
            "endpoint_id": self.endpoint_id,
            "job_id": job_id,
            "request_sha256": request_sha256,
            "observed_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "status": status,
            "timeout_seconds": timeout,
        }
        with self._lock:
            try:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                with self.path.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
                    handle.flush()
                    os.fsync(handle.fileno())
            except OSError as error:
                self._blocked_reason = (
                    f"local ledger persistence failed ({type(error).__name__}); "
                    "manual remote reconciliation is required"
                )
                raise

    def submitted(self, job_id: str, body: dict[str, Any], status: str, timeout: float) -> str:
        digest = _request_sha256(body)
        self._append("submitted", job_id=job_id, request_sha256=digest, status=status, timeout=timeout)
        return digest

    def submission_ambiguous(self, body: dict[str, Any], status: str, timeout: float) -> None:
        with self._lock:
            self._blocked_reason = "an ambiguous Runpod submission was observed; do not submit another batch"
            self._append(
                "submission_ambiguous",
                job_id=None,
                request_sha256=_request_sha256(body),
                status=status,
                timeout=timeout,
            )

    def cancel_requested(self, job_id: str, request_sha256: str, status: str, timeout: float) -> None:
        self._append(
            "cancel_requested",
            job_id=job_id,
            request_sha256=request_sha256,
            status=status,
            timeout=timeout,
        )

    def terminal(self, job_id: str, request_sha256: str, status: str, timeout: float) -> None:
        self._append("terminal", job_id=job_id, request_sha256=request_sha256, status=status, timeout=timeout)

    @contextmanager
    def exclusive_submission(self) -> Iterator[None]:
        """Serialize submits and refuse a ledger that needs human reconciliation."""

        with self._lock:
            if self._blocked_reason is not None:
                raise RuntimeError(f"Runpod proxy submission is blocked: {self._blocked_reason}")
            summary = ledger_summary(self.path, endpoint_id=self.endpoint_id)
            if summary["torn_trailing_record"]:
                self._blocked_reason = "the ledger has a torn trailing record requiring manual investigation"
                raise RuntimeError("job ledger has a torn trailing record; do not submit another batch")
            if summary["ambiguous_submissions"]:
                self._blocked_reason = "the ledger contains an ambiguous submission"
                raise RuntimeError("job ledger has ambiguous submission(s); do not submit another batch")
            if summary["unreconciled_job_ids"]:
                raise RuntimeError("job ledger has unreconciled job(s); reconcile before another submission")
            yield


def ledger_summary(path: Path, *, endpoint_id: str | None = None) -> dict[str, Any]:
    """Return a fail-closed summary of local job identities and terminal receipts."""

    if not path.exists():
        return {
            "ledger": str(path),
            "exists": False,
            "job_count": 0,
            "ambiguous_submissions": 0,
            "torn_trailing_record": False,
            "unreconciled_job_ids": [],
            "all_jobs_terminal": True,
        }
    jobs: dict[str, dict[str, str]] = {}
    ambiguous = 0
    torn_trailing_record = False
    content = path.read_text(encoding="utf-8")
    raw_lines = content.splitlines(keepends=True)
    if not raw_lines and content == "":
        torn_trailing_record = True
    for line_number, raw_line in enumerate(raw_lines, start=1):
        line = raw_line.rstrip("\r\n")
        is_final_line = line_number == len(raw_lines)
        try:
            row = json.loads(line)
        except json.JSONDecodeError as error:
            if is_final_line:
                torn_trailing_record = True
                break
            raise ValueError(f"invalid job ledger JSON at line {line_number}") from error
        try:
            if not isinstance(row, dict) or row.get("schema_version") != "runpod-job-ledger/v1":
                raise ValueError("invalid job ledger record")
            if endpoint_id is not None and row.get("endpoint_id") != endpoint_id:
                raise ValueError("job ledger endpoint mismatch")
            event = row.get("event")
            job_id = row.get("job_id")
            if event == "submission_ambiguous":
                ambiguous += 1
            else:
                if not isinstance(job_id, str) or not job_id:
                    raise ValueError(f"job ledger event {event!r} lacks a job id")
                if event == "submitted":
                    if job_id in jobs:
                        raise ValueError("duplicate submitted job")
                    jobs[job_id] = {
                        "request_sha256": str(row.get("request_sha256", "")),
                        "status": str(row.get("status", "")),
                        "terminal": "false",
                    }
                elif event == "terminal":
                    if job_id not in jobs:
                        raise ValueError("terminal receipt without submitted job")
                    terminal_status = str(row.get("status", "")).upper()
                    if terminal_status not in TERMINAL_STATUSES:
                        raise ValueError("nonterminal terminal receipt")
                    jobs[job_id]["status"] = terminal_status
                    jobs[job_id]["terminal"] = "true"
                elif event == "cancel_requested":
                    if job_id not in jobs:
                        raise ValueError("cancel receipt without submitted job")
                    jobs[job_id]["status"] = str(row.get("status", ""))
                else:
                    raise ValueError(f"unknown job ledger event {event!r}")
        except ValueError as error:
            if is_final_line:
                torn_trailing_record = True
                break
            raise ValueError(f"{error} at line {line_number}") from error
        if is_final_line and not raw_line.endswith(("\n", "\r")):
            torn_trailing_record = True
    unresolved = sorted(job_id for job_id, row in jobs.items() if row["terminal"] != "true")
    return {
        "ledger": str(path),
        "exists": True,
        "job_count": len(jobs),
        "ambiguous_submissions": ambiguous,
        "torn_trailing_record": torn_trailing_record,
        "unreconciled_job_ids": unresolved,
        "all_jobs_terminal": ambiguous == 0 and not torn_trailing_record and not unresolved,
        "jobs": jobs,
    }


def endpoint_base(endpoint_id: str) -> str:
    endpoint_id = endpoint_id.strip()
    if not endpoint_id or "/" in endpoint_id:
        raise ValueError("endpoint id must be a non-empty slug")
    return f"https://api.runpod.ai/v2/{endpoint_id}"


def _auth_headers(api_key: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "User-Agent": "runtime-policy-research/runpod-openai-proxy",
    }


def _json_request(
    method: str,
    url: str,
    *,
    api_key: str,
    payload: dict[str, Any] | None = None,
    timeout: float,
) -> dict[str, Any]:
    data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers=_auth_headers(api_key), method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            value = json.load(response)
    except urllib.error.HTTPError as error:
        detail = error.read(512).decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"Runpod HTTP {error.code}: {detail[:300]}") from error
    except (
        urllib.error.URLError,
        OSError,
        http.client.HTTPException,
        json.JSONDecodeError,
        UnicodeDecodeError,
    ) as error:
        raise RuntimeError(f"Runpod transport/response error: {type(error).__name__}") from error
    if not isinstance(value, dict):
        raise RuntimeError("Runpod returned a non-object JSON body")
    return value


def make_run_payload(route: str, body: dict[str, Any]) -> dict[str, Any]:
    if not route.startswith("/") or not route.endswith("/chat/completions"):
        raise ValueError("route must be an OpenAI chat-completions path")
    return {"input": {"route": route, "body": body}}


def unwrap_completed(body: dict[str, Any]) -> dict[str, Any]:
    """Return the OpenAI response object from a completed Runpod body."""

    output = body.get("output")
    if isinstance(output, list) and output and isinstance(output[0], dict):
        return output[0]
    if isinstance(output, dict):
        return output
    raise RuntimeError("Runpod completed without an OpenAI response object")


def _cancel_and_confirm(
    base: str,
    job_id: str,
    api_key: str,
    *,
    ledger: JobLedger | None,
    request_sha256: str,
    timeout: float,
    observed_status: str,
) -> str:
    """Request cancellation and return the observed terminal state, not a causal claim."""

    ledger_error: OSError | None = None
    if ledger is not None:
        try:
            ledger.cancel_requested(job_id, request_sha256, observed_status, timeout)
        except OSError as error:
            ledger_error = error

    def finish(status: str) -> str:
        nonlocal ledger_error
        if ledger is not None:
            try:
                ledger.terminal(job_id, request_sha256, status, timeout)
            except OSError as error:
                ledger_error = ledger_error or error
        if ledger_error is not None:
            raise RuntimeError(
                f"observed remote terminal status {status} for job {job_id}, "
                "but local ledger persistence failed"
            ) from ledger_error
        return status

    try:
        cancelled = _json_request(
            "POST",
            f"{base}/cancel/{job_id}",
            api_key=api_key,
            timeout=10.0,
        )
        status = str(cancelled.get("status", "")).upper()
        if status not in TERMINAL_STATUSES:
            confirmed = _json_request(
                "GET",
                f"{base}/status/{job_id}",
                api_key=api_key,
                timeout=10.0,
            )
            status = str(confirmed.get("status", "")).upper()
    except RuntimeError as error:
        raise RuntimeError(f"cancellation unverified for job {job_id}: {error}") from error
    if status not in TERMINAL_STATUSES:
        raise RuntimeError(f"cancellation unverified for job {job_id}: status={status or 'missing'}")
    return finish(status)


def reconcile_ledger(
    endpoint_id: str,
    api_key: str,
    ledger_path: Path,
    *,
    run_id: str,
    timeout: float = 10.0,
) -> dict[str, Any]:
    """Resolve every known nonterminal job before a launcher exits or continues."""

    summary = ledger_summary(ledger_path, endpoint_id=endpoint_id)
    torn_trailing_record = bool(summary["torn_trailing_record"])
    # A torn final line cannot safely accept another append. Still query/cancel
    # complete-prefix IDs before requiring manual ledger investigation.
    ledger = None if torn_trailing_record else JobLedger(ledger_path, endpoint_id, run_id)
    base = endpoint_base(endpoint_id)
    for job_id in summary["unreconciled_job_ids"]:
        request_sha256 = summary["jobs"][job_id]["request_sha256"]
        try:
            result = _json_request(
                "GET",
                f"{base}/status/{job_id}",
                api_key=api_key,
                timeout=timeout,
            )
        except RuntimeError:
            _cancel_and_confirm(
                base,
                job_id,
                api_key,
                ledger=ledger,
                request_sha256=request_sha256,
                timeout=timeout,
                observed_status="RECONCILE_POLL_ERROR",
            )
            continue
        status = str(result.get("status", "")).upper()
        if status in TERMINAL_STATUSES:
            if ledger is not None:
                try:
                    ledger.terminal(job_id, request_sha256, status, timeout)
                except OSError as error:
                    raise RuntimeError(
                        f"observed remote terminal status {status} for job {job_id}, "
                        "but local ledger persistence failed"
                    ) from error
            continue
        _cancel_and_confirm(
            base,
            job_id,
            api_key,
            ledger=ledger,
            request_sha256=request_sha256,
            timeout=timeout,
            observed_status=status or "RECONCILE_PENDING",
        )
    if summary["ambiguous_submissions"]:
        raise RuntimeError("job ledger has ambiguous submission(s); do not submit another batch")
    if torn_trailing_record:
        raise RuntimeError(
            "job ledger has a torn trailing record; valid-prefix jobs were reconciled where possible, "
            "but manual investigation is required"
        )
    resolved = ledger_summary(ledger_path, endpoint_id=endpoint_id)
    if not resolved["all_jobs_terminal"]:
        raise RuntimeError("job ledger still has unreconciled jobs after cancellation")
    return resolved


def _run_completion(
    endpoint_id: str,
    api_key: str,
    request_body: dict[str, Any],
    *,
    timeout: float = 300.0,
    ledger: JobLedger | None = None,
) -> dict[str, Any]:
    base = endpoint_base(endpoint_id)
    started = time.monotonic()
    try:
        result = _json_request(
            "POST",
            f"{base}/run",
            api_key=api_key,
            payload=make_run_payload("/v1/chat/completions", request_body),
            timeout=min(30.0, timeout),
        )
    except RuntimeError as error:
        if ledger is not None:
            try:
                ledger.submission_ambiguous(request_body, type(error).__name__, timeout)
            except OSError as ledger_error:
                raise RuntimeError(
                    "Runpod submission is ambiguous and local ledger persistence failed; "
                    "do not retry the batch"
                ) from ledger_error
        raise RuntimeError("Runpod submission ambiguous; no job id was received, so do not retry the batch") from error
    status = str(result.get("status", "")).upper()
    job_id = result.get("id")
    if not job_id:
        if ledger is not None:
            try:
                ledger.submission_ambiguous(request_body, status or "missing_job_id", timeout)
            except OSError as ledger_error:
                raise RuntimeError(
                    "Runpod response has no job id and local ledger persistence failed; "
                    "do not retry the batch"
                ) from ledger_error
        raise RuntimeError("Runpod response lacks a job id; do not retry the batch")
    request_sha256 = _request_sha256(request_body)
    if ledger is not None:
        try:
            request_sha256 = ledger.submitted(str(job_id), request_body, status, timeout)
        except OSError as ledger_error:
            try:
                terminal = _cancel_and_confirm(
                    base,
                    str(job_id),
                    api_key,
                    ledger=None,
                    request_sha256=request_sha256,
                    timeout=timeout,
                    observed_status=status or "LEDGER_WRITE_FAILURE",
                )
                outcome = f"observed remote terminal status {terminal}"
            except RuntimeError as cancellation_error:
                outcome = f"cancellation unverified: {cancellation_error}"
            raise RuntimeError(
                f"Runpod returned job {job_id}, but local ledger persistence failed; {outcome}; "
                "do not submit another batch"
            ) from ledger_error
    while status not in {"COMPLETED", "FAILED", "CANCELLED", "TIMED_OUT"}:
        remaining = timeout - (time.monotonic() - started)
        if remaining <= 0:
            terminal = _cancel_and_confirm(
                base,
                str(job_id),
                api_key,
                ledger=ledger,
                request_sha256=request_sha256,
                timeout=timeout,
                observed_status=status,
            )
            raise RuntimeError(f"Runpod proxy timeout; observed remote terminal status {terminal} for job {job_id}")
        try:
            time.sleep(min(0.5, remaining))
            result = _json_request(
                "GET",
                f"{base}/status/{job_id}",
                api_key=api_key,
                timeout=min(30.0, remaining),
            )
        except RuntimeError as error:
            terminal = _cancel_and_confirm(
                base,
                str(job_id),
                api_key,
                ledger=ledger,
                request_sha256=request_sha256,
                timeout=timeout,
                observed_status="POLL_ERROR",
            )
            raise RuntimeError(
                f"Runpod status poll failed for job {job_id}; observed remote terminal status {terminal}"
            ) from error
        status = str(result.get("status", "")).upper()
    if ledger is not None:
        try:
            ledger.terminal(str(job_id), request_sha256, status, timeout)
        except OSError as error:
            raise RuntimeError(
                f"observed remote terminal status {status} for job {job_id}, "
                "but local ledger persistence failed"
            ) from error
    if status != "COMPLETED":
        detail = result.get("error") or result.get("output") or "no worker detail"
        raise RuntimeError(f"Runpod job {status.lower()}: {str(detail)[:500]}")
    return unwrap_completed(result)


def run_completion(
    endpoint_id: str,
    api_key: str,
    request_body: dict[str, Any],
    *,
    timeout: float = 300.0,
    ledger: JobLedger | None = None,
) -> dict[str, Any]:
    """Run one completion, serializing and fail-closing when a ledger is supplied."""

    if ledger is None:
        return _run_completion(endpoint_id, api_key, request_body, timeout=timeout)
    with ledger.exclusive_submission():
        return _run_completion(endpoint_id, api_key, request_body, timeout=timeout, ledger=ledger)


def _error_payload(message: str) -> dict[str, Any]:
    return {"error": {"message": message, "type": "runpod_proxy_error"}}


class _Handler(BaseHTTPRequestHandler):
    server: "_ProxyServer"

    def _write(self, code: int, value: dict[str, Any]) -> None:
        raw = json.dumps(value, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/health":
            self._write(200, {"status": "ok"})
            return
        if self.path.rstrip("/") == "/v1/models":
            self._write(
                200,
                {
                    "object": "list",
                    "data": [{"id": self.server.model_id, "object": "model"}],
                },
            )
            return
        self._write(404, _error_payload("not found"))

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if not parsed.path.endswith("/chat/completions"):
            self._write(404, _error_payload("only chat completions are supported"))
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            body = json.loads(self.rfile.read(length))
            if not isinstance(body, dict):
                raise ValueError("request body must be a JSON object")
            result = run_completion(
                self.server.endpoint_id,
                self.server.api_key,
                body,
                timeout=self.server.timeout,
                ledger=self.server.job_ledger,
            )
        except (ValueError, RuntimeError, json.JSONDecodeError) as error:
            self._write(502, _error_payload(str(error)[:500]))
            return
        self._write(200, result)

    def log_message(self, format: str, *args: Any) -> None:
        return


class _ProxyServer(ThreadingHTTPServer):
    def __init__(
        self,
        address: tuple[str, int],
        *,
        endpoint_id: str,
        api_key: str,
        model_id: str,
        timeout: float,
        job_ledger: Path,
        run_id: str,
    ) -> None:
        super().__init__(address, _Handler)
        self.endpoint_id = endpoint_id
        self.api_key = api_key
        self.model_id = model_id
        self.timeout = timeout
        self.job_ledger = JobLedger(job_ledger, endpoint_id, run_id)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--endpoint-id", required=True)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--timeout", type=float, default=300.0)
    parser.add_argument("--model-id", default="qwen/qwen3-8b")
    parser.add_argument("--api-key-env", default="RUNPOD_API_KEY")
    parser.add_argument("--job-ledger", type=Path, default=Path("qa/runpod_proxy_jobs.jsonl"))
    parser.add_argument("--run-id", default="unspecified")
    args = parser.parse_args()
    api_key = os.environ.get(args.api_key_env)
    if not api_key:
        raise SystemExit(f"missing {args.api_key_env}")
    server = _ProxyServer(
        (args.host, args.port),
        endpoint_id=args.endpoint_id,
        api_key=api_key,
        model_id=args.model_id,
        timeout=args.timeout,
        job_ledger=args.job_ledger,
        run_id=args.run_id,
    )
    print(f"http://{args.host}:{server.server_port}/v1", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
