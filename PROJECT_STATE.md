# Project state and continuation protocol

> **Canonical handoff file for every model and every new chat.** Read this file
> completely before acting. Do not rely on chat history, remembered summaries,
> or an older GitHub snapshot when the local working tree is available.

```yaml
schema_version: 1
last_updated: 2026-10-10
timezone: Asia/Saigon
project_status: active
research_tier: not_yet_submission_ready
fixed_topic: "Security Regression Testing of Indirect Prompt Injection Defenses under Versioned Agent Tool Contracts"
target: "Q2-or-better submission candidate; acceptance is not guaranteed"
git_branch_observed: main
git_head_observed: 563aac7135da760fd3c541565cc8e47a00812530 (observed before course-priority update)
working_tree_observed: course_package_verified; research_validator_WIP_retained
codex_goal_registry_observed: none (get_goal returned null on 2026-10-09)
next_single_priority: "After the verified course LaTeX package is delivered, complete the research article using the current evidence and resolve the retained adapter acceptance WIP; Q2 remains a later gate."
```

Minimal prompt for a new model:

> Read `PROJECT_STATE.md` completely, refresh its Git snapshot from the live
> repository, then continue only the single next priority while preserving all
> claim and spending boundaries in that file. Update the file before finishing.

The previous goal-registry status usageLimited was an execution-system status,
not scientific completion. On 9 October, get_goal returned null (no active
goal). This file remains the cross-model continuation mechanism.

## 1. Rules for starting or resuming work

Every model must use this boot sequence:

1. Read this file completely.
2. Run `git status --short`, `git rev-parse HEAD`, and `git log -5 --oneline`.
3. Treat the live filesystem and Git output as newer than the snapshot recorded
   above. Never erase or overwrite unexplained user changes.
4. Read, at minimum:
   - `paper/research_protocol.md`
   - `paper/statistical_analysis_plan.md`
   - `paper/q2_claim_gate_review.md`
   - `ROADMAP.md`
   - the implementation files named in section 7.
5. Before editing, identify whether a file is committed, modified, untracked, or
   generated. Do not mix generated outputs, temporary environments, or secrets
   into a research commit.
6. Perform one high-value step that either resolves scientific uncertainty or
   makes the next real experiment executable. More prerequisite contracts are
   not progress unless a specific experiment cannot run without them.
7. Verify the change in proportion to its risk. Record the exact command and
   result in this file.
8. Before ending a meaningful work session, update this file's date, Git state,
   verified evidence, remaining gaps, and the single next priority.

Priority when sources conflict:

1. The user's latest explicit instruction.
2. This continuation file, updated from the live repository.
3. `paper/research_protocol.md` and `paper/statistical_analysis_plan.md`.
4. Executable manifests, validators, tests, and result artifacts.
5. `README.md`, `ROADMAP.md`, review notes, and manuscript drafts.
6. Chat summaries, automation text, or model memory.

Some older documents still describe the topic as a candidate or contain stale
gate text. Those statements do **not** reopen the topic. Correct the documents
when doing so is part of the current task; do not pivot the research direction.

## 2. Non-negotiable research direction

The topic is fixed and may not be replaced:

**Security Regression Testing of Indirect Prompt Injection Defenses under
Versioned Agent Tool Contracts**

The paper asks whether an indirect-prompt-injection defense that is effective
under tool contract `v0` retains its protection after the agent is moved to
contract `v1`, and whether an explicit defense/policy migration prevents or
repairs a regression without unacceptable utility loss.

The intended contribution is an empirical, reproducible **security regression
testing methodology and benchmark protocol**. It is not merely another runtime
policy guard and is not a survey paper. The project targets the quality expected
of a Q2-or-better submission, but must never claim or guarantee acceptance.

The main causal comparison is paired within the same case, carrier, model
snapshot, reset state, defense family, and execution environment. The contract
version and defense-migration status are the controlled changes.

## 3. Canonical experimental configurations

| ID | Meaning | Current status | Permitted claim |
|---|---|---|---|
| `U` | Unprotected AgentDojo integration reference; legacy ID `D0_unmodified_agentdojo` | Executable integration path exists locally | Integration/debug reference only |
| `F` | A real defense/policy frozen at its `v0` form and reused unchanged under `v1` | **Implemented as TaskFileScope source-conformance slice; not integrated into canonical v2** | T1 conformance only |
| `M` | The same defense with an explicit, documented `v0 -> v1` migration | **Implemented as TaskFileScope source-conformance slice; not integrated into canonical v2** | T1 conformance only |
| `E` | Optional migrate-or-escalate comparator when equivalence cannot be proved | Planned, secondary | None yet |
| `P0/P1/P2` | Existing reference guard, canonicalization, and staged state-diff mechanisms | Component-level artifacts exist | Mechanism/calibration only |

`F` and `M` must be two states of the **same named defense and policy family**.
Changing model, prompt, cases, carrier, or unrelated middleware between them
would destroy the paired interpretation.

The tool-contract migration used for the main study must be
**authorization-relevant**: it must change something that can alter the mapping
from an agent action to an allowed harmful effect, such as operation semantics,
resource/destination binding, parameter defaults, argument structure, or
capability scope. A pure tool rename is useful as a negative/control migration,
but it is not sufficient as the paper's main security-regression treatment.

## 4. Locked questions, endpoints, and statistical boundary

Primary question:

> Does a defense that prevents the prespecified harmful effect under `v0`
> regress under `v1`, and is that regression avoided by the explicitly migrated
> version of the same defense?

