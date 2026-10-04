"""Regression checks for the fresh-process correction of the v2 source gate."""

from __future__ import annotations

import copy
import unittest

try:
    from experiments.agentdojo_v2_selected_binding_regeneration_adjudication import (
        ADJUDICATION_STATUS,
        DEFAULT_OUTPUT,
        HISTORICAL_OBSERVATION_STATUS,
        RUNTIME_PLAN_AUTHORIZATION,
        load_adjudication,
        validate_adjudication,
    )
except ModuleNotFoundError:  # direct script execution support
    from agentdojo_v2_selected_binding_regeneration_adjudication import (
        ADJUDICATION_STATUS,
        DEFAULT_OUTPUT,
        HISTORICAL_OBSERVATION_STATUS,
        RUNTIME_PLAN_AUTHORIZATION,
        load_adjudication,
        validate_adjudication,
    )


class AgentDojoV2SelectedBindingRegenerationAdjudicationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.adjudication = load_adjudication(DEFAULT_OUTPUT)

    def test_fixture_retains_the_old_observation_but_reproduces_all_nine_fresh_trials(self) -> None:
        report = validate_adjudication(self.adjudication)
        self.assertEqual(report["adjudication_status"], ADJUDICATION_STATUS)
        self.assertEqual(report["case_count"], 3)
        self.assertEqual(report["case_trial_count"], 9)
        self.assertEqual(report["historical_audit_observation_status"], HISTORICAL_OBSERVATION_STATUS)
        self.assertEqual(report["runtime_plan_authorization"], RUNTIME_PLAN_AUTHORIZATION)
        self.assertEqual([child["child_ordinal"] for child in self.adjudication["fresh_process_children"]], [1, 2, 3])
        for summary in self.adjudication["current_source_reproduction"]["case_summaries"]:
            self.assertEqual(summary["replicate_count"], 3)
            self.assertEqual(summary["unique_observed_pre_state_hash_count"], 1)
            self.assertTrue(summary["all_replicates_equal"])
            self.assertTrue(summary["all_replicates_match_selection_witness"])
            self.assertTrue(summary["all_replicates_match_effect_oracle_witness"])
        self.assertEqual(self.adjudication["self_reported_execution_counters"]["llm_requests"], 0)
        self.assertEqual(self.adjudication["self_reported_execution_counters"]["remote_jobs"], 0)

    def test_missing_duplicate_failed_or_tampered_evidence_is_rejected(self) -> None:
        mutations = (
            lambda value: value["fresh_process_children"].pop(),
            lambda value: value["fresh_process_children"][1].update({"child_ordinal": 1}),
            lambda value: value["fresh_process_children"][0].update({"child_status": "failed"}),
            lambda value: value["fresh_process_children"][0]["trials"][0].update({"observed_pre_state_sha256": "0" * 64}),
            lambda value: value["fresh_process_children"][0]["source_provenance"]["workspace_state_data_files"].update(
                {"src/agentdojo/data/suites/workspace/environment.yaml": "0" * 64}
            ),
            lambda value: value["fresh_process_children"][0]["runtime_witness"]["python"].update(
                {
                    "executable_location": {
                        "location_class": "agentdojo_source_relative",
                        "path": "C:\\Users\\not-a-source\\python.exe",
                    }
                }
            ),
            lambda value: value["inputs"]["prior_regeneration_audit"].update({"sha256": "0" * 64}),
            lambda value: value.update({"runtime_plan_authorization": "authorized"}),
            lambda value: value["current_source_reproduction"]["case_summaries"][0].update(
                {"unique_observed_pre_state_hash_count": 2}
            ),
        )
        for mutate in mutations:
            with self.subTest(mutate=mutate):
                tampered = copy.deepcopy(self.adjudication)
                mutate(tampered)
                with self.assertRaises(ValueError):
                    validate_adjudication(tampered)


if __name__ == "__main__":
    unittest.main()
