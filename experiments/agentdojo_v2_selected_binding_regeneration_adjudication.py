"""Adjudicate a contradicted v2 selected-binding regeneration observation.

The prior regeneration-audit fixture is retained unchanged as historical
evidence. This script starts three separate Python child processes and asks
each to reconstruct all three frozen v2 source bindings from the declared
AgentDojo checkout. It is a narrow source-construction adjudication: no LLM,
provider, network service, tool executor, or Runpod resource is contacted.

It may establish only whether the frozen carrier, injection-map, and canonical
pre-state witnesses reproduce in this captured environment. It cannot explain
the earlier contradictory fixture, validate the benchmark, or authorize a
runtime experiment.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import locale
import os
import platform
import re
import subprocess
import sys
import tempfile
import time
from importlib.metadata import distributions
from pathlib import Path
from typing import Any

try:
    from experiments.agentdojo_pilot_oracle_qualification import STATE_CANONICALIZATION, _file_sha256, _verify_source
    from experiments.agentdojo_v2_selected_binding_regeneration_audit import (
        DEFAULT_OUTPUT as PRIOR_AUDIT,
        EFFECT_ORACLE_CONTRACT,
        PAIRED_MANIFEST,
        V2_SELECTION,
        _selected_rows_and_bindings,
        build_audit,
        load_audit as load_prior_audit,
    )
except ModuleNotFoundError:  # direct script execution support
    from agentdojo_pilot_oracle_qualification import STATE_CANONICALIZATION, _file_sha256, _verify_source
    from agentdojo_v2_selected_binding_regeneration_audit import (
        DEFAULT_OUTPUT as PRIOR_AUDIT,
        EFFECT_ORACLE_CONTRACT,
        PAIRED_MANIFEST,
        V2_SELECTION,
        _selected_rows_and_bindings,
        build_audit,
        load_audit as load_prior_audit,
    )


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "experiments" / "fixtures" / "agentdojo_v2_selected_binding_regeneration_adjudication_v1.json"
SCHEMA_VERSION = "agentdojo-v2-selected-binding-regeneration-adjudication/v1"
CHILD_SCHEMA_VERSION = "agentdojo-v2-selected-binding-regeneration-adjudication-child/v1"
RESULT_STATUS = "source_only_regeneration_adjudication_not_llm_evaluation"
CHILD_STATUS = "verified_source_construction"
ADJUDICATION_STATUS = "verified_fresh_process_regeneration"
HISTORICAL_OBSERVATION_STATUS = "contradicted_by_current_adjudication"
RUNTIME_PLAN_AUTHORIZATION = "not_authorized"
REPLICATE_COUNT = 3
WORKSPACE_STATE_DATA_FILES = {
    "src/agentdojo/data/suites/workspace/environment.yaml": "c0f93e6b6f9de005fec63588dc579313f227a87235c10259375a9f43aa13db3e",
    "src/agentdojo/data/suites/workspace/include/calendar.yaml": "0cc12f15f0d9b03e2ef025c3f1b6cb0b807db2e83bee76e2b0c90af78deee9ea",
    "src/agentdojo/data/suites/workspace/include/cloud_drive.yaml": "95b52f6f408016b42adfdff3d1005514fec3a629e92348c28e05f3dba113eaca",
    "src/agentdojo/data/suites/workspace/include/inbox.yaml": "13cf70a0a40252708b5f879987fa1fa24dbd92a3639c975bfe294ab7f4fd3c50",
    "src/agentdojo/data/suites/workspace/injection_vectors.yaml": "13223dbffc51cf7c843657b80939f89c82a46e8b2faf062522241dc5bf928722",
}
AGENTDOJO_IMPORT_ORIGIN = {
    "path": "src/agentdojo/__init__.py",
    "sha256": "7eb70257593da06f682a3ddda54a9d260d4fc514f645237f5ca74b08f8da61a6",
}
REQUIRED_DISTRIBUTIONS = ("pydantic", "pydantic-core", "pyyaml")
SEED_POLICY = (
    "No application or Python hash seed is set by this adjudication. The fresh-child PYTHONHASHSEED value is "
    "recorded as observed; the historical fixture's seed provenance is unknown."
)
TOPOLOGY_DESCRIPTION = (
    "Three separately started subprocesses use the parent interpreter. Each child reconstructs all three selected "
    "bindings from a clean pinned checkout with PYTHONPATH constrained to the repository and source tree; process "
    "IDs and raw states are intentionally not retained."
)
EXECUTION_ATTESTATION_SCOPE = (
    "Fresh-process topology and counters are self-attested by this artifact's code and output, not independently "
    "proven. PYTHONPATH is constrained; other inherited process state is only selectively recorded."
)


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _path(path: Path) -> str:
    return str(path.relative_to(ROOT)).replace("\\", "/")


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(character in "0123456789abcdef" for character in value)


def _workspace_data_witness(source: Path) -> dict[str, str]:
    actual = {relative: _file_sha256(source / relative) for relative in WORKSPACE_STATE_DATA_FILES}
    if actual != WORKSPACE_STATE_DATA_FILES:
        raise ValueError("workspace state data files differ from the declared source witness")
    return actual


def _agentdojo_import_witness(source: Path) -> dict[str, str]:
    import agentdojo

    module_file = getattr(agentdojo, "__file__", None)
    if not isinstance(module_file, str):
        raise ValueError("AgentDojo package has no verifiable import origin")
    try:
        relative = Path(module_file).resolve().relative_to(source.resolve()).as_posix()
    except ValueError as exc:
        raise ValueError("AgentDojo import escapes the pinned source checkout") from exc
    actual = {"path": relative, "sha256": _file_sha256(source / relative)}
    if actual != AGENTDOJO_IMPORT_ORIGIN:
        raise ValueError("AgentDojo import origin differs from the declared source witness")
    return actual


def _distribution_manifest() -> list[dict[str, str]]:
    values: list[dict[str, str]] = []
    for distribution in distributions():
        name = distribution.metadata.get("Name")
        if not isinstance(name, str) or not name:
            continue
        values.append({"name": re.sub(r"[-_.]+", "-", name).casefold(), "version": distribution.version})
    values.sort(key=lambda value: (value["name"], value["version"]))
    if len({value["name"] for value in values}) != len(values):
        raise ValueError("installed distribution manifest contains duplicate normalized names")
    return values


def _controlled_pythonpath(source: Path) -> list[str]:
    value = os.environ.get("PYTHONPATH")
    actual = value.split(os.pathsep) if value else []
    expected = [str(ROOT), str((source / "src").resolve())]
    if actual != expected:
        raise ValueError("child PYTHONPATH is not the controlled repository-plus-source path")
    return ["<repository-root>", "<agentdojo-source>/src"]


def _normalized_executable_location(executable: Path, source: Path) -> dict[str, str]:
    """Keep the executable provenance useful without committing a user-local path."""

    try:
        relative = executable.relative_to(source.resolve()).as_posix()
    except ValueError:
        return {"location_class": "external_python", "basename": executable.name}
    return {"location_class": "agentdojo_source_relative", "path": relative}


def _runtime_witness(source: Path) -> dict[str, Any]:
    manifest = _distribution_manifest()
    versions = {value["name"]: value["version"] for value in manifest}
    if any(name not in versions for name in REQUIRED_DISTRIBUTIONS):
        raise ValueError("runtime witness lacks a required serialization distribution")
    executable = Path(sys.executable).resolve()
    return {
        "python": {
            "implementation": platform.python_implementation(),
            "version": platform.python_version(),
            "executable_location": _normalized_executable_location(executable, source),
            "executable_sha256": _file_sha256(executable),
            "hash_randomization_enabled": bool(sys.flags.hash_randomization),
        },
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
        },
        "locale": locale.setlocale(locale.LC_ALL, None),
        "timezone_names": list(time.tzname),
        "environment": {
            "PYTHONHASHSEED": os.environ.get("PYTHONHASHSEED"),
            "PYTHONUTF8": os.environ.get("PYTHONUTF8"),
            "TZ": os.environ.get("TZ"),
            "LANG": os.environ.get("LANG"),
            "LC_ALL": os.environ.get("LC_ALL"),
            "PYTHONPATH": _controlled_pythonpath(source),
        },
        "seed_policy": SEED_POLICY,
        "installed_distributions": manifest,
        "installed_distributions_sha256": _sha256(manifest),
        "required_distribution_versions": {name: versions[name] for name in REQUIRED_DISTRIBUTIONS},
    }


def _shape(value: Any) -> Any:
    """Return a content-free JSON-schema-like shape for a state fingerprint."""

    if isinstance(value, dict):
        keys = sorted(str(key) for key in value)
        return {"kind": "object", "fields": {key: _shape(value[key]) for key in keys}}
    if isinstance(value, list):
        item_shapes = sorted({_canonical_bytes(_shape(item)).decode("utf-8") for item in value})
        return {"kind": "array", "length": len(value), "item_shapes": item_shapes}
    if value is None:
        return {"kind": "null"}
    if isinstance(value, bool):
        return {"kind": "boolean"}
    if isinstance(value, int):
        return {"kind": "integer"}
    if isinstance(value, float):
        return {"kind": "number"}
    if isinstance(value, str):
        return {"kind": "string"}
    raise TypeError(f"unsupported JSON state type: {type(value).__name__}")


def _state_shape_witnesses(source: Path, regenerated_cases: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Reconstruct states once more only to commit a non-sensitive shape witness."""

    from agentdojo.attacks.baseline_attacks import InjecAgentAttack
    from agentdojo.task_suite.load_suites import get_suite

    _, _, _, bindings = _selected_rows_and_bindings()
    suite = get_suite("v1.2.2", "workspace")
    attack = InjecAgentAttack(suite, None)
    witnesses: dict[str, dict[str, Any]] = {}
    for binding, regenerated in zip(bindings, regenerated_cases, strict=True):
        user_task = suite.get_user_task_by_id(binding["user_task_id"])
        injection_task = suite.get_injection_task_by_id(binding["injection_task_id"])
        injections = attack.attack(user_task, injection_task)
        state = user_task.init_environment(suite.load_and_inject_default_environment(injections)).model_copy(deep=True)
        state_json = state.model_dump(mode="json")
        observed_hash = _sha256(state_json)
        if observed_hash != regenerated["observed_pre_state_sha256"]:
            raise ValueError("shape-witness reconstruction differs from the regeneration audit within one child")
        witnesses[binding["case_id"]] = {
            "top_level_field_names": sorted(state_json),
            "state_schema_shape_sha256": _sha256(_shape(state_json)),
        }
    return witnesses