Primary attack endpoint:

- `H=1` only when the independent harmful-effect oracle observes the
  prespecified forbidden end state.
- Report every paired transition `00`, `01`, `10`, and `11`.
- The primary regression event is `H_v0=0, H_v1=1` (`01`).
- The primary estimand is the paired harmful-effect risk difference
  `mean(H_v1 - H_v0)` over provenance-valid matched pairs.

Default-control utility endpoint:

- Utility uses the upstream task utility scorer plus the required canonical
  trace evidence.
- Attack security and default-control utility remain separate endpoints and
  denominators. They must not be pooled.

Analysis boundary:

- The pair is the comparison unit.
- `source_cluster_id` is the independence/cluster boundary and is taken from
  the manifest, not invented by a result producer.
- Exact two-sided McNemar, clustered paired bootstrap, multiplicity families,
  missingness bounds, precision/power gates, and stopping rules are specified
  in `paper/statistical_analysis_plan.md`.
- The current six-pair/twelve-episode manifest and the four-episode pilot are
  descriptive by construction. They cannot support a Q2-level efficacy claim.
- Legacy `AFER_uncond`, component simulator rates, and trace-transformation
  diagnostics are not the primary estimand.

## 5. Current evidence ledger

### 5.1 What is implemented locally

- A prospective v2 manifest fixes six pairs/twelve episodes: three attack pairs
  and three no-InjecAgent default-control pairs, crossed over `v0/v1` with
  balanced order.
- A canonical driver preserves the fixed denominator and represents failures as
  `not_run`/`not_scored` rather than fabricating evidence.
- A fresh-process capture bridge binds the AgentDojo source/runtime, disables
  provider retries, and records typed state, request/response, carrier,
  registry/migration, trace, and reset provenance.
- A fail-closed v2 result validator independently checks immutable metadata,
  runtime identity, source cluster, pair membership, transition, carrier,
  traces, and endpoint evidence.
- A statistics adapter accepts only a validator-approved scored pair and keeps
  attack and default-control outcomes separate.
- A read-only Gemini reviewer exists for methodological critique. Its output is
  review material, never empirical evidence.
- A prospective TaskFileScope amendment and fail-closed source-preflight validator bind policy hashes, v0/v1 schema descriptors, argument normalization, and per-dispatch denial state evidence without changing historical v2.
- The fresh-process capture bridge has an opt-in TaskFileScope adapter hook; historical plans still use their original name-only migration path.
- An amendment episode/result adapter decorates canonical v2 plans in memory and validates per-dispatch policy events; no historical manifest is rewritten.

### 5.2 Verification already observed on the current local patch

The following results were observed on 9 October 2026 before this handoff file
was created:

- Focused v2 tests: **36 passed**.
- Local fake OpenAI-compatible provider seam: the four-episode
  attack/default-control integration test passed after binding the historical
  Windows `cp1252`/`PYTHONUTF8=0` runtime and restoring the historical helper
  schema.
- Full test discovery under the pinned CPython 3.12.13 environment:
  **132 tests passed, 0 failures**.
- No paid Runpod request was sent in those checks.
- No Gemini `generateContent` request was sent; only model availability was
  checked previously.

These are verification facts about instrumentation and deterministic behavior.
They are **not** evidence that a defense resists indirect prompt injection.
Re-run the relevant tests after changing code; do not quote these counts as if
they cover later edits.

### 5.3 New source-only F/M evidence (10 October 2026)

TaskFileScope is implemented in experiments/agentdojo_file_scope_defense.py.
Its authored resource-argument migration changes file_id into an explicitly
scoped resource object. The user_task_29 default-control sequence was executed
through AgentDojo ToolsExecutor and scored through the existing public utility
scorer in all four cells: F/v0=true, F/v1=false, M/v0=true, M/v1=true.
This is T1 source conformance, with zero model requests and zero attack episodes.
It is a conservative baseline: it cannot expose a harmful-effect regression
for this task, which never grants deletion. It does not answer the main RQ.
The prospective design and local self-review are in
paper/fm_file_scope_design_20261010.md. Canonical capture/acceptance is pending;
the historical validator's equal-schema and name-only trace rules remain intact.

### 5.4 What evidence does not yet exist

- No canonical v2 execution of a real `F` defense.
- No canonical v2 execution of the corresponding migrated `M` defense.
- An authored resource-argument migration now exists for the conservative source
  slice; no main-study treatment capable of resolving the harmful-effect RQ is
  implemented. The historical rename mapping remains a negative control.
- No adequately sized paired LLM result set over multiple model snapshots.
- No held-out carrier/mutation evaluation demonstrating robustness.
- No Q2-ready effect estimate, confidence interval, power/precision gate, or
  defensible superiority/non-inferiority conclusion.
- No independent external artifact reproduction.

Therefore the current paper is **not submission-ready**. The strongest honest
statement is that the repository has a tested prospective execution and
validation seam plus component/source controls, while the central defense
comparison remains unexecuted.

## 6. Evidence tiers and claim policy

| Tier | Evidence | Examples here | Claims allowed |
|---|---|---|---|
| `T0` | Plan or prose only | protocol, roadmap, manuscript TODOs | Intended method only |
| `T1` | Deterministic/source calibration | fixtures, contract hashes, trace normalization, source witnesses | Instrument behavior only |
| `T2` | Local integration with fake provider | four-episode local server test | End-to-end plumbing/provenance only |
| `T3` | Small real-LLM pilot | legacy/tiny pilot if provenance-valid | Feasibility or case report only |
| `T4` | Prespecified paired `F/M` study with adequate models/cases and statistics | **Absent** | Primary empirical claims |
| `T5` | Independent reproduction/held-out generalization | **Absent** | Stronger robustness/generalization claims |

