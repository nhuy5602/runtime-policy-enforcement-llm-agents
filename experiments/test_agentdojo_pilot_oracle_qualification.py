"""Regression checks for the source-only AgentDojo oracle qualification."""

from __future__ import annotations

import copy
import unittest

try:
    from experiments.agentdojo_pilot_oracle_qualification import (
        DEFAULT_OUTPUT,
        load_qualification,
        validate_qualification,
    )
except ModuleNotFoundError:  # direct ``python experiments/test_*.py`` support
    from agentdojo_pilot_oracle_qualification import DEFAULT_OUTPUT, load_qualification, validate_qualification


class AgentDojoPilotOracleQualificationTests(unittest.TestCase):
    def test_fixture_blocks_the_historical_three_case_execution_plan(self):
        qualification = load_qualification(DEFAULT_OUTPUT)
        report = validate_qualification(qualification)

        self.assertEqual(report["selected_case_count"], 3)
        self.assertEqual(report["qualified_case_count"], 2)
        self.assertEqual(report["rejected_case_count"], 1)
        self.assertEqual(report["execution_status"], "blocked")
        self.assertEqual(report["result_status"], "source_oracle_qualification_only_not_llm_evaluation")
        self.assertEqual(
            qualification["observed_execution_counters"],
            {
                "llm_requests": 0,
                "provider_requests": 0,
                "network_requests": 0,
                "remote_jobs": 0,
                "local_ground_truth_tool_dispatches": 3,
            },
        )

    def test_each_binding_is_state_specific_and_guard_independent(self):
        qualification = load_qualification(DEFAULT_OUTPUT)
        rejected = []
        for binding in qualification["bindings"]:
            self.assertEqual(binding["oracle_binding"]["outcome_field"], "harmful_effect_observed")
            self.assertEqual(
                binding["oracle_binding"]["guard_dependency"], "none; upstream AgentDojo environment/state predicate"
            )
            self.assertIsNone(binding["oracle_binding"]["observed_result"])
            self.assertFalse(binding["local_source_calibration"]["fresh_state_harmful_effect_observed"])
            self.assertEqual(len(binding["exact_pre_execution_state"]["sha256"]), 64)
            self.assertEqual(
                binding["exact_pre_execution_state"]["materialized_carrier_ids"], [binding["attack_binding"]["carrier_id"]]
            )
            if binding["qualification_status"].startswith("ineligible_"):
                rejected.append(binding)

        self.assertEqual(len(rejected), 1)
        self.assertEqual(rejected[0]["attack_binding"]["injection_task_id"], "injection_task_0")
        self.assertFalse(rejected[0]["local_source_calibration"]["injection_ground_truth_harmful_effect_observed"])
        self.assertIn("must_not_be_scheduled", rejected[0]["execution_decision"])

    def test_binding_or_calibration_tampering_is_rejected(self):
        qualification = load_qualification(DEFAULT_OUTPUT)
        for mutate in (
            lambda value: value["bindings"][0]["exact_pre_execution_state"].update({"sha256": "0" * 64}),
            lambda value: value["bindings"][2].update({"qualification_status": "eligible_for_future_manifest_bound_driver"}),
            lambda value: value["selection"].update({"execution_status": "not_run_pending_driver"}),
        ):
            tampered = copy.deepcopy(qualification)
            mutate(tampered)
            with self.assertRaises(ValueError):
                validate_qualification(tampered)


if __name__ == "__main__":
    unittest.main()
