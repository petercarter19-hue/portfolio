# Community — session continuation handoff, 2026-08-04

Written so a fresh Claude Code session resumes exactly here without re-reading
a very long conversation. **This is a session continuation, not a writer
handoff:** Claude Code remains the sole active writer for
`PS-COMMUNITY-PUBLIC-PILOT-001`. Ownership is not relinquished to another
agent, and the frozen `pscf` worktree and Codex Mac worktree stay frozen.

## Handoff block

```text
PeerSlate handoff

Source of truth: origin (Azure DevOps)
Branch: codex/2026-08-01-community-primary-feed-sol-ultra
HEAD: 3897f0da25240d331fa00724f95666706c42af81
Base: origin/main — 0 behind at time of writing
Worktree: C:\Users\peter\Documents\portfolio-community-continuation-001
          (detached HEAD; the branch NAME is held by the frozen pscf worktree,
           so push with an explicit refspec — see "How to push" below)
Working tree: clean
Pushed to Azure: yes
Tests/checks: full suite 2062 passed, 8 skipped, 1 known Windows-only failure
              (test_private_environment_file_has_owner_only_permissions —
               POSIX chmod; passes on Linux CI)
Visual authority/status: Pete gave visual acceptance of the rendered feed on
              2026-08-04 ("This looks fantastic")
Production status: NOT deployed. Flag PEERSLATE_COMMUNITY_PUBLIC_PILOT_ENABLED
              is FALSE in production. Nothing in this package is live.
Next action: process the independent review findings (see below)
Active writer relinquished: no
Self-certification: Pass for the work completed; release gates still open
```

## How to push from this worktree

The branch name is checked out by the frozen `pscf` worktree, so this one runs
detached. Always push with the explicit refspec:

```bash
git push origin HEAD:refs/heads/codex/2026-08-01-community-primary-feed-sol-ultra
```

## What is DONE

- **Disposable SQL proof passes.** Definition 2, runs 422, 424, 429 and 439.
  Retention leases 614/616/622/631 protect them to 2036. Every run confirmed
  exact job-owned cleanup.
- **Two real product defects found and fixed** by that proof:
  `PS-PLAT-000` (dbo.app_users was created by no migration — the database
  could not be rebuilt from the repo) and a `SAVE TRANSACTION` name exceeding
  SQL Server's 32-character limit, which failed the whole Community migration.
- **Retention approved and implemented.** Pete approved the schedule
  2026-08-03 exactly as proposed, live for this release wave, with a recorded
  commitment to readdress it when Community moves behind the sign-in
  experience. `PS-COMMUNITY-RETENTION-001` implements it; a request-cadence
  scheduler runs it.
- **Restore window.** `PS-COMMUNITY-RESTORE-001` turns the 30-day purge delay
  into author-recoverable time, plus the `/the-slate/recently-deleted` screen.
- **Old Community archived** behind the same flag: `/the-slate/my-slate`,
  `/daily`, `/pulse`, `/break` redirect to the new feed when the pilot is on,
  and are untouched while it is off.
- **All six retention evidence items complete**, including production
  configuration evidence and the dated public policy.

## What is OPEN

1. **Independent review** — launched 2026-08-04 against SHA `3897f0d`. Its
   report lands at `INDEPENDENT_REVIEW_2026-08-04.md` in this folder. Process
   its findings first; correct on this same branch and recheck only the
   unresolved items, per the lean delivery policy.
2. **Candidate run** — package gate 7: the exact source SHA must pass
   Candidate Build/Deploy/Smoke/Stop.
3. **Release sequence** — migrate production with the flag off, squash-merge
   through Azure, verify the pipeline, then enable the flag, then verify live
   signed-out and signed-in behaviour. Record a Conditional Gate Launch result,
   not a broad launch.
4. **No entry point to Recently deleted.** The page works and is reachable by
   URL, but nothing links to it. Pete has not yet said where it belongs.
5. **The first real production migration is still unproven.** Everything so far
   ran against a disposable container. Treat the first real Azure SQL migration
   as its own careful step with Pete present, not a line buried in a release
   sequence.

## Separate open PR

**PR 263** — `PS-PLAT-000`, on branch `work/2026-08-04-plat-000-app-users-base`
(worktree `C:\Users\peter\Documents\portfolio-plat-000`). Deliberately split
out of this package because it fixes a platform-wide disaster-recovery gap and
should not wait on a Community release. Additive only, no-op on production,
1781 tests passing. Safe to merge independently.

## Traps that cost time in this session — do not repeat

- **PowerShell `Set-Content -Encoding utf8` writes a UTF-8 BOM.** SQL Server
  rejects it as a syntax error. Use
  `[System.IO.File]::WriteAllText($p,$t,(New-Object System.Text.UTF8Encoding($false)))`.
  A guardrail now asserts no SQL file carries a BOM.
- **`mssql-python` speaks ODBC and silently discards unknown keywords.**
  `Initial Catalog`, `User ID`, `Password` and `Connection Timeout` all
  normalize to None. Use `Database=`, `UID=`, `PWD=`, and pass the login
  timeout to `connect(timeout=)`.
- **This driver never surfaces SQL error numbers in its message text.** Do not
  match on a number like `"52490"`; match the declared guard message instead.
  That mistake made a *correct* rollback refusal look like a failure.
- **`strftime('%-d')` is POSIX-only** and raises on Windows. Format dates in
  Python without platform-specific directives.
- **Merging main into this branch conflicts in `app.py` every time**, always
  additively — Community vs Opportunity Slate vs Workshop config, blueprint
  registration, rate-limit blocks. Resolution is always KEEP BOTH SIDES.
- **`sqlfluff` with `dialect: tsql` parses these files locally** and found the
  BOM instantly. Try a local parser before spending CI runs.
- **The proof's sealed failure code is echoed to the build log** by the seal
  step, because downloading a PipelineArtifact needs a PAT this machine does
  not have. Read it with
  `az devops invoke --area build --resource logs`.

## How to look at it

A fixture-only preview needs no database:

```bash
venv/Scripts/python.exe scripts/preview_community_primary_feed.py
```

Then `/the-slate`, `/the-slate/recently-deleted`, `/the-slate/public-pilot`.
It is labelled "Local fixture preview" on the page so it can never be mistaken
for live data.
