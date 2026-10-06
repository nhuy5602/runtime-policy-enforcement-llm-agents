"""Regression checks for v0/v1 utility-trace canonicalization."""

from __future__ import annotations

import copy
import json
import unittest

try:
    from experiments.agentdojo_v2_utility_trace_normalization_contract import (
        DEFAULT_OUTPUT,
        TraceNormalizationError,
        _tool_mapping,
        load_contract,
        normalize_trace,
        normalize_utility_evidence,
        validate_contract,
        validate_normalization_witness,
    )
except ModuleNotFoundError:  # direct python experiments/test_*.py support
    from agentdojo_v2_utility_trace_normalization_contract import (
        DEFAULT_OUTPUT,
        TraceNormalizationError,
        _tool_mapping,
        load_contract,
        normalize_trace,
        normalize_utility_evidence,
        validate_contract,
        validate_normalization_witness,
    )


class AgentDojoV2UtilityTraceNormalizationContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = load_contract(DEFAULT_OUTPUT)
        self.v0_name, self.v1_name = next(iter(_tool_mapping().items()))
        self.v0_trace = [
            {
                "function": self.v0_name,
                "args": {"stable": ["argument"]},
                "id": None,
                "placeholder_args": None,
            }
        ]

    def test_fixture_is_source_only_and_has_six_compatibility_controls(self) -> None:
        report = validate_contract(self.contract)
        self.assertEqual(report["selected_case_count"], 3)
        self.assertEqual(report["source_only_calibration_control_count"], 6)
        self.assertEqual(report["execution_status"], "not_run_pending_v2_manifest_result_bundle_and_driver")
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
        self.assertNotIn("techservices.com/auth", json.dumps(self.contract, ensure_ascii=False))

    def test_v0_identity_and_v1_inverse_mapping_preserve_arguments(self) -> None:
        v0_canonical, v0_witness = normalize_trace(self.contract, "v0", self.v0_trace)
        v1_raw = copy.deepcopy(self.v0_trace)
        v1_raw[0]["function"] = self.v1_name
        v1_canonical, v1_witness = normalize_trace(self.contract, "v1", v1_raw)
        self.assertEqual(v0_canonical, self.v0_trace)
        self.assertEqual(v1_canonical, self.v0_trace)
        self.assertEqual(v0_witness["arguments_sha256"], v0_witness["canonical_arguments_sha256"])
        self.assertEqual(v1_witness["arguments_sha256"], v1_witness["canonical_arguments_sha256"])
        validate_normalization_witness(self.contract, "v0", self.v0_trace, v0_canonical, v0_witness)
        validate_normalization_witness(self.contract, "v1", v1_raw, v1_canonical, v1_witness)

    def test_unknown_name_or_tampered_witness_fails_closed(self) -> None:
        unknown = copy.deepcopy(self.v0_trace)
        unknown[0]["function"] = "not_a_reviewed_tool"
        with self.assertRaises(TraceNormalizationError):
            normalize_trace(self.contract, "v0", unknown)
        canonical, witness = normalize_trace(self.contract, "v0", self.v0_trace)
        tampered = copy.deepcopy(witness)
        tampered["canonical_trace_sha256"] = "0" * 64
        with self.assertRaises(TraceNormalizationError):
            validate_normalization_witness(self.contract, "v0", self.v0_trace, canonical, tampered)

    def test_normalized_evidence_retains_raw_trace_only_via_witness(self) -> None:
        v1_raw = copy.deepcopy(self.v0_trace)
        v1_raw[0]["function"] = self.v1_name
        evidence = {"terminal_output": "", "function_trace": v1_raw}
        result = normalize_utility_evidence(self.contract, "v1", evidence)
        self.assertEqual(result["canonical_utility_evidence"]["function_trace"], self.v0_trace)
        self.assertEqual(evidence["function_trace"], v1_raw)
        self.assertEqual(result["trace_normalization_witness"]["contract_version"], "v1")

    def test_tampered_contract_is_rejected(self) -> None:
        for mutate in (
            lambda value: value["mapping"].update({"argument_transform": "rewrite"}),
            lambda value: value["source_only_calibration"][0]["v1_synthetic_renaming"].update({"utility_success": False}),
            lambda value: value["future_driver_requirement"].update({"runtime_plan_authorization": "authorized"}),
        ):
            tampered = copy.deepcopy(self.contract)
            mutate(tampered)
            with self.assertRaises(ValueError):
                validate_contract(tampered)


if __name__ == "__main__":
    unittest.main()
