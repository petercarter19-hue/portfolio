# PS-MOMENT-001 — Security, Privacy, and Trust Contract

## Identity and authorization

- Derive `UserKey` only from the authenticated server session.
- Treat Moment keys, Capture keys, revision keys, row-version values, and form fields as untrusted selectors, not proof of ownership.
- Resolve owner profile, source Capture/version, Moment aggregate, and write eligibility inside owner-scoped SQL.
- Foreign, missing, discarded, source-deleted, and stale records use the same outward not-found/changed behavior where distinction would leak another owner's state.
- Use POST plus the existing same-origin protection for create/save/confirm/discard.

## Private-by-default state

- Every proposal and confirmed Moment created here has private visibility.
- Client input cannot set public, connection, selected, placement, Journal, Story, résumé, Work, Project, Feed, or Interview Studio destinations.
- Confirmation changes canonical review status only. It does not broaden audience or trigger any downstream write.
- Application code and SQL—not AI—own status, visibility, ownership, confirmation, deletion propagation, and audit decisions.

## Source and proposal separation

- Display the pinned source as read-only and label it as original or correction revision.
- Display proposed canonical fields separately and label them as editable/private until confirmed.
- Never overwrite the Capture original or revision from the Moment flow.
- Never treat an AI/deterministic proposal as member-confirmed truth.
- Audit metadata must not contain source text, proposed narrative, correction notes, or other body content.

## Deletion propagation

Capture deletion must remain explicit and transactional. Before source rows disappear, Moment relationships are updated to a body-free source-deleted state under the same transaction or an equally safe deterministic procedure contract.

- Unconfirmed proposals with no surviving source cannot be confirmed.
- Confirmed Moments may retain only the member-approved canonical content and body-free tombstone provenance.
- No source text, revision text, or correction note is copied into tombstone/audit records.
- Cross-owner deletion can never update another owner's Moment relationships.

## Validation and concurrency

- Enforce server and SQL length/state validation for every proposed field.
- Use optimistic concurrency so old tabs cannot overwrite newer proposal versions or confirm a stale version.
- Duplicate create/submit behavior must be idempotent or return a safe existing proposal rather than creating parallel canonical candidates for the same source version.
- Logs may contain opaque keys, action, result, duration, and body-free counts; never member text.

## Failure behavior

Database unavailable, source changed/deleted, invalid input, stale version, duplicate confirmation, and unknown key states must fail without partial writes or false success. The protected UI explains the recoverable next action without revealing another owner's record.
