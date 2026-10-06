# Working candidate: security regression under versioned agent tool contracts

Research repository for a paper on indirect prompt injection and tool misuse.
The prior *Semantic Mediation Fidelity Under Tool Adapter Drift* direction is
retained as a component stress artifact, not as a locked novelty claim.

This repository is for building the final scientific paper and its reproducible research artifacts. It intentionally excludes weekly class reports and unrelated course files.

The execution, review, and test gates for a Q2-ready manuscript are defined in [ROADMAP.md](ROADMAP.md).

## Current status

R1 was reopened on 27 September 2026 after a closest-prior audit. The active
candidate is **Security Regression Testing of Indirect Prompt-Injection
Defenses under Versioned Agent Tool Contracts**; it is not locked until the
literature stop gate in `paper/r1_reopening_20260927.md` passes. The repository
still contains a proposal plus preliminary component-level validation: the
simulator verifies policy enforcement at a mock tool boundary; it is **not** an
LLM benchmark and does not establish resistance to prompt injection in a real
Agent. A generic runtime tool guard is a reference implementation, not the
paper's novelty.

The first targeted closest-prior screen is documented in
[`paper/r1_targeted_literature_audit_20260927.md`](paper/r1_targeted_literature_audit_20260927.md).
It is a reproducible screening artifact, not a systematic review; R1 remains
open pending an independent replay of the search.

A concise three-paper primary-source synthesis was added on 02 October 2026:
[`paper/literature_update_20261002.md`](paper/literature_update_20261002.md).
It applies the literature result to the active scope without treating the
course-style synthesis as a novelty gate or an LLM evaluation.

The next protocol artifact freezes the missing paired `v0`/`v1` factor rather
than comparing two post-migration tracks: [`experiments/agentdojo_paired_v0_v1_execution_manifest.py`](experiments/agentdojo_paired_v0_v1_execution_manifest.py)
and its fixture define six counterbalanced pairs with a required real-carrier
attack arm and planned
no-injection arms. [`experiments/agentdojo_paired_result_bundle.py`](experiments/agentdojo_paired_result_bundle.py)
now fail-closes any future result whose caller-supplied manifest, registry,
carrier/model/trace evidence is internally inconsistent, and recomputes the
harmful-effect endpoint independently. Those checks do not themselves prove
runtime provenance or carrier materialization. The contract also exposes a
current design defect: the historical manifest does not pin an arm-specific
no-injection initial state or executable utility oracle, so its benign rows
are intentionally unscorable. These artifacts perform zero model or tool
execution and are not benchmark results; a typed-state driver, a versioned
amendment and a task-scoped D1 policy remain required before any efficacy claim.

The prospective repair for that missing instrument is
[experiments/agentdojo_v2_no_injecagent_default_control_contract.py](experiments/agentdojo_v2_no_injecagent_default_control_contract.py)
and its immutable fixture. It establishes a source-pinned
no-InjecAgent default-carrier control for the three v2 cases and invokes the
actual AgentDojo user-utility dispatcher on both terminal output and a typed
function trace. Crucially, the empty input map to AgentDojo still expands to
nonempty default carrier content. The control therefore isolates replacement by
InjecAgent; it is not a carrier-absent or semantically benign arm. It has six
deterministic source-only calibration controls, no LLM/provider/network/remote
job, and does not alter the historical v1 manifest or result bundle.

The follow-up
[experiments/agentdojo_v2_utility_trace_normalization_contract.py](experiments/agentdojo_v2_utility_trace_normalization_contract.py)
closes a compatibility blocker before any v2 manifest is written: v1 changes
exposed tool names whereas the utility scorer accepts canonical names. It pins
the reversible v1-to-v0 name map, preserves arguments, and requires a digest
witness retaining both raw and canonical traces. Its v1 checks are synthetic
renamings of local ground-truth traces, not a v1 runtime or LLM observation.

The next prospective preregistration is
[experiments/agentdojo_paired_v2_execution_manifest.py](experiments/agentdojo_paired_v2_execution_manifest.py).
It fixes twelve unexecuted episodes: three attack pairs and three distinct
no-InjecAgent default-control utility pairs, each crossed over v0/v1 with a
balanced order. The manifest binds both contracts and requires raw/canonical
trace witnesses for default-control v1 records. It is still only a plan: a v2
result-bundle validator and a provenance-capturing driver are intentionally
absent, and no model call is authorized.

