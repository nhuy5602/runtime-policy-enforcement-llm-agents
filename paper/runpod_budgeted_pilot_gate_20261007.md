# Runpod budgeted pilot gate — 7 October 2026

## Current decision

**NO-GO for a billable job at this checkpoint.** The explicit authorization
in this thread is **USD 10.00 total**, including overhead, with a planned
**USD 8.00 execution envelope + USD 2.00 reserve**. The pasted parallel-chat
claim of USD 13.00 is not new spending authorization and is withdrawn here.
This is an aggregate authorization, not a new allowance for every run.
Request/tool-count caps do not enforce a provider-side dollar ceiling. Prior
spending and the specific resource authorization must be reconciled before
submission; this document does not establish a current available balance.

The permitted pilot is integration feasibility only:

- one attack pair and one `no_injecagent_default_control` pair;
- both `v0` and `v1` siblings, four episodes total;
- one already-bound model snapshot and the frozen v2 manifest;
- per episode, at most 8 model requests and 16 tool dispatches; overflow aborts
  the fresh child before the next provider/tool call and leaves the row
  `not_run`;
- no replacement, no automatic retry, and no additional case chosen after
  observing an outcome.

It cannot support ASR/AFER estimation, population inference, defense
superiority, statistical significance, or a Q2 claim.

## Preconditions before the first paid request

The 9 October continuation protocol in `PROJECT_STATE.md` takes precedence:
automatic jobs remain off, and each paid job requires an explicit user message
to run it. The next scientific priority is the executable F/M comparison and
its non-billable preflight/review, not a new U/D0 remote run.

1. Run the local fake-provider bridge test and the v2 validator under the
   pinned AgentDojo environment:

   ```powershell
   $env:PYTHONUTF8 = "0"
   $env:PYTHONIOENCODING = "utf-8"
   & "tmp\agentdojo-source\.venv31213\Scripts\python.exe" `
     -m unittest experiments.test_agentdojo_paired_v2_capture_bridge -v
   ```

2. Confirm the endpoint and model identity in the current Runpod account
   snapshot. Do not create or modify an endpoint for this pilot.

3. Confirm a clean local job ledger and reconcile every prior job before
   submission. An ambiguous submission, torn ledger, nonterminal job, missing
   billing read, or failed cancellation is an immediate stop.

4. Use the canonical driver in capture mode. It rejects a missing URL/key,
   requires the pinned parent/child runtime, uses the four-episode pilot
   filter, enforces the preregistered request/tool caps, and stops provider
   calls after the first bridge failure.

5. Stop before submission if any record lacks reset, source, registry,
   migration, request/response, carrier/default-control, or oracle evidence.

## Evidence and claim boundary

The output must retain the fixed twelve-row denominator. Only the four selected
rows may be completed; the remaining eight rows stay `pilot_pair_not_selected`.
The v2 validator must be run with the pinned source checkout so default-control
utility is recomputed through AgentDojo's upstream dispatcher. A completed
pilot is still only evidence that the capture pipeline executed in the pinned
sandbox. Current dispatch provenance is retained only as a digest/count
commitment; no security or utility efficacy claim is allowed until a
per-dispatch redacted commitment is retained and validated.

The historical gate
[`runpod_budgeted_pilot_gate_20260927.md`](runpod_budgeted_pilot_gate_20260927.md)
remains a dated record; its USD 10.00 authorization has not been expanded by
the imported chat.

## Preflight reported by the parallel chat on 7 October 2026

- Endpoint `h5ec6v08cb8uc2` is `q2-agentdojo-toolcalling-hub-20260926`,
  type `QUEUE`, model env `qwen/qwen3-8b`, image
  `registry.runpod.net/runpod-workers-worker-vllm-main-dockerfile:16d63772e`,
  GPU pool `AMPERE_80`, one GPU per worker, `workers.min=0`,
  `workers.max=1`, and release `cmuiv9ikc006zsrv0m5oo5ims`.
- Health reported `completed=45`, `failed=0`, `inProgress=0`, `inQueue=0`;
  the active worker `9p3zguw2bjm9lc` in `US-MD-1` was `THROTTLED`, with
  `unhealthy=0`.
- Serverless billing for this endpoint from 1–7 October 2026 returned no
  records and total `0`; aggregate account billing for the same window also
  returned no records and total `0`.

These figures are retained as reported context, not independently rechecked in
this integration review. They do not establish current readiness, available
credit, or authority to submit a new job.
