"""Pin reversible v0/v1 trace canonicalization for the default-control scorer.

The reviewed tool migration changes exposed v1 function names while preserving
their canonical v0 semantics.  The no-InjecAgent default-control utility scorer
loads the canonical AgentDojo registry, so a raw v1 trace must be normalized
before it can be passed to that scorer.  This module makes that mapping
explicit, digest-bound, and fail-closed.

It is a source-only interface calibration.  Its v1 controls transform
canonical ground-truth trace names locally; they are not a v1 runtime,
LLM, defense, or benchmark observation.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
from typing import Any

try:
    from experiments.agentdojo_contract_migration import contract_digest, load_contract as load_tool_contract
    from experiments.agentdojo_pilot_manifest import BENCHMARK_VERSION, SUITE
    from experiments.agentdojo_pilot_oracle_qualification import _file_sha256, _verify_source
    from experiments.agentdojo_v2_no_injecagent_default_control_contract import (
        DEFAULT_OUTPUT as DEFAULT_CONTROL_CONTRACT,
        FUNCTION_TRACE_SCHEMA_VERSION,
        STATE_SCHEMA_VERSION,
        _control_witness,
        load_contract as load_default_control_contract,
        score_default_control_episode,
    )
except ModuleNotFoundError:  # direct python experiments/*.py support
    from agentdojo_contract_migration import contract_digest, load_contract as load_tool_contract
    from agentdojo_pilot_manifest import BENCHMARK_VERSION, SUITE
    from agentdojo_pilot_oracle_qualification import _file_sha256, _verify_source
    from agentdojo_v2_no_injecagent_default_control_contract import (
        DEFAULT_OUTPUT as DEFAULT_CONTROL_CONTRACT,
        FUNCTION_TRACE_SCHEMA_VERSION,
        STATE_SCHEMA_VERSION,
        _control_witness,
        load_contract as load_default_control_contract,
        score_default_control_episode,
    )


ROOT = Path(__file__).resolve().parents[1]
TOOL_CONTRACT = ROOT / "experiments" / "fixtures" / "agentdojo_contract_v0_to_v1.json"
DEFAULT_OUTPUT = ROOT / "experiments" / "fixtures" / "agentdojo_v2_utility_trace_normalization_contract_v1.json"
SCHEMA_VERSION = "agentdojo-v2-utility-trace-normalization-contract/v1"
WITNESS_SCHEMA_VERSION = "agentdojo-utility-trace-normalization-witness/v1"
RESULT_STATUS = "source_only_trace_normalization_calibration_not_llm_evaluation"
VERSIONS = ("v0", "v1")
RUNTIME_PLAN_AUTHORIZATION = "not_authorized"


class TraceNormalizationError(ValueError):
    """A raw trace cannot be canonically mapped under the frozen migration."""


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _path(path: Path) -> str:
    return str(path.relative_to(ROOT)).replace("\\", "/")


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(character in "0123456789abcdef" for character in value)


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise TraceNormalizationError(f"{label} must be an object")
    return value


def _tool_mapping() -> dict[str, str]:
    contract = load_tool_contract(TOOL_CONTRACT)
    mapping = _mapping(contract.get("migration"), "tool migration").get("v0_to_v1")
    if not isinstance(mapping, dict) or not mapping:
        raise ValueError("tool migration has no v0-to-v1 map")
    result = {str(v0): str(v1) for v0, v1 in mapping.items()}
    if any(not v0 or not v1 for v0, v1 in result.items()) or len(result) != len(set(result.values())):
        raise ValueError("tool migration must be a nonempty bijection")
    return result


def _input_bindings() -> dict[str, dict[str, str]]:
    tool = load_tool_contract(TOOL_CONTRACT)
    return {
        "default_control_contract": {
            "path": _path(DEFAULT_CONTROL_CONTRACT),
            "sha256": _file_sha256(DEFAULT_CONTROL_CONTRACT),
        },
        "tool_contract": {
            "path": _path(TOOL_CONTRACT),
            "sha256": _file_sha256(TOOL_CONTRACT),
            "digest": contract_digest(tool),
        },
    }


def _trace_shape(trace: Any) -> list[dict[str, Any]]:
    if not isinstance(trace, list):
        raise TraceNormalizationError("function_trace must be a JSON list")
    result = []
    for index, item in enumerate(trace):
        record = _mapping(item, f"function_trace[{index}]")
        if not isinstance(record.get("function"), str) or not record["function"]:
            raise TraceNormalizationError("function_trace entry lacks a function name")
        if not isinstance(record.get("args"), dict):
            raise TraceNormalizationError("function_trace entry lacks object args")
        result.append(copy.deepcopy(record))
    return result


def _normalization_map(version: str) -> tuple[dict[str, str], str]:
    v0_to_v1 = _tool_mapping()
    if version == "v0":
        return {name: name for name in v0_to_v1}, "v0_identity"
    if version == "v1":
        return {v1: v0 for v0, v1 in v0_to_v1.items()}, "v1_to_canonical_v0"
    raise TraceNormalizationError("unsupported tool-contract version")


def _normalize_unchecked(version: str, raw_trace: Any) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    raw = _trace_shape(raw_trace)
    mapping, direction = _normalization_map(version)
    raw_names = [record["function"] for record in raw]
    if any(name not in mapping for name in raw_names):
        raise TraceNormalizationError("raw trace contains a function absent from the frozen exposed registry")
    canonical = []
    for record in raw:
        normalized = copy.deepcopy(record)
        normalized["function"] = mapping[record["function"]]
        canonical.append(normalized)
    arguments = [record["args"] for record in raw]
    witness = {
        "schema_version": WITNESS_SCHEMA_VERSION,
        "contract_version": version,
        "direction": direction,
        "tool_contract_digest": _input_bindings()["tool_contract"]["digest"],
        "raw_trace_sha256": _sha256(raw),
        "canonical_trace_sha256": _sha256(canonical),
        "raw_function_names_sha256": _sha256(raw_names),
        "canonical_function_names_sha256": _sha256([record["function"] for record in canonical]),
        "arguments_sha256": _sha256(arguments),
        "canonical_arguments_sha256": _sha256([record["args"] for record in canonical]),
        "call_count": len(raw),
    }
    return canonical, witness


def normalize_trace(contract: dict[str, Any], version: str, raw_trace: Any) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Map an exposed v0/v1 trace to canonical v0 names with a witness."""

    validate_contract(contract)
    return _normalize_unchecked(version, raw_trace)


