# IMRaD migration plan and claim freeze

**Status:** editorial plan, not a manuscript and not an empirical result
**Date:** 2026-09-26
**Source dossier:** `paper/q2_ready_report.md`
**Canonical manuscript target:** `paper/imrad_manuscript.md` (to be created only after the
full-result freeze)

## Editorial decision

`q2_ready_report.md` is a research dossier: it combines a protocol, implementation
notes, a deterministic trace-replay pilot, readiness gates, simulated reviews, and
future-run tables. It should not be submitted as the main article.

The journal article should use a conventional structure:

1. Title, abstract, keywords
2. Introduction
3. Related work and contribution boundary
4. Problem definition and threat model
5. Method
6. Experimental methodology
7. Results
8. Discussion
9. Threats to validity, limitations, and ethics
10. Conclusion
11. References

The current `5 + 3 + 2` structure is retained as an internal quality-control map
and, if useful, a short appendix table. It is not a replacement for IMRaD.

## Migration rules

1. Use one canonical manuscript. The current `paper/manuscript.md` is stale and
   must not be merged piecemeal with `q2_ready_report.md`.
2. Write the submission manuscript in English unless the target venue explicitly
   accepts Vietnamese. Vietnamese planning notes may remain in the repository.
3. Keep only claims backed by a frozen run manifest in the main article. Mark
   unexecuted work as `planned` in the dossier, never as a result.
4. Do not put simulated reviewer dialogue, Q2 scorecards, or project-management
   prose in the main article. Move them to supplementary material or an internal
   review file.
5. Write the abstract, results summary, and conclusion last. Their numbers must
   be generated from the same machine-readable result table.
6. Every binary metric in the article must show its numerator, denominator,
   uncertainty interval, and unit of analysis. If cases are paired or clustered,
   the interval must use that pairing/cluster.
7. Keep the pilot and full efficacy tracks separate. A live-model pilot must not
   be presented as AgentDojo/InjecAgent efficacy.

## Section mapping

| IMRaD section | Keep from `q2_ready_report.md` | Rewrite or add | Move out of main article |
|---|---|---|---|
| Title | Title concept: *Semantic Mediation Fidelity Under Tool-Adapter Drift* | Add the attack setting and evaluation scope; avoid implying a new generic runtime guard | Version/date/status banner |
| Abstract | E1.1 research problem; C1–C3 contribution boundary; E5 result schema | Replace all planned numbers with final frozen results; state benchmark, models, primary endpoint, uncertainty, and limitation | Pilot disclaimers longer than one sentence; Q2 language |
| Keywords | Existing keywords | Keep 5–8 indexable terms | Internal labels such as E1–E5/R1–R3/P1–P2 |
| 1. Introduction | E1 motivation, central question, RQ1–RQ3, E1.4 novelty boundary | Add a concise problem example showing a permitted call becoming a forbidden effect after adaptation; state hypotheses and contributions in 3–4 bullets | Full threat-model detail; readiness gates; simulated rebuttals |
| 2. Related work | R1.2 closest-prior matrix; E3.1 benchmark context | Condense into capability/IFC/runtime-policy/action-validation/benchmark families; mark peer-reviewed papers versus preprints; state exact non-overlap with MCP-PEP, CaMeL, Fides, Progent, AgentArmor, AgentSpec, PACT, ActGov, RAC, TraceGrant | Full literature audit, claim-strategy memo, reviewer pass/fail checklist |
| 3. Problem definition and threat model | E1.2 episode model; E1.3 attacker/assets; E2.4 invariants | Define canonical call, observed effect, semantic equivalence, forbidden effect, TCB, non-goals, and irreversible-effect boundary; add an explicit direct-executor bypass threat | Long policy JSON examples; exhaustive attack-family prose |
| 4. Method | E2.1–E2.3 architecture, policy manifest, decision semantics; C1–C3 | Give the normalization/dispatch/attestation algorithm, canonical effect signature, post-effect oracle, and fail-closed behavior; distinguish detection-after-effect from prevention-before-commit | Implementation diary; every fixture validation rule; full source listings |
| 5. Experimental methodology | E3.1–E3.4 benchmark/protocol; E4.1–E4.6 baselines, models, ablations, metrics, statistics, reproducibility | Freeze benchmark commits, model digests, prompt, seeds, split, mutation registry, hardware, cost, and stopping rule; specify paired analysis and power/precision target | Full case manifest, raw prompts, redacted traces, lockfile details, CI logs |
| 6. Results | E5.1–E5.4 only after status is frozen | Organize as (a) primary AFER/SMF, (b) benign utility/BDP, (c) model efficacy and attack families, (d) overhead, (e) ablations | `pending` tables; pilot-only results unless clearly labelled as a sanity check |
| 7. Discussion | E5.6 failure analysis; interpretation of E5.3–E5.4 | Explain model-versus-guard-versus-adapter failures, security–utility trade-off, relation to closest prior, and negative findings | Reviewer A/B simulated responses; project roadmap |
| 8. Validity, limitations, ethics | R3.1–R3.4; “Giới hạn hiện tại” | Separate construct, internal, statistical, and external validity; discuss synthetic secrets, sandboxing, irreversible effects, provider variance, and residual bypass risk | Q2 readiness scorecard; pass/fail gate table |
| 9. Conclusion | E5 and final conclusion | State only evidenced contribution and bounded result; include one sentence on what remains unverified | Future-work backlog and implementation checklist |
| References | `references.bib` | Generate one bibliography from the canonical `.bib`; verify venue/status/DOI | Duplicate hand-maintained reference lists |

