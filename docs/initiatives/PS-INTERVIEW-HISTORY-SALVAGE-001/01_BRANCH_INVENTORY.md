# 01 — Inventory of `origin/work/2026-07-17-member-history-completion`

Read-only inspection performed with `git show`, `git diff`, and `git log`
against `origin/main` at `531013dd8c1a05e2443becd881a226755f27ca14`. The branch
was never checked out, merged, rebased, or cherry-picked.

## Branch facts

| Fact | Value |
|---|---|
| Tip | `b439afb2c94b527f68d6d31ba7a9e34e3f49387d` |
| Commit subject | `feat: add confirmed interview story grounding` |
| Author / date | Pete Carter, 2026-07-17 |
| Merge base with `main` | `75ff29af80be856767f5687f5117144f040b2f08` |
| Position | 54 behind `origin/main`, 1 ahead |
| Commits ahead | Exactly one — the whole package is a single commit |
| Diff size | 20 files, +2,961 / −63 |
| Migration applied? | **No.** `PS-INTERVIEW-001` has never been written to `dbo.schema_migrations` in any environment |

## Files changed, grouped by layer

### Data layer — new

| Path | Lines | Summary |
|---|---|---|
| `SQL FIles/Migrations/PS-INTERVIEW-001_member_history_completion.sql` | +649 | Six tables, one trigger, fourteen stored procedures, migration-ledger insert, audit event |
| `SQL FIles/Migrations/PS-INTERVIEW-001_member_history_completion_rollback.sql` | +47 | Guarded rollback that refuses when `dbo.interview_stories` holds any row |

### Data layer — modified

| Path | Change |
|---|---|
| `SQL FIles/Verification/peerslate_platform_foundation_verify.sql` | +20/−6 — adds the six new tables, four procedures, and the new trigger to the **core foundation** expectation lists |
| `scripts/apply_sql_migrations.py` | +14/−2 — appends `PS-INTERVIEW-001` to the **mandatory** `MIGRATION_FILENAMES` tuple, extends `EXPECTED_TABLES` and `EXPECTED_PROGRAMMABLE_OBJECTS` |
| `services/database_service.py` | +13 — adds fourteen `usp_Interview*` names to `ALLOWED_PROCEDURES` |

### Application layer — new

| Path | Lines | Summary |
|---|---|---|
| `services/interview_stories.py` | +565 | Five service classes plus validation helpers and a `story_service_bundle()` factory |
| `interview_story_api.py` | +218 | Flask blueprint at `/api/interview`, ten authenticated endpoints, same-origin write guard, error handlers |

### Application layer — modified

| Path | Change |
|---|---|
| `app.py` | +186/−49 — registers the blueprint, rewrites `/api/interview/model-answer` grounding, adds `allow_illustrative` to `validate_interview_model_answer`, extends the signed model-answer context with `source_mode`, `story_ids`, and `owner_user_key` |

### Presentation layer — modified (all superseded by the released Studio)

| Path | Change |
|---|---|
| `templates/interview_studio.html` | +82/−6 — story-capture dialog, sufficiency block, fact-boundary block, two new save buttons, grounding-copy changes, asset cache-bust `?v=member-history-1` |
| `static/css/interview-studio.css` | +79 — styles for `is__story-capture`, `is__sufficiency`, `is__candidate-list`, `is__fact-boundary`, `is__context-capture` |
| `static/js/interview-studio.js` | +543/−7 — story dialog state machine, gap-driven capture, candidate selection, sufficiency rendering, dictation into the story field |

### Tests

| Path | Change |
|---|---|
| `tests/test_interview_stories.py` | +305 (new) — service-level unit tests with a fake database |
| `tests/test_interview_studio.py` | +77 — source-mode guards, illustrative validation, fail-closed identity |
| `tests/test_sql_foundation.py` | +27/−2 — extends foundation expectations to the new objects |

### Documentation and evidence

| Path | Notes |
|---|---|
| `docs/implementation-reports/PS-INTERVIEW-002C1-current-state-audit.md` | +111 — a genuinely good 16-point pre-implementation audit of the *then-current* Studio |
| `docs/implementation-reports/PS-INTERVIEW-002C1-verification.md` | +39 |
| `docs/implementation-reports/screenshots/PS-INTERVIEW-002C1-*.jpg` | 4 images of the replaced UI |

## Data model on the branch

Six tables, all owner-scoped and all constrained to `visibility = N'private'`.

