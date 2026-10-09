"""Canonical fixed-denominator driver for the prospective AgentDojo v2 plan.

This module owns scheduling and artifact shape.  Live execution is delegated to
the fresh-process capture bridge, which is enabled only by an explicit,
billable-run confirmation and remains limited to the four-episode pilot.
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import sys
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

try:
    from experiments.agentdojo_paired_v2_execution_manifest import DEFAULT_OUTPUT as DEFAULT_MANIFEST
    from experiments.agentdojo_paired_v2_execution_manifest import load_manifest, validate_manifest
    from experiments.agentdojo_paired_v2_result_bundle import (
        build_result_bundle_template,
        validate_and_summarize_bundle,
    )
except ModuleNotFoundError:  # direct ``python experiments/*.py`` support
    from agentdojo_paired_v2_execution_manifest import DEFAULT_OUTPUT as DEFAULT_MANIFEST
    from agentdojo_paired_v2_execution_manifest import load_manifest, validate_manifest
    from agentdojo_paired_v2_result_bundle import build_result_bundle_template, validate_and_summarize_bundle


ROOT = Path(__file__).resolve().parents[1]
PILOT_BUDGET_USD = "10.00"
DRIVER_CLAIM_TIER = (
    "integration/pilot orchestration only; not defense efficacy, population inference, "
    "or Q2-readiness evidence"
)
Executor = Callable[[dict[str, Any]], Mapping[str, Any] | None]
DEFAULT_CAPTURE_SOURCE = ROOT / "tmp" / "agentdojo-source"
DEFAULT_CAPTURE_API_KEY_ENV = "AGENTDOJO_CAPTURE_API_KEY"
CANONICAL_CAPTURE_MANIFEST = DEFAULT_MANIFEST.resolve()


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _metadata(plan: Mapping[str, Any], manifest_sha256: str, run_id: str) -> dict[str, Any]:
    """Return only immutable plan metadata, never invented live evidence."""

    contract = plan["contract"]
    metadata = {
        "episode_id": plan["episode_id"],
        "pair_id": plan["pair_id"],
        "case_id": plan["case_id"],
        "stratum_id": plan["stratum_id"],
        "user_task_id": plan["user_task_id"],
        "arm": plan["arm"],
        "defense_id": plan["defense_id"],
        "defense_configuration_sha256": plan["defense_configuration_sha256"],
        "policy_manifest_sha256": plan["policy_manifest_sha256"],
        "model_configuration_id": plan["model_configuration_id"],
        "seed": plan["seed"],
        "contract_version": contract["version"],
        "arm_binding_sha256": plan["arm_binding_sha256"],
        "expected_pre_state_sha256": plan["expected_pre_state_sha256"],
        "effect_oracle_contract_sha256": plan["effect_oracle_contract_sha256"],
        "default_control_contract_sha256": plan["default_control_contract_sha256"],
        "trace_normalization_contract_sha256": plan["trace_normalization_contract_sha256"],
        "manifest_sha256": manifest_sha256,
        "attempt_index": 1,
        "automatic_retry": False,
        "run_id": run_id,
    }
    if "source_cluster_id" in plan:
        metadata["source_cluster_id"] = plan["source_cluster_id"]
    return metadata


def _not_run_record(
    plan: Mapping[str, Any], manifest_sha256: str, run_id: str, reason: str
) -> dict[str, Any]:
    return {
        **_metadata(plan, manifest_sha256, run_id),
        "result_status": "not_run",
        "not_run_reason": reason,
    }


def _executor_record(
    plan: Mapping[str, Any],
    manifest_sha256: str,
    run_id: str,
    value: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Accept only executor-supplied completed evidence bound to this plan."""

    if value is None:
        return _not_run_record(plan, manifest_sha256, run_id, "executor_returned_no_record")
    record = dict(value)
    if record.get("result_status") != "completed":
        return _not_run_record(plan, manifest_sha256, run_id, "executor_returned_noncompleted_record")

    metadata = _metadata(plan, manifest_sha256, run_id)
    for field, expected in metadata.items():
        if field in record and record[field] != expected:
            return _not_run_record(plan, manifest_sha256, run_id, f"executor_metadata_mismatch:{field}")

    # These values are immutable scheduling data, not observations.  The
    # executor remains solely responsible for all live evidence required by
    # the bundle validator.
    return {**record, **metadata, "result_status": "completed"}


