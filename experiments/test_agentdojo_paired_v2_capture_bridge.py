import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from experiments.agentdojo_paired_v2_capture_bridge import (
    CaptureBridgeError,
    _RecordingRuntime,
    _RequestCapture,
    _verify_url,
    run_episode,
)


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "tmp" / "agentdojo-source"
MANIFEST = ROOT / "experiments" / "fixtures" / "agentdojo_paired_v2_execution_manifest_v1.json"
PINNED_PYTHON = SOURCE / ".venv31213" / "Scripts" / "python.exe"


def _pinned_runtime_available() -> bool:
    if not PINNED_PYTHON.is_file():
        return False
    try:
        probe = subprocess.run(
            [
                str(PINNED_PYTHON),
                "-c",
                (
                    "import platform, pydantic, yaml; "
                    "assert platform.python_version() == '3.12.13'; "
                    "assert pydantic.__version__ == '2.11.4'; "
                    "assert yaml.__version__ == '6.0.2'"
                ),
            ],
            check=False,
            capture_output=True,
            timeout=15,
        )
        return probe.returncode == 0
    except Exception:
        return False


class _FakeProviderHandler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length", "0"))
        request = json.loads(self.rfile.read(length))
        finished = any(message.get("role") == "tool" for message in request["messages"])
        tool_name = next(tool["function"]["name"] for tool in request["tools"]
                         if tool["function"]["name"] in ("get_current_day", "v1_get_current_day"))
        message = {"role": "assistant", "content": "Done", "tool_calls": None}
        if not finished:
            message.update(content=None, tool_calls=[{
                "id": "call-local-clock", "type": "function",
                "function": {"name": tool_name, "arguments": "{}"},
            }])
        body = {
            "id": "chatcmpl-bridge-test-final" if finished else "chatcmpl-bridge-test-tool",
            "object": "chat.completion",
            "created": 1,
            "model": "qwen/qwen3-8b",
            "choices": [
                {
                    "index": 0,
                    "message": message,
                    "finish_reason": "stop" if finished else "tool_calls",
                }
            ],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        }
        raw = json.dumps(body).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, _format: str, *_args: object) -> None:
        return


