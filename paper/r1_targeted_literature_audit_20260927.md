# R1 targeted literature audit — 27 September 2026

## Status and purpose

**Status: screening completed; R1 remains OPEN.** This is a targeted,
reproducible closest-prior screen for the working candidate *Security Regression
Testing of Indirect Prompt-Injection Defenses under Versioned Agent Tool
Contracts*. It is **not** a systematic review and it does not support a
“first” claim. Its purpose is stricter: prevent the manuscript from claiming a
contribution already demonstrated directly by a close paper, and specify the
conditions under which the candidate must be downgraded to a replication or
case study.

The screen was performed on 27 September 2026. The cut-off is the material
accessible on that date; all papers with a preprint status remain preprints
unless a venue is explicitly stated below.

## Claim test used for screening

A paper would be a **direct overlap** only if the primary evaluation combines
all four properties below in the same experimental condition:

| Code | Required property | What does *not* satisfy it |
|---|---|---|
| P1 | Indirect prompt injection (IPI) delivered through retrieved content or a runtime tool result | Prompt injection in tool metadata/registration, a direct user jailbreak, or a hand-instantiated malicious action |
| P2 | An explicit, paired `v0 -> v1` migration of an agent tool contract | A single static interface, unpaired dynamic tasks, generic tool instability, or an adapter transformation without a versioned comparison |
| P3 | An executing LLM agent that produces the evaluated action | A deterministic reference verifier receiving an already-compromised action |
| P4 | A deterministic, action- or state-grounded harmful-effect oracle | Text-only/judge-only ASR or benign task success alone |

`Yes` below means that the screened source directly evidences the property.
`Partial` means a related but insufficient feature. `No evidence` means that it
was not shown in the cited source passages; it is not an assertion that the
property is impossible in an unpublished artifact.

## Search record

### Sources and method