def validate_normalization_witness(
    contract: dict[str, Any], version: str, raw_trace: Any, canonical_trace: Any, witness: Any
) -> None:
    """Reject an altered mapping, trace, argument, or witness."""

    expected_trace, expected_witness = normalize_trace(contract, version, raw_trace)
    if canonical_trace != expected_trace or witness != expected_witness:
        raise TraceNormalizationError("trace normalization witness does not match the frozen mapping")


def normalize_utility_evidence(contract: dict[str, Any], version: str, evidence: dict[str, Any]) -> dict[str, Any]:
    """Return scorer evidence with canonical trace plus the retained raw-trace witness."""

    if not isinstance(evidence, dict):
        raise TraceNormalizationError("utility evidence must be an object")
    canonical_trace, witness = normalize_trace(contract, version, evidence.get("function_trace"))
    normalized = copy.deepcopy(evidence)
    normalized["function_trace"] = canonical_trace
    return {
        "canonical_utility_evidence": normalized,
        "trace_normalization_witness": witness,
    }


def _source_evidence(
    default_control: dict[str, Any],
    binding: dict[str, Any],
    pre_environment: Any,
    post_environment: Any,
    terminal_output: str,
    canonical_trace: list[dict[str, Any]],
) -> dict[str, Any]:
    pre_state = pre_environment.model_dump(mode="json")
    return {
        "terminal_status": "completed",
        "failure_flags": {"runner_error": False, "tool_error": False, "timeout": False, "cancelled": False},
        "state_schema_version": STATE_SCHEMA_VERSION,
        "source_verification_witness": default_control["source"]["verification_witness"],
        "utility_oracle_implementation_sha256": default_control["utility_oracle_implementation"]["sha256"],
        "no_injecagent_default_control_witness": _control_witness(binding),
        "reset_witness": {"verified": True, "pre_state_sha256": _sha256(pre_state)},
        "typed_pre_state": pre_state,
        "typed_post_state": post_environment.model_dump(mode="json"),
        "terminal_output": terminal_output,
        "function_trace": canonical_trace,
    }


def _simulate_v1_trace(raw_v0: list[dict[str, Any]]) -> list[dict[str, Any]]:
    mapping = _tool_mapping()
    simulated = []
    for record in raw_v0:
        renamed = copy.deepcopy(record)
        try:
            renamed["function"] = mapping[record["function"]]
        except KeyError as exc:
            raise ValueError("selected source trace includes a function outside the reviewed migration") from exc
        simulated.append(renamed)
    return simulated


