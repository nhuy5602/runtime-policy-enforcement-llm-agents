"""Non-billable four-cell source conformance for TaskFileScope F/M.

Runs only the upstream authorized user-task sequence in a local Workspace
sandbox. No model, attack carrier, provider, network, or remote job is invoked.
The result is deliberately not a canonical v2 result bundle.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from dataclasses import replace
from pathlib import Path
from typing import Any

from experiments.adapter_attestation import canonical_json, sha256_text
from experiments.agentdojo_file_scope_defense import (
    FAMILY, SCOPED_TOOLS, FileScopePolicy, FileScopeRuntime, migrate_file_contract,
)


ROOT = Path(__file__).resolve().parents[1]
CASE_ID = "workspace:v1.2.2:user_task_29:injection_task_1:drive_team_building_injection"
TASK_ID = "user_task_29"


def _schema_projection(schema: dict[str, Any], root: dict[str, Any] | None = None) -> dict[str, Any]:
    """Keep only contract semantics; omit Pydantic titles and generated refs."""

    root = schema if root is None else root
    reference = schema.get("$ref")
    if isinstance(reference, str) and reference.startswith("#/$defs/"):
        target = root.get("$defs", {}).get(reference.rsplit("/", 1)[-1])
        if isinstance(target, dict):
            return _schema_projection(target, root)
    properties: dict[str, Any] = {}
    for name, spec in schema.get("properties", {}).items():
        resolved = spec
        if isinstance(spec.get("$ref"), str) and spec["$ref"].startswith("#/$defs/"):
            candidate = root.get("$defs", {}).get(spec["$ref"].rsplit("/", 1)[-1])
            if isinstance(candidate, dict):
                resolved = candidate
        if "properties" in resolved or "$ref" in resolved:
            nested = _schema_projection(resolved, root)
            properties[name] = {
                "type": "object",
                "required": nested["required"],
                "properties": nested["properties"],
                "additional_properties": nested["additional_properties"],
            }
        else:
            value: dict[str, Any] = {"type": spec.get("type")}
            if "const" in spec:
                value["const"] = spec["const"]
            elif isinstance(spec.get("enum"), list) and len(spec["enum"]) == 1:
                value["const"] = spec["enum"][0]
            properties[name] = value
    return {
        "required": sorted(schema.get("required", [])),
        "properties": properties,
        "additional_properties": schema.get("additionalProperties", True) is not False,
    }


def canonical_trace(version: str, trace: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Decode only this authored migration; do not change the frozen normalizer."""

    if version not in {"v0", "v1"}:
        raise ValueError("unsupported contract version")
    result = copy.deepcopy(trace)
    for call in result:
        if version == "v1" and call["function"] in SCOPED_TOOLS:
            args = call["args"]
            expected = {"resource", "content"} if call["function"] == "append_to_file" else {"resource"}
            resource = args.get("resource")
            if set(args) != expected or not isinstance(resource, dict) or set(resource) != {"space", "file_id"}:
                raise ValueError("unexpected v1 resource arguments")
            if resource["space"] != "cloud_drive" or not isinstance(resource["file_id"], str):
                raise ValueError("invalid v1 resource scope or ID")
            del args["resource"]
            args["file_id"] = resource["file_id"]
    return result


