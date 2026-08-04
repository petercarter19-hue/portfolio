# Community secondary-state tranche 1 checkpoint — 2026-08-02

## Bounded result

This checkpoint implements only the local, owner-pilot conversation and composing states that follow the approved primary Feed review. It reuses the existing Community Feed template, client, attachment controls, and API shapes; it adds no schema, migration, service, feature-flag, or Voice-runtime change.

## Implemented UI seam

- A conversation opens with the root post, media, full contribution tree, and selected-reply context when a contribution deep link is used.
- A contribution deep link moves keyboard focus and the scroll position to the exact highlighted reply while keeping the full conversation available around it.
- The conversation uses the same compact five-emoji private Respond rail as the approved Feed. The previous large response dialog and its Done/Remove step are absent.
- The persistent reply composer has an auto-growing typed field, compact File and Photo controls, unavailable Voice/Video/Public-audio controls, a triangular send button, and viewer-namespaced local draft keys. Nested targeting respects the existing depth guard.
- The original-post composer exposes File/Photo plus truthful unavailable media controls. A new post requires Public selection, then explicit **Publish publicly** confirmation. An edit remains a separate PATCH path.
- Save and direct-message affordances are not rendered in this bounded conversation state.

## Local review harness

`scripts/preview_community_secondary_states.py` is deliberately separate from the approved primary Feed harness. It uses Pete-only in-memory fixture data, renders the real template/client assets, accepts only local typed replies and private response changes, and explicitly rejects public post creation and file upload. It never calls persistence services.

Run it with the project review Python and open `http://127.0.0.1:5056/the-slate`; a selected-reply route is available at:

`/the-slate/posts/55555555-5555-4555-8555-555555555555/contributions/66666666-6666-4666-8666-000000000003`

## Verification recorded

- 114 focused Community/runtime/XLSX/secondary-state tests passed.
- 184 adjacent navigation, Community/Journal-boundary, and Workshop tests passed; one unrelated fixture test was skipped.
- 10 Community focus-lifecycle behavioral checks passed.
- JavaScript syntax, Python compilation, dependency integrity, and diff whitespace checks passed.
- Real-browser desktop checks covered the compact Respond rail, click-outside conversation dismissal, targeted reply composition/submission, Public selection and the separate public confirmation, and the selected-contribution deep link.
- A 390 × 844 narrow-browser check covered the focused conversation and sticky reply composer without starting mobile-only feature work.

Evidence:

- `evidence/2026-08-02-secondary-tranche-1/community-conversation-selected-1440x1600-dark.png`
- `evidence/2026-08-02-secondary-tranche-1/community-conversation-selected-390x844-dark.png`
- `evidence/2026-08-02-secondary-tranche-1/community-public-confirmation-1440x1600-dark.png`

## Deliberately not started

No Voice permissions, recording, dictation, transcription, audio retention, Blob or Speech integration, SQL/migration work, public publishing activation, full release work, PR, merge, deployment, or feature-flag activation is included. The fixture is not a live or multi-user claim.
