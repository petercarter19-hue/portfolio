# PS-RESUME-PUBLIC-REFINE-001 — Public Résumé Hierarchy and Scan Refinement

## Assignment

- Writer: Claude Code
- Manager/reviewer: ChatGPT Work
- Branch when accepted: `work/YYYY-MM-DD-resume-public-refine`
- Entry gate: PS-BASELINE-001 is squash-merged, its Azure pipeline is green, and this branch is created from the resulting current `origin/main`.
- Canonical public route: `/petec/resume`; existing legacy redirects remain redirects.

## Outcome

Tighten repeated hierarchy and shorten the default public résumé scan through accessible progressive disclosure while preserving the current meaning, source data, résumé capabilities, and Deep Navy Gold foundation. This is refinement, not a replacement or second résumé.

## Acceptance criteria

1. The opening has one clear identity/hierarchy and one dominant next action; repeated positioning/action language is reduced without losing information.
2. The default desktop scan feels approximately 8–9% more compact, principally through spacing, grouping, and collapsed optional depth—not smaller body type or deleted meaning.
3. Skills remain compact and reveal only the two or three strongest approved proof points by default; complete approved evidence remains reachable.
4. Experience and credential depth is available on demand with clear labels, keyboard support, focus handling, and correct `aria-expanded`/hidden state.
5. The Career Constellation, Ask Pete AI, contact action, ATS-friendly résumé/PDF path, canonical URL, and legacy redirects still work.
6. The page renders from the existing server-provided résumé data. No new static dataset, client-side copy of private data, or backend data fork is introduced.
7. Desktop, mobile, 200% zoom, keyboard, visible focus, reduced motion, and no-JavaScript reading order are reviewed.
8. Focused résumé tests, living-résumé fixture/preview tests, Site Rules, governance guardrails, and the full configured suite pass.

## Writable files

- `templates/resume2.html`
- `static/css/resume2.css`
- `static/css/living-resume-v2.css` only for selectors used exclusively by this résumé page
- `static/js/living-resume-v2.js` only for the current résumé interactions
- `templates/partials/career_constellation.html` only if required to preserve its in-page integration
- `tests/test_resume2.py`
- `tests/test_living_resume_preview.py`
- `tests/test_living_resume_fixtures.py`
- package-specific screenshots under `artifacts/ps-resume-public-refine-001/`
- This initiative directory and its completion report

If another file is required, stop and ask the manager to reserve it before editing.

## Read-only and forbidden domains

- Treat `app.py`, route registration, `static/data/resume_data.json`, and `static/data/living_resume_fixtures.json` as read-only unless the manager separately approves a verified content defect.
- Do not touch Interview Studio, Capture, owner templates/styles, authentication, database/service code, migrations, global navigation, base template, shared theme tokens, or deployment configuration.
- Do not expose private member data, create a new résumé dataset, change route meaning, or begin a wholesale brand/navigation redesign.
- Do not use the retired résumé or MICAP examples.

## Required reading

Follow `START_HERE.md`, then the current governance records, Document Control, Bible/Roadmap/Sync Standard, the résumé source documents listed in `AGENTS.md`, [current problem and intent](01_CURRENT_PROBLEM.md), [experience contract](02_EXPERIENCE_CONTRACT.md), [validation plan](03_VALIDATION_PLAN.md), and [implementation sequence](04_IMPLEMENTATION_PLAN.md).

Close with `docs/templates/OWNER_TECHNICAL_COMPLETION_REPORT.md` and the exact branch plus full commit SHA.
