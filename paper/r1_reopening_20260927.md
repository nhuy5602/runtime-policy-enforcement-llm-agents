# R1 reopening record — 27 September 2026

## Decision

**R1 is OPEN.** The prior working direction, *semantic mediation fidelity
under tool-adapter drift*, is retired as a stand-alone novelty claim. It may
remain a mechanism-validation stress test, but it is not a sufficient Q2 paper
contribution by itself.

This correction is based on a fresh closest-prior audit, not on the pilot
outcomes. In particular, VIGIL already studies verify-before-commit against
tool-stream injection; CXI binds field, effect and invocation authority;
CONTINUITY studies transformation witnesses and effect-bound permits; and
Assidiqi et al. study schema, policy and toolset drift. The project must not
describe its adapter attestation as a new generic enforcement mechanism,
post-call contract, or first drift benchmark.

## Candidate replacement direction (not locked)

> **When Safe Tools Change: Security Regression Testing of Indirect
> Prompt-Injection Defenses under Versioned Agent Tool Contracts**

The candidate contribution is an empirical benchmark/evaluation, rather than
another generic guard. A paired episode runs the same task and indirect-prompt
injection carrier under contract `v0` and a controlled `v1` migration. The
primary endpoint is an action-grounded security regression: an unsafe effect
that is prevented under `v0` but occurs under `v1`.

The candidate remains eligible only if the literature audit does not find a
prior real-agent evaluation combining all three properties below:

1. indirect prompt injection delivered through retrieved content or tool
   output, rather than tool metadata poisoning;
2. explicit, versioned tool-contract migration between paired conditions; and
3. a deterministic harmful-effect oracle on an executing LLM agent.

No “first” claim is permitted even if the audit finds no exact match.

## Proposed research questions

| ID | Question | Primary measurement |
|---|---|---|
| RQ1 | Do IPI defenses that prevent a harmful effect under `v0` retain that protection after a versioned tool-contract migration to `v1`? | Paired security-regression rate, effect-ASR |
| RQ2 | Which migration family creates the largest regression while schema validity and benign end-state success remain acceptable? | Stratified paired rates across rename/alias, new precondition/approval, and authorization-relevant sink/scope changes |
| RQ3 | Can a conservative **migrate-or-escalate** policy reduce regression relative to a frozen policy, and at what benign-success and approval cost? | Effect-ASR, clean end-state success, escalation rate, latency |

`migrate-or-escalate` is a benchmark baseline: when a migration has no
machine-checkable equivalence witness, it escalates instead of attempting a
semantic repair. It is not a claim of a new authorization primitive.

## Non-negotiable protocol changes

- Freeze paired `v0 -> v1` contracts, attack carriers, state oracle and split
  before test execution; keep the model blind to the test label and canonical
  target.
- Use an idempotent/staged sandbox executor. A post-effect state difference is
  evidence of detection/audit only unless the effect has not yet crossed an
  irreversible finality boundary.
- Run actual matched agents, not transformations of a hand-labelled proposal
  trace. Keep model, tool budget, reset protocol and carriers fixed between
  configurations.
- Treat source templates—not mutations of seven fixture calls—as the
  independent clustered unit. Pre-register missing-run handling, paired
  interval/test, multiplicity correction and stopping rule.
- Archive a redacted request/response trace, benchmark commit and lockfile
  hash, endpoint release/configuration, actual request parameters, model
  revision, result manifest and deterministic scorer output for every run.

## Closest-prior audit and scope boundary

| Work | Direct overlap | Boundary for this candidate |
|---|---|---|
| VIGIL [lin2026vigil] | IPI plus verify-before-commit and a tool-stream injection benchmark | Do not reuse its mechanism claim; test contract-version regression instead. |
| CXI [santosgrueiro2026cxi] | Exact-effect/invocation authority on AgentDojo episodes | Do not claim effect authorization; measure whether existing defenses regress across releases. |
| CONTINUITY [zheng2026continuity] | Transformation witnesses, policy evolution and finality permits | Do not claim transformation integrity; its deterministic non-LLM evaluation motivates a real-agent evaluation gap only. |
| Assidiqi et al. [assidiqi2026drift] | Schema, policy and toolset drift with end-state task success | Add IPI and harmful-effect security regression; do not rebrand generic drift adaptation as new. |
| AgentDojo [debenedetti2024agentdojo] | Executing-agent IPI benchmark | Pin the source/runtime and expose the migration condition through the actual tool contract. |

## Literature-audit stop gate

Before the working title is promoted to the manuscript, search arXiv,
Crossref/IEEE Xplore, ACM Digital Library and ACL Anthology with the combined
terms `indirect prompt injection`, `tool contract/schema migration/version`,
`security regression`, `agent`, `action/effect oracle`, and the names of the
closest systems. Record the date, query, inclusion/exclusion reason, venue,
artifact availability and overlap decision for every included result.

If a prior work is found with all three eligibility properties, pivot instead
to a clearly labelled replication or to the SOC delayed-memory-poisoning
candidate described in the Teacher review. Do not retroactively reinterpret a
negative benchmark outcome as novelty.

## Audit record

The initial targeted screen is recorded in
[`r1_targeted_literature_audit_20260927.md`](r1_targeted_literature_audit_20260927.md).
It found no direct all-property overlap **within the screened source set**, but
it is not a systematic review and therefore does **not** close R1 or authorize
a novelty/"first" claim. An independent replay across the named indexes is
still mandatory.
