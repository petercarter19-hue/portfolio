# PS-FEAT-001 first pass

- **Branch / commits:** `codex/ps-feat-001-living-resume`; `0975800 PS-FEAT-001: add Living Resume preview` (based on `ceba528` preflight).
- **Preview route:** `/_internal/living-resume-v2` — local-only unless `ENABLE_DESIGN_SYSTEM_PREVIEW=1`; current `/resume`, `/petec/resume`, and the PDF path are unchanged.
- **Changed files:** `app.py`, `templates/living_resume_v2.html`, `static/css/living-resume-v2.css`, `static/js/living-resume-v2.js`, `static/data/living_resume_fixtures.json`, and `tests/test_living_resume_preview.py`.

## Implemented

- Generic fixture/view models for student, early-career, mid-career, career-changer, freelancer, and senior-career profiles.
- One dominant Ledger frame with an integrated timeline rail. Selecting a chapter replaces detail inside the same frame.
- Compact native-detail skill proof reveals, accessible without a 3D flip.
- Career Constellation below the Ledger, driven from the selected fixture's same chapter records; a node returns to its Ledger chapter.
- Direction C route-scoped color values, Newsreader/Inter typography, visible focus, and reduced-motion scroll behavior.

## Fixture-only / deferred

- All profile, outcome, skill, and evidence wording is generic fixture content. Nothing saves, publishes, verifies evidence, or performs AI/voice actions.
- Voice transcript, structured proposal, source/visibility review, explicit approval, persistence, public/recruiter routes, and tenant schema require backend work.
- No approved Ledger or Constellation visual assets were available; final visual fidelity remains deferred.

## Validation

- `ANTHROPIC_API_KEY=test-preview-key C:\Users\peter\Documents\portfolio\venv\Scripts\python.exe -m unittest tests.test_living_resume_preview` — passed (2 tests).
- Existing Flask route baseline was already 200 for `/resume` and `/petec/resume`.
- `git diff --check` passed before commit.
- Browser review: desktop route rendered; tab-panel selection and Constellation-to-Ledger linking were inspected. A 390×844 capture was attempted; narrow-view rendering needs a second visual QA pass before review approval.

## Review tomorrow

1. Start the app in this worktree and open `http://127.0.0.1:5051/_internal/living-resume-v2`.
2. Switch among all six fixture profile links.
3. Select timeline chapters, open each skill proof, then use a Constellation node to return to the Ledger.
4. Recheck at 390×844, 1440×900, 200% zoom, and reduced motion after final screenshots are supplied.
