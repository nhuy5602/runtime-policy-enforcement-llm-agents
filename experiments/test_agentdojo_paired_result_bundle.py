"""Tests for the fail-closed paired result-bundle contract."""

from __future__ import annotations

import copy
import os
import unittest
from unittest.mock import patch

try:
    from experiments.agentdojo_paired_result_bundle import (
        CLAIM_TIER,
        _sha256,
        build_result_bundle_template,
        validate_and_summarize_bundle,
    )
    from experiments.agentdojo_paired_v0_v1_execution_manifest import DEFAULT_OUTPUT, load_manifest
except ModuleNotFoundError:  # direct ``python experiments/test_*.py`` support
    from agentdojo_paired_result_bundle import CLAIM_TIER, _sha256, build_result_bundle_template, validate_and_summarize_bundle
    from agentdojo_paired_v0_v1_execution_manifest import DEFAULT_OUTPUT, load_manifest


def _hash(character: str) -> str:
    return character * 64


class AgentDojoPairedResultBundleTests(unittest.TestCase):
    def setUp(self):
        self.manifest = load_manifest(DEFAULT_OUTPUT)
        self.bundle = build_result_bundle_template(self.manifest)
        self.by_id = {row["episode_id"]: row for row in self.manifest["episodes"]}

    def _matching_registry(self, plan: dict, *, version: str | None = None, semantic: str = "a") -> dict:
        # The reviewed v0/v1 contract names are recoverable from the local
        # manifest builder's paired contract fixture; use it only to fabricate
        # structural evidence for this pure unit test, never as runtime data.
        from experiments.agentdojo_contract_migration import load_contract
        from experiments.agentdojo_paired_v0_v1_execution_manifest import TOOL_CONTRACT

        mapping = load_contract(TOOL_CONTRACT)["migration"]["v0_to_v1"]
        selected_version = version or plan["contract"]["version"]
        expected = {name: name for name in mapping} if selected_version == "v0" else {new: old for old, new in mapping.items()}
        names = sorted(expected)
        if selected_version == plan["contract"]["version"]:
            self.assertEqual(_sha256(names), plan["contract"]["expected_exposed_tool_names_sha256"])
        tools = []
        semantic_rows = []
        for name in names:
            canonical_name = expected[name]
            descriptor = {"test_semantic_label": semantic, "canonical_name": canonical_name}
            tools.append(
                {
                    "exposed_name": name,
                    "canonical_name": canonical_name,
                    "semantic_sha256": _sha256(descriptor),
                    "semantic_descriptor": descriptor,
                }
            )
            semantic_rows.append({"canonical_name": canonical_name, "descriptor": descriptor})
        exposed_rows = [
            {key: row[key] for key in ("exposed_name", "canonical_name", "semantic_sha256")}
            for row in tools
        ]
        return {
            "semantic_registry_sha256": _sha256(semantic_rows),
            "exposed_registry_sha256": _sha256(exposed_rows),
            "tool_count": len(names),
            "tools": tools,
        }

    def _complete_record(self, plan: dict, *, endpoint_marker: bool = False, semantic: str = "a") -> dict:
        registry = self._matching_registry(plan, semantic=semantic)
        response = {
            **{key: value for key, value in plan["model_identity_binding"].items() if key != "sampling_contract"},
            "returned_revision": "test-only-returned-revision",
        }
        serialized_request = {
            "model": plan["model_identity_binding"]["model_id"],
            "messages": [],
            "tools": [{"type": "function", "function": {"name": row["exposed_name"]}} for row in registry["tools"]],
            "tool_choice": "auto",
            "temperature": 0.0,
        }
        trace_content = {
            "serialized_request_sha256": _sha256(serialized_request),
            "model_response_identity": response,
            "model_originated_tool_call_ids": [],
        }
        typed_pre_state = {"test": "pre"}
        record = {
            "episode_id": plan["episode_id"],
            "result_status": "completed",
            "manifest_sha256": self.bundle["manifest_sha256"],
            "pair_id": plan["pair_id"],
            "case_id": plan["case_id"],
            "stratum_id": plan["stratum_id"],
            "user_task_id": plan["user_task_id"],
            "arm": plan["arm"],
            "defense_id": plan["defense_id"],
            "defense_configuration_sha256": plan["defense_configuration_sha256"],
            "policy_manifest_sha256": plan["policy_manifest_sha256"],
            "model_configuration_id": plan["model_configuration_id"],
            "seed": plan["seed"],
            "contract_version": plan["contract"]["version"],
            "effect_oracle_contract_sha256": plan["effect_oracle_contract_sha256"],
            "attempt_index": 1,
            "automatic_retry": False,
            "run_id": "test-run",
            "source_verification_witness": self.manifest["source"]["agentdojo"]["verification_witness"],
            "oracle_implementation_sha256": _hash("d"),
            "state_schema_version": plan["state_schema_version"],
            "typed_pre_state": typed_pre_state,
            "typed_post_state": {"test": "post", "mock_harm": endpoint_marker},
            "reset_witness": {"verified": True, "pre_state_sha256": _hash("e")},
            "terminal_status": "completed",
            "failure_flags": {"runner_error": False, "tool_error": False, "timeout": False, "cancelled": False},
            "model_response_identity": response,
            "serialized_request": serialized_request,
            "serialized_request_sha256": _sha256(serialized_request),
            "request_parameters_sent": dict(serialized_request),
            "redacted_trace": {
                "schema_version": "agentdojo-redacted-trace/v1",
                "sha256": _sha256(trace_content),
                "redaction_applied": True,
                "redaction_policy_sha256": _hash("2"),
                "content": trace_content,
                "model_request_observed": True,
                "model_response_observed": True,
                "model_originated_tool_call_ids": [],
                "tool_dispatch_provenance": "dispatcher_trace",
            },
            "registry_witness": registry,
            "ground_truth_tool_execution": False,
            # A runner-supplied endpoint is deliberately opposite to the mocked
            # independent oracle below, proving it cannot drive the result.
            "harmful_effect_observed": not endpoint_marker,
        }
        if plan["contract"]["version"] == "v0":
            record["contract_migration_witness_or_absence"] = {"status": "not_applied"}
        else:
            before = self._matching_registry(plan, version="v0", semantic=semantic)
            record["contract_migration_witness_or_absence"] = {
                "status": "applied",
                "witness": {
                    "schema_version": "agentdojo-tool-contract-migration/v1",
                    "contract_sha256": plan["contract"]["tool_contract_digest"],
                    "semantic_schema_preserved": True,
                    "implementation_objects_preserved": True,
                    "before": before,
                    "after": registry,
                },
            }
        if plan["arm"] == "attack":
            injection = plan["attack_or_benign_binding"]["injection"]
            record["carrier_materialization_witness"] = {
                "mode": injection["mode"],
                "injection_task_id": injection["injection_task_id"],
                "carrier_id": injection["carrier_id"],
                "materialized": True,
                "materialized_before_agent": True,
                "pre_agent_state_sha256": _sha256(typed_pre_state),
                "materialization_artifact": {
                    "content": {
                        "injection_task_id": injection["injection_task_id"],
                        "carrier_id": injection["carrier_id"],
                        "pre_agent_state_sha256": _sha256(typed_pre_state),
                    },
                },
            }
            artifact = record["carrier_materialization_witness"]["materialization_artifact"]
            artifact["sha256"] = _sha256(artifact["content"])
        else:
            record["no_injection_witness"] = {
                "mode": "none",
                "injecagent_invoked": False,
                "carrier_present": False,
                "materialized_before_agent": True,
            }
        return record

    def _replace(self, record: dict) -> None:
        for index, row in enumerate(self.bundle["episodes"]):
            if row["episode_id"] == record["episode_id"]:
                self.bundle["episodes"][index] = record
                return
        self.fail("planned result row absent")

    def test_template_has_complete_fixed_denominator_and_no_execution(self):
        with patch.dict(os.environ, {"RUNPOD_API_KEY": "must-not-be-read"}, clear=False), patch(
            "subprocess.run", side_effect=AssertionError("result template must not spawn a process")
        ), patch("urllib.request.urlopen", side_effect=AssertionError("result template must not use the network")):
            first = build_result_bundle_template(self.manifest)
            second = build_result_bundle_template(self.manifest)
        self.assertEqual(first, second)
        self.assertEqual(first["claim_tier"], CLAIM_TIER)
        self.assertEqual(len(first["episodes"]), 12)
        report = validate_and_summarize_bundle(first, manifest=self.manifest)
        self.assertEqual(report["summary"]["fixed_denominator"]["pair_count"], 6)
        self.assertEqual(report["summary"]["attack"]["valid_pair_count"], 0)
        self.assertEqual(report["summary"]["attack"]["security_regression_pair_count"], 0)

    def test_v1_only_attack_cannot_become_a_regression(self):
        v1 = next(plan for plan in self.by_id.values() if plan["arm"] == "attack" and plan["contract"]["version"] == "v1")
        self._replace(self._complete_record(v1, endpoint_marker=True))
        with patch("experiments.agentdojo_paired_result_bundle.score_attack_episode") as scorer:
            scorer.return_value = {"score_status": "scored", "harmful_effect_observed": True, "oracle_id": "test"}
            report = validate_and_summarize_bundle(self.bundle, manifest=self.manifest)
        self.assertEqual(report["summary"]["attack"]["valid_pair_count"], 0)
        self.assertEqual(report["summary"]["attack"]["security_regression_pair_count"], 0)
        pair = next(row for row in report["summary"]["pairs"] if row["pair_id"] == v1["pair_id"])
        self.assertEqual(pair["not_scored_reason"], "missing_or_unscored_v0_or_v1_sibling")

    def test_attack_transition_uses_recomputed_oracle_not_runner_score(self):
        pair = next(
            (plan["pair_id"] for plan in self.by_id.values() if plan["arm"] == "attack"),
        )
        v0 = next(plan for plan in self.by_id.values() if plan["pair_id"] == pair and plan["contract"]["version"] == "v0")
        v1 = next(plan for plan in self.by_id.values() if plan["pair_id"] == pair and plan["contract"]["version"] == "v1")
        self._replace(self._complete_record(v0, endpoint_marker=False, semantic="a"))
        self._replace(self._complete_record(v1, endpoint_marker=True, semantic="a"))

        def independent_oracle(_contract, _case_id, evidence):
            return {
                "score_status": "scored",
                "harmful_effect_observed": evidence["typed_post_state"]["mock_harm"],
                "oracle_id": "test-only-independent-oracle",
                "post_state_sha256": _hash("7"),
            }

        with patch("experiments.agentdojo_paired_result_bundle.score_attack_episode", side_effect=independent_oracle):
            report = validate_and_summarize_bundle(self.bundle, manifest=self.manifest)
        self.assertEqual(report["summary"]["attack"]["valid_pair_count"], 1)
        self.assertEqual(report["summary"]["attack"]["transition_counts"]["01"], 1)
        self.assertEqual(report["summary"]["attack"]["security_regression_pair_count"], 1)
        self.assertEqual(report["statistical_status"], "descriptive_only_no_population_inference")

    def test_benign_rows_are_blocked_until_arm_specific_prestate_and_oracle_are_pinned(self):
        pair = next(plan["pair_id"] for plan in self.by_id.values() if plan["arm"] == "benign")
        for plan in (row for row in self.by_id.values() if row["pair_id"] == pair):
            self._replace(self._complete_record(plan, semantic="a"))
        report = validate_and_summarize_bundle(self.bundle, manifest=self.manifest)
        rows = [row for row in report["episodes"] if row["pair_id"] == pair]
        self.assertEqual({row["not_scored_reason"] for row in rows}, {"benign_initial_state_not_pinned"})
        self.assertTrue(all("benign_utility_oracle_not_pinned" in row["additional_blockers"] for row in rows))
        self.assertEqual(report["summary"]["benign"]["valid_pair_count"], 0)

    def test_duplicate_episode_fails_closed(self):
        v0 = next(plan for plan in self.by_id.values() if plan["arm"] == "attack" and plan["contract"]["version"] == "v0")
        record = self._complete_record(v0, semantic="a")
        self._replace(record)
        self.bundle["episodes"].append(copy.deepcopy(record))
        report = validate_and_summarize_bundle(self.bundle, manifest=self.manifest)
        row = next(row for row in report["episodes"] if row["episode_id"] == v0["episode_id"])
        self.assertEqual(row["not_scored_reason"], "bundle_contract:unexpected_or_duplicate_episode_records")
        self.assertEqual(report["bundle_contract_error"], "unexpected_or_duplicate_episode_records")
        self.assertEqual(report["summary"]["attack"]["valid_pair_count"], 0)

    def test_content_bound_request_and_registry_descriptor_tampering_fail_closed(self):
        v0 = next(plan for plan in self.by_id.values() if plan["arm"] == "attack" and plan["contract"]["version"] == "v0")
        for label, mutate, expected_reason in (
            (
                "request",
                lambda record: record["serialized_request"].update({"messages": ["tampered"]}),
                "serialized_request_content_or_digest_mismatch",
            ),
            (
                "descriptor",
                lambda record: record["registry_witness"]["tools"][0]["semantic_descriptor"].update({"tampered": True}),
                "registry_semantic_descriptor_or_digest_mismatch",
            ),
            (
                "trace",
                lambda record: record["redacted_trace"]["content"].update({"tampered": True}),
                "redacted_trace_content_or_digest_mismatch",
            ),
        ):
            with self.subTest(label=label):
                record = self._complete_record(v0, semantic="a")
                mutate(record)
                self._replace(record)
                report = validate_and_summarize_bundle(self.bundle, manifest=self.manifest)
                row = next(row for row in report["episodes"] if row["episode_id"] == v0["episode_id"])
                self.assertEqual(row["not_scored_reason"], expected_reason)
                self.bundle = build_result_bundle_template(self.manifest)

    def test_mismatched_pair_semantic_registry_cannot_be_scored(self):
        pair = next(plan["pair_id"] for plan in self.by_id.values() if plan["arm"] == "attack")
        v0 = next(plan for plan in self.by_id.values() if plan["pair_id"] == pair and plan["contract"]["version"] == "v0")
        v1 = next(plan for plan in self.by_id.values() if plan["pair_id"] == pair and plan["contract"]["version"] == "v1")
        self._replace(self._complete_record(v0, endpoint_marker=False, semantic="a"))
        self._replace(self._complete_record(v1, endpoint_marker=True, semantic="d"))

        with patch("experiments.agentdojo_paired_result_bundle.score_attack_episode") as scorer:
            scorer.side_effect = [
                {"score_status": "scored", "harmful_effect_observed": False, "oracle_id": "test"},
                {"score_status": "scored", "harmful_effect_observed": True, "oracle_id": "test"},
            ]
            report = validate_and_summarize_bundle(self.bundle, manifest=self.manifest)
        pair_report = next(row for row in report["summary"]["pairs"] if row["pair_id"] == pair)
        self.assertEqual(pair_report["pair_status"], "not_scored")
        self.assertEqual(pair_report["not_scored_reason"], "paired_semantic_registry_mismatch")
        self.assertEqual(report["summary"]["attack"]["security_regression_pair_count"], 0)


if __name__ == "__main__":
    unittest.main()
