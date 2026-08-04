# Production migration, 2026-08-04

## Outcome: production verifies clean

Pete re-ran the foundation set. **All three failures below are resolved and both
verifications now pass against production:**

```text
Verified all eight migration records and all platform, career, and identity tables.
Verified tenant constraints, private profile defaults, and opt-in discovery defaults.
Verified Community public reads, bounded shelf traversal, selected contribution
authorization, structural tombstones, revocation-safe Feed boundaries, two-owner
write isolation, media cleanup, and rollback.
```

The third line is the cross-owner isolation proof that the first run never
reached. It has now run against production: two synthetic owners provisioned,
isolation exercised, synthetic data rolled back.

**A prediction in this document was wrong and is left standing below as
written.** It said findings 2 and 3 would survive the fix because nothing in
that command addressed them. In fact re-running the foundation set also re-ran
the `PS-PLAT-002` and `PS-PLAT-004` backfills, which seeded the missing
`member_profiles` and `connection_preferences` rows for users created since the
originals. The backfills are idempotent and corrective, not merely inert. The
analysis of *why* the rows were missing still holds — no application code
creates them, so the drift will return as soon as another user is created, and
the follow-up package below is still needed.

---

## What was true of production before that fix

**The three Community migrations are applied and committed.** The runner
printed `Applied …` for each of `PS-COMMUNITY-PUBLIC-PILOT-001`,
`PS-COMMUNITY-RETENTION-001`, and `PS-COMMUNITY-RESTORE-001`. This is real
state. It is also inert: the tables are empty, the feature flag is off, and no
deployed code path reaches them.

**The foundation verification that runs afterwards failed**, with three
findings. None is caused by the Community migrations and none blocks Community.
The run raised before reaching `verify_community`, so the two-synthetic-owner
cross-owner isolation check **has not run against production yet**.

---

## Finding 1 — the ledger is missing PS-PLAT-000. This one is mine.

`FAILED: Migration ledger is missing required foundation records: PS-PLAT-000.`

PR 263 merged the `PS-PLAT-000` file and the pipeline deployed the application.
That was reported as "PS-PLAT-000 is on main, the database can now be rebuilt
from the repository." **That was wrong in a way that matters:** merging a
migration file is not applying it. Production's `schema_migrations` has no
`PS-PLAT-000` row because nobody ran it there.

Nothing is broken by this. `dbo.app_users` already exists in production — the
whole point of PS-PLAT-000, which is a no-op plus one ledger row on a database
that already has the table. The verifier is telling the truth about a gap.

**The fix, and why it is now safe.** The only supported way to add a foundation
migration is `--apply` with no `--migration`, which re-runs all nine. The
runbook warns against that, and the warning was earned: this repository's
disposable SQL proof re-applied the *Community* migrations only, so nothing
established that a foundation migration is safe to run twice. That gap is now
closed — the idempotency stage re-applies every migration, foundation included,
each on its own. **Run 475 passed with that in place.**

---

## Findings 2 and 3 — pre-existing drift, not today's work

```text
FAILED: Not every application user has exactly one member profile.
FAILED: One or more members do not have discovery disabled by default.
```

| Check | Compares |
|---|---|
| member profile | `COUNT(dbo.member_profiles)` vs `COUNT(dbo.app_users)` |
| discovery | `COUNT(dbo.connection_preferences WHERE discovery_opt_in = 0)` vs `COUNT(dbo.app_users)` |

**Root cause: no application code creates either row.** Across the repository,
`member_profiles` and `connection_preferences` appear only in migrations,
verification scripts, and tests — never in application code. They were populated
once, by the `PS-PLAT-002` and `PS-PLAT-004` backfills. Any `app_users` row
created after those migrations ran has neither, so these strict-equality checks
drift the moment anyone new signs in.

**Not an active privacy problem.** Discovery is not implemented; nothing reads
`connection_preferences`, so a missing row cannot expose anyone. The honest
description is that the foundation verification asserts an invariant the
application does not maintain.

**Do not fix it by relaxing the check.** The check is right; user creation does
not seed the rows. The fix is a one-time backfill plus seeding both rows
wherever `app_users` rows are created — its own package, and not a Community
blocker.

---

## Production availability check, same day

Reported as "site is down". It was not, on the server side:

```text
https://peerslate.com/            200, ~0.35s, title renders, three consecutive samples
https://peerslate.com/the-slate   200, ~0.35s
https://peerslate.com/petec       200 after redirect to /petec/resume
https://pete.peerslate.com/       200, valid TLS, redirects to /petec/resume
App Service peerslate-pete        Running
Recent main pipeline runs         all succeeded
```

**One address genuinely fails: `www.peerslate.com` returns NXDOMAIN.** It has no
DNS record and is not bound as a custom domain on the App Service, which has
only `peerslate.com`, `pete.peerslate.com`, and the default `azurewebsites.net`
hostname. Anyone reaching the site through `www.` sees a failure that looks
exactly like an outage. Adding it needs a DNS record at the registrar first,
then a hostname binding — an owner action, not an assistant one.

---

## What is left, and who can do it

Two actions remain and **both are blocked for the assistant session** by the
permission guard, which covers production database writes and PR completion.

**1. ~~Add the PS-PLAT-000 ledger row.~~ Done.** Run 475 proved re-applying the
foundation set was safe; Pete ran it and both verifications now pass.

**2. Complete PR 268.** Squash merge, delete source branch. Build validation
approved, merge status `succeeded`. Easiest from the Azure DevOps web UI. This
is the only remaining blocker, and it is blocked for the assistant session.

**3. Still outstanding after that:**

- Confirm the pipeline succeeds and production is healthy after the merge.
- **The flag stays off.** Turning Community on is a separate decision and should
  follow a clean verification, not precede it.
- A re-review of the fourteen review corrections.
- The member-profile / discovery backfill, as its own package.
- Decide whether `www.peerslate.com` should exist.

---

## Evidence

```text
Branch          codex/2026-08-01-community-primary-feed-sol-ultra
Pull request    268 — NOT merged; the only remaining blocker
Applied to prod PS-COMMUNITY-PUBLIC-PILOT-001, -RETENTION-001, -RESTORE-001,
                plus the re-applied foundation set including PS-PLAT-000
Verification    foundation PASS, Community PASS, both against production
Proof runs      465 passed (merged base), 475 passed (foundation idempotency)
Leases          647, 651, 656, 660, 673
Flag            PEERSLATE_COMMUNITY_PUBLIC_PILOT_ENABLED remains false
```
