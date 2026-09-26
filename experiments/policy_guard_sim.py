"""Offline conformance checks for a mock runtime policy gateway.

This module deliberately does not invoke an LLM, browse external content, or
contact real tools. It checks that a fixed policy, a mock dispatcher, and
action-grounded fixture oracles agree at a tool-execution boundary.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import platform
from collections import defaultdict
from dataclasses import asdict, dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any


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
    destinations: tuple[str, ...]
    max_calls: int
    approval_required: bool


@dataclass(frozen=True)
class ToolCall:
    case_id: str
    episode_id: str
    ordinal: int
    step: int
    kind: str
    task_id: str
    tool: str
    operation: str
    resource: str
    destination: str
    carries_sensitive_data: bool
    attack_type: str
    security_oracle: dict[str, object] | None
    utility_oracle: dict[str, object] | None
    expected_policy_trace: dict[str, str]


@dataclass(frozen=True)
class ExecutionEvent:
    effect_id: str
    case_id: str
    episode_id: str
    tool: str
    operation: str
    resource: str
    destination: str


@dataclass(frozen=True)
class AuditEvent:
    case_id: str
    episode_id: str
    initial_decision: Decision
    initial_reason: str
    final_decision: Decision
    final_reason: str
    approval_status: str
    executed: bool
    effect_id: str | None


@dataclass(frozen=True)
class Outcome:
    case_id: str
    episode_id: str
    kind: str
    initial_decision: Decision
    initial_reason: str
    final_decision: Decision
    final_reason: str
    approval_status: str
    executed: bool
    effect_id: str | None


FIXTURE_DIR = Path(__file__).with_name("fixtures")
DEFAULT_POLICY = FIXTURE_DIR / "policy_v1.json"
DEFAULT_CASES = FIXTURE_DIR / "cases_v1.json"
SCHEMA_VERSION = "runtime-policy-fixtures/v1"
SUITE_ID = "reference-policy-guard-v1"
CONFIGURATIONS = ("C0_schema_only", "C1_static_allowlist", "C2_policy_guard")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def expect_value_error(action: Any, message: str) -> None:
    try:
        action()
    except ValueError:
        return
    raise RuntimeError(message)


def canonical_text(value: str) -> str:
    return value.strip().casefold()


def required_string(payload: dict[str, object], key: str, context: str) -> str:
    value = payload.get(key)
    require(isinstance(value, str) and value.strip(), f"{context}.{key} must be a non-empty string")
    return value


def required_mapping(payload: dict[str, object], key: str, context: str) -> dict[str, object]:
    value = payload.get(key)
    require(isinstance(value, dict), f"{context}.{key} must be an object")
    return value


def required_list(payload: dict[str, object], key: str, context: str) -> list[object]:
    value = payload.get(key)
    require(isinstance(value, list), f"{context}.{key} must be an array")
    return value


def require_canonical(value: str, context: str) -> None:
    require(value == canonical_text(value), f"{context} must be canonical lowercase text")


def read_json(path: Path) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise ValueError(f"Could not read fixture {path}: {error}") from error
    except json.JSONDecodeError as error:
        raise ValueError(f"Fixture {path} is not valid JSON: {error}") from error
    require(isinstance(payload, dict), f"Fixture {path} must contain a JSON object")
    return payload


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_effect_signature(value: object, context: str) -> None:
    require(isinstance(value, dict), f"{context} must be an object")
    expected = {"tool", "operation", "resource", "destination"}
    require(set(value) == expected, f"{context} must contain exactly {sorted(expected)}")
    for key in expected:
        item = value[key]
        require(isinstance(item, str), f"{context}.{key} must be a string")
        if key != "destination":
            require(bool(item.strip()), f"{context}.{key} must not be empty")
        require_canonical(item, f"{context}.{key}")


def validate_policy_payload(policy: dict[str, object]) -> None:
    require(policy.get("schema_version") == SCHEMA_VERSION, "Unsupported policy schema_version")
    require(policy.get("suite_id") == SUITE_ID, "Unexpected policy suite_id")
    require(isinstance(policy.get("scope"), str) and policy["scope"], "policy.scope must be set")

    execution = required_mapping(policy, "execution", "policy")
    expected_execution = {
        "case_order": "ordinal_ascending",
        "state_reset": "per_episode",
        "guard_state": "shared_within_episode",
        "executor_state": "shared_within_episode",
    }
    require(execution == expected_execution, "policy.execution does not match the supported semantics")

    allowlist = required_list(policy, "static_allowlist", "policy")
    require(bool(allowlist), "policy.static_allowlist must not be empty")
    allowlist_values: list[str] = []
    for index, item in enumerate(allowlist):
        require(isinstance(item, str) and item.count(".") == 1, f"static_allowlist[{index}] is invalid")
        require_canonical(item, f"static_allowlist[{index}]")
        allowlist_values.append(item)
    require(len(allowlist_values) == len(set(allowlist_values)), "policy.static_allowlist has duplicates")

    capabilities = required_list(policy, "capabilities", "policy")
    require(bool(capabilities), "policy.capabilities must not be empty")
    capability_keys: set[tuple[str, str, str, str]] = set()
    for index, raw in enumerate(capabilities):
        context = f"policy.capabilities[{index}]"
        require(isinstance(raw, dict), f"{context} must be an object")
        fields = ("task_id", "tool", "operation", "resource")
        values = tuple(required_string(raw, key, context) for key in fields)
        for key, value in zip(fields, values, strict=True):
            require_canonical(value, f"{context}.{key}")
        require(values not in capability_keys, f"{context} duplicates a capability")
        capability_keys.add(values)

        destinations = required_list(raw, "destinations", context)
        destination_values: list[str] = []
        for destination_index, destination in enumerate(destinations):
            require(
                isinstance(destination, str) and destination.strip(),
                f"{context}.destinations[{destination_index}] must be a non-empty string",
            )
            require_canonical(destination, f"{context}.destinations[{destination_index}]")
            destination_values.append(destination)
        require(
            len(destination_values) == len(set(destination_values)),
            f"{context}.destinations has duplicates",
        )

        max_calls = raw.get("max_calls")
        require(
            isinstance(max_calls, int) and not isinstance(max_calls, bool) and max_calls > 0,
            f"{context}.max_calls must be a positive integer",
        )
        require(
            isinstance(raw.get("approval_required"), bool),
            f"{context}.approval_required must be boolean",
        )


def validate_case_payload(cases: dict[str, object], policy: dict[str, object]) -> None:
    require(cases.get("schema_version") == SCHEMA_VERSION, "Unsupported case schema_version")
    require(cases.get("suite_id") == policy.get("suite_id"), "Case/policy suite_id mismatch")
    require(isinstance(cases.get("scope"), str) and cases["scope"], "cases.scope must be set")

    raw_cases = required_list(cases, "cases", "cases")
    require(bool(raw_cases), "cases.cases must not be empty")
    case_ids: list[str] = []
    ordinals: list[int] = []
    episode_steps: dict[str, list[int]] = defaultdict(list)

    expected_trace_keys = {
        "initial_decision",
        "initial_reason",
        "final_decision",
        "final_reason",
    }
    for index, raw in enumerate(raw_cases):
        context = f"cases.cases[{index}]"
        require(isinstance(raw, dict), f"{context} must be an object")
        case_id = required_string(raw, "case_id", context)
        episode_id = required_string(raw, "episode_id", context)
        require_canonical(case_id, f"{context}.case_id")
        require_canonical(episode_id, f"{context}.episode_id")
        case_ids.append(case_id)

        ordinal = raw.get("ordinal")
        step = raw.get("step")
        require(
            isinstance(ordinal, int) and not isinstance(ordinal, bool) and ordinal > 0,
            f"{context}.ordinal must be a positive integer",
        )
        require(
            isinstance(step, int) and not isinstance(step, bool) and step > 0,
            f"{context}.step must be a positive integer",
        )
        ordinals.append(ordinal)
        episode_steps[episode_id].append(step)

        kind = raw.get("kind")
        require(kind in {"attack", "benign"}, f"{context}.kind must be attack or benign")
        for key in ("task_id", "tool", "operation", "resource", "destination", "attack_type"):
            value = raw.get(key)
            require(isinstance(value, str), f"{context}.{key} must be a string")
            if key not in {"destination", "attack_type"}:
                require(bool(value.strip()), f"{context}.{key} must not be empty")
            require_canonical(value, f"{context}.{key}")
        require(isinstance(raw.get("carries_sensitive_data"), bool), f"{context}.carries_sensitive_data must be boolean")

        security_oracle = raw.get("security_oracle")
        utility_oracle = raw.get("utility_oracle")
        if kind == "attack":
            require(bool(raw["attack_type"]), f"{context}.attack_type is required for attack cases")
            require(isinstance(security_oracle, dict), f"{context}.security_oracle must be an object")
            require(set(security_oracle) == {"forbidden_effect"}, f"{context}.security_oracle is invalid")
            validate_effect_signature(security_oracle["forbidden_effect"], f"{context}.security_oracle.forbidden_effect")
            require(utility_oracle is None, f"{context}.utility_oracle must be null for attacks")
        else:
            require(not raw["attack_type"], f"{context}.attack_type must be empty for benign cases")
            require(security_oracle is None, f"{context}.security_oracle must be null for benign cases")
            require(isinstance(utility_oracle, dict), f"{context}.utility_oracle must be an object")
            require(
                set(utility_oracle) == {"expected_effect", "completion_mode", "simulated_approval"},
                f"{context}.utility_oracle is invalid",
            )
            validate_effect_signature(utility_oracle["expected_effect"], f"{context}.utility_oracle.expected_effect")
            completion_mode = utility_oracle["completion_mode"]
            approval = utility_oracle["simulated_approval"]
            require(
                completion_mode in {"automatic", "approval_required"},
                f"{context}.utility_oracle.completion_mode is invalid",
            )
            require(
                approval in {"not_required", "approved", "rejected"},
                f"{context}.utility_oracle.simulated_approval is invalid",
            )
            if completion_mode == "automatic":
                require(approval == "not_required", f"{context} automatic calls cannot request approval")
            else:
                require(approval in {"approved", "rejected"}, f"{context} approval outcome is required")

        trace = required_mapping(raw, "reference_assertion", context)
        require(set(trace) == expected_trace_keys, f"{context}.reference_assertion is invalid")
        for trace_key, trace_value in trace.items():
            require(isinstance(trace_value, str) and trace_value, f"{context}.reference_assertion.{trace_key} must be set")
        require(trace["initial_decision"] in Decision, f"{context} has an invalid initial decision")
        require(trace["final_decision"] in Decision, f"{context} has an invalid final decision")

    require(len(case_ids) == len(set(case_ids)), "cases.cases has duplicate case_id")
    require(ordinals == list(range(1, len(raw_cases) + 1)), "cases.cases ordinal must be contiguous and ordered")
    for episode_id, steps in episode_steps.items():
        require(
            sorted(steps) == list(range(1, len(steps) + 1)),
            f"Episode {episode_id} steps must be contiguous from one",
        )


def validate_fixture_payloads(policy: dict[str, object], cases: dict[str, object]) -> None:
    validate_policy_payload(policy)
    validate_case_payload(cases, policy)


def validate_fixtures(policy_path: Path, cases_path: Path) -> None:
    validate_fixture_payloads(read_json(policy_path), read_json(cases_path))


def load_policy(path: Path) -> tuple[tuple[Capability, ...], frozenset[str]]:
    raw = read_json(path)
    capabilities = tuple(
        Capability(
            task_id=item["task_id"],
            tool=item["tool"],
            operation=item["operation"],
            resource=item["resource"],
            destinations=tuple(item["destinations"]),
            max_calls=item["max_calls"],
            approval_required=item["approval_required"],
        )
        for item in raw["capabilities"]
    )
    return capabilities, frozenset(raw["static_allowlist"])


def load_cases(path: Path) -> tuple[ToolCall, ...]:
    raw = read_json(path)
    return tuple(
        ToolCall(
            case_id=item["case_id"],
            episode_id=item["episode_id"],
            ordinal=item["ordinal"],
            step=item["step"],
            kind=item["kind"],
            task_id=item["task_id"],
            tool=item["tool"],
            operation=item["operation"],
            resource=item["resource"],
            destination=item["destination"],
            carries_sensitive_data=item["carries_sensitive_data"],
            attack_type=item["attack_type"],
            security_oracle=item["security_oracle"],
            utility_oracle=item["utility_oracle"],
            expected_policy_trace=item["reference_assertion"],
        )
        for item in raw["cases"]
    )


class PolicyGuard:
    """Two-phase reference monitor: evaluate first, consume only at execution."""

    def __init__(self, capabilities: tuple[Capability, ...]) -> None:
        self.capabilities = capabilities
        self.call_counts: dict[Capability, int] = {}

    def preflight(self, call: ToolCall) -> tuple[Capability | None, Decision, str]:
        capability = next(
            (
                candidate
                for candidate in self.capabilities
                if candidate.task_id == call.task_id
                and candidate.tool == call.tool
                and candidate.operation == call.operation
                and candidate.resource == call.resource
            ),
            None,
        )
        if capability is None:
            return None, Decision.DENY, "outside_task_capability"
        if call.destination and call.destination not in capability.destinations:
            return capability, Decision.DENY, "destination_not_allowed"
        if call.carries_sensitive_data and call.destination:
            return capability, Decision.DENY, "sensitive_egress_denied"
        if self.call_counts.get(capability, 0) >= capability.max_calls:
            return capability, Decision.DENY, "capability_call_limit_reached"
        if capability.approval_required:
            return capability, Decision.REQUIRE_APPROVAL, "approved_scope_requires_human_review"
        return capability, Decision.ALLOW, "capability_allows_call"

    def commit_automatic(self, call: ToolCall) -> tuple[Decision, str]:
        capability, decision, reason = self.preflight(call)
        if decision != Decision.ALLOW:
            return decision, reason
        require(capability is not None, "Policy guard lost an approved capability")
        self.call_counts[capability] = self.call_counts.get(capability, 0) + 1
        return Decision.ALLOW, reason

    def commit_approved(self, call: ToolCall, approved: bool) -> tuple[Decision, str]:
        capability, decision, reason = self.preflight(call)
        if decision != Decision.REQUIRE_APPROVAL:
            return decision, reason
        if not approved:
            return Decision.DENY, "approval_rejected"
        require(capability is not None, "Policy guard lost an approval capability")
        self.call_counts[capability] = self.call_counts.get(capability, 0) + 1
        return Decision.ALLOW, "approval_granted_and_capability_allows_call"

    def calls_used(self, capability: Capability) -> int:
        return self.call_counts.get(capability, 0)


class MockToolExecutor:
    """Records a mock effect only when the dispatcher presents its private token."""

    def __init__(self, dispatch_token: object) -> None:
        self._dispatch_token = dispatch_token
        self.events: list[ExecutionEvent] = []

    def execute(self, call: ToolCall, dispatch_token: object) -> ExecutionEvent:
        if dispatch_token is not self._dispatch_token:
            raise PermissionError("Mock tool execution requires dispatcher authorization")
        event = ExecutionEvent(
            effect_id=f"effect:{call.case_id}",
            case_id=call.case_id,
            episode_id=call.episode_id,
            tool=call.tool,
            operation=call.operation,
            resource=call.resource,
            destination=call.destination,
        )
        self.events.append(event)
        return event


class ToolDispatcher:
    """The only harness path from a proposed tool call to a mock effect."""

    def __init__(
        self,
        configuration: str,
        capabilities: tuple[Capability, ...],
        static_allowlist: frozenset[str],
    ) -> None:
        self.configuration = configuration
        self.static_allowlist = static_allowlist
        self.guard = PolicyGuard(capabilities)
        self._dispatch_token = object()
        self.executor = MockToolExecutor(self._dispatch_token)

    def dispatch(self, call: ToolCall) -> tuple[Outcome, AuditEvent]:
        initial_decision, initial_reason, approval_status = self._initial_decision(call)
        final_decision = initial_decision
        final_reason = initial_reason

        if self.configuration == "C2_policy_guard":
            if initial_decision == Decision.ALLOW:
                final_decision, final_reason = self.guard.commit_automatic(call)
            elif initial_decision == Decision.REQUIRE_APPROVAL:
                approved = self._simulated_approval(call) == "approved"
                approval_status = "approved" if approved else "rejected"
                final_decision, final_reason = self.guard.commit_approved(call, approved)

        effect: ExecutionEvent | None = None
        if final_decision == Decision.ALLOW:
            effect = self.executor.execute(call, self._dispatch_token)

        outcome = Outcome(
            case_id=call.case_id,
            episode_id=call.episode_id,
            kind=call.kind,
            initial_decision=initial_decision,
            initial_reason=initial_reason,
            final_decision=final_decision,
            final_reason=final_reason,
            approval_status=approval_status,
            executed=effect is not None,
            effect_id=effect.effect_id if effect else None,
        )
        audit = AuditEvent(
            case_id=call.case_id,
            episode_id=call.episode_id,
            initial_decision=initial_decision,
            initial_reason=initial_reason,
            final_decision=final_decision,
            final_reason=final_reason,
            approval_status=approval_status,
            executed=effect is not None,
            effect_id=effect.effect_id if effect else None,
        )
        return outcome, audit

    def _initial_decision(self, call: ToolCall) -> tuple[Decision, str, str]:
        if self.configuration == "C0_schema_only":
            return Decision.ALLOW, "schema_valid_without_policy_enforcement", "not_requested"
        if self.configuration == "C1_static_allowlist":
            allowed = f"{call.tool}.{call.operation}" in self.static_allowlist
            if allowed:
                return Decision.ALLOW, "tool_in_static_allowlist", "not_requested"
            return Decision.DENY, "tool_not_in_static_allowlist", "not_requested"
        if self.configuration == "C2_policy_guard":
            _, decision, reason = self.guard.preflight(call)
            return decision, reason, "not_requested"
        raise ValueError(f"Unknown configuration: {self.configuration}")

    @staticmethod
    def _simulated_approval(call: ToolCall) -> str:
        if call.utility_oracle is None:
            return "not_requested"
        return str(call.utility_oracle["simulated_approval"])


def group_episodes(cases: tuple[ToolCall, ...]) -> list[tuple[str, tuple[ToolCall, ...]]]:
    grouped: dict[str, list[ToolCall]] = {}
    for call in sorted(cases, key=lambda item: item.ordinal):
        grouped.setdefault(call.episode_id, []).append(call)
    return [
        (episode_id, tuple(sorted(episode_cases, key=lambda item: item.step)))
        for episode_id, episode_cases in grouped.items()
    ]


def effect_matches(effect: ExecutionEvent, signature: dict[str, object]) -> bool:
    return all(getattr(effect, key) == signature[key] for key in ("tool", "operation", "resource", "destination"))


def score_outcomes(
    cases: tuple[ToolCall, ...],
    outcomes: list[Outcome],
    effects: list[ExecutionEvent],
) -> dict[str, object]:
    outcomes_by_case = {outcome.case_id: outcome for outcome in outcomes}
    effects_by_case: dict[str, list[ExecutionEvent]] = defaultdict(list)
    for effect in effects:
        effects_by_case[effect.case_id].append(effect)

    attack_cases = [call for call in cases if call.kind == "attack"]
    benign_cases = [call for call in cases if call.kind == "benign"]
    attack_successes = 0
    benign_task_completions = 0
    automatic_benign_completions = 0
    approved_benign_completions = 0
    unapproved_high_risk_completions = 0
    false_denials = 0

    for call in attack_cases:
        signature = call.security_oracle["forbidden_effect"]  # validated above
        attack_successes += int(
            any(effect_matches(effect, signature) for effect in effects_by_case[call.case_id])
        )

    for call in benign_cases:
        signature = call.utility_oracle["expected_effect"]  # validated above
        completion_mode = call.utility_oracle["completion_mode"]
        outcome = outcomes_by_case[call.case_id]
        completed = any(effect_matches(effect, signature) for effect in effects_by_case[call.case_id])
        if completed:
            benign_task_completions += 1
            if completion_mode == "automatic":
                automatic_benign_completions += 1
            elif outcome.approval_status == "approved":
                approved_benign_completions += 1
            else:
                unapproved_high_risk_completions += 1
        if outcome.final_decision == Decision.DENY:
            false_denials += 1

    approvals = sum(outcome.initial_decision == Decision.REQUIRE_APPROVAL for outcome in outcomes)
    return {
        "attack_cases": len(attack_cases),
        "attack_cases_with_forbidden_effect": attack_successes,
        "attack_block_rate": (len(attack_cases) - attack_successes) / len(attack_cases),
        "benign_cases": len(benign_cases),
        "benign_task_completions": benign_task_completions,
        "automatic_benign_completions": automatic_benign_completions,
        "approved_benign_completions": approved_benign_completions,
        "unapproved_high_risk_completions": unapproved_high_risk_completions,
        "benign_task_success_rate": benign_task_completions / len(benign_cases),
        "false_denials": false_denials,
        "approval_requests": approvals,
        "harness_dispatch_coverage": len(outcomes) / len(cases),
    }


def assert_execution_invariants(
    cases: tuple[ToolCall, ...],
    outcomes: list[Outcome],
    audits: list[AuditEvent],
    effects: list[ExecutionEvent],
) -> None:
    require(len(outcomes) == len(cases), "Every case must produce an outcome")
    require(len(audits) == len(cases), "Every case must produce an audit event")
    require(
        {outcome.case_id for outcome in outcomes} == {call.case_id for call in cases},
        "Outcome case IDs do not match fixture case IDs",
    )
    require(
        {audit.case_id for audit in audits} == {call.case_id for call in cases},
        "Audit case IDs do not match fixture case IDs",
    )
    outcomes_by_case = {outcome.case_id: outcome for outcome in outcomes}
    audits_by_case = {audit.case_id: audit for audit in audits}
    for case_id, outcome in outcomes_by_case.items():
        audit = audits_by_case[case_id]
        require(asdict(outcome) == asdict(audit) | {"kind": outcome.kind}, "Audit/outcome mismatch")
        require(
            outcome.executed == (outcome.effect_id is not None),
            f"{case_id} execution/effect invariant failed",
        )
    require(
        {effect.case_id for effect in effects} == {
            outcome.case_id for outcome in outcomes if outcome.executed
        },
        "Mock effects do not match allowed outcomes",
    )


def evaluate(
    configuration: str,
    capabilities: tuple[Capability, ...],
    cases: tuple[ToolCall, ...],
    static_allowlist: frozenset[str],
    fixture_hashes: dict[str, str],
) -> dict[str, object]:
    outcomes: list[Outcome] = []
    audits: list[AuditEvent] = []
    effects: list[ExecutionEvent] = []
    for _, episode_cases in group_episodes(cases):
        dispatcher = ToolDispatcher(configuration, capabilities, static_allowlist)
        for call in episode_cases:
            outcome, audit = dispatcher.dispatch(call)
            outcomes.append(outcome)
            audits.append(audit)
            effects.extend(dispatcher.executor.events[-1:] if outcome.executed else [])

    assert_execution_invariants(cases, outcomes, audits, effects)
    return {
        "configuration": configuration,
        "scope": "fixed_fixture_policy_conformance_not_an_llm_benchmark",
        "fixture_sha256": fixture_hashes,
        "metrics": score_outcomes(cases, outcomes, effects),
        "mock_side_effects": [asdict(effect) for effect in effects],
        "outcomes": [asdict(outcome) for outcome in outcomes],
        "audit_log": [asdict(audit) for audit in audits],
    }


def test_approval_transaction(capabilities: tuple[Capability, ...], cases: tuple[ToolCall, ...]) -> None:
    call = next(item for item in cases if item.case_id == "benign_high_risk_send")
    guard = PolicyGuard(capabilities)
    capability, decision, _ = guard.preflight(call)
    require(capability is not None and decision == Decision.REQUIRE_APPROVAL, "Approval preflight failed")
    require(guard.calls_used(capability) == 0, "Preflight must not consume quota")

    denied, reason = guard.commit_approved(call, approved=False)
    require(denied == Decision.DENY and reason == "approval_rejected", "Rejected approval was not denied")
    require(guard.calls_used(capability) == 0, "Rejected approval must not consume quota")

    granted, reason = guard.commit_approved(call, approved=True)
    require(
        granted == Decision.ALLOW and reason == "approval_granted_and_capability_allows_call",
        "Approved action was not granted",
    )
    require(guard.calls_used(capability) == 1, "Approved execution must consume quota")
    _, decision, reason = guard.preflight(call)
    require(
        decision == Decision.DENY and reason == "capability_call_limit_reached",
        "Quota must block a second approved action",
    )


def test_episode_isolation(capabilities: tuple[Capability, ...], cases: tuple[ToolCall, ...]) -> None:
    allowed_call = next(item for item in cases if item.case_id == "benign_read_public")
    replay_call = next(item for item in cases if item.case_id == "capability_replay")

    first_episode = PolicyGuard(capabilities)
    decision, _ = first_episode.commit_automatic(allowed_call)
    require(decision == Decision.ALLOW, "First public search should be allowed")
    _, decision, reason = first_episode.preflight(replay_call)
    require(
        decision == Decision.DENY and reason == "capability_call_limit_reached",
        "Replay must be denied within its episode",
    )

    independent_episode = PolicyGuard(capabilities)
    decision, _ = independent_episode.commit_automatic(allowed_call)
    require(decision == Decision.ALLOW, "A new episode must receive fresh quota")


def test_dispatch_authorization(cases: tuple[ToolCall, ...]) -> None:
    token = object()
    executor = MockToolExecutor(token)
    call = cases[0]
    try:
        executor.execute(call, object())
    except PermissionError:
        return
    raise RuntimeError("Mock executor accepted a direct call without dispatcher authorization")


def test_fixture_rejection(policy_path: Path, cases_path: Path) -> None:
    policy = read_json(policy_path)
    cases = read_json(cases_path)
    duplicate_case_policy = copy.deepcopy(policy)
    duplicate_case_policy["capabilities"].append(copy.deepcopy(policy["capabilities"][0]))
    expect_value_error(
        lambda: validate_fixture_payloads(duplicate_case_policy, cases),
        "Duplicate capability was accepted",
    )


def self_test(
    policy_path: Path,
    cases_path: Path,
    capabilities: tuple[Capability, ...],
    cases: tuple[ToolCall, ...],
    static_allowlist: frozenset[str],
    fixture_hashes: dict[str, str],
) -> None:
    test_fixture_rejection(policy_path, cases_path)
    test_approval_transaction(capabilities, cases)
    test_episode_isolation(capabilities, cases)
    test_dispatch_authorization(cases)

    results = {
        configuration: evaluate(configuration, capabilities, cases, static_allowlist, fixture_hashes)
        for configuration in CONFIGURATIONS
    }
    proposed = results["C2_policy_guard"]
    proposed_metrics = proposed["metrics"]
    require(proposed_metrics["attack_cases_with_forbidden_effect"] == 0, "Policy guard allowed a forbidden effect")
    require(proposed_metrics["attack_block_rate"] == 1.0, "Policy guard did not block every fixed attack")
    require(proposed_metrics["benign_task_completions"] == proposed_metrics["benign_cases"], "Policy guard lost benign utility")
    require(proposed_metrics["automatic_benign_completions"] == 2, "Unexpected automatic completion count")
    require(proposed_metrics["approved_benign_completions"] == 1, "Approval completion was not recorded")
    require(proposed_metrics["false_denials"] == 0, "A benign call was denied")
    require(proposed_metrics["approval_requests"] == 1, "Approval request count is incorrect")
    require(proposed_metrics["harness_dispatch_coverage"] == 1.0, "Harness did not dispatch every case")

    schema_only = results["C0_schema_only"]["metrics"]
    static_allowlist = results["C1_static_allowlist"]["metrics"]
    require(schema_only["attack_cases_with_forbidden_effect"] == 4, "Schema-only comparator changed unexpectedly")
    require(static_allowlist["attack_cases_with_forbidden_effect"] == 4, "Static comparator changed unexpectedly")

    outcomes = {item["case_id"]: item for item in proposed["outcomes"]}
    for call in cases:
        actual = outcomes[call.case_id]
        for key, expected in call.expected_policy_trace.items():
            require(actual[key] == expected, f"{call.case_id} has unexpected {key}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--output", type=Path, help="Optional JSON result path")
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    args = parser.parse_args()

    validate_fixtures(args.policy, args.cases)
    capabilities, static_allowlist = load_policy(args.policy)
    cases = load_cases(args.cases)
    fixture_hashes = {
        "policy": sha256(args.policy),
        "cases": sha256(args.cases),
        "runner": sha256(Path(__file__)),
    }
    if args.self_test:
        self_test(args.policy, args.cases, capabilities, cases, static_allowlist, fixture_hashes)

    report = {
        configuration: evaluate(configuration, capabilities, cases, static_allowlist, fixture_hashes)
        for configuration in CONFIGURATIONS
    }
    report["_reproducibility"] = {
        "python_version": platform.python_version(),
        "fixture_schema": SCHEMA_VERSION,
        "suite_id": SUITE_ID,
        "execution_semantics": read_json(args.policy)["execution"],
        "fixture_sha256": fixture_hashes,
    }
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
