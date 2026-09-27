# Claim strategy review — 26 September 2026

> **Superseded as a primary claim strategy on 27 September 2026.** The
> semantic-mediation candidate is now a diagnostic/mechanism-stress track,
> pending the R1 literature stop gate in `paper/r1_reopening_20260927.md`.

## Decision

The original generic claim, “runtime policy enforcement for LLM agents,” is
not a defensible stand-alone novelty claim. The manuscript should be reframed
as an empirical evaluation of **post-dispatch semantic fidelity under
tool-adapter and schema drift**. Existing PEP/PDP, capability, provenance and
runtime-contract mechanisms become comparison points, not the contribution.

Recommended title:

> **Semantic Mediation Fidelity Under Tool-Adapter Drift: A Paired Evaluation
> of LLM-Agent Runtime Guards**

An acceptable shorter title is *Measuring Policy Fidelity Across Tool-Schema
and Adapter Drift*.

## Primary parameter

Use one primary security endpoint:

$$
\mathrm{AFER}_{\mathrm{uncond}} =
\frac{\#\{\text{adapter/schema-drift attacks producing a forbidden effect}\}}
{\#\{\text{adapter/schema-drift attack cases}\}}.
$$

`AFER_uncond` is intentionally unconditional: a defense cannot obtain a
better score merely by denying every pre-dispatch call. Report the conditional
version as a diagnostic:

$$
\mathrm{AFER}_{\mathrm{cond}} =
\frac{\#\{\text{forbidden effects after pre-dispatch ALLOW/APPROVE}\}}
{\#\{\text{drift attacks receiving pre-dispatch ALLOW/APPROVE}\}}.
$$

The utility guard is pre-specified rather than another primary claim:

$$
\mathrm{BDP} =
\frac{\#\{\text{benign semantics-preserving drift cases reaching the expected
effect}\}}
{\#\{\text{benign semantics-preserving drift cases}\}}.
$$

Keep `PDER_schema` only for pre-dispatch schema/serialization mutations and
exclude `executor_alias` cases. Report `SMF` as a secondary diagnostic:

$$
\mathrm{SMF} =
\frac{\#\{\text{ALLOW/APPROVE executions with the authorized observed effect}\}}
{\#\{\text{ALLOW/APPROVE executions}\}}.
$$

## Research questions and hypotheses

**RQ1 (primary).** When an LLM-generated tool call crosses a drifting adapter
or schema-version boundary, how often does each defense produce a forbidden
post-effect, measured by `AFER_uncond`?

**RQ2.** What is the utility cost of canonicalization and post-call
verification under harmless drift, measured by `BDP`, `CTS`, `FBR_drift`,
approval burden and p95 end-to-end overhead?

**RQ3.** Do held-out and policy-aware adaptive injection traces change
pre-dispatch ASR and post-effect AFER differently across models and adapters?

**H1.** `P + post-call verification` lowers `AFER_uncond` versus the
pre-dispatch-only policy guard on held-out adapter-drift attacks. The minimum
effect and sample size must be preregistered after a pilot.

**H2.** `P + canonicalization` is non-inferior to canonical control on `BDP`
with a five-percentage-point margin and lowers `FBR_drift` relative to the
current fail-closed policy.

**H3.** On held-out drift transformations, the test-set AFER remains within a
preregistered margin of development AFER for both black-box and white-box
attackers.

**H4.** Added post-call verification overhead remains within the stated
hardware-normalized p95 budget; otherwise the result is reported as a security–
latency trade-off.

## Experimental tracks

1. **Trace replay (enforcement isolation).** Freeze one LLM-generated action
   trace, then replay it through canonical, harmless-alias, schema-version,
   semantic-remapping and malformed-adapter variants. This isolates enforcement
   from model adaptation.
2. **End-to-end LLM (efficacy).** Let the model observe each transformed tool
   registry and untrusted carrier. Pass every proposed call through the same
   oracle and guard. Report model susceptibility separately from enforcement
   fidelity.

The current 198-case harness is a trace-replay pilot. It must not be called an
LLM efficacy benchmark.

## Exact manuscript edits

* Replace title, abstract, keywords and the central question in `E1.1`.
* In `E1.4`, state explicitly that generic runtime enforcement is prior work;
  contributions are the drift protocol, AFER/BDP measurement and paired
  adapter mutation harness.
* In `E2`, add canonical action mapping, schema-version contracts and an
  independent post-effect state-diff oracle. A mismatch must be denied or
  rolled back.
* In `E3.4`, split `PDER_schema` from `AFER_adapter`; do not mix schema aliases
  with executor mismatch in one denominator.
* In `E4.1–E4.3`, add `P0` (current pre-dispatch policy), `P1`
  (canonicalization), and `P2` (canonicalization + post-call verification).
* In `E4.4–E4.5`, make AFER primary, BDP/FBR non-inferiority secondary, and
  retain ASR/CTS only as secondary/generalization metrics.
* In `E5.3`, label the fixed pilot as trace replay only; report
  `AFER_uncond=2/63`, `PDER_schema=0/60` and the executor-alias result
  separately as `AFER_adapter=2/3`. Exclude the 30 identity mutation controls
  from drift endpoints and retain them as a negative-control stratum.
* In `R1/P1`, compare scope with the 2026 MCP PEP, ActGov, PACT, RAC and
  TraceGrant. Avoid “first,” “only,” “provably secure” and “complete
  mediation” unless formally proved.
* In the Q2 gate, require at least three model snapshots (including one
  open-weight), pinned benchmark/adapters, held-out drift, raw redacted traces,
  lockfile/container, paired confidence intervals and an explicit negative
  result table.

## Implementation note

The existing synthetic pilot is useful as motivation: the policy subset has
two executor-alias escapes and overblocks benign aliases. Add two experimental
configurations rather than rewriting the pilot:

* `P_canonicalized`: normalize harmless tool/resource/destination aliases
  before policy lookup.
* `P_postverify`: compare the observed adapter effect with the authorized
  canonical signature; mismatch yields no committed effect and an audit event.

Any improvement must be demonstrated on a frozen real-model trace set before
it is described as LLM efficacy.