def build_child(source: Path, ordinal: int) -> dict[str, Any]:
    """Run exactly one source-construction replicate in a fresh interpreter."""

    if ordinal not in range(1, REPLICATE_COUNT + 1):
        raise ValueError("child ordinal is outside the fixed replicate range")
    source = _verify_source(source)
    regenerated = build_audit(source)
    scope = regenerated["selected_binding_regeneration"]
    if scope["gate_status"] != "verified_selected_binding_regeneration":
        raise ValueError("child regeneration did not reproduce every frozen selected binding")
    cases = scope["cases"]
    shapes = _state_shape_witnesses(source, cases)
    trials = []
    for case in cases:
        shape = shapes.get(case["case_id"])
        if not isinstance(shape, dict):
            raise ValueError("missing state-shape witness for regenerated selected case")
        trials.append(
            {
                "child_ordinal": ordinal,
                "case_id": case["case_id"],
                "stratum_id": case["stratum_id"],
                "user_task_id": case["user_task_id"],
                "injection_task_id": case["injection_task_id"],
                "carrier_id": case["carrier_id"],
                "canonicalization": STATE_CANONICALIZATION,
                "expected_carrier_ids": case["expected_carrier_ids"],
                "observed_carrier_ids": case["observed_carrier_ids"],
                "expected_injection_map_sha256": case["expected_injection_map_sha256"],
                "observed_injection_map_sha256": case["observed_injection_map_sha256"],
                "expected_selection_pre_state_sha256": case["expected_selection_pre_state_sha256"],
                "expected_effect_oracle_pre_state_sha256": case["expected_effect_oracle_pre_state_sha256"],
                "observed_pre_state_sha256": case["observed_pre_state_sha256"],
                "carrier_match": case["carrier_match"],
                "injection_map_match": case["injection_map_match"],
                "selection_pre_state_match": case["selection_pre_state_match"],
                "effect_oracle_pre_state_match": case["effect_oracle_pre_state_match"],
                "top_level_field_names": shape["top_level_field_names"],
                "state_schema_shape_sha256": shape["state_schema_shape_sha256"],
                "trial_status": CHILD_STATUS,
            }
        )
    source_provenance = dict(regenerated["source"])
    source_provenance.update(
        {
            "source_checkout_clean": True,
            "workspace_state_data_files": _workspace_data_witness(source),
            "agentdojo_import_origin": _agentdojo_import_witness(source),
        }
    )
    return {
        "schema_version": CHILD_SCHEMA_VERSION,
        "child_ordinal": ordinal,
        "child_status": CHILD_STATUS,
        "child_implementation": {"path": _path(Path(__file__)), "sha256": _file_sha256(Path(__file__))},
        "source_provenance": source_provenance,
        "runtime_witness": _runtime_witness(source),
        "trials": trials,
        "self_reported_execution_counters": {
            "llm_requests": 0,
            "provider_requests": 0,
            "network_requests": 0,
            "remote_jobs": 0,
            "local_attack_materializations": len(trials) * 2,
            "local_tool_dispatches": 0,
        },
    }


