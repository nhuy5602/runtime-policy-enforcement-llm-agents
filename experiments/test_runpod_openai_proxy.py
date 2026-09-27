import unittest

try:
    from experiments.runpod_openai_proxy import (
        endpoint_base,
        make_runsync_payload,
        unwrap_completed,
    )
except ModuleNotFoundError:
    from runpod_openai_proxy import endpoint_base, make_runsync_payload, unwrap_completed


class RunpodOpenAIProxyTests(unittest.TestCase):
    def test_payload_is_route_and_body_preserving(self):
        body = {"model": "qwen/qwen3-8b", "tools": [{"type": "function"}]}
        self.assertEqual(
            make_runsync_payload("/v1/chat/completions", body),
            {"input": {"route": "/v1/chat/completions", "body": body}},
        )

    def test_unwraps_completed_output(self):
        response = {"output": [{"choices": [{"message": {"content": "ok"}}]}]}
        self.assertEqual(unwrap_completed(response)["choices"][0]["message"]["content"], "ok")

    def test_endpoint_id_is_not_a_url_or_path(self):
        self.assertEqual(endpoint_base("gbo4nj1k5ublmt"), "https://api.runpod.ai/v2/gbo4nj1k5ublmt")
        with self.assertRaises(ValueError):
            endpoint_base("https://example.invalid")


if __name__ == "__main__":
    unittest.main()
