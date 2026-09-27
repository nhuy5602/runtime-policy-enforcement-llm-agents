"""Regression tests for paired episode-level statistics."""

from __future__ import annotations

import unittest

try:
    from .paired_statistics import (
        align_rows,
        compare_row_sets,
        exact_mcnemar,
        holm_adjust,
        paired_binary_summary,
        paired_bootstrap_difference,
    )
except ImportError:  # discovery from ``-s experiments``
    from paired_statistics import (  # type: ignore[no-redef]
        align_rows,
        compare_row_sets,
        exact_mcnemar,
        holm_adjust,
        paired_binary_summary,
        paired_bootstrap_difference,
    )


class PairedStatisticsTests(unittest.TestCase):
    def test_exact_mcnemar_uses_only_discordant_pairs(self) -> None:
        result = exact_mcnemar([1, 1, 0, 0], [0, 1, 0, 1])
        self.assertEqual(result["before_1_after_0"], 1)
        self.assertEqual(result["before_0_after_1"], 1)
        self.assertEqual(result["before_1_after_1"], 1)
        self.assertEqual(result["before_0_after_0"], 1)
        self.assertEqual(result["discordant_pairs"], 2)
        self.assertEqual(result["p_exact_two_sided"], 1.0)

    def test_summary_reports_direction_ci_and_small_sample_caveats(self) -> None:
        result = paired_binary_summary(
            [1, 1, 0, 0],
            [0, 1, 0, 1],
            seed=11,
            samples=200,
            cluster_ids=["a", "a", "b", "b"],
        )
        self.assertEqual(result["risk_difference_after_minus_before"], 0.0)
        self.assertEqual(result["n_episodes"], 4)
        self.assertEqual(result["n_independent_units"], 2)
        self.assertEqual(result["unit"], "cluster")
        self.assertEqual(result["statistical_status"], "descriptive_only")
        self.assertEqual(result["paired_bootstrap_95_ci"]["seed"], 11)
        self.assertTrue(result["caveats"])

    def test_cluster_bootstrap_is_reproducible_and_differs_from_episode_unit(self) -> None:
        episode = paired_bootstrap_difference(
            [1, 1, 1, 0],
            [0, 0, 1, 0],
            seed=7,
            samples=300,
        )
        clustered = paired_bootstrap_difference(
            [1, 1, 1, 0],
            [0, 0, 1, 0],
            seed=7,
            samples=300,
            cluster_ids=["source-a", "source-a", "source-a", "source-b"],
        )
        self.assertEqual(episode["estimate"], clustered["estimate"])
        self.assertNotEqual(episode["n_independent_units"], clustered["n_independent_units"])
        self.assertEqual(
            clustered,
            paired_bootstrap_difference(
                [1, 1, 1, 0],
                [0, 0, 1, 0],
                seed=7,
                samples=300,
                cluster_ids=["source-a", "source-a", "source-a", "source-b"],
            ),
        )

    def test_alignment_rejects_missing_or_duplicate_pairs(self) -> None:
        with self.assertRaisesRegex(ValueError, "no paired rows"):
            align_rows(
                [{"case_id": "a", "value": 1}],
                [{"case_id": "b", "value": 0}],
                value="value",
            )
        with self.assertRaisesRegex(ValueError, "duplicate case_id"):
            align_rows(
                [{"case_id": "a", "value": 1}, {"case_id": "a", "value": 0}],
                [{"case_id": "a", "value": 0}],
                value="value",
            )

    def test_compare_row_sets_uses_existing_rows_and_hashes_pair_order(self) -> None:
        before = [
            {"case_id": "b", "source_case_id": "s2", "outcome": 1},
            {"case_id": "a", "source_case_id": "s1", "outcome": 1},
        ]
        after = [
            {"case_id": "a", "source_case_id": "s1", "outcome": 0},
            {"case_id": "b", "source_case_id": "s2", "outcome": 0},
        ]
        result = compare_row_sets(
            before,
            after,
            value="outcome",
            cluster="source_case_id",
            seed=3,
            samples=200,
        )
        self.assertEqual(result["paired_case_count"], 2)
        self.assertEqual(result["before_rate"], 1.0)
        self.assertEqual(result["after_rate"], 0.0)
        self.assertEqual(result["risk_difference_after_minus_before"], -1.0)
        self.assertTrue(result["paired_case_id_sha256"])

    def test_invalid_inputs_fail_closed(self) -> None:
        with self.assertRaises(ValueError):
            exact_mcnemar([0], [0, 1])
        with self.assertRaises(ValueError):
            exact_mcnemar([2], [0])
        with self.assertRaises(ValueError):
            paired_bootstrap_difference([0], [1], samples=0)
        with self.assertRaises(ValueError):
            holm_adjust([0.1, 1.1])

    def test_holm_adjustment_preserves_order_and_monotonicity(self) -> None:
        self.assertEqual(holm_adjust([0.01, 0.04, 0.2]), [0.03, 0.08, 0.2])
        adjusted = holm_adjust([0.04, 0.01, 0.03])
        self.assertEqual(adjusted, [0.06, 0.03, 0.06])


if __name__ == "__main__":
    unittest.main()