The live Runpod preflight and the no-overclaim, budgeted-pilot stop conditions
are recorded in [`paper/runpod_budgeted_pilot_gate_20260927.md`](paper/runpod_budgeted_pilot_gate_20260927.md).
No new billable job was submitted when that gate was recorded.

## Repository layout

```text
paper/
  manuscript.md            Archived mechanism-pilot draft, not the locked paper
  q2_ready_report.md       Archived drift dossier; protocol remains the current scope source
  peer_review_matrix.md    Internal review matrix and Q2 gates
  novelty_pivot_memo.md    Closest-prior review and drift-focused pivot
  claim_strategy_review.md Primary metric/RQ/Hypothesis strategy
  research_protocol.md     Threat model, RQs, protocol, and planned evaluation
  related_work_matrix.md   R1 novelty and overlap gate
  r1_targeted_literature_audit_20260927.md  Search log and closest-prior screen
  literature_update_20261002.md  Three-paper primary-source scope update
experiments/
  policy_guard_sim.py      Offline policy-conformance simulator
  policy_guard_sim_results.json
  offline_benchmark_harness.py
  live_trace_scorer.py      Deterministic scorer for frozen live LLM traces
  test_live_trace_scorer.py Regression tests for causal live scoring
  adapter_attestation.py    Staged adapter/state attestation harness
  agentdojo_contract_migration.py  Fail-closed v0-to-v1 name-only registry control
  agentdojo_pilot_execution_plan.py  No-billable, manifest-bound pilot preflight
  agentdojo_paired_v0_v1_execution_manifest.py  Counterbalanced v0/v1 paired preflight
  agentdojo_paired_result_bundle.py  Fail-closed future-result acceptance and paired transition report
  agentdojo_v2_selected_binding_regeneration_audit.py  Retained historical source-regeneration observation
  agentdojo_v2_selected_binding_regeneration_adjudication.py  Fresh-process correction of that observation
  fixtures/agentdojo_paired_v0_v1_execution_manifest_v1.json  Locked 12-episode plan
  fixtures/agentdojo_v2_selected_binding_regeneration_audit_v1.json  Retained contradicted historical witness
  fixtures/agentdojo_v2_selected_binding_regeneration_adjudication_v1.json  Nine-trial source-only adjudication
  benchmark_outputs/       198-case offline trace benchmark, CSV/JSON/Markdown/SVG
  openai_trace_runner.py   Optional live post-LLM trace generator with carrier/prompt hashes; no tool execution
  live_trace_output.json   Last generic live-track status
  live_trace_runpod_*      Runpod traces, including realistic seven-case pilot
  fixtures/
    agentdojo_pilot_*_v1.json  Pinned feasibility population and execution plan
    policy_v1.json         Versioned capabilities and static allowlist
    cases_v1.json          Versioned calls and security/utility oracles
    split_v1.json          Locked development/test source-component split
```

## Run the prototype check

The current prototype has no third-party Python dependencies.

```powershell
python experiments/policy_guard_sim.py --self-test --output experiments/policy_guard_sim_results.json
```

Run the expanded deterministic trace benchmark:

```powershell
python experiments/offline_benchmark_harness.py --self-test `
  --output-dir experiments/benchmark_outputs --seed 20260926 --bootstrap 1000
```

The harness also supports a locked, source-component split that keeps each
attack/benign-twin pair together and rejects canonical-signature leakage:

```powershell
python experiments/offline_benchmark_harness.py --self-test --split test `
  --output-dir experiments/benchmark_outputs_test --seed 20260926 --bootstrap 1000
```

The split is declared in `experiments/fixtures/split_v1.json` and is still a
synthetic post-LLM trace replay; it is not evidence of independent LLM
efficacy.

Or run both regression checks plus syntax validation with:

```powershell
.\scripts\reproduce_main_table.ps1
```

The optional live trace runner supports a no-network manifest mode and a
non-billing authentication probe. `--dry-run` records case/prompt hashes only;
`--check-auth` performs `GET /models` and never creates a completion. A local
OpenAI-compatible server can be selected with `OPENAI_BASE_URL`; anonymous
access is accepted only for loopback URLs (`localhost`, `127.0.0.1`, `::1`).
The current remote probe is intentionally recorded as `blocked_http_401`; no
paid completion is attempted without an authorized credential.

```powershell
python experiments/openai_trace_runner.py --dry-run `
  --output qa/live_trace_dryrun.json
