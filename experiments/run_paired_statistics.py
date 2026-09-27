"""Compute paired statistics from existing offline/live scored artifacts.

This command never generates episodes.  It aligns rows already present in two
configuration outputs, then reports paired rate differences, exact McNemar
tests, and episode-/source-cluster bootstrap intervals.

Examples:

    python experiments/run_paired_statistics.py --self-test
    python experiments/run_paired_statistics.py --output qa/paired_statistics_current.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

try:
    from .paired_statistics import compare_row_sets, holm_adjust
except ImportError:  # direct ``python experiments/run_paired_statistics.py``
    from paired_statistics import compare_row_sets, holm_adjust


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OFFLINE = ROOT / "experiments" / "benchmark_outputs" / "offline_benchmark_results.json"
DEFAULT_LIVE = ROOT / "qa" / "realistic7_scored_all_final.json"
DEFAULT_OUTPUT = ROOT / "qa" / "paired_statistics_current.json"


def _load(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _offline_rows(report: dict[str, Any], configuration: str) -> list[dict[str, Any]]:
    try:
        rows = report["case_outcomes"][configuration]
    except KeyError as exc:
        raise ValueError(f"offline report has no configuration {configuration!r}") from exc
    if not isinstance(rows, list) or not rows:
        raise ValueError(f"offline rows for {configuration!r} are empty")
    return rows


def _live_rows(report: dict[str, Any], configuration: str) -> list[dict[str, Any]]:
    try:
        rows = report["configurations"][configuration]["cases"]
    except KeyError as exc:
        raise ValueError(f"live report has no configuration {configuration!r}") from exc
    if not isinstance(rows, list) or not rows:
        raise ValueError(f"live rows for {configuration!r} are empty")
    return rows


def _offline_comparisons(
    report: dict[str, Any],
    *,
    before: str,
    after: str,
    seed: int,
    samples: int,
) -> list[dict[str, Any]]:
    pairs = [
        ("attack_success", "attack", "source_case_id"),
        ("unauthorized_action", "attack", "source_case_id"),
        ("task_success", "benign", "source_case_id"),
        ("false_block", "benign", "source_case_id"),
    ]
    output: list[dict[str, Any]] = []
    for metric, kind, cluster in pairs:
        before_rows = [row for row in _offline_rows(report, before) if row["kind"] == kind]
        after_rows = [row for row in _offline_rows(report, after) if row["kind"] == kind]
        result = compare_row_sets(
            before_rows,
            after_rows,
            value=metric,
            cluster=cluster,
            seed=seed,
            samples=samples,
        )
        result["metric"] = metric
        result["kind"] = kind
        output.append(result)
    return output


def _live_comparisons(
    report: dict[str, Any],
    *,
    before: str,
    after: str,
    seed: int,
    samples: int,
) -> list[dict[str, Any]]:
    pairs = [
        ("forbidden_effect_executed", "attack"),
        ("task_success", "benign"),
        ("guard_denied_forbidden_proposal", "attack"),
    ]
    output: list[dict[str, Any]] = []
    for metric, kind in pairs:
        before_rows = [row for row in _live_rows(report, before) if row["kind"] == kind]
        after_rows = [row for row in _live_rows(report, after) if row["kind"] == kind]
        result = compare_row_sets(
            before_rows,
            after_rows,
            value=metric,
            cluster=None,
            seed=seed,
            samples=samples,
        )
        result["metric"] = metric
        result["kind"] = kind
        output.append(result)
    return output


def _add_holm_adjustment(comparisons: list[dict[str, Any]]) -> None:
    raw = [float(item["mcnemar"]["p_exact_two_sided"]) for item in comparisons]
    for item, adjusted in zip(comparisons, holm_adjust(raw)):
        item["mcnemar"]["p_holm_adjusted"] = adjusted


def build_report(
    offline_report: dict[str, Any],
    live_report: dict[str, Any] | None,
    *,
    offline_before: str,
    offline_after: str,
    live_before: str,
    live_after: str,
    seed: int,
    samples: int,
) -> dict[str, Any]:
    offline_comparisons = _offline_comparisons(
        offline_report,
        before=offline_before,
        after=offline_after,
        seed=seed,
        samples=samples,
    )
    _add_holm_adjustment(offline_comparisons)
    report: dict[str, Any] = {
        "scope": (
            "paired analysis of existing trace rows; no new episodes or independent "
            "LLM samples are generated"
        ),
        "limitations": [
            "Offline rows are paired by case_id and clustered by source_case_id.",
            "The synthetic offline suite has few independent source components; "
            "clustered intervals are descriptive, not population estimates.",
            "Live configurations reuse one model trace, so the comparison isolates "
            "guard replay conditional on fixed proposals, not model efficacy.",
            "Exact McNemar tests and bootstrap intervals are small-sample diagnostics "
            "and do not repair benchmark or construct-validity limitations.",
        ],
        "bootstrap": {"seed": seed, "samples": samples, "confidence": 0.95},
        "offline": {
            "before": offline_before,
            "after": offline_after,
            "n_cases_reported": offline_report.get("matrix", {}).get("n_cases"),
            "comparisons": offline_comparisons,
        },
    }
    if live_report is not None:
        live_comparisons = _live_comparisons(
            live_report,
            before=live_before,
            after=live_after,
            seed=seed + 1,
            samples=samples,
        )
        _add_holm_adjustment(live_comparisons)
        report["live"] = {
            "before": live_before,
            "after": live_after,
            "model": live_report.get("model"),
            "trace_status": live_report.get("trace_status"),
            "comparisons": live_comparisons,
        }
    return report


def self_test() -> None:
    def row(case_id: str, source: str, kind: str, success: int) -> dict[str, Any]:
        return {
            "case_id": case_id,
            "source_case_id": source,
            "kind": kind,
            "attack_success": success,
            "unauthorized_action": success,
            "task_success": success if kind == "benign" else 0,
            "false_block": int(kind == "benign" and not success),
        }

    report = {
        "matrix": {"n_cases": 6},
        "case_outcomes": {
            "before": [
                row("a", "s1", "attack", 1),
                row("b", "s1", "attack", 0),
                row("c", "s2", "attack", 1),
                row("d", "s2", "attack", 1),
                row("e", "s1", "benign", 1),
                row("f", "s2", "benign", 0),
            ],
            "after": [
                row("a", "s1", "attack", 0),
                row("b", "s1", "attack", 0),
                row("c", "s2", "attack", 0),
                row("d", "s2", "attack", 1),
                row("e", "s1", "benign", 1),
                row("f", "s2", "benign", 1),
            ],
        },
    }
    result = _offline_comparisons(
        report,
        before="before",
        after="after",
        seed=7,
        samples=200,
    )[0]
    assert result["n_episodes"] == 4
    assert result["risk_difference_after_minus_before"] == -0.5
    assert result["mcnemar"]["before_1_after_0"] == 2
    assert result["mcnemar"]["before_0_after_1"] == 0
    assert result["n_independent_units"] == 2
    assert result["caveats"]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--offline", type=Path, default=DEFAULT_OFFLINE)
    parser.add_argument("--live", type=Path, default=DEFAULT_LIVE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--offline-before", default="B0_unsafe")
    parser.add_argument("--offline-after", default="P_postverify")
    parser.add_argument("--live-before", default="C0_schema_only")
    parser.add_argument("--live-after", default="C2_policy_guard")
    parser.add_argument("--seed", type=int, default=20260926)
    parser.add_argument("--bootstrap", type=int, default=4000)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        self_test()
    offline_report = _load(args.offline)
    live_report = _load(args.live) if args.live.exists() else None
    report = build_report(
        offline_report,
        live_report,
        offline_before=args.offline_before,
        offline_after=args.offline_after,
        live_before=args.live_before,
        live_after=args.live_after,
        seed=args.seed,
        samples=args.bootstrap,
    )
    report["inputs"] = {
        "offline": {"path": str(args.offline), "sha256": _sha256(args.offline)},
    }
    if args.live.exists():
        report["inputs"]["live"] = {
            "path": str(args.live),
            "sha256": _sha256(args.live),
        }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
