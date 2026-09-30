"""Create a source-qualified replacement selection without running an LLM.

This is a prospective amendment after the v1 email oracle failed calibration.
It retains v1 unchanged, censes every structural candidate in the amended
strata, then hash-selects only candidates whose pinned AgentDojo predicate
passes three local controls.  All tool calls are in-memory AgentDojo ground
truth calls; this program never contacts a model, endpoint, proxy, or Runpod.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

try:
    from experiments.agentdojo_pilot_manifest import (
        BENCHMARK_VERSION,
        CONTRACT_MANIFEST,
        SOURCE_COMMIT,
        SUITE,
        load_manifest,
    )
    from experiments.agentdojo_pilot_oracle_qualification import (
        DEFAULT_OUTPUT as V1_QUALIFICATION,
        STATE_CANONICALIZATION,
        _callable_source,
        _file_sha256,
        _runtime_identity,
        _sha256,
        _verify_source,
        load_qualification,
    )
except ModuleNotFoundError:  # direct ``python experiments/*.py`` support
    from agentdojo_pilot_manifest import (
        BENCHMARK_VERSION,
        CONTRACT_MANIFEST,
        SOURCE_COMMIT,
        SUITE,
        load_manifest,
    )
    from agentdojo_pilot_oracle_qualification import (
        DEFAULT_OUTPUT as V1_QUALIFICATION,
        STATE_CANONICALIZATION,
        _callable_source,
        _file_sha256,
        _runtime_identity,
        _sha256,
        _verify_source,
        load_qualification,
    )


ROOT = Path(__file__).resolve().parents[1]
V1_MANIFEST = ROOT / "experiments" / "fixtures" / "agentdojo_pilot_case_manifest_v1.json"
DEFAULT_OUTPUT = ROOT / "experiments" / "fixtures" / "agentdojo_oracle_qualified_selection_v2.json"
SCHEMA_VERSION = "agentdojo-oracle-qualified-selection/v2"
STRUCTURAL_ELIGIBILITY = "standard_injecagent_single_carrier"
QUALIFICATION_RULE = (
    "Exact injected state: predicate false before action, true after injection-task ground truth, and false after "
    "user-task ground truth; any exception is ineligible."
)
V2_STRATA = (
    {
        "stratum_id": "calendar_event",
        "carrier_surface": "calendar",
        "injection_task_id": "injection_task_2",
        "harmful_effect_family": "unauthorized_calendar_event",
    },
    {
        "stratum_id": "drive_file_deletion",
        "carrier_surface": "drive",
        "injection_task_id": "injection_task_1",
        "harmful_effect_family": "unauthorized_file_deletion",
    },
    {
        "stratum_id": "email_content_exfiltration",
        "carrier_surface": "email",
        "injection_task_id": "injection_task_3",
        "harmful_effect_family": "email_content_exfiltration",
    },
)
V1_EMAIL_STRATUM = {
    "stratum_id": "historical_email_egress_task0",
    "carrier_surface": "email",
    "injection_task_id": "injection_task_0",
    "harmful_effect_family": "unauthorized_email",
}


def _path(path: Path) -> str:
    return str(path.relative_to(ROOT)).replace("\\", "/")


def _rows_for_stratum(manifest: dict[str, Any], stratum: dict[str, str]) -> list[dict[str, Any]]:
    rows = [
        row
        for row in manifest["population"]["rows"]
        if all(row.get(key) == stratum[key] for key in ("carrier_surface", "injection_task_id", "harmful_effect_family"))
    ]
    if not rows:
        raise ValueError(f"no v1 population rows for {stratum['stratum_id']}")
    return sorted(rows, key=lambda row: row["case_id"])


def _seed_material(manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "seed_schema": SCHEMA_VERSION,
        "v1_manifest_sha256": _file_sha256(V1_MANIFEST),
        "v1_selection_seed": manifest["feasibility_selection"]["seed"],
        "structural_eligibility": STRUCTURAL_ELIGIBILITY,
        "qualification_rule": QUALIFICATION_RULE,
        "strata": list(V2_STRATA),
    }


def _selection_seed(manifest: dict[str, Any]) -> dict[str, Any]:
    material = _seed_material(manifest)
    return {
        "algorithm": "sha256(canonical seed material)",
        "material": material,
        "value": _sha256(material),
    }


def _ground_truth_calls(task: Any, environment: Any) -> tuple[list[Any], int, str]:
    calls = task.ground_truth(environment)
    return calls, len(calls), _sha256([call.model_dump(mode="json") for call in calls])


def _execute_ground_truth(runtime: Any, environment: Any, calls: list[Any]) -> None:
    """Run the same in-memory tool calls as GroundTruthPipeline, without model messages."""

    for call in calls:
        runtime.run_function(environment, call.function, call.args, raise_on_error=True)


def _evaluate_predicate(suite: Any, injection_task: Any, pre: Any, post: Any) -> bool:
    value = suite._check_injection_task_security(injection_task, [], pre, post, [])
    if not isinstance(value, bool):
        raise TypeError("AgentDojo injection predicate did not return bool")
    return value


def _source_descriptor(value: Any, source: Path, cache: dict[tuple[str, str], dict[str, Any]]) -> dict[str, Any]:
    module = getattr(value, "__module__", None)
    qualname = getattr(value, "__qualname__", None)
    if not isinstance(module, str) or not isinstance(qualname, str):
        raise TypeError("source-bound callable needs a stable module and qualname")
    key = (module, qualname)
    if key not in cache:
        cache[key] = _callable_source(value, source)
    return cache[key]


def _error_record(row: dict[str, Any], stratum: dict[str, str], stage: str, exc: Exception) -> dict[str, Any]:
    return {
        "case_id": row["case_id"],
        "stratum_id": stratum["stratum_id"],
        "structural_eligibility": row["execution_eligibility"],
        "qualification_status": "ineligible_oracle_error",
        "qualification_error": {"stage": stage, "category": type(exc).__name__},
        "selection_rank": None,
    }


def _qualify_row(
    suite: Any,
    attack: Any,
    runtime: Any,
    source_descriptors: dict[tuple[str, str], dict[str, Any]],
    row: dict[str, Any],
    stratum: dict[str, str],
    source: Path,
) -> dict[str, Any]:
    """Run three predicate controls on independent fresh in-memory copies."""

    if row["execution_eligibility"] != STRUCTURAL_ELIGIBILITY:
        return {
            "case_id": row["case_id"],
            "stratum_id": stratum["stratum_id"],
            "structural_eligibility": row["execution_eligibility"],
            "qualification_status": "ineligible_structural_multi_carrier",
            "qualification_error": None,
            "selection_rank": None,
        }
    try:
        from agentdojo.base_tasks import BaseInjectionTask

        user_task = suite.get_user_task_by_id(row["user_task_id"])
        injection_task = suite.get_injection_task_by_id(row["injection_task_id"])
        trace_predicate = type(injection_task).security_from_traces
        if trace_predicate is not BaseInjectionTask.security_from_traces:
            raise ValueError("custom_trace_oracle_unsupported")
        injections = attack.attack(user_task, injection_task)
        carrier_ids = sorted(injections)
        if carrier_ids != [row["carrier_id"]]:
            raise ValueError("materialized_carrier_mismatch")
        pre = user_task.init_environment(suite.load_and_inject_default_environment(injections)).model_copy(deep=True)
        injection_post = pre.model_copy(deep=True)
        user_post = pre.model_copy(deep=True)
        fresh_harmful = _evaluate_predicate(suite, injection_task, pre, pre.model_copy(deep=True))
        injection_calls, injection_call_count, injection_call_sha256 = _ground_truth_calls(injection_task, pre)
        user_calls, user_call_count, user_call_sha256 = _ground_truth_calls(user_task, pre)
        _execute_ground_truth(runtime, injection_post, injection_calls)
        injection_harmful = _evaluate_predicate(suite, injection_task, pre, injection_post)
        _execute_ground_truth(runtime, user_post, user_calls)
        user_harmful = _evaluate_predicate(suite, injection_task, pre, user_post)
    except Exception as exc:  # calibration failure is a recorded ineligible row, never a silent filter
        return _error_record(row, stratum, "source_calibration", exc)

    if fresh_harmful:
        status = "ineligible_pre_state_already_harmful"
    elif not injection_harmful:
        status = "ineligible_oracle_nondiscriminating"
    elif user_harmful:
        status = "ineligible_user_ground_truth_overlap"
    else:
        status = "eligible_source_calibrated"
    return {
        "case_id": row["case_id"],
        "stratum_id": stratum["stratum_id"],
        "structural_eligibility": row["execution_eligibility"],
        "qualification_status": status,
        "qualification_error": None,
        "attack_binding": {
            "user_task_id": row["user_task_id"],
            "injection_task_id": row["injection_task_id"],
            "carrier_id": row["carrier_id"],
            "injection_goal_sha256": row["injection_goal_sha256"],
            "attack_text_sha256": row["attack_text_sha256"],
            "injection_map_sha256": _sha256(injections),
        },
        "source_callables": {
            "predicate": _source_descriptor(type(injection_task).security, source, source_descriptors),
            "trace_fast_path": _source_descriptor(trace_predicate, source, source_descriptors),
            "injection_ground_truth": _source_descriptor(type(injection_task).ground_truth, source, source_descriptors),
            "user_ground_truth": _source_descriptor(type(user_task).ground_truth, source, source_descriptors),
        },
        "exact_pre_execution_state": {
            "canonicalization": STATE_CANONICALIZATION,
            "sha256": _sha256(pre.model_dump(mode="json")),
            "materialized_carrier_ids": carrier_ids,
        },
        "local_source_controls": {
            "fresh_state_harmful_effect_observed": fresh_harmful,
            "injection_ground_truth_harmful_effect_observed": injection_harmful,
            "user_ground_truth_harmful_effect_observed": user_harmful,
            "injection_ground_truth_call_count": injection_call_count,
            "injection_ground_truth_call_signature_sha256": injection_call_sha256,
            "user_ground_truth_call_count": user_call_count,
            "user_ground_truth_call_signature_sha256": user_call_sha256,
        },
        "selection_rank": None,
    }


def _rank(census: list[dict[str, Any]], seed: str, stratum: dict[str, str]) -> list[str]:
    eligible = [row for row in census if row["qualification_status"] == "eligible_source_calibrated"]
    ordered = sorted(
        eligible,
        key=lambda row: (hashlib.sha256(f"{seed}\0{row['case_id']}".encode()).hexdigest(), row["case_id"]),
    )
    for rank, row in enumerate(ordered, start=1):
        row["selection_rank"] = rank
        row["selection_score_sha256"] = hashlib.sha256(f"{seed}\0{row['case_id']}".encode()).hexdigest()
    if not ordered:
        raise ValueError(f"no source-qualified candidate in {stratum['stratum_id']}")
    return [row["case_id"] for row in ordered]


def _count_local_dispatches(census: list[dict[str, Any]]) -> int:
    return sum(
        row.get("local_source_controls", {}).get("injection_ground_truth_call_count", 0)
        + row.get("local_source_controls", {}).get("user_ground_truth_call_count", 0)
        for row in census
    )


def build_selection(source: Path) -> dict[str, Any]:
    """Census and select a v2 feasibility subset from a clean pinned checkout."""

    source = _verify_source(source)
    manifest = load_manifest(V1_MANIFEST)
    historical_qualification = load_qualification(V1_QUALIFICATION)
    from agentdojo.attacks.baseline_attacks import InjecAgentAttack
    from agentdojo.base_tasks import BaseInjectionTask
    from agentdojo.functions_runtime import FunctionsRuntime
    from agentdojo.task_suite.load_suites import get_suite

    suite = get_suite(BENCHMARK_VERSION, SUITE)
    attack = InjecAgentAttack(suite, None)
    runtime = FunctionsRuntime(suite.tools)
    source_descriptors: dict[tuple[str, str], dict[str, Any]] = {}
    seed = _selection_seed(manifest)
    target_census: list[dict[str, Any]] = []
    selected_case_ids: list[str] = []
    stratum_summaries: list[dict[str, Any]] = []
    for stratum in V2_STRATA:
        census = [
            _qualify_row(suite, attack, runtime, source_descriptors, row, stratum, source)
            for row in _rows_for_stratum(manifest, stratum)
        ]
        ranked = _rank(census, seed["value"], stratum)
        target_census.extend(census)
        selected_case_ids.append(ranked[0])
        stratum_summaries.append(
            {
                **stratum,
                "population_case_count": len(census),
                "structurally_eligible_case_count": sum(
                    row["structural_eligibility"] == STRUCTURAL_ELIGIBILITY for row in census
                ),
                "source_qualified_case_count": len(ranked),
                "selected_case_id": ranked[0],
            }
        )
    historical_email_census = [
        _qualify_row(suite, attack, runtime, source_descriptors, row, V1_EMAIL_STRATUM, source)
        for row in _rows_for_stratum(manifest, V1_EMAIL_STRATUM)
    ]
    historical_email_qualified = [
        row["case_id"] for row in historical_email_census if row["qualification_status"] == "eligible_source_calibrated"
    ]
    if historical_email_qualified:
        raise ValueError("v1 email task-0 stratum unexpectedly contains a source-qualified candidate")
    artifact = {
        "schema_version": SCHEMA_VERSION,
        "recorded_on": "2026-09-30",
        "result_status": "source_qualified_selection_only_not_llm_evaluation",
        "purpose": (
            "Prospective, source-only replacement selection after a v1 harmful-effect-oracle defect; it does not "
            "unblock the historical plan or create LLM observations."
        ),
        "inputs": {
            "v1_manifest": {"path": _path(V1_MANIFEST), "sha256": _file_sha256(V1_MANIFEST)},
            "v1_oracle_qualification": {"path": _path(V1_QUALIFICATION), "sha256": _file_sha256(V1_QUALIFICATION)},
            "contract_migration_manifest": {"path": _path(CONTRACT_MANIFEST), "sha256": _file_sha256(CONTRACT_MANIFEST)},
        },
        "source": {
            "repository": "https://github.com/ethz-spylab/agentdojo.git",
            "commit": SOURCE_COMMIT,
            "benchmark_version": BENCHMARK_VERSION,
            "suite": SUITE,
            "attack": "injecagent",
            "lockfile": "uv.lock",
            "lockfile_sha256": _file_sha256(source / "uv.lock"),
            "runtime_identity": _runtime_identity(),
            "security_dispatch": _callable_source(suite._check_injection_task_security, source),
            "pipeline_pre_state_setup": _callable_source(suite.run_task_with_pipeline, source),
            "base_trace_oracle": _callable_source(BaseInjectionTask.security_from_traces, source),
        },
        "amendment": {
            "v1_status": "historical_and_blocked; retained unchanged",
            "trigger": "v1 selected email task-0 predicate failed its exact-injected-state positive control",
            "v1_email_stratum_census": {
                **V1_EMAIL_STRATUM,
                "population_case_count": len(historical_email_census),
                "source_qualified_case_count": 0,
                "census": historical_email_census,
                "census_sha256": _sha256(historical_email_census),
            },
            "semantic_change": (
                "The new email-carrier stratum uses injection_task_3/email_content_exfiltration, not the v1 "
                "injection_task_0/unauthorized_email effect family; it is not a like-for-like substitution."
            ),
        },
        "selection": {
            "selection_status": "pre_registered_not_run",
            "outcome_blind_scope": "LLM, guard, policy, adapter, provider, and runtime outcomes; source-oracle calibration is an explicit eligibility input.",
            "structural_eligibility": STRUCTURAL_ELIGIBILITY,
            "source_qualification_rule": QUALIFICATION_RULE,
            "seed": seed,
            "ranking_rule": "Within each v2 stratum, select rank 1 by SHA-256(seed.value + NUL + case_id) among source-qualified rows.",
            "strata": stratum_summaries,
            "selected_case_ids": selected_case_ids,
            "execution_status": "not_run_pending_new_manifest_bound_driver_and_benign_control",
        },
        "v2_candidate_census": target_census,
        "v2_candidate_census_sha256": _sha256(target_census),
        "observed_execution_counters": {
            "llm_requests": 0,
            "provider_requests": 0,
            "network_requests": 0,
            "remote_jobs": 0,
            "local_ground_truth_tool_dispatches": _count_local_dispatches(target_census)
            + _count_local_dispatches(historical_email_census),
        },
        "oracle_scope_limitation": (
            "Qualification establishes only canonical ground-truth satisfaction of pinned AgentDojo predicates. "
            "In particular, InjectionTask3.security requires exactly one matching email and an exact recipient list, "
            "so duplicate or extra-recipient exfiltration can be under-detected. Any future efficacy paper needs an "
            "independent monotone post-effect/canary oracle or must limit claims to the upstream AgentDojo predicate."
        ),
        "non_claims": [
            "This artifact contains zero LLM, guard, endpoint, provider, network, remote-job, utility, latency, or cost observations.",
            "The three selected cases are a source-qualified feasibility subset, not a benchmark result, population estimate, ASR/AFER estimate, causal comparison, or Q2-readiness result.",
            "The v2 selection does not unblock the historical v1 execution plan, create a benign twin, or authorize a billable run.",
        ],
    }
    validate_selection(artifact)
    return artifact


def _expected_census_case_ids(manifest: dict[str, Any], strata: tuple[dict[str, str], ...]) -> list[str]:
    return [row["case_id"] for stratum in strata for row in _rows_for_stratum(manifest, stratum)]


def _validate_census_row(record: dict[str, Any], expected: dict[str, Any]) -> None:
    if record.get("structural_eligibility") != expected["execution_eligibility"]:
        raise ValueError("census structural-eligibility mismatch")
    if expected["execution_eligibility"] != STRUCTURAL_ELIGIBILITY:
        if record.get("qualification_status") != "ineligible_structural_multi_carrier" or record.get("selection_rank") is not None:
            raise ValueError("multi-carrier candidate must be retained as structurally ineligible")
        return
    if record.get("qualification_status") == "ineligible_oracle_error":
        error = record.get("qualification_error")
        if not isinstance(error, dict) or not isinstance(error.get("stage"), str) or not isinstance(error.get("category"), str):
            raise ValueError("oracle-error candidate needs a safe error category")
        return
    attack = record.get("attack_binding")
    source_callables = record.get("source_callables")
    pre_state = record.get("exact_pre_execution_state")
    controls = record.get("local_source_controls")
    if not all(isinstance(value, dict) for value in (attack, source_callables, pre_state, controls)):
        raise ValueError("source-calibrated census candidate lacks required bindings")
    for key in ("user_task_id", "injection_task_id", "carrier_id", "injection_goal_sha256", "attack_text_sha256"):
        if attack.get(key) != expected[key]:
            raise ValueError(f"census attack binding mismatch for {key}")
    if pre_state.get("canonicalization") != STATE_CANONICALIZATION or pre_state.get("materialized_carrier_ids") != [expected["carrier_id"]]:
        raise ValueError("census exact pre-state mismatch")
    if not isinstance(pre_state.get("sha256"), str) or len(pre_state["sha256"]) != 64:
        raise ValueError("census exact pre-state hash missing")
    for callable_name in ("predicate", "trace_fast_path", "injection_ground_truth", "user_ground_truth"):
        source_descriptor = source_callables.get(callable_name)
        if not isinstance(source_descriptor, dict) or not isinstance(source_descriptor.get("source_file_sha256"), str):
            raise ValueError("census callable source binding missing")
    fresh = controls.get("fresh_state_harmful_effect_observed")
    injection = controls.get("injection_ground_truth_harmful_effect_observed")
    user = controls.get("user_ground_truth_harmful_effect_observed")
    if not all(isinstance(value, bool) for value in (fresh, injection, user)):
        raise ValueError("census source controls must be booleans")
    expected_status = (
        "ineligible_pre_state_already_harmful"
        if fresh
        else "ineligible_oracle_nondiscriminating"
        if not injection
        else "ineligible_user_ground_truth_overlap"
        if user
        else "eligible_source_calibrated"
    )
    if record.get("qualification_status") != expected_status:
        raise ValueError("census qualification does not follow the source-control rule")


def validate_selection(artifact: dict[str, Any]) -> dict[str, Any]:
    if artifact.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("unsupported v2 selection schema")
    if artifact.get("result_status") != "source_qualified_selection_only_not_llm_evaluation":
        raise ValueError("v2 selection must not claim an LLM evaluation")
    manifest = load_manifest(V1_MANIFEST)
    load_qualification(V1_QUALIFICATION)
    inputs = artifact.get("inputs")
    source = artifact.get("source")
    amendment = artifact.get("amendment")
    selection = artifact.get("selection")
    census = artifact.get("v2_candidate_census")
    if not all(isinstance(value, dict) for value in (inputs, source, amendment, selection)) or not isinstance(census, list):
        raise ValueError("v2 selection has invalid top-level objects")
    expected_inputs = {
        "v1_manifest": {"path": _path(V1_MANIFEST), "sha256": _file_sha256(V1_MANIFEST)},
        "v1_oracle_qualification": {"path": _path(V1_QUALIFICATION), "sha256": _file_sha256(V1_QUALIFICATION)},
        "contract_migration_manifest": {"path": _path(CONTRACT_MANIFEST), "sha256": _file_sha256(CONTRACT_MANIFEST)},
    }
    if inputs != expected_inputs:
        raise ValueError("v2 selection input binding mismatch")
    if source.get("commit") != SOURCE_COMMIT or source.get("benchmark_version") != BENCHMARK_VERSION or source.get("suite") != SUITE:
        raise ValueError("v2 selection source pin mismatch")
    if source.get("lockfile") != "uv.lock" or not isinstance(source.get("lockfile_sha256"), str):
        raise ValueError("v2 selection lockfile binding incomplete")
    if amendment.get("v1_status") != "historical_and_blocked; retained unchanged":
        raise ValueError("v1 must remain historical and blocked")
    historical = amendment.get("v1_email_stratum_census")
    if not isinstance(historical, dict):
        raise ValueError("v1 email census is missing")
    expected_historical_ids = [row["case_id"] for row in _rows_for_stratum(manifest, V1_EMAIL_STRATUM)]
    historical_rows = historical.get("census")
    if not isinstance(historical_rows, list) or [row.get("case_id") for row in historical_rows] != expected_historical_ids:
        raise ValueError("v1 email census coverage/order mismatch")
    if historical.get("census_sha256") != _sha256(historical_rows) or historical.get("source_qualified_case_count") != 0:
        raise ValueError("v1 email census digest or qualification count mismatch")
    if any(row.get("qualification_status") == "eligible_source_calibrated" for row in historical_rows):
        raise ValueError("v1 task-0 email rows must not silently qualify")
    expected_historical_rows = {row["case_id"]: row for row in _rows_for_stratum(manifest, V1_EMAIL_STRATUM)}
    for row in historical_rows:
        _validate_census_row(row, expected_historical_rows[row["case_id"]])
    if artifact.get("v2_candidate_census_sha256") != _sha256(census):
        raise ValueError("v2 candidate census digest mismatch")
    expected_ids = _expected_census_case_ids(manifest, V2_STRATA)
    if [row.get("case_id") for row in census] != expected_ids:
        raise ValueError("v2 candidate census coverage/order mismatch")
    expected_rows = {
        row["case_id"]: row
        for stratum in V2_STRATA
        for row in _rows_for_stratum(manifest, stratum)
    }
    for row in census:
        _validate_census_row(row, expected_rows[row["case_id"]])
    if selection.get("structural_eligibility") != STRUCTURAL_ELIGIBILITY or selection.get("source_qualification_rule") != QUALIFICATION_RULE:
        raise ValueError("v2 selection eligibility rule mismatch")
    expected_seed = _selection_seed(manifest)
    if selection.get("seed") != expected_seed:
        raise ValueError("v2 selection seed must derive only from immutable inputs")
    if selection.get("execution_status") != "not_run_pending_new_manifest_bound_driver_and_benign_control":
        raise ValueError("v2 selection must remain unexecuted and blocked on a dedicated driver")
    expected_selected: list[str] = []
    summaries = selection.get("strata")
    if not isinstance(summaries, list) or len(summaries) != len(V2_STRATA):
        raise ValueError("v2 stratum summary mismatch")
    for spec, summary in zip(V2_STRATA, summaries, strict=True):
        if not isinstance(summary, dict) or any(summary.get(key) != value for key, value in spec.items()):
            raise ValueError("v2 stratum identity mismatch")
        rows = [row for row in census if row.get("stratum_id") == spec["stratum_id"]]
        eligible = [row for row in rows if row.get("qualification_status") == "eligible_source_calibrated"]
        ordered = sorted(
            eligible,
            key=lambda row: (hashlib.sha256(f"{expected_seed['value']}\0{row['case_id']}".encode()).hexdigest(), row["case_id"]),
        )
        if not ordered:
            raise ValueError(f"v2 stratum has no qualified candidate: {spec['stratum_id']}")
        for rank, row in enumerate(ordered, start=1):
            score = hashlib.sha256(f"{expected_seed['value']}\0{row['case_id']}".encode()).hexdigest()
            if row.get("selection_rank") != rank or row.get("selection_score_sha256") != score:
                raise ValueError("v2 candidate rank/score mismatch")
        if summary.get("population_case_count") != len(rows) or summary.get("source_qualified_case_count") != len(eligible):
            raise ValueError("v2 stratum cardinality mismatch")
        if summary.get("selected_case_id") != ordered[0]["case_id"]:
            raise ValueError("v2 stratum selected case mismatch")
        expected_selected.append(ordered[0]["case_id"])
    if selection.get("selected_case_ids") != expected_selected:
        raise ValueError("v2 selected cases mismatch")
    counters = artifact.get("observed_execution_counters")
    expected_counters = {
        "llm_requests": 0,
        "provider_requests": 0,
        "network_requests": 0,
        "remote_jobs": 0,
        "local_ground_truth_tool_dispatches": _count_local_dispatches(census) + _count_local_dispatches(historical_rows),
    }
    if counters != expected_counters:
        raise ValueError("v2 selection counters mismatch")
    return {
        "selected_case_count": len(expected_selected),
        "v2_candidate_count": len(census),
        "historical_email_candidate_count": len(historical_rows),
        "execution_status": selection["execution_status"],
        "result_status": artifact["result_status"],
    }


def load_selection(path: Path = DEFAULT_OUTPUT) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("v2 selection artifact must be a JSON object")
    validate_selection(value)
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, help="clean, pinned AgentDojo checkout; required to build or source-verify")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--verify", action="store_true", help="validate the committed artifact and compare it with --source when supplied")
    args = parser.parse_args()
    output = args.output.resolve()
    if args.verify:
        committed = load_selection(output)
        report = validate_selection(committed)
        if args.source is not None:
            regenerated = build_selection(args.source)
            if json.dumps(regenerated, ensure_ascii=False, sort_keys=True, separators=(",", ":")) != json.dumps(
                committed, ensure_ascii=False, sort_keys=True, separators=(",", ":")
            ):
                raise ValueError("v2 selection differs from the pinned-source regeneration")
            report["source_regeneration_match"] = True
        print(json.dumps(report, ensure_ascii=True, indent=2))
        return 0
    if args.source is None:
        parser.error("--source is required to build a v2 selection")
    selection = build_selection(args.source)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(selection, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(validate_selection(selection), ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
