# Novelty pivot memo (R1 update, 26 September 2026)

> **Superseded for contribution selection on 27 September 2026.** The later
> audit found direct overlap with VIGIL, CXI, CONTINUITY and Assidiqi et al.
> Pivot A remains useful as a mechanism-stress analysis, but it is not a
> defensible stand-alone novelty claim. See `paper/r1_reopening_20260927.md`.

## Executive recommendation

The original contribution claim — "runtime policy enforcement at the tool
boundary against indirect prompt injection" — is no longer defensible as a
stand-alone novelty claim. A 2026 *Electronics* article reports a very close
MCP Policy Enforcement Point (PEP), cross-step information-flow labels,
tamper-evident audit logging, five repeats on a real LLM backend, four attack
classes, four additional backends, and a real MCP filesystem transport
demonstration [Wang et al., 2026]. ActGov also reports per-action runtime
validation on AgentDojo and AgentDyn across four models [Zhang et al., 2026].
PACT covers argument-level provenance and capability contracts on AgentDojo
across five models [Fan et al., 2026]. RAC covers multi-step authorization
drift and reports both controlled and LLM-generated workflow results
[Zhang et al., 2026b].

The paper should therefore be reframed as an empirical extension/replication
with one primary measurable axis. The two defensible options below are ordered
by fit to the existing repository.

Recommended title for Pivot A:

> **From Policy Decision to Side Effect: Semantic Mediation Fidelity for
> LLM-Agent Runtime Guards under Indirect Prompt Injection and Tool/Schema
> Drift**

The title makes the attack setting explicit while signaling that the paper's
primary object of study is post-decision semantic fidelity, not another generic
tool-boundary guard.

## Pivot A (recommended): semantic mediation fidelity under adapter and schema drift

### Core claim boundary

Do not claim a new PEP, capability system, provenance system, or workflow
authorization mechanism. Claim instead:

> We quantify whether a policy decision made on a normalized tool call remains
> semantically true after the call crosses a tool adapter, schema-version
> boundary, or serialization layer.

This is a different endpoint from ordinary pre-execution ASR. The enforcement
layer can correctly deny an unsafe call at its own boundary and still fail if
an adapter silently remaps a permitted call into a different resource,
recipient, operation, or side effect. The current repository already contains
three `executor_alias` cases that intentionally expose this limitation; these
must be promoted from an incidental failure test to a pre-registered primary
stress axis.

### Proposed measurable parameters

Let \(c\) be the canonical call admitted by the guard and \(e(c)\) the
observed post-execution effect from the adapter/sandbox state diff.

