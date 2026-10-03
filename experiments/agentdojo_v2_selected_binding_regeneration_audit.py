"""Fail closed when frozen AgentDojo v2 attack pre-states cannot regenerate.

The v2 selection and effect-oracle fixtures are historical, immutable inputs.
This audit does not repair, rewrite, or execute them.  Instead, it recreates
only the three selected InjecAgent pre-agent states from a clean pinned source
checkout and compares carrier, injection-map, and canonical-state witnesses.

It performs deterministic in-memory source construction only.  It never calls
an LLM, endpoint, provider, network service, or Runpod resource.  A blocked
audit is evidence that a future *superseding* manifest must not schedule these
attack rows until the provenance discrepancy is reconciled; it is not a model
or defense result.
"""

from __future__ import annotations

import argparse
import hashlib
import inspect
import json
import platform
import subprocess
from importlib.metadata import version
from pathlib import Path
from typing import Any

try:
    from experiments.agentdojo_oracle_qualified_selection_v2 import DEFAULT_OUTPUT as V2_SELECTION
    from experiments.agentdojo_oracle_qualified_selection_v2 import load_selection
    from experiments.agentdojo_paired_v0_v1_execution_manifest import DEFAULT_OUTPUT as PAIRED_MANIFEST
    from experiments.agentdojo_pilot_manifest import BENCHMARK_VERSION, SUITE
    from experiments.agentdojo_pilot_oracle_qualification import (
        STATE_CANONICALIZATION,
        _file_sha256,
        _verify_source,
    )
    from experiments.agentdojo_v2_effect_oracle_contract import (
        DEFAULT_OUTPUT as EFFECT_ORACLE_CONTRACT,
        _binding_templates,
        _verify_agentdojo_import_origin,
        _verify_effect_source_files,
        load_contract as load_effect_oracle_contract,
    )
except ModuleNotFoundError:  # direct ``python experiments/*.py`` support
    from agentdojo_oracle_qualified_selection_v2 import DEFAULT_OUTPUT as V2_SELECTION, load_selection
    from agentdojo_paired_v0_v1_execution_manifest import DEFAULT_OUTPUT as PAIRED_MANIFEST
    from agentdojo_pilot_manifest import BENCHMARK_VERSION, SUITE
    from agentdojo_pilot_oracle_qualification import STATE_CANONICALIZATION, _file_sha256, _verify_source
    from agentdojo_v2_effect_oracle_contract import (
        DEFAULT_OUTPUT as EFFECT_ORACLE_CONTRACT,
        _binding_templates,
        _verify_agentdojo_import_origin,
        _verify_effect_source_files,
        load_contract as load_effect_oracle_contract,
    )


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "experiments" / "fixtures" / "agentdojo_v2_selected_binding_regeneration_audit_v1.json"
SCHEMA_VERSION = "agentdojo-v2-selected-binding-regeneration-audit/v1"
RESULT_STATUS = "source_only_selected_binding_regeneration_audit_not_llm_evaluation"
BLOCKED_STATUS = "blocked_selected_binding_regeneration_mismatch"
VERIFIED_STATUS = "verified_selected_binding_regeneration"
ATTACK_MATERIALIZER_SOURCES = {
    "InjecAgentAttack": {
        "path": "src/agentdojo/attacks/baseline_attacks.py",
        "sha256": "3f9e597f1543d911a753801d8964f91f5ded12810be8cce34e4235f81449f907",
    },
    "InjecAgentAttack.attack": {
        "path": "src/agentdojo/attacks/base_attacks.py",
        "sha256": "9f5276ddb0e7b4beb2379c2483e0b87f16aa90f40253e57d5da50ec409e9797b",
    },
}
ENVIRONMENT_ATTESTATION_SCOPE = (
    "Git commit, clean tree, origin remote, lockfile digest, and runtime identity match the declared selection "
    "witness; dependency-installation or uv-sync provenance is not independently attested by this audit."
)


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _relative(path: Path) -> str:
    return str(path.relative_to(ROOT)).replace("\\", "/")


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(character in "0123456789abcdef" for character in value)


def _runtime_identity() -> dict[str, str]:
    return {
        "python_implementation": platform.python_implementation(),
        "python_version": platform.python_version(),
        "pydantic_version": version("pydantic"),
        "pyyaml_version": version("PyYAML"),
    }


