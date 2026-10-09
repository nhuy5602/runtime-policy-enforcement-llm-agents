# Q2 claim-gate review — 02 October 2026

> **Historical snapshot.** The gate table and reviewer notes below record the
> repository state audited on 2 October 2026. The dated 7 October addendum at
> the end supersedes implementation-status statements where the v2 validator,
> driver, capture bridge, and local seam have since changed; it does not
> supersede the Q2 efficacy verdict.

## Verdict

**FAIL / continue work.** The study has a defensible drift-focused research
question and a useful enforcement-boundary artifact, but the current evidence
does not support an efficacy or superiority claim for LLM agents. The manuscript
must remain labelled **protocol + trace-replay pilot** until the independent
benchmark, end-to-end model matrix, fair baselines, clustered statistics and
clean-room artifact are complete.

This review is intentionally stricter than a self-test: a passing unit test
proves an implementation invariant, not the corresponding scientific claim.

## Gate audit

| Q2 gate | Current evidence | Verdict | Required evidence before acceptance |
|---|---|---|---|
| Novelty boundary | Targeted closest-prior screen in `paper/r1_targeted_literature_audit_20260927.md`; generic runtime enforcement is explicitly not claimed as new | **Partial** | Independent replay across the named indexes, then a measurable difference or a clearly labelled replication/negative result |
| Independent benchmark | V1 remains blocked. V2 retains all 60 structural rows and selected 3 source-qualified cases; its decision-independent monotone state oracle has 15 local controls plus a 3-case fresh/positive scorer-interface check. The 03 October selected-binding fixture recorded a three-case pre-state mismatch, but a preserved 05 October adjudication runs three freshly started processes over all three cases (9 trials) and reproduces every frozen carrier, injection-map and pre-state witness in one recorded environment. Its package manifest does not independently attest the dependency-installation/build path. A prospective 06 October default-control contract pins the initial state/upstream utility dispatcher, trace canonicalization resolves renamed v1 tool traces, and a new v2 preregistration freezes 6 pairs/12 episodes with distinct attack and default-control arms. All are source-only or preflight artifacts: default carrier text remains, synthetic v1 renaming is not a runtime, and no result-bundle validator, driver, reset/trace provenance, fair baseline, or LLM evidence exists. | **Fail** | Create a v2 result-bundle validator and manifest-bound driver consuming both contracts, with full snapshot/schema and case/arm/carrier/run/trace provenance, reset/source witnesses, frozen scorer/split/budget, fair baselines and redacted traces; then execute the independent model matrix |
| End-to-end LLM efficacy | One paired Qwen3-8B AgentDojo episode completed: both tracks have `utility=true`, `security=false`, and no target `send_email`; no drift, held-out templates, attack-success pair, or independent model | **Fail** | ≥3 model snapshots (≥1 open-weight), realistic carrier, same cases across executable configurations, and drift-aware test results |
| Adapter/state attestation | `experiments/adapter_attestation.py` plus one wildcard-attested integration trace; its process-level sidecar is not an attack oracle and no target attack reached the adapter | **Partial** | Execute a least-privilege attestation in an attack-positive end-to-end benchmark and demonstrate that no irreversible effect crosses before verification; otherwise claim only staged-transaction conformance |
| Fair baselines | Synthetic rows B0/B1/B2/B4 are trace transformations; B3/B5/B6 and external systems are not executed | **Fail** | Implement and freeze executable closest-prior baseline(s) with identical model, prompt, tools, budget and reset protocol |
| Statistics | Synthetic case-level bootstrap is explicitly descriptive. The new manifest pre-registers a v0/v1 pair unit and no-replacement `not_scored` policy, but there is still no independent episode population, paired result, cluster bootstrap or mixed-effects analysis. | **Fail** | Pre-register unit of analysis, source-template clustering, paired CI/test, model/task random effects, multiplicity correction and missing-run handling |
| Reproducibility | Pinned source/lock metadata, self-tests and two target traces exist; the historical one-episode runner manifest/logs are ignored and no full-run environment or main table is reproducible | **Partial** | One clean-room command reproducing main tables from a pinned environment and archived trace manifest |
| IMRaD/results integration | `paper/q2_ready_report.md` separates protocol from pilot, but E5 still contains planned tables and synthetic “baseline” rows that can be misread as LLM results | **Partial** | Keep protocol/pilot labels in title, abstract, tables and conclusion; replace pending cells only from run-linked results |

