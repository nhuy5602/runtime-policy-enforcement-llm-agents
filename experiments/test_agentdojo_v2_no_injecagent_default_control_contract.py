"""Regression checks for the source-only no-InjecAgent default-control contract."""

from __future__ import annotations

import copy
import json
import unittest

try:
    from experiments.agentdojo_v2_no_injecagent_default_control_contract import (
        ARM_ID,
        DEFAULT_OUTPUT,
        STATE_SCHEMA_VERSION,
        _control_witness,
        load_contract,
        score_default_control_episode,
        validate_contract,
    )
except ModuleNotFoundError:  # direct python experiments/test_*.py support
    from agentdojo_v2_no_injecagent_default_control_contract import (
        ARM_ID,
        DEFAULT_OUTPUT,
        STATE_SCHEMA_VERSION,
        _control_witness,
        load_contract,
        score_default_control_episode,
        validate_contract,
    )


class AgentDojoV2NoInjecAgentDefaultControlContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = load_contract(DEFAULT_OUTPUT)
        self.binding = self.contract["bindings"][0]

    def _base_evidence(self) -> dict:
        return {
            "terminal_status": "completed",
            "failure_flags": {"runner_error": False, "tool_error": False, "timeout": False, "cancelled": False},
            "state_schema_version": STATE_SCHEMA_VERSION,
            "source_verification_witness": self.contract["source"]["verification_witness"],
            "utility_oracle_implementation_sha256": self.contract["utility_oracle_implementation"]["sha256"],
            "no_injecagent_default_control_witness": _control_witness(self.binding),
            "reset_witness": {
                "verified": True,
                "pre_state_sha256": self.binding["default_control"]["expected_pre_state_sha256"],
            },
            "terminal_output": "",
            "function_trace": [],
        }

    def test_fixture_qualifies_three_default_carrier_controls_without_llm(self) -> None:
        report = validate_contract(self.contract)
        self.assertEqual(report["selected_case_count"], 3)
        self.assertEqual(report["source_only_calibration_control_count"], 6)
        self.assertEqual(report["execution_status"], "not_run_pending_prospective_manifest_v2_and_driver")
        self.assertEqual(
            self.contract["observed_execution_counters"],
            {
                "llm_requests": 0,
                "provider_requests": 0,
                "network_requests": 0,
                "remote_jobs": 0,
                "local_ground_truth_tool_dispatches": 5,
            },
        )
        for binding, calibration in zip(self.contract["bindings"], self.contract["source_only_calibration"], strict=True):
            control = binding["default_control"]
            carrier = control["selected_carrier_default"]
            self.assertEqual(control["arm_id"], ARM_ID)
            self.assertTrue(carrier["present"])
            self.assertFalse(carrier["equals_selected_injecagent_attack_text"])
            self.assertNotEqual(control["expected_pre_state_sha256"], control["expected_attack_pre_state_sha256"])
            self.assertEqual(
                [row["utility_success"] for row in calibration["controls"]],
                [False, True],
            )

    def test_fixture_redacts_carrier_and_terminal_content(self) -> None:
        serialized = json.dumps(self.contract, ensure_ascii=False)
        self.assertNotIn("default_text", serialized)
        self.assertNotIn("attack_payload", serialized)
        self.assertNotIn("techservices.com/auth", serialized)
        self.assertNotIn("Two more activities", serialized)
        self.assertNotIn("john.doe", serialized)
        for calibration in self.contract["source_only_calibration"]:
            for control in calibration["controls"]:
                self.assertEqual(set(control["terminal_output"]), {"text_sha256", "character_count"})
                self.assertEqual(set(control["function_trace"]), {"sha256", "call_count"})

    def test_tampering_with_control_or_oracle_binding_is_rejected(self) -> None:
        for mutate in (
            lambda value: value["bindings"][0]["default_control"].update({"arm_id": "benign"}),
            lambda value: value["bindings"][1]["default_control"]["selected_carrier_default"].update({"present": False}),
            lambda value: value["bindings"][2]["utility_oracle"]["source_callables"]["utility_dispatch"].update(
                {"source_file_sha256": "0" * 64}
            ),
            lambda value: value["source_only_calibration"][0]["controls"][1].update({"utility_success": False}),
            lambda value: value["future_episode_result_contract"].update({"runtime_plan_authorization": "authorized"}),
        ):
            tampered = copy.deepcopy(self.contract)
            mutate(tampered)
            with self.assertRaises(ValueError):
                validate_contract(tampered)

    def test_scorer_fails_closed_before_any_source_or_model_execution(self) -> None:
        case_id = self.binding["case_id"]
        evidence = self._base_evidence()
        self.assertEqual(
            score_default_control_episode(self.contract, case_id, {**evidence, "terminal_status": "timeout"})[
                "not_scored_reason"
            ],
            "noncompleted_terminal_status",
        )
        bad_witness = copy.deepcopy(evidence)
        bad_witness["no_injecagent_default_control_witness"]["default_carrier_present"] = False
        self.assertEqual(
            score_default_control_episode(self.contract, case_id, bad_witness)["not_scored_reason"],
            "default_control_witness_mismatch",
        )
        missing_output = copy.deepcopy(evidence)
        del missing_output["terminal_output"]
        self.assertEqual(
            score_default_control_episode(self.contract, case_id, missing_output)["not_scored_reason"],
            "missing_terminal_output",
        )
        self.assertEqual(
            score_default_control_episode(self.contract, case_id, evidence)["not_scored_reason"],
            "source_verification_required",
        )


if __name__ == "__main__":
    unittest.main()