def _git_remote(source: Path) -> str:
    completed = subprocess.run(
        ["git", "-C", str(source), "remote", "get-url", "origin"], check=True, capture_output=True, text=True
    )
    return completed.stdout.strip()


def _source_origin(value: Any, source: Path) -> dict[str, str]:
    filename = inspect.getsourcefile(value)
    if filename is None:
        raise ValueError("attack materializer has no inspectable source origin")
    try:
        relative = Path(filename).resolve().relative_to(source.resolve()).as_posix()
    except ValueError as exc:
        raise ValueError("attack materializer import escapes the pinned checkout") from exc
    return {"path": relative, "sha256": _file_sha256(source / relative)}


def _selected_rows_and_bindings() -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    """Load immutable inputs and prove their selected binding is internally aligned."""

    selection = load_selection(V2_SELECTION)
    effect_contract = load_effect_oracle_contract(EFFECT_ORACLE_CONTRACT)
    bindings = _binding_templates(selection)
    if effect_contract.get("bindings") != bindings:
        raise ValueError("v2 effect-oracle bindings differ from the immutable selected binding")
    selected_ids = selection["selection"]["selected_case_ids"]
    census = {row.get("case_id"): row for row in selection["v2_candidate_census"] if isinstance(row, dict)}
    try:
        rows = [census[case_id] for case_id in selected_ids]
    except KeyError as exc:
        raise ValueError(f"v2 selection refers to an absent selected row: {exc}") from exc
    if [row.get("case_id") for row in rows] != [binding["case_id"] for binding in bindings]:
        raise ValueError("v2 selected rows and effect-oracle bindings are not in the same order")
    for row, binding in zip(rows, bindings, strict=True):
        attack = row.get("attack_binding")
        state = row.get("exact_pre_execution_state")
        if not isinstance(attack, dict) or not isinstance(state, dict):
            raise ValueError("selected v2 row lacks an attack or pre-state binding")
        for field in ("user_task_id", "injection_task_id", "carrier_id"):
            if attack.get(field) != binding.get(field):
                raise ValueError(f"selected v2 row differs from effect-oracle binding: {field}")
        if state.get("canonicalization") != STATE_CANONICALIZATION:
            raise ValueError("selected v2 row uses an unsupported state canonicalization")
        if state.get("sha256") != binding.get("expected_pre_state_sha256"):
            raise ValueError("selected v2 and effect-oracle pre-state witnesses differ")
    return selection, effect_contract, rows, bindings


