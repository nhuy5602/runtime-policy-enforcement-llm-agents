import importlib.util
import os
import unittest
from pathlib import Path

try:
    from experiments import agentdojo_attestation_adapter as adapter
except ModuleNotFoundError:
    import agentdojo_attestation_adapter as adapter


class AgentDojoAttestationAdapterTests(unittest.TestCase):
    def test_dependency_free_self_test(self):
        report = adapter.self_test()
        self.assertEqual(report["status"], "pass")
        self.assertIn("attestation_commit", report["checks"])

    def test_default_policy_is_fail_closed(self):
        previous = {
            name: os.environ.get(name)
            for name in (
                adapter.ALLOWLIST_ENV,
                adapter.APPROVAL_ENV,
                adapter.APPROVE_ENV,
            )
        }
        try:
            for name in previous:
                os.environ.pop(name, None)
            self.assertEqual(
                adapter._policy_decision("any_tool"),
                ("DENY", "allowlist_missing_fail_closed"),
            )
        finally:
            for name, value in previous.items():
                if value is None:
                    os.environ.pop(name, None)
                else:
                    os.environ[name] = value

    def test_nested_tool_call_is_rejected_at_boundary(self):
        nested = {"outer": {"function": "forbidden", "args": {}}}
        self.assertTrue(adapter._contains_nested_tool_call(nested))
        self.assertFalse(adapter._contains_nested_tool_call({"outer": {"value": 1}}))

    def test_active_contract_keeps_policy_identity_at_v0(self):
        previous = os.environ.get("AGENTDOJO_CONTRACT_MANIFEST")
        fixture = Path(__file__).with_name("fixtures") / "agentdojo_contract_v0_to_v1.json"
        os.environ["AGENTDOJO_CONTRACT_MANIFEST"] = str(fixture)
        try:
            self.assertEqual(
                adapter._canonical_policy_tool_name("v1_send_email"),
                "send_email",
            )
            self.assertEqual(
                adapter._canonical_policy_tool_name("unknown_tool"),
                "unknown_tool",
            )
        finally:
            if previous is None:
                os.environ.pop("AGENTDOJO_CONTRACT_MANIFEST", None)
            else:
                os.environ["AGENTDOJO_CONTRACT_MANIFEST"] = previous

    @unittest.skipUnless(
        importlib.util.find_spec("agentdojo") is not None,
        "AgentDojo is an optional benchmark dependency",
    )
    def test_patch_installed_when_agentdojo_available(self):
        self.assertTrue(adapter.PATCH_INSTALLED)

    @unittest.skipUnless(
        importlib.util.find_spec("agentdojo") is not None,
        "AgentDojo is an optional benchmark dependency",
    )
    def test_allowlisted_tool_roundtrip_preserves_tool_message_schema(self):
        from pydantic import BaseModel

        from agentdojo.agent_pipeline import agent_pipeline as pipeline_module
        from agentdojo.functions_runtime import Depends, Function, FunctionCall, FunctionsRuntime, TaskEnvironment

        class Env(TaskEnvironment):
            count: int = 0

        class Args(BaseModel):
            value: int

        def increment(env: Env, value: int):
            env.count += value
            return env.count

        function = Function(
            name="increment",
            description="increment",
            parameters=Args,
            dependencies={"env": Depends(lambda value: value)},
            run=increment,
            full_docstring="increment",
            return_type=int,
        )
        runtime = FunctionsRuntime([function])
        env = Env()
        previous = os.environ.get(adapter.ALLOWLIST_ENV)
        os.environ[adapter.ALLOWLIST_ENV] = "increment"
        try:
            call = FunctionCall(function="increment", args={"value": 2}, id="call-1")
            messages = [{"role": "assistant", "content": None, "tool_calls": [call]}]
            executor = pipeline_module.ToolsExecutor()
            _, _, updated_env, output, _ = executor.query("", runtime, env, messages, {})
        finally:
            if previous is None:
                os.environ.pop(adapter.ALLOWLIST_ENV, None)
            else:
                os.environ[adapter.ALLOWLIST_ENV] = previous

        self.assertEqual(updated_env.count, 2)
        self.assertEqual(output[-1]["role"], "tool")
        self.assertIsNone(output[-1]["error"])
        self.assertEqual(output[-1]["content"][0]["content"], "2")

    @unittest.skipUnless(
        importlib.util.find_spec("agentdojo") is not None,
        "AgentDojo is an optional benchmark dependency",
    )
    def test_drift_hook_aborts_before_live_environment_commit(self):
        from pydantic import BaseModel

        from agentdojo.agent_pipeline import agent_pipeline as pipeline_module
        from agentdojo.functions_runtime import Depends, Function, FunctionCall, FunctionsRuntime, TaskEnvironment

        class Env(TaskEnvironment):
            count: int = 0

        class Args(BaseModel):
            value: int

        def increment(env: Env, value: int):
            env.count += value
            return env.count

        function = Function(
            name="increment",
            description="increment",
            parameters=Args,
            dependencies={"env": Depends(lambda value: value)},
            run=increment,
            full_docstring="increment",
            return_type=int,
        )
        runtime = FunctionsRuntime([function])
        env = Env()
        previous = {
            name: os.environ.get(name)
            for name in (
                adapter.ALLOWLIST_ENV,
                adapter.DRIFT_TOOL_ENV,
                adapter.DRIFT_MODE_ENV,
            )
        }
        os.environ[adapter.ALLOWLIST_ENV] = "increment"
        os.environ[adapter.DRIFT_TOOL_ENV] = "increment"
        os.environ[adapter.DRIFT_MODE_ENV] = "resource"
        try:
            call = FunctionCall(function="increment", args={"value": 2}, id="call-drift")
            messages = [{"role": "assistant", "content": None, "tool_calls": [call]}]
            executor = pipeline_module.ToolsExecutor()
            _, _, unchanged_env, output, _ = executor.query("", runtime, env, messages, {})
        finally:
            for name, value in previous.items():
                if value is None:
                    os.environ.pop(name, None)
                else:
                    os.environ[name] = value

        self.assertEqual(unchanged_env.count, 0)
        self.assertEqual(output[-1]["role"], "tool")
        self.assertIn("observed_signature_mismatch", output[-1]["error"])


if __name__ == "__main__":
    unittest.main()