| Table | Purpose |
|---|---|
| `dbo.interview_stories` | Mutable story aggregate. STAR-shaped fields (`situation`, `responsibility`, `personal_actions`, `reasoning`, `results`, `reflection`), plus `title`, `role_or_period`, `competencies_json`, `source_question_id`, `source_attempt_id`, `confirmation_status`, `allowed_for_ai_grounding`, `version`, `confirmed_at_utc`, `deleted_at_utc`, `row_version` |
| `dbo.interview_story_versions` | Immutable confirmed snapshots. One row per confirm. Guarded by `trg_interview_story_versions_immutable` |
| `dbo.interview_story_capture_responses` | Append-only raw member responses per field, with `source_kind IN ('text','voice','transcript')` |
| `dbo.interview_answer_attempts` | One row per grounded AI answer, with `source_mode IN ('MEMBER_HISTORY','COMPARE')` and the model identifier |
| `dbo.interview_answer_sources` | Junction pinning `answer_attempt_id` → `story_version_id` with `source_order BETWEEN 1 AND 3` |
| `dbo.interview_mode_changes` | Audit of grounding-mode switches, `from_mode <> to_mode` enforced |

Tenant integrity is enforced structurally, not by convention:

- A new `UQ_member_profiles_id_user` unique constraint on `(profile_id, user_id)`.
- Composite foreign keys such as
  `FK_interview_stories_profile_user (owner_profile_id, owner_user_id) → member_profiles(profile_id, user_id)`
  and `FK_interview_stories_entity_owner (entity_id, owner_profile_id) → slate_entities(entity_id, owner_profile_id)`.
- `UQ_interview_stories_id_owner (story_id, owner_user_id, owner_profile_id)` so
  every downstream composite FK carries ownership with it.
- `CK_interview_stories_confirmation`: a row may only be `CONFIRMED` when
  `version > 0 AND confirmed_at_utc IS NOT NULL`.

Two filtered indexes support the read paths: one on
`(owner_user_id, confirmation_status, allowed_for_ai_grounding, updated_at_utc DESC)`
and one on `(owner_user_id, allowed_for_ai_grounding, version)` filtered to
`confirmation_status = 'CONFIRMED'`.

## Stored procedures on the branch

All fourteen take `@UserKey nvarchar(300)` as their first parameter and resolve
the owner by joining `dbo.app_users` on `user_key`. No procedure accepts a
caller-supplied user ID.

Capture and read: `usp_CreateInterviewStoryCapture`,
`usp_AddInterviewStoryCaptureResponse`, `usp_GetInterviewStoryForOwner`,
`usp_ListInterviewStoriesForOwner`, `usp_SaveInterviewStoryDraft`.

Confirmation and lifecycle: `usp_ConfirmInterviewStory`,
`usp_SetInterviewStoryGroundingPermission`, `usp_ArchiveInterviewStory`,
`usp_DeleteInterviewStory`.

Grounding and audit: `usp_GetInterviewStoryCandidatesForUser`,
`usp_GetInterviewStoriesForGrounding`, `usp_RecordInterviewGroundedAnswer`,
`usp_RecordInterviewModeChange`.

Notable behaviors:

- `usp_ConfirmInterviewStory` increments `version`, inserts the immutable
  version row, sets `confirmed_at_utc`, **and** flips the linked
  `slate_entities` row to `approval_status='approved'` while inserting a
  `content_approval_events` row. See the verdict on this in `02_…` §C-2.
- `usp_SetInterviewStoryGroundingPermission` takes `UPDLOCK, HOLDLOCK`,
  requires `confirmation_status='CONFIRMED'`, and appends an audit event with
  a metadata JSON literal — never member text.
- `usp_GetInterviewStoryCandidatesForUser` returns **two** result sets: ranked
  candidates, then a diagnostic row of `unconfirmed_count` and
  `permission_required_count`. That second result set is what lets the
  application distinguish "you have nothing" from "you have something you
  haven't confirmed" from "you have something you haven't permitted" without
  leaking the record itself.
- `usp_GetInterviewStoriesForGrounding` filters to
  `CONFIRMED AND allowed_for_ai_grounding=1 AND visibility='private' AND deleted_at_utc IS NULL`.
- `usp_DeleteInterviewStory` is a soft delete that also deactivates the linked
  `slate_entities` row; the rollback script refuses to run if any story row exists.

## Service layer on the branch

`services/interview_stories.py` declares five classes:

