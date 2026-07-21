# PS-JOURNAL-001 — J1 Backend Implementation Brief (image-independent)

**Manager/architect:** Claude Code (Opus), designated by Pete 2026-07-21.
**Implementer:** Sonnet 5. **Reviewer:** Opus. **Base:** `origin/main`.
**Branch:** `work/2026-07-21-journal-backend-j1` (extend it or a child branch).

## Purpose and hard boundary

Build the **image-independent backend foundation** for the one private Journal:
a derived-Journal read and a single idempotent Save Moment path, **flag-off**,
fully unit-tested with the mocked database, exactly like Owner Home and Photo
backends shipped ahead of their UIs.

**DO NOT** in this task:
- create or edit any template, CSS, or JS, or any member-facing screen;
- enable the feature flag anywhere, or change `/app` behavior;
- modify existing capture/Moment/Voice/Photo procedures or their routes;
- apply any migration to a live database;
- touch `CURRENT_BASELINE.yaml`, the Bible, or the Roadmap.

The member-facing Journal and composer screens are gated on accepted visual
authority (the ChatGPT image set) and are a **separate later task**. This task is
the engine underneath them.

## What already exists (audited — build on it, don't rebuild)

- Sources + Moments + Placements live via allowlisted procedures in
  `services/database_service.py` (`usp_CreateCapture`, `usp_GetMomentForOwner`,
  `usp_CreateOrReopenMomentProposal`, `usp_SaveMomentProposal`,
  `usp_ConfirmMoment`, `usp_ListMomentPlacementsForOwner`, Voice/Photo lifecycle,
  etc.). Today the owner flow is a 3-step proposal→save→confirm in
  `owner_routes.py`.
- `services/moment_service.py` validates Moment fields (kinds, precision,
  lengths, utf16 counting). Reuse it.
- `database_service` API: `first_row(proc, params)`, `first_result`,
  `execute_procedure`; params are `("@Name", value)` tuples; only allowlisted
  procedure names run.
- Migration pattern: `SQL Files/Migrations/proposed/*.sql` +
  `*_rollback.sql` + `SQL Files/Verification/*_owner_isolation_verify.sql`.
  (Note the sibling `SQL FIles/` typo-dir is legacy; write to `SQL Files/`.)
- Tests mock the database (no live DB needed); 705 tests currently pass via
  `python -m unittest discover -s tests -q`.
- Legacy `/api/journal/today|history|responses` in `peerslate_api.py` is the OLD
  daily-prompt feature (`usp_GetTodayJournalPromptForUser`,
  `usp_GetUserJournalHistory`, `usp_SaveJournalResponse`). **Do not remove it**;
  the new one-Journal read must use a distinct name/namespace to avoid collision.

## Deliverables

### 1. Proposed SQL — derived Journal read + one-step Save Moment
File: `SQL Files/Migrations/proposed/PS-JOURNAL-001_journal_reads.sql`
(+ `_rollback.sql`, + `SQL Files/Verification/PS-JOURNAL-001_owner_isolation_verify.sql`).

- `usp_ListJournalMomentsForOwner(@UserKey, @IncludeArchived bit=0, @Limit int, @Cursor nvarchar NULL)`:
  returns the owner's Moments by **derived membership** — every eligible saved
  Moment (active lifecycle; archived only when asked) ordered by occurrence/display
  time then key, keyset-paginated. **No `journal_entry` table, no copied body**;
  select from the existing Moment/source tables, filtered by the owner resolved
  from `@UserKey`. Return only fields a list needs (key, kind, title, occurred_on,
  precision, privacy/visibility, source type, lifecycle state, version number).
- `usp_SaveMomentForOwner(@UserKey, @IdempotencyKey, … accepted Moment fields …)`:
  a single idempotent commit that creates one source + one canonical Moment first
  version in one transaction (or documents a compensating sequence), returning the
  moment key + version + a truthful outcome. A repeated `@IdempotencyKey` returns
  the same Moment, never a duplicate. It must NOT publish, place, broaden audience,
  or write any projection. New Moments default to private/Only Me.
- Every statement idempotent/guarded; rollback script reverses only these objects;
  verification script proves cross-owner isolation (owner A cannot read B).
- These are **proposed** scripts (not applied here). Match the style of the
  existing `proposed/PS-MOMENT-001_moments.sql`.

### 2. Service — `services/journal_service.py`
- `class JournalService` with injected `database=database_service`.
- `list_owner_journal(user_key, *, include_archived=False, limit=50, cursor=None)`
  → calls `usp_ListJournalMomentsForOwner`, returns `{"items": [...], "next_cursor": ...}`;
  each item is a plain dict; no cross-owner data; tolerant of empty/None rows.
- `save_moment(user_key, idempotency_key, proposal)` where `proposal` is the dict
  returned by `moment_service.validate_moment_proposal` → calls
  `usp_SaveMomentForOwner`, returns `{"moment_key","version","saved":True}`; raises
  a typed `JournalServiceError(code)` on a false-save / changed / limit condition
  (mirror the `CaptureLifecycleError` pattern). Never report success without a key.
- Module singleton `journal_service = JournalService()`.

### 3. Allowlist + flag
- Add the two new procedure names to the `database_service` allowlist frozenset.
- Add flag `PEERSLATE_JOURNAL_ENABLED` (default **false**) read the same way as the
  existing owner-home/capture flags; document it in `.env.example` with a
  "keep off until the visual gate + migration pass" note.

### 4. API (backend only, flag-gated, no UI)
In `peerslate_api.py` (or a small `journal_api` blueprint if cleaner), owner-only,
identity-resolved, same-origin-guarded like the other member writes:
- `GET /api/journal/moments` → list (flag on: owner's derived Journal; flag off or
  non-owner/unauth: **neutral 404**, leaking nothing).
- `POST /api/journal/moments` → save one Moment via `journal_service.save_moment`
  with a client idempotency key; flag-gated; validation via `moment_service`.
- Authorization **before** retrieval; never fetch-then-filter. No new top-level
  route, no template, no navigation.

### 5. Tests (add; keep all 705 green)
`tests/test_journal_service.py` and `tests/test_owner_journal.py`:
- valid list + save (mocked DB), shapes correct;
- **idempotency**: same key → one Moment, not two;
- **false-save guard**: DB returns no key → service raises, API does not claim saved;
- **derived membership**: absence of any "journal placement" is fine; archived
  excluded by default, included on request;
- **owner isolation**: user A's key never returns user B's rows (mock asserts the
  `@UserKey` param is threaded into every read);
- **flag off** → `/api/journal/moments` GET/POST return neutral 404;
- **unauth / non-owner** → neutral 404, no content, no counts;
- **no journal body**: assert the service/proc contract writes no second content
  table (documented + asserted at the SQL-shape level via the proposed script).

## Contracts to honor (from the locked architecture)
- One private canonical Moment per Save; Journal membership derived; **no Add to
  Journal step**; no second body table.
- Save never publishes/shares/broadens audience; those are later explicit,
  previewed actions (J2). Default Only Me.
- Idempotent save; optimistic concurrency respected; truthful failure.
- Authorization before retrieval; neutral not-found for unauthorized.
- Works with AI/speech unavailable (this layer has no AI dependency — keep it that
  way).

## Definition of done
- `python -m unittest discover -s tests -q` → all green (705 + new).
- New files only as listed; **zero** template/CSS/JS changes; flag default off;
  `/app` and existing routes unchanged (prove with the route/behavior tests).
- Commit with a clear message; push the branch; report branch + full SHA + the
  exact commands/results + a short self-review noting any assumption or follow-up.
- Then STOP for Opus review. Do not open a PR yet.