The screen used primary-source records where possible: arXiv abstract/HTML,
[ACL Anthology](https://aclanthology.org/), and the accessible full text of the
IEEE Access article identified by its DOI. It also inspected the reference
lists and named systems of the closest papers. Search results were screened by
title/abstract first, then by the methods/evaluation passages for the closest
candidates. The source set and its limitation are recorded here so a second
reviewer can replay it rather than trusting an undocumented novelty judgment.

### Reproducible query log

These literal queries were run on 27 September 2026 using the relevant source
index or source-indexed search interface:

1. `"indirect prompt injection" "tool contract" versioned agent`
2. `"indirect prompt injection" "schema drift" LLM agent`
3. `"prompt injection" "schema migration" "LLM agent"`
4. `"prompt injection" "tool contract" versioned agent`
5. `site:aclanthology.org "prompt injection" schema agent`
6. `site:dl.acm.org "prompt injection" "tool contract" agent`
7. `10.1109/ACCESS.2026.3696096`

The search log is intentionally query-level rather than result-count-level:
web indexes change and the audit does not claim exhaustive recall. In
particular, a separate reviewer must replay the queries in arXiv, Crossref/IEEE
Xplore, ACM Digital Library, and ACL Anthology before R1 may be closed.

## Closest-source screening table

| Source | Evidence relevant to the screen | P1 | P2 | P3 | P4 | Disposition |
|---|---|---:|---:|---:|---:|---|
| [InjecAgent (ACL Findings 2024)](https://aclanthology.org/2024.findings-acl.624/) | 1,054 IPI cases for tool-integrated agents; direct-harm and data-exfiltration intentions. | Yes | No evidence | Yes | Partial | Essential IPI benchmark antecedent; no versioned contract comparison. |
| [AgentDyn (arXiv:2602.03117)](https://arxiv.org/html/2602.03117v3) | 60 open-ended tasks and 560 injection cases; it evaluates defenses with ASR/utility. The screened full text has no `version` or `schema` occurrence. | Yes | No evidence | Yes | No evidence | Strong closest benchmark for realistic IPI/utility, but not a tool-contract migration study. |
| [VIGIL (ACL 2026)](https://aclanthology.org/2026.acl-long.443/) | Tool-stream IPI, verify-before-commit, and SIREN with 959 cases; reports ASR and utility. | Yes | No evidence | Yes | Partial | Rules out claiming tool-stream IPI or verify-before-commit itself as new. |
| [Assidiqi et al. (IEEE Access 2026)](https://doi.org/10.1109/ACCESS.2026.3696096) | Controlled schema, policy, and toolset perturbations; evaluates reference-free agents with exact end-state task success. | No evidence | Partial | Yes | No (task-success oracle) | Closest interface-drift work. It does not supply the required IPI carrier or harmful-effect endpoint. |
| [CXI (arXiv:2607.06000)](https://arxiv.org/html/2607.06000v1) | AgentDojo live episodes and exact-effect/invocation authority; source describes policy versions but not a paired `v0 -> v1` migration. | Partial | No evidence | Yes | Yes | Rules out claiming exact-effect authorization or a generic action manifest as new. |
| [CONTINUITY (arXiv:2609.05269)](https://arxiv.org/html/2609.05269v1) | Deterministic cross-layer fault suite with effect ASR and transformations, but every attack begins after the planner is assumed compromised. | No (assumed compromise) | Partial | No | Yes | Rules out claiming generic transformation witnesses, finality permits, or deterministic effect containment as new. |
| [MCPTox (arXiv:2508.14925)](https://arxiv.org/html/2508.14925v1) | 1,312 cases across real MCP servers, explicitly distinguishes tool-*description* poisoning from IPI via tool execution results. | No (metadata) | No evidence | Yes | Partial | Relevant threat family but outside the candidate’s IPI-carrier definition. |
| [ShareLock (arXiv:2606.27027)](https://arxiv.org/html/2606.27027v1) | Multi-tool poisoning distributes payload across tool descriptions during registration; evaluates LLM clients. | No (metadata) | No evidence | Yes | Partial | Relevant MCP supply-chain threat, not a paired IPI contract-migration evaluation. |

The `Partial` marks are deliberately conservative. For example, an exact
database-state score is deterministic but it is not a **harmful-effect** oracle
unless the outcome predicate specifies an unauthorized side effect. Likewise,
a paper that discusses a policy epoch or an alias transformation is not thereby
a matched release-migration experiment.

## R1 decision from this screen

No screened source directly demonstrates **P1+P2+P3+P4 in one paired
experiment**. This is a *negative screening observation*, not evidence that
the candidate is unique. It is sufficient only to keep the candidate eligible
for protocol design. It is not sufficient to promote the title to the
submission manuscript, claim novelty, or use “first”, “unexplored”, or
“unaddressed”.

The most dangerous near-overlaps are distinct and must be named whenever the
candidate is described:

- VIGIL for tool-stream IPI defense and benchmark design;
- Assidiqi et al. for controlled schema/policy/toolset drift;
- CXI and CONTINUITY for exact-effect and cross-layer execution integrity;
- AgentDyn for security–utility evaluation of IPI defenses under dynamic tasks.

If later screening finds a work with all four properties, the project shall
switch to a labelled replication/extension and remove any implied novelty
language. If not, the final contribution must remain an empirical *security
regression measurement* with a transparent closest-prior table—not a new
runtime enforcement primitive.

## Gate needed before R1 can close

R1 can be changed from OPEN to PASS only when an independent reviewer records
all of the following in a dated append-only audit entry:

1. replay of the seven queries in arXiv, Crossref/IEEE Xplore, ACM Digital
   Library, and ACL Anthology, including review of all candidates meeting P1 or
   P2;
2. source URL/DOI, venue status, access date, and P1–P4 decision for every
   included candidate;
3. a conflict check for the four near-overlaps above and any papers citing
   them; and
4. an explicit signed decision: `no direct overlap observed`, `direct overlap
   found`, or `insufficient search coverage`.

Until then, this repository must label the proposed contribution as a
**working candidate** and retain the no-result/no-novelty fallbacks in
`paper/r1_reopening_20260927.md`.

## Bibliographic keys added with this audit

The metadata sources for newly added keys are [AgentDyn](https://arxiv.org/abs/2602.03117),
[MCPTox](https://arxiv.org/abs/2508.14925), and
[ShareLock](https://arxiv.org/abs/2606.27027). Existing keys for the other
screened records are retained in `paper/references.bib`.