## Corrections applied to the manuscript

### Paired-design correction — 02 October 2026

**Student action.** The old pilot plan compared two tracks only after applying
the migration and therefore could not measure a `v0 -> v1` regression. The new
[`agentdojo_paired_v0_v1_execution_manifest.py`](../experiments/agentdojo_paired_v0_v1_execution_manifest.py)
and locked fixture enumerate six immutable units (three attack and three
planned no-injection benign rows), each with exactly one counterbalanced
`v0` and `v1` sibling. They bind case, carrier/no-carrier construction, D0,
model-configuration metadata, seed, reset/pre-state evidence, registry witness
and the decision-independent effect oracle. The generator makes zero model,
network, sandbox, tool, or remote-job calls.

**Teacher verdict.** Accept this as a preregistration and reproducibility
correction; reject it as efficacy evidence. The current `D0` is explicitly an
unmodified-pipeline reference, the model revision and sampling controls remain
unobserved, and no driver yet captures the required typed pre/post states. A
completed paired run must preserve those evidence fields and a separately
frozen task-scoped D1 policy before it can support a defense-comparison or
security-regression result.

1. The one-episode AgentDojo smoke is summarized only from the two committed
   target traces in `experiments/independent_runs/agentdojo_smoke_summary.json`.
   Both raw AgentDojo `security` flags are `false`; neither trace proposes or
   executes `send_email`. The old summary's contrary `send_email`/email-state
   statement was removed. This is an integration fact, not an attack-defense
   result.
2. Synthetic B0/B1/B2/B4 rows are labelled **trace-emulator/reference
   transformations**, not executed LLM baselines. Their rates cannot support
   “guard beats prompt-only” or LLM ASR claims.
3. “Probability” language is reserved for a sampled independent episode
   population. For the current fixture and synthetic matrix, use “observed
   forbidden-effect count/rate in the evaluated cases”.
4. P2 is described as a staged post-verification/rollback contract. It is not
   evidence that an adapter has undone an irreversible external effect after
   emission.
5. The 198 rows are mutation cases clustered around **7 source components**
   (3 and 4 in the locked development/test split). Row-level bootstrap
   intervals are descriptive diagnostics, not population confidence intervals;
   the full run must use clustered/paired analysis.
6. The AgentDojo pilot-case manifest is now source-pinned and outcome-blind,
   but it is recorded as `not_run`. Its three hash-selected feasibility rows
   cannot be reported as an LLM benchmark, an ASR/AFER estimate, or evidence
   of a v0/v1 drift effect.
7. Source-only oracle qualification exposes a concrete dataset/oracle defect:
   the selected `user_task_18`/`injection_task_0` case has a false predicate
   even after its own deterministic ground truth on the exact injected state.
   This blocks the historical plan instead of treating a false raw `security`
   flag as a secure result. The two remaining qualifying cases are still not
   an executable sample, efficacy evidence, or a licence to replace the third
   case by hand.
8. V2 is a transparent prospective amendment, not a retroactive repair: it
   retains the failed v1 pool, censes every structural candidate before a
   derived-seed selection, and labels task-3 email-content-exfiltration as a
   changed threat family. Its predicate can under-detect duplicate or
   extra-recipient sends, so the artifact validates only canonical AgentDojo
   predicate satisfaction—not broad exfiltration prevention.
