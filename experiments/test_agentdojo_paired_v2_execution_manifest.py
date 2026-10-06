"""Regression checks for the prospective v2 paired preregistration."""

from __future__ import annotations

import copy
import unittest

try:
    from experiments.agentdojo_paired_v2_execution_manifest import (
        ARMS,
        DEFAULT_CONTROL_ARM,
        DEFAULT_OUTPUT,
        RESULT_BUNDLE_SCHEMA_VERSION,
        load_manifest,
        validate_manifest,
    )
    from experiments.agentdojo_paired_v0_v1_execution_manifest import DEFAULT_OUTPUT as V1_OUTPUT
    from experiments.agentdojo_paired_v0_v1_execution_manifest import load_manifest as load_v1_manifest
except ModuleNotFoundError:  # direct python experiments/test_*.py support
    from agentdojo_paired_v2_execution_manifest import (
        ARMS,
        DEFAULT_CONTROL_ARM,
        DEFAULT_OUTPUT,
        RESULT_BUNDLE_SCHEMA_VERSION,
        load_manifest,
        validate_manifest,
    )
    from agentdojo_paired_v0_v1_execution_manifest import DEFAULT_OUTPUT as V1_OUTPUT
    from agentdojo_paired_v0_v1_execution_manifest import load_manifest as load_v1_manifest


class AgentDojoPairedV2ExecutionManifestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = load_manifest(DEFAULT_OUTPUT)

    def test_fixture_has_complete_balanced_fixed_denominator(self) -> None:
        report = validate_manifest(self.manifest)
        self.assertEqual(report["pair_count"], 6)
        self.assertEqual(report["episode_count"], 12)
        self.assertEqual(report["attack_pair_count"], 3)
        self.assertEqual(report["default_control_pair_count"], 3)
        self.assertEqual((report["v0_first_pair_count"], report["v1_first_pair_count"]), (3, 3))
        self.assertEqual(self.manifest["design"]["arms"], list(ARMS))
        self.assertEqual(self.manifest["result_bundle_compatibility"]["schema_version"], RESULT_BUNDLE_SCHEMA_VERSION)
        self.assertEqual(self.manifest["observed_execution_counters"]["remote_jobs"], 0)

    def test_default_control_arm_is_distinct_and_requires_trace_witness(self) -> None:
        controls = [row for row in self.manifest["episodes"] if row["arm"] == DEFAULT_CONTROL_ARM]
        self.assertEqual(len(controls), 6)
        for row in controls:
            binding = row["arm_binding"]
            self.assertFalse(binding["injection"]["injecagent_invoked"])
            self.assertTrue(binding["injection"]["default_carrier_present"])
            self.assertEqual(binding["outcome"]["endpoint_field"], "utility_success")
            self.assertTrue(binding["trace_normalization_contract"]["raw_trace_must_be_retained"])
            self.assertTrue(binding["trace_normalization_contract"]["canonical_trace_must_be_retained"])
            self.assertTrue(
                {"raw_function_trace", "canonical_function_trace", "trace_normalization_witness"}
                <= set(row["required_driver_evidence"])
            )
            if row["contract"]["version"] == "v1":
                self.assertEqual(binding["trace_normalization_contract"]["v1_direction"], "v1_to_canonical_v0")

    def test_attack_arm_remains_bound_to_effect_oracle(self) -> None:
        attacks = [row for row in self.manifest["episodes"] if row["arm"] == "attack"]
        self.assertEqual(len(attacks), 6)
        for row in attacks:
            binding = row["arm_binding"]
            self.assertEqual(binding["injection"]["mode"], "injecagent_real_runtime_carrier_required")
            self.assertEqual(binding["outcome"]["endpoint_field"], "harmful_effect_observed")
            self.assertIsNone(row["default_control_contract_sha256"])
            self.assertIsNone(row["trace_normalization_contract_sha256"])

    def test_tampering_or_incomplete_control_definition_is_rejected(self) -> None:
        controls = [row for row in self.manifest["episodes"] if row["arm"] == DEFAULT_CONTROL_ARM]
        for mutate in (
            lambda value: value["source"]["default_control_contract"].update({"sha256": "0" * 64}),
            lambda value: controls_for(value)[0]["arm_binding"]["injection"].update({"injecagent_invoked": True}),
            lambda value: controls_for(value)[0]["required_driver_evidence"].remove("trace_normalization_witness"),
        ):
            tampered = copy.deepcopy(self.manifest)
            mutate(tampered)
            with self.assertRaises(ValueError):
                validate_manifest(tampered)

    def test_historical_v1_manifest_remains_semantically_distinct(self) -> None:
        historical = load_v1_manifest(V1_OUTPUT)
        self.assertEqual(historical["schema_version"], "agentdojo-paired-v0-v1-execution-manifest/v1")
        self.assertIn("benign", historical["design"]["arms"])
        self.assertNotIn(DEFAULT_CONTROL_ARM, historical["design"]["arms"])


def controls_for(manifest: dict) -> list[dict]:
    return [row for row in manifest["episodes"] if row["arm"] == DEFAULT_CONTROL_ARM]


if __name__ == "__main__":
    unittest.main()