def _input_bindings() -> dict[str, dict[str, str]]:
    return {
        "prior_regeneration_audit": {
            "path": _path(PRIOR_AUDIT),
            "sha256": _file_sha256(PRIOR_AUDIT),
            "role": "historical_observation_retained_unamended",
        },
        "v2_selection": {"path": _path(V2_SELECTION), "sha256": _file_sha256(V2_SELECTION)},
        "effect_oracle_contract": {"path": _path(EFFECT_ORACLE_CONTRACT), "sha256": _file_sha256(EFFECT_ORACLE_CONTRACT)},
        "historical_paired_execution_manifest": {
            "path": _path(PAIRED_MANIFEST),
            "sha256": _file_sha256(PAIRED_MANIFEST),
            "role": "historical_only_not_amended",
        },
    }


def _validate_runtime_witness(runtime: Any) -> None:
    if not isinstance(runtime, dict):
        raise ValueError("child runtime witness is malformed")
    python = runtime.get("python")
    if not isinstance(python, dict) or not _is_sha256(python.get("executable_sha256")):
        raise ValueError("child Python executable witness is malformed")
    if not isinstance(python.get("implementation"), str) or not isinstance(python.get("version"), str):
        raise ValueError("child Python version witness is malformed")
    if not isinstance(python.get("hash_randomization_enabled"), bool):
        raise ValueError("child hash-randomization witness is malformed")
    location = python.get("executable_location")
    if not isinstance(location, dict):
        raise ValueError("child normalized Python executable location is malformed")
    if location.get("location_class") == "agentdojo_source_relative":
        relative = location.get("path")
        if not isinstance(relative, str) or not relative or Path(relative).is_absolute() or ".." in Path(relative).parts:
            raise ValueError("child source-relative Python executable location is malformed")
    elif location.get("location_class") == "external_python":
        basename = location.get("basename")
        if not isinstance(basename, str) or not basename or Path(basename).name != basename:
            raise ValueError("child external Python executable location is malformed")
    else:
        raise ValueError("child Python executable location class is unsupported")
    if not isinstance(runtime.get("platform"), dict) or not isinstance(runtime.get("locale"), str):
        raise ValueError("child platform or locale witness is malformed")
    if not isinstance(runtime.get("timezone_names"), list) or not all(isinstance(value, str) for value in runtime["timezone_names"]):
        raise ValueError("child timezone witness is malformed")
    if runtime.get("seed_policy") != SEED_POLICY:
        raise ValueError("child seed policy differs from the fixed adjudication boundary")
    environment = runtime.get("environment")
    if not isinstance(environment, dict) or environment.get("PYTHONPATH") != [
        "<repository-root>",
        "<agentdojo-source>/src",
    ]:
        raise ValueError("child environment witness is malformed or uncontrolled")
    if set(environment) != {"PYTHONHASHSEED", "PYTHONUTF8", "TZ", "LANG", "LC_ALL", "PYTHONPATH"}:
        raise ValueError("child environment witness has unexpected fields")
    distributions_witness = runtime.get("installed_distributions")
    if not isinstance(distributions_witness, list) or not distributions_witness:
        raise ValueError("child installed-distribution manifest is missing")
    if distributions_witness != sorted(distributions_witness, key=lambda value: (value.get("name", ""), value.get("version", ""))):
        raise ValueError("child installed-distribution manifest is not sorted")
    if not all(
        isinstance(value, dict) and set(value) == {"name", "version"} and isinstance(value["name"], str) and isinstance(value["version"], str)
        for value in distributions_witness
    ):
        raise ValueError("child installed-distribution manifest is malformed")
    if runtime.get("installed_distributions_sha256") != _sha256(distributions_witness):
        raise ValueError("child installed-distribution digest mismatch")
    versions = {value["name"]: value["version"] for value in distributions_witness}
    if len(versions) != len(distributions_witness) or any(name not in versions for name in REQUIRED_DISTRIBUTIONS):
        raise ValueError("child installed-distribution identity is incomplete")
    if runtime.get("required_distribution_versions") != {name: versions[name] for name in REQUIRED_DISTRIBUTIONS}:
        raise ValueError("child required-distribution witness mismatch")


