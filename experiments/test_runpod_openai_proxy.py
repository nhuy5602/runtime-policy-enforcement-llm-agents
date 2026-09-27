import http.client
import json
import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

try:
    from experiments.runpod_openai_proxy import (
        endpoint_base,
        JobLedger,
        _json_request,
        make_run_payload,
        ledger_summary,
        reconcile_ledger,
        run_completion,
        unwrap_completed,
    )
except ModuleNotFoundError:
    from runpod_openai_proxy import (
        JobLedger,
        _json_request,
        endpoint_base,
        ledger_summary,
        make_run_payload,
        reconcile_ledger,
        run_completion,
        unwrap_completed,
    )


class RunpodOpenAIProxyTests(unittest.TestCase):
    def test_payload_is_route_and_body_preserving(self):
        body = {"model": "qwen/qwen3-8b", "tools": [{"type": "function"}]}
        self.assertEqual(
            make_run_payload("/v1/chat/completions", body),
            {"input": {"route": "/v1/chat/completions", "body": body}},
        )

    def test_queue_lifecycle_returns_completion_and_records_terminal_receipt(self):
        responses = [
            {"id": "job-1", "status": "IN_QUEUE"},
            {"id": "job-1", "status": "IN_PROGRESS"},
            {"id": "job-1", "status": "COMPLETED", "output": {"choices": [{"message": {"content": "ok"}}]}},
        ]
        with tempfile.TemporaryDirectory() as temporary:
            ledger_path = Path(temporary) / "jobs.jsonl"
            ledger = JobLedger(ledger_path, "endpoint-1", "test-run")
            with patch("experiments.runpod_openai_proxy._json_request", side_effect=responses) as request:
                with patch("experiments.runpod_openai_proxy.time.monotonic", side_effect=(0.0, 0.1, 0.2)):
                    with patch("experiments.runpod_openai_proxy.time.sleep"):
                        response = run_completion("endpoint-1", "key", {"model": "test"}, timeout=1.0, ledger=ledger)
            summary = ledger_summary(ledger_path)
        self.assertEqual(response["choices"][0]["message"]["content"], "ok")
        self.assertTrue(summary["all_jobs_terminal"])
        self.assertEqual(summary["jobs"]["job-1"]["status"], "COMPLETED")
        self.assertEqual(request.call_args_list[1].args[:2], ("GET", "https://api.runpod.ai/v2/endpoint-1/status/job-1"))
        self.assertEqual(request.call_args_list[2].args[:2], ("GET", "https://api.runpod.ai/v2/endpoint-1/status/job-1"))

    def test_timeout_requests_and_confirms_remote_cancellation(self):
        responses = [
            {"id": "job-1", "status": "IN_QUEUE"},
            {"id": "job-1", "status": "CANCELLED"},
        ]
        with tempfile.TemporaryDirectory() as temporary:
            ledger_path = Path(temporary) / "jobs.jsonl"
            ledger = JobLedger(ledger_path, "endpoint-1", "test-run")
            with patch("experiments.runpod_openai_proxy._json_request", side_effect=responses) as request:
                with patch("experiments.runpod_openai_proxy.time.monotonic", side_effect=(0.0, 2.0)):
                    with self.assertRaisesRegex(RuntimeError, "remote terminal status CANCELLED for job job-1"):
                        run_completion("endpoint-1", "key", {"model": "test"}, timeout=1.0, ledger=ledger)
            events = [json.loads(line)["event"] for line in ledger_path.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(events, ["submitted", "cancel_requested", "terminal"])
        self.assertEqual(request.call_args_list[0].args[:2], ("POST", "https://api.runpod.ai/v2/endpoint-1/run"))
        self.assertEqual(request.call_args_list[1].args[:2], ("POST", "https://api.runpod.ai/v2/endpoint-1/cancel/job-1"))

    def test_timeout_records_terminal_race_as_an_observation(self):
        for terminal in ("COMPLETED", "FAILED"):
            with self.subTest(terminal=terminal), tempfile.TemporaryDirectory() as temporary:
                ledger_path = Path(temporary) / "jobs.jsonl"
                ledger = JobLedger(ledger_path, "endpoint-1", "test-run")
                with patch(
                    "experiments.runpod_openai_proxy._json_request",
                    side_effect=[
                        {"id": "job-1", "status": "IN_QUEUE"},
                        {"id": "job-1", "status": terminal},
                    ],
                ):
                    with patch("experiments.runpod_openai_proxy.time.monotonic", side_effect=(0.0, 2.0)):
                        with self.assertRaisesRegex(RuntimeError, f"observed remote terminal status {terminal}"):
                            run_completion("endpoint-1", "key", {"model": "test"}, timeout=1.0, ledger=ledger)
                self.assertEqual(ledger_summary(ledger_path)["jobs"]["job-1"]["status"], terminal)

    def test_nonterminal_cancel_response_requires_a_terminal_status_poll(self):
        responses = [
            {"id": "job-1", "status": "IN_QUEUE"},
            {"id": "job-1", "status": "IN_PROGRESS"},
            {"id": "job-1", "status": "CANCELLED"},
        ]
        with tempfile.TemporaryDirectory() as temporary:
            ledger_path = Path(temporary) / "jobs.jsonl"
            ledger = JobLedger(ledger_path, "endpoint-1", "test-run")
            with patch("experiments.runpod_openai_proxy._json_request", side_effect=responses) as request:
                with patch("experiments.runpod_openai_proxy.time.monotonic", side_effect=(0.0, 2.0)):
                    with self.assertRaisesRegex(RuntimeError, "observed remote terminal status CANCELLED"):
                        run_completion("endpoint-1", "key", {"model": "test"}, timeout=1.0, ledger=ledger)
        self.assertEqual(request.call_args_list[2].args[:2], ("GET", "https://api.runpod.ai/v2/endpoint-1/status/job-1"))

    def test_timeout_fails_closed_when_remote_cancellation_is_not_confirmed(self):
        responses = [
            {"id": "job-1", "status": "IN_QUEUE"},
            {"id": "job-1", "status": "IN_PROGRESS"},
            {"id": "job-1", "status": "IN_PROGRESS"},
        ]
        with patch("experiments.runpod_openai_proxy._json_request", side_effect=responses):
            with patch("experiments.runpod_openai_proxy.time.monotonic", side_effect=(0.0, 2.0)):
                with self.assertRaisesRegex(RuntimeError, "cancellation unverified"):
                    run_completion("endpoint-1", "key", {"model": "test"}, timeout=1.0)

    def test_poll_error_cancels_the_identified_job_before_failing(self):
        responses = [
            {"id": "job-1", "status": "IN_QUEUE"},
            RuntimeError("transport"),
            {"id": "job-1", "status": "CANCELLED"},
        ]
        with patch("experiments.runpod_openai_proxy._json_request", side_effect=responses) as request:
            with patch("experiments.runpod_openai_proxy.time.monotonic", side_effect=(0.0, 0.1)):
                with self.assertRaisesRegex(RuntimeError, "status poll failed.*CANCELLED"):
                    run_completion("endpoint-1", "key", {"model": "test"}, timeout=1.0)
        self.assertEqual(request.call_args_list[2].args[:2], ("POST", "https://api.runpod.ai/v2/endpoint-1/cancel/job-1"))

    def test_ambiguous_submission_is_recorded_and_not_retried(self):
        with tempfile.TemporaryDirectory() as temporary:
            ledger_path = Path(temporary) / "jobs.jsonl"
            ledger = JobLedger(ledger_path, "endpoint-1", "test-run")
            with patch("experiments.runpod_openai_proxy._json_request", side_effect=RuntimeError("transport")) as request:
                with self.assertRaisesRegex(RuntimeError, "submission ambiguous"):
                    run_completion("endpoint-1", "key", {"model": "test"}, timeout=1.0, ledger=ledger)
            row = json.loads(ledger_path.read_text(encoding="utf-8"))
        self.assertEqual(row["event"], "submission_ambiguous")
        self.assertIsNone(row["job_id"])
        self.assertNotIn("body", row)
        self.assertNotIn("api_key", row)
        self.assertEqual(request.call_count, 1)

        with patch("experiments.runpod_openai_proxy._json_request") as later_request:
            with self.assertRaisesRegex(RuntimeError, "submission is blocked"):
                run_completion("endpoint-1", "key", {"model": "later"}, timeout=1.0, ledger=ledger)
        later_request.assert_not_called()

    def test_response_without_job_id_is_recorded_and_latches_proxy(self):
        with tempfile.TemporaryDirectory() as temporary:
            ledger_path = Path(temporary) / "jobs.jsonl"
            ledger = JobLedger(ledger_path, "endpoint-1", "test-run")
            with patch(
                "experiments.runpod_openai_proxy._json_request",
                return_value={"status": "IN_QUEUE"},
            ) as request:
                with self.assertRaisesRegex(RuntimeError, "lacks a job id"):
                    run_completion("endpoint-1", "key", {"model": "test"}, timeout=1.0, ledger=ledger)
            row = json.loads(ledger_path.read_text(encoding="utf-8"))
            self.assertEqual(row["event"], "submission_ambiguous")
            self.assertIsNone(row["job_id"])
            self.assertEqual(request.call_count, 1)
            with patch("experiments.runpod_openai_proxy._json_request") as later_request:
                with self.assertRaisesRegex(RuntimeError, "submission is blocked"):
                    run_completion("endpoint-1", "key", {"model": "later"}, timeout=1.0, ledger=ledger)
        later_request.assert_not_called()

    def test_ambiguous_ledger_blocks_launcher_reconciliation_without_another_request(self):
        with tempfile.TemporaryDirectory() as temporary:
            ledger_path = Path(temporary) / "jobs.jsonl"
            ledger = JobLedger(ledger_path, "endpoint-1", "test-run")
            ledger.submission_ambiguous({"model": "test"}, "TimeoutError", 1.0)
            with patch("experiments.runpod_openai_proxy._json_request") as request:
                with self.assertRaisesRegex(RuntimeError, "ambiguous submission"):
                    reconcile_ledger("endpoint-1", "key", ledger_path, run_id="test-run")
        request.assert_not_called()

    def test_launcher_reconciliation_cancels_an_outstanding_ledger_job(self):
        with tempfile.TemporaryDirectory() as temporary:
            ledger_path = Path(temporary) / "jobs.jsonl"
            ledger = JobLedger(ledger_path, "endpoint-1", "test-run")
            request_hash = ledger.submitted("job-1", {"model": "test"}, "IN_QUEUE", 1.0)
            with patch(
                "experiments.runpod_openai_proxy._json_request",
                side_effect=[
                    {"id": "job-1", "status": "IN_QUEUE"},
                    {"id": "job-1", "status": "CANCELLED"},
                ],
            ) as request:
                summary = reconcile_ledger("endpoint-1", "key", ledger_path, run_id="test-run")
        self.assertTrue(summary["all_jobs_terminal"])
        self.assertEqual(summary["jobs"]["job-1"]["request_sha256"], request_hash)
        self.assertEqual(request.call_args_list[0].args[:2], ("GET", "https://api.runpod.ai/v2/endpoint-1/status/job-1"))
        self.assertEqual(request.call_args_list[1].args[:2], ("POST", "https://api.runpod.ai/v2/endpoint-1/cancel/job-1"))

    def test_reconciliation_records_an_already_terminal_job_without_cancellation(self):
        with tempfile.TemporaryDirectory() as temporary:
            ledger_path = Path(temporary) / "jobs.jsonl"
            ledger = JobLedger(ledger_path, "endpoint-1", "test-run")
            ledger.submitted("job-1", {"model": "test"}, "IN_QUEUE", 1.0)
            with patch(
                "experiments.runpod_openai_proxy._json_request",
                return_value={"id": "job-1", "status": "FAILED"},
            ) as request:
                summary = reconcile_ledger("endpoint-1", "key", ledger_path, run_id="test-run")
        self.assertTrue(summary["all_jobs_terminal"])
        self.assertEqual(summary["jobs"]["job-1"]["status"], "FAILED")
        self.assertEqual(request.call_count, 1)
        self.assertEqual(request.call_args.args[:2], ("GET", "https://api.runpod.ai/v2/endpoint-1/status/job-1"))

    def test_reconciliation_poll_error_requests_remote_cancellation(self):
        with tempfile.TemporaryDirectory() as temporary:
            ledger_path = Path(temporary) / "jobs.jsonl"
            ledger = JobLedger(ledger_path, "endpoint-1", "test-run")
            ledger.submitted("job-1", {"model": "test"}, "IN_QUEUE", 1.0)
            with patch(
                "experiments.runpod_openai_proxy._json_request",
                side_effect=[RuntimeError("transport"), {"id": "job-1", "status": "CANCELLED"}],
            ) as request:
                summary = reconcile_ledger("endpoint-1", "key", ledger_path, run_id="test-run")
        self.assertTrue(summary["all_jobs_terminal"])
        self.assertEqual(request.call_args_list[1].args[:2], ("POST", "https://api.runpod.ai/v2/endpoint-1/cancel/job-1"))

    def test_torn_final_record_blocks_submissions_but_reconciles_valid_prefix(self):
        with tempfile.TemporaryDirectory() as temporary:
            ledger_path = Path(temporary) / "jobs.jsonl"
            ledger = JobLedger(ledger_path, "endpoint-1", "test-run")
            ledger.submitted("job-1", {"model": "test"}, "IN_QUEUE", 1.0)
            with ledger_path.open("a", encoding="utf-8") as handle:
                handle.write('{"schema_version":"runpod-job-ledger/v1"')
            summary = ledger_summary(ledger_path, endpoint_id="endpoint-1")
            self.assertTrue(summary["torn_trailing_record"])
            self.assertEqual(summary["unreconciled_job_ids"], ["job-1"])
            with patch(
                "experiments.runpod_openai_proxy._json_request",
                side_effect=[
                    {"id": "job-1", "status": "IN_QUEUE"},
                    {"id": "job-1", "status": "CANCELLED"},
                ],
            ) as request:
                with self.assertRaisesRegex(RuntimeError, "torn trailing record"):
                    reconcile_ledger("endpoint-1", "key", ledger_path, run_id="test-run")
            self.assertEqual(request.call_args_list[0].args[:2], ("GET", "https://api.runpod.ai/v2/endpoint-1/status/job-1"))
            self.assertEqual(request.call_args_list[1].args[:2], ("POST", "https://api.runpod.ai/v2/endpoint-1/cancel/job-1"))
            with patch("experiments.runpod_openai_proxy._json_request") as later_request:
                with self.assertRaisesRegex(RuntimeError, "torn trailing record"):
                    run_completion("endpoint-1", "key", {"model": "later"}, timeout=1.0, ledger=ledger)
        later_request.assert_not_called()

    def test_unreconciled_ledger_refuses_proxy_submission(self):
        with tempfile.TemporaryDirectory() as temporary:
            ledger_path = Path(temporary) / "jobs.jsonl"
            ledger = JobLedger(ledger_path, "endpoint-1", "test-run")
            ledger.submitted("job-1", {"model": "test"}, "IN_QUEUE", 1.0)
            with patch("experiments.runpod_openai_proxy._json_request") as request:
                with self.assertRaisesRegex(RuntimeError, "reconcile before another submission"):
                    run_completion("endpoint-1", "key", {"model": "later"}, timeout=1.0, ledger=ledger)
        request.assert_not_called()

    def test_ledger_write_failure_attempts_cancellation_and_latches_process(self):
        with tempfile.TemporaryDirectory() as temporary:
            ledger_path = Path(temporary) / "jobs.jsonl"
            ledger = JobLedger(ledger_path, "endpoint-1", "test-run")
            with patch.object(Path, "open", side_effect=OSError("disk full")):
                with patch(
                    "experiments.runpod_openai_proxy._json_request",
                    side_effect=[
                        {"id": "job-1", "status": "IN_QUEUE"},
                        {"id": "job-1", "status": "CANCELLED"},
                    ],
                ) as request:
                    with self.assertRaisesRegex(RuntimeError, "ledger persistence failed; observed remote terminal status CANCELLED"):
                        run_completion("endpoint-1", "key", {"model": "test"}, timeout=1.0, ledger=ledger)
            self.assertEqual(request.call_args_list[1].args[:2], ("POST", "https://api.runpod.ai/v2/endpoint-1/cancel/job-1"))
            with patch("experiments.runpod_openai_proxy._json_request") as later_request:
                with self.assertRaisesRegex(RuntimeError, "submission is blocked"):
                    run_completion("endpoint-1", "key", {"model": "later"}, timeout=1.0, ledger=ledger)
        later_request.assert_not_called()

    def test_malformed_provider_json_is_normalized_to_a_runtime_error(self):
        class MalformedResponse(BytesIO):
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc_value, traceback):
                self.close()
                return False

        with patch(
            "experiments.runpod_openai_proxy.urllib.request.urlopen",
            return_value=MalformedResponse(b"{"),
        ):
            with self.assertRaisesRegex(RuntimeError, "JSONDecodeError"):
                _json_request(
                    "POST",
                    "https://api.runpod.ai/v2/endpoint-1/run",
                    api_key="key",
                    payload={"input": {}},
                    timeout=1.0,
                )

    def test_incomplete_submit_response_is_ledgered_as_ambiguous(self):
        with tempfile.TemporaryDirectory() as temporary:
            ledger_path = Path(temporary) / "jobs.jsonl"
            ledger = JobLedger(ledger_path, "endpoint-1", "test-run")
            with patch(
                "experiments.runpod_openai_proxy.urllib.request.urlopen",
                side_effect=http.client.IncompleteRead(b"", 20),
            ):
                with self.assertRaisesRegex(RuntimeError, "submission ambiguous"):
                    run_completion("endpoint-1", "key", {"model": "test"}, timeout=1.0, ledger=ledger)
            row = json.loads(ledger_path.read_text(encoding="utf-8"))
        self.assertEqual(row["event"], "submission_ambiguous")
        self.assertEqual(row["status"], "RuntimeError")

    def test_unwraps_completed_output(self):
        response = {"output": [{"choices": [{"message": {"content": "ok"}}]}]}
        self.assertEqual(unwrap_completed(response)["choices"][0]["message"]["content"], "ok")

    def test_endpoint_id_is_not_a_url_or_path(self):
        self.assertEqual(endpoint_base("gbo4nj1k5ublmt"), "https://api.runpod.ai/v2/gbo4nj1k5ublmt")
        with self.assertRaises(ValueError):
            endpoint_base("https://example.invalid")


if __name__ == "__main__":
    unittest.main()
