# PS-VOICE-001 Test and Release Plan

## Automated tests

- Client state machine, supported/unsupported format detection, 3-minute limit, 20 MB limit, permission denial, cancel, retry, double-submit prevention, status announcements, and text fallback.
- Owner route authentication, same-origin mutation checks, safe validation errors, no-cache media responses, and neutral cross-owner behavior.
- Service adapters with deterministic fake Blob/Speech clients: success, timeout, malformed result, empty transcript, retry, provider error, storage error, already-absent Blob, and deletion retry.
- SQL migration shape, owner resolution, explicit states, row-version concurrency, idempotent confirmation, preserved raw transcript, source/Capture link, archive/restore, export, deletion pending/finalization, body-free tombstone, and protected rollback guards.
- Two-owner negatives for every voice source, transcription, confirmation, playback, export, delete, retry, and stale-token path.
- No-content-in-log/audit/blob-metadata assertions.
- Existing Capture/Moment/Placement/database/site/governance tests and the complete configured suite.

## Isolated real-resource proof

Before production release, prove with no production/member data:

1. SQL migration apply, verifier, guarded rollback, and reapply on isolated real SQL Server.
2. Private Blob upload/read/delete under a temporary container or account with public access checks.
3. One short synthetic, non-member audio file transcribed through the selected Speech endpoint under an isolated test identity or manager-approved temporary role.
4. Cross-identity denial for Blob and application routes.
5. Infrastructure plan/apply/verify idempotence and exact resource cleanup.

No test evidence may print audio, transcript content, credentials, access tokens, or private storage locators.

## Manager release order

1. Review the exact Codex branch SHA and completion report.
2. Rerun focused tests, governance/Site Rules, complete suite, compile/diff checks, migration plan, and static secret/content scans.
3. Run infrastructure `plan`; inspect exact resources, roles, settings, and cost boundary.
4. Provision/verify production Storage and managed-identity roles without keys.
5. Apply/verify the production SQL migration through the configured secure path.
6. Open Azure PR, squash-merge, and wait for matching Build and Deploy success.
7. Verify public routes are unchanged and protected voice routes fail closed when logged out.
8. Perform a real signed-in owner smoke test: record a harmless phrase, review/edit, save, play/export, archive/restore, delete, and verify audio is gone.
9. Record exact PR, merge SHA, pipeline, resource, migration, and live evidence in the manager closeout.

## Rollback

- Application rollback must leave existing text Capture operational.
- Before any real voice data exists, guarded SQL rollback may remove Voice objects and restore protected procedures only if fingerprints and later-migration checks pass.
- After real voice data exists, rollback must refuse destructive schema removal. Disable the Voice UI/route through a reviewed application rollback while preserving private data and deletion access, then prepare a separate preservation migration.
- Infrastructure is not deleted while any voice source, deletion-pending record, backup, or rollback obligation remains.