## Main-article content budget

The following is a practical target for a 10–12 page journal-format article,
excluding references and supplement:

| Section | Target content |
|---|---|
| Introduction | 1–1.5 pages; one motivating adapter-remapping example |
| Related work | 1–1.5 pages; one closest-prior comparison table |
| Problem/threat model | 1 page; one threat/TCB diagram |
| Method | 2 pages; one architecture diagram and one algorithm box |
| Experimental methodology | 1.5–2 pages; one matrix table |
| Results | 2–3 pages; primary table, utility/overhead table, failure figure |
| Discussion/validity/ethics | 1.5–2 pages |
| Conclusion | 0.25–0.5 page |

If the venue has a different page limit, preserve the order and claim boundary,
not the exact page counts.

## What belongs in the supplement or artifact

### Supplementary methods

- Complete policy schema and all validation constraints.
- Canonicalization alias tables and the full mutation registry.
- Formal definitions of `AFER_uncond`, `AFER_cond`, `PDER_schema`, `SMF`,
  `BDP`, `CTS`, `FBR`, `STS`, approval burden, and mediation coverage.
- Full baseline configuration, prompt templates, tool descriptions, decoding
  parameters, and repair/retry rules.
- Power or precision calculations and multiplicity-correction plan.
- Additional ablations, per-domain/per-model tables, and all negative results.
- Complete threat-to-validity and reviewer-response matrix.

### Artifact package

- Frozen benchmark and adapter commits.
- Model identifiers/checksums, container or lockfile, hardware and endpoint
  manifest.
- Policy/case/mutation manifests and hashes.
- Redacted raw traces, effect/state-diff logs, canary definitions, and scorer.
- One-command reproduction of the primary table.
- Security and data card documenting that no real secrets or external side
  effects are used.

### Internal-only documents

- `5 + 3 + 2` work-package map.
- Reviewer A/B simulated rebuttals.
- Q2 scorecard and readiness gate.
- Runpod setup notes and billing/endpoint diagnostics.
- Stale manuscript versions and migration logs.

## Claim freeze

### Claims allowed before the full benchmark

The dossier and any pilot-only draft may state:

