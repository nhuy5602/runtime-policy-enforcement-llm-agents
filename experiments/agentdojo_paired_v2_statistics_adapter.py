"""Manifest-bound adapter from accepted v2 pairs to paired statistics rows.

The result-bundle validator owns provenance and endpoint recomputation.  This
module is deliberately a separate, small boundary: it consumes the validator
report, keeps the fixed denominator and ``not_scored`` reasons visible, and
only emits complete pairs for ``paired_statistics.compare_row_sets``.

It never infers a missing endpoint, treats an unscored row as zero/one, or
combines attack and default-control arms.  Scored records must carry an
explicit ``source_cluster_id`` supplied by the manifest-bound driver; the
adapter does not guess independence from ``case_id``.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

try:
    from experiments.agentdojo_paired_v2_execution_manifest import (
        DEFAULT_CONTROL_ARM,
        DEFAULT_OUTPUT as DEFAULT_MANIFEST,
        load_manifest,
    )
    from experiments.agentdojo_paired_v2_result_bundle import (
        _load_json,
        validate_and_summarize_bundle,
    )
except ModuleNotFoundError:  # direct ``python experiments/*.py`` support
    from agentdojo_paired_v2_execution_manifest import (
        DEFAULT_CONTROL_ARM,
        DEFAULT_OUTPUT as DEFAULT_MANIFEST,
        load_manifest,
    )
    from agentdojo_paired_v2_result_bundle import _load_json, validate_and_summarize_bundle


ROOT = Path(__file__).resolve().parents[1]
ADAPTER_SCHEMA_VERSION = "agentdojo-paired-v2-statistics-input/v1"


def _plans_by_episode(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(row["episode_id"]): row for row in manifest["episodes"]}


def _pair_rows(
    report: dict[str, Any],
    manifest: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    plans = _plans_by_episode(manifest)
    episodes = {
        str(row["episode_id"]): row
        for row in report.get("episodes", [])
        if isinstance(row, dict) and row.get("episode_id") in plans
    }
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    pair_reports: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for pair in report.get("summary", {}).get("pairs", []):
        if isinstance(pair, dict) and isinstance(pair.get("pair_id"), str):
            pair_reports[pair["pair_id"]].append(pair)
    for plan in manifest["episodes"]:
        grouped[str(plan["pair_id"])].append(plan)

    complete: list[dict[str, Any]] = []
    incomplete: list[dict[str, Any]] = []
    for pair_id, siblings in sorted(grouped.items()):
        if len(siblings) != 2:
            incomplete.append(
                {
                    "analysis_pair_id": pair_id,
                    "arm": siblings[0].get("arm") if siblings else None,
                    "pair_status": "not_scored",
                    "not_scored_reason": "manifest_pair_does_not_have_two_siblings",
                }
            )
            continue
        by_version = {str(plan["contract"]["version"]): plan for plan in siblings}
        if set(by_version) != {"v0", "v1"}:
            incomplete.append(
                {
                    "analysis_pair_id": pair_id,
                    "arm": siblings[0].get("arm"),
                    "pair_status": "not_scored",
                    "not_scored_reason": "manifest_pair_missing_v0_or_v1",
                }
            )
            continue
        v0_plan, v1_plan = by_version["v0"], by_version["v1"]
        accepted = pair_reports.get(pair_id, [])
        pair_report = accepted[0] if len(accepted) == 1 else {}
        if report.get("bundle_contract_error") or pair_report.get("pair_status") != "scored":
            incomplete.append({
                "analysis_pair_id": pair_id,
                "arm": v0_plan.get("arm"),
                "pair_status": "not_scored",
                "not_scored_reason": "validator_pair_not_accepted",
                "validator_reason": report.get("bundle_contract_error") or pair_report.get(
                    "not_scored_reason", "missing_or_duplicate_pair_report"
                ),
            })
            continue
        if any(pair_report.get(field) != expected for field, expected in (
            ("arm", v0_plan["arm"]),
            ("v0_episode_id", v0_plan["episode_id"]),
            ("v1_episode_id", v1_plan["episode_id"]),
        )):
            incomplete.append({"analysis_pair_id": pair_id, "arm": v0_plan["arm"],
                               "pair_status": "not_scored", "not_scored_reason": "validator_pair_identity_mismatch"})
            continue
        invariant_fields = (
            "case_id",
            "source_cluster_id",
            "arm",
            "stratum_id",
            "defense_id",
            "defense_configuration_sha256",
            "policy_manifest_sha256",
            "model_configuration_id",
            "seed",
            "arm_binding_sha256",
            "expected_pre_state_sha256",
            "effect_oracle_contract_sha256",
            "default_control_contract_sha256",
            "trace_normalization_contract_sha256",
        )
        if any(v0_plan.get(field) != v1_plan.get(field) for field in invariant_fields):
            incomplete.append(
                {
                    "analysis_pair_id": pair_id,
                    "arm": v0_plan.get("arm"),
                    "pair_status": "not_scored",
                    "not_scored_reason": "manifest_pair_invariant_mismatch",
                }
            )
            continue
        v0 = episodes.get(str(v0_plan["episode_id"]))
        v1 = episodes.get(str(v1_plan["episode_id"]))
        if not v0 or not v1 or v0.get("score_status") != "scored" or v1.get("score_status") != "scored":
            reasons = sorted(
                {
                    str((row or {}).get("not_scored_reason") or "missing_episode_report")
                    for row in (v0, v1)
                    if not row or row.get("score_status") != "scored"
                }
            )
            incomplete.append(
                {
                    "analysis_pair_id": pair_id,
                    "arm": v0_plan.get("arm"),
                    "pair_status": "not_scored",
                    "not_scored_reason": "missing_or_unscored_v0_or_v1_sibling",
                    "episode_reasons": reasons,
                }
            )
            continue
        if not isinstance(v0.get("endpoint"), bool) or not isinstance(v1.get("endpoint"), bool):
            incomplete.append(
                {
                    "analysis_pair_id": pair_id,
                    "arm": v0_plan.get("arm"),
                    "pair_status": "not_scored",
                    "not_scored_reason": "scored_endpoint_is_not_boolean",
                }
            )
            continue

        # The driver must bind the same source cluster to both siblings.  Do
        # not silently use case_id: that would turn repeated mutations into
        # independent observations.
        cluster = v0_plan.get("source_cluster_id")
        if not isinstance(cluster, str) or not cluster.strip() or any(
            row.get("source_cluster_id") != cluster for row in (v0, v1)
        ):
            incomplete.append(
                {
                    "analysis_pair_id": pair_id,
                    "arm": v0_plan.get("arm"),
                    "pair_status": "not_scored",
                    "not_scored_reason": "source_cluster_id_missing_or_mismatched",
                }
            )
            continue

        if pair_report.get("transition") != f"{int(v0['endpoint'])}{int(v1['endpoint'])}":
            incomplete.append({"analysis_pair_id": pair_id, "arm": v0_plan["arm"],
                               "pair_status": "not_scored", "not_scored_reason": "validator_transition_mismatch"})
            continue

        complete.append(
            {
                "analysis_pair_id": pair_id,
                "source_cluster_id": v0["source_cluster_id"],
                "model_configuration_id": v0_plan["model_configuration_id"],
                "stratum_id": v0_plan["stratum_id"],
                "arm": v0_plan["arm"],
                "case_id": v0_plan["case_id"],
                "defense_id": v0_plan["defense_id"],
                "seed": v0_plan["seed"],
                "endpoint_v0": int(v0["endpoint"]),
                "endpoint_v1": int(v1["endpoint"]),
                "v0_episode_id": v0_plan["episode_id"],
                "v1_episode_id": v1_plan["episode_id"],
            }
        )
    return complete, incomplete


def build_statistics_input(
    bundle: dict[str, Any],
    *,
    manifest: dict[str, Any] | None = None,
    source: Path | None = None,
) -> dict[str, Any]:
    """Validate a bundle and return fixed-denominator paired-analysis input."""

    if manifest is None:
        manifest = load_manifest(DEFAULT_MANIFEST)
    report = validate_and_summarize_bundle(bundle, manifest=manifest, source=source)
    complete, incomplete = _pair_rows(report, manifest)
    by_arm: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in complete:
        by_arm[str(row["arm"])].append(row)
    return {
        "schema_version": ADAPTER_SCHEMA_VERSION,
        "claim_tier": "descriptive_only_until_statistical_analysis_plan_gates_pass",
        "manifest_sha256": report["manifest_sha256"],
        "validator_report_schema_version": report["schema_version"],
        "validator_bundle_contract_error": report["bundle_contract_error"],
        "fixed_denominator": report["summary"]["fixed_denominator"],
        "planned_pair_count": len(manifest["episodes"]) // 2,
        "complete_pair_count": len(complete),
        "not_scored_pair_count": len(incomplete),
        "complete_pairs_by_arm": {
            "attack": len(by_arm.get("attack", [])),
            DEFAULT_CONTROL_ARM: len(by_arm.get(DEFAULT_CONTROL_ARM, [])),
        },
        "complete_pairs": complete,
        "not_scored_pairs": incomplete,
        "not_scored_episode_reasons": report["not_scored_episode_reasons"],
        "cross_arm_comparison": "prohibited",
        "statistics_mapping": {
            "attack": {
                "before": "endpoint_v0",
                "after": "endpoint_v1",
                "key": "analysis_pair_id",
                "cluster": "source_cluster_id",
            },
            "default_control": {
                "before": "endpoint_v0",
                "after": "endpoint_v1",
                "key": "analysis_pair_id",
                "cluster": "source_cluster_id",
            },
        },
    }


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--source", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    manifest = load_manifest(args.manifest.resolve())
    output = build_statistics_input(
        _load_json(args.bundle.resolve()),
        manifest=manifest,
        source=args.source.resolve() if args.source else None,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
