# PS-CAPTURE-002 — Security and Privacy Contract

## Authorization invariants

- The server obtains `identity.user_key` from the existing authenticated identity boundary.
- The browser sends only an opaque capture key and expected row version; it never supplies owner/profile/user IDs.
- SQL resolves the owner and filters by owner plus capture key in one operation.
- Foreign, missing, deleted, or inaccessible captures produce the same outward result.
- Authorization is repeated for every action; a prior list response is not authorization.

## Request and concurrency safety

- Reuse the existing same-origin write check for every POST.
- Validate UUID/key, row-version, text length, and non-whitespace content before the database call and again in SQL.
- Reject stale row versions so two tabs cannot silently overwrite lifecycle state.
- Preserve the 8,000 UTF-16-code-unit body limit unless a separate approved migration changes it.
- Never place Capture bodies, revision bodies, exported JSON, or free-form correction notes in logs or audit metadata.

## Privacy invariants

- Visibility remains `private` throughout this package.
- No correction, archive, restore, delete, or export action publishes content or changes audience.
- Export responses are private/no-store and are not persisted server-side.
- Delete removes all stored body text in the Capture aggregate transaction. The remaining audit tombstone is non-content metadata only.
- Error messages and timing-sensitive branches should avoid confirming the existence of another owner’s capture.

## Negative evidence required

- owner A cannot read, correct, archive, restore, delete, or export owner B’s capture;
- forged/malformed keys and missing authentication fail safely;
- cross-site POSTs fail before database mutation;
- stale row versions do not mutate;
- correction does not alter original body, visibility, or create a placement/Moment;
- delete audit metadata contains no content and deleted text no longer appears in list/get/export;
- export never includes internal IDs or another owner’s records.