def _build_case_calibration(
    default_control: dict[str, Any], binding: dict[str, Any], source: Path
) -> tuple[dict[str, Any], int]:
    from agentdojo.agent_pipeline.ground_truth_pipeline import GroundTruthPipeline
    from agentdojo.functions_runtime import FunctionsRuntime
    from agentdojo.task_suite.load_suites import get_suite
    from agentdojo.task_suite.task_suite import functions_stack_trace_from_messages, model_output_from_messages

    suite = get_suite(BENCHMARK_VERSION, SUITE)
    user_task = suite.get_user_task_by_id(binding["user_task_id"])
    pre = user_task.init_environment(suite.load_and_inject_default_environment({})).model_copy(deep=True)
    if _sha256(pre.model_dump(mode="json")) != binding["default_control"]["expected_pre_state_sha256"]:
        raise ValueError("source default-control pre-state differs from its pinned binding")
    _, _, post, messages, _ = GroundTruthPipeline(user_task).query("", FunctionsRuntime(suite.tools), pre.model_copy(deep=True))
    blocks = model_output_from_messages(messages)
    if not isinstance(blocks, list):
        raise ValueError("ground-truth pipeline produced no terminal output blocks")
    terminal_output = "\n".join(
        block.get("content", "") for block in blocks if isinstance(block, dict) and isinstance(block.get("content"), str)
    )
    raw_v0 = [call.model_dump(mode="json") for call in functions_stack_trace_from_messages(messages)]
    canonical_v0, witness_v0 = _normalize_unchecked("v0", raw_v0)
    simulated_v1 = _simulate_v1_trace(raw_v0)
    canonical_v1, witness_v1 = _normalize_unchecked("v1", simulated_v1)
    if canonical_v0 != raw_v0 or canonical_v1 != raw_v0:
        raise ValueError("trace canonicalization does not preserve selected source trace semantics")
    result_v0 = score_default_control_episode(
        default_control,
        binding["case_id"],
        _source_evidence(default_control, binding, pre, post, terminal_output, canonical_v0),
        source,
    )
    result_v1 = score_default_control_episode(
        default_control,
        binding["case_id"],
        _source_evidence(default_control, binding, pre, post, terminal_output, canonical_v1),
        source,
    )
    if any(result.get("score_status") != "scored" or result.get("utility_success") is not True for result in (result_v0, result_v1)):
        raise ValueError("canonical trace did not pass the pinned upstream utility scorer")
    return (
        {
            "case_id": binding["case_id"],
            "ground_truth_trace": {
                "v0_raw_trace_sha256": _sha256(raw_v0),
                "canonical_trace_sha256": _sha256(canonical_v0),
                "call_count": len(raw_v0),
            },
            "v0_identity": {
                "trace_normalization_witness": witness_v0,
                "utility_scorer_status": result_v0["score_status"],
                "utility_success": result_v0["utility_success"],
            },
            "v1_synthetic_renaming": {
                "trace_normalization_witness": witness_v1,
                "utility_scorer_status": result_v1["score_status"],
                "utility_success": result_v1["utility_success"],
            },
        },
        len(raw_v0),
    )


def build_contract(source: Path) -> dict[str, Any]:
    """Build the source-only interface calibration from the pinned checkout."""

    source = _verify_source(source)
    default_control = load_default_control_contract(DEFAULT_CONTROL_CONTRACT)
    _tool_mapping()
    calibrations = [_build_case_calibration(default_control, binding, source) for binding in default_control["bindings"]]
    cases = [item[0] for item in calibrations]
    dispatches = sum(item[1] for item in calibrations)
    contract = {
        "schema_version": SCHEMA_VERSION,
        "recorded_on": "2026-10-06",
        "result_status": RESULT_STATUS,
        "purpose": (
            "Source-pinned canonicalization of renamed v0/v1 tool traces before the selected AgentDojo "
            "no-InjecAgent default-control utility scorer."
        ),
        "inputs": _input_bindings(),
        "source_verification_witness": default_control["source"]["verification_witness"],
        "normalization_implementation": {
            "path": _path(Path(__file__)),
            "sha256": _file_sha256(Path(__file__)),
            "raw_trace_schema_version": FUNCTION_TRACE_SCHEMA_VERSION,
            "canonical_trace_schema_version": FUNCTION_TRACE_SCHEMA_VERSION,
            "witness_schema_version": WITNESS_SCHEMA_VERSION,
        },
        "mapping": {
            "v0_to_v1": _tool_mapping(),
            "v0_direction": "v0_identity",
            "v1_direction": "v1_to_canonical_v0",
            "argument_transform": "identity",
        },
        "source_only_calibration": cases,
        "source_only_calibration_sha256": _sha256(cases),
        "observed_execution_counters": {
            "llm_requests": 0,
            "provider_requests": 0,
            "network_requests": 0,
            "remote_jobs": 0,
            "local_ground_truth_tool_dispatches": dispatches,
        },
        "future_driver_requirement": {
            "raw_trace_must_be_retained": True,
            "canonical_trace_must_be_retained": True,
            "trace_normalization_witness_required": True,
            "runtime_plan_authorization": RUNTIME_PLAN_AUTHORIZATION,
        },
        "scope_limitations": [
            "The v1 path renames only locally constructed ground-truth function-call records. It is not a v1 AgentDojo runtime, model, carrier, registry, or tool-dispatch observation.",
            "Normalization preserves function arguments byte-for-byte at the canonical JSON level but cannot prove a future runtime exposed the expected registry, retained the raw trace, or dispatched the calls.",
            "This contract solves only trace-name compatibility with the pinned default-control utility scorer. A prospective manifest/result bundle and provenance-bound driver remain required.",
        ],
        "non_claims": [
            "This artifact contains no LLM, model response, provider, endpoint, Runpod job, network, defense, attack, utility-efficacy, latency, cost, ASR, AFER, causal, statistical, or Q2-readiness observation.",
            "It does not authorize an execution, make the synthetic renamed trace a benchmark result, or change the immutable historical v1 manifest/result bundle.",
        ],
    }
    validate_contract(contract)
    return contract


