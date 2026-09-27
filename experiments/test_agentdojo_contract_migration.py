import importlib.util
import os
import unittest
from pathlib import Path
from types import SimpleNamespace

try:
    from experiments import agentdojo_contract_migration as migration
except ModuleNotFoundError:  # direct ``python experiments/test_*.py`` support
    import agentdojo_contract_migration as migration


FIXTURE = Path(__file__).with_name("fixtures") / "agentdojo_contract_v0_to_v1.json"


def _fake_run(*_args, **_kwargs):
    return "ok"


class FakeParameters:
    @staticmethod
    def model_json_schema():
        return {"type": "object", "properties": {"value": {"type": "integer"}}}


class FakeFunction:
    def __init__(self, name: str):
        self.name = name
        self.description = f"Description for {name}"
        self.parameters = FakeParameters
        self.dependencies = {"env": object()}
        self.run = _fake_run
        self.full_docstring = f"Full documentation for {name}"

    def model_copy(self, *, update):
        copied = FakeFunction(update["name"])
        copied.description = self.description
        copied.parameters = self.parameters
        copied.dependencies = self.dependencies
        copied.run = self.run
        copied.full_docstring = self.full_docstring
        return copied


class FakeRuntime:
    def __init__(self, functions):
        self.functions = dict(functions)

    def update_functions(self, functions):
        self.functions = dict(functions)


class AgentDojoContractMigrationTests(unittest.TestCase):
    def setUp(self):
        self.contract = migration.load_contract(FIXTURE)

    def _v0_runtime(self):
        names = self.contract["migration"]["v0_to_v1"]
        return FakeRuntime({name: FakeFunction(name) for name in names})

    def test_fixture_is_one_to_one_and_has_a_stable_digest(self):
        mapping = self.contract["migration"]["v0_to_v1"]
        self.assertEqual(len(mapping), 24)
        self.assertEqual(len(set(mapping.values())), len(mapping))
        self.assertFalse(set(mapping) & set(mapping.values()))
        self.assertEqual(
            migration.canonical_tool_name("v1_send_email", self.contract),
            "send_email",
        )
        self.assertEqual(
            migration.contract_digest(self.contract),
            migration.contract_digest(migration.load_contract(FIXTURE)),
        )

    def test_complete_registry_migration_preserves_semantic_witness(self):
        runtime = self._v0_runtime()
        witness = migration.apply_contract_to_runtime(runtime, self.contract)
        expected_v1 = set(self.contract["migration"]["v0_to_v1"].values())
        self.assertEqual(set(runtime.functions), expected_v1)
        self.assertTrue(witness["implementation_objects_preserved"])
        self.assertTrue(witness["semantic_schema_preserved"])
        self.assertNotEqual(
            witness["before"]["exposed_registry_sha256"],
            witness["after"]["exposed_registry_sha256"],
        )
        self.assertEqual(
            witness["before"]["semantic_registry_sha256"],
            witness["after"]["semantic_registry_sha256"],
        )
        self.assertEqual(migration.apply_contract_to_runtime(runtime, self.contract), witness)

    def test_incomplete_or_unwitnessed_registry_is_rejected(self):
        incomplete = self._v0_runtime()
        incomplete.functions.pop("send_email")
        with self.assertRaisesRegex(ValueError, "incomplete or mixed"):
            migration.apply_contract_to_runtime(incomplete, self.contract)

        already_v1 = self._v0_runtime()
        mapping = self.contract["migration"]["v0_to_v1"]
        already_v1.update_functions(
            {v1: FakeFunction(v1) for v1 in mapping.values()}
        )
        with self.assertRaisesRegex(ValueError, "un-witnessed"):
            migration.apply_contract_to_runtime(already_v1, self.contract)

    @unittest.skipUnless(
        importlib.util.find_spec("agentdojo") is not None,
        "AgentDojo is an optional benchmark dependency",
    )
    def test_openai_tool_schema_hook_exposes_v1_names_without_a_model_request(self):
        from agentdojo.agent_pipeline.llms import openai_llm
        from agentdojo.functions_runtime import FunctionsRuntime
        from agentdojo.task_suite.load_suites import get_suite

        suite = get_suite("v1.2.2", "workspace")
        runtime = FunctionsRuntime(suite.tools)
        captured = {}
        original_request = openai_llm.chat_completion_request
        original_manifest = os.environ.get(migration.MANIFEST_ENV)

        def fake_request(_client, _model, _messages, tools, _reasoning_effort, _temperature):
            captured["tools"] = tools
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content=None, tool_calls=None))]
            )

        openai_llm.chat_completion_request = fake_request
        os.environ[migration.MANIFEST_ENV] = str(FIXTURE)
        try:
            llm = openai_llm.OpenAILLM(client=object(), model="local-test")
            llm.query("", runtime, messages=[])
        finally:
            openai_llm.chat_completion_request = original_request
            if original_manifest is None:
                os.environ.pop(migration.MANIFEST_ENV, None)
            else:
                os.environ[migration.MANIFEST_ENV] = original_manifest

        tool_names = {tool["function"]["name"] for tool in captured["tools"]}
        self.assertIn("v1_send_email", tool_names)
        self.assertNotIn("send_email", tool_names)
        self.assertTrue(getattr(runtime, migration._RUNTIME_MARKER)["semantic_schema_preserved"])

    @unittest.skipUnless(
        importlib.util.find_spec("agentdojo") is not None,
        "AgentDojo is an optional benchmark dependency",
    )
    def test_attested_dispatch_uses_v1_runtime_name_and_v0_policy_name(self):
        from experiments import agentdojo_attestation_adapter as adapter
        from agentdojo.agent_pipeline import agent_pipeline as pipeline_module
        from agentdojo.functions_runtime import FunctionCall, FunctionsRuntime
        from agentdojo.task_suite.load_suites import get_suite

        suite = get_suite("v1.2.2", "workspace")
        runtime = FunctionsRuntime(suite.tools)
        migration.apply_contract_to_runtime(runtime, self.contract)
        env = suite.load_and_inject_default_environment({})
        previous = {
            migration.MANIFEST_ENV: os.environ.get(migration.MANIFEST_ENV),
            adapter.ALLOWLIST_ENV: os.environ.get(adapter.ALLOWLIST_ENV),
        }
        os.environ[migration.MANIFEST_ENV] = str(FIXTURE)
        os.environ[adapter.ALLOWLIST_ENV] = "get_current_day"
        adapter._AUDIT_LOG.clear()
        try:
            call = FunctionCall(function="v1_get_current_day", args={}, id="contract-call")
            messages = [{"role": "assistant", "content": None, "tool_calls": [call]}]
            executor = pipeline_module.ToolsExecutor()
            _, _, _, output, _ = executor.query("", runtime, env, messages, {})
        finally:
            for name, value in previous.items():
                if value is None:
                    os.environ.pop(name, None)
                else:
                    os.environ[name] = value

        self.assertIsNone(output[-1]["error"])
        self.assertEqual(adapter._AUDIT_LOG[-1]["tool"], "v1_get_current_day")
        self.assertEqual(adapter._AUDIT_LOG[-1]["policy_tool"], "get_current_day")


if __name__ == "__main__":
    unittest.main()
