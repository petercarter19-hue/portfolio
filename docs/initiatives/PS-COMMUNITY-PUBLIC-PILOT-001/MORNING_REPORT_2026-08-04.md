# Morning report — 2026-08-04

## The headline

**The independent review failed the package, and it was right to.** It found
fourteen defects in work I built last night, including two that would have
taken the whole site down or silently broken a promise we publish to members.
Twelve are now fixed and proven against a real database. One is not fixed, and
that one is the most interesting thing in this report.

## The two serious ones

**Enabling the Community flag would have returned HTTP 500 on every page,
including the homepage.** Seven new database procedures were never added to the
allowlist. Calling an unknown one raises an error type my "never fail a member
request" handlers were not catching — and because the housekeeping sweep runs
on every request, it took down every route. The reviewer reproduced it.

**The 30-day purge could never have run.** It empties a post's body, but the
existing rules require at least one character, so the erasure would have failed
silently, forever, while the policy page told members their content was being
permanently erased.

Both are fixed. The second is now proven on a real SQL Server: the disposable
proof deletes a post, runs the actual purge over it, and asserts a body-free
tombstone exists — where before it only applied and rolled back migrations and
never ran a purge at all. That gap is why a purge that could never work looked
fine.

> **Update, 07:30.** F5 is now fixed too — see below; the section that follows
> describes the first attempt, which failed usefully. Thirteen of fourteen
> findings are closed, the branch is synced to current `main`, and **PR 268 is
> open and green**. The next step is the first production migration, which
> needs you.

## The one that took two attempts, and why it matters

**A legal hold does not protect attached files.** A hold is supposed to preserve
evidence; it preserves the words and loses the files.

I tried to fix it. The fix meant adding a condition to a procedure owned by one
migration, using columns created by a different one — which SQL Server does not
allow in the natural place — so I restated the procedure in the second
migration, plus a third copy in the rollback.

**The repository rejected it.** Your migrations stamp a fingerprint of every
procedure they own and refuse to re-apply if the definition has changed
underneath them. My restatement changed one, so the check correctly refused.

I could have made the check pass by re-stamping the fingerprint. That would have
defeated a guard that was doing its job, so I reverted instead. The real fix is
to move those columns into the base migration so a single procedure carries the
condition — a deliberate structural change, not a 4am edit to the one migration
the reviewer had verified as sound.

**On your go-ahead I did it the right way instead.** The hold columns moved to
the tables the procedure actually reads, so a single definition carries the
condition — no duplication, no drift test, and the guard has nothing to object
to. A hold now stops attachment cleanup. Proven on a real server.

**One limitation remains and it is real:** cleanup is claimed inside the removal
request, so a hold applied *after* someone removes a post is still too late for
the files. A hold placed before the removal saves everything. Closing that
window means keeping attachments for the full 30 days, which would undo the
retention schedule you approved — so I left it, and it is recorded in the code.

## Everything else

- **Reply drafts never expired.** Two of three draft surfaces were correct; the
  test asserted two surfaces and shipped the third unbounded. Fixed, and the
  test now checks every function that reads a draft rather than a list I
  maintain by hand.
- **The purge would have deleted an unbounded number of revision rows** in one
  transaction, on a sweep that runs inside a member's request. Now scoped to
  the batch.
- **Recently deleted offered restores that could not work** — moderated items,
  and replies whose parent post is still gone. Both removed from the list, and
  a direct attempt now says why instead of falsely reporting success.
- **A legal hold could be attributed to a user id that does not exist.** Now
  validated. I deliberately kept holds on live posts legal, against the
  reviewer's suggestion: holding a post *before* its author deletes it is the
  one sequence where a hold would actually save the files.
- **The policy promised attachment deletion "within an hour"**, backed by a
  worker that only runs when a request arrives. The wording now describes what
  actually happens. Your approved schedule is unchanged — only the sentence.
- **Restore cannot bring back files**, exactly as your approved schedule
  requires. Rather than change the schedule, the recovery screen, the restore
  confirmation and the policy now all say so plainly.
- **The scheduler's comment claimed it never blocks a request.** It blocks the
  one that triggers it. Corrected, and workers now stagger their first sweep so
  a restart does not fire them all at once.
- **PR 263 merged and deployed.** Your database can now be rebuilt from your own
  repository; before this it could not. Production is healthy.

## Where it stands

| | |
|---|---|
| Branch | `codex/2026-08-01-community-primary-feed-sol-ultra`, HEAD `4fdf19d` |
| Pull request | **268, open and green.** Build validation approved, merge status succeeded |
| Base | Synced to current `origin/main` (`a4923f93`) |
| Suite | 2,136 passed, 8 skipped, 1 known Windows-only failure |
| SQL proof | Run 465 **passed** on the merged base, purge included. Leases 647, 651, 656, 660 |
| Production | Healthy. Community flag still off. Nothing is live. |
| Self-certification | **Conditional** — 13 of 14 fixed, F14 documented, not re-reviewed |

## What needs you

1. **The first production migration.** This is the next action and the one real
   risk left. Everything proven so far ran against a throwaway container.
   Merging PR 268 deploys to production — Community stays flag-off, so nothing
   user-facing changes, but the deploy itself is real. I stopped here rather
   than merge on my own.
2. **A re-review of these corrections.** The lean policy says recheck the open
   findings rather than replay the audit, but four of these changed real
   behaviour.
3. **Look at the Recently deleted link.** It sits in the existing policy line
   at the bottom of the feed, owner-only. Public visitors do not see it —
   verified by rendering the page both ways. It has not had your visual
   acceptance.
4. **Confirm the legal-hold limitation is acceptable**, or say the word and I
   will hold attachments for the full 30 days instead.
5. **Ownership scoping before a second member joins the pilot.** One cleanup
   filter relies on the route's owner check rather than the database. Not
   exploitable while you are the only writer.

## Honest note

Both serious defects were mine, written in one long session, and both passed a
fully green 2,000-test suite. The tests I had written checked that the code
*said* the right things — they matched SQL text and mocked the database. They
did not check that it *did* them. The new tests target the wiring and the real
database instead. Tonight also spent three pipeline runs and a reverted change
on a fix that a guard in your own repository was right to reject, which is a
cheaper way to learn that lesson than the alternative.

## Reference

```text
Branch          codex/2026-08-01-community-primary-feed-sol-ultra
HEAD            47e30be
Review          docs/initiatives/PS-COMMUNITY-PUBLIC-PILOT-001/INDEPENDENT_REVIEW_2026-08-04.md
Response        docs/initiatives/PS-COMMUNITY-PUBLIC-PILOT-001/REVIEW_RESPONSE_2026-08-04.md
Proof runs      455 passed (purge executed, lease 647)
                456 failed  forward_idempotency_unexpected
                457 failed  ifm_community_migration_drift_a_protected_procedure_changed
                461 passed (all corrections, lease 651)
Deployed        PR 263 / PS-PLAT-000 only. Community remains flag-off.
```