def _validate_witness_shape(witness: Any, version: str) -> None:
    value = _mapping(witness, "trace normalization witness")
    expected_direction = "v0_identity" if version == "v0" else "v1_to_canonical_v0"
    required = {
        "schema_version",
        "contract_version",
        "direction",
        "tool_contract_digest",
        "raw_trace_sha256",
        "canonical_trace_sha256",
        "raw_function_names_sha256",
        "canonical_function_names_sha256",
        "arguments_sha256",
        "canonical_arguments_sha256",
        "call_count",
    }
    if set(value) != required or (
        value.get("schema_version") != WITNESS_SCHEMA_VERSION
        or value.get("contract_version") != version
        or value.get("direction") != expected_direction
        or value.get("tool_contract_digest") != _input_bindings()["tool_contract"]["digest"]
        or not all(
            _is_sha256(value.get(key))
            for key in (
                "raw_trace_sha256",
                "canonical_trace_sha256",
                "raw_function_names_sha256",
                "canonical_function_names_sha256",
                "arguments_sha256",
                "canonical_arguments_sha256",
            )
        )
        or not isinstance(value.get("call_count"), int)
        or value["call_count"] <= 0
        or value["arguments_sha256"] != value["canonical_arguments_sha256"]
    ):
        raise ValueError("trace normalization witness is malformed")


