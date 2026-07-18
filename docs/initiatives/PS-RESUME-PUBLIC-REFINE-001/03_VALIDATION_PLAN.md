# PS-RESUME-PUBLIC-REFINE-001 — Validation Plan

## Automated evidence

Update focused tests before or with the implementation to prove:

- one canonical public résumé and unchanged redirect behavior;
- the same server-provided data and no second dataset;
- required impact, skills, experience, credentials, constellation, AI, contact, and résumé/PDF affordances remain;
- default disclosure state is intentional and full details remain reachable;
- toggle controls and panels have stable IDs and correct accessibility attributes;
- multiple fixtures render without hardcoded Pete-specific counts/assumptions;
- JavaScript supports keyboard/focus/status behavior and reduced motion;
- no Interview Studio, backend, auth, or Capture files enter the diff.

Run at minimum:

- `tests/test_resume2.py`
- `tests/test_living_resume_preview.py`
- `tests/test_living_resume_fixtures.py`
- `tests/test_site_rules.py`
- `tests/test_governance_pointers.py`
- the repository’s complete discovered test command in a configured environment

## Visual and interaction evidence

Capture named before/after screenshots at 1440×900, 1920×1080, and 390×844. Include opening, default scan, one expanded experience chapter, skills evidence, credentials, and constellation. Record the measured or clearly explained basis for the 8–9% perceived-compression judgment.

Review keyboard-only navigation, focus restoration, 200% zoom, reduced motion, no-JavaScript reading order, and obvious access to the traditional résumé/PDF.

## Release evidence

The Azure pipeline must be green. After deployment, verify `/petec/resume`, the legacy redirect, key assets, AI-open interaction, disclosures, PDF link, and mobile rendering. Visual screenshots are review evidence; they do not replace route, accessibility, or test proof.
