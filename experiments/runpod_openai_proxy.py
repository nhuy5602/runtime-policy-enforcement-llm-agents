"""Bridge OpenAI Chat Completions requests to a Runpod ``/runsync`` endpoint.

The vLLM endpoint's direct ``/openai/v1/chat/completions`` route can reject
AgentDojo's tool-bearing request shape. This local, dependency-free bridge
forwards the complete request body through the worker's documented
``/runsync`` route and unwraps the standard OpenAI completion object.
"""

from __future__ import annotations

import argparse
import json
import os
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlparse


def endpoint_base(endpoint_id: str) -> str:
    endpoint_id = endpoint_id.strip()
    if not endpoint_id or "/" in endpoint_id:
        raise ValueError("endpoint id must be a non-empty slug")
    return f"https://api.runpod.ai/v2/{endpoint_id}"


def _auth_headers(api_key: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "User-Agent": "runtime-policy-research/runpod-openai-proxy",
    }


def _json_request(
    method: str,
    url: str,
    *,
    api_key: str,
    payload: dict[str, Any] | None = None,
    timeout: float,
) -> dict[str, Any]:
    data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers=_auth_headers(api_key), method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            value = json.load(response)
    except urllib.error.HTTPError as error:
        detail = error.read(512).decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"Runpod HTTP {error.code}: {detail[:300]}") from error
    except (urllib.error.URLError, TimeoutError) as error:
        raise RuntimeError(f"Runpod transport error: {type(error).__name__}") from error
    if not isinstance(value, dict):
        raise RuntimeError("Runpod returned a non-object JSON body")
    return value


def make_runsync_payload(route: str, body: dict[str, Any]) -> dict[str, Any]:
    if not route.startswith("/") or not route.endswith("/chat/completions"):
        raise ValueError("route must be an OpenAI chat-completions path")
    return {"input": {"route": route, "body": body}}


def unwrap_completed(body: dict[str, Any]) -> dict[str, Any]:
    """Return the OpenAI response object from a completed Runpod body."""

    output = body.get("output")
    if isinstance(output, list) and output and isinstance(output[0], dict):
        return output[0]
    if isinstance(output, dict):
        return output
    raise RuntimeError("Runpod completed without an OpenAI response object")


def run_completion(
    endpoint_id: str,
    api_key: str,
    request_body: dict[str, Any],
    *,
    timeout: float = 300.0,
) -> dict[str, Any]:
    base = endpoint_base(endpoint_id)
    started = time.monotonic()
    result = _json_request(
        "POST",
        f"{base}/runsync",
        api_key=api_key,
        payload=make_runsync_payload("/v1/chat/completions", request_body),
        timeout=min(30.0, timeout),
    )
    status = str(result.get("status", "")).upper()
    job_id = result.get("id")
    while status not in {"COMPLETED", "FAILED", "CANCELLED", "TIMED_OUT"}:
        if not job_id:
            raise RuntimeError("Runpod returned a non-terminal body without a job id")
        remaining = timeout - (time.monotonic() - started)
        if remaining <= 0:
            raise RuntimeError("Runpod proxy timeout")
        result = _json_request(
            "GET",
            f"{base}/status/{job_id}",
            api_key=api_key,
            timeout=min(30.0, remaining),
        )
        status = str(result.get("status", "")).upper()
    if status != "COMPLETED":
        detail = result.get("error") or result.get("output") or "no worker detail"
        raise RuntimeError(f"Runpod job {status.lower()}: {str(detail)[:500]}")
    return unwrap_completed(result)


def _error_payload(message: str) -> dict[str, Any]:
    return {"error": {"message": message, "type": "runpod_proxy_error"}}


class _Handler(BaseHTTPRequestHandler):
    server: "_ProxyServer"

    def _write(self, code: int, value: dict[str, Any]) -> None:
        raw = json.dumps(value, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/health":
            self._write(200, {"status": "ok"})
            return
        if self.path.rstrip("/") == "/v1/models":
            self._write(
                200,
                {
                    "object": "list",
                    "data": [{"id": self.server.model_id, "object": "model"}],
                },
            )
            return
        self._write(404, _error_payload("not found"))

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if not parsed.path.endswith("/chat/completions"):
            self._write(404, _error_payload("only chat completions are supported"))
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            body = json.loads(self.rfile.read(length))
            if not isinstance(body, dict):
                raise ValueError("request body must be a JSON object")
            result = run_completion(
                self.server.endpoint_id,
                self.server.api_key,
                body,
                timeout=self.server.timeout,
            )
        except (ValueError, RuntimeError, json.JSONDecodeError) as error:
            self._write(502, _error_payload(str(error)[:500]))
            return
        self._write(200, result)

    def log_message(self, format: str, *args: Any) -> None:
        return


class _ProxyServer(ThreadingHTTPServer):
    def __init__(
        self,
        address: tuple[str, int],
        *,
        endpoint_id: str,
        api_key: str,
        model_id: str,
        timeout: float,
    ) -> None:
        super().__init__(address, _Handler)
        self.endpoint_id = endpoint_id
        self.api_key = api_key
        self.model_id = model_id
        self.timeout = timeout


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--endpoint-id", required=True)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--timeout", type=float, default=300.0)
    parser.add_argument("--model-id", default="qwen/qwen3-8b")
    parser.add_argument("--api-key-env", default="RUNPOD_API_KEY")
    args = parser.parse_args()
    api_key = os.environ.get(args.api_key_env)
    if not api_key:
        raise SystemExit(f"missing {args.api_key_env}")
    server = _ProxyServer(
        (args.host, args.port),
        endpoint_id=args.endpoint_id,
        api_key=api_key,
        model_id=args.model_id,
        timeout=args.timeout,
    )
    print(f"http://{args.host}:{server.server_port}/v1", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