9. The new v2 effect-oracle contract is accepted only as a source-pinned
   measurement repair. It scores typed pre/post state without reading policy,
   guard, adapter, model-label or upstream aggregate-security inputs, and
   marks incomplete evidence `not_scored`. Its 15 local controls repair the
   exact-count regressions for calendar and email, but create zero LLM,
   utility, prevention, causal or statistical observations.
   The source verifier's three fresh/positive score checks validate only the
   API wiring; their caller-supplied state and witness fields are not run
   provenance and cannot be aggregated as benchmark rows.

## Reviewer questions that remain unanswered

1. What is the exact independent unit of analysis: task, source template,
   attack instance, model seed, or adapter mutation? Why is the chosen unit
   independent for the reported CI?
2. Does the end-to-end track expose the transformed registry and carrier to the
   model without revealing the attack label, fixture ID or canonical target?
3. For B1/B2/B4, is a real model prompted and allowed to generate calls, or is
   the harness only mutating a pre-labelled trace? If the latter, why are those
   rows called baselines?
4. Can the executor perform an irreversible external action before returning an
   observed descriptor? If yes, P2 is detection/audit, not prevention.
5. Which failures are model non-attacks, guard denials, adapter mismatches and
   oracle errors? Are all denominators fixed before looking at test outcomes?
6. What evidence shows that the independent oracle does not reuse policy labels,
   model-provided sensitivity fields or the expected effect generated by the
   same code under test?
7. Why do the three feasibility strata cover calendar creation, Drive deletion
   and email egress, and what pre-specified rule—not observed model behavior—
   will define the eventual statistical episode population beyond this pilot?

## Teacher review of this round

**Decision: accept the preregistration artifact; reject any efficacy claim.**
The manifest materially improves traceability because it fixes the candidate
population and selection before a new completion is requested. It does not
solve independence or external validity: 840 rows share user tasks, carriers
and injection goals, while the selected three are a deliberately tiny
feasibility set. A valid later analysis still needs a run-bound driver,
independent episode definition and clustering plan, executable fair baselines,
an attack-positive end-to-end matrix, and model replication. Any manuscript
sentence that calls this artifact a benchmark result should be rejected.

The new execution plan is also accepted only as a preflight artifact. It
correctly refuses to treat a generic InjecAgent CLI call with a missing
`--injection-task` as a benign twin, and it reserves error/timeout/invalid
traces as `not_scored`. It still does not provide a driver, a frozen non-wildcard
attestation policy, a completed oracle result, or a fair comparison.

**Round-specific teacher audit:** this plan contributes reproducibility, not
novelty. Methodologically it fixes planned invocation/task-episode cardinality
and prevents a false benign control; statistically it creates zero independent
observations; ethically it performs zero external actions. It therefore cannot
support an efficacy, prevention, causal, cost-control, or Q2-readiness claim.

**Oracle-qualification teacher audit:** accept the fail-closed rejection of
the email case; reject any attempt to run the old plan, manually swap in an
email case, or label the negative control as an LLM security result. The local
ground-truth calibration is useful validation of the benchmark measurement
instrument, but it does not evaluate an LLM or the proposed guard. A new
pre-registered, oracle-qualified selection must precede any endpoint use.

**V2-selection and effect-oracle teacher audit:** accept the census,
derived-seed selection and the later decision-independent monotone
measurement contract as reproducibility/measurement repairs. The contract
correctly detects duplicate calendar/email effects and target egress through
extra recipients, CC, BCC or trash without consuming the guard's own label. Reject
claims that this restores the old plan, validates a security defense, measures
an LLM, or detects paraphrased/partial leakage. Before an efficacy paper,
execute a paired, reset-verified model matrix through a dedicated driver with
a genuine benign arm, fixed denominators, full snapshot validation and
case/arm/carrier/run/trace provenance, and redacted traces.