python experiments/openai_trace_runner.py --check-auth --max-cases 0 `
  --output qa/live_trace_authcheck.json
```

## Local LLM smoke track

This repository includes a CPU-compatible local path for trace generation. The
host used for the artifact has 16 GB RAM and no NVIDIA CUDA device, so this
track is for integration/smoke validation rather than the primary efficacy
claim.

Install the runtime and create the pinned Python environment:

```powershell
winget install --id ggml.llamacpp -e --accept-source-agreements --accept-package-agreements
uv venv --python 3.13 .venv
```

Start Qwen3-4B in an OpenAI-compatible local server (the first run downloads
the GGUF file):

```powershell
.\scripts\start_local_llm.ps1
```

On a CPU-only machine, use the smaller smoke model after downloading it:

```powershell
New-Item -ItemType Directory -Force D:\Models\qwen3 | Out-Null
curl.exe -L --fail -o D:\Models\qwen3\Qwen3-0.6B-Q4_0.gguf `
  https://huggingface.co/ggml-org/Qwen3-0.6B-GGUF/resolve/main/Qwen3-0.6B-Q4_0.gguf
.\scripts\start_local_llm.ps1 `
  -ModelPath D:\Models\qwen3\Qwen3-0.6B-Q4_0.gguf -Context 4096 -Threads 8
```

Then generate redacted traces through the local Chat Completions endpoint:

```powershell
.\.venv\Scripts\python.exe experiments/openai_trace_runner.py `
  --api-style chat --base-url http://127.0.0.1:8080/v1 `
  --model Qwen/Qwen3-4B-GGUF:Q4_K_M --max-cases 7 `
  --seed 20260926 --temperature 0 --top-p 1 `
  --max-output-tokens 256 `
  --output experiments/live_trace_qwen3_4b_local.json
```

The exact local model/runtime fields are recorded in
`experiments/local_model_run_manifest.json`. Keep this track separate from the
main paper result: the latter still requires a pinned CUDA run on at least
three model snapshots and an external agent benchmark.

The completed CPU smoke run is recorded in
`experiments/local_model_smoke_run.json` and
`experiments/live_trace_qwen3_0_6b_local_full7.json`. It generated seven
post-LLM proposals without executing any tool; malformed or incomplete model
proposals remain valid failure outcomes and must not be silently repaired.

## Runpod endpoint track

The project records a manually released Runpod serverless queue endpoint for
the independent benchmark: `h5ec6v08cb8uc2`. The endpoint manifest is
`experiments/runpod_endpoint_manifest.json`; it contains no credential and
must be refreshed from a live read before a billable run.

Set the account key only in the current shell, then check readiness and model
discovery before submitting a completion:

```powershell
$env:RUNPOD_API_KEY = "<paste locally; never commit or send in chat>"
.\scripts\check_runpod_endpoint.ps1
```

This endpoint is a `serverless_queue`. Its documented OpenAI-compatible route
is `/openai/v1`; the local `experiments/runpod_openai_proxy.py` is the
tool-bearing fallback. It submits a queue job to `/run` with
`input.route=/v1/chat/completions`, logs no prompt or key (only job identity,
request hash, and lifecycle metadata), polls `/status`, and requests
`/cancel/<job-id>` on deadline or polling failure. The
deployed model is `qwen/qwen3-8b`,
with vLLM `ENABLE_AUTO_TOOL_CHOICE=true` and `TOOL_CALL_PARSER=hermes`. A
completion is billable, so it is intentionally guarded:

```powershell
$env:RUNPOD_MODEL = "Qwen/Qwen3-8B"
.\scripts\run_runpod_trace.ps1 -MaxCases 1 -ConfirmBillable
```

This invokes the OpenAI-compatible route and writes
`experiments/live_trace_runpod_h5ec6v08cb8uc2.json`. The runner resolves
`RUNPOD_API_KEY` only for Runpod URLs, never writes the key, and still never
executes a proposed tool. If the endpoint exposes only the generic Runpod
worker route shown in its Quick start panel, use the `/runsync` adapter:

```powershell
.\scripts\run_runpod_trace.ps1 -Transport runsync -MaxCases 1 -ConfirmBillable
```

Do not use `-Transport direct` for this endpoint. The
`https://<endpoint-id>.api.runpod.ai/v1` surface is for Runpod load-balancing
endpoints, not a queue endpoint; the script now fails fast before a billable
request if the manifest identifies a queue.

The native queue path uses a larger output budget because Qwen3 may emit a
reasoning trace before its JSON:

