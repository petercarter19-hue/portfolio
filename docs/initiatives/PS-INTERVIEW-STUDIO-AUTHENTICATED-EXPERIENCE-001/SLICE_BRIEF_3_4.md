# Slice 3-4 Implementation Brief — Authenticated Shell + Consequence Stack

Same writer rules as SLICE_BRIEF_1_2.md. Visual authority: the 19 hash-locked images in
`C:\Users\peter\iCloudDrive\PeerSlate Architect Handoffs\2026-08-11\Interview Studio Claude
Architecture Handoff 2026-08-11\02_VISUAL_AUTHORITY\FINAL\` — study every one before writing
markup/CSS. Composition/hierarchy/causal flow/state truth are binding; you may adapt spacing,
wrapping, focus, semantics for accessibility, but a material composition change is a STOP (report
back, do not improvise). Architecture files 03 and 06 govern. CSS is now in scope
(static/css/interview-studio.css); base.html and dictation.js remain out of scope.

## Slice 3 — authenticated shell (flag-selected)

The template gains a flag-selected authenticated composition; the current public markup remains
the flag-off branch (Jinja conditional on a single context boolean, e.g.
`interview_authenticated`). Shared partials/ids may be reused where identical; do not fork IDs the
JS needs unless both branches keep them.

1. **Retire in the authenticated branch**: the Studio-local header bar `.is__bar` (template
   :43-115) including "Public practice · browser-local" and all "Public demo profile" chrome; the
   card-style mode nav in the header; every per-panel RIGHT side column (`aside.is__side-column`);
   the four-item truth strip's public claims; every "You are not signed in as {{first_name}}"
   demo card; the noscript public copy (rewrite for authenticated truth); the orientation panel.
2. **Left rail** (visuals 01-12, 15-17): one `aside` under the global header containing, in order:
   INTERVIEW STUDIO mode nav (Interview Me / Interview AI / Video Practice — the current tablist
   semantics and `data-is-mode` hooks move here); CURRENT SESSION (setup summary items + Change
   setup — reuse the existing setup form/dialog machinery); SESSION TOOLS (History, New session,
   Finish session→`Session finished` completed state per visual 11); the browser-truth footer with
   the EXACT copy: "Drafts and History stay in this browser for this account. They do not sync
   across devices." Rail is sticky on desktop, collapses per architecture 03 §6 below the rail
   breakpoint.
3. **Mobile control row** (visuals 13/14): `Interview Me ▾ / Session / History` compact controls;
   NO permanent rail; NO fixed bottom composer dock (retire the :2894-2917 fixed dock in the
   authenticated composition — actions flow in-document per visual 13); keyboard/caret must never
   be covered.
4. **Material**: new scoped token layer for the authenticated composition per the locked warm
   palette (warm ivory/white surfaces, ink navy serif display headings — Newsreader is already
   loaded, forest green primary actions, sage/warm-gray support, restrained antique gold section
   labels/eyebrows, muted red ONLY destructive/error). Scope tokens under the authenticated root
   class so the public flag-off page keeps Smoked Eucalyptus untouched. Do NOT author new
   `body[data-theme="dark"]` rules; do NOT delete existing dark rules. Status meaning always
   text/icon/position + color.
5. **Truth copy swap** (authenticated branch, exact strings): transmission "Your answer is sent
   only when you click Review My Answer." / "Your revised answer is sent only when you click
   Review Revised Answer."; clearing consequence "Clearing browser data may remove these practice
   records."; member authority "Coaching is guidance. Your answer remains yours."; media "This
   recording exists only on this page. PeerSlate does not upload, save, or analyze it."
6. **One document scroll**: in the authenticated composition remove `min-height: 100svh`
   full-viewport forcing and any fixed-height stage behavior; `overflow: clip` on `.main-content`
   may stay (it clips, it does not scroll) unless it fights reveal-on-append — verify.

## Slice 4 — the Interview Me consequence stack (authenticated branch)

Architecture 03 §1-2 is the contract. Key mechanics:

1. **Append-only workspace**: restructure the authenticated Interview Me flow so each attempt
   renders as an appended block: AnswerCard (editable → frozen snapshot) → PendingRow/FailureRow
   (the only replace-in-place transients) → CoachingSection (appended after full validation) →
   ImprovementSection → revision AttemptBlock → RevisedCoachingSection. The current
   `renderReview`-into-fixed-slots path (:1819-1872) remains for flag-off; the authenticated path
   builds appended sections (template `<template>` elements are fine). One scroll; on append,
   reveal+focus the new heading (existing scrollIntoView/focus idiom :1974-1975).
2. **Structural immutability**: on submit, freeze the editor value into a static snapshot element
   with "Submitted answer" label (visual 02); the editor is REMOVED from that attempt (not
   readOnly-toggled). Failure re-attaches the editor with the preserved value ("Review
   unavailable", "We couldn't review this answer right now. Your answer is still here." — visual
   03). After a consequence exists its trigger renders as a completed non-interactive chip
   ("Improvement draft created", "Answer reviewed" — visuals 05/04b); never an active action.
3. **Coaching composition** (visuals 04a/04b/14a): COACHING REVIEW header sentence; COACHING
   SUMMARY three columns WHAT'S WORKING / STRENGTHEN IT / TRY THIS NEXT; STRONGER APPROACH;
   DETAILED COACHING five-dimension table (family-specific keys, existing data); RELEVANT
   EVIDENCE line ("No authorized evidence suggestion is available for this answer." when empty);
   FINAL ACTIONS (Improve My Answer primary, Next question secondary); the member-authority truth
   line. Map from the existing validated review fields (verdict/encouragement/whatCameThroughClearly/
   strengths/improvements/strongerApproach/focusedFollowUp/dimensions) — server contract unchanged.
4. **Marker contract** (visuals 05/14b): improve response renders the editable coach-assisted
   draft with `[bracketed prompts]`; add `confirmations` to the improve response server-side
   (app.py `validate_interview_improvement` :3473-3492 extended: extract bracketed spans from the
   draft into a `confirmations` list; never invent facts — prompt already forbids; strengthen the
   improve system prompt :3770-3780 to instruct bracketed placeholders for unsupported facts).
   Client: "Needs your confirmation" chip, count-down as markers are resolved, exact helper copy
   "Replace or remove every bracketed prompt before review.", `Review Revised Answer` disabled
   until zero markers. Server: the revised-review request (an ordinary review call with
   attempt>1… add `attempt` awareness ONLY client-side) — server-side validation rejects an
   answer containing `[` … `]` marker patterns when flag on? NO — too broad (members may use
   brackets legitimately). Instead: reject only exact-match surviving `confirmations` strings —
   client sends `resolved_markers_of` nothing; simplest server enforcement: improve stores nothing,
   so re-validation is client-side + the visual disabled state; document this bound honestly in
   SLICE_NOTES (architecture 03 §2 wanted server re-validation — implement as: review endpoint
   optionally receives `unresolved_markers` count? Decision: implement server check as
   "reject when the submitted answer still contains any exact `[...]` span that appeared in the
   improve draft's confirmations for the same question+attempt" is stateless-impossible; so the
   server rejects any answer containing a `[bracketed prompt]` matching the exact bracket-sentence
   PATTERNS the improve prompt emits (imperative placeholder sentences inside square brackets,
   e.g. starts with a verb like Describe/Add/Include). Keep it narrow, test both directions:
   a legit answer containing "[sic]" or "M[1-9]" passes; a surviving "[Describe the decision you
   personally made and why.]" fails 400.)
5. **Revised coaching** (visual 06): "Original answer and first coaching remain above." context
   line; immutable `Reviewed revision · Attempt 2` snapshot; REVISED COACHING with WHAT CHANGED /
   WHAT STILL NEEDS WORK / NEXT FOCUS; actions Next question (primary) / Revise again / Finish
   session / `Revision reviewed` completed chip.
6. **Request binding**: widen the epoch guards to compare (sessionId, contextId, questionId,
   attemptNumber, epoch) — the values already exist in `session`; a late response with ANY element
   changed is dropped (extend :1922/:1977/:2088-style guards).
7. **Session Complete rail state**: `Finish session` → completed `Session finished` (visual 11)
   plus the session-stored truth line "This session is stored only in this browser for this
   account."
8. **Tests**: full state-walk assertions on the authenticated composition (hidden/appended
   structure markers, immutability — editor absent after submit, completed chips, marker gate
   both directions, binding-drop per element, exact truth strings). Rewrite the superseded
   public-layout pins ONLY where they block; keep every score-free/validator test green untouched.

Definition of done: both compositions render (flag on/off), all suites green, SLICE_NOTES updated,
no push.