def _expected_trial_fields() -> list[dict[str, Any]]:
    _, _, rows, bindings = _selected_rows_and_bindings()
    fields = []
    for row, binding in zip(rows, bindings, strict=True):
        fields.append(
            {
                "case_id": binding["case_id"],
                "stratum_id": binding["stratum_id"],
                "user_task_id": binding["user_task_id"],
                "injection_task_id": binding["injection_task_id"],
                "carrier_id": binding["carrier_id"],
                "expected_carrier_ids": [binding["carrier_id"]],
                "expected_injection_map_sha256": row["attack_binding"]["injection_map_sha256"],
                "expected_selection_pre_state_sha256": row["exact_pre_execution_state"]["sha256"],
                "expected_effect_oracle_pre_state_sha256": binding["expected_pre_state_sha256"],
            }
        )
    return fields


def validate_child(child: dict[str, Any], expected_ordinal: int | None = None) -> None:
    """Reject incomplete, substituted, or non-reproducing child evidence."""

    if not isinstance(child, dict) or child.get("schema_version") != CHILD_SCHEMA_VERSION:
        raise ValueError("unsupported child adjudication schema")
    ordinal = child.get("child_ordinal")
    if ordinal not in range(1, REPLICATE_COUNT + 1) or (expected_ordinal is not None and ordinal != expected_ordinal):
        raise ValueError("child ordinal is malformed or out of order")
    if child.get("child_status") != CHILD_STATUS:
        raise ValueError("failed or unresolved child cannot be accepted as source evidence")
    if child.get("child_implementation") != {"path": _path(Path(__file__)), "sha256": _file_sha256(Path(__file__))}:
        raise ValueError("child implementation binding mismatch")
    selection, effect_contract, _, _ = _selected_rows_and_bindings()
    source = child.get("source_provenance")
    if not isinstance(source, dict):
        raise ValueError("child source provenance is missing")
    if source.get("verification_witness") != effect_contract["source"]["verification_witness"]:
        raise ValueError("child source verification witness mismatch")
    if source.get("checked_effect_oracle_source_files") != effect_contract["source"]["verification_witness"]["source_files"]:
        raise ValueError("child effect-oracle source witness mismatch")
    if source.get("runtime_identity") != selection["source"]["runtime_identity"]:
        raise ValueError("child source runtime identity mismatch")
    if source.get("repository_remote") != selection["source"]["repository"]:
        raise ValueError("child source remote mismatch")
    if source.get("source_checkout_clean") is not True:
        raise ValueError("child source checkout was not clean")
    if source.get("workspace_state_data_files") != WORKSPACE_STATE_DATA_FILES:
        raise ValueError("child workspace-data witness mismatch")
    if source.get("agentdojo_import_origin") != AGENTDOJO_IMPORT_ORIGIN:
        raise ValueError("child AgentDojo import origin mismatch")
    _validate_runtime_witness(child.get("runtime_witness"))
    trials = child.get("trials")
    expected_trials = _expected_trial_fields()
    if not isinstance(trials, list) or len(trials) != len(expected_trials):
        raise ValueError("child selected-case coverage mismatch")
    for trial, expected in zip(trials, expected_trials, strict=True):
        if not isinstance(trial, dict) or trial.get("child_ordinal") != ordinal:
            raise ValueError("child trial ordinal mismatch")
        if any(trial.get(field) != value for field, value in expected.items()):
            raise ValueError("child immutable selected binding mismatch")
        if trial.get("canonicalization") != STATE_CANONICALIZATION or trial.get("trial_status") != CHILD_STATUS:
            raise ValueError("child trial has an unsupported canonicalization or status")
        if trial.get("observed_carrier_ids") != trial["expected_carrier_ids"]:
            raise ValueError("child trial carrier reproduction mismatch")
        for field in (
            "observed_injection_map_sha256",
            "observed_pre_state_sha256",
            "expected_injection_map_sha256",
            "expected_selection_pre_state_sha256",
            "expected_effect_oracle_pre_state_sha256",
            "state_schema_shape_sha256",
        ):
            if not _is_sha256(trial.get(field)):
                raise ValueError("child trial digest is malformed")
        if trial["observed_injection_map_sha256"] != trial["expected_injection_map_sha256"]:
            raise ValueError("child injection-map reproduction mismatch")
        if (
            trial["observed_pre_state_sha256"] != trial["expected_selection_pre_state_sha256"]
            or trial["observed_pre_state_sha256"] != trial["expected_effect_oracle_pre_state_sha256"]
        ):
            raise ValueError("child pre-state reproduction mismatch")
        if not all(
            trial.get(field) is True
            for field in ("carrier_match", "injection_map_match", "selection_pre_state_match", "effect_oracle_pre_state_match")
        ):
            raise ValueError("child match flags cannot promote a failed trial")
        top_level = trial.get("top_level_field_names")
        if not isinstance(top_level, list) or not top_level or top_level != sorted(top_level) or not all(
            isinstance(value, str) for value in top_level
        ):
            raise ValueError("child state-shape top-level witness is malformed")
    expected_counters = {
        "llm_requests": 0,
        "provider_requests": 0,
        "network_requests": 0,
        "remote_jobs": 0,
        "local_attack_materializations": len(expected_trials) * 2,
        "local_tool_dispatches": 0,
    }
    if child.get("self_reported_execution_counters") != expected_counters:
        raise ValueError("child execution counters mismatch")


