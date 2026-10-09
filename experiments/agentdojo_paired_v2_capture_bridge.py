"""Fresh-process AgentDojo v2 capture bridge.

The v2 driver owns scheduling; this module owns one episode's runtime evidence.
Each call to :func:`run_episode` starts a new Python process so import caches,
runtime registries, and mutable AgentDojo environments cannot leak between the
v0 and v1 siblings.

The bridge is deliberately small and fail-closed:

* it requires an explicit OpenAI-compatible base URL and API key;
* it verifies the pinned AgentDojo checkout and source witnesses before running;
* it replaces AgentDojo's tenacity-wrapped request helper with a one-call
  recorder (no automatic retry);
* it records only redacted model metadata plus hashes, never API credentials.

The endpoint can be a local OpenAI-compatible server for integration tests. A
completed record from a fake/local provider is still only integration evidence;
the manifest's Runpod-bound model identity must be used for a research run.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "experiments" / "fixtures" / "agentdojo_paired_v2_execution_manifest_v1.json"
CAPTURE_SCHEMA_VERSION = "agentdojo-paired-v2-capture/v1"
REDACTION_POLICY = "agentdojo-paired-v2-capture-redaction/v1"
API_KEY_ENV = "AGENTDOJO_CAPTURE_API_KEY"


class CaptureBridgeError(RuntimeError):
    """The episode could not produce provenance-valid runtime evidence."""


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _text_sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(ch in "0123456789abcdef" for ch in value)


def _execution_budget(plan: Mapping[str, Any]) -> dict[str, Any]:
    """Validate the manifest-bound per-episode provider/tool budget."""

    raw = plan.get("execution_budget")
    if not isinstance(raw, Mapping):
        raise CaptureBridgeError("episode execution budget is missing")
    fields = ("max_model_requests_per_episode", "max_tool_calls_per_episode")
    values: dict[str, Any] = {}
    for field in fields:
        value = raw.get(field)
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise CaptureBridgeError(f"episode execution budget field {field} is invalid")
        values[field] = value
    overflow_policy = raw.get("overflow_policy")
    if not isinstance(overflow_policy, str) or not overflow_policy.strip():
        raise CaptureBridgeError("episode execution budget overflow policy is missing")
    values["overflow_policy"] = overflow_policy
    return values


def _jsonable(value: Any) -> Any:
    """Convert AgentDojo/OpenAI/Pydantic values into the JSON evidence domain."""

    if hasattr(value, "model_dump"):
        try:
            return _jsonable(value.model_dump(mode="json"))
        except TypeError:
            return _jsonable(value.model_dump())
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise TypeError(f"value is not JSON-serializable: {type(value).__name__}")


def _state_json(environment: Any) -> dict[str, Any] | None:
    if environment is None or not hasattr(environment, "model_dump"):
        return None
    try:
        value = _jsonable(environment.model_dump(mode="json"))
    except (TypeError, ValueError):
        return None
    return value if isinstance(value, dict) else None


def _git_text(source: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(source), *args],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return completed.stdout.strip()


def _verify_source_checkout(source: Path, expected_commit: str) -> Path:
    source = source.resolve()
    if not source.is_dir() or not (source / "src").is_dir():
        raise CaptureBridgeError(f"pinned AgentDojo source is missing: {source}")
    try:
        actual_commit = _git_text(source, "rev-parse", "HEAD")
        dirty = _git_text(source, "status", "--porcelain")
    except (OSError, subprocess.CalledProcessError) as exc:
        raise CaptureBridgeError("unable to verify the pinned AgentDojo checkout") from exc
    if actual_commit != expected_commit:
        raise CaptureBridgeError(f"AgentDojo source must be pinned at {expected_commit}, got {actual_commit}")
    if dirty:
        raise CaptureBridgeError("AgentDojo source checkout is not clean")
    return source


def _verify_url(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CaptureBridgeError("base_url is required; no model request was made")
    normalized = value.strip().rstrip("/")
    parsed = urlparse(normalized)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise CaptureBridgeError("base_url must be an absolute http(s) URL")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise CaptureBridgeError("base_url must not contain credentials, query, or fragment")
    return normalized


def _manifest_and_plan(plan: Mapping[str, Any]) -> tuple[dict[str, Any], str]:
    from experiments.agentdojo_paired_v2_execution_manifest import load_manifest

    manifest = load_manifest(DEFAULT_MANIFEST)
    episode_id = plan.get("episode_id")
    selected = next((row for row in manifest["episodes"] if row["episode_id"] == episode_id), None)
    base_plan = dict(plan)
    for field in (
        "defense_adapter_id", "defense_variant", "amendment_manifest_sha256",
        "amendment_cell", "amendment_policy_sha256",
        "amendment_schema_descriptor_sha256", "amendment_normalization_sha256",
        "amendment_expected_utility_success",
    ):
        base_plan.pop(field, None)
    if selected is None or _canonical_bytes(dict(selected)) != _canonical_bytes(base_plan):
        raise CaptureBridgeError("episode plan is not the pinned v2 manifest row")
    return manifest, _sha256(manifest)


def _runtime_metadata(expected: Mapping[str, Any]) -> dict[str, str]:
    """Return the child runtime identity after checking manifest-bound fields.

    The pinned source contract historically recorded only Python/Pydantic/
    PyYAML.  Comparing the expected mapping as a subset keeps old fixtures
    readable while allowing the v2 fixture to bind the OpenAI client and
    AgentDojo distribution versions as soon as they are recorded there.
    """

    from importlib.metadata import version
    import locale

    actual: dict[str, str] = {
        "default_text_encoding": locale.getpreferredencoding(False).lower(),
        "python_utf8_mode": str(sys.flags.utf8_mode),
        "python_implementation": platform.python_implementation(),
        "python_version": platform.python_version(),
    }
    for field, distribution in (
        ("openai_version", "openai"),
        ("agentdojo_version", "agentdojo"),
        ("pydantic_version", "pydantic"),
        ("pyyaml_version", "PyYAML"),
    ):
        try:
            actual[field] = version(distribution)
        except Exception as exc:  # pragma: no cover - import metadata is environment-specific
            raise CaptureBridgeError(f"required runtime package is unavailable: {distribution}") from exc
    mismatches = {key: (expected.get(key), actual.get(key)) for key in expected if expected.get(key) != actual.get(key)}
    if mismatches:
        raise CaptureBridgeError(f"runtime identity mismatch: expected {dict(expected)!r}, observed {actual!r}")
    return actual


def _pythonpath_witness(source: Path) -> dict[str, Any]:
    """Require and record the controlled repository-plus-source PYTHONPATH."""

    entries = os.environ.get("PYTHONPATH", "").split(os.pathsep) if os.environ.get("PYTHONPATH") else []
    expected = [str(ROOT.resolve()), str((source / "src").resolve())]
    if entries != expected:
        raise CaptureBridgeError(
            "child PYTHONPATH is not the controlled repository-plus-source path"
        )
    return {
        "schema_version": "agentdojo-v2-pythonpath-witness/v1",
        "entries": ["<repository-root>", "<agentdojo-source>/src"],
        "entries_sha256": _sha256(entries),
        "entry_count": len(entries),
    }


def _source_witnesses(
    source: Path, plan: Mapping[str, Any]
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, str], dict[str, Any]]:
    """Load contracts and verify their declared source files in the child."""

    from experiments.agentdojo_v2_effect_oracle_contract import (
        _verify_agentdojo_import_origin as verify_effect_origin,
        _verify_effect_source_files,
        load_contract as load_effect_contract,
    )
    from experiments.agentdojo_v2_no_injecagent_default_control_contract import (
        _verify_control_source_files,
        _verify_agentdojo_import_origin as verify_control_origin,
        load_contract as load_default_control_contract,
    )
    from experiments.agentdojo_v2_utility_trace_normalization_contract import load_contract as load_trace_contract

    effect = load_effect_contract(ROOT / "experiments" / "fixtures" / "agentdojo_v2_effect_oracle_contract_v1.json")
    default_control = load_default_control_contract(
        ROOT / "experiments" / "fixtures" / "agentdojo_v2_no_injecagent_default_control_contract_v1.json"
    )
    trace_contract = load_trace_contract(
        ROOT / "experiments" / "fixtures" / "agentdojo_v2_utility_trace_normalization_contract_v1.json"
    )
    runtime_identity = _runtime_metadata(plan["runtime_identity"])
    pythonpath_witness = _pythonpath_witness(source)
    if plan["arm"] == "attack":
        _verify_effect_source_files(source)
        verify_effect_origin(source)
        source_witness = effect["source"]["verification_witness"]
    else:
        _verify_control_source_files(source)
        verify_control_origin(source)
        source_witness = default_control["source"]["verification_witness"]
    return effect, default_control, trace_contract, runtime_identity, pythonpath_witness


class _RecordingRuntime:
    """A thin proxy around FunctionsRuntime that records real tool dispatches."""

    def __init__(self, base_runtime: Any, *, max_tool_calls: int) -> None:
        self._base = base_runtime
        if isinstance(max_tool_calls, bool) or not isinstance(max_tool_calls, int) or max_tool_calls <= 0:
            raise CaptureBridgeError("max_tool_calls must be a positive integer")
        self._max_tool_calls = max_tool_calls
        self.dispatch_events: list[dict[str, Any]] = []

    @property
    def functions(self) -> dict[str, Any]:
        return self._base.functions

    def update_functions(self, functions: dict[str, Any]) -> None:
        self._base.update_functions(functions)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._base, name)

    def run_function(
        self,
        env: Any,
        function: str,
        kwargs: Mapping[str, Any],
        raise_on_error: bool = False,
    ) -> tuple[Any, str | None]:
        if len(self.dispatch_events) >= self._max_tool_calls:
            raise CaptureBridgeError("tool_call_cap_exceeded")
        pre = _state_json(env)
        try:
            result, error = self._base.run_function(env, function, kwargs, raise_on_error=raise_on_error)
        except BaseException as exc:
            event = {
                    "function": function,
                    "args": _jsonable(kwargs),
                    "pre_state_sha256": _sha256(pre) if pre is not None else None,
                    "post_state_sha256": _sha256(_state_json(env)) if _state_json(env) is not None else None,
                    "error": f"{type(exc).__name__}: {exc}",
                }
            policy_events = getattr(self._base, "events", ())
            if policy_events:
                event["policy_event"] = dict(policy_events[-1])
            self.dispatch_events.append(event)
            raise
        post = _state_json(env)
        event = {
                "function": function,
                "args": _jsonable(kwargs),
                "pre_state_sha256": _sha256(pre) if pre is not None else None,
                "post_state_sha256": _sha256(post) if post is not None else None,
                "result_sha256": _sha256(_jsonable(result)),
                "error": error,
            }
        policy_events = getattr(self._base, "events", ())
        if policy_events:
            event["policy_event"] = dict(policy_events[-1])
        self.dispatch_events.append(event)
        return result, error


def _prepare_runtime_for_plan(runtime: Any, plan: Mapping[str, Any]) -> tuple[Any, str | None]:
    """Install an amendment-specific guard without changing historical v2.

    Historical plans omit defense_adapter_id and follow the existing name-only
    contract migration. A prospective TaskFileScope plan opts in explicitly
    and owns its v0/v1 argument migration instead.
    """

    adapter_id = plan.get("defense_adapter_id")
    if adapter_id is None:
        return runtime, None
    if adapter_id != "TaskFileScope":
        raise CaptureBridgeError(f"unsupported defense adapter: {adapter_id}")
    from experiments.agentdojo_file_scope_defense import FileScopePolicy, FileScopeRuntime, migrate_file_contract

    variant = plan.get("defense_variant")
    version = plan.get("contract", {}).get("version")
    if variant not in {"F", "M"} or version not in {"v0", "v1"}:
        raise CaptureBridgeError("TaskFileScope plans require defense_variant F/M and v0/v1")
    policy_contract = "v1" if variant == "M" and version == "v1" else "v0"
    prepared = migrate_file_contract(runtime) if version == "v1" else runtime
    policy = FileScopePolicy("user_task_29", "3", "team-building-activities.docx", policy_contract)
    return FileScopeRuntime(prepared, policy), adapter_id


class _RequestCapture:
    """One-call OpenAI helper replacement used inside the fresh child."""

    def __init__(self, plan: Mapping[str, Any]) -> None:
        self.plan = plan
        budget = _execution_budget(plan)
        self._max_model_requests = budget["max_model_requests_per_episode"]
        self.requests: list[dict[str, Any]] = []
        self.responses: list[dict[str, Any]] = []
        self.response_tool_call_ids: list[list[str]] = []
        self.tool_call_ids: list[str] = []

    def request(
        self,
        client: Any,
        model: str,
        messages: Sequence[Any],
        tools: Sequence[Any],
        reasoning_effort: Any,
        temperature: float | None,
    ) -> Any:
        if len(self.requests) >= self._max_model_requests:
            raise CaptureBridgeError("model_request_cap_exceeded")
        body: dict[str, Any] = {
            "model": model,
            "messages": _jsonable(messages),
            "tools": _jsonable(list(tools)),
            "tool_choice": "auto" if tools else None,
            "temperature": temperature,
        }
        self.requests.append(body)
        kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "tools": list(tools),
            "tool_choice": "auto" if tools else None,
            "temperature": temperature,
        }
        if reasoning_effort is not None:
            kwargs["reasoning_effort"] = reasoning_effort
        response = client.chat.completions.create(**kwargs)
        response_json = _jsonable(response)
        if not isinstance(response_json, dict):
            raise CaptureBridgeError("OpenAI-compatible provider returned a non-object response")
        self.responses.append(response_json)
        response_tool_call_ids: list[str] = []
        choices = response_json.get("choices")
        if isinstance(choices, list) and choices:
            message = choices[0].get("message")
            if isinstance(message, dict):
                calls = message.get("tool_calls") or []
                if isinstance(calls, list):
                    for call in calls:
                        if isinstance(call, dict) and isinstance(call.get("id"), str) and call["id"]:
                            response_tool_call_ids.append(call["id"])
        self.response_tool_call_ids.append(response_tool_call_ids)
        self.tool_call_ids.extend(response_tool_call_ids)
        return response

    def response_identity(self, index: int = 0) -> dict[str, Any]:
        if index < 0 or index >= len(self.responses):
            raise CaptureBridgeError("model returned no observable response")
        response = self.responses[index]
        model_binding = self.plan["model_identity_binding"]
        identity = {
            key: model_binding[key]
            for key in ("endpoint_manifest_sha256", "endpoint_release_id", "image_digest", "model_id")
        }
        returned_revision = response.get("system_fingerprint")
        if isinstance(returned_revision, str) and returned_revision:
            identity["returned_revision"] = returned_revision
        else:
            identity["returned_revision"] = ""
            identity["revision_status"] = "unavailable_with_reason"
            identity["revision_unavailable_reason"] = "provider response omitted an immutable release revision"
        if isinstance(response.get("id"), str):
            identity["response_id"] = response["id"]
        if isinstance(response.get("model"), str):
            identity["response_model"] = response["model"]
        if isinstance(response.get("created"), int):
            identity["response_created"] = response["created"]
        return identity

    def request_records(self) -> list[dict[str, Any]]:
        """Return a one-to-one commitment for every request and response."""

        if len(self.requests) != len(self.responses):
            raise CaptureBridgeError("model request/response provenance is incomplete")
        if len(self.response_tool_call_ids) != len(self.responses):
            raise CaptureBridgeError("model response tool-call provenance is incomplete")
        return [
            {
                "ordinal": index,
                "serialized_request": request,
                "serialized_request_sha256": _sha256(request),
                "request_parameters_sent": dict(request),
                "response_sha256": _sha256(response),
                "response_identity": self.response_identity(index),
                "model_originated_tool_call_ids": list(self.response_tool_call_ids[index]),
            }
            for index, (request, response) in enumerate(zip(self.requests, self.responses, strict=True))
        ]


def _metadata(plan: Mapping[str, Any], manifest_digest: str, run_id: str) -> dict[str, Any]:
    contract = plan["contract"]
    metadata = {
        "episode_id": plan["episode_id"],
        "pair_id": plan["pair_id"],
        "case_id": plan["case_id"],
        "stratum_id": plan["stratum_id"],
        "user_task_id": plan["user_task_id"],
        "arm": plan["arm"],
        "defense_id": plan["defense_id"],
        "defense_configuration_sha256": plan["defense_configuration_sha256"],
        "policy_manifest_sha256": plan["policy_manifest_sha256"],
        "model_configuration_id": plan["model_configuration_id"],
        "seed": plan["seed"],
        "contract_version": contract["version"],
        "arm_binding_sha256": plan["arm_binding_sha256"],
        "expected_pre_state_sha256": plan["expected_pre_state_sha256"],
        "effect_oracle_contract_sha256": plan["effect_oracle_contract_sha256"],
        "default_control_contract_sha256": plan["default_control_contract_sha256"],
        "trace_normalization_contract_sha256": plan["trace_normalization_contract_sha256"],
        "manifest_sha256": manifest_digest,
        "attempt_index": 1,
        "automatic_retry": False,
        "run_id": run_id,
    }
    if "source_cluster_id" in plan:
        metadata["source_cluster_id"] = plan["source_cluster_id"]
    for field in (
        "defense_adapter_id", "defense_variant", "amendment_manifest_sha256",
        "amendment_cell", "amendment_policy_sha256",
        "amendment_schema_descriptor_sha256", "amendment_normalization_sha256",
        "amendment_expected_utility_success",
    ):
        if field in plan:
            metadata[field] = plan[field]
    return metadata


def _carrier_witness(plan: Mapping[str, Any], pre_state: Mapping[str, Any], injections: Mapping[str, str]) -> dict[str, Any]:
    binding = plan["arm_binding"]["injection"]
    carrier_id = binding["carrier_id"]
    text = injections.get(carrier_id)
    if not isinstance(text, str) or not text:
        raise CaptureBridgeError("InjecAgent did not materialize the selected carrier")
    pre_hash = _sha256(pre_state)
    artifact = {
        "injection_task_id": binding["injection_task_id"],
        "carrier_id": carrier_id,
        "pre_agent_state_sha256": pre_hash,
        "carrier_text_sha256": _text_sha256(text),
        "carrier_text_character_count": len(text),
        "injection_map_sha256": _sha256(dict(injections)),
    }
    return {
        "mode": binding["mode"],
        "injection_task_id": binding["injection_task_id"],
        "carrier_id": carrier_id,
        "materialized": True,
        "materialized_before_agent": True,
        "pre_agent_state_sha256": pre_hash,
        "materialization_artifact": {"content": artifact, "sha256": _sha256(artifact)},
    }


def _trace_evidence(
    plan: Mapping[str, Any],
    request_capture: _RequestCapture,
    raw_trace: list[dict[str, Any]],
    canonical_trace: list[dict[str, Any]],
    normalization_witness: dict[str, Any] | None,
    dispatch_events: list[dict[str, Any]],
) -> dict[str, Any]:
    if not request_capture.requests or not request_capture.responses:
        raise CaptureBridgeError("model request/response provenance is missing")
    request_records = request_capture.request_records()
    first_record = request_records[0]
    first_request = first_record["serialized_request"]
    first_response = first_record["response_identity"]
    request_sha256s = [item["serialized_request_sha256"] for item in request_records]
    response_sha256s = [item["response_sha256"] for item in request_records]
    response_ids = [item["response_identity"].get("response_id") for item in request_records]
    response_identities = [item["response_identity"] for item in request_records]
    trace_content: dict[str, Any] = {
        "serialized_request_sha256": first_record["serialized_request_sha256"],
        "model_response_identity": first_response,
        "model_response_identities": response_identities,
        "model_originated_tool_call_ids": request_capture.tool_call_ids,
        "model_originated_tool_call_count": len(request_capture.tool_call_ids),
        "request_count": len(request_records),
        "request_sha256s": request_sha256s,
        "response_count": len(request_records),
        "response_sha256s": response_sha256s,
        "response_ids": response_ids,
        "model_request_records_sha256": _sha256(request_records),
        "dispatcher_trace_sha256": _sha256(dispatch_events),
        "dispatcher_event_count": len(dispatch_events),
        "dispatch_provenance_gate": (
            "digest_and_count_only; retain a per-dispatch redacted commitment before any "
            "security-or-utility efficacy claim"
        ),
    }
    if plan.get("defense_adapter_id") == "TaskFileScope":
        policy_events = [
            event["policy_event"]
            for event in dispatch_events
            if isinstance(event, dict) and isinstance(event.get("policy_event"), dict)
        ]
        if len(policy_events) != len(dispatch_events):
            raise CaptureBridgeError("TaskFileScope dispatch policy evidence is incomplete")
        trace_content["per_dispatch_policy_events"] = policy_events
        trace_content["policy_event_count"] = len(policy_events)
    if plan["arm"] != "attack":
        if normalization_witness is None:
            raise CaptureBridgeError("default-control trace normalization witness is missing")
        trace_content["raw_function_trace_sha256"] = normalization_witness["raw_trace_sha256"]
        trace_content["canonical_function_trace_sha256"] = normalization_witness["canonical_trace_sha256"]
    return {
        "serialized_request": first_request,
        "serialized_request_sha256": first_record["serialized_request_sha256"],
        "request_parameters_sent": first_record["request_parameters_sent"],
        "model_response_identity": first_response,
        "model_request_records": request_records,
        "redacted_trace": {
            "schema_version": "agentdojo-redacted-trace/v1",
            "sha256": _sha256(trace_content),
            "redaction_applied": True,
            "redaction_policy_sha256": _text_sha256(REDACTION_POLICY),
            "content": trace_content,
            "model_request_observed": True,
            "model_response_observed": True,
            "model_originated_tool_call_ids": request_capture.tool_call_ids,
            "tool_dispatch_provenance": "dispatcher_trace",
        },
    }


def _build_record(
    plan: Mapping[str, Any],
    manifest_digest: str,
    run_id: str,
    *,
    pre_state: dict[str, Any],
    post_state: dict[str, Any],
    reset_witness: dict[str, Any],
    terminal_output: str,
    raw_trace: list[dict[str, Any]],
    canonical_trace: list[dict[str, Any]],
    normalization_witness: dict[str, Any] | None,
    request_capture: _RequestCapture,
    dispatch_events: list[dict[str, Any]],
    source_witness: dict[str, Any],
    effect_contract: dict[str, Any],
    default_control: dict[str, Any],
    runtime_migration: dict[str, Any],
    carrier_witness: dict[str, Any] | None,
    failure_flags: dict[str, bool],
    runtime_identity: dict[str, str],
    pythonpath_witness: dict[str, Any],
) -> dict[str, Any]:
    trace = _trace_evidence(
        plan,
        request_capture,
        raw_trace,
        canonical_trace,
        normalization_witness,
        dispatch_events,
    )
    record: dict[str, Any] = {
        **_metadata(plan, manifest_digest, run_id),
        "schema_version": CAPTURE_SCHEMA_VERSION,
        "result_status": "completed",
        "typed_pre_state": pre_state,
        "typed_post_state": post_state,
        "reset_witness": reset_witness,
        "terminal_status": "completed",
        "failure_flags": failure_flags,
        "ground_truth_tool_execution": False,
        "source_verification_witness": source_witness,
        "runtime_identity_witness": runtime_identity,
        "pythonpath_witness": pythonpath_witness,
        "state_schema_version": effect_contract["oracle_implementation"]["state_schema_version"],
        "contract_migration_witness_or_absence": runtime_migration,
        "raw_function_trace": raw_trace,
        "canonical_function_trace": canonical_trace,
        "function_trace": canonical_trace,
        "execution_budget_witness": {
            "schema_version": "agentdojo-execution-budget-witness/v1",
            "max_model_requests_per_episode": _execution_budget(plan)["max_model_requests_per_episode"],
            "max_tool_calls_per_episode": _execution_budget(plan)["max_tool_calls_per_episode"],
            "model_request_count": len(request_capture.requests),
            "model_tool_call_count": len(request_capture.tool_call_ids),
            "tool_dispatch_count": len(dispatch_events),
            "overflow": False,
        },
        **trace,
    }
    if plan["arm"] == "attack":
        record.update(
            {
                "oracle_implementation_sha256": effect_contract["oracle_implementation"]["sha256"],
                "carrier_materialization_witness": carrier_witness,
            }
        )
    else:
        binding = plan["arm_binding"]["default_control_contract"]
        record.update(
            {
                "utility_oracle_implementation_sha256": default_control["utility_oracle_implementation"]["sha256"],
                "no_injecagent_default_control_witness": binding["control_witness"],
                "terminal_output": terminal_output,
                "trace_normalization_witness": normalization_witness,
            }
        )
    return record


def _run_child(
    plan: dict[str, Any],
    *,
    source_root: Path,
    base_url: str,
    api_key: str,
    model: str,
    run_id: str,
    timeout: float,
) -> dict[str, Any]:
    # Verify and prepend the source before importing any module that can import
    # AgentDojo. A globally installed copy must never win import resolution.
    sys.path.insert(0, str(ROOT))
    from experiments.agentdojo_pilot_manifest import SOURCE_COMMIT

    execution_budget = _execution_budget(plan)
    expected_commit = SOURCE_COMMIT
    source = _verify_source_checkout(source_root, expected_commit)
    source_src = source / "src"
    sys.path.insert(0, str(source_src))
    manifest, manifest_digest = _manifest_and_plan(plan)

    # Importing the pinned source and contracts is intentionally lazy: the
    # parent process can reject missing credentials without importing AgentDojo.
    from experiments.agentdojo_contract_migration import (
        MANIFEST_ENV,
        _registry_witness,
        apply_contract_to_runtime,
        load_contract as load_tool_contract,
    )
    from experiments.agentdojo_v2_utility_trace_normalization_contract import (
        _normalize_unchecked,
        load_contract as load_trace_contract,
    )
    if model != plan["model_identity_binding"]["model_id"]:
        raise CaptureBridgeError(
            f"model mismatch: plan binds {plan['model_identity_binding']['model_id']}, requested {model}"
        )
    (
        effect_contract,
        default_control,
        trace_contract,
        runtime_identity,
        pythonpath_witness,
    ) = _source_witnesses(source, plan)
    tool_contract = load_tool_contract(ROOT / plan["contract"]["tool_contract_manifest"])

    from agentdojo.attacks.baseline_attacks import InjecAgentAttack
    from agentdojo.agent_pipeline.agent_pipeline import AgentPipeline, load_system_message
    from agentdojo.agent_pipeline.basic_elements import InitQuery, SystemMessage
    from agentdojo.agent_pipeline.llms import openai_llm
    from agentdojo.agent_pipeline.tool_execution import ToolsExecutionLoop, ToolsExecutor
    from agentdojo.functions_runtime import FunctionsRuntime
    from agentdojo.task_suite.load_suites import get_suite
    from agentdojo.task_suite.task_suite import functions_stack_trace_from_messages, model_output_from_messages
    from agentdojo.types import get_text_content_as_str
    import openai

    # Historical v1 migration is activated only through the manifest
    # environment variable. Amendment-specific defenses own their migration.
    amendment_adapter = plan.get("defense_adapter_id")
    if plan["contract"]["version"] == "v1" and amendment_adapter is None:
        os.environ[MANIFEST_ENV] = str(ROOT / plan["contract"]["tool_contract_manifest"])
    else:
        os.environ.pop(MANIFEST_ENV, None)

    suite = get_suite("v1.2.2", "workspace")
    user_task = suite.get_user_task_by_id(plan["user_task_id"])
    injection_task = None
    injections: dict[str, str] = {}
    carrier_witness: dict[str, Any] | None = None
    if plan["arm"] == "attack":
        injection_task = suite.get_injection_task_by_id(plan["arm_binding"]["injection"]["injection_task_id"])
        attack = InjecAgentAttack(suite, None)
        injections = attack.attack(user_task, injection_task)
        if sorted(injections) != [plan["arm_binding"]["injection"]["carrier_id"]]:
            raise CaptureBridgeError("InjecAgent materialized an unexpected carrier set")
        environment = user_task.init_environment(suite.load_and_inject_default_environment(injections))
    else:
        defaults = suite.get_injection_vector_defaults()
        control = plan["arm_binding"]["default_control_contract"]["control_witness"]
        carrier_id = control["selected_carrier_id"]
        carrier_text = defaults.get(carrier_id)
        if (
            not isinstance(carrier_text, str)
            or not carrier_text
            or _text_sha256(carrier_text) != control["selected_carrier_default_sha256"]
            or _sha256(defaults) != control["default_injection_map_sha256"]
        ):
            raise CaptureBridgeError("default-carrier construction does not match the pinned control witness")
        environment = user_task.init_environment(suite.load_and_inject_default_environment({}))
    pre_environment = environment.model_copy(deep=True)
    pre_state = _state_json(pre_environment)
    if pre_state is None or _sha256(pre_state) != plan["expected_pre_state_sha256"]:
        raise CaptureBridgeError("fresh pre-state does not match the manifest binding")
    if plan["arm"] == "attack":
        carrier_witness = _carrier_witness(plan, pre_state, injections)

    runtime_base = FunctionsRuntime(suite.tools)
    runtime_base, applied_adapter = _prepare_runtime_for_plan(runtime_base, plan)
    runtime = _RecordingRuntime(
        runtime_base,
        max_tool_calls=execution_budget["max_tool_calls_per_episode"],
    )
    migration_before = _registry_witness(runtime.functions, tool_contract)

    capture = _RequestCapture(plan)
    original_request = openai_llm.chat_completion_request
    openai_llm.chat_completion_request = capture.request
    try:
        # The SDK retries independently of AgentDojo's replaced request helper.
        client = openai.OpenAI(
            api_key=api_key, base_url=base_url,
            timeout=max(5.0, min(timeout, 300.0)), max_retries=0,
        )
        llm = openai_llm.OpenAILLM(client, model, temperature=0.0)
        pipeline = AgentPipeline(
            [
                SystemMessage(load_system_message(None)),
                InitQuery(),
                llm,
                ToolsExecutionLoop(
                    [ToolsExecutor(), llm],
                    max_iters=max(0, execution_budget["max_model_requests_per_episode"] - 1),
                ),
            ]
        )
        pipeline.name = model
        _, _, post_environment, messages, _ = pipeline.query(user_task.PROMPT, runtime, pre_environment)
    finally:
        openai_llm.chat_completion_request = original_request

    migration_marker = getattr(runtime, "_agentdojo_contract_migration_witness", None)
    if applied_adapter is not None:
        runtime_migration = {
            "status": "defense_adapter_applied",
            "adapter_id": applied_adapter,
            "defense_variant": plan["defense_variant"],
            "contract_version": plan["contract"]["version"],
        }
        registry_witness = _registry_witness(runtime.functions, tool_contract)
    elif plan["contract"]["version"] == "v1":
        if not isinstance(migration_marker, Mapping):
            raise CaptureBridgeError("v1 migration did not leave a native witness on the runtime")
        runtime_migration = {"status": "applied", "witness": dict(migration_marker)}
        registry_witness = dict(migration_marker["after"])
    else:
        runtime_migration = {"status": "not_applied"}
        registry_witness = migration_before

    if (
        not messages
        or messages[-1].get("role") != "assistant"
        or messages[-1].get("tool_calls")
    ):
        raise CaptureBridgeError("AgentDojo did not produce a terminal assistant message")
    terminal_blocks = model_output_from_messages(messages)
    terminal_output = get_text_content_as_str(terminal_blocks or [])
    raw_trace = [call.model_dump(mode="json") for call in functions_stack_trace_from_messages(messages)]
    if plan.get("defense_adapter_id") == "TaskFileScope":
        from experiments.agentdojo_file_scope_preflight import canonical_trace as normalize_file_scope_trace

        canonical_trace = normalize_file_scope_trace(plan["contract"]["version"], raw_trace)
        normalization_witness = {
            "schema_version": "task-file-scope-trace-normalization/v1",
            "version": plan["contract"]["version"],
            "raw_trace_sha256": _sha256(raw_trace),
            "canonical_trace_sha256": _sha256(canonical_trace),
        }
    else:
        canonical_trace, normalization_witness = _normalize_unchecked(plan["contract"]["version"], raw_trace)
    post_state = _state_json(post_environment)
    if post_state is None:
        raise CaptureBridgeError("post-environment is not a typed JSON state")
    tool_error = any(
        message.get("role") == "tool" and message.get("error") is not None for message in messages
    )
    failure_flags = {
        "runner_error": False,
        "tool_error": bool(tool_error),
        "timeout": False,
        "cancelled": False,
    }
    record = _build_record(
        plan,
        manifest_digest,
        run_id,
        pre_state=pre_state,
        post_state=post_state,
        reset_witness={
            "verified": True,
            "pre_state_sha256": _sha256(pre_state),
            "strategy": "fresh_child_process_and_deep_copy",
            "source_commit": manifest["source"]["agentdojo"]["verification_witness"]["commit"],
        },
        terminal_output=terminal_output,
        raw_trace=raw_trace,
        canonical_trace=canonical_trace,
        normalization_witness=normalization_witness,
        request_capture=capture,
        dispatch_events=runtime.dispatch_events,
        source_witness=(
            effect_contract["source"]["verification_witness"]
            if plan["arm"] == "attack"
            else default_control["source"]["verification_witness"]
        ),
        effect_contract=effect_contract,
        default_control=default_control,
        runtime_migration=runtime_migration,
        carrier_witness=carrier_witness,
        failure_flags=failure_flags,
        runtime_identity=runtime_identity,
        pythonpath_witness=pythonpath_witness,
    )
    record["registry_witness"] = registry_witness
    return record


def run_episode(
    plan: Mapping[str, Any],
    *,
    source_root: Path,
    python_executable: str | Path,
    base_url: str,
    api_key: str,
    model: str,
    run_id: str,
    timeout: float = 300.0,
) -> dict[str, Any]:
    """Run exactly one manifest row in a fresh child process.

    The parent performs only input validation and process orchestration. Missing
    endpoint credentials are rejected before a child is spawned.
    """

    if not isinstance(plan, Mapping):
        raise CaptureBridgeError("plan must be an object")
    if not isinstance(api_key, str) or not api_key.strip():
        raise CaptureBridgeError("api_key is required; no model request was made")
    normalized_url = _verify_url(base_url)
    if not isinstance(run_id, str) or not run_id.strip():
        raise CaptureBridgeError("run_id must be a non-empty string")
    if timeout <= 0:
        raise CaptureBridgeError("timeout must be positive")
    _execution_budget(plan)
    executable = Path(python_executable)
    if not executable.is_file():
        raise CaptureBridgeError(f"python executable does not exist: {executable}")
    source = Path(source_root).resolve()
    if not source.is_dir():
        raise CaptureBridgeError(f"source_root does not exist: {source}")

    with tempfile.TemporaryDirectory(prefix="agentdojo-v2-capture-") as temp_dir:
        temp = Path(temp_dir)
        plan_path = temp / "plan.json"
        output_path = temp / "record.json"
        plan_path.write_text(json.dumps(dict(plan), ensure_ascii=False, indent=2), encoding="utf-8")
        environment = os.environ.copy()
        environment[API_KEY_ENV] = api_key
        environment["PYTHONIOENCODING"] = "utf-8"
        # Do not let an inherited path shadow the pinned source or dependencies.
        # The child records and validates this exact two-entry path.
        environment["PYTHONPATH"] = os.pathsep.join([str(ROOT), str(source / "src")])
        child = [
            str(executable),
            str(Path(__file__).resolve()),
            "--child",
            "--plan",
            str(plan_path),
            "--output",
            str(output_path),
            "--source-root",
            str(source),
            "--base-url",
            normalized_url,
            "--model",
            model,
            "--run-id",
            run_id,
            "--timeout",
            str(timeout),
        ]
        try:
            completed = subprocess.run(
                child,
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                env=environment,
                timeout=max(5.0, timeout + 5.0),
            )
        except subprocess.TimeoutExpired as exc:
            raise CaptureBridgeError("capture child timed out; no retry was attempted") from exc
        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout or "capture child failed").strip()
            raise CaptureBridgeError(detail[:2000])
        try:
            value = json.loads(output_path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError) as exc:
            raise CaptureBridgeError("capture child exited without a valid record") from exc
        if not isinstance(value, dict) or value.get("result_status") != "completed":
            raise CaptureBridgeError("capture child returned a non-completed record")
        return value


def _child_main(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--child", action="store_true")
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--timeout", type=float, default=300.0)
    args = parser.parse_args(list(argv))
    if not args.child:
        parser.error("--child is required")
    api_key = os.environ.get(API_KEY_ENV, "")
    if not api_key:
        raise SystemExit("missing AGENTDOJO_CAPTURE_API_KEY")
    plan = json.loads(args.plan.read_text(encoding="utf-8"))
    record = _run_child(
        plan,
        source_root=args.source_root,
        base_url=args.base_url,
        api_key=api_key,
        model=args.model,
        run_id=args.run_id,
        timeout=args.timeout,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    try:
        return _child_main(sys.argv[1:] if argv is None else argv)
    except Exception as exc:
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
