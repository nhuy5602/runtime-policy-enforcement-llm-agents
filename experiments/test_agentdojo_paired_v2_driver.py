"""Focused checks for the canonical paired-v2 orchestration seam."""

from __future__ import annotations

import unittest
import shutil
import tempfile
from pathlib import Path

try:
    from experiments.agentdojo_paired_v2_driver import (
        budgeted_pilot_pair_ids,
        main,
        run_manifest,
    )
    from experiments.agentdojo_paired_v2_execution_manifest import DEFAULT_OUTPUT, load_manifest
    from experiments.agentdojo_paired_v2_result_bundle import validate_and_summarize_bundle
except ModuleNotFoundError:  # direct ``python experiments/test_*.py`` support
    from agentdojo_paired_v2_driver import budgeted_pilot_pair_ids, run_manifest
    from agentdojo_paired_v2_execution_manifest import DEFAULT_OUTPUT, load_manifest
    from agentdojo_paired_v2_result_bundle import validate_and_summarize_bundle


class AgentDojoPairedV2DriverTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = load_manifest(DEFAULT_OUTPUT)
        cls.episode_ids = [row["episode_id"] for row in cls.manifest["episodes"]]

    def test_runs_each_frozen_episode_once_in_manifest_order(self) -> None:
        seen: list[str] = []

        def executor(plan: dict) -> None:
            seen.append(plan["episode_id"])
            return None

        result = run_manifest(self.manifest, executor, run_id="driver-test")
        bundle, report = result["bundle"], result["report"]

        self.assertEqual(seen, self.episode_ids)
        self.assertEqual([row["episode_id"] for row in bundle["episodes"]], self.episode_ids)
        self.assertEqual(len(bundle["episodes"]), 12)
        self.assertEqual(report["summary"]["fixed_denominator"]["pair_count"], 6)
        self.assertTrue(all(row["result_status"] == "not_run" for row in bundle["episodes"]))
        self.assertTrue(all(row["run_id"] == "driver-test" for row in bundle["episodes"]))
        self.assertTrue(all(row["not_run_reason"] == "executor_returned_no_record" for row in bundle["episodes"]))
        self.assertIsNone(report["bundle_contract_error"])

    def test_executor_error_and_metadata_mismatch_fail_closed(self) -> None:
        seen: list[str] = []

        def executor(plan: dict) -> dict | None:
            seen.append(plan["episode_id"])
            if len(seen) == 1:
                raise RuntimeError("test failure")
            if len(seen) == 2:
                return {"result_status": "completed", "episode_id": "wrong"}
            return None

        bundle = run_manifest(self.manifest, executor, run_id="driver-test")["bundle"]

        self.assertEqual(seen, self.episode_ids)
        self.assertEqual(len(seen), len(set(seen)))
        self.assertEqual(len(bundle["episodes"]), 12)
        self.assertEqual(bundle["episodes"][0]["not_run_reason"], "executor_error:RuntimeError")
        self.assertEqual(
            bundle["episodes"][1]["not_run_reason"], "executor_metadata_mismatch:episode_id"
        )
        self.assertTrue(all(row["result_status"] == "not_run" for row in bundle["episodes"]))

    def test_no_executor_is_an_honest_zero_request_pilot_artifact(self) -> None:
        bundle = run_manifest(self.manifest, None, run_id="driver-test")["bundle"]

        self.assertEqual(bundle["driver_claim_tier"].startswith("integration/pilot"), True)
        self.assertEqual(bundle["pilot_budget"]["authorized_total_usd"], "10.00")
        self.assertEqual(bundle["pilot_budget"]["execution_envelope_usd"], "8.00")
        self.assertFalse(bundle["pilot_budget"]["provider_enforced_dollar_cap"])
        self.assertFalse(bundle["pilot_budget"]["paid_execution_authorized"])
        self.assertTrue(
            all(row["not_run_reason"] == "real_capture_bridge_not_supplied" for row in bundle["episodes"])
        )

    def test_dry_run_skips_executor_and_marks_every_episode(self) -> None:
        calls = 0

        def executor(plan: dict) -> dict:
            nonlocal calls
            calls += 1
            raise AssertionError("dry_run must not invoke the executor")

        result = run_manifest(self.manifest, executor, run_id="driver-test", dry_run=True)
        bundle = result["bundle"]

        self.assertEqual(calls, 0)
        self.assertEqual(bundle["result_status"], "integration_pilot_dry_run")
        self.assertTrue(all(row["not_run_reason"] == "dry_run" for row in bundle["episodes"]))

    def test_report_and_bundle_are_descriptive_not_live_efficacy(self) -> None:
        result = run_manifest(self.manifest, lambda plan: None, run_id="driver-report")
        bundle, report = result["bundle"], result["report"]
        validated = validate_and_summarize_bundle(bundle, manifest=self.manifest)

        self.assertEqual(validated["result_status"], "descriptive_only_bundle_validation")
        self.assertEqual(validated["statistical_status"], "descriptive_only_no_population_inference")
        self.assertTrue(any("efficacy" in claim.lower() for claim in validated["claims_not_supported"]))
        self.assertIn("pilot", str(bundle["driver_claim_tier"]).lower())
        self.assertIn("not real-agent", str(report["claim_tier"]).lower())
        self.assertIn("efficacy", str(report["claim_tier"]).lower())

    def test_budgeted_pilot_keeps_full_denominator_and_runs_four_rows(self) -> None:
        selected = budgeted_pilot_pair_ids(self.manifest)
        seen: list[str] = []

        def executor(plan: dict) -> dict:
            seen.append(plan["episode_id"])
            return {"result_status": "completed"}

        result = run_manifest(
            self.manifest,
            executor,
            run_id="pilot-filter",
            selected_pair_ids=selected,
        )
        bundle = result["bundle"]
        self.assertEqual(len(selected), 2)
        self.assertEqual(len(seen), 4)
        self.assertEqual(
            {row["pair_id"] for row in self.manifest["episodes"] if row["episode_id"] in seen},
            selected,
        )
        self.assertEqual(len(bundle["episodes"]), 12)
        self.assertEqual(
            sum(row.get("not_run_reason") == "pilot_pair_not_selected" for row in bundle["episodes"]),
            8,
        )

    def test_capture_mode_rejects_a_noncanonical_manifest_path(self) -> None:
        with tempfile.TemporaryDirectory(prefix="agentdojo-v2-manifest-copy-") as temp_dir:
            copied = Path(temp_dir) / "manifest.json"
            shutil.copyfile(DEFAULT_OUTPUT, copied)
            with self.assertRaises(SystemExit) as raised:
                main(
                    [
                        "--capture-bridge",
                        "--manifest",
                        str(copied),
                        "--bundle-output",
                        str(Path(temp_dir) / "bundle.json"),
                        "--run-id",
                        "canonical-manifest-test",
                    ]
                )
        self.assertEqual(raised.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
