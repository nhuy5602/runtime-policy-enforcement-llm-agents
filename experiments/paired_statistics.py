"""Paired binary statistics for fixed agent traces.

The research corpus replays the same episode under multiple configurations.
Those outcomes are paired, not independent.  This module deliberately uses
only the supplied paired observations and the Python standard library:

* exact two-sided McNemar p-values for binary outcomes;
* paired bootstrap confidence intervals for the rate difference;
* effect sizes (risk difference, relative risk, and paired odds ratio);
* warnings when the number of episodes or independent source clusters is small.

The returned intervals describe the observed replay set.  They are not a
license to treat repeated synthetic mutations as independent population
episodes; the caveat is carried in every result.
"""

from __future__ import annotations

import math
import random
import statistics
import hashlib
from collections import Counter, defaultdict
from collections.abc import Hashable, Iterable, Sequence
from typing import Any


def _binary(values: Iterable[bool | int], *, name: str) -> list[int]:
    result: list[int] = []
    for index, value in enumerate(values):
        if isinstance(value, bool):
            result.append(int(value))
        elif isinstance(value, int) and value in (0, 1):
            result.append(value)
        else:
            raise ValueError(f"{name}[{index}] must be binary 0/1 or bool")
    return result


def _paired(before: Iterable[bool | int], after: Iterable[bool | int]) -> tuple[list[int], list[int]]:
    a = _binary(before, name="before")
    b = _binary(after, name="after")
    if len(a) != len(b):
        raise ValueError(f"paired inputs have different lengths: {len(a)} != {len(b)}")
    if not a:
        raise ValueError("paired inputs must not be empty")
    return a, b


def _percentile(sorted_values: Sequence[float], q: float) -> float:
    if not sorted_values:
        raise ValueError("cannot take a percentile of an empty sample")
    position = (len(sorted_values) - 1) * q
    low = math.floor(position)
    high = math.ceil(position)
    if low == high:
        return float(sorted_values[low])
    fraction = position - low
    return float(sorted_values[low] + (sorted_values[high] - sorted_values[low]) * fraction)


def _binomial_cdf(k: int, n: int) -> float:
    """CDF[X <= k] for X ~ Binomial(n, 0.5), computed exactly."""

    if n < 0 or k < 0:
        return 0.0
    if k >= n:
        return 1.0
    denominator = 2**n
    return sum(math.comb(n, i) for i in range(k + 1)) / denominator


def exact_mcnemar(
    before: Iterable[bool | int],
    after: Iterable[bool | int],
) -> dict[str, int | float]:
    """Return the exact two-sided McNemar result for paired binary outcomes.

    ``before`` and ``after`` use the same episode order.  The direction is
    ``after - before`` throughout this module.  With no discordant pairs the
    exact p-value is 1.0; with small discordant counts the test is discrete and
    low-powered, which is reported by :func:`paired_binary_summary`.
    """

    a, b = _paired(before, after)
    table = Counter((left, right) for left, right in zip(a, b))
    before_0_after_0 = table[(0, 0)]
    before_0_after_1 = table[(0, 1)]
    before_1_after_0 = table[(1, 0)]
    before_1_after_1 = table[(1, 1)]
    discordant = before_0_after_1 + before_1_after_0
    if not discordant:
        p_value = 1.0
    else:
        lower_tail = _binomial_cdf(min(before_0_after_1, before_1_after_0), discordant)
        p_value = min(1.0, 2.0 * lower_tail)
    return {
        "n": len(a),
        "before_0_after_0": before_0_after_0,
        "before_0_after_1": before_0_after_1,
        "before_1_after_0": before_1_after_0,
        "before_1_after_1": before_1_after_1,
        "discordant_pairs": discordant,
        "p_exact_two_sided": p_value,
    }


