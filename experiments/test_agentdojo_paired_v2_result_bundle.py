"""Regression checks for the fail-closed prospective v2 result bundle."""

from __future__ import annotations

import copy
import os
import unittest
from unittest.mock import patch

try:
    from experiments.agentdojo_paired_v2_execution_manifest import DEFAULT_CONTROL_ARM, DEFAULT_OUTPUT, load_manifest
    from experiments.agentdojo_paired_v2_result_bundle import (
        CLAIM_TIER,
        _sha256,
        build_result_bundle_template,
        validate_and_summarize_bundle,
    )
    from experiments.agentdojo_v2_no_injecagent_default_control_contract import load_contract as load_default_control
    from experiments.agentdojo_v2_utility_trace_normalization_contract import _tool_mapping, normalize_trace
except ModuleNotFoundError:  # direct python experiments/test_*.py support
    from agentdojo_paired_v2_execution_manifest import DEFAULT_CONTROL_ARM, DEFAULT_OUTPUT, load_manifest
    from agentdojo_paired_v2_result_bundle import CLAIM_TIER, _sha256, build_result_bundle_template, validate_and_summarize_bundle
    from agentdojo_v2_no_injecagent_default_control_contract import load_contract as load_default_control
    from agentdojo_v2_utility_trace_normalization_contract import _tool_mapping, normalize_trace


def _hash(character: str) -> str:
    return character * 64