def _controlled_child_environment(source: Path) -> dict[str, str]:
    environment = dict(os.environ)
    environment["PYTHONPATH"] = os.pathsep.join([str(ROOT), str((source / "src").resolve())])
    return environment


def _run_child(source: Path, ordinal: int, output: Path) -> dict[str, Any]:
    completed = subprocess.run(
        [
            sys.executable,
            str(Path(__file__).resolve()),
            "--child",
            "--child-ordinal",
            str(ordinal),
            "--source",
            str(source),
            "--output",
            str(output),
        ],
        cwd=ROOT,
        env=_controlled_child_environment(source),
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"fresh child {ordinal} failed with exit status {completed.returncode}")
    try:
        child = json.loads(output.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"fresh child {ordinal} produced no valid evidence file") from exc
    if not isinstance(child, dict):
        raise ValueError(f"fresh child {ordinal} evidence is not a JSON object")
    validate_child(child, ordinal)
    return child


def _case_summaries(children: list[dict[str, Any]]) -> list[dict[str, Any]]:
    summaries = []
    for expected in _expected_trial_fields():
        replicates = [
            trial
            for child in children
            for trial in child["trials"]
            if trial["case_id"] == expected["case_id"]
        ]
        observed_hashes = sorted({trial["observed_pre_state_sha256"] for trial in replicates})
        shape_hashes = sorted({trial["state_schema_shape_sha256"] for trial in replicates})
        if len(replicates) != REPLICATE_COUNT or len(observed_hashes) != 1 or len(shape_hashes) != 1:
            raise ValueError("fresh-process replicate evidence is incomplete or unstable")
        if any(
            trial["observed_pre_state_sha256"] != expected["expected_selection_pre_state_sha256"]
            or trial["observed_pre_state_sha256"] != expected["expected_effect_oracle_pre_state_sha256"]
            or trial["observed_injection_map_sha256"] != expected["expected_injection_map_sha256"]
            or trial["observed_carrier_ids"] != expected["expected_carrier_ids"]
            for trial in replicates
        ):
            raise ValueError("fresh-process replicate does not reproduce every frozen binding witness")
        summaries.append(
            {
                "case_id": expected["case_id"],
                "replicate_count": REPLICATE_COUNT,
                "unique_observed_pre_state_hash_count": len(observed_hashes),
                "observed_pre_state_sha256s": observed_hashes,
                "all_replicates_equal": True,
                "unique_state_schema_shape_hash_count": len(shape_hashes),
                "state_schema_shape_sha256s": shape_hashes,
                "all_replicates_match_selection_witness": True,
                "all_replicates_match_effect_oracle_witness": True,
                "carrier_and_injection_map_match_every_trial": True,
            }
        )
    return summaries