```powershell
.\scripts\run_runpod_trace.ps1 -Transport runsync -MaxCases 1 `
  -MaxOutputTokens 2048 -ConfirmBillable
```

The separate standalone trace runner's `/runsync` path forwards the supplied request body to the worker's
`/v1/chat/completions` route. The AgentDojo queue proxy's local ledger is a
recoverability control, not a Runpod-enforced dollar cap; an ambiguous submit
without a job ID, or any unreconciled job receipt, blocks further submissions.
The launcher reconciles old receipts before either arm begins. A terminal
status observed after `/cancel` may be `COMPLETED` or `FAILED` due to a race;
it does not prove that the cancellation request stopped execution. The
standalone trace runner can request
`chat_template_kwargs.enable_thinking=false`; the AgentDojo proxy does not
inject sampling or thinking parameters, so every full run must archive its
actual serialized request before those parameters are described as locked.

For the pinned independent benchmark, first acquire the exact AgentDojo source
and lockfile, then run the one-task paired smoke. The Runpod key is injected
only through the current shell or CI secret; the script never reads a Codex
configuration file:

```powershell
$benchRoot = "D:\Research\benchmarks"
python experiments/independent_benchmark_runner.py --source-root $benchRoot --fetch --smoke
python scripts/run_agentdojo_paired_smoke.py --source-root $benchRoot
```

The script starts the proxy, runs the same `user_task_0`/`injection_task_0`
once for baseline and once for the attested adapter, and writes a short
manifest under `qa/`. The current one-task artifact is a pilot only: both
tracks completed with 100% utility and 0% injection security, so it is
evidence of end-to-end execution and a reproducible failure case—not a Q2
efficacy result.

Before any new billable feasibility episode, verify the separately committed,
outcome-blind population artifact. It enumerates 840 carrier-visible
AgentDojo/InjecAgent candidates at the pinned source commit and selects three
single-carrier feasibility cases by a fixed hash rule. It contains no model
outputs or outcome labels, and the selected three cases are neither an efficacy
sample nor a population estimate:

```powershell
python experiments/agentdojo_pilot_manifest.py --verify
$agentDojo = Join-Path $benchRoot "agentdojo"
& "$agentDojo\.venv\Scripts\python.exe" experiments/agentdojo_pilot_manifest.py `
  --verify --source $agentDojo
```

`independent_benchmark_runner.py --smoke` validates the manifest digest and
its contract-migration dependency before reporting the benchmark pin. The
current paired-smoke launcher is deliberately **not** a generic executor for
these selected rows; a run-bound case/arm driver, independent outcome adapter,
and a renewed endpoint/cost confirmation remain required before a billable
episode.

The companion preflight plan is separately reproducible and makes no model,
network, proxy, credential, or sandbox call:

```powershell
python experiments/agentdojo_pilot_execution_plan.py --verify
```

It locks 12 unexecuted invocations (3 selected cases × attack/benign twin ×
baseline/attested) and records 18 nominal upstream task episodes: every
InjecAgent invocation contains an additional standalone injection-task utility
episode. It deliberately marks every benign-twin execution as blocked because
the current generic runner always enables InjecAgent; omitting only
`--injection-task` would broaden the attack set rather than produce a benign
twin. This is a preflight artifact, not a successful run or cost estimate.

The historical three-case plan is now additionally **blocked** by a
source-only harmful-effect-oracle qualification. It materializes each exact
injected pre-state from the pinned source, verifies that the upstream predicate
is false before any local action, and then exercises only that injection task's
deterministic ground truth. No model, endpoint, proxy, network request, or
Runpod job is involved:

```powershell
python experiments/agentdojo_pilot_oracle_qualification.py --verify
$agentDojo = Join-Path $benchRoot "agentdojo"
& "$agentDojo\.venv\Scripts\python.exe" experiments/agentdojo_pilot_oracle_qualification.py `
  --verify --source $agentDojo
