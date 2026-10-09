# Project state and continuation protocol

> **Canonical handoff file for every model and every new chat.** Read this file
> completely before acting. Do not rely on chat history, remembered summaries,
> or an older GitHub snapshot when the local working tree is available.

```yaml
schema_version: 1
last_updated: 2026-10-09
timezone: Asia/Saigon
project_status: active
research_tier: not_yet_submission_ready
fixed_topic: "Security Regression Testing of Indirect Prompt Injection Defenses under Versioned Agent Tool Contracts"
target: "Q2-or-better submission candidate; acceptance is not guaranteed"
git_branch_observed: main
git_head_observed: bf9e1c9f28a74b093b819dd9072e0d317f3607d2
working_tree_observed: dirty
codex_goal_registry_observed: usageLimited
next_single_priority: "Freeze the current v2 pipeline patch, then implement one real defense as F and its explicitly migrated form as M under an authorization-relevant v0-to-v1 tool-contract change."
```

Minimal prompt for a new model:

> Read `PROJECT_STATE.md` completely, refresh its Git snapshot from the live
> repository, then continue only the single next priority while preserving all
> claim and spending boundaries in that file. Update the file before finishing.

The observed Codex goal-registry state `usageLimited` is an execution-system
status, not scientific completion and not permission to change the topic. This
file remains the cross-model continuation mechanism.

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
| `F` | A real defense/policy frozen at its `v0` form and reused unchanged under `v1` | **Not implemented in canonical v2 experiment** | None yet |
| `M` | The same defense with an explicit, documented `v0 -> v1` migration | **Not implemented in canonical v2 experiment** | None yet |
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

### 5.3 What evidence does not yet exist

- No canonical v2 execution of a real `F` defense.
- No canonical v2 execution of the corresponding migrated `M` defense.
- No main-study authorization-relevant contract migration; the current rename
  mapping is a compatibility/negative control.
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

## 8. Live Git state at this handoff

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

### P0 — Preserve the verified v2 seam

1. Review the current diff for scope, secrets, generated files, stale claims,
   and budget values.
2. Confirm the source files listed in section 8 are attributable to this
   research task.
3. Re-run the relevant focused tests and, before release, the full suite.
4. Commit and push only the attributable source/doc patch. Keep generated
   directories and local credentials out of Git.

This is repository hygiene, not the next scientific contribution.

### P1 — Specify one real defense and one real migration

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