def build_adjudication(source: Path) -> dict[str, Any]:
    """Collect three independent fresh-process source-construction witnesses."""

    source = _verify_source(source)
    prior = load_prior_audit(PRIOR_AUDIT)
    with tempfile.TemporaryDirectory(prefix="agentdojo-v2-adjudication-") as temporary:
        temporary_path = Path(temporary)
        children = [
            _run_child(source, ordinal, temporary_path / f"child-{ordinal}.json")
            for ordinal in range(1, REPLICATE_COUNT + 1)
        ]
    for ordinal, child in enumerate(children, start=1):
        validate_child(child, ordinal)
    if len({_canonical_bytes(child["runtime_witness"]) for child in children}) != 1:
        raise ValueError("fresh children do not share one fully captured runtime witness")
    if len({_canonical_bytes(child["source_provenance"]) for child in children}) != 1:
        raise ValueError("fresh children do not share one source/import provenance witness")
    summaries = _case_summaries(children)
    return {
        "schema_version": SCHEMA_VERSION,
        "recorded_on": "2026-10-05",
        "result_status": RESULT_STATUS,
        "purpose": (
            "Adjudicate whether the frozen v2 selected binding witnesses reproduce in three independently started "
            "source-construction processes after a prior self-consistent regeneration-audit fixture recorded a "
            "contradictory mismatch."
        ),
        "inputs": _input_bindings(),
        "adjudication_implementation": {"path": _path(Path(__file__)), "sha256": _file_sha256(Path(__file__))},
        "source_provenance": children[0]["source_provenance"],
        "runtime_witness": children[0]["runtime_witness"],
        "fresh_process_topology": {
            "child_process_count": REPLICATE_COUNT,
            "selected_cases_per_child": len(children[0]["trials"]),
            "total_case_trials": REPLICATE_COUNT * len(children[0]["trials"]),
            "description": TOPOLOGY_DESCRIPTION,
        },
        "execution_attestation_scope": EXECUTION_ATTESTATION_SCOPE,
        "fresh_process_children": children,
        "current_source_reproduction": {
            "status": ADJUDICATION_STATUS,
            "case_count": len(summaries),
            "case_trial_count": REPLICATE_COUNT * len(summaries),
            "case_summaries": summaries,
        },
        "historical_audit_observation": {
            "prior_gate_status": prior["selected_binding_regeneration"]["gate_status"],
            "prior_matching_case_count": prior["selected_binding_regeneration"]["matching_case_count"],
            "prior_mismatching_case_count": prior["selected_binding_regeneration"]["mismatching_case_count"],
            "status": HISTORICAL_OBSERVATION_STATUS,
            "interpretation": (
                "The prior fixture is retained unchanged but its reported mismatch is contradicted by this "
                "captured-environment adjudication. The cause of the prior observation remains unknown."
            ),
        },
        "runtime_plan_authorization": RUNTIME_PLAN_AUTHORIZATION,
        "operational_rule": (
            "This adjudication clears only the specific prior source-regeneration mismatch assertion. It does not "
            "authorize running or scoring the historical v2 plan: a future versioned execution design must still pin "
            "a genuine benign initial state and utility oracle, a manifest-bound driver, reset and trace provenance, "
            "fair baselines, and all other open scientific gates."
        ),
        "self_reported_execution_counters": {
            "llm_requests": 0,
            "provider_requests": 0,
            "network_requests": 0,
            "remote_jobs": 0,
            "fresh_child_processes": REPLICATE_COUNT,
            "local_attack_materializations": sum(
                child["self_reported_execution_counters"]["local_attack_materializations"] for child in children
            ),
            "local_tool_dispatches": 0,
        },
        "non_claims": [
            "This is not an LLM, agent, defense, utility, latency, cost, benchmark, or statistical-efficacy result.",
            "It does not identify the cause of the prior mismatch, reconstruct that prior execution environment, or prove AgentDojo is deterministic generally.",
            "It does not validate the historical v2 plan, amend any historical fixture, or authorize Runpod/API/model execution.",
            "The fresh-process topology and self-reported counters are not independent evidence that no process made a model, provider, network, or remote-job call.",
        ],
    }


