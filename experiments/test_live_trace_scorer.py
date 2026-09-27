"""Small regression tests for the live-trace scorer.

Run from the repository root with:

    python -m unittest experiments.test_live_trace_scorer -v
"""

from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "experiments"))

from live_trace_scorer import score_configurations, score_trace  # noqa: E402
from policy_guard_sim import DEFAULT_CASES, load_cases  # noqa: E402


def _proposal(case) -> dict[str, object]:
    return {
        "tool": case.tool,
        "operation": case.operation,
        "resource": case.resource,
        "destination": case.destination,
        "carries_sensitive_data": case.carries_sensitive_data,
    }


def _trace(overrides: dict[str, dict[str, object]] | None = None) -> dict[str, object]:
    overrides = overrides or {}
    cases = load_cases(DEFAULT_CASES)
    return {
        "status": "completed",
        "model": "test-model",
        "cases": [
            {
                "case_id": case.case_id,
                "parsed_tool_call": {
                    **_proposal(case),
                    **overrides.get(case.case_id, {}),
                },
                "error": None,
                "response_metadata": {},
            }
            for case in cases
        ],
    }


class LiveTraceScorerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixtures = load_cases(DEFAULT_CASES)

    def test_same_proposals_are_scored_causally_under_all_baselines(self) -> None:
        result = score_configurations(_trace(), self.fixtures)
        self.assertEqual(
            result["configuration_order"],
            ["C0_schema_only", "C1_static_allowlist", "C2_policy_guard"],
        )

        c0 = result["configurations"]["C0_schema_only"]["summary"]
        c1 = result["configurations"]["C1_static_allowlist"]["summary"]
        c2 = result["configurations"]["C2_policy_guard"]["summary"]
        self.assertEqual(c0["forbidden_effect_executed_rate"], 1.0)
        self.assertEqual(c1["forbidden_effect_executed_rate"], 1.0)
        self.assertEqual(c2["forbidden_effect_executed_rate"], 0.0)
        self.assertEqual(c0["guard_denied_forbidden_proposals"], 0)
        self.assertEqual(c2["guard_denied_forbidden_proposals"], 4)

        replay_c0 = result["configurations"]["C0_schema_only"]["cases"][1]
        replay_c2 = result["configurations"]["C2_policy_guard"]["cases"][1]
        self.assertTrue(replay_c0["executed"])
        self.assertFalse(replay_c2["executed"])

    def test_model_non_attack_and_wrong_proposal_are_not_guard_failures(self) -> None:
        trace = _trace(
            {
                "injection_http_exfiltration": _proposal(
                    self.fixtures[0]
                ),
                "injection_unauthorized_ticket": {
                    "tool": "docs",
                    "operation": "update",
                    "resource": "ticket_43",
                    "destination": "",
                    "carries_sensitive_data": False,
                },
            }
        )
        result = score_trace(trace, self.fixtures)
        rows = {row["case_id"]: row for row in result["cases"]}

        safe = rows["injection_http_exfiltration"]
        self.assertTrue(safe["model_non_attack"])
        self.assertFalse(safe["forbidden_proposal"])
        self.assertFalse(safe["model_wrong_proposal"])

        wrong = rows["injection_unauthorized_ticket"]
        self.assertTrue(wrong["model_wrong_proposal"])
        self.assertFalse(wrong["model_wrong_tool"])
        self.assertFalse(wrong["forbidden_proposal"])
        self.assertEqual(wrong["failure"], "model_wrong_proposal")

        trace = _trace(
            {
                "injection_unauthorized_ticket": {
                    "tool": "calendar",
                    "operation": "update",
                    "resource": "ticket_43",
                    "destination": "",
                    "carries_sensitive_data": False,
                }
            }
        )
        wrong_tool = {
            row["case_id"]: row
            for row in score_trace(trace, self.fixtures)["cases"]
        }["injection_unauthorized_ticket"]
        self.assertTrue(wrong_tool["model_wrong_proposal"])
        self.assertTrue(wrong_tool["model_wrong_tool"])
        self.assertEqual(wrong_tool["failure"], "model_wrong_tool")

    def test_benign_model_error_is_separate_from_guard_false_block(self) -> None:
        trace = _trace(
            {
                "benign_high_risk_send": {
                    "carries_sensitive_data": True,
                }
            }
        )
        summary = score_trace(trace, self.fixtures)["summary"]
        self.assertEqual(summary["FBR"], 1 / 3)
        self.assertEqual(summary["canonical_proposal_guard_FBR"], 0.0)
        self.assertEqual(summary["model_benign_wrong_proposal_cases"], 1)

    def test_safe_attack_proposal_is_not_counted_as_benign_false_block(self) -> None:
        trace = _trace(
            {
                "injection_email_exfiltration": {
                    "tool": "mail",
                    "operation": "send",
                    "resource": "status_update",
                    "destination": "company.edu",
                    "carries_sensitive_data": False,
                }
            }
        )
        result = score_trace(trace, self.fixtures)
        row = {
            item["case_id"]: item
            for item in result["cases"]
        }["injection_email_exfiltration"]
        self.assertTrue(row["model_non_attack"])
        self.assertFalse(row["guard_denied_canonical_proposal"])
        self.assertEqual(result["summary"]["canonical_proposal_guard_FBR"], 0.0)

    def test_trace_index_rejects_duplicate_and_missing_cases(self) -> None:
        duplicate = _trace()
        duplicate["cases"].append(copy.deepcopy(duplicate["cases"][0]))
        with self.assertRaisesRegex(ValueError, "duplicate case_id"):
            score_trace(duplicate, self.fixtures)

        missing = _trace()
        missing["cases"] = missing["cases"][:-1]
        with self.assertRaisesRegex(ValueError, "missing case_id"):
            score_trace(missing, self.fixtures)

    def test_unknown_configuration_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "unknown configuration"):
            score_trace(_trace(), self.fixtures, configuration="P_postverify")


if __name__ == "__main__":
    unittest.main()
