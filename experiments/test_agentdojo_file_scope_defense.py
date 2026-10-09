"""TaskFileScope authorization checks; no attacks, providers or external tools."""

import json
import os
import subprocess
import unittest
from dataclasses import replace
from pathlib import Path

from experiments.agentdojo_file_scope_defense import FileScopePolicy, FileScopeRuntime, migrate_file_contract
from experiments.agentdojo_file_scope_preflight import canonical_trace


ROOT = Path(__file__).resolve().parents[1]
PINNED = ROOT / "tmp/agentdojo-source/.venv31213/Scripts/python.exe"
try:
    from agentdojo.functions_runtime import FunctionCall, FunctionsRuntime, make_function
    from agentdojo.default_suites.v1.tools.cloud_drive_client import append_to_file, get_file_by_id, search_files_by_filename
    NATIVE_AVAILABLE = True
except ImportError:
    NATIVE_AVAILABLE = False


@unittest.skipUnless(NATIVE_AVAILABLE, "optional AgentDojo runtime required")
class FileScopeDefenseTests(unittest.TestCase):
    def runtime(self, version="v0", migrated=False):
        base = FunctionsRuntime([make_function(fn) for fn in
                                 (append_to_file, get_file_by_id, search_files_by_filename)])
        if version == "v1":
            base = migrate_file_contract(base)
        policy = FileScopePolicy("task", "3", "team-building-activities.docx")
        if migrated:
            policy = replace(policy, argument_contract="v1")
        return FileScopeRuntime(base, policy)

    def test_denials_never_reach_native_dispatch(self):
        for version, migrated, args in (
            ("v0", False, {"file_id": "other"}),
            ("v0", False, {"file_id": "3", "extra": True}),
            ("v0", False, {"file_id": 3}),
            ("v0", False, {"file_id": FunctionCall(function="get_current_day", args={})}),
            ("v1", False, {"resource": {"space": "cloud_drive", "file_id": "3"}}),
            ("v1", True, {"resource": {"space": "wrong_space", "file_id": "3"}}),
            ("v1", True, {"resource": {"space": "cloud_drive", "file_id": "3", "extra": True}}),
            ("v1", True, {"file_id": "3"}),
        ):
            with self.subTest(version=version, migrated=migrated, args=args):
                runtime = self.runtime(version, migrated)
                # None cannot satisfy native dependencies: any dispatch would fail.
                response, error = runtime.run_function(None, "get_file_by_id", args, raise_on_error=True)
                self.assertIsNone(error)
                self.assertEqual(response["policy_decision"], "DENY")
                self.assertFalse(runtime.events[-1]["dispatched"])
        runtime = self.runtime()
        result, error = runtime.run_function(None, "get_current_day", {})
        self.assertEqual(result["policy_decision"], "DENY")
        self.assertIsNone(error)

    def test_migration_is_explicit_and_does_not_mutate_v0(self):
        runtime = self.runtime()
        original = runtime.functions["append_to_file"]
        migrated = migrate_file_contract(runtime)
        self.assertEqual(set(original.parameters.model_fields), {"file_id", "content"})
        self.assertEqual(set(migrated.functions["append_to_file"].parameters.model_fields), {"resource", "content"})
        with self.assertRaises(ValueError):
            migrate_file_contract(migrated)
        with self.assertRaises(TypeError):
            runtime.functions["new"] = original
        with self.assertRaises(ValueError):
            runtime.update_functions(migrated.functions)

    def test_native_tool_errors_are_not_policy_denials(self):
        from unittest.mock import Mock
        runtime = self.runtime()
        runtime._base.run_function = Mock(return_value=("", "ValueError: native failure"))
        result, error = runtime.run_function(None, "get_file_by_id", {"file_id": "3"})
        self.assertEqual(error, "ValueError: native failure")
        self.assertEqual(runtime.events[-1]["decision"], "ALLOW")
        self.assertTrue(runtime.events[-1]["tool_error"])
        self.assertEqual(runtime._base.run_function.call_count, 1)


class FileScopePreflightTests(unittest.TestCase):
    def test_normalizer_rejects_ambiguous_scope_without_mutating_raw(self):
        raw = [{"function": "append_to_file", "args": {
            "resource": {"space": "cloud_drive", "file_id": "3"}, "content": "activities",
        }}]
        normalized = canonical_trace("v1", raw)
        self.assertEqual(normalized[0]["args"], {"file_id": "3", "content": "activities"})
        self.assertIn("resource", raw[0]["args"])
        raw[0]["args"]["file_id"] = "other"
        with self.assertRaises(ValueError):
            canonical_trace("v1", raw)

    @unittest.skipUnless(PINNED.is_file(), "pinned Windows source runtime required")
    def test_four_cells_use_public_utility_scorer(self):
        probe = subprocess.run(
            [str(PINNED), "-B", "-m", "experiments.agentdojo_file_scope_preflight"],
            cwd=ROOT, env={**os.environ, "PYTHONUTF8": "0", "PYTHONIOENCODING": "utf-8"},
            capture_output=True, text=True, encoding="utf-8", timeout=120,
        )
        self.assertEqual(probe.returncode, 0, probe.stderr)
        report = json.loads(probe.stdout)
        self.assertEqual(report["cells"], {"F/v0": True, "F/v1": False, "M/v0": True, "M/v1": True})
        self.assertEqual(report["model_requests"], 0)
        self.assertEqual(report["evidence_tier"], "T1_source_conformance_only")


if __name__ == "__main__":
    unittest.main()