def build_audit(source: Path) -> dict[str, Any]:
    """Regenerate only selected attack bindings from a clean pinned checkout."""

    source = _verify_source(source)
    selection, effect_contract, rows, bindings = _selected_rows_and_bindings()
    checked_source_files = _verify_effect_source_files(source)
    _verify_agentdojo_import_origin(source)
    runtime_identity = _runtime_identity()
    if runtime_identity != selection["source"].get("runtime_identity"):
        raise ValueError("selected-binding audit runtime identity differs from the declared selection witness")
    repository_remote = _git_remote(source)
    if repository_remote != selection["source"].get("repository"):
        raise ValueError("selected-binding audit source origin differs from the declared selection repository")

    from agentdojo.attacks.baseline_attacks import InjecAgentAttack
    from agentdojo.task_suite.load_suites import get_suite

    suite = get_suite(BENCHMARK_VERSION, SUITE)
    attack = InjecAgentAttack(suite, None)
    materializer_sources = {
        "InjecAgentAttack": _source_origin(InjecAgentAttack, source),
        "InjecAgentAttack.attack": _source_origin(InjecAgentAttack.attack, source),
    }
    if materializer_sources != ATTACK_MATERIALIZER_SOURCES:
        raise ValueError("selected-binding audit attack-materializer source drift or import-origin mismatch")
    cases = []
    for row, binding in zip(rows, bindings, strict=True):
        selected_attack = row["attack_binding"]
        selected_state = row["exact_pre_execution_state"]
        user_task = suite.get_user_task_by_id(binding["user_task_id"])
        injection_task = suite.get_injection_task_by_id(binding["injection_task_id"])
        injections = attack.attack(user_task, injection_task)
        observed_carrier_ids = sorted(injections)
        pre_state = user_task.init_environment(suite.load_and_inject_default_environment(injections)).model_copy(deep=True)
        observed_pre_state_sha256 = _sha256(pre_state.model_dump(mode="json"))
        expected_carrier_ids = [binding["carrier_id"]]
        expected_pre_state_sha256 = binding["expected_pre_state_sha256"]
        expected_injection_map_sha256 = selected_attack["injection_map_sha256"]
        observed_injection_map_sha256 = _sha256(injections)
        cases.append(
            {
                "case_id": binding["case_id"],
                "stratum_id": binding["stratum_id"],
                "user_task_id": binding["user_task_id"],
                "injection_task_id": binding["injection_task_id"],
                "carrier_id": binding["carrier_id"],
                "expected_carrier_ids": expected_carrier_ids,
                "observed_carrier_ids": observed_carrier_ids,
                "carrier_match": observed_carrier_ids == expected_carrier_ids,
                "expected_injection_map_sha256": expected_injection_map_sha256,
                "observed_injection_map_sha256": observed_injection_map_sha256,
                "injection_map_match": observed_injection_map_sha256 == expected_injection_map_sha256,
                "expected_selection_pre_state_sha256": selected_state["sha256"],
                "expected_effect_oracle_pre_state_sha256": expected_pre_state_sha256,
                "observed_pre_state_sha256": observed_pre_state_sha256,
                "selection_pre_state_match": observed_pre_state_sha256 == selected_state["sha256"],
                "effect_oracle_pre_state_match": observed_pre_state_sha256 == expected_pre_state_sha256,
            }
        )

    def matches(case: dict[str, Any]) -> bool:
        return all(
            case[field] is True
            for field in (
                "carrier_match",
                "injection_map_match",
                "selection_pre_state_match",
                "effect_oracle_pre_state_match",
            )
        )

    matching_case_count = sum(matches(case) for case in cases)
    gate_status = VERIFIED_STATUS if matching_case_count == len(cases) else BLOCKED_STATUS
    return {
        "schema_version": SCHEMA_VERSION,
        "recorded_on": "2026-10-03",
        "result_status": RESULT_STATUS,
        "purpose": (
            "Audit whether the three immutable v2 selected InjecAgent bindings regenerate their carrier, injection-map, "
            "and exact pre-agent-state witnesses from a clean pinned AgentDojo checkout."
        ),
        "inputs": {
            "v2_selection": {"path": _relative(V2_SELECTION), "sha256": _file_sha256(V2_SELECTION)},
            "effect_oracle_contract": {
                "path": _relative(EFFECT_ORACLE_CONTRACT),
                "sha256": _file_sha256(EFFECT_ORACLE_CONTRACT),
            },
            "historical_paired_execution_manifest": {
                "path": _relative(PAIRED_MANIFEST),
                "sha256": _file_sha256(PAIRED_MANIFEST),
                "role": "historical_only_not_amended",
            },
        },
        "source": {
            "verification_witness": effect_contract["source"]["verification_witness"],
            "checked_effect_oracle_source_files": checked_source_files,
            "repository_remote": repository_remote,
            "runtime_identity": runtime_identity,
            "environment_attestation_scope": ENVIRONMENT_ATTESTATION_SCOPE,
            "attack_materializer_sources": materializer_sources,
        },
        "audit_implementation": {"path": _relative(Path(__file__)), "sha256": _file_sha256(Path(__file__))},
        "selected_binding_regeneration": {
            "gate_status": gate_status,
            "required_match": (
                "Every selected case must match carrier IDs, injection-map digest, and both immutable canonical "
                "pre-state digests before a superseding manifest may schedule an attack episode."
            ),
            "case_count": len(cases),
            "matching_case_count": matching_case_count,
            "mismatching_case_count": len(cases) - matching_case_count,
            "cases": cases,
            "cases_sha256": _sha256(cases),
        },
        "self_reported_execution_counters": {
            "llm_requests": 0,
            "provider_requests": 0,
            "network_requests": 0,
            "remote_jobs": 0,
            "local_attack_materializations": len(cases),
            "local_tool_dispatches": 0,
        },
        "operational_rule": (
            "When gate_status is blocked_selected_binding_regeneration_mismatch, do not run or score the historical "
            "v2 attack plan. Preserve its fixtures unchanged; diagnose the unexplained source-or-runtime state mismatch "
            "and issue a new versioned selection, effect-oracle contract, and execution manifest before any future runtime episode."
        ),
        "non_claims": [
            "This source-only audit is not an LLM, agent, defense, utility, latency, cost, or benchmark-efficacy observation.",
            "A matching audit would establish source reproducibility of selected binding witnesses only, not runtime provenance, benign-arm parity, or a causal defense effect.",
            "The audit does not authorize a Runpod/API call, modify the historical v1/v2 fixtures, or repair the observed discrepancy.",
            "The self-reported counters are not independent evidence that a process made no model, provider, network, or remote-job call.",
        ],
    }


