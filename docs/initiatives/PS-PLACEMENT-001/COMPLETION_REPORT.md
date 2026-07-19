# PeerSlate Completion and Handoff Report - PS-PLACEMENT-001

## A. Status

- Package: PS-PLACEMENT-001 - Reference-Only Private Moment Placement Foundation
- Status: Ready for ChatGPT Work manager review. The reference model, owner-scoped procedures, migration/rollback, isolated SQL lifecycle, real lock-wait concurrency proof, and repository gates are complete.
- Branch and commit: `work/2026-07-18-placement-001`; the exact report/handoff commit is supplied with the branch handoff because a commit cannot record its own SHA.
- Base: authoritative Azure DevOps `origin/main` at `4598e8a71f08db475db6906e4a787039d7b3c2ec`. The task branch and current merge-base both use that exact synchronized commit.
- Worktree: `C:\Users\peter\Documents\portfolio-placement-001`.
- PR / pipeline / environment: No PR was opened, and no merge or deployment was attempted. SQL proof used the short-lived Basic Azure SQL database `ps-placement-001-gate-20260718` only.
- Production state: PS-PLACEMENT-001 is not in production. No production SQL was applied or inspected.
- Writer ownership: ChatGPT Codex relinquishes active writer ownership with this committed and pushed handoff. ChatGPT Work owns review and every release gate.

## B. What changed technically

### Reference and lifecycle model

- Added `dbo.moment_placements` as a body-free reference aggregate. It stores only opaque/internal identifiers, owner, exact Moment version, target entity, active/removed lifecycle state, actor IDs, UTC lifecycle timestamps, and SQL `rowversion`.
- Added a unique logical key across owner, Moment, exact Moment version, and destination. One lifecycle row is created once and later reactivated rather than duplicated.
- Added composite foreign keys from placement to the same-owner Moment and same-owner destination, plus an exact `(moment_id, version_number)` foreign key. The migration adds only the minimum `UQ_moments_id_owner` key required for that tenant-safe reference.
- The table has no Capture body, Moment title/narrative/why-it-matters, target content, presentation wording, audience, prompt, AI output, or JSON snapshot column.

### Owner-scoped procedures

- Added `usp_CreateOrReactivateMomentPlacement`, `usp_ListMomentPlacementsForOwner`, and `usp_RemoveMomentPlacement` to the database-service allowlist.
- Every procedure resolves the active owner profile from the server-supplied `app_users.user_key`; callers cannot supply a profile/owner ID.
- Creation locks the Moment, destination, and logical placement range in a consistent order. It requires the exact current Moment row-version, a private confirmed Moment with an existing confirmed version, and a same-owner destination that is active, approved, private, unpublished, and not deleted.
- A confirmed Moment whose source is a body-free deleted-source tombstone remains eligible. A proposal, including a source-deleted proposal, is not eligible.
- Create/reactivate returns deterministic `created`, `existing`, `reactivated`, `stale`, `not_confirmed`, `target_unavailable`, or `not_found` reference-only outcomes. Return values are captured while the transaction lock is held, so a later lifecycle write cannot change the metadata paired with an earlier outcome.
- Remove is explicit and row-version protected. It changes only the placement lifecycle row and returns `removed`, `already_removed`, `stale`, or `not_found`.
- List returns reference/lifecycle metadata and current destination eligibility flags only. It does not join or return Capture text, Moment canonical wording, or destination content.
- Audit events are appended only for real create, reactivate, and remove transitions and contain identifiers/lifecycle metadata only. Idempotent and stale results do not add duplicate success audit events.
- Placement confirmation is not automatic, and Moment confirmation was not changed.

### Migration, rollback, runner, and tests

- Added the versioned forward migration, production-safe two-owner verifier, and guarded rollback.
- The rollback refuses when lifecycle rows exist, a later migration exists, a protected procedure is missing or drifted, a later table/procedure depends on Placement, or a later foreign key consumes the Placement-added Moment-owner key. All refusal checks run before destructive statements.
- A safe rollback removes only the three Placement procedures, `dbo.moment_placements`, the Placement-added Moment-owner key, and the Placement ledger row.
- Registered PS-PLACEMENT-001 as an explicit optional migration and verifier in `scripts/apply_sql_migrations.py`. Plan-only selection opens no database connection.
- Added static contract tests and a gated real-SQL two-connection concurrency test. No route, template, stylesheet, JavaScript, public resume, or Interview Studio file changed.

Changed files are limited to the package allowlist:

- `SQL FIles/Migrations/proposed/PS-PLACEMENT-001_moment_placements.sql`
- `SQL FIles/Migrations/proposed/PS-PLACEMENT-001_moment_placements_rollback.sql`
- `SQL FIles/Verification/PS-PLACEMENT-001_owner_isolation_verify.sql`
- `scripts/apply_sql_migrations.py`
- `services/database_service.py`
- `tests/test_database_service.py`
- `tests/test_placement_migration.py`
- `docs/initiatives/PS-PLACEMENT-001/COMPLETION_REPORT.md`

## C. What this means in plain English

PeerSlate can now remember that one exact, member-confirmed version of a Moment has been deliberately placed in one existing private Slate destination without copying any of the Moment's words. The placement is a durable pointer with its own lifecycle: create it once, remove it explicitly, and reactivate the same pointer later when the source and destination are still eligible.

The Moment remains the canonical source. Placement does not rewrite the Moment, the deleted-source tombstone, the destination, its audience, access grants, publication state, or any downstream room content.

## D. What the website or member can do now

