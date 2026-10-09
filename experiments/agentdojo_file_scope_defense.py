"""TaskFileScope: fail-closed authorization for a trusted read/append task.

The optional AgentDojo dependency is imported only by migrate_file_contract.
This module has no model, provider, network, attack, or execution entry point.
The authored v1 contract is separate from the historical name-only control.
"""

from __future__ import annotations

import copy
import json
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from types import MappingProxyType
from typing import Any

from experiments.adapter_attestation import canonical_json, sha256_text


FAMILY = "TaskFileScope/v1"
SCOPED_TOOLS = frozenset({"get_file_by_id", "append_to_file"})
PERMITTED_TOOLS = SCOPED_TOOLS | {"search_files_by_filename"}


@dataclass(frozen=True)
class FileScopePolicy:
    """Trusted task grants; argument_contract is the only F-to-M change."""

    task_id: str
    file_id: str
    filename: str
    argument_contract: str = "v0"

    def __post_init__(self) -> None:
        if self.argument_contract not in {"v0", "v1"}:
            raise ValueError("unsupported policy argument contract")
        for value in (self.task_id, self.file_id, self.filename):
            if not isinstance(value, str) or not value or value != value.strip():
                raise ValueError("task, file ID and filename must be explicit nonempty strings")

    @property
    def sha256(self) -> str:
        return sha256_text(canonical_json({"family": FAMILY, **asdict(self)}))


def migrate_file_contract(runtime: Any) -> Any:
    """Return a new native runtime with explicit scoped-resource v1 arguments.

    Only read/append parameter schemas and their decoding adapters change.
    Other native tools remain exposed so a denial is observable, not hidden by
    an F/M-dependent schema filter. No native tool is invoked by this function.
    """

    from typing import Literal

    from agentdojo.functions_runtime import FunctionsRuntime
    from pydantic import ConfigDict, create_model

    resource = create_model(
        "ScopedDriveResource",
        __config__=ConfigDict(extra="forbid", strict=True),
        space=(Literal["cloud_drive"], ...),
        file_id=(str, ...),
    )

    def adapt(original):
        def run(*, resource, **kwargs):
            return original(file_id=resource["file_id"], **kwargs)

        return run

    functions = dict(runtime.functions)
    for name in sorted(SCOPED_TOOLS):
        native = functions[name]
        expected = {"file_id", "content"} if name == "append_to_file" else {"file_id"}
        if set(native.parameters.model_fields) != expected:
            raise ValueError("file contract migration requires the native v0 schema")
        fields = {"resource": (resource, ...)}
        if name == "append_to_file":
            fields["content"] = (str, ...)
        parameters = create_model(
            "ScopedReadFile" if name == "get_file_by_id" else "ScopedAppendFile",
            __config__=ConfigDict(extra="forbid", strict=True),
            **fields,
        )
        description = (
            "Read a file using its explicit cloud_drive resource."
            if name == "get_file_by_id"
            else "Append content to a file using its explicit cloud_drive resource."
        )
        functions[name] = native.model_copy(update={
            "parameters": parameters,
            "run": adapt(native.run),
            "description": description,
            "full_docstring": description,
        })
    return FunctionsRuntime(list(functions.values()))


class FileScopeRuntime:
    """Authorize before native dispatch; policy denials are normal responses.

    The trusted caller creates a fresh instance per task/episode and retains
    the base runtime. This protects tool-calling agents, not untrusted Python
    code with access to this process or the native callable objects.
    """

    def __init__(self, runtime: Any, policy: FileScopePolicy) -> None:
        if not isinstance(policy, FileScopePolicy):
            raise TypeError("a trusted FileScopePolicy is required")
        if not PERMITTED_TOOLS <= set(runtime.functions):
            raise ValueError("runtime lacks the task's required file tools")
        self._base = runtime
        self._policy = policy
        self._registered = dict(runtime.functions)
        self._events: list[dict[str, Any]] = []

    @property
    def functions(self) -> Mapping[str, Any]:
        return MappingProxyType(self._base.functions)

    @property
    def policy(self) -> FileScopePolicy:
        return self._policy

    @property
    def events(self) -> tuple[dict[str, Any], ...]:
        return tuple(dict(event) for event in self._events)

    def update_functions(self, functions: Mapping[str, Any]) -> None:
        if any(self._registered.get(name) is not value for name, value in functions.items()):
            raise ValueError("a guarded runtime only accepts filtering of registered functions")
        self._base.update_functions(dict(functions))

    def _authorize(self, function: str, arguments: dict[str, Any]) -> str | None:
        if function not in PERMITTED_TOOLS:
            return "tool_not_granted"
        native = self.functions.get(function)
        if native is None or self._registered.get(function) is not native:
            return "registry_changed_or_tool_unavailable"
        if set(arguments) - set(native.parameters.model_fields):
            return "unknown_argument"
        try:
            # Reject nested FunctionCall objects before FunctionsRuntime can
            # evaluate them. Never stringify unsupported Python objects.
            json.dumps(arguments, allow_nan=False)
            native.parameters.model_validate(arguments, strict=True)
        except (TypeError, ValueError, RecursionError):
            return "invalid_arguments"
        if function == "search_files_by_filename":
            return None if arguments.get("filename") == self.policy.filename else "filename_not_granted"
        if self.policy.argument_contract == "v0":
            resource_id = arguments.get("file_id")
        else:
            resource = arguments.get("resource")
            if not isinstance(resource, dict) or set(resource) != {"space", "file_id"}:
                return "policy_resource_shape_mismatch"
            if resource["space"] != "cloud_drive":
                return "resource_space_not_granted"
            resource_id = resource["file_id"]
        if not isinstance(resource_id, str) or resource_id != self.policy.file_id:
            return "file_not_granted_or_policy_not_migrated"
        return None

    def run_function(
        self, env: Any, function: str, kwargs: Mapping[str, Any], raise_on_error: bool = False
    ) -> tuple[Any, str | None]:
        if not isinstance(function, str):
            raise TypeError("function name must be a string")
        arguments = copy.deepcopy(dict(kwargs)) if isinstance(kwargs, Mapping) else None
        reason = "invalid_arguments" if arguments is None else self._authorize(function, arguments)
        try:
            digest = sha256_text(canonical_json(arguments)) if arguments is not None else None
        except (TypeError, ValueError, RecursionError):
            digest = None
        event = {
            "ordinal": len(self._events), "tool": function,
            "policy_sha256": self.policy.sha256, "arguments_sha256": digest,
            "decision": "DENY" if reason else "ALLOW", "reason": reason,
            "dispatched": reason is None, "tool_error": False,
        }
        self._events.append(event)
        if reason:
            return {"policy_decision": "DENY", "reason": reason}, None
        try:
            result, error = self._base.run_function(env, function, arguments, raise_on_error=raise_on_error)
        except Exception:
            event["tool_error"] = True
            raise
        event["tool_error"] = error is not None
        return result, error