def run_preflight(source: Path) -> dict[str, Any]:
    from experiments.agentdojo_paired_v2_capture_bridge import _runtime_metadata
    from experiments.agentdojo_paired_v2_execution_manifest import CAPTURE_RUNTIME_IDENTITY
    from experiments.agentdojo_v2_no_injecagent_default_control_contract import (
        DEFAULT_OUTPUT, _source_context, _source_score_evidence, load_contract,
        score_default_control_episode,
    )

    # Source/runtime checks precede local tool execution; no fixture re-hashing.
    runtime_identity = _runtime_metadata(CAPTURE_RUNTIME_IDENTITY)
    suite = _source_context(source.resolve())
    contract = load_contract(DEFAULT_OUTPUT)
    binding = next(row for row in contract["bindings"] if row["case_id"] == CASE_ID)
    from agentdojo.agent_pipeline.tool_execution import ToolsExecutor
    from agentdojo.functions_runtime import FunctionCall, FunctionsRuntime

    task = suite.get_user_task_by_id(TASK_ID)
    # Grants come from trusted setup, never an oracle or untrusted tool content.
    frozen = FileScopePolicy(TASK_ID, "3", "team-building-activities.docx")
    cells = []
    for defense in ("F", "M"):
        for version in ("v0", "v1"):
            policy = replace(frozen, argument_contract="v1") if (defense, version) == ("M", "v1") else frozen
            pre = task.init_environment(suite.load_and_inject_default_environment({})).model_copy(deep=True)
            pre_state = pre.model_dump(mode="json")
            pre_digest = sha256_text(canonical_json(pre_state))
            if pre_digest != binding["default_control"]["expected_pre_state_sha256"]:
                raise ValueError("default-control pre-state differs from its pinned binding")
            post = pre.model_copy(deep=True)
            base = FunctionsRuntime(suite.tools)
            if version == "v1":
                base = migrate_file_contract(base)
            runtime = FileScopeRuntime(base, policy)
            schemas = {
                name: _schema_projection(runtime.functions[name].parameters.model_json_schema())
                for name in sorted(SCOPED_TOOLS)
            }
            raw_trace = []
            # Ground truth is the authorized user sequence, not attack ground truth.
            for index, call in enumerate(task.ground_truth(pre)):
                args = copy.deepcopy(call.args)
                if version == "v1" and call.function in SCOPED_TOOLS:
                    args["resource"] = {"space": "cloud_drive", "file_id": args.pop("file_id")}
                exposed = FunctionCall(function=call.function, args=args, id=f"source-control-{index}")
                messages = [{"role": "assistant", "content": [], "tool_calls": [exposed]}]
                before_call = post.model_dump(mode="json")
                _, _, post, outputs, _ = ToolsExecutor().query(task.PROMPT, runtime, post, messages)
                if outputs[-1].get("error") is not None:
                    raise ValueError("source conformance encountered a native tool error")
                if runtime.events[-1]["decision"] == "DENY" and post.model_dump(mode="json") != before_call:
                    raise ValueError("a denied call changed the sandbox state")
                raw_trace.append(exposed.model_dump(mode="json"))
            normalized = canonical_trace(version, raw_trace)
            trace = [FunctionCall.model_validate(call) for call in normalized]
            evidence = _source_score_evidence(contract, binding, pre, post, "", trace)
            utility = score_default_control_episode(contract, CASE_ID, evidence, source)
            if utility["score_status"] != "scored":
                raise ValueError(f"source utility was not scored: {utility['not_scored_reason']}")
            cells.append({
                "cell": f"{defense}/{version}",
                "policy_sha256": policy.sha256,
                "policy_argument_contract": policy.argument_contract,
                "schema_descriptors": schemas,
                "exposed_parameter_schemas_sha256": sha256_text(canonical_json(schemas)),
                "pre_state_sha256": pre_digest,
                "post_state_sha256": utility["post_state_sha256"],
                "raw_trace_sha256": sha256_text(canonical_json(raw_trace)),
                "canonical_trace_sha256": sha256_text(canonical_json(normalized)),
                "utility_success": utility["utility_success"],
                "utility_oracle_id": utility["utility_oracle_id"],
                "policy_events": list(runtime.events),
            })
    expected = [True, False, True, True]
    if [cell["utility_success"] for cell in cells] != expected:
        raise ValueError("source utility differs from the predeclared F:10 / M:11 prediction")
    if len({cell["pre_state_sha256"] for cell in cells}) != 1:
        raise ValueError("four-cell source reset mismatch")
    if not (cells[0]["policy_sha256"] == cells[1]["policy_sha256"] == cells[2]["policy_sha256"] != cells[3]["policy_sha256"]):
        raise ValueError("F/M policy identity mismatch")
    if not (cells[0]["exposed_parameter_schemas_sha256"] == cells[2]["exposed_parameter_schemas_sha256"]
            and cells[1]["exposed_parameter_schemas_sha256"] == cells[3]["exposed_parameter_schemas_sha256"]
            and cells[0]["exposed_parameter_schemas_sha256"] != cells[1]["exposed_parameter_schemas_sha256"]):
        raise ValueError("schema contrast is not matched across defenses")
    return {
        "schema_version": "task-file-scope-source-preflight/v1",
        "evidence_tier": "T1_source_conformance_only",
        "canonical_v2_result_bundle": False,
        "defense_family": FAMILY,
        "case_id": CASE_ID,
        "source_cluster_id": "workspace:v1.2.2:user_task_29",
        "source": contract["source"]["verification_witness"],
        "runtime_identity": runtime_identity,
        "implementation_sha256": {
            name: hashlib.sha256((ROOT / "experiments" / name).read_bytes()).hexdigest()
            for name in ("agentdojo_file_scope_defense.py", "agentdojo_file_scope_preflight.py")
        },
        "model_requests": 0, "remote_jobs": 0,
        "attack_episodes_executed": 0,
        "cells": cells,
        "remaining_gate": "prospective manifest/validator/trace amendment and independent review",
        "non_claim": "source utility conformance only; no LLM or harmful-effect regression observation",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=ROOT / "tmp" / "agentdojo-source")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    output = args.output.resolve() if args.output else None
    if output is not None and not output.is_relative_to(ROOT / "qa"):
        parser.error("source-conformance output must remain under ignored qa/")
    report = run_preflight(args.source)
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + chr(10), encoding="utf-8")
    print(json.dumps({
        "evidence_tier": report["evidence_tier"],
        "cells": {row["cell"]: row["utility_success"] for row in report["cells"]},
        "model_requests": 0,
    }, indent=2))


if __name__ == "__main__":
    main()
