# Response to the independent review — PS-COMMUNITY-PUBLIC-PILOT-001

**Writer:** Claude Fable 5 (assigned writer, self-managed lane)
**Review answered:** `INDEPENDENT_REVIEW_2026-08-04.md`, verdict **Fail**, 14 findings
**Reviewed SHA:** `3897f0da25240d331fa00724f95666706c42af81`
**Response SHA:** `a7bc8e65272f11db4fc7ed53ae53ae87b1620fb9`

The review was correct on every finding it raised. Two were P0s that would have
taken the whole site down or silently broken the erasure promise the policy
page publishes. Both are fixed and proven. This document records what changed,
what I deliberately did differently from the recommendation, and what still
needs Pete.

---

## Status by finding

| ID | Sev | Status | Evidence |
|---|---|---|---|
| F1 | P0 | **Fixed, proven** | Allowlist + broad catch; `test_community_retention_wiring.py`; reviewer's scenario reproduced against the fix — `/` and `/the-slate` return 200 |
| F2 | P0 | **Fixed, proven on a real server** | Tombstone-permitting constraints; **SQL proof run 455 executes the purge and asserts a body-free tombstone** |
| F3 | P1 | **Fixed as disclosure** | Recovery screen, restore confirmation, and policy all state files are not recoverable |
| F4 | P1 | **Resolved by F1–F3** | Behaviour now matches the published text; `test_community_policy_states_retention.py` binds wording to code |
| F5 | P1 | **Fixed on the second attempt** | Hold columns moved to the migration that owns the procedure; proof run 464 |
| F6 | P2 | **Fixed** | Reply drafts wrapped and expired; contract test now catches any missed surface automatically |
| F7 | P2 | **Fixed** | Revision deletes scoped to the batch via `OUTPUT` |
| F8 | P2 | **Fixed, with a deliberate deviation** | Operator validated; header corrected; live holds still permitted — reasoning below |
| F9 | P2 | **Fixed as wording** | Policy describes the mechanism instead of an hour it cannot guarantee |
| F10 | P3 | **Fixed** | Rollback refuses while `PS-COMMUNITY-RESTORE-001` is applied |
| F11 | P3 | **Fixed** | Moderated records excluded from the list; distinct `moderated` outcome |
| F12 | P3 | **Fixed** | Replies under a still-removed post are no longer offered |
| F13 | P3 | **Fixed** | Docstring corrected; per-worker startup stagger |
| F14 | P3 | **Documented, not changed** | Reliance recorded below; revisit before a second member |

Full suite after the fixes: **2,088 passed, 8 skipped, 2,426 subtests passed**,
one known Windows-only failure (`test_private_environment_file_has_owner_only_permissions`,
POSIX `chmod`, passes on Linux CI).

---

## Where I did something other than what was recommended

**F8 — I did not reject holds on live records.** The reviewer suggested
rejecting a hold unless the record is already removed. I validated the operator
and corrected the false comment, but kept live holds legal, because that is the
one case where a hold actually saves attachments. F5's real limitation is that
cleanup runs inside the removal request, so a hold applied afterwards is always
too late for the files. A hold placed *before* the author deletes is therefore
the only sequence that preserves them, and rejecting it would remove the
feature's one working path.

**F5 — I tried to fix the half that needs no decision, and the repository
stopped me. It was right to.** Details in the section below; the honest summary
is that a legal hold still does not preserve attachments.

**F9 — I changed the wording, not the schedule.** Pete approved "attachment
files are deleted within an hour of removal". The mechanism deletes them
synchronously inside the removal request, with a best-effort retry behind it.
"Within an hour" was a promise about a clock; the new text is a description of
the mechanism. The approved schedule is untouched.

**F3 — disclosure over deferral, for the same reason.** Changing when
attachments die is a schedule change. Telling members the truth is not.

---

## F5 in full: an attempted fix the repository rejected

This is the one finding I did not close, and the way it failed is worth
recording.

**The attempt.** I added legal-hold predicates to
`usp_ClaimPublicCommunityMediaCleanup` so a held record's attachments would be
skipped by cleanup. That procedure belongs to the base community migration, but
the `legal_hold_*` columns are created by the retention migration, and SQL
Server resolves column references against an already-existing table at
`CREATE PROCEDURE` time — so the predicate cannot be added where the procedure
lives. I restated the procedure in the retention migration instead, plus a third
copy in the rollback (which drops those columns), and wrote a drift test to keep
the three in step.

