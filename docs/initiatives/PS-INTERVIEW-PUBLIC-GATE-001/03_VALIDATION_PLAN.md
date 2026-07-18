# PS-INTERVIEW-PUBLIC-GATE-001 — Validation Plan

## Automated evidence

Update focused tests before or with implementation to prove:

- `/interview-studio` remains public and legacy aliases still redirect;
- the page visibly identifies the public demonstration and named public-profile grounding;
- generic, public-history, and compare labels remain distinct;
- browser history/goals/drafts are not described as account-backed or private server history;
- submission and camera/media disclosures match the implemented behavior;
- essential labels exist in server-rendered HTML;
- existing written, AI, compare, history, camera, storage-clear, failure, and accessibility behavior remains;
- no owner route, database, Capture/Moment, résumé, global-nav, or shared-theme file enters the diff.

Run at minimum:

- `tests/test_interview_studio.py`
- `tests/test_navigation.py`
- `tests/test_site_rules.py`
- `tests/test_governance_pointers.py`
- the repository's complete discovered test command in a configured environment

## Visual and interaction evidence

Capture named before/after screenshots at 1440×900, 1920×1080, and 390×844 for the default written-practice state, public-history grounding mode, browser-local history, and camera/media disclosure. Show one failure/fallback state when it can be produced without changing external services.

Review keyboard-only use, dialog focus return, live-region announcements, 200% zoom, reduced motion, no-JavaScript truth labels, local-storage unavailable behavior, and camera/microphone denial.

## Boundary evidence

The completion report must state separately:

- what remains browser-local;
- what a submit action sends to PeerSlate;
- which named public profile data can ground an answer;
- what is not account-backed;
- that `/app/interview-studio` is reserved and unimplemented;
- that no Capture, Moment, Journal, résumé, or public record is created.

## Release evidence

After manager review and Azure squash merge, the matching pipeline must be green. Production verification covers `/interview-studio`, `/interview-studio/history`, a legacy redirect, visible public/browser labels, mode switching, typed submission, API failure handling, media fallback, and mobile width. Real account-private history is not part of this package and must not be claimed.