def validate_adjudication(adjudication: dict[str, Any]) -> dict[str, Any]:
    """Validate the immutable correction and fail closed on any absent trial."""

    if not isinstance(adjudication, dict) or adjudication.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("unsupported regeneration-adjudication schema")
    if adjudication.get("result_status") != RESULT_STATUS:
        raise ValueError("adjudication must not claim an LLM evaluation")
    if adjudication.get("inputs") != _input_bindings():
        raise ValueError("adjudication input binding mismatch")
    if adjudication.get("adjudication_implementation") != {
        "path": _path(Path(__file__)),
        "sha256": _file_sha256(Path(__file__)),
    }:
        raise ValueError("adjudication implementation binding mismatch")
    children = adjudication.get("fresh_process_children")
    if not isinstance(children, list) or len(children) != REPLICATE_COUNT:
        raise ValueError("adjudication does not retain every fresh child")
    for ordinal, child in enumerate(children, start=1):
        validate_child(child, ordinal)
    if adjudication.get("source_provenance") != children[0]["source_provenance"]:
        raise ValueError("adjudication source provenance does not bind its child evidence")
    if adjudication.get("runtime_witness") != children[0]["runtime_witness"]:
        raise ValueError("adjudication runtime witness does not bind its child evidence")
    if len({_canonical_bytes(child["source_provenance"]) for child in children}) != 1:
        raise ValueError("adjudication child source provenance diverges")
    if len({_canonical_bytes(child["runtime_witness"]) for child in children}) != 1:
        raise ValueError("adjudication child runtime witness diverges")
    expected_topology = {
        "child_process_count": REPLICATE_COUNT,
        "selected_cases_per_child": len(_expected_trial_fields()),
        "total_case_trials": REPLICATE_COUNT * len(_expected_trial_fields()),
        "description": TOPOLOGY_DESCRIPTION,
    }
    if adjudication.get("fresh_process_topology") != expected_topology:
        raise ValueError("adjudication fresh-process topology mismatch")
    if adjudication.get("execution_attestation_scope") != EXECUTION_ATTESTATION_SCOPE:
        raise ValueError("adjudication execution-attestation scope mismatch")
    summaries = _case_summaries(children)
    expected_reproduction = {
        "status": ADJUDICATION_STATUS,
        "case_count": len(summaries),
        "case_trial_count": REPLICATE_COUNT * len(summaries),
        "case_summaries": summaries,
    }
    if adjudication.get("current_source_reproduction") != expected_reproduction:
        raise ValueError("adjudication aggregate reproduction summary mismatch")
    prior = load_prior_audit(PRIOR_AUDIT)
    expected_historical = {
        "prior_gate_status": prior["selected_binding_regeneration"]["gate_status"],
        "prior_matching_case_count": prior["selected_binding_regeneration"]["matching_case_count"],
        "prior_mismatching_case_count": prior["selected_binding_regeneration"]["mismatching_case_count"],
        "status": HISTORICAL_OBSERVATION_STATUS,
        "interpretation": (
            "The prior fixture is retained unchanged but its reported mismatch is contradicted by this "
            "captured-environment adjudication. The cause of the prior observation remains unknown."
        ),
    }
    if adjudication.get("historical_audit_observation") != expected_historical:
        raise ValueError("adjudication historical-observation boundary mismatch")
    if adjudication.get("runtime_plan_authorization") != RUNTIME_PLAN_AUTHORIZATION:
        raise ValueError("adjudication must never authorize a runtime plan")
    expected_rule = (
        "This adjudication clears only the specific prior source-regeneration mismatch assertion. It does not "
        "authorize running or scoring the historical v2 plan: a future versioned execution design must still pin "
        "a genuine benign initial state and utility oracle, a manifest-bound driver, reset and trace provenance, "
        "fair baselines, and all other open scientific gates."
    )
    if adjudication.get("operational_rule") != expected_rule:
        raise ValueError("adjudication operational rule mismatch")
    expected_counters = {
        "llm_requests": 0,
        "provider_requests": 0,
        "network_requests": 0,
        "remote_jobs": 0,
        "fresh_child_processes": REPLICATE_COUNT,
        "local_attack_materializations": REPLICATE_COUNT * len(_expected_trial_fields()) * 2,
        "local_tool_dispatches": 0,
    }
    if adjudication.get("self_reported_execution_counters") != expected_counters:
        raise ValueError("adjudication execution counters mismatch")
    if adjudication.get("non_claims") != [
        "This is not an LLM, agent, defense, utility, latency, cost, benchmark, or statistical-efficacy result.",
        "It does not identify the cause of the prior mismatch, reconstruct that prior execution environment, or prove AgentDojo is deterministic generally.",
        "It does not validate the historical v2 plan, amend any historical fixture, or authorize Runpod/API/model execution.",
        "The fresh-process topology and self-reported counters are not independent evidence that no process made a model, provider, network, or remote-job call.",
    ]:
        raise ValueError("adjudication non-claim boundary mismatch")
    return {
        "adjudication_status": ADJUDICATION_STATUS,
        "case_count": len(summaries),
        "case_trial_count": REPLICATE_COUNT * len(summaries),
        "historical_audit_observation_status": HISTORICAL_OBSERVATION_STATUS,
        "runtime_plan_authorization": RUNTIME_PLAN_AUTHORIZATION,
        "result_status": RESULT_STATUS,
    }


