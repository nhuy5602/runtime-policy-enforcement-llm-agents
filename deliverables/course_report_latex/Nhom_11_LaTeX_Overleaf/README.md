# Group 11 Course Report in LaTeX

The report is in English; the presentation slides remain in Vietnamese, as requested. This package follows the Completion track in the supplied rubric. The work order is course report, research article, then Q2 submission readiness.

## Edit on Overleaf

1. Create New Project > Upload Project and upload the source ZIP.
2. In Settings, set Main document to main.tex and Compiler to XeLaTeX.
3. Recompile the report. Overleaf runs BibTeX as needed.
4. Select slides.tex as the main document to compile the 10-slide Vietnamese presentation.
5. Use Share to invite the group. Compilation requires no API key or AgentDojo runtime.

### Error: fontspec requires either XeTeX or LuaTeX

This error occurs when the Overleaf project uses pdfLaTeX. Open Settings, find Compiler, select XeLaTeX, and click Recompile. If needed, use Recompile from scratch in the menu next to the Recompile button. The TeX editor hint in main.tex does not override the project compiler. Apply the same setting when compiling slides.tex.

The included latexmkrc selects XeLaTeX as the latexmk default. It does not replace checking the Overleaf project setting, which can override that default. Do not remove fontspec or change fonts to fix a compiler-selection error.

## Files to edit

| File | Content |
|---|---|
| main.tex | Title, authors, abstract, section order |
| sections/01_problem.tex | Problem, objectives, threat model |
| sections/02_background.tex | Background |
| sections/03_related.tex | Related work |
| sections/04_solution.tex | Solution, authorization, F/M |
| sections/05_evaluation.tex | Implementation, evidence, evaluation plan |
| sections/06_conclusion.tex | Limitations and conclusion |
| references.bib | Bibliography |
| slides.tex | Vietnamese slide content and speaker notes |

Do not edit llncs.cls or splncs04.bst when revising the report. The group can divide sections among members; this package does not assign individual contributions.

## Compile locally

Install TeX Live or MiKTeX with XeLaTeX, BibTeX, and the packages used in main.tex.

    xelatex main.tex
    bibtex main
    xelatex main.tex
    xelatex main.tex
    xelatex slides.tex
    xelatex slides.tex

Or use Tectonic, which runs bibliography and reference passes automatically and downloads dependencies on first use:

    tectonic main.tex
    tectonic slides.tex

TeX Gyre Termes/Heros and Latin Modern Mono provide consistent fonts across operating systems and Overleaf. Sources use UTF-8. Escape LaTeX special characters in prose; add citations with the cite command and sections with the section command. Avoid manual page breaks to correct a single local rendering.

## Template and fidelity

User-supplied template: Template-1-cột.docm, SHA-256 257ec3d1c458f8b8c7438edb35ff3ace39d62bece9aad3009f272782902005bb. The original Word macro document was not modified or executed.

The LaTeX source uses LNCS class 2.26 (25 February 2025) from CTAN, with a one-column layout, title/author/abstract/keyword block, numbered sections, and references. This is a structural conversion, not a pixel-identical Word replica: TeX Gyre Termes replaces Times New Roman, so line breaks and pagination may differ. Sample ORCID/email fields and example disclosures were not attributed to the group.

Class source: https://mirrors.ctan.org/macros/latex/contrib/llncs.zip. See LLNCS-LICENSE.md for CC BY 4.0 and Springer attribution. The class and bibliography style files are unchanged.

## Evidence scope

- The four-cell F/M table is source conformance, not an LLM benchmark.
- The fake provider checks integration; it does not show defense efficacy.
- The 144-test count is recorded for research snapshot e678ea2; it does not cover later research work in progress.
- These checks do not establish ASR, statistical confidence, novelty, or Q2 readiness.
- Group names were taken from the existing course report. Verify names and add course or instructor details only when confirmed.

## Reproduce technical checks if needed

From the research repository, run PowerShell with the pinned environment installed:

    $env:PYTHONUTF8 = "0"
    $env:PYTHONIOENCODING = "utf-8"
    $python = ".\tmp\agentdojo-source\.venv31213\Scripts\python.exe"
    & $python -B -m experiments.agentdojo_file_scope_preflight --output qa\course_source_check.json
    & $python -B -m unittest experiments.test_agentdojo_file_scope_defense -v

The LaTeX ZIP contains report and presentation sources but no experiment runtime. These commands are not needed to compile or edit the report.
