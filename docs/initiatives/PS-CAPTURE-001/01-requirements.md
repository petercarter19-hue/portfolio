# Requirements

## Member story

As a signed-in PeerSlate member, I can quickly save a text thought privately
and see my recent captures without exposing it to another member or publishing
it anywhere.

## In scope

- Protected `GET` and `POST /app/capture` routes.
- Text composer with required-body and 8,000-character validation.
- Private, owner-scoped SQL persistence.
- Newest-first recent-capture list and an honest empty state.
- Owner workspace link to Capture.
- Forward migration, guarded rollback, and transactional two-owner isolation
  verification.
- Privacy-safe schema and capture-created audit events.

## Out of scope

- Voice, photo, video, document, or URL capture.
- Journal UI or persistence changes.
- Placement into Project, Story, Work, Resume, or Feed.
- Publication, audience selection, AI enrichment, View As, export, archive,
  correction, or delete UI.
- Changes to `identity.py` or `auth_routes.py`.

## Acceptance criteria

1. Anonymous access redirects to sign-in with `/app/capture` as `return_to`.
2. Server-derived identity is the only owner input; no client owner/profile ID
   is accepted.
3. A valid text body creates one `private` / `captured` record and redirects to
   the capture page.
4. Blank or overlong input creates no record and produces an accessible
   validation message.
5. Recent results contain only the authenticated owner's active, non-deleted
   captures, newest first.
6. Missing/unavailable storage returns a controlled 503 and never reports a
   successful save.
7. No place, publish, Journal, or AI control is represented as working.
8. Focused tests, site guardrails, full suite, SQL verification, desktop/mobile
   review, pipeline, and production checks pass before completion.
