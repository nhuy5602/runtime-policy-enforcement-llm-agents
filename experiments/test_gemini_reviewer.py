"""Tests for the read-only Gemini review bridge."""

from __future__ import annotations

import json
import unittest

from experiments.gemini_reviewer import GeminiReviewError, _response_text, _selected_files, call_gemini


class _Response:
    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self) -> bytes:
        return json.dumps(self.payload).encode()


class GeminiReviewerTests(unittest.TestCase):
    def test_file_selection_is_root_bound(self) -> None:
        names, prompt = _selected_files(["paper/research_protocol.md"])
        self.assertEqual(names, ["paper/research_protocol.md"])
        self.assertIn("BEGIN paper/research_protocol.md", prompt)
        with self.assertRaises(GeminiReviewError):
            _selected_files(["../outside.txt"])

    def test_api_key_uses_header_and_response_is_parsed(self) -> None:
        observed = {}

        def opener(request, *, timeout):
            observed["url"] = request.full_url
            observed["headers"] = dict(request.header_items())
            observed["body"] = json.loads(request.data)
            observed["timeout"] = timeout
            return _Response(
                {
                    "modelVersion": "review-model-version",
                    "candidates": [{"content": {"parts": [{"text": "Strict review"}, {"text": "Second part"}]}}],
                    "usageMetadata": {"promptTokenCount": 10},
                }
            )

        result = call_gemini(
            "Review this",
            api_key="local-test-secret",
            model="gemini-test-pro",
            timeout=3,
            opener=opener,
        )
        self.assertNotIn("local-test-secret", observed["url"])
        self.assertEqual(observed["headers"]["X-goog-api-key"], "local-test-secret")
        self.assertEqual(observed["body"]["contents"][0]["parts"][0]["text"], "Review this")
        self.assertEqual(result["text"], "Strict review\nSecond part")
        self.assertEqual(result["model_version"], "review-model-version")

    def test_invalid_response_or_model_fails_closed(self) -> None:
        with self.assertRaises(GeminiReviewError):
            _response_text({"candidates": []})
        with self.assertRaises(GeminiReviewError):
            call_gemini("x", api_key="key", model="models/not-allowed", opener=lambda *_a, **_k: None)


if __name__ == "__main__":
    unittest.main()
