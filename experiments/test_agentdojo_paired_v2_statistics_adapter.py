import copy
import unittest

from experiments.agentdojo_paired_v2_execution_manifest import load_manifest
from experiments.agentdojo_paired_v2_statistics_adapter import _pair_rows


class AgentDojoPairedV2StatisticsAdapterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = load_manifest()

    def _report(self, *, omit_cluster_for: str | None = None) -> dict:
        episodes = []
        for plan in self.manifest["episodes"]:
            row = {
                "episode_id": plan["episode_id"],
                "score_status": "scored",
                "endpoint": False,
                "not_scored_reason": None,
                "source_cluster_id": plan["source_cluster_id"],
            }
            if plan["contract"]["version"] == "v1":
                row["endpoint"] = plan["arm"] == "attack"
            if plan["episode_id"] == omit_cluster_for:
                row.pop("source_cluster_id")
            episodes.append(row)
        pairs = {}
        for plan in self.manifest["episodes"]:
            pairs.setdefault(plan["pair_id"], {})[plan["contract"]["version"]] = plan
        return {"bundle_contract_error": None, "episodes": episodes, "summary": {"pairs": [
            {"pair_id": pair_id, "arm": versions["v0"]["arm"], "pair_status": "scored",
             "not_scored_reason": None, "v0_episode_id": versions["v0"]["episode_id"],
             "v1_episode_id": versions["v1"]["episode_id"],
             "transition": "01" if versions["v0"]["arm"] == "attack" else "00"}
            for pair_id, versions in pairs.items()
        ]}}

    def test_complete_pairs_are_emitted_separately_by_arm(self) -> None:
        complete, incomplete = _pair_rows(self._report(), self.manifest)
        self.assertEqual(len(complete), 6)
        self.assertEqual(incomplete, [])
        self.assertEqual(
            {row["arm"] for row in complete},
            {"attack", "no_injecagent_default_control"},
        )
        self.assertTrue(all(row["endpoint_v0"] in (0, 1) for row in complete))
        self.assertTrue(all(row["endpoint_v1"] in (0, 1) for row in complete))

    def test_missing_cluster_is_not_imputed_or_scored(self) -> None:
        episode_id = self.manifest["episodes"][0]["episode_id"]
        complete, incomplete = _pair_rows(
            self._report(omit_cluster_for=episode_id),
            self.manifest,
        )
        self.assertEqual(len(complete), 5)
        self.assertEqual(len(incomplete), 1)
        self.assertEqual(
            incomplete[0]["not_scored_reason"],
            "source_cluster_id_missing_or_mismatched",
        )

    def test_rejected_pair_is_excluded_even_when_both_endpoints_are_scored(self):
        report = self._report()
        report["summary"]["pairs"][0].update(
            pair_status="not_scored", not_scored_reason="paired_semantic_registry_mismatch"
        )
        complete, incomplete = _pair_rows(report, self.manifest)
        self.assertEqual(len(complete), 5)
        self.assertEqual(incomplete[0]["validator_reason"], "paired_semantic_registry_mismatch")

    def test_cluster_must_match_manifest_not_just_sibling(self):
        report = self._report()
        for row in report["episodes"]:
            row["source_cluster_id"] = "invented-independent-cluster"
        complete, incomplete = _pair_rows(report, self.manifest)
        self.assertEqual(complete, [])
        self.assertEqual(len(incomplete), 6)

    def test_missing_episode_is_recorded_without_crashing(self):
        report = self._report()
        report["episodes"].pop()
        complete, incomplete = _pair_rows(report, self.manifest)
        self.assertEqual(len(complete), 5)
        self.assertIn("missing_episode_report", incomplete[0]["episode_reasons"])

    def test_missing_duplicate_or_wrong_transition_pair_reports_fail_closed(self):
        for mutation in ("missing", "duplicate", "transition", "identity", "bundle"):
            with self.subTest(mutation=mutation):
                report = self._report()
                pairs = report["summary"]["pairs"]
                if mutation == "missing":
                    pairs.pop(0)
                elif mutation == "duplicate":
                    pairs.append(copy.deepcopy(pairs[0]))
                elif mutation == "transition":
                    pairs[0]["transition"] = "11"
                elif mutation == "identity":
                    pairs[0]["v1_episode_id"] = "wrong-episode"
                else:
                    report["bundle_contract_error"] = "manifest_digest_mismatch"
                complete, incomplete = _pair_rows(report, self.manifest)
                self.assertEqual(len(complete) + len(incomplete), 6)
                self.assertLess(len(complete), 6)


if __name__ == "__main__":
    unittest.main()
