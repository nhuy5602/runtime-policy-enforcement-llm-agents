"""Fail-closed tests for the prospective TaskFileScope amendment."""

from __future__ import annotations

import copy
import json
import os
import subprocess
import unittest
from pathlib import Path

from experiments.agentdojo_file_scope_amendment import (
    DEFAULT_OUTPUT,
    build_manifest,
    validate_manifest,
    validate_preflight_report,
)
ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "tmp" / "agentdojo-source"
PINNED = SOURCE / ".venv31213" / "Scripts" / "python.exe"


@unittest.skipUnless(SOURCE.is_dir(), "pinned AgentDojo source checkout required")
class FileScopeAmendmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = json.loads(DEFAULT_OUTPUT.read_text(encoding="utf-8"))
        report_path = ROOT / "qa" / ".file_scope_amendment_test_preflight.json"
        try:
            completed = subprocess.run(
                [str(PINNED), "-B", "-m", "experiments.agentdojo_file_scope_preflight",
                 "--output", str(report_path)],
                cwd=ROOT,
                env={**os.environ, "PYTHONUTF8": "0", "PYTHONIOENCODING": "utf-8"},
                capture_output=True, text=True, encoding="utf-8", timeout=120,
            )
            if completed.returncode != 0:
                raise RuntimeError(completed.stderr or completed.stdout)
            cls.report = json.loads(report_path.read_text(encoding="utf-8"))
        finally:
            report_path.unlink(missing_ok=True)

    def test_fixture_is_deterministic_and_distinct_from_historical_v2(self) -> None:
        self.assertEqual(self.manifest, build_manifest())
        self.assertEqual(validate_manifest(self.manifest)["cell_count"], 4)
        self.assertEqual(self.manifest["schema_version"], "agentdojo-file-scope-fm-amendment/v1")
        from experiments.agentdojo_paired_v2_execution_manifest import load_manifest, DEFAULT_OUTPUT as V2
        historical = load_manifest(V2)
        self.assertEqual(historical["schema_version"], "agentdojo-paired-v0-v1-execution-manifest/v2")

    def test_source_preflight_is_accepted(self) -> None:
        result = validate_preflight_report(self.manifest, self.report)
        self.assertEqual(result["utility_sequence"], [True, False, True, True])
        self.assertEqual(result["claim_tier"], "T1_source_conformance_only")
        self.assertEqual(result["cell_count"], 4)

    def test_missing_or_crossing_denial_evidence_fails_closed(self) -> None:
        tampered = copy.deepcopy(self.report)
        denied = next(
            event
            for row in tampered["cells"]
            for event in row["policy_events"]
            if event["decision"] == "DENY"
        )
        denied["dispatched"] = True
        with self.assertRaises(ValueError):
            validate_preflight_report(self.manifest, tampered)

    def test_schema_and_policy_tampering_fail_closed(self) -> None:
        for mutate in (
            lambda report: report["cells"][1].update({"exposed_parameter_schemas_sha256": "0" * 64}),
            lambda report: report["cells"][3].update({"policy_sha256": "0" * 64}),
            lambda report: report["cells"][1]["policy_events"][1].update({"post_state_sha256": "0" * 64}),
        ):
            tampered = copy.deepcopy(self.report)
            mutate(tampered)
            with self.assertRaises(ValueError):
                validate_preflight_report(self.manifest, tampered)


if __name__ == "__main__":
    unittest.main()