1. The work proposes a drift-aware evaluation protocol that separates
   pre-dispatch authorization from observed post-adapter effects.
2. The work defines the AFER/SMF/BDP metric suite and a paired mutation harness.
3. In the deterministic trace-replay pilot, the stated configurations produced
   the stated fixture outcomes. These are mock/simulator results.
4. The seven-case Qwen3-8B Runpod execution is a parser and integration pilot,
   not a general LLM-efficacy result.
5. Generic runtime policy enforcement, capability control, provenance control,
   and post-effect verification are established directions; this paper does
   not claim to be the first in any of them.

### Claims forbidden until the acceptance gates pass

Do not write any of the following in the article:

- “Q2-ready,” “state of the art,” “first,” “only,” or “novel runtime policy
  enforcement” without a specific, evidenced scope.
- “Full LLM efficacy,” “AgentDojo efficacy,” or “InjecAgent efficacy” without
  a pinned run on that benchmark.
- “Prevents prompt injection” as a general claim.
- “AFER = 0” or “P2 prevents forbidden effects” when the oracle only detects an
  effect after it was created or hides it in post-processing.
- “Complete mediation,” “provably secure,” or “production-safe” without a
  formal proof and integration evidence covering direct-executor bypass,
  TOCTOU, stale capability, and adapter failure.
- Cross-model generalization from one Qwen endpoint or from a seven-case pilot.
- Statistical superiority from the three adapter cases or from row-bootstrap
  intervals that ignore source-case clustering.

## Acceptance gates for unfreezing the main article

The canonical manuscript may replace pilot language with efficacy language only
when all gates below are satisfied:

| Gate | Required evidence | Current status |
|---|---|---|
| Independent benchmark | Pinned AgentDojo and/or InjecAgent run, plus a documented custom drift suite | Not met |
| Model coverage | At least three model snapshots, including one reproducible open-weight model | Not met |
| Adapter fidelity | Real sandbox adapter/proxy with semantic-preserving and semantic-changing mutations | Not met |
| Independent oracle | Arguments/payload, canary/sink, state-diff, and irreversible-effect semantics | Not met |
| Mediation proof | Direct-executor bypass, stale/replay token, TOCTOU, fail-open/fail-closed tests | Not met |
| Strong baselines | Approval upper bound and at least one executable closest-prior defense | Not met |
| Held-out evaluation | Split by domain/schema/attack template; black-box and white-box adaptive tracks | Not met |
| Statistics | Paired/clustered 95% intervals, effect sizes, multiplicity correction, precision/power rationale | Not met |
| Reproducibility | Container/lockfile, model/benchmark hashes, redacted traces, one-command table reproduction | Not met |
| Canonical consistency | One manuscript, one bibliography, no stale `pending` cells in Results | Not met |

Until all gates pass, the manuscript title and abstract must include neither
“efficacy” nor “Q2-ready”; use “protocol and trace-replay pilot.”

## Migration sequence

1. Freeze `q2_ready_report.md` and current artifacts as a dated dossier.
2. Create `paper/imrad_manuscript.md` from the section map above; use
   `DATA_REQUIRED` placeholders instead of invented values.
3. Move R1–R3, P1–P2, the 5+3+2 map, and the Q2 scorecard to supplement/internal
   files.
4. Run the full benchmark and generate one machine-readable result table.
5. Populate Methods and Results from the run manifest; update the abstract and
   conclusion last.
6. Run a claim audit: every number must resolve to a trace, table row, and
   numerator/denominator; every novelty sentence must identify its closest
   prior and differentiating endpoint.
7. Render the manuscript and supplement, inspect references/figures, and run
   the reproducibility command from a clean environment.

## Editorial stop condition

If the full run does not show a meaningful AFER/SMF/BDP improvement, the article
must be submitted as a careful measurement/replication or negative-result paper.
Do not change the primary endpoint or contribution wording after inspecting the
test set.
