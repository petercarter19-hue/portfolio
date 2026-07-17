# Data model

## `dbo.captures`

| Field | Contract |
| --- | --- |
| `capture_id` | Internal bigint identity primary key |
| `capture_key` | Stable unique UUID for references and audit |
| `owner_profile_id` | Required FK to `member_profiles(profile_id)` |
| `capture_type` | Controlled type; this slice writes `text` only |
| `body` | Canonical captured text, maximum 8,000 characters through the write contract |
| `visibility` | Defaults to and is forced to `private` |
| `status` | Defaults to and is forced to `captured` |
| `active`, `deleted_at_utc` | Lifecycle fields; read contract excludes inactive/deleted rows |
| timestamps, `row_version` | Ordering, update, and concurrency metadata |

The owner/newest index starts with `owner_profile_id`, followed by
`created_at_utc DESC` and `capture_id DESC` for stable ordering.

## Procedure contracts

`usp_CreateCapture(@UserKey nvarchar(300), @CaptureType, @Body)` resolves the
active user and active profile, validates input, inserts one private capture,
appends a metadata-only `capture.created` audit event, and returns the created
row atomically.

`usp_ListCapturesForOwner(@UserKey nvarchar(300), @Take = 50)` resolves the same
owner boundary, clamps the requested count to 1-100, and returns only that
profile's active, non-deleted captures newest first.

No procedure accepts `owner_profile_id` from the caller.

## Rollback

The rollback removes the two procedures, table, and ledger record only when the
table has no member data and no later foreign-key or programmable-object
dependency. A blocked rollback is safer than silent data loss.
