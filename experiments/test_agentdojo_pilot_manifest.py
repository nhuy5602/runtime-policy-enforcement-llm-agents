"""Regression checks for the outcome-blind AgentDojo pilot population."""

from __future__ import annotations

import copy
import unittest
from pathlib import Path

try:
    from experiments.agentdojo_pilot_manifest import load_manifest, validate_manifest
except ModuleNotFoundError:  # direct ``python experiments/test_*.py`` support
    from agentdojo_pilot_manifest import load_manifest, validate_manifest


FIXTURE = Path(__file__).with_name("fixtures") / "agentdojo_pilot_case_manifest_v1.json"


class AgentDojoPilotManifestTests(unittest.TestCase):
    def test_population_is_pinned_outcome_blind_and_not_run(self):
        manifest = load_manifest(FIXTURE)
        report = validate_manifest(manifest)

        self.assertEqual(report["case_count"], 840)
        self.assertEqual(report["selected_attack_episode_count"], 3)
        self.assertEqual(report["result_status"], "not_run")
        self.assertEqual(
            report["selected_case_ids"],
            [
                "workspace:v1.2.2:user_task_7:injection_task_2:calendar_moving_event_reason_injection",
                "workspace:v1.2.2:user_task_28:injection_task_1:drive_feedback_injection",
                "workspace:v1.2.2:user_task_18:injection_task_0:email_hiking_injection",
            ],
        )
        rows = {row["case_id"]: row for row in manifest["population"]["rows"]}
        for case_id in report["selected_case_ids"]:
            self.assertEqual(rows[case_id]["execution_eligibility"], "standard_injecagent_single_carrier")
            self.assertEqual(
                rows[case_id]["harmful_effect_oracle"]["guard_dependency"],
                "none; upstream environment/state oracle",
            )

    def test_row_or_selection_tampering_is_rejected(self):
        manifest = load_manifest(FIXTURE)

        row_tampered = copy.deepcopy(manifest)
        row_tampered["population"]["rows"][0]["carrier_surface"] = "email"
        with self.assertRaises(ValueError):
            validate_manifest(row_tampered)

        selection_tampered = copy.deepcopy(manifest)
        selection_tampered["feasibility_selection"]["selected_attack_episode_count"] = 4
        with self.assertRaises(ValueError):
            validate_manifest(selection_tampered)


if __name__ == "__main__":
    unittest.main()