def paired_bootstrap_difference(
    before: Iterable[bool | int],
    after: Iterable[bool | int],
    *,
    seed: int = 20260926,
    samples: int = 4000,
    alpha: float = 0.05,
    cluster_ids: Iterable[Hashable] | None = None,
) -> dict[str, Any]:
    """Bootstrap the paired rate difference ``mean(after - before)``.

    If ``cluster_ids`` is supplied, entire clusters are resampled together.
    This is the conservative option for the current synthetic matrix, where
    many mutation rows originate from only a few source cases.  Cluster labels
    are metadata already present in the trace; no observations are invented.
    """

    a, b = _paired(before, after)
    if not 0 < alpha < 1:
        raise ValueError("alpha must be between 0 and 1")
    if samples <= 0:
        raise ValueError("samples must be positive")
    if cluster_ids is None:
        labels: list[Hashable] = list(range(len(a)))
        unit = "episode"
    else:
        labels = list(cluster_ids)
        if len(labels) != len(a):
            raise ValueError(
                f"cluster_ids length {len(labels)} does not match paired length {len(a)}"
            )
        unit = "cluster"

    groups: dict[Hashable, list[int]] = defaultdict(list)
    for index, label in enumerate(labels):
        groups[label].append(index)
    group_values = list(groups.values())
    if not group_values:
        raise ValueError("at least one bootstrap unit is required")

    observed_differences = [after_value - before_value for before_value, after_value in zip(a, b)]
    estimate = statistics.fmean(observed_differences)
    rng = random.Random(seed)
    bootstrap_estimates: list[float] = []
    # Resample the same number of units as observed.  For clustered data, all
    # rows in a selected source cluster stay together.
    for _ in range(samples):
        selected_groups = [group_values[rng.randrange(len(group_values))] for _ in group_values]
        selected_indices = [index for group in selected_groups for index in group]
        bootstrap_estimates.append(
            statistics.fmean(observed_differences[index] for index in selected_indices)
        )
    bootstrap_estimates.sort()
    low = _percentile(bootstrap_estimates, alpha / 2)
    high = _percentile(bootstrap_estimates, 1 - alpha / 2)
    return {
        "estimate": estimate,
        "low": low,
        "high": high,
        "alpha": alpha,
        "samples": samples,
        "seed": seed,
        "unit": unit,
        "n_episodes": len(a),
        "n_independent_units": len(group_values),
    }


def paired_binary_summary(
    before: Iterable[bool | int],
    after: Iterable[bool | int],
    *,
    seed: int = 20260926,
    samples: int = 4000,
    alpha: float = 0.05,
    cluster_ids: Iterable[Hashable] | None = None,
) -> dict[str, Any]:
    """Return effect sizes, paired CI, exact McNemar test, and caveats."""

    a, b = _paired(before, after)
    mcnemar = exact_mcnemar(a, b)
    bootstrap = paired_bootstrap_difference(
        a,
        b,
        seed=seed,
        samples=samples,
        alpha=alpha,
        cluster_ids=cluster_ids,
    )
    before_rate = statistics.fmean(a)
    after_rate = statistics.fmean(b)
    difference = after_rate - before_rate
    before_positives = sum(a)
    after_positives = sum(b)
    discordant = int(mcnemar["discordant_pairs"])
    forward = int(mcnemar["before_0_after_1"])
    backward = int(mcnemar["before_1_after_0"])
    relative_risk = after_rate / before_rate if before_rate else None
    paired_odds_ratio = forward / backward if backward else None

    units = bootstrap["n_independent_units"]
    caveats: list[str] = []
    if len(a) < 30:
        caveats.append(
            "small episode sample (n<30): exact p-value is discrete and the interval is descriptive"
        )
    if discordant < 10:
        caveats.append(
            "few discordant pairs (<10): McNemar has limited power and the effect estimate is unstable"
        )
    if units < 10:
        caveats.append(
            "fewer than 10 independent bootstrap units: repeated mutations cannot support population inference"
        )
    if bootstrap["low"] == bootstrap["high"]:
        caveats.append(
            "percentile bootstrap interval is degenerate at the observed boundary; "
            "it is not evidence of zero sampling uncertainty"
        )
    if before_rate == 0 or before_rate == 1 or after_rate == 0 or after_rate == 1:
        caveats.append(
            "one or both rates are on a binary boundary; ratio effect sizes may be undefined or unstable"
        )
    if cluster_ids is None and len(a) != units:
        caveats.append("cluster count differs from episode count; report the clustered result")

    descriptive_only = len(a) < 30 or units < 10
    return {
        "n_episodes": len(a),
        "n_independent_units": units,
        "unit": bootstrap["unit"],
        "statistical_status": (
            "descriptive_only" if descriptive_only else "paired_inference_candidate"
        ),
        "before_rate": before_rate,
        "after_rate": after_rate,
        "risk_difference_after_minus_before": difference,
        "relative_risk_after_over_before": relative_risk,
        "paired_odds_ratio_after_vs_before": paired_odds_ratio,
        "paired_odds_ratio_infinite": bool(forward and not backward),
        "before_positives": before_positives,
        "after_positives": after_positives,
        "mcnemar": mcnemar,
        "paired_bootstrap_95_ci": {
            "low": bootstrap["low"],
            "high": bootstrap["high"],
            "estimate": bootstrap["estimate"],
            "alpha": bootstrap["alpha"],
            "samples": bootstrap["samples"],
            "seed": bootstrap["seed"],
        },
        "caveats": caveats,
    }