class AgentDojoPairedV2CaptureBridgeTests(unittest.TestCase):
    def test_url_validation_is_fail_closed(self) -> None:
        with self.assertRaises(CaptureBridgeError):
            _verify_url("")
        with self.assertRaises(CaptureBridgeError):
            _verify_url("not-a-url")
        self.assertEqual(_verify_url("http://127.0.0.1:8000/v1/"), "http://127.0.0.1:8000/v1")

    def test_missing_credentials_are_rejected_before_child_spawn(self) -> None:
        with self.assertRaisesRegex(CaptureBridgeError, "api_key is required"):
            run_episode(
                {},
                source_root=SOURCE,
                python_executable=sys.executable,
                base_url="http://127.0.0.1:1/v1",
                api_key="",
                model="qwen/qwen3-8b",
                run_id="bridge-test",
                timeout=1,
            )
        with self.assertRaisesRegex(CaptureBridgeError, "base_url is required"):
            run_episode(
                {},
                source_root=SOURCE,
                python_executable=sys.executable,
                base_url="",
                api_key="test-key",
                model="qwen/qwen3-8b",
                run_id="bridge-test",
                timeout=1,
            )

    def test_request_and_tool_caps_abort_before_the_next_call(self) -> None:
        capture = _RequestCapture(
            {
                "execution_budget": {
                    "max_model_requests_per_episode": 1,
                    "max_tool_calls_per_episode": 1,
                    "overflow_policy": "test",
                }
            }
        )

        class _Completions:
            calls = 0

            def create(self, **_kwargs):
                self.calls += 1
                return {"id": f"response-{self.calls}", "choices": [{"message": {"tool_calls": None}}]}

        class _Client:
            def __init__(self) -> None:
                self.chat = type("_Chat", (), {"completions": _Completions()})()

        client = _Client()
        capture.request(client, "test-model", [], [], None, 0.0)
        with self.assertRaisesRegex(CaptureBridgeError, "model_request_cap_exceeded"):
            capture.request(client, "test-model", [], [], None, 0.0)
        self.assertEqual(client.chat.completions.calls, 1)

        class _Runtime:
            functions = {}

            def run_function(self, _env, _function, _kwargs, raise_on_error=False):
                return "ok", None

        class _Environment:
            def model_dump(self, mode="json"):
                return {}

        recording = _RecordingRuntime(_Runtime(), max_tool_calls=1)
        recording.run_function(_Environment(), "tool", {})
        with self.assertRaisesRegex(CaptureBridgeError, "tool_call_cap_exceeded"):
            recording.run_function(_Environment(), "tool", {})

    @unittest.skipUnless(
        _pinned_runtime_available(),
        "requires the pinned CPython 3.12.13 / pydantic 2.11.4 / PyYAML 6.0.2 runtime",
    )
    def test_provider_failure_is_not_retried_by_sdk(self) -> None:
        from experiments.agentdojo_paired_v2_execution_manifest import load_manifest

        manifest = load_manifest(MANIFEST)
        plan = next(row for row in manifest["episodes"]
                    if row["arm"] == "no_injecagent_default_control"
                    and row["contract"]["version"] == "v0")
        requests = []

        class UnavailableProvider(_FakeProviderHandler):
            def do_POST(self) -> None:  # noqa: N802
                self.rfile.read(int(self.headers.get("Content-Length", "0")))
                requests.append(self.path)
                body = b'{"error": {"message": "local test unavailable"}}'
                self.send_response(503)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        server = ThreadingHTTPServer(("127.0.0.1", 0), UnavailableProvider)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with self.assertRaisesRegex(CaptureBridgeError, "InternalServerError"):
                run_episode(
                    plan, source_root=SOURCE, python_executable=PINNED_PYTHON,
                    base_url=f"http://127.0.0.1:{server.server_port}/v1",
                    api_key="local-test-key", model="qwen/qwen3-8b",
                    run_id="bridge-no-sdk-retry", timeout=45,
                )
            self.assertEqual(requests, ["/v1/chat/completions"])
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

    @unittest.skipUnless(
        _pinned_runtime_available(),
        "requires the pinned CPython 3.12.13 / pydantic 2.11.4 / PyYAML 6.0.2 runtime",
    )
    def test_local_provider_record_reaches_v2_validator(self) -> None:
        from experiments.agentdojo_paired_v2_execution_manifest import load_manifest
        from experiments.agentdojo_paired_v2_result_bundle import build_result_bundle_template

        manifest = load_manifest(MANIFEST)
        pair_ids = [
            next(row["pair_id"] for row in manifest["episodes"] if row["arm"] == "attack"),
            next(
                row["pair_id"]
                for row in manifest["episodes"]
                if row["arm"] == "no_injecagent_default_control"
            ),
        ]
        siblings = sorted(
            (row for row in manifest["episodes"] if row["pair_id"] in pair_ids),
            key=lambda row: row["execution_order"],
        )
        server = ThreadingHTTPServer(("127.0.0.1", 0), _FakeProviderHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            records = [
                run_episode(
                    plan,
                    source_root=SOURCE,
                    python_executable=PINNED_PYTHON,
                    base_url=f"http://127.0.0.1:{server.server_port}/v1",
                    api_key="local-test-key",
                    model="qwen/qwen3-8b",
                    run_id=f"bridge-test-{plan['contract']['version']}",
                    timeout=45,
                )
                for plan in siblings
            ]
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

        bundle = build_result_bundle_template(manifest)
        by_episode = {record["episode_id"]: record for record in records}
        for index, row in enumerate(bundle["episodes"]):
            if row["episode_id"] in by_episode:
                bundle["episodes"][index] = by_episode[row["episode_id"]]
        for plan, record in zip(siblings, records, strict=True):
            self.assertEqual(len(record["model_request_records"]), 2)
            self.assertEqual(record["execution_budget_witness"]["tool_dispatch_count"], 1)
            self.assertEqual(record["source_cluster_id"], plan["source_cluster_id"])
            self.assertEqual(record["runtime_identity_witness"], plan["runtime_identity"])
            if plan["arm"] == "no_injecagent_default_control":
                self.assertEqual(
                    record["no_injecagent_default_control_witness"],
                    plan["arm_binding"]["default_control_contract"]["control_witness"],
                )
        with tempfile.TemporaryDirectory(prefix="agentdojo-v2-bridge-test-") as temp_dir:
            bundle_path = Path(temp_dir) / "bundle.json"
            report_path = Path(temp_dir) / "report.json"
            bundle_path.write_text(json.dumps(bundle, ensure_ascii=False), encoding="utf-8")
            env = {
                **dict(os.environ),
                "PYTHONPATH": os.pathsep.join(
                    [str(ROOT), str(SOURCE / "src"), os.environ.get("PYTHONPATH", "")]
                ),
                "PYTHONIOENCODING": "utf-8",
            }
            completed = subprocess.run(
                [
                    str(PINNED_PYTHON),
                    str(ROOT / "experiments" / "agentdojo_paired_v2_result_bundle.py"),
                    "--bundle",
                    str(bundle_path),
                    "--manifest",
                    str(MANIFEST),
                    "--source",
                    str(SOURCE),
                    "--output",
                    str(report_path),
                ],
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                env=env,
                timeout=120,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
            report = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertIsNone(report["bundle_contract_error"])
        self.assertEqual(report["summary"]["attack"]["valid_pair_count"], 1)
        self.assertEqual(report["summary"]["default_control"]["valid_pair_count"], 1,
                         report["not_scored_episode_reasons"])
        from experiments.agentdojo_paired_v2_statistics_adapter import _pair_rows
        complete, incomplete = _pair_rows(report, manifest)
        self.assertEqual(len(complete), 2)
        self.assertEqual(len(incomplete), 4)


if __name__ == "__main__":
    unittest.main()
