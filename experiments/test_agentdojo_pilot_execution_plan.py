"""Tests for the no-billable AgentDojo pilot execution plan."""

from __future__ import annotations

import copy
import os
import unittest
from unittest.mock import patch

try:
    from experiments.agentdojo_pilot_execution_plan import (
        DEFAULT_OUTPUT,
        _canonical_bytes,
        build_plan,
        load_plan,
        validate_plan,
    )
except ModuleNotFoundError:  # direct ``python experiments/test_*.py`` support
    from agentdojo_pilot_execution_plan import DEFAULT_OUTPUT, _canonical_bytes, build_plan, load_plan, validate_plan


class AgentDojoPilotExecutionPlanTests(unittest.TestCase):
    def test_fixture_locks_twelve_unexecuted_invocations(self):
        plan = load_plan(DEFAULT_OUTPUT)
        report = validate_plan(plan)

        self.assertEqual(report["selected_case_count"], 3)
        self.assertEqual(report["planned_invocation_count"], 12)
        self.assertEqual(report["attack_invocation_count"], 6)
        self.assertEqual(report["benign_twin_invocation_count"], 6)
        self.assertEqual(plan["selection"]["nominal_upstream_task_episodes"], 18)
        self.assertFalse(plan["execution_policy"]["network_or_model_calls_allowed"])
        self.assertFalse(plan["execution_policy"]["automatic_retry_allowed"])
        self.assertEqual(
            plan["observed_execution_counters"],
            {"provider_requests": 0, "remote_jobs": 0, "tool_dispatches": 0, "cost_usd": 0.0},
        )
        for episode in plan["episodes"]:
            self.assertEqual(episode["result_status"], "not_run")
            self.assertIn("unobserved", episode["reset_before_episode"])
            self.assertIn("not_scored", episode["outcome_scoring_rule"])
            self.assertFalse(episode["outcome_oracle"]["evaluated"])
            self.assertIsNone(episode["outcome_oracle"]["outcome"])
            if episode["arm"] == "benign_twin":
                self.assertEqual(episode["injection"]["mode"], "none")
                self.assertIn("blocked", episode["executor_status"])
            if episode["track"] == "attested":
                self.assertIn("wildcard allowlist is prohibited", episode["configuration"]["attested_policy"])

    def test_plan_generation_is_deterministic_and_has_no_external_side_effect(self):
        with patch.dict(os.environ, {"RUNPOD_API_KEY": "must-not-be-read"}, clear=False), patch(
            "subprocess.run", side_effect=AssertionError("planner must not spawn a process")
        ), patch("urllib.request.urlopen", side_effect=AssertionError("planner must not make network calls")):
            first = build_plan()
            second = build_plan()
        self.assertEqual(_canonical_bytes(first), _canonical_bytes(second))
        self.assertEqual(first["result_status"], "preflight_only_not_run")

    def test_any_binding_or_cardinality_tampering_is_rejected(self):
        plan = load_plan(DEFAULT_OUTPUT)
        for mutate in (
            lambda value: value["episodes"][0].update({"user_task_id": "user_task_0"}),
            lambda value: value["episodes"].pop(),
            lambda value: value["source"]["agentdojo"].update({"commit": "0" * 40}),
        ):
            tampered = copy.deepcopy(plan)
            mutate(tampered)
            with self.assertRaises(ValueError):
                validate_plan(tampered)


if __name__ == "__main__":
    unittest.main()
