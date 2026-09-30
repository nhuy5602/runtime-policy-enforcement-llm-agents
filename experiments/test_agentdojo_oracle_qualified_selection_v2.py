"""Regression checks for the source-only AgentDojo v2 selection amendment."""

from __future__ import annotations

import copy
import unittest

try:
    from experiments.agentdojo_oracle_qualified_selection_v2 import (
        DEFAULT_OUTPUT,
        load_selection,
        validate_selection,
    )
except ModuleNotFoundError:  # direct ``python experiments/test_*.py`` support
    from agentdojo_oracle_qualified_selection_v2 import DEFAULT_OUTPUT, load_selection, validate_selection


class AgentDojoOracleQualifiedSelectionV2Tests(unittest.TestCase):
    def test_fixture_censes_all_structural_rows_and_selects_three_unrun_cases(self):
        selection = load_selection(DEFAULT_OUTPUT)
        report = validate_selection(selection)

        self.assertEqual(report["selected_case_count"], 3)
        self.assertEqual(report["v2_candidate_count"], 60)
        self.assertEqual(report["historical_email_candidate_count"], 11)
        self.assertEqual(report["execution_status"], "not_run_pending_new_manifest_bound_driver_and_benign_control")
        self.assertEqual(
            selection["selection"]["selected_case_ids"],
            [
                "workspace:v1.2.2:user_task_8:injection_task_2:calendar_introductory_meeting_injection",
                "workspace:v1.2.2:user_task_29:injection_task_1:drive_team_building_injection",
                "workspace:v1.2.2:user_task_22:injection_task_3:email_password_reset_injection",
            ],
        )
        counters = selection["observed_execution_counters"]
        self.assertEqual(
            {key: counters[key] for key in ("llm_requests", "provider_requests", "network_requests", "remote_jobs")},
            {"llm_requests": 0, "provider_requests": 0, "network_requests": 0, "remote_jobs": 0},
        )
        self.assertGreater(counters["local_ground_truth_tool_dispatches"], 0)

    def test_source_controls_and_v1_failure_are_explicit(self):
        selection = load_selection(DEFAULT_OUTPUT)
        qualified = [row for row in selection["v2_candidate_census"] if row["qualification_status"] == "eligible_source_calibrated"]
        self.assertEqual(len(qualified), 29)
        for row in qualified:
            controls = row["local_source_controls"]
            self.assertFalse(controls["fresh_state_harmful_effect_observed"])
            self.assertTrue(controls["injection_ground_truth_harmful_effect_observed"])
            self.assertFalse(controls["user_ground_truth_harmful_effect_observed"])
            self.assertGreater(row["selection_rank"], 0)
        historical = selection["amendment"]["v1_email_stratum_census"]["census"]
        self.assertEqual(
            sum(row["qualification_status"] == "ineligible_oracle_nondiscriminating" for row in historical), 6
        )
        self.assertIn("exactly one matching email", selection["oracle_scope_limitation"])

    def test_tampering_seed_rank_or_calibration_is_rejected(self):
        selection = load_selection(DEFAULT_OUTPUT)
        for mutate in (
            lambda value: value["selection"]["seed"].update({"value": "0" * 64}),
            lambda value: value["v2_candidate_census"][0].update({"selection_rank": 99}),
            lambda value: value["v2_candidate_census"][0]["source_callables"]["predicate"].update(
                {"source_file_sha256": "0" * 64}
            ),
            lambda value: value["amendment"]["v1_email_stratum_census"]["census"][0].update(
                {"qualification_status": "eligible_source_calibrated"}
            ),
        ):
            tampered = copy.deepcopy(selection)
            mutate(tampered)
            with self.assertRaises(ValueError):
                validate_selection(tampered)


if __name__ == "__main__":
    unittest.main()
