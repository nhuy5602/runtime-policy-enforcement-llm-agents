"""Episode-plan/result adapter for the opt-in TaskFileScope capture path.

The adapter decorates one historical v2 episode plan in memory. The historical
manifest remains the identity anchor; adapter fields are stripped before the
capture bridge compares the base plan. No network or model call occurs here.
"""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any

from experiments.agentdojo_file_scope_amendment import (
    CASE_ID,
    DEFAULT_OUTPUT as AMENDMENT,
    SOURCE_CLUSTER_ID,
    build_manifest,
    validate_manifest,
)


ROOT = Path(__file__).resolve().parents[1]
ADAPTER_ID = "TaskFileScope"


def _file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_adapter_plan(base_plan: dict[str, Any], defense_variant: str) -> dict[str, Any]:
    """Decorate a canonical v2 plan with explicit amendment identity."""

    if defense_variant not in {"F", "M"}:
        raise ValueError("defense_variant must be F or M")
    if base_plan.get("case_id") != CASE_ID or base_plan.get("user_task_id") != "user_task_29":
        raise ValueError("TaskFileScope adapter is bound to the selected user_task_29 case")
    if base_plan.get("source_cluster_id") != SOURCE_CLUSTER_ID:
        raise ValueError("TaskFileScope adapter source cluster mismatch")
    manifest = build_manifest()
    validate_manifest(manifest)
    version = base_plan.get("contract", {}).get("version")
    if version not in {"v0", "v1"}:
        raise ValueError("base plan must expose v0 or v1")
    cell = f"{defense_variant}/{version}"
    cell_binding = next(row for row in manifest["cells"] if row["cell"] == cell)
    decorated = copy.deepcopy(base_plan)
    decorated.update(
        {
            "defense_adapter_id": ADAPTER_ID,
            "defense_variant": defense_variant,
            "amendment_manifest_sha256": _file_sha(AMENDMENT),
            "amendment_cell": cell,
            "amendment_policy_sha256": manifest["policy_variants"][defense_variant][version]["policy_sha256"],
            "amendment_schema_descriptor_sha256": manifest["schema_descriptor_sha256"][version],
            "amendment_normalization_sha256": manifest["argument_normalization_sha256"],
            "amendment_expected_utility_success": cell_binding["expected_utility_success"],
        }
    )
    return decorated


def validate_adapter_record(record: dict[str, Any], plan: dict[str, Any]) -> dict[str, Any]:
    """Accept only a record carrying adapter identity and every policy event."""

    if plan.get("defense_adapter_id") != ADAPTER_ID:
        raise ValueError("plan is not a TaskFileScope adapter plan")
    for field in (
        "defense_adapter_id",
        "defense_variant",
        "amendment_manifest_sha256",
        "amendment_cell",
        "amendment_policy_sha256",
        "amendment_schema_descriptor_sha256",
        "amendment_normalization_sha256",
    ):
        if field not in record:
            raise ValueError(f"adapter record missing {field}")
    if record["defense_adapter_id"] != plan["defense_adapter_id"]:
        raise ValueError("adapter identity mismatch")
    for field in (
        "defense_variant",
        "amendment_manifest_sha256",
        "amendment_cell",
        "amendment_policy_sha256",
        "amendment_schema_descriptor_sha256",
        "amendment_normalization_sha256",
    ):
        if record[field] != plan[field]:
            raise ValueError(f"adapter record mismatch: {field}")
    trace = record.get("redacted_trace")
    content = trace.get("content") if isinstance(trace, dict) else None
    events = content.get("per_dispatch_policy_events") if isinstance(content, dict) else None
    if not isinstance(events, list) or not events:
        raise ValueError("adapter record lacks per-dispatch policy events")
    for event in events:
        if not isinstance(event, dict):
            raise ValueError("malformed adapter policy event")
        required = (
            "ordinal", "tool", "policy_sha256", "arguments_sha256", "decision",
            "dispatched", "tool_error", "pre_state_sha256", "post_state_sha256",
        )
        if any(field not in event for field in required):
            raise ValueError("adapter policy event is incomplete")
        if event["policy_sha256"] != plan["amendment_policy_sha256"]:
            raise ValueError("adapter policy event hash mismatch")
        if event["decision"] == "DENY":
            if event["dispatched"] is not False or event["tool_error"] is not False:
                raise ValueError("adapter denial crossed native dispatch")
            if event["pre_state_sha256"] != event["post_state_sha256"]:
                raise ValueError("adapter denial changed state")
        elif event["decision"] == "ALLOW":
            if event["dispatched"] is not True:
                raise ValueError("adapter allow was not dispatched")
        else:
            raise ValueError("unknown adapter policy decision")
    return {"status": "adapter_record_accepted", "event_count": len(events), "cell": plan["amendment_cell"]}
