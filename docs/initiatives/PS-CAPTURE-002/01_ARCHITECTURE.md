# PS-CAPTURE-002 — Architecture and Data Contract

## Source and revision model

`dbo.captures` remains the private source aggregate and owner boundary. Its existing `body` is the immutable original input. Add `dbo.capture_revisions` with, at minimum:

- surrogate primary key and parent `capture_id` foreign key;
- monotonically increasing `revision_number` unique within a capture;
- corrected body;
- optional owner-entered correction note;
- correction timestamp and actor/user provenance available through the current identity/audit model;
- a row version if needed for diagnostic evidence, while the parent capture row version is the write-concurrency token.

The current body is the highest revision body, falling back to `dbo.captures.body`. A correction inserts a revision and updates only the parent’s `updated_at_utc`, which advances its `row_version`. It never changes visibility and never creates another product object.

## Lifecycle states

- **Active:** existing `active = 1`, `status = captured`, `deleted_at_utc IS NULL`.
- **Archived:** `active = 0`, `status = archived`, `deleted_at_utc IS NULL`. Restore returns it to active/captured.
- **Deleted:** original capture and revision rows are physically removed after explicit confirmation and ownership/concurrency checks. Audit retains only entity key, action, outcome, counts/status, and timestamps—never body text.

Archive is the reversible safety choice. Delete is irreversible and must be described that way in the protected UI.

## Stored-procedure boundary

Use owner-resolving procedures; proposed names are:

- `dbo.usp_GetCaptureForOwner`
- `dbo.usp_ListCapturesForOwner` updated to return current body, original/current version metadata, row version, and an explicit archived filter
- `dbo.usp_CorrectCapture`
- `dbo.usp_ArchiveCapture`
- `dbo.usp_RestoreCapture`
- `dbo.usp_DeleteCapture`
- `dbo.usp_ExportCaptureForOwner`

Each accepts `@UserKey` plus an opaque `@CaptureKey`. Writes also accept `@ExpectedRowVersion`. Procedures resolve the active user/profile inside SQL, scope the capture in the same predicate, run transactionally, and return a generic not-found/changed result for foreign or missing keys.

## Protected HTTP boundary

Use the existing `/app/capture` experience with focused routes:

- `POST /app/capture/<capture_key>/correct`
- `POST /app/capture/<capture_key>/archive`
- `POST /app/capture/<capture_key>/restore`
- `POST /app/capture/<capture_key>/delete`
- `GET /app/capture/<capture_key>/export`

Keep controls compact inside the protected Capture template. Use POST for state change, same-origin validation, opaque keys, and an expected row-version value. Delete requires a deliberate confirmation control; it must not be a GET or a generic one-click link.

## Export contract

Return UTF-8 JSON with an explicit schema/version label, capture key/type/visibility/status/timestamps, the original text, ordered revisions, current-version designation, and provenance timestamps. Add `Content-Disposition: attachment` plus `Cache-Control: private, no-store`. Do not include internal numeric IDs, user keys, another owner’s data, audit internals, or placement claims.

## Migration and rollback

Create versioned migration `PS-CAPTURE-002` after verifying PS-CAPTURE-001. The rollback must restore the prior list procedure and remove only PS-CAPTURE-002 objects. It must stop rather than silently discard data if revision rows or archived lifecycle state exist. Record apply/rollback in the migration ledger and body-free audit metadata.
