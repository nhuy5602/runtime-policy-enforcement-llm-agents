"""Tests for the honest AgentDojo paired-smoke scorer."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from experiments.agentdojo_paired_scorer import _sha256, score_manifest, score_track


ROOT = Path(__file__).resolve().parents[1]


def _record(*, security: bool, tool: str = "get_current_day") -> dict[str, object]:
    return {
        "user_task_id": "user_task_0",
        "injection_task_id": "injection_task_0",
        "status": "completed",
        "utility": True,
        "security": security,
        "benchmark_version": "v1.2.2",
        "agentdojo_package_version": "0.1.35",
        "duration": 1.0,
        "messages": [
            {
                "role": "assistant",
                "tool_calls": [
                    {"function": tool, "args": {}, "id": "call-1"},
                ],
            },
            {
                "role": "tool",
                "tool_call": {"function": tool},
                "tool_call_id": "call-1",
                "error": None,
            },
        ],
    }


class AgentDojoPairedScorerTests(unittest.TestCase):
    def test_artifact_hash_normalizes_checkout_line_endings(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            lf = root / "lf.json"
            crlf = root / "crlf.json"
            lf.write_bytes(b'{"case":"smoke"}\n')
            crlf.write_bytes(b'{"case":"smoke"}\r\n')
            self.assertEqual(_sha256(lf), _sha256(crlf))

    def test_raw_security_true_is_attack_success(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "trace.json"
            path.write_text(json.dumps(_record(security=True)), encoding="utf-8")
            result = score_track(
                path,
                user_task="user_task_0",
                injection_task="injection_task_0",
                expected_attack_tool="send_email",
                track="baseline",
            )
        self.assertTrue(result["attack_success"])
        self.assertFalse(result["secure_outcome"])
        self.assertFalse(result["expected_attack_tool_proposed"])

    def test_manifest_writes_one_episode_descriptive_report(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for track, security in (("baseline", False), ("attested", False)):
                target = (
                    root
                    / track
                    / "openai-compatible"
                    / "workspace"
                    / "user_task_0"
                    / "injecagent"
                    / "injection_task_0.json"
                )
                target.parent.mkdir(parents=True)
                target.write_text(json.dumps(_record(security=security)), encoding="utf-8")
            manifest = {
                "result_status": "completed",
                "endpoint_id": "test",
                "model_id": "test-model",
                "user_task": "user_task_0",
                "injection_task": "injection_task_0",
                "baseline": {"output_dir": str(root / "baseline")},
                "attested": {"output_dir": str(root / "attested")},
            }
            manifest_path = root / "manifest.json"
            output_path = root / "score.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            report = score_manifest(manifest_path, output_path=output_path)
            self.assertTrue(report["descriptive_only"])
            self.assertEqual(report["independent_units"], 1)
            self.assertEqual(
                report["paired_delta_attested_minus_baseline"]["attack_success"], 0
            )
            self.assertTrue(output_path.exists())

    def test_committed_smoke_summary_matches_target_traces(self) -> None:
        summary_path = ROOT / "experiments" / "independent_runs" / "agentdojo_smoke_summary.json"
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        case = summary["paired_case"]
        for track, summary_key in (
            ("baseline", "baseline"),
            ("attested", "attested_wildcard"),
        ):
            source = summary["source_artifacts"][f"{track}_episode"]
            scored = score_track(
                ROOT / source["path"],
                user_task=case["user_task"],
                injection_task=case["injection_task"],
                expected_attack_tool=case["expected_attack_tool"],
                track=track,
            )
            self.assertEqual(scored["trace_sha256"], source["canonical_lf_sha256"])
            self.assertEqual(scored["utility"], summary[summary_key]["utility"])
            self.assertEqual(scored["attack_success"], summary[summary_key]["attack_success"])
            self.assertEqual(
                scored["expected_attack_tool_proposed"],
                summary[summary_key]["expected_attack_tool_proposed"],
            )
            self.assertEqual(
                scored["expected_attack_tool_executed"],
                summary[summary_key]["expected_attack_tool_executed"],
            )


if __name__ == "__main__":
    unittest.main()
