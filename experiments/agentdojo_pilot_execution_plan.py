"""Freeze a no-network, no-model execution plan for the AgentDojo pilot.

The plan is a preregistration/preflight artifact, not an executor.  In
particular, it records that the current generic runner cannot execute a
benign twin safely because it always enables InjecAgent.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

try:
    from experiments.agentdojo_pilot_manifest import load_manifest as load_pilot_manifest
except ModuleNotFoundError:  # direct ``python experiments/*.py`` support
    from agentdojo_pilot_manifest import load_manifest as load_pilot_manifest


ROOT = Path(__file__).resolve().parents[1]
PILOT_MANIFEST = ROOT / "experiments" / "fixtures" / "agentdojo_pilot_case_manifest_v1.json"
BENCHMARK_MANIFEST = ROOT / "experiments" / "independent_benchmark_manifest.json"
DEFAULT_OUTPUT = ROOT / "experiments" / "fixtures" / "agentdojo_pilot_execution_plan_v1.json"
TRACKS = ("baseline", "attested")
ARMS = ("attack", "benign_twin")


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must be a JSON object")
    return value


def _bindings() -> dict[str, Any]:
    benchmark = _load_json(BENCHMARK_MANIFEST).get("benchmarks", {}).get("agentdojo")
    if not isinstance(benchmark, dict):
        raise ValueError("independent benchmark manifest lacks AgentDojo")
    environment = benchmark.get("environment") or {}
    contract = benchmark.get("contract_migration") or {}
    required = ("repository", "commit", "benchmark_version", "suite", "attack")
    if any(not isinstance(benchmark.get(name), str) or not benchmark[name] for name in required):
        raise ValueError("AgentDojo benchmark binding is incomplete")
    if not isinstance(environment.get("lockfile"), str) or not isinstance(environment.get("lockfile_sha256"), str):
        raise ValueError("AgentDojo lockfile binding is incomplete")
    if not isinstance(contract.get("manifest"), str) or not isinstance(contract.get("manifest_sha256"), str):
        raise ValueError("AgentDojo contract binding is incomplete")
    return {
        "repository": benchmark["repository"],
        "commit": benchmark["commit"],
        "benchmark_version": benchmark["benchmark_version"],
        "suite": benchmark["suite"],
        "attack": benchmark["attack"],
        "lockfile": environment["lockfile"],
        "lockfile_sha256": environment["lockfile_sha256"],
        "contract_migration_manifest": contract["manifest"],
        "contract_migration_manifest_sha256": contract["manifest_sha256"],
        "contract_migration_witness_required": True,
    }


def _episode(row: dict[str, Any], arm: str, track: str, order: int) -> dict[str, Any]:
    if arm == "attack":
        subject_id = row["case_id"]
        oracle = {**row["harmful_effect_oracle"], "evaluated": False, "outcome": None}
        injection = {
            "mode": "injecagent",
            "injection_task_id": row["injection_task_id"],
            "carrier_id": row["carrier_id"],
            "injection_goal_sha256": row["injection_goal_sha256"],
            "attack_text_sha256": row["attack_text_sha256"],
        }
        executor_status = "not_run; a manifest-bound attack driver is still required"
        nominal_upstream_task_episodes = 2
    elif arm == "benign_twin":
        subject_id = row["benign_twin_id"]
        oracle = {
            "kind": "agentdojo_user_task_utility",
            "user_task_id": row["user_task_id"],
            "guard_dependency": "none; upstream user-task utility oracle",
            "evaluated": False,
            "outcome": None,
        }
        injection = {"mode": "none", "injection_task_id": None, "carrier_id": row["carrier_id"]}
        executor_status = (
            "blocked; current generic runner always enables InjecAgent, so a benign twin "
            "must not be approximated by omitting only --injection-task"
        )
        nominal_upstream_task_episodes = 1
    else:  # pragma: no cover - constants are validated below
        raise ValueError(f"unsupported plan arm {arm!r}")
    return {
        "execution_order": order,
        "episode_id": f"{row['case_id']}:{arm}:{track}",
        "result_status": "not_run",
        "pilot_case_id": row["case_id"],
        "episode_subject_id": subject_id,
        "arm": arm,
        "track": track,
        "user_task_id": row["user_task_id"],
        "carrier": {"id": row["carrier_id"], "surface": row["carrier_surface"]},
        "migration_family": row["migration_family"],
        "configuration": {
            "reviewed_name_only_contract_migration": "required_for_both_tracks",
            "attestation_adapter": "not_loaded" if track == "baseline" else "required",
            "attested_policy": (
                "not_applicable" if track == "baseline" else "unresolved; integration-only wildcard allowlist is prohibited"
            ),
        },
        "injection": injection,
        "outcome_oracle": oracle,
        "outcome_scoring_rule": (
            "only a completed, schema-valid AgentDojo trace may be scored; "
            "timeout, error, or invalid trace remains not_scored"
        ),
        "reset_before_episode": "required; initial-state hash is unobserved until execution",
        "nominal_upstream_task_episodes": nominal_upstream_task_episodes,
        "required_trace_metadata": [
            "serialized_request_sha256",
            "model_id_and_revision",
            "endpoint_release_id",
            "initial_state_sha256",
            "redacted_trace",
            "contract_migration_witness",
            "outcome_oracle_result",
        ],
        "unobserved_runtime_facts": [
            "model_revision",
            "endpoint_release_id",
            "initial_state_sha256",
            "response",
            "outcome_oracle_result",
        ],
        "retry_policy": "no automatic retry; failure requires manual review before any new submission",
        "executor_status": executor_status,
    }


def build_plan() -> dict[str, Any]:
    """Build a deterministic plan only; this function makes no external calls."""

    pilot = load_pilot_manifest(PILOT_MANIFEST)
    rows = {row["case_id"]: row for row in pilot["population"]["rows"]}
    selected = pilot["feasibility_selection"]["selected_case_ids"]
    episodes: list[dict[str, Any]] = []
    for case_id in selected:
        row = rows.get(case_id)
        if row is None or row["execution_eligibility"] != "standard_injecagent_single_carrier":
            raise ValueError("selected pilot case is not eligible for the declared single-carrier plan")
        for arm in ARMS:
            for track in TRACKS:
                episodes.append(_episode(row, arm, track, len(episodes) + 1))
    bindings = _bindings()
    if pilot["source"]["commit"] != bindings["commit"] or pilot["source"]["benchmark_version"] != bindings["benchmark_version"]:
        raise ValueError("pilot and benchmark source bindings disagree")
    if pilot["source"]["contract_migration_manifest_sha256"].upper() != bindings[
        "contract_migration_manifest_sha256"
    ].upper():
        raise ValueError("pilot and benchmark contract bindings disagree")
    return {
        "schema_version": "agentdojo-pilot-execution-plan/v1",
        "recorded_on": "2026-09-28",
        "result_status": "preflight_only_not_run",
        "purpose": "Pinned, outcome-blind no-billable execution plan; not a benchmark result or an execution authorization.",
        "source": {
            "pilot_case_manifest": str(PILOT_MANIFEST.relative_to(ROOT)).replace("\\", "/"),
            "pilot_case_manifest_sha256": _file_sha256(PILOT_MANIFEST),
            "agentdojo": bindings,
        },
        "execution_policy": {
            "network_or_model_calls_allowed": False,
            "automatic_retry_allowed": False,
            "external_execution_authorization": "not_granted_by_this_artifact",
            "ordering": "fixed case-selection order, then attack/benign twin and baseline/attested; not counterbalancing",
        },
        "observed_execution_counters": {
            "provider_requests": 0,
            "remote_jobs": 0,
            "tool_dispatches": 0,
            "cost_usd": 0.0,
        },
        "selection": {
            "selected_case_ids": selected,
            "attack_track_invocations": pilot["feasibility_selection"]["planned_attack_track_invocations"],
            "benign_twin_invocations": pilot["feasibility_selection"]["planned_benign_twin_invocations"],
            "total_planned_invocations": len(episodes),
            "nominal_upstream_task_episodes": sum(row["nominal_upstream_task_episodes"] for row in episodes),
            "cardinality_note": (
                "each InjecAgent invocation includes a standalone injection-task utility episode plus "
                "the injected user episode; request/token counts remain unobserved and variable"
            ),
        },
        "episodes": episodes,
        "non_claims": [
            "No endpoint, credential, proxy, model, tool or sandbox execution occurred while creating this plan.",
            "The plan does not establish LLM efficacy, ASR/AFER, guard superiority, a v0/v1 effect, or a provider cost cap.",
            "The three-case feasibility subset and its correlated source population are not an independent statistical sample.",
        ],
    }


def validate_plan(plan: dict[str, Any]) -> dict[str, Any]:
    expected = build_plan()
    if plan.get("schema_version") != "agentdojo-pilot-execution-plan/v1":
        raise ValueError("unsupported pilot execution plan schema")
    if plan.get("result_status") != "preflight_only_not_run":
        raise ValueError("pilot execution plan must remain preflight_only_not_run")
    if _canonical_bytes(plan) != _canonical_bytes(expected):
        raise ValueError("pilot execution plan differs from current pinned preregistration inputs")
    return {
        "selected_case_count": len(plan["selection"]["selected_case_ids"]),
        "planned_invocation_count": len(plan["episodes"]),
        "attack_invocation_count": sum(row["arm"] == "attack" for row in plan["episodes"]),
        "benign_twin_invocation_count": sum(row["arm"] == "benign_twin" for row in plan["episodes"]),
        "result_status": plan["result_status"],
    }


def load_plan(path: Path = DEFAULT_OUTPUT) -> dict[str, Any]:
    plan = _load_json(path)
    validate_plan(plan)
    return plan


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--verify", action="store_true", help="verify an existing preflight-only plan")
    args = parser.parse_args()
    output = args.output.resolve()
    if args.verify:
        report = validate_plan(load_plan(output))
    else:
        plan = build_plan()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        report = validate_plan(plan)
    print(json.dumps(report, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
