import json
import unittest
from pathlib import Path

try:
    from experiments.independent_benchmark_runner import (
        DEFAULT_MANIFEST,
        build_command,
        load_manifest,
        smoke,
    )
except ModuleNotFoundError:  # direct ``python experiments/test_*.py`` support
    from independent_benchmark_runner import DEFAULT_MANIFEST, build_command, load_manifest, smoke


class IndependentBenchmarkManifestTests(unittest.TestCase):
    def test_manifest_is_pinned_and_smoke_is_honest(self):
        manifest = load_manifest(DEFAULT_MANIFEST)
        report = smoke(manifest, None)
        self.assertTrue(report["manifest_valid"])
        self.assertEqual(manifest["status"], "not_run")
        self.assertEqual(manifest["benchmarks"]["agentdojo"]["result_status"], "not_run")
        self.assertEqual(
            manifest["benchmarks"]["agentdojo"]["commit"],
            "089ed468cf3ed0322acc66b0211f26d9d90dbf60",
        )
        self.assertEqual(
            manifest["benchmarks"]["injecagent"]["commit"],
            "f19c9f2c79a41046eb13c03c51a24c567a8ffa07",
        )
        self.assertTrue(report["benchmarks"]["agentdojo"]["adapter_module_exists"])
        self.assertEqual(
            manifest["benchmarks"]["agentdojo"]["environment"]["lockfile_sha256"],
            "2B67DA5479A37727CBDCB39C57A9070F9264F3350237173B3EAE21CC12ED215A",
        )

    def test_commands_contain_no_secret(self):
        manifest = load_manifest(DEFAULT_MANIFEST)
        command = build_command(
            "agentdojo",
            manifest["benchmarks"]["agentdojo"],
            None,
            Path("out"),
        )
        rendered = json.dumps(command)
        self.assertIn("OPENAI_COMPATIBLE", rendered)
        self.assertIn("qwen/qwen3-8b", rendered)
        self.assertIn("module-to-load", rendered)
        self.assertNotIn("RUNPOD_API_KEY", rendered)

        locked_command = build_command(
            "agentdojo",
            manifest["benchmarks"]["agentdojo"],
            Path("benchmarks/agentdojo"),
            Path("out"),
        )
        self.assertIn("--locked", locked_command)

        smoke_command = build_command(
            "agentdojo",
            manifest["benchmarks"]["agentdojo"],
            None,
            Path("out"),
            track="baseline",
            user_task="user_task_0",
            injection_task="injection_task_0",
        )
        smoke_rendered = json.dumps(smoke_command)
        self.assertIn("--user-task", smoke_rendered)
        self.assertIn("user_task_0", smoke_rendered)
        self.assertIn("--injection-task", smoke_rendered)
        self.assertIn("injection_task_0", smoke_rendered)
        self.assertNotIn("module-to-load", smoke_rendered)

        baseline_command = build_command(
            "agentdojo",
            manifest["benchmarks"]["agentdojo"],
            None,
            Path("out"),
            track="baseline",
        )
        baseline_rendered = json.dumps(baseline_command)
        self.assertNotIn("module-to-load", baseline_rendered)
        self.assertIn("OPENAI_COMPATIBLE", baseline_rendered)

        injec_command = build_command(
            "injecagent",
            manifest["benchmarks"]["injecagent"],
            Path("source"),
            Path("out"),
        )
        self.assertIn("<missing:INJECAGENT_MODEL_NAME>", json.dumps(injec_command))


if __name__ == "__main__":
    unittest.main()