* **Semantic Mediation Fidelity (SMF):**
  \[
  \mathrm{SMF} =
  \frac{\#\{\text{ALLOW/APPROVE calls with }e(c)=\mathrm{authorized}(c)\}}
       {\#\{\text{ALLOW/APPROVE calls}\}}.
  \]
* **Adapter-induced Forbidden Effect Rate (AFER):** forbidden effects divided
  by adapter-drift attack cases whose pre-dispatch call passed the guard.
* **Benign Drift Portability (BDP):** clean-task success on harmless alias,
  serialization, and schema-version mutations.
* Keep ordinary ASR/UAR/CTS/FBR as secondary metrics. Report a separate
  **pre-dispatch security** result and **post-effect security** result.

The current pilot result is not a full result for this claim. It only shows
that the existing fixture contains a non-zero adapter mismatch. The manuscript
must report the numerator and denominator for SMF/AFER on a frozen LLM trace
set before making any efficacy statement.

### Experimental matrix

1. Generate/freeze the same LLM traces for every defense and model.
2. Replay each trace through:
   * canonical adapter (control);
   * harmless aliases (`tool`, `resource`, `destination`);
   * schema-version changes and field-order/serialization changes;
   * semantic remapping (adapter sends to a different resource/recipient);
   * malformed or stale adapter metadata.
3. Compare:
   * B0 unsafe;
   * B2 static allowlist;
   * the existing P policy guard;
   * P + canonicalization;
   * P + post-call state-diff/adapter attestation (proposed extension).
4. Use deterministic state-diff/canary oracles. Do not use an LLM judge for the
   primary endpoint.
5. Report paired bootstrap confidence intervals and a per-drift-family
   breakdown.

### Exact research-question edits

Replace the current generic RQ1 with:

> **RQ1 (primary).** When an LLM-generated tool call is routed through
> semantically drifting adapters or schema versions, how often does each
> enforcement configuration preserve the authorization decision through the
> observed side effect, measured by SMF and AFER?

Replace RQ2 with:

> **RQ2.** What is the security–utility trade-off of canonicalization and
> post-call semantic verification under harmless versus adversarial drift,
> measured by BDP, CTS, FBR, approval burden, and p95 end-to-end overhead?

Retain a narrower RQ3:

> **RQ3.** Do adaptive held-out injection traces change pre-dispatch ASR,
> post-effect AFER, or both, across models and tool adapters?

### Exact hypothesis edits

* **H1 (fidelity):** P + post-call semantic verification has lower AFER than
  pre-dispatch-only P on adapter-drift cases; the primary comparison is paired
  with a 95% CI and a preregistered minimum effect.
* **H2 (portability):** P + canonicalization has higher BDP than fail-closed P
  on harmless alias/schema mutations, without increasing AFER on adversarial
  mutations.
* **H3 (cost):** post-call verification increases p95 mediator overhead by no
  more than the preregistered budget; if the budget is exceeded, report the
  trade-off rather than changing the claim.

Do not carry over the old "20 percentage-point ASR reduction" hypothesis
unless the sample-size calculation is redone for the new primary endpoint.

### Exact contribution wording

Use:

1. **A drift-aware evaluation protocol** that separates pre-dispatch policy
   decisions from observed post-adapter effects.
2. **An action-semantic fidelity metric suite** (SMF, AFER, BDP) for measuring
   whether authorization survives interface evolution.
3. **A reproducible adapter mutation harness** with deterministic state-diff
   oracles and paired LLM traces.
4. **An empirical result, positive or negative,** on when post-call
   verification is worth its utility and latency cost.

Do not use "first", "provably secure", "complete mediation", or "solves
policy drift" without a formal scope and evidence.

### Why this pivot is defensible

The closest 2026 runtime-PEP paper evaluates path scope, exfiltration,
cross-step label propagation, rate caps, audit tampering, multiple backends,
and a real MCP transport. Its full paper is especially useful for a precise
gap statement: it reports adapter path-normalisation and says that full
adapter-level path calibration, production-scale transport, and residual
check-to-execution races remain future work [Wang et al., 2026]. Therefore,
Pivot A should be framed as an extension of those stated limitations, not as a
claim that the prior work ignored adapters. ActGov focuses on policy
construction and per-action authorization, while RAC focuses on workflow-level
authorization lineage; neither should be described as a direct evaluation of
post-adapter effect equivalence. This is a scope distinction, not a claim that
no unpublished system tests adapters.

## Pivot B (secondary): security per human approval and approval fatigue

### Core claim boundary

Treat the guard as a selective mediator and evaluate the operational cost of
its `REQUIRE_APPROVAL` decisions. The novelty is an evaluation axis and
paired protocol, not a new approval primitive.

The closest runtime-PEP work reports ASR, task utility, rule false positives,
and sub-millisecond overhead, but does not make approval workload the primary
endpoint [Wang et al., 2026]. AgentSpec includes user confirmation as one
enforcement action but is a general DSL, not a controlled approval-budget
study [Wang et al., 2026b]. A 2026 systematic analysis argues that policy
specification, runtime approval, and scope configuration dominate deployed
practice while approval fatigue remains under-evaluated [Wang et al., 2026c].

### Proposed measurable parameters

* **Approval Burden (AB):** approval requests per episode, split into benign
  and attack episodes.
* **Necessary Approval Rate (NAR):** approvals required for a legitimate
  high-risk action divided by all approvals.
* **Approval Waste Rate (AWR):** approvals triggered by actions that would
  have been safely allowed or denied by the deterministic oracle.
* **Secure Task Success at budget \(B\) (STS@B):** secure task success under a
  fixed maximum number of human approvals per episode.
* **Security-per-Approval (SPA):** prevented forbidden effects per approval
  request. This must be reported together with CTS/FBR; it is not a
  replacement for security rate.

Do not call synthetic approval latency a human-subject result. If no human
study is run, call it "approval-event burden" and use a preregistered review
time model only as sensitivity analysis.

### Exact research-question edits

> **RQ1 (primary).** At a fixed security target, how many approval events per
> episode are required by each defense, and what fraction of those approvals
> are necessary rather than avoidable?

> **RQ2.** How does an approval budget change secure task success, benign
> completion, and false-block rate across attack families and models?

> **RQ3.** Does adaptive/held-out injection increase approval burden even when
> post-effect ASR remains low?

### Exact hypothesis edits

* **H1:** The proposed selective policy has higher NAR and lower AWR than
  approval-everything B5 at matched post-effect ASR.
* **H2:** STS@B decreases smoothly as the approval budget is reduced; report
  the full Pareto curve rather than one threshold.
* **H3:** Adaptive attacks increase AB more than non-adaptive attacks at the
  same ASR, indicating an operational cost not visible in ASR alone.

### Why this pivot is defensible

It directly answers the practical objection that ASR can be reduced by blocking
or escalating almost everything. It also turns the existing approval counter
into a first-class endpoint without pretending that one pilot approval event
is evidence about real operators. The paper must add either a human review
experiment or a clearly labeled event-level proxy; otherwise this remains a
secondary systems-analysis contribution.

## Pivots that should not be used as the sole novelty claim

* **Generic runtime PEP/least privilege/capability enforcement:** already
  covered by the 2026 MCP PEP paper, CaMeL, Fides, Progent, AgentArmor,
  ClawGuard, and ActGov.
* **Argument-level provenance:** PACT directly claims this abstraction and
  reports AgentDojo results across five models.
* **Workflow authorization drift/lineage:** RAC directly targets this failure
  mode and reports a large TraceBench evaluation.
* **Hidden policy/world state:** PhantomPolicy/Sentinel already defines this
  class and evaluates world-state-grounded enforcement. It can be an external
  stress condition, but should not be presented as an unclaimed invention.

## Minimum full-LLM run needed for a defensible paper

For either pivot, the current offline post-LLM trace simulator is insufficient.
The minimum artifact should include:

* at least three model backends, including one open-weight reproducible model;
* pinned benchmark commit and adapter code for AgentDojo and/or InjecAgent;
* frozen policy, prompt, seed, decoding, model identifiers/checksums, and
  redacted raw traces;
* the same trace replayed through all baselines and all drift mutations;
* deterministic post-effect state-diff/canary oracle;
* per-case numerator/denominator for ASR, SMF/AFER/BDP or AB/NAR/AWR/STS@B;
* paired bootstrap or exact paired tests, 95% confidence intervals, effect
  sizes, and multiplicity correction;
* mediation-bypass tests and adapter-failure tests;
* an explicit negative-result table. If an endpoint does not improve, the
  manuscript must report the trade-off or replication result rather than
  changing the contribution after seeing the data.

## Source notes

The closest-prior distinctions in this memo are based on the primary papers
listed below. They should be added to `references.bib` before the manuscript is
frozen.

* Wang, Zhu, and Li. "Runtime Policy Enforcement for MCP-Based LLM Agents."
  *Electronics* 15(13), 2829, 2026. DOI:
  10.3390/electronics15132829
  (https://doi.org/10.3390/electronics15132829).
* Wang, Poskitt, and Sun. "AgentSpec: Customizable Runtime Enforcement for
  Safe and Reliable LLM Agents." ICSE 2026. DOI:
  10.1145/3744916.3764546 (https://arxiv.org/abs/2503.18666).
* Fan et al. "The Granularity Mismatch in Agent Security: Argument-Level
  Provenance Solves Enforcement and Isolates the LLM Reasoning Bottleneck."
  arXiv:2605.11039, 2026 (https://arxiv.org/abs/2605.11039).
* Zhang, Peng, Jiang, and Zhang. "ActGov: Governing LLM Agent Actions via
  Policy-Constrained Validation." arXiv:2609.24446, 2026
  (https://arxiv.org/abs/2609.24446).
* Zhang, Lee, Zhuang, and Peng. "Runtime Authorization Consistency Checking
  for MCP-based Agentic Workflows." arXiv:2609.23498, 2026
  (https://arxiv.org/abs/2609.23498).
* Wu and Gong. "Policy-Invisible Violations in LLM-Based Agents."
  arXiv:2604.12177, 2026 (https://arxiv.org/abs/2604.12177).
* Wang, Li, and Tian. "Reframing LLM Agent Security as an Agent-Human
  Interaction Problem." arXiv:2605.24309, 2026
  (https://arxiv.org/abs/2605.24309).
