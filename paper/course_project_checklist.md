# Course-project completion checklist

This is the fallback delivery tier for the same research direction:

**Security Regression Testing of Indirect Prompt-Injection Defenses under
Versioned Agent Tool Contracts**

It is not a substitute for the live-evidence gates required for a Q2+
submission. Every unexecuted result must be labelled as planned, simulated,
source-calibrated, or `not_run`.

| Requirement from the course brief | Canonical project output | Status on October 7, 2026 |
|---|---|---|
| What problem is solved? | `paper/research_protocol.md` and the current claim in `README.md` | Defined; keep the paired `v0 -> v1` regression question primary |
| Check feasibility of the new proposal | `paper/literature_update_20261002.md`, source-only oracle checks, v2 dry-run, and the local fake-provider bridge test | Local capture feasibility established; billable Runpod pilot is pending |
| Detailed research outline | `paper/research_protocol.md` and `ROADMAP.md` | Present; needs one canonical IMRaD report |
| Find and synthesize related literature | `paper/related_work_matrix.md`, `paper/r1_targeted_literature_audit_20260927.md`, `paper/literature_update_20261002.md` | Present as a bounded synthesis; not yet a closed systematic review |
| Detailed background knowledge | `paper/research_protocol.md` and selected archival sections of `paper/manuscript.md` | Present; migrate only the active thesis into the canonical report |
| Detail part of the proposed solution | `experiments/agentdojo_paired_v2_execution_manifest.py`, `experiments/agentdojo_paired_v2_result_bundle.py`, `experiments/agentdojo_paired_v2_driver.py` | Present as a pinned manifest, acceptance contract, and dry-run orchestration seam |
| Detail implementation/evaluation plan | `paper/research_protocol.md`, `ROADMAP.md`, v2 manifest, driver, and capture bridge | Present; fair baselines and multi-model evaluation remain open |
| Write the report in the required format | `paper/imrad_manuscript.md` | Draft created; results remain explicitly `not_run` until live evidence exists |
| Prepare the presentation | `deliverables/course_presentation_security_regression.pptx` | 8-slide editable deck created from the canonical manuscript |

## Minimum acceptance package

The course-tier package is complete when the repository contains:

1. one canonical IMRaD manuscript aligned with the current claim;
2. one reproducible dry-run or pilot result bundle with a fixed denominator;
3. one explicit limitations and claim-boundary section;
4. one presentation deck whose sections map to this table; and
5. a short command sequence that recreates the report artifacts without
   network access.

The research tier remains open until the pinned AgentDojo driver produces
provenance-valid `v0` and `v1` observations, the result bundle scores them
independently, and the literature/statistical/reproducibility gates pass.
