"""Offline policy-conformance simulator for the Runtime Policy Guard proposal.

This is not an LLM benchmark. It tests whether a tool-boundary policy blocks
pre-recorded harmful tool calls and preserves explicitly permitted calls.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
from dataclasses import asdict, dataclass
from enum import StrEnum
from pathlib import Path


class Decision(StrEnum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    REQUIRE_APPROVAL = "REQUIRE_APPROVAL"


@dataclass(frozen=True)
class Capability:
    task_id: str
    tool: str
    operation: str
    resource: str
    destinations: tuple[str, ...] = ()
    max_calls: int = 1
    approval_required: bool = False


@dataclass(frozen=True)
class ToolCall:
    case_id: str
    task_id: str
    tool: str
    operation: str
    resource: str
    destination: str = ""
    carries_sensitive_data: bool = False
    is_harmful: bool = False
    is_benign: bool = False
    attack_type: str = ""
    security_oracle: str = ""
    utility_oracle: str = ""


@dataclass(frozen=True)
class Outcome:
    case_id: str
    decision: Decision
    reason: str
    harmful: bool
    benign: bool
    executed: bool


class PolicyGuard:
    """A small, deterministic reference gateway for mock-tool calls."""

    def __init__(self, capabilities: tuple[Capability, ...]):
        self.capabilities = capabilities
        self.call_counts: dict[Capability, int] = {}

    def decide(self, call: ToolCall) -> tuple[Decision, str]:
        candidate = next(
            (
                capability
                for capability in self.capabilities
                if capability.task_id == call.task_id
                and capability.tool == call.tool
                and capability.operation == call.operation
                and capability.resource == call.resource
            ),
            None,
        )
        if candidate is None:
            return Decision.DENY, "outside_task_capability"
        if call.destination and call.destination not in candidate.destinations:
            return Decision.DENY, "destination_not_allowed"
        if call.carries_sensitive_data and call.destination:
            return Decision.DENY, "sensitive_egress_denied"
        count = self.call_counts.get(candidate, 0)
        if count >= candidate.max_calls:
            return Decision.DENY, "capability_call_limit_reached"
        self.call_counts[candidate] = count + 1
        if candidate.approval_required:
            return Decision.REQUIRE_APPROVAL, "approved_scope_requires_human_review"
        return Decision.ALLOW, "capability_allows_call"


class MockToolExecutor:
    """Records side effects instead of contacting a real tool or network."""

    def __init__(self) -> None:
        self.side_effects: list[str] = []

    def execute(self, call: ToolCall) -> None:
        self.side_effects.append(call.case_id)


FIXTURE_DIR = Path(__file__).with_name("fixtures")
DEFAULT_POLICY = FIXTURE_DIR / "policy_v1.json"
DEFAULT_CASES = FIXTURE_DIR / "cases_v1.json"


def read_json(path: Path) -> dict[str, object]:
    with path.open(encoding="utf-8") as file:
        return json.load(file)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_fixtures(policy_path: Path, cases_path: Path) -> dict[str, dict[str, str]]:
    policy = read_json(policy_path)
    cases = read_json(cases_path)
    assert policy["schema_version"] == "runtime-policy-fixtures/v1"
    assert cases["schema_version"] == policy["schema_version"]
    assert cases["suite_id"] == policy["suite_id"]

    raw_cases = cases["cases"]
    case_ids = [item["case_id"] for item in raw_cases]
    ordinals = [item["ordinal"] for item in raw_cases]
    assert len(case_ids) == len(set(case_ids))
    assert ordinals == list(range(1, len(raw_cases) + 1))
    for item in raw_cases:
        assert item["is_harmful"] != item["is_benign"]
        assert set(item["reference_assertion"]) == {"decision", "reason"}
    return {item["case_id"]: item["reference_assertion"] for item in raw_cases}


def load_policy(path: Path) -> tuple[tuple[Capability, ...], frozenset[str]]:
    raw = read_json(path)
    capabilities = tuple(
        Capability(
            task_id=item["task_id"],
            tool=item["tool"],
            operation=item["operation"],
            resource=item["resource"],
            destinations=tuple(item.get("destinations", [])),
            max_calls=item.get("max_calls", 1),
            approval_required=item.get("approval_required", False),
        )
        for item in raw["capabilities"]
    )
    return capabilities, frozenset(raw["static_allowlist"])


def load_cases(path: Path) -> tuple[ToolCall, ...]:
    raw = read_json(path)
    return tuple(
        ToolCall(
            case_id=item["case_id"],
            task_id=item["task_id"],
            tool=item["tool"],
            operation=item["operation"],
            resource=item["resource"],
            destination=item.get("destination", ""),
            carries_sensitive_data=item.get("carries_sensitive_data", False),
            is_harmful=item.get("is_harmful", False),
            is_benign=item.get("is_benign", False),
            attack_type=item.get("attack_type", ""),
            security_oracle=item.get("security_oracle", ""),
            utility_oracle=item.get("utility_oracle", ""),
        )
        for item in raw["cases"]
    )


def baseline_decision(
    configuration: str, call: ToolCall, static_allowlist: frozenset[str]
) -> tuple[Decision, str]:
    if configuration == "C0_schema_only":
        return Decision.ALLOW, "schema_valid_without_policy_enforcement"
    if configuration == "C1_static_allowlist":
        allowed = f"{call.tool}.{call.operation}" in static_allowlist
        return (
            (Decision.ALLOW, "tool_in_static_allowlist")
            if allowed
            else (Decision.DENY, "tool_not_in_static_allowlist")
        )
    raise ValueError(f"Unknown baseline: {configuration}")


def evaluate(
    configuration: str,
    capabilities: tuple[Capability, ...],
    cases: tuple[ToolCall, ...],
    static_allowlist: frozenset[str],
    fixture_hashes: dict[str, str],
) -> dict[str, object]:
    guard = PolicyGuard(capabilities)
    executor = MockToolExecutor()
    outcomes: list[Outcome] = []
    for call in cases:
        if configuration == "C2_policy_guard":
            decision, reason = guard.decide(call)
        else:
            decision, reason = baseline_decision(configuration, call, static_allowlist)
        executed = decision == Decision.ALLOW
        if executed:
            executor.execute(call)
        outcomes.append(
            Outcome(call.case_id, decision, reason, call.is_harmful, call.is_benign, executed)
        )

    harmful = [outcome for outcome in outcomes if outcome.harmful]
    benign = [outcome for outcome in outcomes if outcome.benign]
    blocked_harmful = sum(outcome.decision == Decision.DENY for outcome in harmful)
    harmful_executions = sum(outcome.executed for outcome in harmful)
    automatic_benign = sum(outcome.decision == Decision.ALLOW for outcome in benign)
    approvals = sum(outcome.decision == Decision.REQUIRE_APPROVAL for outcome in outcomes)
    return {
        "configuration": configuration,
        "scope": "policy_conformance_simulation_not_an_llm_benchmark",
        "fixture_sha256": fixture_hashes,
        "harmful_cases": len(harmful),
        "blocked_harmful_cases": blocked_harmful,
        "harmful_executions": harmful_executions,
        "policy_stop_rate": blocked_harmful / len(harmful),
        "benign_cases": len(benign),
        "automatic_benign_success_rate": automatic_benign / len(benign),
        "approval_eligible_benign_rate": (
            sum(outcome.decision == Decision.REQUIRE_APPROVAL for outcome in benign) / len(benign)
        ),
        "approval_count": approvals,
        "harness_dispatch_coverage": len(outcomes) / len(cases),
        "mock_side_effects": executor.side_effects,
        "outcomes": [asdict(outcome) for outcome in outcomes],
    }


def self_test(
    capabilities: tuple[Capability, ...],
    cases: tuple[ToolCall, ...],
    static_allowlist: frozenset[str],
    fixture_hashes: dict[str, str],
    reference_assertions: dict[str, dict[str, str]],
) -> None:
    proposed = evaluate("C2_policy_guard", capabilities, cases, static_allowlist, fixture_hashes)
    schema_only = evaluate("C0_schema_only", capabilities, cases, static_allowlist, fixture_hashes)
    static = evaluate("C1_static_allowlist", capabilities, cases, static_allowlist, fixture_hashes)

    assert proposed["blocked_harmful_cases"] == proposed["harmful_cases"]
    assert proposed["harmful_executions"] == 0
    assert schema_only["blocked_harmful_cases"] == 0
    assert static["blocked_harmful_cases"] < proposed["blocked_harmful_cases"]
    outcomes = {item["case_id"]: item for item in proposed["outcomes"]}
    for case_id, assertion in reference_assertions.items():
        assert outcomes[case_id]["decision"] == assertion["decision"]
        assert outcomes[case_id]["reason"] == assertion["reason"]
    assert outcomes["benign_read_public"]["decision"] == Decision.ALLOW
    assert outcomes["benign_high_risk_send"]["decision"] == Decision.REQUIRE_APPROVAL
    assert outcomes["benign_ticket_update"]["decision"] == Decision.ALLOW


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--output", help="Optional JSON result path")
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    args = parser.parse_args()
    reference_assertions = validate_fixtures(args.policy, args.cases)
    capabilities, static_allowlist = load_policy(args.policy)
    cases = load_cases(args.cases)
    fixture_hashes = {
        "policy": sha256(args.policy),
        "cases": sha256(args.cases),
        "runner": sha256(Path(__file__)),
    }
    self_test(capabilities, cases, static_allowlist, fixture_hashes, reference_assertions)
    report = {
        name: evaluate(name, capabilities, cases, static_allowlist, fixture_hashes)
        for name in ("C0_schema_only", "C1_static_allowlist", "C2_policy_guard")
    }
    report["_reproducibility"] = {
        "python_version": platform.python_version(),
        "fixture_schema": "runtime-policy-fixtures/v1",
        "suite_id": "reference-policy-guard-v1",
        "fixture_sha256": fixture_hashes,
    }
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as file:
            file.write(rendered + "\n")
    print(rendered)


if __name__ == "__main__":
    main()