def validate_audit(audit: dict[str, Any]) -> dict[str, Any]:
    """Validate immutable bindings and fail closed on malformed provenance evidence."""

    if not isinstance(audit, dict) or audit.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("unsupported selected-binding regeneration-audit schema")
    if audit.get("result_status") != RESULT_STATUS:
        raise ValueError("regeneration audit must not claim an LLM evaluation")
    selection, effect_contract, rows, bindings = _selected_rows_and_bindings()
    expected_inputs = {
        "v2_selection": {"path": _relative(V2_SELECTION), "sha256": _file_sha256(V2_SELECTION)},
        "effect_oracle_contract": {"path": _relative(EFFECT_ORACLE_CONTRACT), "sha256": _file_sha256(EFFECT_ORACLE_CONTRACT)},
        "historical_paired_execution_manifest": {
            "path": _relative(PAIRED_MANIFEST),
            "sha256": _file_sha256(PAIRED_MANIFEST),
            "role": "historical_only_not_amended",
        },
    }
    if audit.get("inputs") != expected_inputs:
        raise ValueError("regeneration audit input binding mismatch")
    implementation = audit.get("audit_implementation")
    if implementation != {"path": _relative(Path(__file__)), "sha256": _file_sha256(Path(__file__))}:
        raise ValueError("regeneration audit implementation binding mismatch")
    source = audit.get("source")
    if not isinstance(source, dict) or source.get("verification_witness") != effect_contract["source"]["verification_witness"]:
        raise ValueError("regeneration audit source witness mismatch")
    if source.get("checked_effect_oracle_source_files") != effect_contract["source"]["verification_witness"]["source_files"]:
        raise ValueError("regeneration audit checked source files mismatch")
    if source.get("repository_remote") != selection["source"].get("repository"):
        raise ValueError("regeneration audit source origin mismatch")
    if source.get("runtime_identity") != selection["source"].get("runtime_identity"):
        raise ValueError("regeneration audit runtime identity mismatch")
    if source.get("environment_attestation_scope") != ENVIRONMENT_ATTESTATION_SCOPE:
        raise ValueError("regeneration audit environment-attestation scope mismatch")
    if source.get("attack_materializer_sources") != ATTACK_MATERIALIZER_SOURCES:
        raise ValueError("regeneration audit attack-materializer binding mismatch")
    scope = audit.get("selected_binding_regeneration")
    if not isinstance(scope, dict):
        raise ValueError("regeneration audit scope missing")
    expected_requirement = (
        "Every selected case must match carrier IDs, injection-map digest, and both immutable canonical "
        "pre-state digests before a superseding manifest may schedule an attack episode."
    )
    if scope.get("required_match") != expected_requirement:
        raise ValueError("regeneration audit required-match rule mismatch")
    cases = scope.get("cases")
    if not isinstance(cases, list) or len(cases) != len(bindings):
        raise ValueError("regeneration audit case coverage mismatch")
    matching_case_count = 0
    for case, row, binding in zip(cases, rows, bindings, strict=True):
        if not isinstance(case, dict):
            raise ValueError("regeneration audit case is malformed")
        selected_attack = row["attack_binding"]
        selected_state = row["exact_pre_execution_state"]
        expected_fields = {
            "case_id": binding["case_id"],
            "stratum_id": binding["stratum_id"],
            "user_task_id": binding["user_task_id"],
            "injection_task_id": binding["injection_task_id"],
            "carrier_id": binding["carrier_id"],
            "expected_carrier_ids": [binding["carrier_id"]],
            "expected_injection_map_sha256": selected_attack["injection_map_sha256"],
            "expected_selection_pre_state_sha256": selected_state["sha256"],
            "expected_effect_oracle_pre_state_sha256": binding["expected_pre_state_sha256"],
        }
        if any(case.get(field) != value for field, value in expected_fields.items()):
            raise ValueError("regeneration audit immutable case binding mismatch")
        if not isinstance(case.get("observed_carrier_ids"), list) or not all(isinstance(value, str) for value in case["observed_carrier_ids"]):
            raise ValueError("regeneration audit observed carrier IDs malformed")
        for field in (
            "observed_injection_map_sha256",
            "observed_pre_state_sha256",
            "expected_injection_map_sha256",
            "expected_selection_pre_state_sha256",
            "expected_effect_oracle_pre_state_sha256",
        ):
            if not _is_sha256(case.get(field)):
                raise ValueError("regeneration audit state or injection digest malformed")
        expected_booleans = {
            "carrier_match": case["observed_carrier_ids"] == case["expected_carrier_ids"],
            "injection_map_match": case["observed_injection_map_sha256"] == case["expected_injection_map_sha256"],
            "selection_pre_state_match": case["observed_pre_state_sha256"] == case["expected_selection_pre_state_sha256"],
            "effect_oracle_pre_state_match": case["observed_pre_state_sha256"] == case["expected_effect_oracle_pre_state_sha256"],
        }
        if any(case.get(field) is not value for field, value in expected_booleans.items()):
            raise ValueError("regeneration audit match flags do not follow evidence")
        if all(expected_booleans.values()):
            matching_case_count += 1
    if scope.get("case_count") != len(cases) or scope.get("matching_case_count") != matching_case_count:
        raise ValueError("regeneration audit case counts mismatch")
    if scope.get("mismatching_case_count") != len(cases) - matching_case_count:
        raise ValueError("regeneration audit mismatch count incorrect")
    if scope.get("cases_sha256") != _sha256(cases):
        raise ValueError("regeneration audit case digest mismatch")
    expected_status = VERIFIED_STATUS if matching_case_count == len(cases) else BLOCKED_STATUS
    if scope.get("gate_status") != expected_status:
        raise ValueError("regeneration audit gate status does not follow the observed witnesses")
    if audit.get("self_reported_execution_counters") != {
        "llm_requests": 0,
        "provider_requests": 0,
        "network_requests": 0,
        "remote_jobs": 0,
        "local_attack_materializations": len(cases),
        "local_tool_dispatches": 0,
    }:
        raise ValueError("regeneration audit execution counters mismatch")
    expected_rule = (
        "When gate_status is blocked_selected_binding_regeneration_mismatch, do not run or score the historical "
        "v2 attack plan. Preserve its fixtures unchanged; diagnose the unexplained source-or-runtime state mismatch "
        "and issue a new versioned selection, effect-oracle contract, and execution manifest before any future runtime episode."
    )
    if audit.get("operational_rule") != expected_rule:
        raise ValueError("regeneration audit operational rule mismatch")
    if audit.get("non_claims") != [
        "This source-only audit is not an LLM, agent, defense, utility, latency, cost, or benchmark-efficacy observation.",
        "A matching audit would establish source reproducibility of selected binding witnesses only, not runtime provenance, benign-arm parity, or a causal defense effect.",
        "The audit does not authorize a Runpod/API call, modify the historical v1/v2 fixtures, or repair the observed discrepancy.",
        "The self-reported counters are not independent evidence that a process made no model, provider, network, or remote-job call.",
    ]:
        raise ValueError("regeneration audit non-claim boundary mismatch")
    return {
        "gate_status": scope["gate_status"],
        "case_count": len(cases),
        "matching_case_count": matching_case_count,
        "mismatching_case_count": len(cases) - matching_case_count,
        "result_status": audit["result_status"],
    }


def load_audit(path: Path = DEFAULT_OUTPUT) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("regeneration audit must be a JSON object")
    validate_audit(value)
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, help="clean pinned AgentDojo checkout; required to build or source-verify")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--verify", action="store_true", help="validate an existing audit and compare it with --source")
    args = parser.parse_args()
    output = args.output.resolve()
    if args.verify:
        committed = load_audit(output)
        report = validate_audit(committed)
        if args.source is not None:
            regenerated = build_audit(args.source)
            if _canonical_bytes(regenerated) != _canonical_bytes(committed):
                raise ValueError("selected-binding regeneration audit differs from the pinned-source regeneration")
            report["source_regeneration_match"] = True
        print(json.dumps(report, ensure_ascii=True, indent=2))
        return 0
    if args.source is None:
        parser.error("--source is required to build a selected-binding regeneration audit")
    audit = build_audit(args.source)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(validate_audit(audit), ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
