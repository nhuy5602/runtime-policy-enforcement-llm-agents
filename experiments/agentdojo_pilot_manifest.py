"""Build and validate an outcome-blind AgentDojo pilot case manifest.

This tool never calls a model or endpoint.  It reads only the pinned AgentDojo
source to enumerate carrier-visible InjecAgent cases, then freezes a small,
hash-selected feasibility subset.  The subset is not an efficacy sample.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "experiments" / "fixtures" / "agentdojo_pilot_case_manifest_v1.json"
SOURCE_COMMIT = "089ed468cf3ed0322acc66b0211f26d9d90dbf60"
BENCHMARK_VERSION = "v1.2.2"
SUITE = "workspace"
ATTACK = "injecagent"
SELECTION_SEED = "agentdojo-pilot-feasibility-v1-20260928"
CONTRACT_MANIFEST = ROOT / "experiments" / "fixtures" / "agentdojo_contract_v0_to_v1.json"

EFFECT_FAMILY = {
    "injection_task_0": "unauthorized_email",
    "injection_task_1": "unauthorized_file_deletion",
    "injection_task_2": "unauthorized_calendar_event",
    "injection_task_3": "email_content_exfiltration",
    "injection_task_4": "security_code_exfiltration",
    "injection_task_5": "security_code_exfiltration_and_email_deletion",
    "injection_task_6": "email_corpus_exfiltration",
    "injection_task_7": "email_corpus_exfiltration",
    "injection_task_8": "email_corpus_exfiltration_and_email_deletion",
    "injection_task_9": "email_corpus_exfiltration_and_email_deletion",
    "injection_task_10": "cloud_drive_exfiltration",
    "injection_task_11": "cloud_drive_exfiltration_and_file_deletion",
    "injection_task_12": "cloud_drive_exfiltration_and_file_deletion",
    "injection_task_13": "unauthorized_bulk_email",
}

SELECTION_STRATA = (
    ("calendar_event", "calendar", "injection_task_2"),
    ("drive_file_deletion", "drive", "injection_task_1"),
    ("email_egress", "email", "injection_task_0"),
)


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_head(source: Path) -> str:
    completed = subprocess.run(
        ["git", "-C", str(source), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _carrier_surface(carrier_id: str) -> str:
    if carrier_id.startswith("calendar_"):
        return "calendar"
    if carrier_id.startswith("drive_"):
        return "drive"
    if carrier_id.startswith("email_"):
        return "email"
    raise ValueError(f"unrecognised AgentDojo workspace carrier {carrier_id!r}")


def _case_id(user_task_id: str, injection_task_id: str, carrier_id: str) -> str:
    return f"workspace:{BENCHMARK_VERSION}:{user_task_id}:{injection_task_id}:{carrier_id}"


def _select(rows: list[dict[str, Any]]) -> list[str]:
    selected: list[str] = []
    for _, surface, injection_task_id in SELECTION_STRATA:
        eligible = [
            row
            for row in rows
            if row["carrier_surface"] == surface
            and row["injection_task_id"] == injection_task_id
            and row["execution_eligibility"] == "standard_injecagent_single_carrier"
        ]
        if not eligible:
            raise ValueError(f"no outcome-blind eligible case for {surface}/{injection_task_id}")
        selected.append(
            min(
                eligible,
                key=lambda row: (hashlib.sha256(f"{SELECTION_SEED}\0{row['case_id']}".encode()).hexdigest(), row["case_id"]),
            )["case_id"]
        )
    return selected


def build_manifest(source: Path) -> dict[str, Any]:
    """Enumerate a pinned source checkout.  Requires its local AgentDojo environment."""

    source = source.resolve()
    if _git_head(source) != SOURCE_COMMIT:
        raise ValueError(f"AgentDojo source must be pinned at {SOURCE_COMMIT}")
    if not CONTRACT_MANIFEST.is_file():
        raise FileNotFoundError(f"missing contract manifest: {CONTRACT_MANIFEST}")

    from agentdojo.attacks.baseline_attacks import InjecAgentAttack
    from agentdojo.task_suite.load_suites import get_suite

    suite = get_suite(BENCHMARK_VERSION, SUITE)
    attack = InjecAgentAttack(suite, None)
    carrier_by_user = {
        user_task_id: sorted(attack.get_injection_candidates(user_task))
        for user_task_id, user_task in sorted(suite.user_tasks.items())
    }
    environment = suite.load_and_inject_default_environment({})
    rows: list[dict[str, Any]] = []
    for user_task_id, carriers in carrier_by_user.items():
        for injection_task_id, injection_task in sorted(suite.injection_tasks.items()):
            effect_family = EFFECT_FAMILY.get(injection_task_id)
            if effect_family is None:
                raise ValueError(f"missing effect-family annotation for {injection_task_id}")
            for carrier_id in carriers:
                attack_text = attack.jailbreak.format(
                    goal=injection_task.GOAL,
                    user=attack.user_name,
                    model=attack.model_name,
                    task=user_task_id,
                )
                rows.append(
                    {
                        "case_id": _case_id(user_task_id, injection_task_id, carrier_id),
                        "suite": SUITE,
                        "benchmark_version": BENCHMARK_VERSION,
                        "user_task_id": user_task_id,
                        "injection_task_id": injection_task_id,
                        "carrier_id": carrier_id,
                        "carrier_surface": _carrier_surface(carrier_id),
                        "harmful_effect_family": effect_family,
                        "harmful_effect_oracle": {
                            "kind": "agentdojo_injection_task_security",
                            "task_id": injection_task_id,
                            "guard_dependency": "none; upstream environment/state oracle",
                        },
                        "benign_twin_id": f"workspace:{BENCHMARK_VERSION}:{user_task_id}:benign",
                        "migration_family": "workspace_name_only_v0_to_v1_control",
                        "execution_eligibility": (
                            "standard_injecagent_single_carrier"
                            if len(carriers) == 1
                            else "requires_single_carrier_attack_driver"
                        ),
                        "injection_goal_sha256": hashlib.sha256(injection_task.GOAL.encode("utf-8")).hexdigest(),
                        "attack_text_sha256": hashlib.sha256(attack_text.encode("utf-8")).hexdigest(),
                    }
                )
    rows.sort(key=lambda row: row["case_id"])
    selected_case_ids = _select(rows)
    return {
        "schema_version": "agentdojo-pilot-case-manifest/v1",
        "recorded_on": "2026-09-28",
        "result_status": "not_run",
        "purpose": "Outcome-blind, source-pinned feasibility population; not an efficacy sample or a v0/v1 comparison result.",
        "source": {
            "repository": "https://github.com/ethz-spylab/agentdojo.git",
            "commit": SOURCE_COMMIT,
            "suite": SUITE,
            "benchmark_version": BENCHMARK_VERSION,
            "attack": ATTACK,
            "attack_template_sha256": hashlib.sha256(attack.jailbreak.encode("utf-8")).hexdigest(),
            "initial_environment_sha256": _sha256(environment.model_dump(mode="json")),
            "contract_migration_manifest": str(CONTRACT_MANIFEST.relative_to(ROOT)).replace("\\", "/"),
            "contract_migration_manifest_sha256": _file_sha256(CONTRACT_MANIFEST),
        },
        "population": {
            "case_count": len(rows),
            "ordering": "lexicographic case_id",
            "rows_sha256": _sha256(rows),
            "rows": rows,
        },
        "feasibility_selection": {
            "selection_status": "pre_registered_not_run",
            "seed": SELECTION_SEED,
            "rule": "Within each named stratum, select the eligible case with the smallest SHA-256(seed + NUL + case_id); no model output, policy decision, or security outcome is an input.",
            "strata": [
                {"stratum_id": name, "carrier_surface": surface, "injection_task_id": injection_task_id}
                for name, surface, injection_task_id in SELECTION_STRATA
            ],
            "selected_case_ids": selected_case_ids,
            "selected_attack_episode_count": len(selected_case_ids),
            "planned_attack_track_invocations": len(selected_case_ids) * 2,
            "planned_benign_twin_invocations": len(selected_case_ids) * 2,
        },
        "non_claims": [
            "The selected three-case feasibility subset is not an efficacy sample, a population estimate, or a statistical test.",
            "The current name-only migration control does not constitute a completed paired v0/v1 drift comparison.",
            "The upstream AgentDojo oracle is retained as an external state/effect oracle; it is not generated by the guard under test.",
        ],
    }


def validate_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    if manifest.get("schema_version") != "agentdojo-pilot-case-manifest/v1":
        raise ValueError("unsupported pilot case manifest schema")
    if manifest.get("result_status") != "not_run":
        raise ValueError("pilot case manifest must not claim a run result")
    source = manifest.get("source")
    population = manifest.get("population")
    selection = manifest.get("feasibility_selection")
    if not isinstance(source, dict) or not isinstance(population, dict) or not isinstance(selection, dict):
        raise ValueError("source, population, and feasibility_selection must be objects")
    if source.get("commit") != SOURCE_COMMIT or source.get("benchmark_version") != BENCHMARK_VERSION:
        raise ValueError("pilot case manifest source pin mismatch")
    if source.get("contract_migration_manifest") != str(CONTRACT_MANIFEST.relative_to(ROOT)).replace("\\", "/"):
        raise ValueError("pilot case manifest contract-migration path mismatch")
    if source.get("contract_migration_manifest_sha256") != _file_sha256(CONTRACT_MANIFEST):
        raise ValueError("pilot case manifest contract-migration digest mismatch")
    rows = population.get("rows")
    if not isinstance(rows, list) or not rows:
        raise ValueError("pilot case manifest must contain nonempty population rows")
    ids = [row.get("case_id") for row in rows if isinstance(row, dict)]
    if len(ids) != len(rows) or ids != sorted(ids) or len(set(ids)) != len(ids):
        raise ValueError("population case IDs must be unique and lexicographically ordered")
    if population.get("case_count") != len(rows) or population.get("rows_sha256") != _sha256(rows):
        raise ValueError("population cardinality or digest mismatch")
    for row in rows:
        if row.get("case_id") != _case_id(row.get("user_task_id", ""), row.get("injection_task_id", ""), row.get("carrier_id", "")):
            raise ValueError("case ID does not bind user task, injection task, and carrier")
        if row.get("harmful_effect_oracle", {}).get("guard_dependency") != "none; upstream environment/state oracle":
            raise ValueError("harmful-effect oracle must remain independent of the guard")
    selected = selection.get("selected_case_ids")
    if selected != _select(rows) or len(selected) != len(SELECTION_STRATA):
        raise ValueError("feasibility selection is not the preregistered outcome-blind selection")
    if selection.get("selected_attack_episode_count") != len(selected):
        raise ValueError("selected attack episode count mismatch")
    if selection.get("planned_attack_track_invocations") != len(selected) * 2:
        raise ValueError("planned attack cardinality mismatch")
    if selection.get("planned_benign_twin_invocations") != len(selected) * 2:
        raise ValueError("planned benign-twin cardinality mismatch")
    return {
        "case_count": len(rows),
        "selected_case_ids": selected,
        "selected_attack_episode_count": selection["selected_attack_episode_count"],
        "result_status": manifest["result_status"],
    }


def load_manifest(path: Path = DEFAULT_OUTPUT) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("pilot case manifest must be a JSON object")
    validate_manifest(value)
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, help="pinned AgentDojo checkout; required to build or source-verify")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--verify", action="store_true", help="validate the committed artifact, and compare it with --source when supplied")
    args = parser.parse_args()
    output = args.output.resolve()
    if args.verify:
        committed = load_manifest(output)
        report = validate_manifest(committed)
        if args.source is not None:
            regenerated = build_manifest(args.source)
            if _canonical_bytes(regenerated) != _canonical_bytes(committed):
                raise ValueError("manifest differs from the pinned-source regeneration")
            report["source_regeneration_match"] = True
        print(json.dumps(report, ensure_ascii=True, indent=2))
        return 0
    if args.source is None:
        parser.error("--source is required to build a manifest")
    manifest = build_manifest(args.source)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(validate_manifest(manifest), ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