**Historical selected-binding regeneration teacher audit — 03 October 2026
(superseded as a current mismatch claim):** the preserved audit fixture
recorded a three-case mismatch and the then-current teacher review rejected
execution, scoring, or silent re-hashing of the historical v2 plan. That
fixture is retained rather than edited, but its mismatch conclusion must now
be read with the 05 October adjudication below; it is not a current empirical
finding. Neither the historical fixture nor the correction is LLM efficacy,
statistics, novelty, or Q2 evidence.

**Selected-binding regeneration adjudication — 05 October 2026:** the teacher
rejects continuing to present the 03 October mismatch record as a current
empirical blocker. A new immutable adjudication retains that older fixture
unchanged, records its digest and status, and starts three fresh Python
processes that each rebuild all three selected bindings. All nine trials match
both frozen pre-state witnesses as well as the carrier and injection-map
digests; the artifact captures source/data/import provenance, interpreter
digest, normalized distribution manifest, locale/timezone and the observed
seed policy, but not an independently attested dependency-install/build path.
Accept this only as a narrow correction: it contradicts the old
observation in one captured environment, but does not establish its cause,
historical-environment equivalence, general determinism, benchmark validity,
or any LLM/defense/utility result. The historical execution plan remains
unauthorized because its independent benign arm, executable utility oracle,
manifest-bound driver, reset/trace provenance, fair baselines and other
scientific gates remain open.

**Result-bundle-contract teacher audit — 02 October 2026:** accept the new
validator as a necessary pre-execution claim-control and reproducibility
repair. It makes a future runner preserve the fixed 12-episode denominator;
rejects missing,
duplicate, retry, metadata, registry, carrier, model/request and trace
evidence-consistency failures; recomputes native registry roots and
independently recomputes attack endpoints rather than accepting a runner
score. Reject any claimed benign result: the current
manifest's pre-state hash is bound to injected attack state, while the claimed
no-injection state and utility scorer are not pinned. The validator therefore
returns `benign_initial_state_not_pinned` until a prospective versioned
amendment supplies both. It emits transition counts only; with D0, three
attack pairs and no real execution, it cannot support defense efficacy,
statistics, population inference or Q2 readiness. Its hashes are
self-consistency checks over caller-supplied JSON, not proof of runtime
provenance, InjecAgent materialization or endpoint execution.

**No-InjecAgent default-control teacher audit — 06 October 2026:** accept the
new contract only as a prospective measurement repair. It correctly replaces
the unsound phrase “carrier absent” with a source-pinned default-carrier
control, preserves the historical v1 artifacts, and calls the actual
TaskSuite utility dispatcher instead of trusting a runner Boolean. Its six
source-only controls establish neither benign LLM utility nor defense efficacy:
the password-reset default may itself be untrusted-looking, positive
GroundTruthPipeline traces are not model behavior, post-state variability is
not frozen, and no run/trace/reset provenance exists. Reject model, security,
statistical, ethical-safety, novelty, or Q2-readiness claims until a manifest
v2 driver captures those conditions and a fair executable model matrix is
completed.

**Trace-normalization teacher audit — 06 October 2026:** reject a direct
v1 utility score until a raw renamed trace is canonicalized under the pinned
migration map. The new contract accepts only a reversible name transformation
with unchanged argument digest and retains raw/canonical trace witnesses. Its
source controls rename local ground-truth records; they do not demonstrate a
v1 registry, tool dispatch, model output, utility outcome, or defense result.
The forthcoming v2 manifest and driver must bind this witness before invoking
the default-control scorer.

**Paired-manifest v2 teacher audit — 06 October 2026:** accept the new
preregistration as a necessary design repair because it separates the attack
and default-carrier endpoints, fixes the pre-state/oracle inputs, and rejects
raw v1 control traces without normalization. Reject any inference from the
manifest itself: it has zero observations, no v2 result-bundle validator, no
driver-owned reset/request/response/registry provenance, no fair defense
baseline, and no statistics.