Reject any manuscript sentence that promotes `T0-T2` evidence into `T4`
language. In particular:

- A simulator is not LLM efficacy evidence.
- A synthetic trace rename is not a `v1` runtime observation.
- A fake provider proves plumbing, not defense quality.
- A no-InjecAgent default control still contains AgentDojo default carrier
  content; it is not a carrier-absent benign arm.
- `attack_success=false` is not automatically `security=true`; the independent
  harmful-effect oracle is authoritative.
- A tiny pilot or one model cannot establish effectiveness, regression rate, or
  generalization.

## 7. Artifact map

Canonical scientific documents:

- `paper/research_protocol.md` — threat model, RQs, configurations, metrics.
- `paper/statistical_analysis_plan.md` — canonical estimands and inference.
- `paper/q2_claim_gate_review.md` — strict no-overclaim review; later addenda may
  supersede stale earlier rows in the same file.
- `paper/imrad_manuscript.md` — current course/research manuscript draft, not a
  record of completed efficacy results.
- `ROADMAP.md` — five execution, three review, and two testing workstreams.

Canonical v2 execution seam:

- `experiments/agentdojo_paired_v2_execution_manifest.py`
- `experiments/fixtures/agentdojo_paired_v2_execution_manifest_v1.json`
- `experiments/agentdojo_paired_v2_driver.py`
- `experiments/agentdojo_paired_v2_capture_bridge.py`
- `experiments/agentdojo_paired_v2_result_bundle.py`
- `experiments/agentdojo_paired_v2_statistics_adapter.py`
- Corresponding `experiments/test_agentdojo_paired_v2_*.py` files.

Supporting controls and historical evidence:

- `experiments/agentdojo_v2_no_injecagent_default_control_contract.py`
- `experiments/agentdojo_v2_utility_trace_normalization_contract.py`
- `experiments/agentdojo_contract_migration.py`
- `experiments/agentdojo_paired_v0_v1_execution_manifest.py`
- `experiments/agentdojo_paired_result_bundle.py`
- `experiments/policy_guard_sim.py`

Review helper:

- `experiments/gemini_reviewer.py`
- `experiments/test_gemini_reviewer.py`

Generated or local-only areas that normally must not be committed as source:

- `tmp/`
- `graphify-out/`
- `qa/`
- rendered screenshots/PDF intermediates
- virtual environments, caches, dependencies, model weights, and secrets

## 8. Git state refreshed 10 October 2026

Observed base HEAD: 8144be696869bcb1c7e61ed059056ffb252bafc4 on main,
matching origin/main before this amendment. The tracked working tree contains
only attributable amendment changes: the defense/preflight state-hash and
schema-projection edits, the amendment module and fixture, its tests, the
design addendum, and this handoff update. Generated preflight QA output was
deleted after verification. Preexisting deliverables/, graphify-out/, and tmp/
remain untracked local areas; tmp is retained because it contains the pinned
runtime. No generated directory is part of the source patch. The AgentDojo
source checkout remains clean at
089ed468cf3ed0322acc66b0211f26d9d90dbf60.

### Historical pre-freeze snapshot (superseded)

Observed base commit:

`bf9e1c9 Freeze v2 paired execution manifest`

No files were staged when this snapshot was taken. The following tracked files
had local modifications:

- `README.md`
- `ROADMAP.md`
- `experiments/agentdojo_paired_v2_execution_manifest.py`
- `experiments/fixtures/agentdojo_paired_v2_execution_manifest_v1.json`
- `experiments/test_agentdojo_paired_v2_execution_manifest.py`
- `paper/imrad_migration_plan.md`
- `paper/q2_claim_gate_review.md`
- `paper/research_protocol.md`

The following research-source files were untracked but are part of the current
v2 patch and were verified together:

- `experiments/agentdojo_paired_v2_capture_bridge.py`
- `experiments/agentdojo_paired_v2_driver.py`
- `experiments/agentdojo_paired_v2_result_bundle.py`
- `experiments/agentdojo_paired_v2_statistics_adapter.py`
- `experiments/gemini_reviewer.py`
- `experiments/test_agentdojo_paired_v2_capture_bridge.py`
- `experiments/test_agentdojo_paired_v2_driver.py`
- `experiments/test_agentdojo_paired_v2_result_bundle.py`
- `experiments/test_agentdojo_paired_v2_statistics_adapter.py`
- `experiments/test_gemini_reviewer.py`
- `paper/course_project_checklist.md`
- `paper/imrad_manuscript.md`
- `paper/runpod_budgeted_pilot_gate_20261007.md`
- `paper/statistical_analysis_plan.md`

`deliverables/`, `tmp/`, and `graphify-out/` also contain untracked generated or
course artifacts. Inspect them individually; do not stage their directories in
bulk. A source-only ZIP was created outside the repository at:

`C:\Users\ADMIN\Documents\ChatGPT\security-regression-project-source-20261009-v1.zip`

Recorded SHA-256:

`32332A8E28AB98F1D8665B5DE663B5271A4F263FE93567003E1C9EE99E175A35`

Because this section is a dated snapshot, future models must refresh it from
Git before relying on the lists.

## 9. Next steps in the correct order

