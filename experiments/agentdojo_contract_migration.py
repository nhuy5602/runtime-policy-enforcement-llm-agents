"""Fail-closed, name-only tool-contract migration for a pinned AgentDojo suite.

The AgentDojo OpenAI-compatible LLM adapter serializes ``runtime.functions``
into the tool schemas it exposes to the model.  This module is loaded before a
benchmark run and, only when its explicit manifest environment variable is
set, replaces the pinned Workspace registry's v0 names with its declared v1
names.  It preserves the same function object fields and callable; a witness
hash checks that name-independent descriptors match before and after.

It is deliberately a narrow *control* for a future migration-fidelity study.
It does not emulate a malicious tool, arbitrary adapter drift, real external
side effects, or an LLM security result.
"""

from __future__ import annotations

import atexit
import json
import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any

try:
    from adapter_attestation import canonical_json, sha256_text
except ModuleNotFoundError:  # pragma: no cover - package import from repo root
    from experiments.adapter_attestation import canonical_json, sha256_text


SCHEMA_VERSION = "agentdojo-tool-contract-migration/v1"
MANIFEST_ENV = "AGENTDOJO_CONTRACT_MANIFEST"
AUDIT_PATH_ENV = "AGENTDOJO_CONTRACT_AUDIT_PATH"
_RUNTIME_MARKER = "_agentdojo_contract_migration_witness"
_AUDIT_LOG: list[dict[str, Any]] = []


def _required_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value.strip()


def load_contract(path: Path) -> dict[str, Any]:
    """Load and validate the explicitly selected v0-to-v1 contract."""

    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("unsupported AgentDojo contract migration schema")
    source = payload.get("source")
    if not isinstance(source, Mapping):
        raise ValueError("contract source must be an object")
    for field in ("project", "commit", "benchmark_version", "suite"):
        _required_text(source.get(field), f"source.{field}")
    migration = payload.get("migration")
    if not isinstance(migration, Mapping) or migration.get("kind") != "function-name-only":
        raise ValueError("contract must declare a function-name-only migration")
    mapping = migration.get("v0_to_v1")
    if not isinstance(mapping, Mapping) or not mapping:
        raise ValueError("contract migration.v0_to_v1 must be a non-empty object")
    names_v0: set[str] = set()
    names_v1: set[str] = set()
    for raw_v0, raw_v1 in mapping.items():
        v0 = _required_text(raw_v0, "migration v0 name")
        v1 = _required_text(raw_v1, "migration v1 name")
        if v0 == v1:
            raise ValueError(f"contract does not migrate name {v0!r}")
        if v0 in names_v0 or v1 in names_v1:
            raise ValueError("contract names must be one-to-one")
        names_v0.add(v0)
        names_v1.add(v1)
    if names_v0 & names_v1:
        raise ValueError("v0 and v1 contract namespaces must not overlap")
    return payload


def contract_digest(contract: Mapping[str, Any]) -> str:
    """Return a stable SHA-256 over the complete reviewed migration contract."""

    return sha256_text(canonical_json(dict(contract)))


def _mapping(contract: Mapping[str, Any]) -> dict[str, str]:
    raw = contract["migration"]["v0_to_v1"]
    return {str(v0): str(v1) for v0, v1 in raw.items()}


def canonical_tool_name(name: str, contract: Mapping[str, Any]) -> str:
    """Map an exposed v1 tool name back to the stable v0 policy identity."""

    reverse = {v1: v0 for v0, v1 in _mapping(contract).items()}
    return reverse.get(name, name)


def _runtime_entries(runtime: Any) -> dict[str, Any]:
    functions = getattr(runtime, "functions", None)
    if not isinstance(functions, Mapping):
        raise TypeError("AgentDojo runtime.functions must be a mapping")
    entries: dict[str, Any] = {}
    for raw_name, function in functions.items():
        name = _required_text(raw_name, "runtime function name")
        if name in entries:
            raise ValueError(f"duplicate runtime function name {name!r}")
        if _required_text(getattr(function, "name", None), "function.name") != name:
            raise ValueError(f"runtime key/name mismatch for {name!r}")
        entries[name] = function
    return entries


def _semantic_descriptor(function: Any) -> dict[str, Any]:
    """Serialize fields expected to stay invariant under a name-only migration."""

    parameters = getattr(function, "parameters", None)
    schema_fn = getattr(parameters, "model_json_schema", None)
    if not callable(schema_fn):
        raise TypeError("AgentDojo function parameters must expose model_json_schema")
    implementation = getattr(function, "run", None)
    module = getattr(implementation, "__module__", None)
    qualname = getattr(implementation, "__qualname__", None)
    if not isinstance(module, str) or not isinstance(qualname, str):
        raise TypeError("AgentDojo function run callable needs stable module and qualname")
    dependencies = getattr(function, "dependencies", None)
    if not isinstance(dependencies, Mapping):
        raise TypeError("AgentDojo function dependencies must be a mapping")
    return {
        "description": _required_text(getattr(function, "description", None), "function.description"),
        "full_docstring": _required_text(getattr(function, "full_docstring", None), "function.full_docstring"),
        "parameters": schema_fn(),
        "dependency_keys": sorted(str(key) for key in dependencies),
        "implementation": f"{module}.{qualname}",
    }