**The rejection.** Proof run 457 failed at the idempotency stage. The base
community migration stamps a SHA-256 of every procedure it owns into an
extended property and refuses re-application when a definition no longer
matches. My restatement changed that definition, so the second apply correctly
refused.

**Why I reverted rather than routed around it.** The guard is doing exactly what
it should: one migration must not silently redefine another's procedure. I could
have re-stamped the hash from the retention migration, which would have made the
guard pass while defeating its purpose. Three copies of a fifty-line procedure
was already a smell I had flagged in this document before the guard confirmed
it. And the correct fix — moving the `legal_hold_*` columns into the base
migration so its own procedure carries the predicate in one place — is a
migration-ownership change that deserves deliberate design rather than a 4am
edit to the one migration the reviewer verified as sound.

**The second attempt, which worked.** Pete approved proceeding on the reading
that contradicts nothing already signed off: a hold suspends *pending* cleanup,
and the general attachment schedule is unchanged. The fix is ownership rather
than duplication — the `legal_hold_*` columns and their completeness
constraints now live with the tables in the base migration, so its own
procedure carries the predicate in one place. Retention keeps what it actually
owns: the purge marker, the jobs that honour a hold, and the procedure that
sets one, and it now refuses loudly if the base migration ever stops supplying
the columns rather than failing to compile a procedure much later. Its rollback
no longer drops columns it does not own. One definition, no drift test, no
third copy. Proof run 464 passed; run 465 passed again on the merged base.

**The limitation that remains, and it is real.** Cleanup is claimed inside the
removal request, so a hold applied *after* a member removes a post is still too
late for the bytes. A hold placed before the removal preserves everything. That
is recorded in the procedure itself, and a test fails if the note disappears.
Closing that gap means holding attachments for the full 30 days, which
contradicts the schedule Pete approved — still his call, and unchanged by this
fix.

**Diagnosis cost, and what it bought.** Run 456 reported only
`forward_idempotency_unexpected` — "re-applying three files broke somewhere". I
made that stage apply each file separately under the same bounded-message
treatment the first-application stage already used, which turned the next run's
code into `ifm_community_migration_drift_a_protected_procedure_changed`. That
named the cause immediately. The stage runs against the still-empty database, so
it carries the same disclosure reasoning as the stage it borrowed from.

---

## What still needs Pete

1. **F5's residue — must a hold applied *after* removal still save the files?**
   A hold now protects attachments, but only if it precedes the removal.
   Closing the remaining window means holding attachments for the full 30 days,
   which contradicts the retention schedule you approved. Say the word and it
   changes; otherwise the limitation stands as documented.
2. **F14 — ownership scoping before a second member.** The targeted cleanup
   filters rely on the route's owner check rather than SQL-level scoping. Not
   exploitable while the site owner is the only writer. It must be scoped in SQL
   before the pilot admits anyone else.
3. **A re-review of these fixes.** The lean policy says recheck the unresolved
   findings rather than replay the audit, but F1, F2, F5, and F11 changed real
   behaviour.
4. **The first production migration.** Everything proven so far ran against a
   disposable container.

---

## Evidence

```text
Branch          codex/2026-08-01-community-primary-feed-sol-ultra
Response SHA    a7bc8e65272f11db4fc7ed53ae53ae87b1620fb9
Suite           2088 passed, 8 skipped, 2426 subtests, 1 known Windows-only failure
SQL proof       run 455 PROOF_FAILURE_CODE=none_proof_passed (purge executed), lease 647
                run 456 queued on a7bc8e6 to cover the F5-F13 SQL changes
New tests       tests/test_community_media_cleanup_hold.py
                tests/test_community_retention_wiring.py
Changed         PS-COMMUNITY-RETENTION-001_retention.sql (+rollback)
                PS-COMMUNITY-RESTORE-001_restore.sql
                services/community_retention_service.py
                services/community_restore_service.py
                static/js/community-v1.js
                templates/community_pilot_policy.html
                templates/community_recently_deleted.html
                tests/community_draft_expiry.test.js
                tests/test_community_draft_expiry.py
                tests/test_community_policy_states_retention.py
```

**Self-certification: Conditional.** Thirteen of fourteen findings are fixed,
the suite is green on current `origin/main`, the P0s and F5 are proven against a
real database, and nothing is deployed. It is Conditional, not Pass, because
F14 is documented rather than fixed, one F5 limitation is accepted and awaiting
Pete's confirmation, the Recently-deleted entry point has not had visual
acceptance, and these corrections have not been re-reviewed.
