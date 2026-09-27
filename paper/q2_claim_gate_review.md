# Q2 claim-gate review — 26 September 2026

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
| Novelty boundary | `paper/claim_strategy_review.md`, `paper/related_work_matrix.md`; generic runtime enforcement is explicitly not claimed as new | **Partial** | Freeze a closest-prior table and show a measurable difference or a clearly labelled replication/negative result |
| Independent benchmark | Protocol names AgentDojo/InjecAgent, but repository has no pinned external run manifest or benchmark outputs | **Fail** | Pinned commit/snapshot, adapter, scorer, split, budget and redacted traces |
| End-to-end LLM efficacy | One descriptive Qwen3-8B run over 7 fixed fixtures; no drift mutation, held-out templates or independent model | **Fail** | ≥3 model snapshots (≥1 open-weight), realistic carrier, same cases across B0–B6/P0–P2, and drift-aware test results |
| Adapter/state attestation | `experiments/adapter_attestation.py`; `qa/adapter_attestation_selftest.json` reports `all_pass=true`; fixture smoke aborts mismatches before live commit | **Partial** | Execute the attestation in the end-to-end benchmark and demonstrate that the adapter cannot emit an irreversible side effect before verification; otherwise claim only staged-transaction conformance |
| Fair baselines | Synthetic rows B0/B1/B2/B4 are trace transformations; B3/B5/B6 and external systems are not executed | **Fail** | Implement and freeze executable closest-prior baseline(s) with identical model, prompt, tools, budget and reset protocol |
| Statistics | Synthetic case-level bootstrap is explicitly descriptive; no paired test, cluster bootstrap or mixed-effects analysis for an independent episode population | **Fail** | Pre-register unit of analysis, source-template clustering, paired CI/test, model/task random effects, multiplicity correction and missing-run handling |
| Reproducibility | Hashes, self-tests and split manifest exist; model digest, lockfile/container, full-run command and raw redacted traces are incomplete | **Partial** | One clean-room command reproducing main tables from a pinned environment and archived trace manifest |
| IMRaD/results integration | `paper/q2_ready_report.md` separates protocol from pilot, but E5 still contains planned tables and synthetic “baseline” rows that can be misread as LLM results | **Partial** | Keep protocol/pilot labels in title, abstract, tables and conclusion; replace pending cells only from run-linked results |

## Corrections applied to the manuscript

1. The live pilot should cite `experiments/live_trace_runpod_gbo4nj1k5ublmt_realistic7.json`
   and `qa/realistic7_scored_all_final.json`, not the earlier labelled
   `runsync` trace. The latest descriptive figures are: 7/7 parse/schema-valid,
   4/7 exact-call match, 1/4 forbidden proposals, and C2 post-guard
   forbidden effects 0/4 with CTS 3/3 and FBR 0/3.
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

## Short reviewer report

**Verdict:** progress, not Q2-plausible.
**Blocker:** independent end-to-end benchmark and fair statistical comparison
are missing; current live evidence is a seven-case descriptive pilot.
**Evidence:** attestation self-test passes and latest realistic Runpod trace is
schema-valid, but no pinned external benchmark/model matrix exists.
**Changes:** corrected stale live-trace references, downgraded synthetic rows to
trace-emulator status, tightened probability/rollback language, and recorded
the gate audit above.
**Tests:** manuscript consistency checks and artifact-path checks pass; no new
LLM or billable Runpod job was submitted by this review.
**Next step:** run the independent benchmark through the same attested
dispatcher, then compute paired/clustered intervals and closest-prior
comparisons before drafting a final manuscript.
