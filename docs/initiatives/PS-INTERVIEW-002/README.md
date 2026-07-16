# PS-INTERVIEW-002 — Interview mode clarity (public-safe slice, 2026-07-16)

## What landed
- **Grounding-mode control** in Interview AI: `Best-practice example |
  Use Pete's history | Compare` (accessible radio group, teal room accent).
- **Server**: `/api/interview/model-answer` accepts `mode`
  (member_history default / best_practice / compare). Best-practice uses
  a generic prompt with no profile history, hard-labeled as illustrative,
  and returns no source ids; compare returns both answers. Follow-ups
  remain grounded in the member context as before.
- **Truth labeling**: generic answers show "Illustrative best-practice
  example — not Pete's real history" and "no personal history used";
  member answers keep the inspectable source list, now titled
  "Relevant history used".
- **v1.2 copy**: "Proof you may have missed" → "Relevant history you may
  have missed"; "approved evidence" → "approved history/sources";
  "model-answer reference" → "best-practice example".
- **Missing-history behavior (pre-auth honest version)**: when the
  approved history cannot support a question, the workspace says there
  is no strong example yet, points to the best-practice mode, and states
  plainly that adding your own history arrives with PeerSlate accounts.

## Deferred to the auth phase (reported, not mocked)
Session/answer/feedback persistence, retrieval-scope records, private
interview-story drafts, voice-answer capture into the Journal, and the
add-missing-history flow — all require sign-in, owner records, and
private storage (v1.1 prerequisites). Nothing was built as a fake shell.

## Verification
Full suite 205 tests OK (3 new: mode control present, generic labeling,
v1.2 language). Existing 40 interview tests unchanged and green.
Checklist: no canonical objects yet (no persistence); AI cannot publish
or write anything; deterministic code controls validation and rate
limits; original answer never overwritten (unchanged behavior).
