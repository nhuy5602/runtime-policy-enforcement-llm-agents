"""Regression checks for the paired AgentDojo smoke launcher."""

from __future__ import annotations

import importlib.util
import os
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "run_agentdojo_paired_smoke.py"
SPEC = importlib.util.spec_from_file_location("paired_smoke", SCRIPT)
assert SPEC and SPEC.loader
paired_smoke = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(paired_smoke)


class PairedSmokeSecretTests(unittest.TestCase):
    def test_key_is_injected_and_missing_key_fails_closed(self) -> None:
        with patch.dict(os.environ, {"RUNPOD_API_KEY": "injected-key"}, clear=True):
            self.assertEqual(paired_smoke.resolve_runpod_key(), "injected-key")
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "RUNPOD_API_KEY"):
                paired_smoke.resolve_runpod_key()


if __name__ == "__main__":
    unittest.main()
