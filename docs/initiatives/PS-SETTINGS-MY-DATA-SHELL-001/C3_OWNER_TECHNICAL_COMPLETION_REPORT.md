# C3 owner technical completion report

**Package:** `PS-SETTINGS-ACCOUNT-EXPORT-EXPERIENCE-001`
**Outcome:** The signed-in member's own account-export request, status and
authenticated proxy download, behind a default-off flag.

## What was delivered

Three owner-scoped routes over the merged C1 foundation and C2 assembly, a
route-layer experience service, the storage adapter's only read path, the
member-facing screen, and the Settings change — all behind
`PEERSLATE_ACCOUNT_EXPORT_ENABLED`, default false. Merging changes nothing a
member can reach.

## Base and final SHA

- Base: `3c43269f` (activation merge, PR 789)
- Surface extension: PR 793, merged `8c53b81b`
- Final candidate: recorded in the review receipt

## Changed paths

`owner_routes.py`, `app.py`, `services/account_export_experience_service.py`,
`services/account_export_storage_service.py`, `services/database_service.py`,
`templates/owner_settings.html`, `templates/owner_account_export.html`,
`tests/test_account_export_experience.py`, `tests/test_database_service.py`,
`tests/test_owner_settings.py`, and the two C3 documents. All within the
claim's surfaces, after the extension.

## Tests

- 17 tests in `tests/test_account_export_experience.py`, covering the flag on
  both reads and the write, cross-site refusal, hostile owner fields,
  all-pairs indistinguishability of every unreadable job, the identical
  refusal code path for exists-but-not-yours versus does-not-exist, download
  headers, locator containment across all six download outcomes, a
  hash-mismatch failing closed, and the allowlist's exact contents.
- Full suite locally: **4849 tests, OK, 24 skipped.**
- Everything uses fake cursors and a fake storage adapter. No database or
  container was contacted.

## Review

Protected. Independent privacy/access review required; see the receipt.

## Merge, deployment, schema and live state

Repository merge only. **Not deployed. No schema applied. No container or
worker identity provisioned. Production authority withheld throughout.**

## Honest limitations

1. **Enabling the flag would not produce a working export.** The worker that
   assembles an archive is C2's and runs nowhere yet — no host, no schedule,
   no identity. With the flag on and no worker, a request would sit at
   `queued` indefinitely. C3 is the member's half of the feature only.
2. **No live proof of anything.** Every assertion is against fakes. The
   procedures' real behaviour, the container's real access, and the real
   privacy boundary remain unproven until the eight migrations are applied
   and an end-to-end run happens on a real account.
3. **An export is 12 of 30 domains.** Journal and Projects are excluded by
   the owner's 2026-08-31 decision to ship without them; the screen says so.
   The remaining omissions carry the ledger's own reasons.
4. **Session hint, not authority.** The Settings page remembers the member's
   own job key in the session for convenience. Ownership is re-proved in SQL
   on every read, so the hint cannot widen access, but it is not a substitute
   for a "list my jobs" procedure, which C1 did not ship.

## Next action

Independent review, then merge. After that, the separately gated production
work: apply `PS-SETTINGS-EXPORT-001` and `003`–`009`, provision the private
container and a dedicated worker identity, give the worker somewhere to run,
then deploy and verify live. Each of those needs its own authorization; the
container, identity and schedule create real Azure resources and cost.
