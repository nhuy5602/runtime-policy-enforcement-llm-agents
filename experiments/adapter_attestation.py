"""Minimal adapter-aware transaction and effect-attestation harness.

The existing policy simulator evaluates a proposed call before a mocked
effect is recorded.  This module exercises the missing boundary explicitly:

* a policy enforcement point (PEP) issues a session-bound nonce and captures
  a pre-state hash;
* the adapter executes only against a staged state and returns the observed
  effect, request body, state hashes, and sink/canary evidence;
* the mediator commits the staged state only when the observed effect and
  state transition match the authorized signature;
* stale/replayed tokens, adapter remapping, body/payload changes, state-hash
  tampering, and canary mismatches abort without committing side effects.

It is intentionally dependency-free and uses an in-memory adapter.  The
adapter is a test double, but the transaction invariants are real and are
written so that a concrete tool adapter can implement the same ``execute``
protocol.  This is an enforcement-isolation harness, not an end-to-end LLM
efficacy benchmark.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import secrets
from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Protocol


SCHEMA_VERSION = "adapter-attestation/v1"


def _normalize(value: Any) -> Any:
    """Return a JSON-safe, deterministic representation or raise ``ValueError``."""

    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("non-finite numbers are not supported in attestation payloads")
        return value
    if isinstance(value, Mapping):
        normalized: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError("attestation object keys must be strings")
            normalized[key] = _normalize(item)
        return {key: normalized[key] for key in sorted(normalized)}
    if isinstance(value, (list, tuple)):
        return [_normalize(item) for item in value]
    raise ValueError(f"unsupported attestation value type: {type(value).__name__}")


def canonical_json(value: Any) -> str:
    """Canonical JSON used by both signature and state hashing."""

    return json.dumps(
        _normalize(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def state_hash(state: Mapping[str, Any]) -> str:
    """Hash the complete adapter state, not just a model-supplied field."""

    return sha256_text(canonical_json(state))


def _required_text(value: str, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value.strip()


@dataclass(frozen=True)
class EffectSignature:
    """Canonical authorization contract, including arguments and request body."""

    policy_version: str
    task_id: str
    session_id: str
    tool: str
    operation: str
    resource: str
    destination: str
    arguments: Mapping[str, Any]
    body: Any = None
    canary_sink: str | None = None

    def __post_init__(self) -> None:
        for name in (
            "policy_version",
            "task_id",
            "session_id",
            "tool",
            "operation",
            "resource",
        ):
            _required_text(getattr(self, name), name)
        if not isinstance(self.destination, str):
            raise ValueError("destination must be a string")
        object.__setattr__(self, "destination", self.destination.strip())
        if self.canary_sink is not None:
            _required_text(self.canary_sink, "canary_sink")
        if not isinstance(self.arguments, Mapping):
            raise ValueError("arguments must be an object")
        # Freeze the values semantically at construction time.  ``begin`` also
        # deep-copies the signature before placing it in the pending ledger.
        object.__setattr__(self, "arguments", _normalize(dict(self.arguments)))
        object.__setattr__(self, "body", _normalize(self.body))

    def canonical(self) -> dict[str, Any]:
        return {
            "policy_version": self.policy_version,
            "task_id": self.task_id,
            "session_id": self.session_id,
            "tool": self.tool,
            "operation": self.operation,
            "resource": self.resource,
            "destination": self.destination,
            "arguments": copy.deepcopy(dict(self.arguments)),
            "body": copy.deepcopy(self.body),
            "canary_sink": self.canary_sink,
        }

    def digest(self) -> str:
        return sha256_text(canonical_json(self.canonical()))


@dataclass(frozen=True)
class DispatchToken:
    """Opaque-ish session token issued by the mediator for one transaction."""

    transaction_id: str
    nonce: str
    session_id: str
    pre_state_hash: str
    expected_signature_digest: str


@dataclass(frozen=True)
class AdapterObservation:
    """Adapter report returned after executing against a staged state."""

    observed_signature: EffectSignature
    reported_pre_state_hash: str
    reported_post_state_hash: str
    state_before: Mapping[str, Any]
    state_after: Mapping[str, Any]
    sink_evidence: tuple[str, ...] = ()


@dataclass(frozen=True)
class AttestationAudit:
    schema_version: str
    transaction_id: str
    session_id: str
    status: str
    reason: str
    token_pre_state_hash: str
    observed_pre_state_hash: str | None
    expected_signature_digest: str
    observed_signature_digest: str | None
    observed_post_state_hash: str | None
    recomputed_post_state_hash: str | None
    state_diff: Mapping[str, Any]
    sink_evidence: tuple[str, ...]


@dataclass(frozen=True)
class AttestationResult:
    committed: bool
    reason: str
    audit: AttestationAudit
    observation: AdapterObservation | None = None


class Adapter(Protocol):
    def execute(
        self,
        authorized_signature: EffectSignature,
        staged_state: dict[str, Any],
    ) -> AdapterObservation:
        """Execute against ``staged_state`` and report what actually happened."""


def _state_diff(before: Mapping[str, Any], after: Mapping[str, Any]) -> dict[str, Any]:
    """Return a compact recursive state-diff oracle for the audit record."""

    result: dict[str, Any] = {}

    def walk(path: str, left: Any, right: Any) -> None:
        if isinstance(left, Mapping) and isinstance(right, Mapping):
            keys = sorted(set(left) | set(right))
            for key in keys:
                child = f"{path}/{key}" if path else f"/{key}"
                walk(child, left.get(key), right.get(key))
            return
        if left != right:
            result[path or "/"] = {"before": copy.deepcopy(left), "after": copy.deepcopy(right)}

    walk("", _normalize(before), _normalize(after))
    return result


@dataclass
class _PendingTransaction:
    token: DispatchToken
    expected_signature: EffectSignature


class AttestationEngine:
    """Optimistic, staged-state mediator for one or more sessions."""

    def __init__(
        self,
        initial_state: Mapping[str, Any] | None = None,
        *,
        nonce_factory: Callable[[], str] | None = None,
    ) -> None:
        self._state: dict[str, Any] = _normalize(dict(initial_state or {}))
        self._nonce_factory = nonce_factory or (lambda: secrets.token_urlsafe(18))
        self._pending: dict[str, _PendingTransaction] = {}
        self._used_tokens: set[str] = set()
        self._audits: list[AttestationAudit] = []

    @property
    def state(self) -> dict[str, Any]:
        return copy.deepcopy(self._state)

    @property
    def audit_log(self) -> tuple[AttestationAudit, ...]:
        return tuple(self._audits)

    def mutate_state(self, mutator: Callable[[dict[str, Any]], None]) -> None:
        """Test/integration hook for an external concurrent state change."""

        candidate = copy.deepcopy(self._state)
        mutator(candidate)
        self._state = _normalize(candidate)

    def begin(self, expected_signature: EffectSignature) -> DispatchToken:
        """Issue a one-use token bound to session, signature and pre-state."""

        expected = copy.deepcopy(expected_signature)
        nonce = _required_text(self._nonce_factory(), "nonce")
        transaction_id = f"{expected.session_id}:{nonce}"
        if transaction_id in self._pending or transaction_id in self._used_tokens:
            raise ValueError("nonce_factory produced a duplicate transaction id")
        token = DispatchToken(
            transaction_id=transaction_id,
            nonce=nonce,
            session_id=expected.session_id,
            pre_state_hash=state_hash(self._state),
            expected_signature_digest=expected.digest(),
        )
        self._pending[transaction_id] = _PendingTransaction(token=token, expected_signature=expected)
        return token

    def commit(
        self,
        token: DispatchToken,
        adapter: Adapter,
        *,
        before_execute: Callable[[dict[str, Any]], None] | None = None,
    ) -> AttestationResult:
        """Verify and atomically commit one adapter execution.

        ``before_execute`` is a deterministic TOCTOU test hook.  A production
        adapter can achieve the same invariant with a compare-and-swap/version
        check immediately before dispatch.
        """

        pending = self._pending.get(token.transaction_id)
        if pending is None:
            reason = "replay_token" if token.transaction_id in self._used_tokens else "unknown_token"
            return self._finish_unknown(token, reason)

        # A copied or forged token must not be able to consume the pending
        # transaction; the legitimate token remains usable.
        if token != pending.token:
            return self._finish(
                pending,
                status="aborted",
                reason="token_integrity_mismatch",
                observed=None,
                consume=False,
            )

        live_hash = state_hash(self._state)
        if live_hash != token.pre_state_hash:
            return self._finish(
                pending,
                status="aborted",
                reason="pre_state_changed_toctou",
                observed=None,
                consume=True,
            )

        if before_execute is not None:
            before_execute(self._state)
            self._state = _normalize(self._state)
            if state_hash(self._state) != token.pre_state_hash:
                return self._finish(
                    pending,
                    status="aborted",
                    reason="pre_state_changed_toctou",
                    observed=None,
                    consume=True,
                )

        staged_state = copy.deepcopy(self._state)
        try:
            observation = adapter.execute(pending.expected_signature, staged_state)
        except Exception as error:  # pragma: no cover - defensive integration boundary
            return self._finish(
                pending,
                status="aborted",
                reason=f"adapter_error:{type(error).__name__}",
                observed=None,
                consume=True,
            )

        observed_digest = observation.observed_signature.digest()
        if observed_digest != token.expected_signature_digest:
            return self._finish(
                pending,
                status="aborted",
                reason="observed_signature_mismatch",
                observed=observation,
                consume=True,
            )

        if observation.reported_pre_state_hash != token.pre_state_hash:
            return self._finish(
                pending,
                status="aborted",
                reason="pre_state_hash_mismatch",
                observed=observation,
                consume=True,
            )

        recomputed_before = state_hash(observation.state_before)
        if recomputed_before != token.pre_state_hash:
            return self._finish(
                pending,
                status="aborted",
                reason="adapter_pre_state_oracle_mismatch",
                observed=observation,
                consume=True,
            )

        recomputed_post = state_hash(observation.state_after)
        if observation.reported_post_state_hash != recomputed_post:
            return self._finish(
                pending,
                status="aborted",
                reason="post_state_hash_mismatch",
                observed=observation,
                consume=True,
            )

        if state_hash(staged_state) != recomputed_post:
            return self._finish(
                pending,
                status="aborted",
                reason="adapter_state_oracle_mismatch",
                observed=observation,
                consume=True,
            )

        if (
            pending.expected_signature.canary_sink is not None
            and pending.expected_signature.canary_sink not in observation.sink_evidence
        ):
            return self._finish(
                pending,
                status="aborted",
                reason="canary_mismatch",
                observed=observation,
                consume=True,
            )

        # The live state must not have changed while the adapter was running.
        if state_hash(self._state) != live_hash:
            return self._finish(
                pending,
                status="aborted",
                reason="live_state_changed_during_dispatch",
                observed=observation,
                consume=True,
            )

        self._state = _normalize(dict(observation.state_after))
        return self._finish(
            pending,
            status="committed",
            reason="attestation_verified",
            observed=observation,
            consume=True,
        )

    def _finish_unknown(self, token: DispatchToken, reason: str) -> AttestationResult:
        audit = AttestationAudit(
            schema_version=SCHEMA_VERSION,
            transaction_id=token.transaction_id,
            session_id=token.session_id,
            status="aborted",
            reason=reason,
            token_pre_state_hash=token.pre_state_hash,
            observed_pre_state_hash=None,
            expected_signature_digest=token.expected_signature_digest,
            observed_signature_digest=None,
            observed_post_state_hash=None,
            recomputed_post_state_hash=None,
            state_diff={},
            sink_evidence=(),
        )
        self._audits.append(audit)
        return AttestationResult(False, reason, audit, None)

    def _finish(
        self,
        pending: _PendingTransaction,
        *,
        status: str,
        reason: str,
        observed: AdapterObservation | None,
        consume: bool,
    ) -> AttestationResult:
        if consume:
            self._pending.pop(pending.token.transaction_id, None)
            self._used_tokens.add(pending.token.transaction_id)
        observed_digest = observed.observed_signature.digest() if observed else None
        recomputed_post = state_hash(observed.state_after) if observed else None
        audit = AttestationAudit(
            schema_version=SCHEMA_VERSION,
            transaction_id=pending.token.transaction_id,
            session_id=pending.token.session_id,
            status=status,
            reason=reason,
            token_pre_state_hash=pending.token.pre_state_hash,
            observed_pre_state_hash=observed.reported_pre_state_hash if observed else None,
            expected_signature_digest=pending.token.expected_signature_digest,
            observed_signature_digest=observed_digest,
            observed_post_state_hash=observed.reported_post_state_hash if observed else None,
            recomputed_post_state_hash=recomputed_post if observed else None,
            state_diff=(
                _state_diff(observed.state_before, observed.state_after)
                if observed is not None
                else {}
            ),
            sink_evidence=observed.sink_evidence if observed else (),
        )
        self._audits.append(audit)
        return AttestationResult(status == "committed", reason, audit, observed)


class InMemoryAdapter:
    """Deterministic adapter double that records effects in staged state."""

    def __init__(
        self,
        *,
        observed_signature: EffectSignature | None = None,
        mutate: Callable[[dict[str, Any], EffectSignature], None] | None = None,
        reported_pre_state_hash: str | None = None,
        reported_post_state_hash: str | None = None,
        sink_evidence: tuple[str, ...] | None = None,
    ) -> None:
        self.observed_signature = observed_signature
        self.mutate = mutate
        self.reported_pre_state_hash = reported_pre_state_hash
        self.reported_post_state_hash = reported_post_state_hash
        self.sink_evidence = sink_evidence
        self.calls = 0

    def execute(
        self,
        authorized_signature: EffectSignature,
        staged_state: dict[str, Any],
    ) -> AdapterObservation:
        self.calls += 1
        before = copy.deepcopy(staged_state)
        actual = copy.deepcopy(self.observed_signature or authorized_signature)
        effects = staged_state.setdefault("effects", [])
        if not isinstance(effects, list):
            raise ValueError("adapter state.effects must be a list")
        effects.append(actual.canonical())
        if self.mutate is not None:
            self.mutate(staged_state, actual)
        before_hash = state_hash(before)
        after_hash = state_hash(staged_state)
        sinks = (
            self.sink_evidence
            if self.sink_evidence is not None
            else ((actual.canary_sink,) if actual.canary_sink else ())
        )
        return AdapterObservation(
            observed_signature=actual,
            reported_pre_state_hash=self.reported_pre_state_hash or before_hash,
            reported_post_state_hash=self.reported_post_state_hash or after_hash,
            state_before=before,
            state_after=copy.deepcopy(staged_state),
            sink_evidence=tuple(sinks),
        )


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _signature(*, session_id: str = "session-1", body: Any = None, canary: str | None = None) -> EffectSignature:
    return EffectSignature(
        policy_version="policy-v2",
        task_id="task-1",
        session_id=session_id,
        tool="mail",
        operation="send",
        resource="outbox",
        destination="approved.example",
        arguments={"subject": "status", "recipients": ["team@example.test"]},
        body=body if body is not None else {"text": "normal status"},
        canary_sink=canary,
    )


def self_test() -> dict[str, Any]:
    """Run deterministic transaction/attestation checks and return a report."""

    nonce_counter = iter(
        [
            "nonce-001",
            "nonce-002",
            "nonce-003",
            "nonce-004",
            "nonce-005",
            "nonce-006",
            "nonce-007",
        ]
    )
    fresh = lambda: next(nonce_counter)
    checks: dict[str, Any] = {}

    engine = AttestationEngine({"version": 1}, nonce_factory=fresh)
    expected = _signature(body={"text": "approved"}, canary="canary://approved")
    token = engine.begin(expected)
    happy_adapter = InMemoryAdapter()
    happy = engine.commit(token, happy_adapter)
    _assert(happy.committed and happy.reason == "attestation_verified", "happy path did not commit")
    _assert(happy_adapter.calls == 1, "happy path did not invoke adapter exactly once")
    _assert(len(engine.state["effects"]) == 1, "happy path did not commit staged effect")
    checks["happy_path"] = asdict(happy.audit)

    unchanged = AttestationEngine({"version": 1}, nonce_factory=fresh)
    expected_body = _signature(body={"text": "approved"})
    mismatch_token = unchanged.begin(expected_body)
    tampered = _signature(body={"text": "exfiltrate"})
    mismatch_adapter = InMemoryAdapter(observed_signature=tampered)
    before = state_hash(unchanged.state)
    mismatch = unchanged.commit(mismatch_token, mismatch_adapter)
    _assert(not mismatch.committed and mismatch.reason == "observed_signature_mismatch", "body mismatch was accepted")
    _assert(state_hash(unchanged.state) == before, "body mismatch committed a side effect")
    checks["body_or_signature_mismatch"] = asdict(mismatch.audit)

    hash_engine = AttestationEngine({"version": 1}, nonce_factory=fresh)
    hash_token = hash_engine.begin(_signature())
    hash_adapter = InMemoryAdapter(reported_post_state_hash="0" * 64)
    hash_result = hash_engine.commit(hash_token, hash_adapter)
    _assert(not hash_result.committed and hash_result.reason == "post_state_hash_mismatch", "post hash tampering was accepted")
    _assert(hash_engine.state == {"version": 1}, "post hash mismatch committed a side effect")
    checks["post_state_hash_mismatch"] = asdict(hash_result.audit)

    replay_engine = AttestationEngine({"version": 1}, nonce_factory=fresh)
    replay_token = replay_engine.begin(_signature())
    replay_first = replay_engine.commit(replay_token, InMemoryAdapter())
    replay_second = replay_engine.commit(replay_token, InMemoryAdapter())
    _assert(replay_first.committed and replay_second.reason == "replay_token", "replay token was not rejected")
    _assert(len(replay_engine.state["effects"]) == 1, "replay changed committed state")
    checks["replay_rejection"] = asdict(replay_second.audit)

    stale_engine = AttestationEngine({"version": 1}, nonce_factory=fresh)
    stale_token = stale_engine.begin(_signature())
    stale_engine.mutate_state(lambda value: value.update({"version": 2}))
    stale_adapter = InMemoryAdapter()
    stale_result = stale_engine.commit(stale_token, stale_adapter)
    _assert(not stale_result.committed and stale_result.reason == "pre_state_changed_toctou", "stale state was not rejected")
    _assert(stale_adapter.calls == 0, "stale state invoked adapter")
    checks["stale_state_toctou"] = asdict(stale_result.audit)

    hook_engine = AttestationEngine({"version": 1}, nonce_factory=fresh)
    hook_token = hook_engine.begin(_signature())
    hook_adapter = InMemoryAdapter()
    hook_result = hook_engine.commit(
        hook_token,
        hook_adapter,
        before_execute=lambda value: value.update({"concurrent": True}),
    )
    _assert(not hook_result.committed and hook_result.reason == "pre_state_changed_toctou", "TOCTOU hook was not rejected")
    _assert(hook_adapter.calls == 0, "TOCTOU hook invoked adapter")
    checks["in_commit_toctou"] = asdict(hook_result.audit)

    sink_engine = AttestationEngine({"version": 1}, nonce_factory=fresh)
    sink_token = sink_engine.begin(_signature(canary="canary://approved"))
    sink_result = sink_engine.commit(
        sink_token,
        InMemoryAdapter(sink_evidence=("canary://wrong",)),
    )
    _assert(not sink_result.committed and sink_result.reason == "canary_mismatch", "canary mismatch was accepted")
    _assert(sink_engine.state == {"version": 1}, "canary mismatch committed a side effect")
    checks["canary_mismatch"] = asdict(sink_result.audit)

    return {
        "schema_version": SCHEMA_VERSION,
        "scope": "transaction_attestation_in_memory_adapter_conformance",
        "checks": checks,
        "all_pass": True,
        "invariants": [
            "authorized signature includes normalized arguments and body",
            "token binds session, nonce, expected signature digest and pre-state hash",
            "adapter executes only on a staged copy",
            "mismatch, replay, stale state and canary failure never commit live state",
            "post-state hash and recursive state diff are independently audited",
        ],
    }


def fixture_smoke() -> dict[str, Any]:
    """Exercise the attestation path on the benchmark's adapter-drift fixtures.

    The offline benchmark already creates three ``executor_alias`` rows where
    the policy-level call is allowed but the adapter is supposed to produce a
    forbidden destination/resource.  This check routes those rows through the
    staged transaction engine, plus one clean benign row.  It deliberately
    remains a smoke/conformance check: it does not call an LLM and does not
    estimate population-level AFER.
    """

    # Lazy import keeps the core attestation module dependency-free and avoids
    # importing the larger benchmark when only ``--self-test`` is requested.
    import sys

    experiment_dir = str(Path(__file__).resolve().parent)
    if experiment_dir not in sys.path:
        sys.path.insert(0, experiment_dir)
    from offline_benchmark_harness import make_matrix
    from policy_guard_sim import DEFAULT_CASES, load_cases

    matrix = make_matrix(load_cases(DEFAULT_CASES))
    selected = [
        case
        for case in matrix
        if case.drift == "executor_alias" or (
            case.call.kind == "benign"
            and case.call.case_id == "benign_read_public__clean"
        )
    ]
    selected.sort(key=lambda case: case.call.case_id)

    def make_signature(case: Any, raw: Mapping[str, Any]) -> EffectSignature:
        return EffectSignature(
            policy_version="runtime-policy-fixtures/v1",
            task_id=case.call.task_id,
            session_id=f"fixture:{case.call.case_id}",
            tool=str(raw["tool"]),
            operation=str(raw["operation"]),
            resource=str(raw["resource"]),
            destination=str(raw["destination"]),
            arguments={
                "case_id": case.call.case_id,
                "ordinal": case.call.ordinal,
                "step": case.call.step,
            },
            body={"carrier": case.carrier_text},
            canary_sink=f"canary://{raw['destination'] or raw['resource']}",
        )

    rows: list[dict[str, Any]] = []
    for index, case in enumerate(selected, start=1):
        expected_raw = {
            "tool": case.call.tool,
            "operation": case.call.operation,
            "resource": case.call.resource,
            "destination": case.call.destination,
        }
        expected = make_signature(case, expected_raw)
        actual = (
            make_signature(case, case.actual_effect_override)
            if case.actual_effect_override is not None
            else None
        )
        engine = AttestationEngine(
            {"revision": 1, "case_id": case.call.case_id},
            nonce_factory=lambda index=index: f"fixture-{index:03d}",
        )
        token = engine.begin(expected)
        adapter = InMemoryAdapter(observed_signature=actual)
        result = engine.commit(token, adapter)
        rows.append(
            {
                "case_id": case.call.case_id,
                "drift": case.drift,
                "kind": case.call.kind,
                "committed": result.committed,
                "reason": result.reason,
                "adapter_calls": adapter.calls,
                "live_state_effects": len(engine.state.get("effects", [])),
                "state_unchanged_on_abort": (
                    result.committed
                    or "effects" not in engine.state
                ),
            }
        )

    mismatch_rows = [row for row in rows if row["drift"] == "executor_alias"]
    clean_rows = [row for row in rows if row["case_id"] == "benign_read_public__clean"]
    if len(mismatch_rows) != 3 or len(clean_rows) != 1:
        raise AssertionError("fixture smoke selection does not contain 3 adapter attacks and 1 clean control")
    if any(row["committed"] or row["reason"] != "observed_signature_mismatch" for row in mismatch_rows):
        raise AssertionError("adapter-drift fixture bypass was not rejected by attestation")
    if not clean_rows[0]["committed"]:
        raise AssertionError("clean fixture did not commit")

    return {
        "schema_version": SCHEMA_VERSION,
        "scope": "fixture_adapter_drift_smoke_conformance_not_an_llm_benchmark",
        "n_cases": len(rows),
        "n_adapter_mismatch_cases": len(mismatch_rows),
        "adapter_mismatch_aborts": sum(
            row["reason"] == "observed_signature_mismatch" and not row["committed"]
            for row in mismatch_rows
        ),
        "clean_commits": sum(row["committed"] for row in clean_rows),
        "rows": rows,
        "all_pass": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true", help="run deterministic attestation checks")
    parser.add_argument(
        "--fixture-smoke",
        action="store_true",
        help="route three adapter-drift fixture rows and one clean control through the attestation engine",
    )
    parser.add_argument("--output", type=Path, help="write the JSON self-test report")
    args = parser.parse_args()
    if args.self_test == args.fixture_smoke:
        parser.error("use exactly one of --self-test or --fixture-smoke")
    report = self_test() if args.self_test else fixture_smoke()
    text = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