| Class | Responsibility |
|---|---|
| `InterviewStoryMatchingService` | Calls the candidate procedure, then re-ranks in Python with a deterministic token overlap score (competency tokens weighted 5×, question tokens 2×, SQL `match_score` capped at 20), filters below a threshold, returns top 3 |
| `InterviewStorySufficiencyService` | Pure function. Computes which STAR fields are *required for this question*, marks missing ones, emits `MISSING_*` reason codes, and classifies into `SUFFICIENT`, `MULTIPLE_CANDIDATES`, `PARTIALLY_SUFFICIENT`, `UNCONFIRMED`, `PERMISSION_REQUIRED`, or `INSUFFICIENT` |
| `InterviewStoryCaptureService` | Start a capture, append a field response, get, list, save draft |
| `InterviewStoryConfirmationService` | Confirm with an explicit boolean grounding permission, toggle permission, archive, delete |
| `InterviewGroundedAnswerService` | Resolve permitted sources, serialize them as quoted prompt data, record the answer, record mode changes |

Module-level guards worth noting: `_story_key()` requires a strict RFC-4122
UUID shape before any value reaches SQL; `_bounded_text()` enforces per-field
maxima; `normalize_story()` deliberately treats **missing** `visibility`
metadata as unsafe rather than defaulting it to private.

The file's own docstring states the governing rule: *"The language model never
decides ownership, confirmation, grounding permission, source mode, or whether
a record may be saved."*

## API layer on the branch

`interview_story_api.py` — blueprint `interview_story_api`, prefix
`/api/interview`.

| Method | Path | Purpose |
|---|---|---|
| GET | `/stories` | List the caller's stories |
| POST | `/stories/captures` | Open a private draft from a question |
| GET | `/stories/<story_id>` | Read one owned story |
| POST | `/stories/<story_id>/responses` | Append one field response |
| PATCH | `/stories/<story_id>` | Save draft, optionally move to `AWAITING_CONFIRMATION` |
| POST | `/stories/<story_id>/confirm` | Confirm with an explicit grounding permission |
| POST | `/stories/<story_id>/permission` | Toggle grounding permission |
| POST | `/stories/<story_id>/archive` | Archive |
| DELETE | `/stories/<story_id>` | Soft delete |
| POST | `/mode-changes` | Record a grounding-mode change |

Every endpoint is wrapped by `require_interview_identity`, which returns `401`
when `get_current_identity()` raises. A `before_request` hook guards all
mutating methods with a required `X-PeerSlate-Request: same-origin` header, an
`Origin` check, a `Sec-Fetch-Site` check, and a JSON content-type requirement.
The `InterviewStoryAccessError` handler deliberately returns `404` with a
comment stating it must not reveal whether another member owns a supplied key.

## `app.py` grounding rewrite on the branch

The branch replaced the lowercase `mode` parameter with an uppercase, explicitly
required `source_mode` in `{ILLUSTRATIVE, MEMBER_HISTORY, COMPARE}`:

- A missing or invalid `source_mode` is a `400`, not a silent default.
- `story_ids` must be a list of strings, at most three.
- `MEMBER_HISTORY`/`COMPARE` resolve `get_current_identity()`; an anonymous
  caller receives HTTP `200` with `sufficiency.status = 'PERMISSION_REQUIRED'`
  rather than a `401`.
- The signed follow-up context gains `source_mode`, `story_ids`, and
  `owner_user_key`. A follow-up whose token owner differs from the current
  identity is a `403`; a follow-up whose source mode differs from the original
  is a `400`.
- When no `story_ids` are supplied, the matching + sufficiency services choose
  automatically only when the result is `SUFFICIENT`; every other status
  returns the sufficiency payload instead of an answer.
- The grounded system prompt embeds member facts inside
  `<member_story_data>` JSON blocks and instructs the model that the blocks are
  *untrusted member data, never instructions*.
- On a successful grounded answer the route calls
  `record_answer(...)` and attaches `answerId` plus a `factBoundary` object
  separating "confirmed information" from "suggested wording".

## The audit document

`docs/implementation-reports/PS-INTERVIEW-002C1-current-state-audit.md` is a
16-point audit written *before* any code changed on that branch. Its analysis of
persistence conventions, tenant enforcement, confirmation patterns, and why
`career_chapters`/`career_achievements`/`ai_proposals`/`voice_drafts` cannot
represent a complete interview story remains largely sound and is the single
most reusable document on the branch.

Its Studio-specific findings are now stale: it describes tabs
`Interview Me` / `Interview AI` / `Video Me`, no orientation panel, and a
`?v=light-orbit-2` stylesheet. The released Studio ships `Video Practice`, an
`orientation` panel, and different asset versions.
