# PS-INTERVIEW-PUBLIC-GATE-001 — Owner-Approved Design Scope

## Decision status

- Owner: Pete Carter
- Decision date: 2026-07-18; dual-theme visual authority updated 2026-07-19
- Designated session manager: Claude Co-Work
- Gate 2.4 review session: Codex manager-review session
- Disposition: Gate A approved for the current public package
- Approved approach: Approach A — preserve interactive public practice and make its boundaries unmistakable
- Implementation authorization: none; this decision authorizes the next design-only step

## Current public product decision

`/interview-studio` remains a genuinely interactive, unauthenticated public experience. The design must preserve:

- written answers and server-side coaching;
- Interview AI best-practice, named public-profile, and compare modes;
- browser-local drafts, goals, completed attempts, and history;
- local camera and microphone rehearsal using browser media APIs;
- existing public routes, deep links, failure behavior, and fallbacks.

The design shall simplify the opening, progressively disclose secondary depth, and explain the real storage, transmission, identity, grounding, and media boundaries. It shall not convert the page into a fictional zero-input tour during this package.

## Approved owner decisions

1. **Current approach:** preserve interactive public practice with explicit truth and privacy labels.
2. **Theme boundary:** the current public route stays light-first Deep Navy Gold.
   Image 5 Concept A controls default/light and Image 5 Concept C controls an
   optional dark expression of the same public Studio. Both themes share one
   semantic DOM, state machine, functionality, truth, and accessibility model.
3. **Demo identity:** retain Pete Carter because the page uses his approved public profile and résumé data. Label it as a public demo profile, never as signed-in identity.
4. **Vocabulary:** use **Interview Me** for member-entered answers, **Interview AI** for model responses, and **Video Practice** for local camera rehearsal.
5. **Worked-example tour:** exclude it from the current implementation. Preserve the concept for the future public demonstration.
6. **Future direction:** after an authenticated private Studio exists, passes privacy/identity verification, and is live, PeerSlate may reconsider converting the public route to the scripted guided-demonstration model. This is approved direction in principle, not automatic implementation authorization.

The exact source path, composition rules, shared component/theme architecture,
nine-screen dual-theme requirement, theme persistence/no-state-loss contract,
and definitive Claude handoff are controlled by
`09_DUAL_THEME_VISUAL_AUTHORITY_AND_CLAUDE_BRIEF.md`. That newer owner decision
supersedes any statement in this file or file `06` that reserves dark styling
exclusively for a future authenticated Studio. It does not authorize product
implementation.

## Verified current facts Fable may rely on

- `/interview-studio` is public and unauthenticated.
- `/interview-studio/history` displays current-browser practice records only.
- `/interview-me`, `/petec/interview-me`, and `/petec/interview-studio` redirect to the canonical public route.
- Pete Carter context is server-rendered public demo-profile data, not authenticated member identity.
- Interview coaching and model-answer endpoints are rate-limited and use the existing public profile/context controls.
- Browser practice state is namespaced in local storage and is not an account-backed history system.
- Camera and microphone streams are handled in the browser. Recorded media is converted to a local object URL for playback; it is not uploaded or analyzed.
- There is no authenticated `/app/interview-studio`, server-backed private practice history, private Interview Story save, or per-member Studio entitlement system today.

## Current design allocation

Design the following current-public states using the real interactive behavior:

1. Public orientation and named demo-profile framing.
2. Focused active written question and answer entry.
3. Truthful processing with the answer preserved.
4. Bottom-line-first review with practice-signal score framing.
5. Interview AI source-mode labels and comparison.
6. Honest Video Practice permission, recording, playback, and text-only fallback.
7. Browser-local History with clear/delete controls and an honest empty state.
8. Processing failure with edit/retry and answer preservation.
9. Camera or microphone denial with a usable written/text fallback.

For each primary journey, include desktop, mobile portrait, mobile landscape, keyboard focus, reduced motion, 200% zoom/reflow, long-answer, and unavailable-state considerations in the editable design source.

## Visual semantics

- Navy `#203767` / strong navy `#132447`: primary actions, headings, active/selected states, and current step.
- Marigold `#B87900`, text-safe `#8A5A00`, soft `#F4E4B4`: highlights, progress, and grounding/source chips.
- Teal `#1E725F`: success and completion only.
- Amber: caution.
- Red: true error or destructive action.
- Current public implementation remains light-first. Do not import the protected owner rail or dark owner shell.

## Required public truth language

The composition may refine the exact wording, but it must preserve these meanings near the relevant action:

- **Public demo profile: Pete Carter — coaching grounded in his public résumé.**
- **Your practice answer:** entered by the visitor and sent to PeerSlate only when submitted for coaching.
- **Best-practice example:** generic and illustrative; it is not Pete's or the visitor's real experience.
- **Grounded in Pete's public profile — demo:** uses only the approved public-profile context supplied to this page.
- **Saved only in this browser:** applies to drafts, goals, completed attempts, and public practice history.
- **Local camera rehearsal:** no recording upload or delivery analysis occurs.
- **Practice signal — not an employer prediction:** applies to any aggregate score.

## Future design bank — not current implementation

Preserve as future authenticated-Studio design material only:

- scripted public guided sample and future sign-in gate;
- authenticated choose-practice and session setup;
- private server-backed sessions and History & Growth;
- private member-history grounding;
- Improve with Coach save workflow;
- Save as Interview Story;
- private job-description context;
- per-member entitlements;
- protected-route denial and stale-account states;
- private media processing or delivery analytics.

These concepts require a separately authorized authenticated-Studio initiative with server-derived identity, authorization-before-retrieval, persistence, lifecycle/data-rights controls, and backend ownership.

## Design exit gate

Fable returns separate full-screen production-intent designs for the current-public allocation, editable responsive source, a component/state inventory, and a short self-review against this file. The Codex Gate 2.4 session records a durable complete-package review, Claude Co-Work confirms it as designated manager, and Pete plus that manager must issue a clean visual sign-off before implementation begins.
