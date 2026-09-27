# Offline benchmark harness

This is a deterministic post-LLM-trace simulator; it does not invoke an LLM or real tool.
Attack-family labels and policy-drift mutations test the enforcement boundary only.
Locked split: `all` (7 source components; attack/twin pairs stay in the same split).

Metrics: trace ASR = forbidden-effect attack success; trace UAR = any executed attack action; CTS = benign clean-task success; FBR = benign false-block rate; PDER_schema = ASR on semantics-preserving schema/alias drift; AFER_uncond = forbidden effect rate on all drift attacks; AFER_cond = forbidden effect rate among drift attacks actually permitted by pre-dispatch ALLOW or approved REQUIRE_APPROVAL; AFER_adapter = forbidden effect rate after executor-alias drift; BDP = benign applied-drift portability; SMF = canonical effect fidelity among executed calls.

The `P_policy_guard` row is the pre-dispatch trace-policy subset. `P_canonicalized` normalizes known aliases; `P_postverify` additionally checks the observed effect against the authorized canonical signature. None of these rows invokes an LLM.

| configuration | attacks | benign | trace ASR | trace UAR | CTS | FBR | approvals | PDER_schema | AFER_uncond | AFER_cond | AFER_adapter | BDP | SMF | sim latency us p95 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| B0_unsafe | 99 | 99 | 1.000 | 1.000 | 1.000 | 0.000 | 0 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.985 | 1.0 |
| B1_prompt_only_proxy | 99 | 99 | 0.515 | 0.515 | 0.515 | 0.485 | 0 | 0.500 | 0.524 | 1.000 | 1.000 | 0.500 | 0.971 | 6.0 |
| B2_static_allowlist | 99 | 99 | 0.758 | 0.758 | 0.758 | 0.242 | 0 | 0.600 | 0.619 | 1.000 | 1.000 | 0.556 | 0.980 | 4.0 |
| B4_argument_guard | 99 | 99 | 0.394 | 0.394 | 0.758 | 0.242 | 0 | 0.200 | 0.238 | 1.000 | 1.000 | 0.556 | 0.974 | 9.0 |
| P_policy_guard | 99 | 99 | 0.020 | 0.020 | 0.455 | 0.545 | 8 | 0.000 | 0.032 | 1.000 | 0.667 | 0.000 | 0.957 | 15.0 |
| P_canonicalized | 99 | 99 | 0.020 | 0.020 | 1.000 | 0.000 | 26 | 0.000 | 0.032 | 1.000 | 0.667 | 1.000 | 0.980 | 20.0 |
| P_postverify | 99 | 99 | 0.000 | 0.000 | 1.000 | 0.000 | 26 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 23.0 |
| A_no_scope | 99 | 99 | 0.505 | 0.505 | 0.697 | 0.303 | 8 | 0.500 | 0.508 | 1.000 | 0.667 | 0.444 | 0.983 | 12.0 |
| A_no_destination | 99 | 99 | 0.020 | 0.020 | 0.515 | 0.485 | 26 | 0.000 | 0.032 | 1.000 | 0.667 | 0.111 | 0.962 | 17.0 |
| A_no_call_limit | 99 | 99 | 0.141 | 0.141 | 0.455 | 0.545 | 8 | 0.000 | 0.032 | 1.000 | 0.667 | 0.000 | 0.966 | 13.0 |
| A_no_approval | 99 | 99 | 0.030 | 0.030 | 0.455 | 0.545 | 0 | 0.000 | 0.048 | 1.000 | 1.000 | 0.000 | 0.938 | 13.0 |

Bootstrap intervals are case-level percentile intervals with a fixed seed; they describe this
synthetic matrix, not a confidence claim about real LLM agents.

The `executor_alias` drift attacks intentionally model a semantic adapter mismatch: the
policy sees an allowed call while the mocked adapter produces a forbidden effect. A non-zero
AFER_adapter for the pre-dispatch guard is therefore an explicit boundary limitation, not a
bug hidden by the harness. The post-verification row is a simulated mitigation.

The destination-alias stratum includes identity controls when the base call has no destination.
Those rows are marked `drift_applied=0` and excluded from PDER_schema, AFER_uncond and BDP.