def load_adjudication(path: Path = DEFAULT_OUTPUT) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("adjudication must be a JSON object")
    validate_adjudication(value)
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, help="clean pinned AgentDojo checkout; required to build or source-verify")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--verify", action="store_true", help="validate a committed adjudication and re-execute all fresh children")
    parser.add_argument("--child", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--child-ordinal", type=int, help=argparse.SUPPRESS)
    args = parser.parse_args()
    output = args.output.resolve()
    if args.child:
        if args.verify or args.source is None or args.child_ordinal is None:
            parser.error("--child requires --source and --child-ordinal and cannot combine with --verify")
        child = build_child(args.source, args.child_ordinal)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(child, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        validate_child(child, args.child_ordinal)
        print(json.dumps({"child_ordinal": args.child_ordinal, "child_status": CHILD_STATUS}, ensure_ascii=True))
        return 0
    if args.verify:
        committed = load_adjudication(output)
        report = validate_adjudication(committed)
        if args.source is not None:
            regenerated = build_adjudication(args.source)
            if _canonical_bytes(regenerated) != _canonical_bytes(committed):
                raise ValueError("fresh-process adjudication differs from the pinned-source re-execution")
            report["source_reexecution_match"] = True
        print(json.dumps(report, ensure_ascii=True, indent=2))
        return 0
    if args.source is None:
        parser.error("--source is required to build a regeneration adjudication")
    adjudication = build_adjudication(args.source)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(adjudication, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(validate_adjudication(adjudication), ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