class AgentDojoPairedV2ResultBundleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = load_manifest(DEFAULT_OUTPUT)
        cls.default_control = load_default_control()
        cls.trace_contract = cls._load_trace_contract()
        cls.v0_name, cls.v1_name = next(iter(_tool_mapping().items()))

    def setUp(self) -> None:
        self.bundle = build_result_bundle_template(self.manifest)
        self.by_id = {row["episode_id"]: row for row in self.manifest["episodes"]}

    def _matching_registry(self, plan: dict, *, version: str | None = None, semantic: str = "a") -> dict:
        from experiments.agentdojo_contract_migration import load_contract
        from experiments.agentdojo_paired_v2_execution_manifest import TOOL_CONTRACT

        mapping = load_contract(TOOL_CONTRACT)["migration"]["v0_to_v1"]
        selected_version = version or plan["contract"]["version"]
        expected = {name: name for name in mapping} if selected_version == "v0" else {new: old for old, new in mapping.items()}
        names = sorted(expected)
        tools, semantic_rows = [], []
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
            {key: row[key] for key in ("exposed_name", "canonical_name", "semantic_sha256")} for row in tools
        ]
        return {
            "semantic_registry_sha256": _sha256(semantic_rows),
            "exposed_registry_sha256": _sha256(exposed_rows),
            "tool_count": len(names),
            "tools": tools,
        }

    def _common_record(self, plan: dict, *, semantic: str = "a") -> tuple[dict, dict]:
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
        request_records = [
            {
                "ordinal": 0,
                "serialized_request": serialized_request,
                "serialized_request_sha256": _sha256(serialized_request),
                "request_parameters_sent": dict(serialized_request),
                "response_sha256": _hash("a"),
                "response_identity": response,
                "model_originated_tool_call_ids": [],
            }
        ]
        trace_content = {
            "serialized_request_sha256": _sha256(serialized_request),
            "model_response_identity": response,
            "model_response_identities": [response],
            "model_originated_tool_call_ids": [],
            "model_originated_tool_call_count": 0,
            "request_count": 1,
            "request_sha256s": [_sha256(serialized_request)],
            "response_count": 1,
            "response_sha256s": [_hash("a")],
            "response_ids": [None],
            "model_request_records_sha256": _sha256(request_records),
            "dispatcher_trace_sha256": _sha256([]),
            "dispatcher_event_count": 0,
            "dispatch_provenance_gate": (
                "digest_and_count_only; retain a per-dispatch redacted commitment before any "
                "security-or-utility efficacy claim"
            ),
        }
        record = {
            "episode_id": plan["episode_id"],
            "result_status": "completed",
            "manifest_sha256": self.bundle["manifest_sha256"],
            "pair_id": plan["pair_id"],
            "case_id": plan["case_id"],
            "source_cluster_id": plan["source_cluster_id"],
            "stratum_id": plan["stratum_id"],
            "user_task_id": plan["user_task_id"],
            "arm": plan["arm"],
            "defense_id": plan["defense_id"],
            "defense_configuration_sha256": plan["defense_configuration_sha256"],
            "policy_manifest_sha256": plan["policy_manifest_sha256"],
            "model_configuration_id": plan["model_configuration_id"],
            "seed": plan["seed"],
            "contract_version": plan["contract"]["version"],
            "arm_binding_sha256": plan["arm_binding_sha256"],
            "expected_pre_state_sha256": plan["expected_pre_state_sha256"],
            "effect_oracle_contract_sha256": plan["effect_oracle_contract_sha256"],
            "default_control_contract_sha256": plan["default_control_contract_sha256"],
            "trace_normalization_contract_sha256": plan["trace_normalization_contract_sha256"],
            "attempt_index": 1,
            "automatic_retry": False,
            "run_id": "test-run",
            "runtime_identity_witness": dict(plan["runtime_identity"]),
            "pythonpath_witness": {
                "schema_version": "agentdojo-v2-pythonpath-witness/v1",
                "entries": ["<repository-root>", "<agentdojo-source>/src"],
                "entry_count": 2,
                "entries_sha256": _hash("c"),
            },
            "typed_pre_state": {"test": "pre"},
            "typed_post_state": {"test": "post"},
            "reset_witness": {"verified": True, "pre_state_sha256": _hash("e")},
            "terminal_status": "completed",
            "failure_flags": {"runner_error": False, "tool_error": False, "timeout": False, "cancelled": False},
            "model_response_identity": response,
            "model_request_records": request_records,
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
            "execution_budget_witness": {
                "schema_version": "agentdojo-execution-budget-witness/v1",
                "max_model_requests_per_episode": plan["execution_budget"]["max_model_requests_per_episode"],
                "max_tool_calls_per_episode": plan["execution_budget"]["max_tool_calls_per_episode"],
                "model_request_count": 1,
                "model_tool_call_count": 0,
                "tool_dispatch_count": 0,
                "overflow": False,
            },
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
        return record, registry

    def _complete_record(self, plan: dict, *, semantic: str = "a") -> dict:
        record, _ = self._common_record(plan, semantic=semantic)
        if plan["arm"] == "attack":
            record.update(
                {
                    "source_verification_witness": self.manifest["source"]["agentdojo"]["verification_witness"],
                    "oracle_implementation_sha256": _hash("d"),
                    "state_schema_version": "agentdojo-workspace-state-json/v1",
                    "carrier_materialization_witness": {
                        "mode": plan["arm_binding"]["injection"]["mode"],
                        "injection_task_id": plan["arm_binding"]["injection"]["injection_task_id"],
                        "carrier_id": plan["arm_binding"]["injection"]["carrier_id"],
                        "materialized": True,
                        "materialized_before_agent": True,
                        "pre_agent_state_sha256": _sha256(record["typed_pre_state"]),
                    },
                }
            )
            artifact = {
                "injection_task_id": record["carrier_materialization_witness"]["injection_task_id"],
                "carrier_id": record["carrier_materialization_witness"]["carrier_id"],
                "pre_agent_state_sha256": record["carrier_materialization_witness"]["pre_agent_state_sha256"],
            }
            record["carrier_materialization_witness"]["materialization_artifact"] = {
                "content": artifact,
                "sha256": _sha256(artifact),
            }
            record["harmful_effect_observed"] = True
            return record

        control_binding = plan["arm_binding"]["default_control_contract"]
        raw_name = self.v0_name if plan["contract"]["version"] == "v0" else self.v1_name
        raw_trace = [{"function": raw_name, "args": {"test": "argument"}, "id": None, "placeholder_args": None}]
        canonical_trace, normalization_witness = normalize_trace(self.trace_contract, plan["contract"]["version"], raw_trace)
        record.update(
            {
                "source_verification_witness": self.default_control["source"]["verification_witness"],
                "utility_oracle_implementation_sha256": self.default_control["utility_oracle_implementation"]["sha256"],
                "state_schema_version": "agentdojo-workspace-state-json/v1",
                # Keep test records isolated from the manifest. Mutation tests
                # intentionally corrupt this witness and must not alter the
                # pinned plan used by later validation calls.
                "no_injecagent_default_control_witness": copy.deepcopy(control_binding["control_witness"]),
                "terminal_output": "test-only-output",
                "function_trace": canonical_trace,
                "raw_function_trace": raw_trace,
                "canonical_function_trace": canonical_trace,
                "trace_normalization_witness": normalization_witness,
                "utility_success": False,
            }
        )
        trace_content = record["redacted_trace"]["content"]
        trace_content["raw_function_trace_sha256"] = normalization_witness["raw_trace_sha256"]
        trace_content["canonical_function_trace_sha256"] = normalization_witness["canonical_trace_sha256"]
        record["redacted_trace"]["sha256"] = _sha256(trace_content)
        return record

    @staticmethod
    def _load_trace_contract() -> dict:
        from experiments.agentdojo_v2_utility_trace_normalization_contract import load_contract

        return load_contract()

    def _replace(self, record: dict) -> None:
        for index, row in enumerate(self.bundle["episodes"]):
            if row["episode_id"] == record["episode_id"]:
                self.bundle["episodes"][index] = record
                return
        self.fail("planned row absent")

    def test_template_has_full_denominator_and_zero_observations(self) -> None:
        with patch.dict(os.environ, {"RUNPOD_API_KEY": "must-not-be-read"}, clear=False):
            template = build_result_bundle_template(self.manifest)
        self.assertEqual(template["claim_tier"], CLAIM_TIER)
        self.assertEqual(len(template["episodes"]), 12)
        report = validate_and_summarize_bundle(template, manifest=self.manifest)
        self.assertEqual(report["summary"]["fixed_denominator"]["pair_count"], 6)
        self.assertEqual(report["summary"]["attack"]["valid_pair_count"], 0)
        self.assertEqual(report["summary"]["default_control"]["valid_pair_count"], 0)

    def test_default_control_pair_uses_normalized_trace_and_recomputed_oracle(self) -> None:
        pair = next(plan["pair_id"] for plan in self.by_id.values() if plan["arm"] == DEFAULT_CONTROL_ARM)
        v0 = next(plan for plan in self.by_id.values() if plan["pair_id"] == pair and plan["contract"]["version"] == "v0")
        v1 = next(plan for plan in self.by_id.values() if plan["pair_id"] == pair and plan["contract"]["version"] == "v1")
        self._replace(self._complete_record(v0))
        self._replace(self._complete_record(v1))

        def oracle(_contract, _case_id, evidence, _source):
            return {
                "score_status": "scored",
                "utility_success": evidence["terminal_output"] == "test-only-output" and _case_id == v0["case_id"],
                "utility_oracle_id": "test-only-upstream-utility",
                "post_state_sha256": _hash("7"),
            }

        with patch("experiments.agentdojo_paired_v2_result_bundle.score_default_control_episode", side_effect=oracle):
            report = validate_and_summarize_bundle(self.bundle, manifest=self.manifest)
        pair_report = next(row for row in report["summary"]["pairs"] if row["pair_id"] == pair)
        self.assertEqual(pair_report["pair_status"], "scored")
        self.assertEqual(pair_report["transition"], "11")
        self.assertEqual(report["summary"]["default_control"]["valid_pair_count"], 1)
        self.assertEqual(report["summary"]["default_control"]["utility_regression_pair_count"], 0)

    def test_runner_utility_boolean_and_v1_only_result_cannot_define_transition(self) -> None:
        v1 = next(
            plan for plan in self.by_id.values() if plan["arm"] == DEFAULT_CONTROL_ARM and plan["contract"]["version"] == "v1"
        )
        record = self._complete_record(v1)
        record["utility_success"] = True
        self._replace(record)
        with patch("experiments.agentdojo_paired_v2_result_bundle.score_default_control_episode") as oracle:
            oracle.return_value = {
                "score_status": "scored",
                "utility_success": False,
                "utility_oracle_id": "recomputed",
                "post_state_sha256": _hash("7"),
            }
            report = validate_and_summarize_bundle(self.bundle, manifest=self.manifest)
        pair = next(row for row in report["summary"]["pairs"] if row["pair_id"] == v1["pair_id"])
        self.assertEqual(pair["pair_status"], "not_scored")
        self.assertEqual(pair["not_scored_reason"], "missing_or_unscored_v0_or_v1_sibling")

    def test_default_control_without_verified_source_remains_not_scored(self) -> None:
        pair = next(plan["pair_id"] for plan in self.by_id.values() if plan["arm"] == DEFAULT_CONTROL_ARM)
        for plan in (row for row in self.by_id.values() if row["pair_id"] == pair):
            self._replace(self._complete_record(plan))
        report = validate_and_summarize_bundle(self.bundle, manifest=self.manifest)
        rows = [row for row in report["episodes"] if row["pair_id"] == pair]
        self.assertEqual(
            {row["not_scored_reason"] for row in rows},
            {"default_control_oracle:source_verification_required"},
        )

    def _assert_default_control_failure(self, mutate, expected: str) -> None:
        plan = next(plan for plan in self.by_id.values() if plan["arm"] == DEFAULT_CONTROL_ARM)
        record = self._complete_record(plan)
        mutate(record)
        self._replace(record)
        report = validate_and_summarize_bundle(self.bundle, manifest=self.manifest)
        row = next(row for row in report["episodes"] if row["episode_id"] == plan["episode_id"])
        self.assertEqual(row["not_scored_reason"], expected)

    def test_default_control_rejects_missing_normalization_witness(self) -> None:
        self._assert_default_control_failure(
            lambda record: record.pop("trace_normalization_witness"),
            "missing_required_driver_evidence:trace_normalization_witness",
        )

    def test_default_control_rejects_wrong_canonical_trace(self) -> None:
        self._assert_default_control_failure(
            lambda record: record.update({"canonical_function_trace": []}),
            "trace_normalization_witness_mismatch",
        )

    def test_default_control_rejects_wrong_control_witness(self) -> None:
        self._assert_default_control_failure(
            lambda record: record["no_injecagent_default_control_witness"].update({"injecagent_invoked": True}),
            "default_control_witness_mismatch",
        )

    def test_default_control_rejects_unlinked_dispatcher_trace(self) -> None:
        def mutate(record: dict) -> None:
            record["redacted_trace"]["content"]["raw_function_trace_sha256"] = "0" * 64
            record["redacted_trace"]["sha256"] = _sha256(record["redacted_trace"]["content"])

        self._assert_default_control_failure(mutate, "dispatcher_trace_normalization_provenance_mismatch")

    def test_arm_binding_tampering_fails_closed(self) -> None:
        plan = next(iter(self.by_id.values()))
        record = self._complete_record(plan)
        record["arm_binding_sha256"] = "0" * 64
        self._replace(record)
        report = validate_and_summarize_bundle(self.bundle, manifest=self.manifest)
        row = next(row for row in report["episodes"] if row["episode_id"] == plan["episode_id"])
        self.assertEqual(row["not_scored_reason"], "immutable_metadata_mismatch:arm_binding_sha256")

    def test_expected_prestate_tampering_fails_closed(self) -> None:
        plan = next(iter(self.by_id.values()))
        record = self._complete_record(plan)
        record["expected_pre_state_sha256"] = "0" * 64
        self._replace(record)
        report = validate_and_summarize_bundle(self.bundle, manifest=self.manifest)
        row = next(row for row in report["episodes"] if row["episode_id"] == plan["episode_id"])
        self.assertEqual(row["not_scored_reason"], "immutable_metadata_mismatch:expected_pre_state_sha256")

    def test_attack_pair_uses_independent_effect_oracle(self) -> None:
        pair = next(plan["pair_id"] for plan in self.by_id.values() if plan["arm"] == "attack")
        v0 = next(plan for plan in self.by_id.values() if plan["pair_id"] == pair and plan["contract"]["version"] == "v0")
        v1 = next(plan for plan in self.by_id.values() if plan["pair_id"] == pair and plan["contract"]["version"] == "v1")
        self._replace(self._complete_record(v0))
        self._replace(self._complete_record(v1))

        def oracle(_contract, _case_id, evidence):
            return {
                "score_status": "scored",
                "harmful_effect_observed": evidence["typed_post_state"]["test"] == "post" and _case_id == v1["case_id"],
                "oracle_id": "test-only-effect",
                "post_state_sha256": _hash("7"),
            }

        with patch("experiments.agentdojo_paired_v2_result_bundle.score_attack_episode", side_effect=oracle):
            report = validate_and_summarize_bundle(self.bundle, manifest=self.manifest)
        pair_report = next(row for row in report["summary"]["pairs"] if row["pair_id"] == pair)
        self.assertEqual(pair_report["pair_status"], "scored")
        self.assertEqual(pair_report["transition"], "11")

    def test_cluster_and_runtime_witness_are_manifest_bound(self):
        plan = next(iter(self.by_id.values()))
        mutations = [
            (lambda r: r.update(source_cluster_id="fabricated"), "immutable_metadata_mismatch:source_cluster_id"),
            (lambda r: r["runtime_identity_witness"].update(openai_version="wrong"), "runtime_identity_witness_mismatch"),
            (lambda r: r["pythonpath_witness"].update(entries=[]), "pythonpath_witness_mismatch"),
        ]
        for mutate, expected in mutations:
            with self.subTest(expected=expected):
                self.bundle = build_result_bundle_template(self.manifest)
                record = self._complete_record(plan)
                mutate(record)
                self._replace(record)
                report = validate_and_summarize_bundle(self.bundle, manifest=self.manifest)
                row = next(r for r in report["episodes"] if r["episode_id"] == plan["episode_id"])
                self.assertEqual(row["not_scored_reason"], expected)

    def test_duplicate_or_wrong_contract_digest_fails_closed(self) -> None:
        plan = next(iter(self.by_id.values()))
        record = self._complete_record(plan)
        self._replace(record)
        self.bundle["episodes"].append(copy.deepcopy(record))
        report = validate_and_summarize_bundle(self.bundle, manifest=self.manifest)
        self.assertEqual(report["bundle_contract_error"], "unexpected_or_duplicate_episode_records")
        self.bundle = build_result_bundle_template(self.manifest)
        self.bundle["default_control_contract_sha256"] = "0" * 64
        report = validate_and_summarize_bundle(self.bundle, manifest=self.manifest)
        self.assertEqual(report["bundle_contract_error"], "default_control_contract_digest_mismatch")

    def test_multiple_model_requests_are_fully_bound_and_scored(self) -> None:
        plan = next(plan for plan in self.by_id.values() if plan["arm"] == "attack")
        record = self._complete_record(plan)
        second = copy.deepcopy(record["model_request_records"][0])
        second["ordinal"] = 1
        second["serialized_request"]["messages"] = [{"role": "assistant", "content": "follow-up"}]
        second["serialized_request_sha256"] = _sha256(second["serialized_request"])
        second["request_parameters_sent"] = dict(second["serialized_request"])
        second["response_sha256"] = _hash("b")
        record["model_request_records"].append(second)
        record["execution_budget_witness"]["model_request_count"] = 2
        trace_content = record["redacted_trace"]["content"]
        trace_content.update(
            {
                "model_response_identities": [
                    item["response_identity"] for item in record["model_request_records"]
                ],
                "request_count": 2,
                "request_sha256s": [
                    item["serialized_request_sha256"] for item in record["model_request_records"]
                ],
                "response_count": 2,
                "response_sha256s": [item["response_sha256"] for item in record["model_request_records"]],
                "response_ids": [
                    item["response_identity"].get("response_id") for item in record["model_request_records"]
                ],
                "model_request_records_sha256": _sha256(record["model_request_records"]),
            }
        )
        record["redacted_trace"]["sha256"] = _sha256(trace_content)
        self._replace(record)
        with patch(
            "experiments.agentdojo_paired_v2_result_bundle.score_attack_episode",
            return_value={
                "score_status": "scored",
                "harmful_effect_observed": False,
                "oracle_id": "test-only-effect",
                "post_state_sha256": _hash("7"),
            },
        ):
            report = validate_and_summarize_bundle(self.bundle, manifest=self.manifest)
        row = next(item for item in report["episodes"] if item["episode_id"] == plan["episode_id"])
        self.assertEqual(row["score_status"], "scored")

    def test_multiple_model_requests_without_per_request_binding_fail_closed(self) -> None:
        plan = next(plan for plan in self.by_id.values() if plan["arm"] == "attack")
        record = self._complete_record(plan)
        record["execution_budget_witness"]["model_request_count"] = 2
        record["redacted_trace"]["content"]["request_count"] = 2
        record["redacted_trace"]["sha256"] = _sha256(record["redacted_trace"]["content"])
        self._replace(record)
        report = validate_and_summarize_bundle(self.bundle, manifest=self.manifest)
        row = next(item for item in report["episodes"] if item["episode_id"] == plan["episode_id"])
        self.assertEqual(row["not_scored_reason"], "model_request_records_count_mismatch")


if __name__ == "__main__":
    unittest.main()
