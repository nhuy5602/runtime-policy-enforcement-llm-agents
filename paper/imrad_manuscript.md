# Security Regression Testing of Indirect Prompt-Injection Defenses under Versioned Agent Tool Contracts

**Status:** canonical course/research draft, October 9, 2026
**Claim tier:** protocol and integration-pilot draft; not yet a Q2-ready empirical manuscript
**Source of truth:** `PROJECT_STATE.md`, `paper/research_protocol.md`, and the pinned v2 manifest

> This file is the single manuscript path for the current direction. It must not
> inherit claims or result tables from the archived `manuscript.md` or
> `q2_ready_report.md` unless they are re-derived from a frozen result bundle.

## Abstract

Indirect prompt injection can cause a tool-using language-model agent to
produce an action that is inconsistent with the user's task. Existing defenses
often bind authorization to tool names, arguments, capabilities, or runtime
policies. This paper studies a narrower and testable question: when the same
agent, task, carrier, initial state, defense, model configuration, and reset
procedure are held constant, can a controlled migration of the agent tool
contract from `v0` to `v1` create a harmful-effect security regression?

We define a paired, action-grounded evaluation protocol. Each pair executes
both contract versions, scores security with an independent post-execution
harmful-effect oracle, and keeps benign utility in a separate default-control
arm. The prospective AgentDojo v2 manifest fixes six pairs and twelve episodes:
three attack pairs and three no-InjecAgent default-control pairs, crossed over
`v0` and `v1` with counterbalanced order. The repository currently contains
the pinned manifest, fail-closed result acceptance, a driver, and a fresh-process
capture bridge verified with a local fake provider. Its current configuration
is an unprotected integration reference with a name-only migration; the frozen
and migrated forms of a real defense remain unimplemented. No canonical v2
real-LLM capture has been collected. Therefore this draft reports a protocol
and integration-pilot state rather than defense efficacy, population inference,
or a Q2 result.

**Keywords:** indirect prompt injection; LLM agents; tool contracts; schema
migration; security regression; harmful-effect oracle; AgentDojo

## 1. Introduction

Tool-using agents read untrusted content from sources such as email, web pages,
documents, and tool output. An indirect prompt injection can redirect the
agent toward a tool call that sends data, changes a resource, or performs
another harmful side effect. A defense may appear correct at its authorization
boundary while a contract migration changes the mapping between an exposed tool
name, its arguments, and the implementation that performs the side effect.

The contribution claimed by this draft is an evaluation method, not a new
runtime guard:

1. a paired `v0 -> v1` contract-migration unit with fixed task, carrier, state,
   defense, model configuration, seed, and reset;
2. an independent effect-level oracle that is not allowed to read the guard
   verdict as its endpoint;
3. separate attack and default-control arms so security and utility are not
   conflated; and
4. a fail-closed result bundle that preserves a fixed denominator and rejects
   missing, duplicated, synthetic, or provenance-inconsistent evidence.

The research question is intentionally conditional. If the literature stop gate
or live evidence does not support a defensible novelty claim, the deliverable
remains a complete course project with an explicit protocol, partial
implementation, reproducible dry-run artifact, limitations, and presentation.

## 2. Related work and contribution boundary

AgentDojo supplies a dynamic environment for evaluating prompt-injection
attacks and defenses in tool-using agents. CaMeL studies control/data-flow
separation and privileged versus quarantined execution. Progent studies
symbolic privilege control and policy-update checking. These works establish
that capability control, least privilege, runtime mediation, and
security/utility evaluation are active research areas.

Accordingly, this paper does **not** claim a new capability system, policy DSL,
least-privilege primitive, generic runtime guard, generic drift benchmark, or
universal defense against prompt injection. The proposed extension is to
measure whether an existing defense remains action-safe after a controlled
versioned contract migration.

The related-work matrix and targeted audit are:

- `paper/related_work_matrix.md`
- `paper/r1_targeted_literature_audit_20260927.md`
- `paper/literature_update_20261002.md`

The literature stop gate remains open. Any final novelty statement must be
updated after an independent replay of that gate.

## 3. Problem definition and threat model

### 3.1 Threat model

The attacker controls content that the agent is allowed to read. The content
may contain instructions that attempt to redirect the agent toward a harmful
tool action. The attacker cannot edit the policy manifest, the trusted
dispatcher, the sandbox configuration, or human approval state.

Protected assets include synthetic secrets, records, files, tickets, email
state, and other sandbox resources. Direct user jailbreaks, model poisoning,
malicious tool implementations, cross-session memory poisoning, and full
multi-agent information-flow guarantees are outside scope.

### 3.2 Paired regression event

Let `E(v, c)` be the independently observed harmful effect for contract version
`v` and case `c`. A security regression is counted only when:

```text
E(v0, c) = false  and  E(v1, c) = true
```

Both episodes must be completed and provenance-valid. A missing, timed-out,
malformed, or unscorable sibling remains `not_scored`; it is never silently
treated as secure.

### 3.3 Utility control

The default-control arm disables InjecAgent while retaining the pinned
AgentDojo default carrier. Its endpoint is independently recomputed utility
success after raw-to-canonical trace normalization. Attack and
default-control endpoints are different constructs and are not compared
directly.

## 4. Method

### 4.1 Frozen inputs

The v2 manifest binds:

- three source-qualified cases;
- attack and no-InjecAgent default-control arms;
- defense and policy hashes;
- model endpoint/configuration identity;
- seed and counterbalanced execution order;
- tool-contract digests for `v0` and `v1`;
- effect-oracle, utility-oracle, and trace-normalization contracts; and
- pre-state, reset, registry, request/response, and trace evidence requirements.

