"""Fail-closed AgentDojo ``ToolsExecutor`` adapter for attestation experiments.

AgentDojo imports its ``ToolsExecutor`` class before loading modules supplied by
``--module-to-load``.  Importing this module therefore replaces the class
reference used by ``AgentPipeline.from_config``.  The replacement keeps
AgentDojo's tool-result message shape, but executes a tool only when:

1. the explicit ``AGENTDOJO_ATTESTATION_ALLOWLIST`` names the tool (or is the
   explicit ``*`` opt-in);
2. approval-gated tools are explicitly approved with
   ``AGENTDOJO_ATTESTATION_APPROVE=1``; and
3. the project's ``AttestationEngine`` verifies the argument-level effect and
   staged environment transition.

The default is deny-all.  This is an adapter integration artifact, not a claim
that AgentDojo's simulated tools represent irreversible external side effects.
No real network, email, filesystem, or payment tool is executed by AgentDojo's
default benchmark suites.  Paired drift can be injected deterministically with
``AGENTDOJO_ATTESTATION_DRIFT_TOOL`` and
``AGENTDOJO_ATTESTATION_DRIFT_MODE=resource|destination|arguments``.
"""

from __future__ import annotations

import argparse
import atexit
import copy
import dataclasses
import hashlib
import json
import os
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

try:
    from adapter_attestation import (
        AdapterObservation,
        AttestationEngine,
        EffectSignature,
        canonical_json,
        state_hash,
    )
except ModuleNotFoundError:  # pragma: no cover - package import from repo root
    from experiments.adapter_attestation import (
        AdapterObservation,
        AttestationEngine,
        EffectSignature,
        canonical_json,
        state_hash,
    )


POLICY_VERSION = "agentdojo-attestation/v1"
AUDIT_PATH_ENV = "AGENTDOJO_ATTESTATION_AUDIT_PATH"
ALLOWLIST_ENV = "AGENTDOJO_ATTESTATION_ALLOWLIST"
APPROVAL_ENV = "AGENTDOJO_ATTESTATION_APPROVAL_TOOLS"
APPROVE_ENV = "AGENTDOJO_ATTESTATION_APPROVE"
DRIFT_TOOL_ENV = "AGENTDOJO_ATTESTATION_DRIFT_TOOL"
DRIFT_MODE_ENV = "AGENTDOJO_ATTESTATION_DRIFT_MODE"

_AUDIT_LOG: list[dict[str, Any]] = []


def _csv_env(name: str) -> frozenset[str]:
    value = os.environ.get(name, "")
    return frozenset(part.strip() for part in value.split(",") if part.strip())


def _policy_decision(tool_name: str) -> tuple[str, str]:
    """Return ``ALLOW``, ``REQUIRE_APPROVAL`` or ``DENY`` and a stable reason."""

    allowlist = _csv_env(ALLOWLIST_ENV)
    if not allowlist:
        return "DENY", "allowlist_missing_fail_closed"
    if "*" not in allowlist and tool_name not in allowlist:
        return "DENY", "tool_not_in_explicit_allowlist"
    if tool_name in _csv_env(APPROVAL_ENV) and os.environ.get(APPROVE_ENV) != "1":
        return "REQUIRE_APPROVAL", "explicit_approval_required"
    return "ALLOW", "explicit_allowlist_match"


def _jsonable(value: Any) -> Any:
    """Convert a Pydantic environment to the attestation module's JSON domain."""

    if hasattr(value, "model_dump"):
        try:
            value = value.model_dump(mode="json")
        except TypeError:
            value = value.model_dump()
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    if isinstance(value, Mapping):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    raise ValueError(f"environment contains unsupported attestation value: {type(value).__name__}")


def _environment_state(env: Any) -> dict[str, Any]:
    return {"environment": _jsonable(env)}


