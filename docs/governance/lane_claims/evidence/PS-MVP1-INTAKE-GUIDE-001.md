# PS-MVP1-INTAKE-GUIDE-001 candidate evidence

Runtime-inert post-review record. The required independent exact-SHA review
passed. This file does not change application behavior.

The active Protected claim assigns implementation to sole writer
`session:1f54dff0-ea02-46b9-b097-ae7608178396` (governed transfer from
`session:01a08dfb-7229-75f0-8017-07dd590f1795`, merged as PR 1004, base
`d3968419b15fba4ecfabe00f0494c615a936457e`); repository authority is
`through_merge` and production authority is withheld.

Exact reviewed candidate
`b8e3bc1290f6b779ff2c458260e25f18322af0a2` finishes the unfinished WIP lease
repair `4e09e841780d5b4abd1b49e9f7c4ad7ba953a6be` (nine files, +811/-33) with
two minimum corrections (exact allowlist set 158->159 for the new claim
procedure; strictly truthful stale-claim conflict wording). Owned changes
touch only the claimed Package C surfaces:

- `SQL FIles/Migrations/proposed/PS-RESUME-INTAKE-001_resume_intake.sql`
- `SQL FIles/Migrations/proposed/PS-RESUME-INTAKE-001_resume_intake_rollback.sql`
- `SQL FIles/Verification/PS-RESUME-INTAKE-001_resume_intake_verify.sql`
- `services/database_service.py`
- `services/resume_intake_service.py`
- `services/resume_intake_repository.py`
- `static/js/resume-intake.js`
- `tests/test_resume_intake_service.py`
- `tests/test_resume_intake_sql.py`
- `tests/test_database_service.py`

No D media files are included. Intake SQL stays proposed with gate null and
unapplied.

## Outcome

The bounded composer contract now reserves a durable
owner/request/digest-scoped processing claim
(`usp_ClaimResumeIntakeRecordingForOwner`, `SERIALIZABLE` with
`UPDLOCK,HOLDLOCK`, closed 11-key validation, receipt-first replay/conflict,
full-binding claim check, 5-minute lease with preallocated lease/source keys)
before any provider contact. Only the claim holder calls transcription.
Contenders receive honest `pending` (`recording_pending` vs
`recording_recovery_required`), `idempotency_conflict`, or completed
structural-receipt replay without provider contact. Finalization
(`usp_CommitResumeIntakeCommandForOwner`, 17 keys) binds the same lease,
source, digest, entrance, policy, lifecycle epoch, audio, length, type, and
duration, verifies the live leased claim and owner-state epoch/policy match,
then writes the source, marks the claim `completed`, and stores the receipt in
one transaction. An expired lease records `recovery_required` and never
transfers provider custody; ambiguous finalization leaves the claim pending so
a retry re-checks rather than repeating provider work. The browser renders a
truthful `pending` state with retry gated on recovery.

Preserved accepted fixes: per-recording immutable retry metadata across
intervening recordings; SQL winner-result validation and owner-qualified
hydration; guide stable request identity with original receipt distinct from
current state; Education/Credential required fields; eligible private-draft
Impact parents; partial field preservation; source purge and truthful replay.

## Implementation record

Inherited DeepSeek/Sol work (WIP checkpoint `4e09e84`, prior reviewed
candidate `f0e1fa59` with 143-check prior-candidate evidence and a reported
297 including 16 browser journeys) is preserved and attributed to those
earlier workers; it is not this Cursor repair. This Cursor/Spark 1.3 finish
(worker conversation `1f54dff0-ea02-46b9-b097-ae7608178396`) adopted the
existing worktree, merged current main, passed its own write preflight,
inspected the WIP, and added exactly two corrections in commit `b8e3bc12`.
No paid-provider, model-switch, or hidden-supervisor turns were used. Missing
telemetry is unavailable.

## Verification and independent review

Writer ran 213 focused checks plus 23 subtests
(`test_resume_intake_service`, `test_resume_intake_sql`,
`test_resume_intake_policy`, `test_resume_intake_jobs`,
`test_resume_intake_proposals`, `test_database_service`,
`test_peerslate_api`, `test_resume_draft_service`,
`test_resume_intake_routes`) and 16 Chrome-to-Flask browser journeys
(`test_resume_intake_browser`); all passed. New coverage: shared-store
cross-instance claim prevents provider duplication (in-memory and SQL-shaped
simulator paths, one provider call, pending then replay), expired claim
requires recovery without lease transfer, and SQL-contract lease text
(`pending` + `recovery_required`, no `SET lease_id = NEWID`, finalize binds
all fence fields).

Separate independent reviewer
`agent:cursor-independent-review-fff5fd79-bce4-45c8-8c84-3ce8b419e888`
re-verified the exact pushed candidate `b8e3bc12` clean, confirmed the prior
REVISE blocker H1 resolved with no blocking regression, reran 149 focused
checks plus 17 subtests (all passed), and returned verdict PASS with two
non-blocking advisories requiring no change. The implementer did not issue
its own independent PASS.

Limits: synthetic, in-memory, and simulator-backed SQL-contract evidence
only. Two-connection SQL-engine execution, SQL compilation on a live engine,
and live transcription providers are unproved and withheld as the later
pre-enable step. No production deploy, feature enablement, schema apply, live
identity, D-G backends, full My Data UI, or later package activation. Resume
onboarding retention/limits remain unselected; fixtures are not product
policy.