def validate_contract(contract: dict[str, Any]) -> dict[str, Any]:
    if contract.get("schema_version") != SCHEMA_VERSION or contract.get("result_status") != RESULT_STATUS:
        raise ValueError("unsupported trace-normalization contract")
    if contract.get("recorded_on") != "2026-10-06" or contract.get("inputs") != _input_bindings():
        raise ValueError("trace-normalization inputs mismatch")
    default_control = load_default_control_contract(DEFAULT_CONTROL_CONTRACT)
    if contract.get("source_verification_witness") != default_control["source"]["verification_witness"]:
        raise ValueError("trace-normalization source witness mismatch")
    if contract.get("normalization_implementation") != {
        "path": _path(Path(__file__)),
        "sha256": _file_sha256(Path(__file__)),
        "raw_trace_schema_version": FUNCTION_TRACE_SCHEMA_VERSION,
        "canonical_trace_schema_version": FUNCTION_TRACE_SCHEMA_VERSION,
        "witness_schema_version": WITNESS_SCHEMA_VERSION,
    }:
        raise ValueError("trace-normalization implementation binding mismatch")
    if contract.get("mapping") != {
        "v0_to_v1": _tool_mapping(),
        "v0_direction": "v0_identity",
        "v1_direction": "v1_to_canonical_v0",
        "argument_transform": "identity",
    }:
        raise ValueError("trace-normalization mapping mismatch")
    cases = contract.get("source_only_calibration")
    expected_ids = [binding["case_id"] for binding in default_control["bindings"]]
    if not isinstance(cases, list) or [item.get("case_id") if isinstance(item, dict) else None for item in cases] != expected_ids:
        raise ValueError("trace-normalization calibration coverage mismatch")
    dispatches = 0
    for case in cases:
        ground_truth = _mapping(case.get("ground_truth_trace"), "ground truth trace")
        if set(ground_truth) != {"v0_raw_trace_sha256", "canonical_trace_sha256", "call_count"} or not (
            _is_sha256(ground_truth.get("v0_raw_trace_sha256"))
            and _is_sha256(ground_truth.get("canonical_trace_sha256"))
            and isinstance(ground_truth.get("call_count"), int)
            and ground_truth["call_count"] > 0
            and ground_truth["v0_raw_trace_sha256"] == ground_truth["canonical_trace_sha256"]
        ):
            raise ValueError("ground-truth trace calibration mismatch")
        v0 = _mapping(case.get("v0_identity"), "v0 identity calibration")
        v1 = _mapping(case.get("v1_synthetic_renaming"), "v1 synthetic calibration")
        _validate_witness_shape(v0.get("trace_normalization_witness"), "v0")
        _validate_witness_shape(v1.get("trace_normalization_witness"), "v1")
        if (
            v0.get("utility_scorer_status") != "scored"
            or v0.get("utility_success") is not True
            or v1.get("utility_scorer_status") != "scored"
            or v1.get("utility_success") is not True
            or v0["trace_normalization_witness"]["raw_trace_sha256"] != ground_truth["v0_raw_trace_sha256"]
            or v0["trace_normalization_witness"]["canonical_trace_sha256"] != ground_truth["canonical_trace_sha256"]
            or v1["trace_normalization_witness"]["canonical_trace_sha256"] != ground_truth["canonical_trace_sha256"]
            or v0["trace_normalization_witness"]["call_count"] != ground_truth["call_count"]
            or v1["trace_normalization_witness"]["call_count"] != ground_truth["call_count"]
        ):
            raise ValueError("trace-normalization utility calibration mismatch")
        dispatches += ground_truth["call_count"]
    if contract.get("source_only_calibration_sha256") != _sha256(cases):
        raise ValueError("trace-normalization calibration digest mismatch")
    if contract.get("observed_execution_counters") != {
        "llm_requests": 0,
        "provider_requests": 0,
        "network_requests": 0,
        "remote_jobs": 0,
        "local_ground_truth_tool_dispatches": dispatches,
    }:
        raise ValueError("trace-normalization execution counters mismatch")
    if contract.get("future_driver_requirement") != {
        "raw_trace_must_be_retained": True,
        "canonical_trace_must_be_retained": True,
        "trace_normalization_witness_required": True,
        "runtime_plan_authorization": RUNTIME_PLAN_AUTHORIZATION,
    }:
        raise ValueError("trace-normalization future-driver requirement mismatch")
    limitations = [
        "The v1 path renames only locally constructed ground-truth function-call records. It is not a v1 AgentDojo runtime, model, carrier, registry, or tool-dispatch observation.",
        "Normalization preserves function arguments byte-for-byte at the canonical JSON level but cannot prove a future runtime exposed the expected registry, retained the raw trace, or dispatched the calls.",
        "This contract solves only trace-name compatibility with the pinned default-control utility scorer. A prospective manifest/result bundle and provenance-bound driver remain required.",
    ]
    non_claims = [
        "This artifact contains no LLM, model response, provider, endpoint, Runpod job, network, defense, attack, utility-efficacy, latency, cost, ASR, AFER, causal, statistical, or Q2-readiness observation.",
        "It does not authorize an execution, make the synthetic renamed trace a benchmark result, or change the immutable historical v1 manifest/result bundle.",
    ]
    if contract.get("scope_limitations") != limitations or contract.get("non_claims") != non_claims:
        raise ValueError("trace-normalization claim boundary mismatch")
    return {
        "selected_case_count": len(cases),
        "source_only_calibration_control_count": len(cases) * len(VERSIONS),
        "result_status": contract["result_status"],
        "execution_status": "not_run_pending_v2_manifest_result_bundle_and_driver",
    }


def load_contract(path: Path = DEFAULT_OUTPUT) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("trace-normalization contract must be a JSON object")
    validate_contract(value)
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, help="clean pinned AgentDojo checkout; required to build or source-verify")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--verify", action="store_true", help="verify the committed contract and compare it with --source")
    args = parser.parse_args()
    output = args.output.resolve()
    if args.verify:
        committed = load_contract(output)
        report = validate_contract(committed)
        if args.source is not None:
            regenerated = build_contract(args.source)
            if _canonical_bytes(regenerated) != _canonical_bytes(committed):
                raise ValueError("trace-normalization contract differs from pinned-source regeneration")
            report["source_regeneration_match"] = True
        print(json.dumps(report, ensure_ascii=True, indent=2))
        return 0
    if args.source is None:
        parser.error("--source is required to build a trace-normalization contract")
    contract = build_contract(args.source)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(contract, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(validate_contract(contract), ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