This package adds no website or member-facing control. After the migration is reviewed and applied in an approved environment, an authorized future backend consumer can explicitly create/reactivate, list, or remove private placement references through the stored-procedure boundary.

There is still no UI for placement and no automatic placement during Moment confirmation. Nothing becomes public, shared, rendered in another room, or copied into another domain.

## E. How this connects to PeerSlate

This is the first backend contract for Bible/Roadmap v2.3's "create once, place many" direction. Capture remains private source material; a confirmed Moment remains the exact member-approved canonical story; Placement is now a separate, private, explicit reference from that exact canonical version to an eligible owner-owned Slate destination.

That boundary lets later purpose-specific rooms retrieve canonical content through their own authorized services without duplicating or silently diverging from the Moment. It also preserves the Sync Standard distinction between canonical source records, references, derived projections, and publication decisions.

## F. Verification and validation

### Automated repository gates

- Placement/database/Capture/Moment focused run: 83 tests passed; one real-SQL integration test was skipped by design when its isolated-gate flag was absent. Expected unavailable-storage negative paths logged errors and returned no false success.
- Governance pointers and Site Rules: 17 tests passed.
- Complete suite: 323 tests passed; the same gated real-SQL test was the only skip.
- Changed Python syntax/import compilation passed.
- `git diff --check` passed.
- Migration plan-only selection printed only `PS-PLACEMENT-001_moment_placements.sql` and made no database connection.
- Staged changed-file allowlist, secret-pattern scan, staged diff review, local/remote SHA comparison, and clean-tree verification are recorded in the exact branch handoff.
- UI screenshots are not applicable because this package was required to add no route, template, styling, script, or UI.

### Isolated real SQL Server proof

- Used the empty Basic Azure SQL database `ps-placement-001-gate-20260718` on the existing PeerSlate SQL server; no production/member data was present. Only the empty legacy `dbo.app_users` prerequisite was bootstrapped.
- Applied and verified the eight foundation migrations, PS-CAPTURE-001, PS-CAPTURE-002, PS-MOMENT-001, and PS-PLACEMENT-001 in release order. The Capture and Moment verifiers completed with rollback-only synthetic data before the next package was applied.
- The Placement verifier used two synthetic owners and proved same-owner integrity, cross-owner/forged denial, exact confirmed-version pinning, stale Moment and placement tokens, every prohibited destination state, explicit remove/reactivate, idempotent create, deleted-source confirmed eligibility, deleted-source proposal denial, current target availability, and complete synthetic rollback.
- The independent-connection concurrency test deliberately held the Moment lock before releasing two simultaneous creators. Both creator sessions were observed in `LCK_M_U` waits. After release they completed without deadlock as one `created` and one `existing`, returned the same placement key and row-version, persisted one active row, and wrote one create-success audit event.
- Two simultaneous removers serialized to `removed` plus `stale`. An overlapping remove/reactivate sequence completed without deadlock and ended with one valid active reference.
- Placement/audit/request sentinel occurrences were zero. Relation, access-grant, and publication-version counts for the destination were zero and unchanged. The confirmed private Moment and active/approved/private/unpublished destination remained unchanged.
- Guarded rollback refused with error 52334 while a placement lifecycle row existed, error 52332 while a synthetic later migration existed, and error 52333 after a protected procedure alteration. Placement artifacts remained intact after each refusal.
- After removing test-only blocking state and restoring the protected definition, normal rollback removed only Placement artifacts. Capture, Moment, entity, relation, access, publication, and audit foundations remained present.
- Reapply and final Placement verification passed.
- The exact database resource was validated Online immediately before deletion, deleted, and an Azure server query returned `[]` for that exact name. The temporary database and all remaining synthetic fixtures are gone.
- The first exploratory gate invocation selected all optional migrations together, which ran the older PS-CAPTURE-001 verifier only after PS-CAPTURE-002 had expanded its list result. That orchestration order produced a result-column mismatch. The database was deleted and recreated; the authoritative lifecycle above applied and verified each optional package sequentially, and all gates passed. No production resource or non-allowlisted repository file was involved.

## G. Known gaps, risks, and exclusions

- The branch is not live. ChatGPT Work still owns review, production-migration approval, Azure PR, squash merge, pipeline/deploy verification, and any protected production validation.
- No placement route, UI, destination picker, owner Home/viewer, public projection, or purpose-specific presentation wording exists.
- Placement does not create or modify Journal, Story, Work, Project, resume, Interview Studio, Feed, sharing, matching, voice, media, or AI records.
- Placement does not change audience, access grants, publication versions, destination visibility, or authentication architecture.
- A future consumer must retrieve canonical Moment and destination content through its own authorized domain services; Placement intentionally stores and returns references only.
- Rollback is intentionally blocked once any real placement lifecycle row exists or a later migration/dependency appears. A future rollback in that state requires an explicit data-preservation plan rather than destructive reversal.
- The real-SQL concurrency test is gated and skipped in ordinary local/CI runs unless the exact isolated connection and `PS_PLACEMENT_SQL_GATE=1` are supplied. Its required execution passed against the deleted temporary database.

## H. Clear next step

ChatGPT Work should review the exact pushed branch/SHA, migration and rollback, body-free schema, owner/target integrity, and SQL evidence. If approved, ChatGPT Work owns the Azure PR and production SQL gate. Codex must not open the PR, merge, deploy, or begin a downstream package from this handoff.

## I. What Pete needs to do or decide

None. ChatGPT Work owns the documented manager and release gates. Pete is needed only if review finds a product or data-lifecycle conflict not resolved by the current controlled package.