```

Two cases qualify, but the selected email case
`user_task_18`/`injection_task_0` fails the positive control on its own
InjecAgent-injected state: its upstream predicate remains false even after the
local injection-task ground truth. It must not be scheduled or interpreted as
a secure outcome. A future replacement needs a new outcome-blind selection
artifact with a stated oracle-eligibility rule, rather than a manual case
substitution. This calibration is neither an LLM result nor a defense-efficacy
result.

That replacement is now frozen separately in
`experiments/fixtures/agentdojo_oracle_qualified_selection_v2.json`. It keeps
v1 immutable and blocked, censes every structural candidate in the amended
calendar, Drive, and email-content-exfiltration strata, and chooses one row per
stratum from source-qualified rows with a seed derived only from immutable v1
inputs and the v2 stratum specification:

```powershell
python experiments/agentdojo_oracle_qualified_selection_v2.py --verify
$agentDojo = Join-Path $benchRoot "agentdojo"
& "$agentDojo\.venv\Scripts\python.exe" experiments/agentdojo_oracle_qualified_selection_v2.py `
  --verify --source $agentDojo
```

The census contains 60 structural rows (29 source-qualified single-carrier
rows) and retains all multi-carrier exclusions. The v1 email `injection_task_0`
pool has zero qualifying single-carrier rows; v2 therefore declares—not
conceals—a new task-3 **email-content-exfiltration** threat family. Its exact
AgentDojo predicate is non-monotone (duplicate or extra-recipient email can
evade it), so it supports only canonical-predicate calibration, never a claim
of complete exfiltration detection or defense efficacy. V2 is not an executor:
a new manifest-bound driver and a true benign control are still required.

The known count-based oracle defect is now repaired at the **measurement
instrument** level by
`experiments/fixtures/agentdojo_v2_effect_oracle_contract_v1.json`. The
contract is decision-independent: its future scorer reads only typed pre/post
Workspace state, never a guard decision, policy, adapter audit, model label or
upstream aggregate `security` flag. It pins the selected v2 artifact, source
files, code hash and reset-state hash; malformed evidence, drift, timeout or
missing snapshots is `not_scored` rather than “secure”. Verify it locally:

```powershell
python experiments/agentdojo_v2_effect_oracle_contract.py --verify
$agentDojo = Join-Path $benchRoot "agentdojo"
& "$agentDojo\.venv\Scripts\python.exe" experiments/agentdojo_v2_effect_oracle_contract.py `
  --verify --source $agentDojo
```

Its 15 deterministic source controls use no model, provider, network or
Runpod job. They show that a new matching calendar event and a deleted Drive
file remain detected without an exact-count condition; for email, duplicate,
extra-recipient, CC-target, BCC-target and send-then-delete variants remain
detected across both active mail and trash even when the upstream predicate
returns `false`.
This is not LLM efficacy evidence. The email rule is limited to literal
source-body-bearing egress in the pinned sandbox, not paraphrase, partial
leakage, attachments, encryption or side channels; a dedicated driver and a
genuine no-injection benign arm remain mandatory before any run.
The source-backed verification command also exercises the full score API on
three fresh/positive local controls (six scored control states). This validates
the declared state-evidence interface only. Until a manifest-bound driver
creates provenance-bound snapshots, the supplied source/reset/status fields
are assertions, not admissible benchmark observations.

The prior 03 October v2 selected-binding audit fixture remains preserved,
but its claimed all-case pre-state mismatch is now a **contradicted historical
observation**, not a current benchmark finding. The correction in
`experiments/fixtures/agentdojo_v2_selected_binding_regeneration_adjudication_v1.json`
starts three separate processes, each reconstructing all three selected
bindings. In one recorded local runtime environment with incomplete
installation/build provenance, all nine trials reproduce
the frozen carrier, injection-map, and canonical pre-state witnesses. It also
records workspace-data hashes, AgentDojo import origin, Python executable and
digest, package manifest, locale/timezone, and seed policy. It preserves the
older fixture unchanged and does not assert why it differed; package names and
versions do not independently attest a particular `uv sync` or build.

Re-execute the correction locally with no model or remote call:

```powershell
$agentDojo = Join-Path $benchRoot "agentdojo"
& "$agentDojo\.venv\Scripts\python.exe" experiments/agentdojo_v2_selected_binding_regeneration_adjudication.py `
  --verify --source $agentDojo
```

`source_reexecution_match: true` means the complete nine-trial source-only
adjudication reproduced in that same captured environment. It clears only the
specific prior mismatch assertion. It is not an LLM, defense, utility,
benchmark, or statistical result; it neither explains the older fixture nor
authorizes the historical v2 runtime plan. That plan remains unexecutable
until a future versioned design supplies its genuine no-injection initial
state and utility oracle, manifest-bound driver, reset/trace provenance, fair
baselines, and the remaining scientific gates.

The prospective default-control repair is reproducible from the same pinned
source environment:

