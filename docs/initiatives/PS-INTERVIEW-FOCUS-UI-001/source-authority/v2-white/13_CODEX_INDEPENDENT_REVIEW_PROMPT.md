# 13 — Ready-to-Paste Codex Independent Review Prompt

Use this in a separate Codex review task after implementation is complete and before owner approval. The reviewer should not be the same agent/thread that wrote the change when an independent review lane is available.

---

Independently review the implementation of `PS-INTERVIEW-FOCUS-UI-001` against the current repository, the complete initiative package, and the implementation diff. Do not modify code during the first pass.

Read the initiative in order, open all fourteen PNGs at 100%, and inspect the actual runtime states. Treat current released behavior and tests as functional authority; treat `visual-authority/` as composition/hierarchy authority; treat the written specification as authority for responsive, failure, permission, and accessibility states not fully visible in the PNGs.

Audit these areas skeptically:

1. **Scope containment** — no backend, endpoint, request/response, AI prompt/rubric/score, database, authentication, authorization, Azure, route, storage-semantic, or unrelated global-shell change.
2. **Typing-first input** — the textarea is immediately obvious and canonical; optional dictation never displaces, clears, gates, or obscures typing.
3. **State continuity** — current question and complete answer remain visible/preserved through drafting, dictation, submission, processing, review, improve, retry, advance, failure, permission denial, reload, and drawer use.
4. **Progressive disclosure** — inactive future panels are neither visible nor exposed to assistive technology.
5. **White visual authority** — pure white canvas, white primary surfaces, cool-gray support surfaces, navy text, cobalt interaction emphasis, and restrained teal status accents; no beige/ivory/gold fallback.
6. **Responsive behavior** — desktop rail yields before the main stage becomes cramped; mobile uses one column, drawers/sheets, safe-area-aware action dock, and no keyboard/content overlap.
7. **Theme parity** — light/dark share DOM, actions, content order, state, and responsive behavior.
8. **Accessibility** — logical headings, real controls, persistent textarea label, visible focus, live-region restraint, focus restoration, reduced motion, 200% reflow, 320px stress case, and touch targets.
9. **Truth boundaries** — browser-local drafts/history remain clear; no account-backed sync, media upload, employer prediction, publication, or private-profile implication.
10. **Regression risk** — no duplicate event handlers, duplicate state sources, hidden focusable controls, lost keyboard shortcut, broken deep link, broken back/forward, or neighboring-page CSS leak.

Run or verify the required tests and compare screenshots at all specified viewports. Use image overlays or pixel/geometry comparison where practical, but do not fail an implementation for harmless rendering differences that improve accessibility or preserve real content.

Return:

- verdict: `Approve`, `Approve with required corrections`, or `Reject`;
- blocking findings first, each with severity, evidence, affected file/state, and exact correction;
- nonblocking polish findings separately;
- requirement-to-evidence matrix;
- confirmation of exact visual-authority count and palette;
- confirmation that no merge or deployment was performed by the review.

Do not soften findings because the implementation is visually close. A preserved product contract and a dependable state model are more important than superficial screenshot similarity.

---
