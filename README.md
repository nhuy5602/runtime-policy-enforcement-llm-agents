# Runtime Policy Enforcement for LLM Agents

Research repository for the paper **Runtime Policy Enforcement for LLM Agents Against Indirect Prompt Injection and Tool Misuse**.

This repository is for building the final scientific paper and its reproducible research artifacts. It intentionally excludes weekly class reports and unrelated course files.

## Current status

The manuscript is a research proposal plus a preliminary component-level validation. The current simulator verifies policy enforcement at a mock tool boundary; it is **not** an LLM benchmark and does not establish resistance to prompt injection in a real Agent.

## Repository layout

```text
paper/
  manuscript.md            Scientific report draft
  research_protocol.md     Threat model, RQs, protocol, and planned evaluation
experiments/
  policy_guard_sim.py      Offline policy-conformance simulator
  policy_guard_sim_results.json
```

## Run the prototype check

The current prototype has no third-party Python dependencies.

```powershell
python experiments/policy_guard_sim.py --self-test --output experiments/policy_guard_sim_results.json
```

The expected component result is that the policy guard denies all four pre-recorded harmful calls, automatically allows two benign calls, and routes one benign high-risk call to approval. This is a conformance result on a fixed fixture, not an attack-success-rate result for an LLM.

## Research scope

The study investigates whether a runtime policy gateway can prevent an Agent's proposed tool call from producing an unauthorized side effect after the Agent has read untrusted external content. The primary future experiment will compare an unsafe Agent, a prompt-only baseline, a static tool filter, and the proposed policy guard on AgentDojo or an equivalent sandbox.

The study does not claim a new capability system, information-flow-control mechanism, or generic solution to prompt injection. It evaluates a transparent policy profile, action-grounded security oracles, and the trade-offs among security, utility, approval burden, and latency.

## Next research steps

1. Version the case manifest, policy manifest, and scoring oracle separately from the simulator.
2. Add session binding, expiry, argument-level constraints, state-diff logging, and a bypass-resistance integration test.
3. Run the preregistered AgentDojo evaluation with a real LLM Agent and report paired outcomes, confidence intervals, latency, and failure cases.