def _contains_nested_tool_call(value: Any) -> bool:
    """Reject nested FunctionCall values that could bypass this dispatcher."""

    if hasattr(value, "function") and hasattr(value, "args"):
        return True
    if isinstance(value, Mapping):
        if "function" in value and "args" in value:
            return True
        return any(_contains_nested_tool_call(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return any(_contains_nested_tool_call(item) for item in value)
    return False


def _copy_environment_into(target: Any, source: Any) -> None:
    """Commit a staged Pydantic environment without relying on private fields."""

    fields = getattr(type(target), "model_fields", None)
    if fields is None:
        raise TypeError("AgentDojo environment is not a Pydantic model")
    for field_name in fields:
        object.__setattr__(target, field_name, copy.deepcopy(getattr(source, field_name)))


def _session_id(runtime: Any, messages: Sequence[Mapping[str, Any]]) -> str:
    first_user = next(
        (
            block.get("content")
            for block in messages
            if block.get("role") == "user" and block.get("content") is not None
        ),
        "",
    )
    return f"agentdojo:{id(runtime)}:{hashlib.sha256(str(first_user).encode()).hexdigest()[:16]}"


class _RuntimeAdapter:
    """Run an AgentDojo function against a staged environment copy."""

    def __init__(
        self,
        runtime: Any,
        staged_env: Any,
        tool_name: str,
        args: dict[str, Any],
        observed_signature: EffectSignature | None = None,
    ) -> None:
        self.runtime = runtime
        self.staged_env = staged_env
        self.tool_name = tool_name
        self.args = args
        self.observed_signature = observed_signature
        self.result: Any = ""
        self.error: str | None = None

    def execute(self, authorized_signature: EffectSignature, staged_state: dict[str, Any]) -> AdapterObservation:
        before_state = copy.deepcopy(staged_state)
        self.result, self.error = self.runtime.run_function(self.staged_env, self.tool_name, self.args)
        if self.error is not None:
            raise RuntimeError(f"tool_execution_error:{self.error}")
        staged_state["environment"] = _jsonable(self.staged_env)
        staged_state.setdefault("effects", []).append(authorized_signature.canonical())
        return AdapterObservation(
            observed_signature=self.observed_signature or authorized_signature,
            reported_pre_state_hash=state_hash(before_state),
            reported_post_state_hash=state_hash(staged_state),
            state_before=before_state,
            state_after=copy.deepcopy(staged_state),
        )


def _audit(
    *,
    tool_name: str,
    decision: str,
    reason: str,
    result: Any | None = None,
    error: str | None = None,
    attestation_reason: str | None = None,
    attestation_summary: dict[str, Any] | None = None,
) -> None:
    if result is None:
        result_digest = None
    else:
        try:
            result_digest = hashlib.sha256(canonical_json(_jsonable(result)).encode()).hexdigest()
        except Exception:
            result_digest = hashlib.sha256(repr(result).encode()).hexdigest()
    _AUDIT_LOG.append(
        {
            "schema_version": POLICY_VERSION,
            "tool": tool_name,
            "decision": decision,
            "reason": reason,
            "result_digest": result_digest,
            "error": error,
            "attestation_reason": attestation_reason,
            "attestation": attestation_summary,
        }
    )


def _write_audit() -> None:
    path = os.environ.get(AUDIT_PATH_ENV)
    if not path:
        return
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(_AUDIT_LOG, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


atexit.register(_write_audit)


def _install_agentdojo_patch() -> bool:
    """Patch every known ToolsExecutor reference used by AgentDojo 0.1.35+."""

    try:
        from agentdojo.agent_pipeline import agent_pipeline as pipeline_module
        from agentdojo.agent_pipeline import tool_execution as execution_module
    except ImportError:
        return False

    base_executor = execution_module.ToolsExecutor

    class AttestedToolsExecutor(base_executor):
        """Drop-in executor with explicit policy and staged attestation."""

        def __init__(self, tool_output_formatter=None):
            super().__init__(tool_output_formatter=tool_output_formatter or execution_module.tool_result_to_str)
            self._engines: dict[int, tuple[str, AttestationEngine]] = {}

        def _engine_for(self, runtime: Any, env: Any, messages: Sequence[Mapping[str, Any]]) -> tuple[str, AttestationEngine]:
            key = id(runtime)
            session = _session_id(runtime, messages)
            current = _environment_state(env)
            if key not in self._engines:
                self._engines[key] = (session, AttestationEngine(current))
            else:
                previous_session, engine = self._engines[key]
                if previous_session != session:
                    self._engines[key] = (session, AttestationEngine(current))
                elif engine.state.get("environment") != current["environment"]:
                    raise RuntimeError("agentdojo environment changed outside the attested executor")
            return self._engines[key]

        def query(self, query, runtime, env=None, messages=(), extra_args=None):
            if extra_args is None:
                extra_args = {}
            if not messages or messages[-1].get("role") != "assistant":
                return query, runtime, env, messages, extra_args
            tool_calls = messages[-1].get("tool_calls") or []
            if not tool_calls:
                return query, runtime, env, messages, extra_args

            try:
                from agentdojo.agent_pipeline.tool_execution import is_string_list
                from agentdojo.functions_runtime import EmptyEnv
                from agentdojo.types import ChatToolResultMessage, text_content_block_from_string
            except ImportError as error:  # pragma: no cover
                raise RuntimeError("AgentDojo runtime imports are unavailable") from error

            if env is None:
                env = EmptyEnv()
            session, engine = self._engine_for(runtime, env, messages)
            tool_results = []
            for tool_call in tool_calls:
                name = str(tool_call.function)
                args = dict(tool_call.args or {})
                for key, value in list(args.items()):
                    if isinstance(value, str) and is_string_list(value):
                        # Match AgentDojo's upstream conversion while keeping
                        # evaluation constrained to literal containers.
                        import ast

                        args[key] = ast.literal_eval(value)

                if _contains_nested_tool_call(args):
                    error = "runtime_attestation:deny:nested_tool_call_not_supported"
                    _audit(tool_name=name, decision="DENY", reason="nested_tool_call_not_supported", error=error)
                    tool_results.append(
                        ChatToolResultMessage(
                            role="tool",
                            content=[text_content_block_from_string("")],
                            tool_call_id=tool_call.id,
                            tool_call=tool_call,
                            error=error,
                        )
                    )
                    continue

                if name not in runtime.functions:
                    error = f"ToolNotFoundError: The requested function `{name}` is not available."
                    _audit(tool_name=name, decision="DENY", reason="unknown_tool", error=error)
                    tool_results.append(
                        ChatToolResultMessage(
                            role="tool",
                            content=[text_content_block_from_string("")],
                            tool_call_id=tool_call.id,
                            tool_call=tool_call,
                            error=error,
                        )
                    )
                    continue

                decision, reason = _policy_decision(name)
                if decision != "ALLOW":
                    error = f"runtime_attestation:{decision.lower()}:{reason}"
                    _audit(tool_name=name, decision=decision, reason=reason, error=error)
                    tool_results.append(
                        ChatToolResultMessage(
                            role="tool",
                            content=[text_content_block_from_string("")],
                            tool_call_id=tool_call.id,
                            tool_call=tool_call,
                            error=error,
                        )
                    )
                    continue

                signature = EffectSignature(
                    policy_version=POLICY_VERSION,
                    task_id=session,
                    session_id=session,
                    tool=name,
                    operation="invoke",
                    resource=name,
                    destination="",
                    arguments=args,
                )
                try:
                    token = engine.begin(signature)
                    staged_env = env.model_copy(deep=True)
                    adapter = None
                    adapter = _RuntimeAdapter(
                        runtime,
                        staged_env,
                        name,
                        args,
                        observed_signature=_drifted_signature(signature),
                    )
                    attested = engine.commit(token, adapter)
                    if not attested.committed:
                        error = f"runtime_attestation:aborted:{attested.reason}"
                        _audit(
                            tool_name=name,
                            decision="DENY",
                            reason="attestation_abort",
                            error=error,
                            attestation_reason=attested.reason,
                            attestation_summary={
                                "status": attested.audit.status,
                                "reason": attested.audit.reason,
                                "state_diff_paths": sorted(attested.audit.state_diff),
                                "token_pre_state_hash": attested.audit.token_pre_state_hash,
                                "observed_post_state_hash": attested.audit.observed_post_state_hash,
                            },
                        )
                        tool_results.append(
                            ChatToolResultMessage(
                                role="tool",
                                content=[text_content_block_from_string("")],
                                tool_call_id=tool_call.id,
                                tool_call=tool_call,
                                error=error,
                            )
                        )
                        continue
                    _copy_environment_into(env, staged_env)
                    _audit(
                        tool_name=name,
                        decision="ALLOW",
                        reason=reason,
                        result=adapter.result,
                        error=adapter.error,
                        attestation_reason=attested.reason,
                        attestation_summary={
                            "status": attested.audit.status,
                            "reason": attested.audit.reason,
                            "state_diff_paths": sorted(attested.audit.state_diff),
                            "token_pre_state_hash": attested.audit.token_pre_state_hash,
                            "observed_post_state_hash": attested.audit.observed_post_state_hash,
                        },
                    )
                    tool_results.append(
                        ChatToolResultMessage(
                            role="tool",
                            content=[text_content_block_from_string(self.output_formatter(adapter.result))],
                            tool_call_id=tool_call.id,
                            tool_call=tool_call,
                            error=adapter.error,
                        )
                    )
                except Exception as error:  # fail closed at the tool boundary
                    detail = (adapter.error if adapter is not None else None) or type(error).__name__
                    text = f"runtime_attestation:adapter_error:{detail}"
                    _audit(tool_name=name, decision="DENY", reason="adapter_error", error=text)
                    tool_results.append(
                        ChatToolResultMessage(
                            role="tool",
                            content=[text_content_block_from_string("")],
                            tool_call_id=tool_call.id,
                            tool_call=tool_call,
                            error=text,
                        )
                    )

            return query, runtime, env, [*messages, *tool_results], extra_args

    pipeline_module.ToolsExecutor = AttestedToolsExecutor
    execution_module.ToolsExecutor = AttestedToolsExecutor
    try:
        import agentdojo.agent_pipeline as public_module

        public_module.ToolsExecutor = AttestedToolsExecutor
    except ImportError:
        pass
    return True


def _drifted_signature(signature: EffectSignature) -> EffectSignature | None:
    """Inject deterministic adapter drift for a paired, sandbox-only run."""

    if os.environ.get(DRIFT_TOOL_ENV) != signature.tool:
        return None
    mode = os.environ.get(DRIFT_MODE_ENV, "resource")
    if mode == "resource":
        return dataclasses.replace(signature, resource=f"{signature.resource}:drift")
    if mode == "destination":
        return dataclasses.replace(signature, destination="attacker.invalid")
    if mode == "arguments":
        return dataclasses.replace(signature, arguments={**signature.arguments, "__drift__": True})
    raise ValueError(f"unsupported {DRIFT_MODE_ENV}={mode!r}")


PATCH_INSTALLED = _install_agentdojo_patch()


def integration_status() -> dict[str, Any]:
    return {
        "status": "installed" if PATCH_INSTALLED else "dependency_missing",
        "policy": "deny-all unless AGENTDOJO_ATTESTATION_ALLOWLIST is explicit",
        "approval": f"{APPROVAL_ENV} tools require {APPROVE_ENV}=1",
        "attestation": "arguments, staged environment state, nonce and post-state hash",
        "paired_drift_hook": f"{DRIFT_TOOL_ENV}/{DRIFT_MODE_ENV} (resource|destination|arguments)",
        "external_side_effect_claim": "none; AgentDojo default suites are simulated",
    }


def self_test() -> dict[str, Any]:
    """Dependency-free policy/attestation smoke (does not invoke AgentDojo)."""

    original = {name: os.environ.get(name) for name in (ALLOWLIST_ENV, APPROVAL_ENV, APPROVE_ENV)}
    try:
        for name in original:
            os.environ.pop(name, None)
        decision, reason = _policy_decision("send_email")
        assert decision == "DENY" and reason == "allowlist_missing_fail_closed"

        os.environ[ALLOWLIST_ENV] = "search,send_email"
        os.environ[APPROVAL_ENV] = "send_email"
        decision, reason = _policy_decision("send_email")
        assert decision == "REQUIRE_APPROVAL" and reason == "explicit_approval_required"

        os.environ[APPROVE_ENV] = "1"
        decision, reason = _policy_decision("send_email")
        assert decision == "ALLOW" and reason == "explicit_allowlist_match"

        engine = AttestationEngine({"environment": {"count": 0}})
        signature = EffectSignature(
            policy_version=POLICY_VERSION,
            task_id="self-test",
            session_id="self-test",
            tool="counter",
            operation="invoke",
            resource="counter",
            destination="",
            arguments={"delta": 1},
        )

        class CounterAdapter:
            def execute(self, authorized_signature, staged_state):
                before = copy.deepcopy(staged_state)
                staged_state["environment"]["count"] += 1
                staged_state.setdefault("effects", []).append(authorized_signature.canonical())
                return AdapterObservation(
                    observed_signature=authorized_signature,
                    reported_pre_state_hash=state_hash(before),
                    reported_post_state_hash=state_hash(staged_state),
                    state_before=before,
                    state_after=copy.deepcopy(staged_state),
                )

        result = engine.commit(engine.begin(signature), CounterAdapter())
        assert result.committed and engine.state["environment"]["count"] == 1
        return {
            "status": "pass",
            "patch_installed": PATCH_INSTALLED,
            "checks": ["deny_by_default", "approval_gate", "attestation_commit"],
        }
    finally:
        for name, value in original.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if not args.self_test:
        print(json.dumps(integration_status(), indent=2))
        return 0
    print(json.dumps(self_test(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