## Short reviewer report

**Verdict:** progress, not Q2-plausible.
**Blocker:** independent end-to-end benchmark and fair statistical comparison
are missing; current live evidence is a seven-case descriptive pilot.
**Evidence:** attestation self-test passes; one pinned AgentDojo integration
smoke has parseable target traces, but it has no target attack effect, no drift,
no tracked runner manifest, and no external benchmark/model matrix.
**Changes:** reconciled the summary with raw target traces, retained the
integration evidence, and rejected it as a security-efficacy result.
**Tests:** manuscript consistency checks and artifact-path checks pass; no new
LLM or billable Runpod job was submitted by this review.
**Next step:** implement a v2 manifest-bound driver consuming the qualified
no-InjecAgent default-carrier control, then bind an independent monotone
post-effect/canary oracle; only then run the paired,
reset-verified model matrix and compute clustered intervals/closest-prior
comparisons.

## Addendum — 7 October 2026

The dated review above predates the current v2 implementation seam. Since that
review:

- `agentdojo_paired_v2_result_bundle.py` now validates the attack oracle,
  default-control utility oracle, raw/canonical trace witness, registry and
  migration evidence under one fixed twelve-row denominator.
- `agentdojo_paired_v2_driver.py` is the canonical scheduler. Its capture mode
  is limited to one pair per arm (four episodes), preserves the other eight
  rows as `pilot_pair_not_selected`, requires explicit billable confirmation,
  and stops provider calls after the first bridge failure.
- `agentdojo_paired_v2_capture_bridge.py` runs each episode in a fresh
  CPython 3.12.13 child process, disables AgentDojo's automatic request retry,
  enforces a preregistered limit of 8 model requests and 16 tool dispatches,
  and captures typed pre/post/reset, carrier/default-control, registry/
  migration, request/response, and raw/canonical trace provenance. The
  validator remains fail-closed for multiple model requests until every request
  is bound, rather than scoring only the first request.
- `paper/statistical_analysis_plan.md` and
  `agentdojo_paired_v2_statistics_adapter.py` now lock the estimand,
  source-cluster rule, McNemar/clustered-bootstrap/Holm procedures,
  missingness bounds, precision/power gates, and fixed-denominator handoff.
- The local fake-provider seam completed both one attack pair and one
  default-control pair; the focused v2 suite passed 31 tests and the full
  experiment suite passed 123 tests with five optional AgentDojo skips.
- Runpod preflight on 7 October 2026 was read-only: endpoint
  `h5ec6v08cb8uc2` had an empty queue and 45 completed/0 failed jobs; its
  active worker was `THROTTLED`; billing for 1–7 October returned `0`.
  No billable job was submitted.

The verdict remains **FAIL for Q2 efficacy claims**. The implementation blocker
has moved from “no capture bridge” to “first provenance-valid remote pilot,
multi-request/per-dispatch provenance completion, fair baselines,
multi-model/held-out evaluation, clustered statistics, and clean-room
reproduction.” The local seam is integration evidence, not an effectiveness
result.

## Continuation correction — 9 October 2026

`PROJECT_STATE.md` supersedes the dated next-step statements above. The current
executable configuration is U/D0 with a name-only migration; a remote run of
that configuration cannot answer the frozen-versus-migrated defense question.
Specify one defense family F/M and an authorization-relevant contract change,
then implement and review the smallest non-billable slice before any explicitly
requested real-LLM pilot. Per-dispatch provenance, fair baselines, model/case
coverage, statistical gates, and independent reproduction remain open.

The P0 source review found a no-retry violation in the capture bridge: replacing
AgentDojo's request helper did not disable the OpenAI SDK's own retry policy. A
loopback HTTP 503 regression check observed three attempts before the fix and
one attempt after setting `max_retries=0`. This validates request-budget
instrumentation only. It adds no defense, model-efficacy, or population evidence.