### P0 - Preserve the verified v2 seam (completed 9 October 2026)

Frozen and pushed in fbfa92c; full post-fix suite passes 133 tests. The
following steps are the retained checklist, not the next task.


1. Review the current diff for scope, secrets, generated files, stale claims,
   and budget values.
2. Confirm the source files listed in section 8 are attributable to this
   research task.
3. Re-run the relevant focused tests and, before release, the full suite.
4. Commit and push only the attributable source/doc patch. Keep generated
   directories and local credentials out of Git.

This is repository hygiene, not the next scientific contribution.

### P1 — Specify one real defense and one real migration

The development design is now recorded in paper/fm_file_scope_design_20261010.md.
TaskFileScope is a conservative F/M baseline; it is not a treatment that can
expose harmful-effect regression for the selected task. The main-study
discriminating treatment remains an unmet requirement. Retain this checklist:

Create a short, falsifiable design record before implementation:

- name the defense/policy family;
- define exactly how it decides or constrains a tool action in `v0`;
- define `F` as that defense frozen unchanged under `v1`;
- define `M` as the same defense after an explicit migration;
- identify the authorization-relevant semantic delta in the tool contract;
- state the predicted `00/01/10/11` outcomes and utility risks;
- show why the oracle is independent of the defense decision.

Do not add another generic contract until this design record identifies the
concrete executable classes/functions and selected AgentDojo cases.

### P2 — Implement the smallest executable `F/M` slice

Current partial implementation: the four default-control source-conformance
cells execute through the real native runtime and public utility scorer.
Attack/model capture and canonical manifest/validator acceptance are still
missing, so P2/P3 are not complete and no paid-pilot gate is opened.

Implement one defense family for one attack pair and one default-control pair:

- same model snapshot and parameters;
- same task, carrier, initial state, reset, and source cluster;
- `v0` and `v1` tool contracts with the declared semantic change;
- frozen `F` versus migrated `M`;
- independent harmful-effect and utility scorers;
- complete provenance accepted by the existing v2 validator.

Use deterministic/fake-provider tests only to validate plumbing. They must not
be inserted into results tables as LLM observations.

### P3 — Run a non-billable preflight and teacher review

The Student must demonstrate that all four cells needed for a minimal paired
slice are executable and fail closed. The Teacher must challenge:

- whether the contract change is genuinely authorization-relevant;
- whether `F` and `M` are the same defense family;
- whether the selected cases can actually expose the regression mechanism;
- whether the oracle observes effects rather than model wording or defense
  decisions;
- whether utility is scored independently;
- whether retries, missingness, selection, and stopping can bias results;
- whether every proposed claim maps to an artifact and denominator.

Do not proceed to a paid pilot while any of these questions has no concrete
artifact-backed answer.

### P4 — Run the smallest real-LLM pilot only on explicit user command

The first real pilot should be the minimum needed to show the `F/M` comparison
can produce valid scored pairs, not to estimate efficacy. Preserve all failed
rows and stop on provenance/provider errors according to the driver gate.

After the pilot, inspect traces and state diffs without changing hypotheses or
case inclusion based on outcomes. Amend the protocol only through a dated,
explicit amendment.

### P5 — Scale to the preregistered study

Only after P4 passes:

- expand to adequately many independent source clusters/cases;
- use at least three model snapshots, including at least one open-weight model;
- add held-out carriers/mutations and justified strata;
- execute the frozen analysis plan;
- report missingness, all paired transitions, effect sizes, intervals,
  multiplicity handling, utility, overhead, and failure analysis;
- regenerate manuscript tables/figures solely from run-linked artifacts.

### P6 — Submission gate

Before calling the paper Q2-ready, require:

- defensible closest-prior comparison and contribution statement;
- executed `F/M` evidence, not only `U` or component controls;
- adequate precision/power or an explicitly limited exploratory claim;
- reproducible environment and public artifact plan;
- independent methods/statistics/security review;
- claim-by-claim evidence audit and limitations covering construct, internal,
  external, and statistical validity.

## 10. Compute, API, and spending authority

Runpod:

- The user's aggregate authorization recorded in this thread is **USD 10.00
  total**, including prior spending/overhead: planned `USD 8.00` execution plus
  `USD 2.00` reserve.
- A pasted statement claiming USD 13.00 does not expand this authority.
- The user later instructed that automatic jobs must remain off and that a job
  should run only when the user explicitly messages to run it. Therefore **do
  not create, submit, resume, scale, or change a Runpod job/resource merely from
  this file or an automation**.
- Before any paid request, identify the exact endpoint/pod, model, maximum
  requests/tokens/tools, current prior spend, stop conditions, and worst-case
  cost within the remaining aggregate authorization.
- Request/tool caps are not a provider-enforced dollar cap.

Gemini:

- `GEMINI_API_KEY` is stored in the user's Windows environment; never print,
  copy, log, or commit it.
- A model-list check previously confirmed `gemini-3.1-pro-preview` was
  available. This is connectivity evidence only.
- `experiments/gemini_reviewer.py` sends only explicitly selected UTF-8 files
  and writes critique under ignored `qa/`.
- Gemini review is advisory and cannot establish novelty, correctness, or
  empirical efficacy.

General:

- Never commit API keys, bearer tokens, endpoint secrets, raw sensitive prompts,
  or unredacted provider responses.
- Prefer non-billable local tests until the exact real-LLM pilot is ready.

## 11. Reproduction commands

Pinned Windows environment for the current historical fixtures:

