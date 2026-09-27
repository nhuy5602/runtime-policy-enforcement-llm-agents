"""Run one reproducible AgentDojo baseline/attested smoke through Runpod.

The caller injects RUNPOD_API_KEY through the environment. The script starts a
dependency-free local /runsync bridge and executes the same pinned
user/injection task once without and once with the attestation adapter.  The
key is never printed or written to the result manifest.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
def resolve_runpod_key() -> str:
    """Read the caller-injected key without touching user configuration."""

    value = os.environ.get("RUNPOD_API_KEY", "").strip()
    if not value:
        raise RuntimeError("RUNPOD_API_KEY is missing or empty")
    return value


def wait_for_proxy(url: str, timeout: float) -> None:
    deadline = time.monotonic() + timeout
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=3) as response:
                if response.status == 200:
                    return
        except (urllib.error.URLError, TimeoutError) as error:
            last_error = error
        time.sleep(0.5)
    raise RuntimeError(f"local proxy did not become ready: {last_error!r}")


def run_track(
    *,
    track: str,
    output_dir: Path,
    log_path: Path,
    env: dict[str, str],
    source_root: Path,
    user_task: str,
    injection_task: str,
) -> int:
    command = [
        sys.executable,
        str(ROOT / "experiments" / "independent_benchmark_runner.py"),
        "--benchmark",
        "agentdojo",
        "--track",
        track,
        "--run",
        "--source-root",
        str(source_root),
        "--user-task",
        user_task,
        "--injection-task",
        injection_task,
        "--output",
        str(output_dir),
    ]
    output_dir.mkdir(parents=True, exist_ok=True)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("w", encoding="utf-8") as log:
        completed = subprocess.run(
            command,
            cwd=ROOT,
            env=env,
            stdout=log,
            stderr=subprocess.STDOUT,
            check=False,
        )
    return completed.returncode


def main() -> int:
    # Windows cp1252 consoles cannot render Vietnamese paths in the manifest.
    # Keep the machine-readable result successful even when stdout is legacy.
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--endpoint-id", default="h5ec6v08cb8uc2")
    parser.add_argument("--model-id", default="qwen/qwen3-8b")
    parser.add_argument(
        "--source-root",
        type=Path,
        help="directory containing the pinned agentdojo clone; required for a locked run",
    )
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--proxy-ready-timeout", type=float, default=60.0)
    parser.add_argument("--user-task", default="user_task_0")
    parser.add_argument("--injection-task", default="injection_task_0")
    parser.add_argument(
        "--run-label",
        default="20260926",
        help="suffix for output/log paths so policy variants do not overwrite one another",
    )
    parser.add_argument(
        "--attested-allowlist",
        default="*",
        help="comma-separated adapter allowlist; '*' is an integration-only wildcard",
    )
    parser.add_argument(
        "--approval-tools",
        default="",
        help="comma-separated tools that require explicit approval in the attested track",
    )
    parser.add_argument(
        "--approve",
        action="store_true",
        help="set AGENTDOJO_ATTESTATION_APPROVE=1 for the attested track",
    )
    parser.add_argument(
        "--skip-baseline",
        action="store_true",
        help="reuse the existing baseline artifact and run only a new attested policy variant",
    )
    parser.add_argument(
        "--manifest-output",
        type=Path,
        default=Path("qa/agentdojo_paired_smoke_20260926.json"),
    )
    args = parser.parse_args()

    if args.source_root is None:
        raise SystemExit("blocked: --source-root containing the pinned agentdojo clone is required")
    source_root = args.source_root.resolve()
    if not (source_root / "agentdojo").is_dir():
        raise SystemExit(f"blocked: expected pinned agentdojo clone under {source_root}")

    manifest_path = (ROOT / args.manifest_output).resolve()
    baseline_dir = ROOT / "experiments" / "independent_runs" / f"agentdojo_smoke_baseline_{args.run_label}"
    attested_dir = ROOT / "experiments" / "independent_runs" / f"agentdojo_smoke_attested_{args.run_label}"
    baseline_log = ROOT / "qa" / f"agentdojo_smoke_baseline_{args.run_label}.log"
    attested_log = ROOT / "qa" / f"agentdojo_smoke_attested_{args.run_label}.log"
    proxy_stdout = ROOT / "qa" / f"runpod_proxy_h5ec_smoke_{args.run_label}.stdout.log"
    proxy_stderr = ROOT / "qa" / f"runpod_proxy_h5ec_smoke_{args.run_label}.stderr.log"

    key = resolve_runpod_key()
    env = os.environ.copy()
    env.update(
        {
            "RUNPOD_API_KEY": key,
            "OPENAI_COMPATIBLE_BASE_URL": f"http://127.0.0.1:{args.port}/v1",
            "OPENAI_COMPATIBLE_API_KEY": "local-proxy",
            "PYTHONUTF8": "1",
            "PYTHONIOENCODING": "utf-8",
        }
    )
    proxy_command = [
        sys.executable,
        "-u",
        str(ROOT / "experiments" / "runpod_openai_proxy.py"),
        "--endpoint-id",
        args.endpoint_id,
        "--port",
        str(args.port),
        "--timeout",
        "1800",
        "--model-id",
        args.model_id,
    ]
    proxy_stdout.parent.mkdir(parents=True, exist_ok=True)
    proxy = subprocess.Popen(
        proxy_command,
        cwd=ROOT,
        env=env,
        stdout=proxy_stdout.open("w", encoding="utf-8"),
        stderr=proxy_stderr.open("w", encoding="utf-8"),
    )
    baseline_code: int | None = None
    attested_code: int | None = None
    error: str | None = None
    try:
        wait_for_proxy(f"http://127.0.0.1:{args.port}/health", args.proxy_ready_timeout)
        baseline_env = env.copy()
        for name in (
            "AGENTDOJO_ATTESTATION_ALLOWLIST",
            "AGENTDOJO_ATTESTATION_APPROVAL_TOOLS",
            "AGENTDOJO_ATTESTATION_APPROVE",
            "AGENTDOJO_ATTESTATION_AUDIT_PATH",
        ):
            baseline_env.pop(name, None)
        if args.skip_baseline:
            baseline_code = 0
        else:
            baseline_code = run_track(
                track="baseline",
                output_dir=baseline_dir,
                log_path=baseline_log,
                env=baseline_env,
                source_root=source_root,
                user_task=args.user_task,
                injection_task=args.injection_task,
            )

        attested_env = env.copy()
        attested_env["AGENTDOJO_ATTESTATION_ALLOWLIST"] = args.attested_allowlist
        if args.approval_tools:
            attested_env["AGENTDOJO_ATTESTATION_APPROVAL_TOOLS"] = args.approval_tools
        else:
            attested_env.pop("AGENTDOJO_ATTESTATION_APPROVAL_TOOLS", None)
        if args.approve:
            attested_env["AGENTDOJO_ATTESTATION_APPROVE"] = "1"
        else:
            attested_env.pop("AGENTDOJO_ATTESTATION_APPROVE", None)
        attested_env["AGENTDOJO_ATTESTATION_AUDIT_PATH"] = str(
            attested_dir / "adapter_audit.json"
        )
        attested_code = run_track(
            track="attested",
            output_dir=attested_dir,
            log_path=attested_log,
            env=attested_env,
            source_root=source_root,
            user_task=args.user_task,
            injection_task=args.injection_task,
        )
    except Exception as exc:  # preserve a machine-readable short report
        error = f"{type(exc).__name__}: {exc}"
    finally:
        if proxy.poll() is None:
            proxy.terminate()
            try:
                proxy.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proxy.kill()
                proxy.wait(timeout=10)

    report: dict[str, Any] = {
        "schema_version": "agentdojo-paired-smoke/v1",
        "endpoint_id": args.endpoint_id,
        "model_id": args.model_id,
        "source_root": str(source_root),
        "user_task": args.user_task,
        "injection_task": args.injection_task,
        "same_model_and_tasks": True,
        "baseline": {
            "track": "baseline",
            "exit_code": baseline_code,
            "output_dir": str(baseline_dir),
            "log": str(baseline_log),
        },
        "attested": {
            "track": "attested",
            "allowlist": args.attested_allowlist,
            "approval_tools": args.approval_tools,
            "approval_granted": args.approve,
            "exit_code": attested_code,
            "output_dir": str(attested_dir),
            "log": str(attested_log),
        },
        "proxy": {
            "transport": "runpod_runsync",
            "local_base_url": f"http://127.0.0.1:{args.port}/v1",
            "stdout": str(proxy_stdout),
            "stderr": str(proxy_stderr),
        },
        "error": error,
        "result_status": (
            "completed"
            if error is None and baseline_code == 0 and attested_code == 0
            else "failed_or_incomplete"
        ),
        "baseline_reused": args.skip_baseline,
        "non_claims": [
            "A successful process exit is not itself a security or efficacy score.",
            "This smoke covers one paired task only and is not a Q2 result.",
        ],
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["result_status"] == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