def budgeted_pilot_pair_ids(manifest: Mapping[str, Any]) -> set[str]:
    """Select one outcome-blind pair per arm for the hard four-episode pilot."""

    by_arm: dict[str, set[str]] = {}
    for plan in manifest["episodes"]:
        by_arm.setdefault(str(plan["arm"]), set()).add(str(plan["pair_id"]))
    selected: set[str] = set()
    for arm in ("attack", "no_injecagent_default_control"):
        candidates = sorted(by_arm.get(arm, ()))
        if not candidates:
            raise ValueError(f"manifest has no pair for pilot arm {arm!r}")
        selected.add(candidates[0])
    return selected


def _capture_executor(
    *,
    source_root: Path,
    python_executable: Path,
    base_url: str,
    api_key: str,
    model: str,
    run_id: str,
    timeout: float,
) -> Executor:
    from experiments.agentdojo_paired_v2_capture_bridge import run_episode

    halted = False

    def execute(plan: dict[str, Any]) -> Mapping[str, Any]:
        nonlocal halted
        if halted:
            raise RuntimeError("capture_halted_after_first_error")
        try:
            return run_episode(
                plan,
                source_root=source_root,
                python_executable=python_executable,
                base_url=base_url,
                api_key=api_key,
                model=model,
                run_id=run_id,
                timeout=timeout,
            )
        except Exception:
            # No paid retry or replacement after a bridge failure.  The driver
            # still emits fixed-denominator not_run rows for the remaining
            # plans, but this closure never reaches the provider again.
            halted = True
            raise

    return execute