def _registry_witness(entries: Mapping[str, Any], contract: Mapping[str, Any]) -> dict[str, Any]:
    mapping = _mapping(contract)
    reverse = {v1: v0 for v0, v1 in mapping.items()}
    semantic_rows = []
    exposed_rows = []
    for name, function in entries.items():
        canonical_name = reverse.get(name, name)
        semantic = _semantic_descriptor(function)
        semantic_rows.append({"canonical_name": canonical_name, "descriptor": semantic})
        exposed_rows.append(
            {
                "exposed_name": name,
                "canonical_name": canonical_name,
                "semantic_sha256": sha256_text(canonical_json(semantic)),
            }
        )
    semantic_rows.sort(key=lambda row: row["canonical_name"])
    exposed_rows.sort(key=lambda row: row["exposed_name"])
    return {
        "semantic_registry_sha256": sha256_text(canonical_json(semantic_rows)),
        "exposed_registry_sha256": sha256_text(canonical_json(exposed_rows)),
        "tool_count": len(exposed_rows),
        "tools": exposed_rows,
    }


def apply_contract_to_runtime(runtime: Any, contract: Mapping[str, Any]) -> dict[str, Any]:
    """Apply the contract once, or reject incomplete/mixed registry states.

    The initial runtime must contain exactly the reviewed v0 Workspace tool
    names.  Subsequent calls may see a v1 subset after an upstream tool filter,
    but only after this module has recorded the first full-registry witness.
    """

    mapping = _mapping(contract)
    digest = contract_digest(contract)
    entries_before = _runtime_entries(runtime)
    names_before = set(entries_before)
    expected_v0 = set(mapping)
    expected_v1 = set(mapping.values())
    marker = getattr(runtime, _RUNTIME_MARKER, None)

    if not names_before:
        if marker is None:
            raise ValueError("refusing an empty initial runtime registry")
        return marker
    if names_before <= expected_v1:
        if not isinstance(marker, Mapping) or marker.get("contract_sha256") != digest:
            raise ValueError("refusing an un-witnessed or different pre-migrated v1 registry")
        return dict(marker)
    if names_before != expected_v0:
        unknown = sorted(names_before - expected_v0 - expected_v1)
        raise ValueError(
            "refusing incomplete or mixed v0/v1 runtime registry"
            + (f"; unexpected={unknown}" if unknown else "")
        )
    if marker is not None:
        raise ValueError("refusing a witnessed runtime that unexpectedly reverted to v0")

    before = _registry_witness(entries_before, contract)
    migrated: dict[str, Any] = {}
    for v0_name, function in entries_before.items():
        v1_name = mapping[v0_name]
        model_copy = getattr(function, "model_copy", None)
        if not callable(model_copy):
            raise TypeError("AgentDojo function must expose Pydantic model_copy")
        updated = model_copy(update={"name": v1_name})
        if _required_text(getattr(updated, "name", None), "migrated function.name") != v1_name:
            raise ValueError(f"function migration did not expose expected name {v1_name!r}")
        if getattr(updated, "run", None) is not getattr(function, "run", None):
            raise ValueError(f"function migration changed the implementation for {v0_name!r}")
        migrated[v1_name] = updated
    update_functions = getattr(runtime, "update_functions", None)
    if not callable(update_functions):
        raise TypeError("AgentDojo runtime must expose update_functions")
    update_functions(migrated)
    entries_after = _runtime_entries(runtime)
    if set(entries_after) != expected_v1:
        raise ValueError("runtime did not retain the complete reviewed v1 registry")
    after = _registry_witness(entries_after, contract)
    witness = {
        "schema_version": SCHEMA_VERSION,
        "contract_sha256": digest,
        "source": dict(contract["source"]),
        "migration_kind": contract["migration"]["kind"],
        "before": before,
        "after": after,
        "implementation_objects_preserved": True,
        "semantic_schema_preserved": before["semantic_registry_sha256"]
        == after["semantic_registry_sha256"],
    }
    if not witness["semantic_schema_preserved"]:
        raise ValueError("name-independent tool descriptors changed during migration")
    setattr(runtime, _RUNTIME_MARKER, witness)
    _AUDIT_LOG.append(witness)
    return witness


def apply_contract_from_environment(runtime: Any) -> dict[str, Any] | None:
    """Apply only an explicit manifest; an imported module is otherwise inert."""

    raw_path = os.environ.get(MANIFEST_ENV, "").strip()
    if not raw_path:
        return None
    return apply_contract_to_runtime(runtime, load_contract(Path(raw_path)))


def _write_audit() -> None:
    raw_path = os.environ.get(AUDIT_PATH_ENV, "").strip()
    if not raw_path or not _AUDIT_LOG:
        return
    path = Path(raw_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"schema_version": SCHEMA_VERSION, "events": _AUDIT_LOG}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


atexit.register(_write_audit)


def _wrap_query(cls: Any) -> bool:
    original = getattr(cls, "query", None)
    if not callable(original):
        return False
    if getattr(original, "_agentdojo_contract_migration", False):
        return True

    def wrapped(self: Any, query: Any, runtime: Any, *args: Any, **kwargs: Any) -> Any:
        apply_contract_from_environment(runtime)
        return original(self, query, runtime, *args, **kwargs)

    setattr(wrapped, "_agentdojo_contract_migration", True)
    setattr(wrapped, "__wrapped__", original)
    setattr(cls, "query", wrapped)
    return True


def _install_agentdojo_patch() -> bool:
    """Patch the OpenAI-compatible tool-schema producers when AgentDojo exists."""

    try:
        from agentdojo.agent_pipeline.llms import openai_llm
    except ImportError:
        return False
    return _wrap_query(openai_llm.OpenAILLM) and _wrap_query(openai_llm.OpenAILLMToolFilter)


PATCH_INSTALLED = _install_agentdojo_patch()


def integration_status() -> dict[str, Any]:
    return {
        "status": "installed" if PATCH_INSTALLED else "dependency_missing",
        "activation": f"set {MANIFEST_ENV} to the reviewed contract fixture",
        "audit": f"set {AUDIT_PATH_ENV} for a migration witness",
        "non_claim": "a successful migration is not LLM efficacy or security evidence",
    }
