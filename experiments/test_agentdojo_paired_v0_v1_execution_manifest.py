"""Regression checks for the outcome-blind paired v0/v1 execution manifest."""

from __future__ import annotations

import copy
import os
import unittest
from unittest.mock import patch

try:
    from experiments.agentdojo_paired_v0_v1_execution_manifest import (
        DEFAULT_OUTPUT,
        _canonical_bytes,
        build_manifest,
        load_manifest,
        validate_manifest,
    )
except ModuleNotFoundError:  # direct ``python experiments/test_*.py`` support
    from agentdojo_paired_v0_v1_execution_manifest import (
        DEFAULT_OUTPUT,
        _canonical_bytes,
        build_manifest,
        load_manifest,
        validate_manifest,
    )


class AgentDojoPairedV0V1ExecutionManifestTests(unittest.TestCase):
    def test_fixture_locks_complete_counterbalanced_pairs(self):
        manifest = load_manifest(DEFAULT_OUTPUT)
        report = validate_manifest(manifest)

        self.assertEqual(report["pair_count"], 6)
        self.assertEqual(report["episode_count"], 12)
        self.assertEqual(report["attack_pair_count"], 3)
        self.assertEqual(report["benign_pair_count"], 3)
        self.assertEqual(report["v0_first_pair_count"], 3)
        self.assertEqual(report["v1_first_pair_count"], 3)
        self.assertEqual(manifest["result_status"], "preflight_only_not_run")
        self.assertEqual(
            manifest["observed_execution_counters"],
            {
                "llm_requests": 0,
                "provider_requests": 0,
                "network_requests": 0,
                "remote_jobs": 0,
                "tool_dispatches": 0,
                "cost_usd": 0.0,
            },
        )

        pairs: dict[str, list[dict]] = {}
        for row in manifest["episodes"]:
            pairs.setdefault(row["pair_id"], []).append(row)
            self.assertEqual(row["result_status"], "not_run")
            self.assertIn("registry_witness", row["required_driver_evidence"])
            self.assertIn("typed_pre_state", row["required_driver_evidence"])
            self.assertIn("typed_post_state", row["required_driver_evidence"])
            if row["arm"] == "benign":
                injection = row["attack_or_benign_binding"]["injection"]
                self.assertEqual(injection["mode"], "none")
                self.assertIsNone(injection["injection_task_id"])
                self.assertIsNone(injection["carrier_id"])

        self.assertEqual(len(pairs), 6)
        for siblings in pairs.values():
            self.assertEqual({row["contract"]["version"] for row in siblings}, {"v0", "v1"})
            self.assertEqual(siblings[0]["case_id"], siblings[1]["case_id"])
            self.assertEqual(siblings[0]["expected_pre_state_sha256"], siblings[1]["expected_pre_state_sha256"])
            self.assertNotEqual(
                siblings[0]["contract"]["expected_exposed_tool_names_sha256"],
                siblings[1]["contract"]["expected_exposed_tool_names_sha256"],
            )

    def test_build_is_deterministic_and_does_not_use_external_execution(self):
        with patch.dict(os.environ, {"RUNPOD_API_KEY": "must-not-be-read"}, clear=False), patch(
            "subprocess.run", side_effect=AssertionError("preflight must not spawn a process")
        ), patch("urllib.request.urlopen", side_effect=AssertionError("preflight must not make network calls")):
            first = build_manifest()
            second = build_manifest()
        self.assertEqual(_canonical_bytes(first), _canonical_bytes(second))
        self.assertFalse(first["execution_policy"]["network_or_model_calls_allowed"])
        self.assertFalse(first["execution_policy"]["remote_jobs_allowed"])

    def test_missing_sibling_mixed_registry_false_benign_or_broken_counterbalance_is_rejected(self):
        manifest = load_manifest(DEFAULT_OUTPUT)
        mutations = (
            lambda value: value["episodes"].pop(),
            lambda value: value["episodes"][0]["contract"].update({"version": "v1"}),
            lambda value: value["episodes"][0]["attack_or_benign_binding"]["injection"].update(
                {"mode": "injecagent_real_runtime_carrier_required", "injection_task_id": "injection_task_2"}
            ),
            lambda value: [row.update({"execution_order": row["execution_order"] + 1}) for row in value["episodes"]],
        )
        for mutate in mutations:
            with self.subTest(mutate=mutate):
                tampered = copy.deepcopy(manifest)
                mutate(tampered)
                with self.assertRaises(ValueError):
                    validate_manifest(tampered)


if __name__ == "__main__":
    unittest.main()