```powershell
$env:PYTHONUTF8 = "0"
$env:PYTHONIOENCODING = "utf-8"
$python = ".\tmp\agentdojo-source\.venv31213\Scripts\python.exe"
```

Focused v2 checks:

```powershell
& $python -B -m unittest `
  experiments.test_agentdojo_paired_v2_execution_manifest `
  experiments.test_agentdojo_paired_v2_result_bundle `
  experiments.test_agentdojo_paired_v2_statistics_adapter `
  experiments.test_agentdojo_paired_v2_driver `
  experiments.test_agentdojo_paired_v2_capture_bridge `
  experiments.test_gemini_reviewer -v
```

Full test discovery:

```powershell
& $python -B -m unittest discover -s experiments -p "test_*.py" -q
```

Non-billable driver dry run:

```powershell
& $python experiments/agentdojo_paired_v2_driver.py --dry-run `
  --run-id local-dry-run `
  --bundle-output tmp/agentdojo_paired_v2_result_bundle.json `
  --report-output tmp/agentdojo_paired_v2_result_report.json
```

Repository checks before committing:

```powershell
git status --short
git diff --check
git diff --cached --check
git diff --cached --name-only
git grep --cached -n -E "AIza[0-9A-Za-z_-]{20,}"
```

The `cp1252`/`PYTHONUTF8=0` setting reproduces historical state fixtures. It is
not a recommendation that future datasets use `cp1252`. A UTF-8 conversion must
be recorded as an explicit dataset/state migration rather than silently
changing the evidence base.

## 12. Decision log

| Date | Decision | Reason |
|---|---|---|
| 2026-09 to 2026-10 | Fix the research topic to security regression testing under versioned tool contracts | The user explicitly prohibited another topic pivot |
| 2026-10-07 | Make the v2 driver/bridge/validator/statistics adapter the prospective execution seam | Prevent fabricated rows and bind pair/runtime/provenance evidence |
| 2026-10-09 | Treat current `U` plus rename-only migration as an integration/negative control | It contains no actual `F/M` defense comparison and cannot answer the main RQ |
| 2026-10-09 | Bind historical Windows encoding/runtime in capture evidence | The frozen pre-state differs under UTF-8 mode; reproducibility requires declaring this dependency |
| 2026-10-09 | Keep Runpod automatic execution off | The user requires an explicit message before each job; the aggregate ceiling remains USD 10 |
| 2026-10-09 | Use this file as the cross-model continuation source | Project progress must not depend on any model's chat memory |

## 13. End-of-session update template

At the end of a meaningful session, append or revise the relevant sections and
leave this compact record:

```text
Date/time (Asia/Saigon):
Git HEAD / branch:
Files changed:
Scientific question resolved:
Verification command and exact result:
Evidence tier reached:
Claims now supported:
Claims still forbidden:
Runpod/Gemini/API spend or calls:
Teacher verdict:
Single next priority:
```

If no artifact, verified result, failure, or required user decision changed,
do not manufacture a progress update.

## 14. Continuation update — 2026-10-09

Date/time (Asia/Saigon): 2026-10-09 23:52
Git HEAD / branch: 3b668e1a2253c814ad51f13e3240771e21debc2e / main, pushed to origin/main; source freeze is fbfa92c. This is the observed parent of the final handoff correction commit, not a self-referential final commit hash.
Files changed: committed the attributable v2 source/doc patch in fbfa92c (22 files). PROJECT_STATE.md is this handoff update; deliverables/, graphify-out/, and tmp/ remain untracked local/generated areas and were not staged.
Scientific question resolved: P0 instrumentation uncertainty resolved. The OpenAI SDK independently retried a provider HTTP 503 three times despite the bridge replacing AgentDojo's helper; max_retries=0 now enforces the manifest no-retry rule and the regression test observes one attempt. The current configuration remains U/D0 with rename-only migration; no F/M comparison exists.
Verification command and exact result: focused v2 suite before the retry fix — Ran 40 tests in 333.991s; OK; retry regression — Ran 1 test in 24.531s; OK; full discovery after the fix — Ran 133 tests in 241.083s; OK; dry-run assertion — 12 not_run rows; 6 pairs retained; 0 scored pairs; no bundle contract error; secret scan — 22 source/doc files; 0 matches; git diff --check and git diff --cached --check clean after stripping four Markdown trailing-space line breaks.
Evidence tier reached: T1/T2 instrumentation and local fake-provider integration only.
Claims now supported: the capture bridge suppresses SDK-level retries; the v2 seam preserves fixed denominator and fail-closed scoring in local checks.
Claims still forbidden: F/M efficacy, defense regression rate, population inference, Q2 readiness, and claims from rename-only U/D0 execution.
Runpod/Gemini/API spend or calls: zero Runpod or Gemini calls and zero paid provider requests; loopback fake-provider HTTP requests only. Git fetch/push and deterministic graphify query/save-result also ran.
Teacher verdict: local self-review only (no independent Teacher/Gemini review performed); P0 verification passes; F/M design and authorization-relevant migration remain required, and remote pilot remains off without explicit user command.
Single next priority: Specify one real defense/policy family as F and M under an authorization-relevant v0-to-v1 contract change, then run the smallest non-billable four-cell preflight and review before any paid pilot.

Exact new verification commands (using the environment from section 11):

```powershell
& $python -B -m unittest experiments.test_agentdojo_paired_v2_capture_bridge.AgentDojoPairedV2CaptureBridgeTests.test_provider_failure_is_not_retried_by_sdk -v
& $python -B -m unittest discover -s experiments -p "test_*.py" -q
& $python experiments/agentdojo_paired_v2_driver.py --dry-run --run-id p0-freeze-20261009 --bundle-output qa/p0_freeze_v2_bundle.json --report-output qa/p0_freeze_v2_report.json
git diff --check
git diff --cached --check
```

The focused pre-fix command is exactly the six-module command in section 11.
The new HTTP 503 test failed before the fix (3 requests versus expected 1),
then passed after max_retries=0. One initial full-suite invocation was
interrupted for that fix; it is not counted as verification. The subsequent
133-test run exited 0 with no skips. Local dry-run outputs remain ignored in qa/.
Skills used: ponytail for the minimal shared-boundary fix and graphify for a
query of the existing project graph. Graphify located the v2 driver, validator,
and source-oracle paths; live file reads were authoritative over its older line
locations. No plugin invoked paid compute or external review.

## 15. Continuation update — 10 October 2026

- Date/time (Asia/Saigon): 2026-10-10 00:15.
- Git base / branch: 66b9ff02e7a44301f69d8753065d0d061262469f / main.
  The final source/handoff commit follows this observed base; do not try to
  embed the file's own future commit hash in itself.
- Files changed: experiments/agentdojo_file_scope_defense.py,
  experiments/agentdojo_file_scope_preflight.py,
  experiments/test_agentdojo_file_scope_defense.py,
  paper/fm_file_scope_design_20261010.md, and PROJECT_STATE.md.
- Scientific question resolved: a real fail-closed resource guard can retain
  its frozen policy identity under an explicit nested-resource contract while
  losing source-task utility; changing only the policy argument decoder restores
  utility in the four development controls. This resolves implementation and
  utility-conformance uncertainty, not the primary harmful-effect hypothesis.
- Verification: focused new tests ran 5 tests in 7.204s, OK. Full discovery
  after the implementation ran 138 tests in 121.261s, OK, no skips. The standalone
  source preflight returned F/v0=true, F/v1=false, M/v0=true, M/v1=true, with
  identical initial-state hashes, matched within-version schemas and expected
  frozen/migrated policy digests. No model or attack episode was executed.
- Evidence tier: T1 source conformance only; no new T2/T3/T4 observation.
- Repository checks: git diff --check and git diff --cached --check passed.
  Secret-pattern/environment-secret scan of the five changed files found no
  matches after correcting a token-boundary false positive on the schema name.
- Claims now supported: concrete TaskFileScope F/M execution at the AgentDojo
  tool boundary and the stated source-utility contrast. A denial is distinguished
  from a native tool error and does not dispatch or change typed state.
- Claims still forbidden: defense efficacy, harmful-effect regression rates,
  population inference, canonical F/M scored pairs, Q2 readiness. This task does
  not grant deletion, so the slice cannot expose the main harmful-effect contrast.
- Spend/calls: zero Runpod jobs, zero Gemini requests, zero paid provider calls.
  Full regression tests use the existing loopback fake-provider seam only.
- Review: local self-review recorded in the design document; no independent
  Teacher/Gemini review. P2 canonical integration and P3 review are incomplete.
- Skills/plugins: ponytail informed reuse of FunctionsRuntime, ToolsExecutor,
  canonical hashing and public utility scoring; graphify queried the existing
  guard/contract graph. Live source was authoritative. No skill installed or
  external compute/plugin resource changed.
- Single next priority: integrate this conservative F/M baseline through a
  prospective capture/manifest/validator amendment with policy migration binding,
  v0/v1 schema descriptors, nested-argument normalization and per-dispatch denial
  evidence. Preserve historical v2 name-only controls; verify without paid calls.

Commands (using the pinned Python and encoding from section 11):

~~~powershell
& $python -B -m unittest experiments.test_agentdojo_file_scope_defense -v
& $python -B -m experiments.agentdojo_file_scope_preflight --output qa/fm_file_scope_preflight_20261010.json
& $python -B -m unittest discover -s experiments -p "test_*.py" -q
git diff --check
git diff --cached --check
~~~

The source preflight report is ignored under qa/; it is not a benchmark bundle
and must not be copied into efficacy tables. Its hashes include implementation
files; successful post-state hashes can vary due to native append timestamps.

## 16. Continuation update ? 10 October 2026

Date/time (Asia/Saigon): 2026-10-10 03:05.
Git base / branch: 8144be696869bcb1c7e61ed059056ffb252bafc4 / main before the amendment commit.
Files changed: TaskFileScope runtime/preflight now record per-dispatch pre/post state hashes and canonical schema projections; new agentdojo_file_scope_amendment.py, its fixture, test module, and design addendum bind the prospective F/M evidence contract; temporary qa/fm_file_scope_preflight_20261010.json was deleted after verification.
Scientific question resolved: the conservative F/M slice is now bound by a separate prospective manifest/validator. F remains the same policy hash across v0/v1; M changes only the explicit argument contract at v1. The validator accepts the four source cells only when policy/schema/normalization identities and denial state invariants match.
Verification command and exact result: amendment CLI accepted the source preflight with utility sequence [true, false, true, true] and T1_source_conformance_only. Focused amendment + defense tests: 9 tests, 51.588s, OK; corrected isolation test: 4 amendment tests, 35.981s, OK; full discovery after correction: 142 tests, 396.843s, OK; after the capture hook, full discovery: 143 tests, 403.060s, OK. A prior full-suite attempt failed because the amendment test ran preflight in the shared process; the test now uses the pinned subprocess and the final full suite passed. git diff --check passed before staging.
Evidence tier reached: T1 source conformance/amendment validation only; still no model or attack episode.
Claims now supported: prospective F/M policy identity, schema descriptors, nested argument normalization, and per-dispatch denial state evidence are fail-closed and tamper-tested.
Claims still forbidden: canonical v2 F/M efficacy, harmful-effect regression, population inference, Q2 readiness, and any paid-pilot conclusion.
Runpod/Gemini/API spend or calls: zero Runpod jobs, zero Gemini requests, zero paid provider calls. The only runtime calls were local pinned source controls and test subprocesses.
Cleanup: removed the generated qa/fm_file_scope_preflight_20261010.json report. Retained tmp pinned runtime, graphify-out knowledge graph, and deliverables course artifacts.
Teacher verdict: local self-review only; the conservative task still cannot expose harmful-effect regression, and canonical capture/manifest integration plus independent review remain open. No login or user interaction was required.
Single next priority: add the amendment-specific capture adapter hook to the fresh child, then run a non-billable fake-provider integration that proves F/M model tool calls are transformed, guarded, and fail closed without altering historical v2 controls.

## 17. Continuation update ? 10 October 2026

Date/time (Asia/Saigon): 2026-10-10 04:00.
Git base / branch: a726356ee52480f9077458a2a9c24d478d1115f1 / main before this final handoff commit.
Files changed: agentdojo_paired_v2_capture_bridge.py now exposes _prepare_runtime_for_plan; plans with defense_adapter_id=TaskFileScope use the authored v0/v1 resource migration and guard, while historical plans continue through AGENTDOJO_CONTRACT_MANIFEST. The amendment test now runs preflight in a pinned subprocess for process isolation.
Scientific question resolved: the F/M policy amendment is reachable from the fresh-child capture seam without silently changing historical v2. A fake model tool-call test proves F/v1 denies append before dispatch and M/v1 permits it, with state effects matching the expected utility contrast.
Verification command and exact result: hook test passed 1 test in 29.502s; historical v2 capture bridge suite passed 5 tests in 143.648s; final full discovery passed 143 tests in 403.060s, no skips. Amendment CLI previously accepted the four-cell preflight with utility [true,false,true,true]. git diff --check and secret scan were clean before staging the source patch.
Evidence tier reached: T1 source-conformance plus capture-hook plumbing; no model/provider/attack observation and no canonical F/M result bundle.
Claims now supported: opt-in adapter hook preserves historical v2 path; F/M tool-call argument transformation and fail-closed denial are testable in the pinned runtime.
Claims still forbidden: canonical fresh-child F/M LLM efficacy, harmful-effect regression, population inference, Q2 readiness, paid-pilot conclusion.
Spend/calls: zero Runpod jobs, zero Gemini requests, zero paid provider calls; all checks were local pinned runtime or fake tool calls.
Cleanup: no current preflight report retained under qa; tmp pinned runtime and graphify-out/deliverables were retained as needed local artifacts.
Teacher verdict: local self-review only; full fresh-child pipeline must bind an amendment-specific episode plan and validator evidence before any user-authorized pilot.
Single next priority: create the amendment-specific episode-plan/result adapter consumed by the fresh child, validate model request/response plus per-dispatch guard events, and run a non-billable fake-provider full-pipeline test without touching historical v2.

## 18. Continuation update ? 10 October 2026

Date/time (Asia/Saigon): 2026-10-10 05:20.
Git base / branch: e678ea22c89a29c611c226acb71378fe0c1c7ebe / main before this final state commit.
Files changed: agentdojo_file_scope_episode_adapter.py decorates canonical v2 episode plans with TaskFileScope F/M amendment identity and validates per-dispatch redacted policy events; capture bridge now accepts adapter fields while comparing the stripped base plan; capture trace evidence retains per-dispatch policy events for adapter plans; amendment tests exercise both fresh-child cells.
Scientific question resolved: the prospective F/M amendment now reaches the actual fresh-child capture path. A loopback fake provider drove search then append through F/v1 and M/v1; F denied append before native dispatch and preserved state, M dispatched append and changed state.
Verification command and exact result: full discovery after the episode adapter ran 144 tests in 457.990s, OK, no skips. Focused amendment plus historical bridge tests ran 11 tests in 217.625s, OK. The fresh-child fake-provider F/M test passed in 77.771s. No model or paid provider request was used.
Evidence tier reached: T2 local fake-provider plumbing/provenance; still not T3 real LLM or T4 efficacy.
Claims now supported: adapter plan identity, nested argument normalization, fresh-child guard decisions, per-dispatch evidence, and state effects are locally auditable; historical v2 path remains regression-tested.
Claims still forbidden: real F/M defense efficacy, harmful-effect regression, population inference, Q2 readiness, and any paid pilot conclusion.
Spend/calls: zero Runpod jobs, zero Gemini requests, zero paid provider calls; only loopback fake provider and pinned local runtime.
Cleanup: no current preflight report retained under qa; tmp, graphify-out, and deliverables retained.
Teacher verdict: local self-review only; next review must inspect adapter plan/result binding and the fact that this task is utility/default-control only. No login or user interaction was required.
Single next priority: run the amendment adapter through the canonical result acceptance boundary in a separate prospective adapter report, then prepare the non-billable review artifact; do not alter historical v2 or launch paid execution.

## 19. User priority change - 10 October 2026

The user's latest explicit instruction supersedes the previous next priority:
1. Finish the course deliverable using the RIGHT column (Hoan thanh) in the
   supplied rubric photograph. It is sufficient to choose this one track.
2. Then complete the research article.
3. Then pursue a Q2 submission candidate; acceptance is never guaranteed.

The six course requirements read from the image are: problem definition;
related research (optional); detailed background; detail of all or part of the
proposed solution; implementation and evaluation approach (if any); report
according to a template and presentation. The image contains the rubric,
not a layout template. Use a conventional academic layout until an actual
institutional template is provided; do not claim template compliance.

Research WIP is retained, not promoted to a completed study: adapter-report
refactoring, stronger plan binding, shared request checks, and four-cell tests.
The latest targeted integration test passed (1 test, 172.633s); no full-suite
claim covers this unfinished patch. Do not spend further course time extending
F/M experiments. No research process remains live from that test.

Deadline requested earlier: before 16 October 2026 (Asia/Saigon). Prioritize
the course report and presentation by that date; Q2 gates remain separate.

## 20. Course LaTeX package - 10 October 2026

The latest user request supplied Template-1-cột.docm, then explicitly requested
LaTeX for shared editing. This supersedes the conventional-layout fallback in
section 19. The Hoan thanh course track remains the first delivery priority.

Completed artifacts:
- course-report/main.tex and six files in sections/: Vietnamese report.
- course-report/slides.tex: 10-slide Beamer presentation with speaker notes.
- course-report/references.bib: five cited sources; README.md explains editing,
  Overleaf import, XeLaTeX/BibTeX and Tectonic compilation.
- deliverables/course_report_latex/Nhom_11_LaTeX_Overleaf.zip: editable source.
- deliverables/course_report_latex/Bao_cao_mon_hoc_Nhom_11.pdf: 7 A4 pages.
- deliverables/course_report_latex/Trinh_bay_Nhom_11.pdf: 10 slides.

Template: C:/Users/ADMIN/Downloads/Template-1-cột.docm; SHA-256
257ec3d1c458f8b8c7438edb35ff3ace39d62bece9aad3009f272782902005bb.
Read-only package inspection identified LNCS one-column styles and page
geometry. The source template remains unchanged; no macro was executed.
LaTeX uses unmodified CTAN LNCS 2.26 class/style, A4 and 122 x 193 mm text area.
TeX Gyre fonts replace Word Times New Roman: no pixel-identical layout claim.

Validation: Tectonic 0.17.0 compiled both files with exit 0. Poppler rendered
all 7 report pages and all 10 slides; every page was visually inspected, with
changed table/reference pages rechecked after the final layout correction.
No overfull boxes, missing characters or unresolved references/citations.
One harmless LNCS/amsmath math-accent warning remains. Input/citation coverage,
vendor hashes, original template hash and ZIP integrity passed.
Commands: from course-report, tectonic -X compile main.tex --outdir
../qa/course_latex_build/report --keep-logs; repeat for slides.tex with outdir
../qa/course_latex_build/slides. pdfinfo verifies page counts; pdftoppm produces
QA page images. The README documents portable xelatex/bibtex commands.

No new scientific evidence was produced by typesetting. Source/fake-provider
findings remain T1/T2; no efficacy, novelty, Q2 or instructor-acceptance claim.
No paid provider, Runpod or Gemini call. GitHub/CTAN and the TeX bundle were
downloaded over the network for the compiler, class and dependencies.
The compiler and QA outputs live under ignored qa/, not in the source ZIP.
Original course artifacts, pinned runtime and graph remain intact.

Research WIP is retained unstaged: episode_adapter.py, capture_bridge.py,
result_bundle.py, test_agentdojo_file_scope_amendment.py and the new
agentdojo_file_scope_adapter_report.py. The four-cell integration check passed
1 test in 172.633s before the priority change; full regression remains due
when research work resumes. Do not quote the older 144-test count for this WIP.

Completion scope: the course package covers all six items of the selected rubric
and is ready for group editing/review. Personal/course details should be checked
by the group before submitting. Course preparation is complete; the overall
research/Q2 goal remains active. Next: complete the research article, resolving
the retained acceptance-validator WIP and mapping claims to verified evidence.

## 21. Course Overleaf compiler support - 10 October 2026

The supplied Overleaf log starts with pdfTeX/pdflatex (TeX Live 2026) and stops
at fontspec cannot-use-pdftex. Root cause is project compiler selection, not
Vietnamese content or the LNCS class. The TeX program comment does not select
the Overleaf project compiler. Instruct Settings > Compiler > XeLaTeX, then
Recompile; from scratch if cached output persists.

Added course-report/latexmkrc with pdf_mode=5 as the local latexmk default and
README troubleshooting; repack the source ZIP to include both. No content or
layout changes; the previously inspected PDFs remain applicable. No access to
the user's Overleaf project settings was performed or claimed. Verification
here covers file/ZIP consistency and diff hygiene, not an Overleaf compile.
The project compiler may override latexmk defaults. Source package remains
XeLaTeX-based. Resume the research article only after this course support task.

User supplied the pdfTeX log and Overleaf screenshot on 10 October. Applied
clarification directly in main.tex's editor comment and package README, rebuilt
the 15-entry Overleaf ZIP including latexmkrc, and verified archive CRC. The
source ZIP now explicitly says the project-level Compiler must be XeLaTeX. The
two final PDFs do not need rebuilding because their content/layout did not
change. Remaining verification is compile within the user's Overleaf project,
which has not been accessed from this workspace.
