"""Regression checks for the retained historical selected-binding audit fixture.

The fixture is internally self-consistent. Its source-regeneration conclusion
is deliberately adjudicated separately, so this test must not call it a
reproducible current block.
"""

from __future__ import annotations

import copy
import unittest

try:
    from experiments.agentdojo_v2_selected_binding_regeneration_audit import (
        BLOCKED_STATUS,
        DEFAULT_OUTPUT,
        load_audit,
        validate_audit,
    )
except ModuleNotFoundError:  # direct ``python experiments/test_*.py`` support
    from agentdojo_v2_selected_binding_regeneration_audit import BLOCKED_STATUS, DEFAULT_OUTPUT, load_audit, validate_audit


class AgentDojoV2SelectedBindingRegenerationAuditTests(unittest.TestCase):
    def setUp(self) -> None:
        self.audit = load_audit(DEFAULT_OUTPUT)

    def test_historical_fixture_remains_self_consistent_and_not_an_llm_result(self) -> None:
        report = validate_audit(self.audit)
        self.assertEqual(report["gate_status"], BLOCKED_STATUS)
        self.assertEqual(report["case_count"], 3)
        self.assertEqual(report["matching_case_count"], 0)
        self.assertEqual(report["mismatching_case_count"], 3)
        self.assertEqual(
            self.audit["self_reported_execution_counters"],
            {
                "llm_requests": 0,
                "provider_requests": 0,
                "network_requests": 0,
                "remote_jobs": 0,
                "local_attack_materializations": 3,
                "local_tool_dispatches": 0,
            },
        )
        for case in self.audit["selected_binding_regeneration"]["cases"]:
            self.assertTrue(case["carrier_match"])
            self.assertTrue(case["injection_map_match"])
            self.assertFalse(case["selection_pre_state_match"])
            self.assertFalse(case["effect_oracle_pre_state_match"])

    def test_tampering_with_provenance_or_gate_logic_is_rejected(self) -> None:
        mutations = (
            lambda value: value["inputs"]["v2_selection"].update({"sha256": "0" * 64}),
            lambda value: value["audit_implementation"].update({"sha256": "0" * 64}),
            lambda value: value["source"]["attack_materializer_sources"]["InjecAgentAttack"].update({"sha256": "0" * 64}),
            lambda value: value["source"]["runtime_identity"].update({"pydantic_version": "0.0.0"}),
            lambda value: value["selected_binding_regeneration"]["cases"][0].update({"observed_pre_state_sha256": "0" * 64}),
            lambda value: value["selected_binding_regeneration"]["cases"][0].update({"selection_pre_state_match": True}),
            lambda value: value["selected_binding_regeneration"].update({"matching_case_count": 1}),
            lambda value: value["selected_binding_regeneration"].update({"gate_status": "verified_selected_binding_regeneration"}),
        )
        for mutate in mutations:
            with self.subTest(mutate=mutate):
                tampered = copy.deepcopy(self.audit)
                mutate(tampered)
                with self.assertRaises(ValueError):
                    validate_audit(tampered)


if __name__ == "__main__":
    unittest.main()