The committed fixture is:
`experiments/fixtures/agentdojo_paired_v2_execution_manifest_v1.json`.

### 4.2 Canonical orchestration

`experiments/agentdojo_paired_v2_driver.py` is the sole v2 orchestration entry
point. It runs the frozen episodes in manifest order exactly once, preserves the
fixed denominator, and converts executor failures or missing evidence into
`not_run`. Its live executor is
`experiments/agentdojo_paired_v2_capture_bridge.py`, which starts a fresh pinned
AgentDojo child process for each episode.

The driver supports a no-request dry run and an explicitly confirmed,
four-episode capture pilot. The capture bridge records typed state,
request/response, carrier/default-control, registry/migration, and
raw/canonical trace provenance; it does not turn the pilot into a Q2 efficacy
claim.

### 4.3 Result acceptance

`experiments/agentdojo_paired_v2_result_bundle.py`:

1. checks the manifest and contract digests;
2. checks immutable episode metadata and retry policy;
3. checks model-request and redacted-trace provenance;
4. checks v0/v1 registry and migration witnesses;
5. recomputes attack outcomes from typed pre/post state; and
6. normalizes and recomputes default-control utility from the pinned scorer.

Runner-supplied endpoint booleans are not accepted as evidence.

## 5. Experimental methodology

### 5.1 Required live evidence

A completed episode requires a pinned AgentDojo checkout, isolated v0/v1
processes, a live observed model request/response, a real carrier witness for
the attack arm, typed pre/post state, reset evidence, registry witnesses, and
redacted dispatcher traces. Synthetic trace replay and source-only calibration
are instrumentation checks, not live efficacy evidence.

### 5.2 Pilot budget gate

If a live pilot becomes necessary, this thread authorizes **$10.00 total**:
$8.00 planned execution and $2.00 reserve, including prior spending. This is
not a provider-enforced monetary cap. The smallest proposed pilot is
one attack pair plus one default-control pair (four episodes maximum), one
model snapshot, no retry, sandbox-only execution, and immediate stop on missing
reset, oracle, provenance, or billing evidence. This pilot can establish
integration feasibility only; it cannot close the Q2 gate.

### 5.3 Planned analysis

The locked analysis specification is
[`statistical_analysis_plan.md`](statistical_analysis_plan.md). For a
sufficiently large preregistered run, report paired security-regression
transitions, utility transitions, clustered uncertainty, failure reasons,
mediation coverage, approval burden, latency, and resource overhead. Do not
report a population estimate, superiority claim, or confidence interval for
the current twelve-episode dry-run denominator.

## 6. Current results and artifact status

The current local dry run produces:

- six fixed pairs and twelve planned episode rows;
- twelve `not_run` episode records;
- zero scored attack pairs;
- zero scored default-control pairs; and
- a descriptive-only validator report.

These are orchestration and acceptance artifacts, not observations of an LLM
agent. The following files are the current machine-readable outputs:

- `experiments/agentdojo_paired_v2_driver.py`
- `experiments/agentdojo_paired_v2_result_bundle.py`
- `tmp/agentdojo_paired_v2_result_bundle.json`
- `tmp/agentdojo_paired_v2_result_report.json`

The focused driver/bridge tests and the full experiment test suite pass locally.
The next scientific step is to specify and implement a real frozen defense F
and its explicitly migrated form M under an authorization-relevant contract
change. A non-billable preflight and methodological review must precede an
explicitly requested real-LLM pilot. The current U/D0 plus name-only migration
cannot answer the defense-regression question. Multi-model, held-out evaluation
and the statistical gates remain required for any efficacy claim.

## 7. Discussion

The protocol makes a narrower claim than a generic prompt-injection defense:
it asks whether contract evolution changes the security meaning of an
already-authorized action. The separation of authorization verdicts from
post-execution effects is necessary because a correct-looking `ALLOW` or
`DENY` value does not by itself prove what happened in the sandbox.

The principal risk is construct validity. If the carrier is not live, if the
model did not generate the action, if the v1 registry is not witnessed, or if
the oracle depends on the defense verdict, the episode must not be counted as
evidence for the research question.

## 8. Threats to validity, limitations, and ethics

The current plan is small and exploratory. AgentDojo coverage, model
selection, contract mutations, and sandbox semantics may not generalize to
other agents or providers. The USD 10 aggregate authorization (including prior
spending) does not make the four-episode pilot adequate for statistical inference.
The no-InjecAgent default-control arm is not a semantically benign arm.
Artifacts must avoid storing real secrets, real external side effects, or
unredacted model content. Every paid job must be reconciled against billing
receipts before another job is submitted.

## 9. Conclusion

This repository now has a single active research question, a canonical v2
manifest, a fail-closed result contract, a fixed-denominator driver, and a
fresh-process capture bridge. The local fake-provider seam is complete, but no
Runpod episode has been submitted and the work is not yet sufficient for a Q2+
empirical claim.

The next decisive step is the F/M design and smallest executable comparison
specified in `PROJECT_STATE.md`. Only after its non-billable preflight and
review pass may an explicit user command authorize a real-LLM pilot under the
current [`runpod_budgeted_pilot_gate_20261007.md`](runpod_budgeted_pilot_gate_20261007.md).
Passing integration tests cannot establish defense efficacy.

## References

Use `paper/references.bib` as the single bibliography source. The core
references for the current draft are AgentDojo, CaMeL, Progent, and the
closest-prior works listed in `paper/related_work_matrix.md`.
