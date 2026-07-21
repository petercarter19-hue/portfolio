# PS-JOURNAL-001 — J1.1 Backend Brief: Server-Side Journal Search

**Manager/architect:** Fable. **Implementer:** Sonnet 5. **Reviewer:** Opus.
**Base:** current `origin/main`. **Branch:** `work/2026-07-21-journal-search-j11-impl`.

## Purpose

Close the disclosed J1 deferral: deterministic, owner-authorized, server-side
search over the member's own Moments (`PS-JRN-JRN-006`: search begins with
deterministic structured/full-text owner-authorized retrieval). The accepted
Manage view (doc 13) shows the search field this powers. Flag-gated by the same
`PEERSLATE_JOURNAL_ENABLED` (still false); nothing user-visible changes.

## Scope

### 1. SQL — extend the UNAPPLIED proposed migration in place
`SQL FIles/Migrations/proposed/PS-JOURNAL-001_journal_reads.sql` has never been
applied to any database (confirmed proposed-only), so extend it rather than
adding a second file: add `usp_SearchJournalMomentsForOwner(@UserKey,
@SearchText nvarchar(200), @IncludeArchived bit = 0, @Limit int, @Cursor
nvarchar NULL)`:
- Owner resolved from `@UserKey` first; authorization before retrieval.
- Deterministic predicate: case-insensitive `LIKE` containment over the
  member's own Moment title + narrative (accepted current version only), with
  proper escaping of `%`, `_`, `[` in the input — no dynamic SQL, bound
  parameters only.
- Same keyset pagination + ordering contract as the list proc; same list-shape
  columns; confirmed/active membership rules identical; archived only when
  requested.
- Update `..._rollback.sql` (drop the new proc; same guards) and
  `SQL FIles/Verification/PS-JOURNAL-001_owner_isolation_verify.sql` (two-owner
  search isolation: owner A's search never returns B's rows; wildcard-injection
  attempt returns literal-match behavior; empty/no-match returns empty set, not
  an error; pagination order proven). Keep THROW codes in the 527xx namespace,
  unique vs existing.

### 2. Service
`services/journal_service.py`: add `search_owner_journal(user_key, search_text,
*, include_archived=False, limit=50, cursor=None)` returning the same
`{"items": [...], "next_cursor": ...}` shape; validate/trim `search_text`
(1–200 chars after strip; reject empty with `JournalServiceError("required")`).
Allowlist the new procedure in `services/database_service.py`.

### 3. API
`GET /api/journal/moments?q=<text>` — same endpoint, optional `q` param routes
to search; absent `q` keeps the existing list behavior byte-identical. Same
flag/identity/neutral-404 gates. `q` over 200 chars → 400 member-safe error.

### 4. Tests (all existing green + new)
Extend `tests/test_journal_service.py` / `tests/test_owner_journal.py`:
valid search shape; empty-q rejected at service, listy behavior preserved at
API without `q`; owner isolation (`@UserKey` threaded); wildcard escaping
(`%`, `_` treated literally — assert the escaped parameter reaches the mock);
flag-off/unauth neutral 404 unchanged; over-length `q` → 400.

## Hard boundaries
Do NOT touch: the frontend lane's files (owner_routes.py, templates/, static/),
existing applied procedures, the Moment/list contracts beyond the additive `q`,
CURRENT_BASELINE/Bible/Roadmap, the flag default. No PR. The other Sonnet lane
(`work/2026-07-21-journal-frontend-j1-impl`) is active — if you believe you must
edit a file that lane plausibly owns, STOP and report instead.

## Done + report
Full suite green at your pushed SHA (`ANTHROPIC_API_KEY=test
/Users/petercarter/portfolio/venv/bin/python -m unittest discover -s tests -q`);
push branch; report branch + full SHA, files, exact test result line,
assumptions (especially SQL text-matching semantics and any collation caveat),
self-certification Pass/Conditional/Fail. STOP for Opus review.