~~~powershell
$agentDojo = Join-Path $benchRoot "agentdojo"
& "$agentDojo\.venv\Scripts\python.exe" experiments/agentdojo_v2_no_injecagent_default_control_contract.py `
  --verify --source $agentDojo
~~~

The verified report must show source_regeneration_match: true and three
scored negative/positive source controls. This only qualifies the initial-state
and utility-oracle instrument for a future manifest v2. It retains default
carrier content, stores no raw carrier text/output/trace in Git, cannot prove
runtime provenance, and is not permission to execute a model or Runpod job.

Verify the required v0/v1 trace-name compatibility before a future v2 driver:

~~~powershell
& "$agentDojo\.venv\Scripts\python.exe" experiments/agentdojo_v2_utility_trace_normalization_contract.py `
  --verify --source $agentDojo
~~~

Both paired tracks now load the reviewed
`experiments/fixtures/agentdojo_contract_v0_to_v1.json` before AgentDojo
serializes its tool schemas. It migrates all 24 pinned Workspace function names
from `v0` to distinct `v1_*` names while preserving their implementation and
parameter schemas, then emits a name-independent hash witness. The baseline
omits only the attestation adapter; it does not omit this controlled migration.
The local pinned-runtime check is recorded in
`experiments/agentdojo_contract_migration_validation_20260927.json`. This is a
feasibility/control validation, not a security or LLM-efficacy result.

The expected component result is that the policy guard prevents all four fixed forbidden effects, automatically completes two benign calls, and completes one benign high-risk call only after a simulated approval. The expanded harness evaluates 198 deterministic post-LLM traces and deliberately reports alias overblocking and adapter-mismatch residuals. Both are conformance/stress results, not attack-success-rate results for an LLM.

The live runner also supports `--prompt-mode realistic`. This track removes
attack/benign labels and the fixture case identifier from the model prompt while
retaining the task capability schema. The frozen seven-case Qwen3-8B run is
`experiments/live_trace_runpod_gbo4nj1k5ublmt_realistic7.json`; it remains a
descriptive pilot because it has one model, seven handcrafted cases, no
adapter-drift replay, and no external benchmark.

The adapter boundary is tested separately:

```powershell
python experiments/adapter_attestation.py --self-test `
  --output qa/adapter_attestation_selftest.json
python experiments/adapter_attestation.py --fixture-smoke `
  --output qa/adapter_attestation_fixture_smoke.json
python -m unittest experiments.test_live_trace_scorer -v
```

The attestation harness verifies staged commit, session-bound nonce,
normalized arguments/body, pre/post state hashes, recursive state diff,
replay/TOCTOU rejection, and canary evidence. It is an
enforcement-isolation artifact, not proof that an irreversible external side
effect can be rolled back after emission.

GitHub Actions runs the JSON validation and simulator self-test on each push and pull request. It does not call an LLM, use secrets, or contact real tools. The Runpod Qwen3-8B seven-case trace is now frozen as a pilot and scored by `experiments/live_trace_scorer.py`; the full LLM efficacy benchmark remains pending because this pilot has no drift mutation, held-out split, or model replication.

## Research scope

The active candidate investigates whether a defense that prevents an
indirect-prompt-injection effect under a tool contract `v0` regresses after a
controlled `v1` migration. The primary parameter would be a paired,
action-grounded security-regression rate; benign end-state success,
escalation/approval burden and latency are guardrails. Semantic mediation
fidelity, AFER and benign drift portability remain mechanism-level diagnostic
metrics. The full experiment would combine paired trace replay for enforcement
isolation with end-to-end LLM efficacy on AgentDojo/InjecAgent or an equivalent
sandbox.

The study does not claim a new capability system, information-flow-control
mechanism, post-call contract, generic drift benchmark, or generic solution to
prompt injection. It evaluates action-grounded security regression and keeps
semantic-mediation diagnostics separate from LLM efficacy claims.

## Next research steps

1. Run the frozen trace-replay protocol on a real model trace set, preserving
   separate P0/P1/P2 outputs and raw redacted traces.
2. Run the preregistered end-to-end track on at least three model snapshots
   (including one open-weight model) with AgentDojo/InjecAgent or an equivalent
   sandbox, held-out drift, paired confidence intervals and failure analysis.
3. Add lockfile/container, session binding, expiry, argument-level constraints,
   state-diff logging and a real adapter-bypass integration test before making a
   Q2 submission claim.