def run_manifest(
    manifest: dict[str, Any],
    executor: Executor | None,
    *,
    run_id: str,
    dry_run: bool = False,
    source: Path | None = None,
    selected_pair_ids: set[str] | None = None,
    paid_execution_authorized: bool = False,
) -> dict[str, dict[str, Any]]:
    """Run every frozen episode once and return its bundle plus validation report.

    ``executor`` is intentionally a tiny injected callable for offline tests
    and a future pinned AgentDojo capture bridge.  It receives a deep copy of
    one frozen episode and must return a complete evidence record to claim
    ``completed``.  ``dry_run`` skips the executor completely. Exceptions and
    absent records become fixed-denominator ``not_run`` rows; the driver never
    synthesizes completion evidence.
    """

    if not _text(run_id):
        raise ValueError("run_id must be a non-empty string")
    validate_manifest(manifest)
    bundle = build_result_bundle_template(manifest)
    digest = str(bundle["manifest_sha256"])

    records: list[dict[str, Any]] = []
    for plan in manifest["episodes"]:
        if dry_run:
            records.append(_not_run_record(plan, digest, run_id, "dry_run"))
            continue
        if selected_pair_ids is not None and plan["pair_id"] not in selected_pair_ids:
            records.append(_not_run_record(plan, digest, run_id, "pilot_pair_not_selected"))
            continue
        if executor is None:
            records.append(_not_run_record(plan, digest, run_id, "real_capture_bridge_not_supplied"))
            continue
        try:
            value = executor(copy.deepcopy(plan))
        except Exception as error:
            records.append(
                _not_run_record(plan, digest, run_id, f"executor_error:{type(error).__name__}")
            )
            continue
        records.append(_executor_record(plan, digest, run_id, value))

    bundle["episodes"] = records
    if dry_run:
        bundle["result_status"] = "integration_pilot_dry_run"
    elif executor is None:
        bundle["result_status"] = "blocked_capture_bridge_missing"
    else:
        bundle["result_status"] = "integration_pilot_executor_records"
    bundle["driver_claim_tier"] = DRIVER_CLAIM_TIER
    bundle["pilot_budget"] = {
        "authorized_total_usd": PILOT_BUDGET_USD,
        "execution_envelope_usd": "8.00",
        "reserve_usd": "2.00",
        "provider_enforced_dollar_cap": False,
        "paid_execution_authorized": paid_execution_authorized,
        "execution_budget": manifest["design"]["execution_budget"],
        "enforcement": (
            "four-episode capture filter, no automatic retry, and stop-after-first-bridge-error; "
            "fresh child aborts before the next provider/tool call at the preregistered per-episode caps; "
            "Runpod billing remains provider-side and is not a hard dollar ceiling"
        ),
    }
    bundle["non_claims"] = [
        *bundle.get("non_claims", []),
        "The driver does not convert a runner endpoint Boolean into a scientific outcome.",
        "The four-episode pilot is integration evidence only and cannot support Q2 efficacy claims.",
        "Dispatch provenance is currently retained as a digest/count commitment only; "
        "a per-dispatch redacted commitment is required before any security or utility efficacy claim.",
    ]
    report = validate_and_summarize_bundle(bundle, manifest=manifest, source=source)
    return {"bundle": bundle, "report": report}


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--bundle-output", type=Path, required=True)
    parser.add_argument("--report-output", type=Path)
    parser.add_argument("--run-id", required=True)
    parser.add_argument(
        "--capture-bridge",
        action="store_true",
        help="run the hard four-episode pilot through the fresh-process capture bridge",
    )
    parser.add_argument("--source-root", type=Path, default=DEFAULT_CAPTURE_SOURCE)
    parser.add_argument("--python-executable", type=Path)
    parser.add_argument("--base-url", default=os.environ.get("OPENAI_COMPATIBLE_BASE_URL"))
    parser.add_argument("--api-key-env", default=DEFAULT_CAPTURE_API_KEY_ENV)
    parser.add_argument("--model")
    parser.add_argument("--timeout", type=float, default=300.0)
    parser.add_argument(
        "--confirm-billable",
        action="store_true",
        help="required for capture, including local proxies; requests may incur charges",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="write a fixed-denominator, no-request integration/pilot artifact",
    )
    args = parser.parse_args(argv)

    manifest = load_manifest(args.manifest.resolve())
    executor: Executor | None = None
    source: Path | None = None
    selected_pair_ids: set[str] | None = None
    if args.capture_bridge and not args.dry_run:
        if args.manifest.resolve() != CANONICAL_CAPTURE_MANIFEST:
            parser.error(
                "--capture-bridge requires the canonical v2 manifest "
                f"{CANONICAL_CAPTURE_MANIFEST}"
            )
        if not args.base_url:
            parser.error("--capture-bridge requires --base-url or OPENAI_COMPATIBLE_BASE_URL")
        api_key = os.environ.get(args.api_key_env)
        if not api_key:
            parser.error(f"--capture-bridge requires API key environment variable {args.api_key_env}")
        if not args.confirm_billable:
            parser.error("--capture-bridge requires --confirm-billable, including when using a local Runpod proxy")
        source = args.source_root.resolve()
        python_executable = (
            args.python_executable.resolve()
            if args.python_executable
            else (source / ".venv31213" / "Scripts" / "python.exe")
        )
        if Path(sys.executable).resolve() != python_executable:
            parser.error(
                "capture parent and child must use the same pinned Python; run this driver with "
                f"{python_executable}"
            )
        model = args.model or manifest["model_configurations"][0]["model_id"]
        executor = _capture_executor(
            source_root=source,
            python_executable=python_executable,
            base_url=args.base_url,
            api_key=api_key,
            model=model,
            run_id=args.run_id,
            timeout=args.timeout,
        )
        selected_pair_ids = budgeted_pilot_pair_ids(manifest)
    result = run_manifest(
        manifest,
        executor,
        run_id=args.run_id,
        dry_run=args.dry_run,
        source=source,
        selected_pair_ids=selected_pair_ids,
        paid_execution_authorized=bool(args.capture_bridge and args.confirm_billable),
    )
    bundle = result["bundle"]
    report = result["report"]
    if selected_pair_ids is not None:
        bundle["pilot_selection"] = {
            "rule": "lexicographically first pair ID within each frozen arm",
            "pair_ids": sorted(selected_pair_ids),
            "episode_count": 4,
        }
    _write_json(args.bundle_output.resolve(), bundle)
    if args.report_output:
        _write_json(args.report_output.resolve(), report)
    print(json.dumps(report, ensure_ascii=False, indent=2))

    if args.dry_run or args.capture_bridge:
        if args.capture_bridge and not any(row.get("result_status") == "completed" for row in bundle["episodes"]):
            return 2
        return 0
    print(
        "blocked: no pinned AgentDojo capture bridge is supplied; no paid pilot was launched",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