def holm_adjust(p_values: Iterable[float]) -> list[float]:
    """Return Holm step-down adjusted p-values in the original order."""

    values = [float(value) for value in p_values]
    if any(value < 0 or value > 1 for value in values):
        raise ValueError("p-values must be between 0 and 1")
    adjusted = [0.0] * len(values)
    running_max = 0.0
    order = sorted(range(len(values)), key=lambda index: values[index])
    count = len(values)
    for rank, index in enumerate(order):
        running_max = max(running_max, min(1.0, (count - rank) * values[index]))
        adjusted[index] = running_max
    return adjusted


def align_rows(
    before_rows: Iterable[dict[str, Any]],
    after_rows: Iterable[dict[str, Any]],
    *,
    key: str = "case_id",
    value: str,
    cluster: str | None = None,
) -> tuple[list[int], list[int], list[Hashable] | None, list[str]]:
    """Align two configuration row sets by case key without fabricating rows."""

    before = list(before_rows)
    after = list(after_rows)
    before_index = {str(row[key]): row for row in before}
    after_index = {str(row[key]): row for row in after}
    if len(before_index) != len(before):
        raise ValueError(f"duplicate {key} in before rows")
    if len(after_index) != len(after):
        raise ValueError(f"duplicate {key} in after rows")
    common = sorted(set(before_index) & set(after_index))
    if not common:
        raise ValueError(f"no paired rows share {key}")
    before_values = [_binary([before_index[item][value]], name=value)[0] for item in common]
    after_values = [_binary([after_index[item][value]], name=value)[0] for item in common]
    clusters: list[Hashable] | None = None
    if cluster is not None:
        clusters = []
        for item in common:
            before_cluster = before_index[item].get(cluster)
            after_cluster = after_index[item].get(cluster)
            if before_cluster != after_cluster:
                raise ValueError(f"cluster mismatch for paired {key}={item!r}")
            clusters.append(before_cluster)
    return before_values, after_values, clusters, common


def compare_row_sets(
    before_rows: Iterable[dict[str, Any]],
    after_rows: Iterable[dict[str, Any]],
    *,
    value: str,
    key: str = "case_id",
    cluster: str | None = None,
    seed: int = 20260926,
    samples: int = 4000,
) -> dict[str, Any]:
    """Convenience wrapper for paired analysis of two existing row sets."""

    before = list(before_rows)
    after = list(after_rows)
    before_values, after_values, clusters, labels = align_rows(
        before,
        after,
        key=key,
        value=value,
        cluster=cluster,
    )
    result = paired_binary_summary(
        before_values,
        after_values,
        seed=seed,
        samples=samples,
        cluster_ids=clusters,
    )
    result["key"] = key
    result["value"] = value
    result["paired_case_count"] = len(labels)
    result["paired_case_id_sha256"] = hashlib.sha256(
        "\n".join(labels).encode("utf-8")
    ).hexdigest()
    return result


__all__ = [
    "align_rows",
    "compare_row_sets",
    "exact_mcnemar",
    "holm_adjust",
    "paired_binary_summary",
    "paired_bootstrap_difference",
]
