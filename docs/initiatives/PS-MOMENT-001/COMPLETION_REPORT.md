# PeerSlate Completion and Handoff Report - PS-MOMENT-001

## A. Status

- Package: PS-MOMENT-001 - Controlled Private Capture-to-Moment Convergence
- Status: Ready for ChatGPT Work re-review. The manager-required source-row serialization correction, hardened rollback, isolated two-connection SQL proof, complete SQL lifecycle, responsive protected-UI proof, focused regressions, Site Rules, governance guardrails, and complete suite are complete. Production SQL, Azure PR/merge, deployment, and real-member validation remain manager-owned release gates.
- Branch and commit: `work/2026-07-18-moment-001`; manager review started from exact handoff HEAD `4e390cc659b8e9c1d8cf99bceb7dc6da6b783c90`. The exact rework report/handoff commit is supplied with the branch handoff because a commit cannot record its own SHA.
- Base: authoritative Azure DevOps `origin/main` at `158a2ae9b7a0a88a02e8fb0a30e2ed9bcce9926e`. Fetch and pipeline checks confirmed that exact required baseline before the task branch was created.
- PR / pipeline / environment: No PR was created and no merge or deploy was attempted. Work used the isolated worktree at `C:\Users\peter\Documents\portfolio-moment-001` and a short-lived empty Basic Azure SQL database named `ps-moment-001-gate-20260718`.
- Production state: PS-CAPTURE-001 and PS-CAPTURE-002 remain the deployed source boundary. PS-MOMENT-001 application and schema changes are not in production. No production SQL was applied.
- Writer ownership: ChatGPT Codex relinquishes active writer ownership with this committed and pushed handoff. ChatGPT Work owns review and all release-gate decisions.

## B. What changed technically

### Data and state model

- Added `dbo.moments` as the private owner-scoped aggregate. Its state is limited to `proposal` or `confirmed`; visibility is constrained to `private`; the row carries the current proposal version, the confirmed version, confirmation actor/time, and a SQL row-version concurrency token.
- Added `dbo.moment_versions` for immutable proposed canonical field versions. It stores the member-facing Moment type, title, date and date precision, narrative, and optional why-it-matters field. Confirmation pins one exact version rather than copying mutable current fields into another surface.
- Added `dbo.moment_sources` as a one-to-one source relationship that pins the exact Capture and exact Capture revision by internal IDs, opaque keys, and revision number. The relationship intentionally has no source-body or source-note column.
- A Capture correction creates a later Capture revision only. `usp_GetMomentForOwner` reads source text from the pinned revision and reports the latest available source revision separately, so a correction can be detected but never silently rewrites a proposal or confirmed Moment.
- Capture deletion now changes linked Moment sources to `deleted`, records a deletion timestamp, nulls deleted Capture/revision IDs, and preserves only opaque source keys plus revision number before the Capture aggregate and its bodies are deleted. This is the body-free tombstone boundary.
- An unconfirmed proposal whose source is deleted cannot be saved or confirmed. A previously confirmed Moment keeps only the exact member-approved canonical version while reporting that its source was deleted.

### Owner-scoped SQL contracts

- Added `usp_CreateOrReopenMomentProposal`, `usp_GetMomentForOwner`, `usp_SaveMomentProposal`, `usp_ConfirmMoment`, and `usp_DiscardMomentProposal` to the database-service allowlist.
- Every procedure resolves the active owner profile from the server-supplied `app_users.user_key`. Browser-supplied user/profile identifiers are never accepted.
- Creation is idempotent for one owner plus one exact source revision. Read, save, confirm, and discard predicates include the resolved owner. Foreign, forged, missing, or discarded records produce the same outward not-found/changed shape.
- Save requires the current Moment row-version token and creates a new immutable private proposal version. Confirm requires the current row-version token, the exact current proposal version, valid required fields, an available source, and a deliberate member action. Stale tokens or stale proposal versions are rejected.
- SQL validates the same allowed types, date precisions, required fields, and UTF-16 length limits as the Flask service. Confirmation records the confirming owner and UTC timestamp.
- Manager review identified a serialization defect in the reviewed handoff: save and confirmation locked the Moment row but read the joined source relationship without a lock, leaving an unsafe window in which Capture deletion could tombstone that source after the availability decision. Both `usp_SaveMomentProposal` and `usp_ConfirmMoment` now join the exact `dbo.moment_sources` row with `UPDLOCK, HOLDLOCK` while checking `source_state`. Their source decision and Capture deletion's tombstone update are therefore mutually serialized through transaction completion.
- None of the procedures inserts or updates Slate entities, publication versions, access grants, relations, Journal records, placements, profiles, resumes, Story, Work, Projects, Feed, or Interview Studio.

### Protected HTTP and service boundary

- Added a deterministic `moment_service` validator for allowed Moment kinds, required fields, date precision/date parsing, and SQL-compatible UTF-16 length limits.
- Added protected routes to create/reopen a proposal from an exact Capture revision, review one private Moment, save a private proposal version, explicitly confirm it, and explicitly discard an unconfirmed proposal.
- All writes are POST-only, same-origin checked, UUID validated, concurrency-token validated, and owner-derived from the trusted identity boundary. No hidden owner or visibility input is rendered.
- Capture now exposes a minimal `Review as a Moment` control for the immutable original or current correction revision. Archived Capture content does not expose the entry control.
- The new review template presents the pinned Capture source in a labeled read-only region and the proposed canonical fields in a separate editable region. Confirmation is disabled until the stored current version is valid and source-accessible; it also requires a checkbox.
- Confirmed Moments render member-approved canonical fields read-only. A deleted source renders a body-free tombstone, not the deleted Capture text.
- The surface includes an explicit boundary statement and no publish, placement, audience, sharing, Journal, resume, or other downstream controls. Only Moment-specific selectors were added to the existing protected owner stylesheet; global navigation/theme and public surfaces were not changed.

### Migration, rollback, and verification

- Registered PS-MOMENT-001 as an explicit optional migration and verifier in `scripts/apply_sql_migrations.py`; plan-only mode does not open a database connection.
- The forward migration is transactional, requires PS-CAPTURE-002, records its migration ledger row, creates the three tables and five procedures, and replaces Capture deletion only to add deterministic source tombstoning.
- The forward migration records a SHA-256 definition fingerprint as an extended property on each of the six protected Moment/Capture procedures. The rollback refuses to run if any Moment data exists, if an unknown later dependency references a Moment table, if a migration ledger entry is newer than PS-MOMENT-001, or if a protected procedure is missing or no longer matches its recorded fingerprint. These guards execute before any procedure is dropped or the PS-CAPTURE-002 delete definition can be restored. When safe, rollback removes only PS-MOMENT-001 objects, removes its delete-procedure fingerprint, and restores the exact PS-CAPTURE-002 Capture-delete contract.
- The real-SQL verifier uses two synthetic owners inside a rollback-only transaction. It proves owner isolation, forged and cross-owner denial, stale row/proposal rejection, idempotent exact source pinning, later-correction non-rewrite behavior, deterministic deletion propagation for unconfirmed and confirmed states, private-only state, body-free tombstones, and unchanged downstream publication/placement counts.

## C. What this means in plain English

A Capture is the member's private source note. A Moment proposal is a separate private draft of the structured story the member may want to keep. A confirmed Moment is the exact proposal version the member deliberately approved as canonical content.

PeerSlate now has a controlled boundary between those three things. The member can see exactly which Capture version is being used, rewrite the proposed Moment fields without changing the Capture, and confirm only after an explicit review. If the Capture is corrected later, the earlier proposal or confirmed Moment does not change behind the member's back. If the Capture is deleted, PeerSlate removes its text and keeps only a source-deleted marker; only canonical wording the member had already confirmed may remain.

Confirmation means "keep this as my private canonical Moment." It does not mean publish, share, place, add to Journal, update a resume, or send the content anywhere else.

## D. What the website or member can do now

On this branch, after the migration is applied in an approved environment, a signed-in member can:

- choose the original or current correction revision of one active private Capture;
- create or reopen one private proposal pinned to that exact source revision;
- inspect the selected source as read-only and see when a later correction exists;
- edit and save separately versioned canonical Moment fields;
- explicitly confirm the current valid version with current concurrency tokens;
- explicitly discard an unconfirmed proposal;
- see a confirmed private Moment read-only; and
- see a body-free source-deleted tombstone without losing previously confirmed canonical language.

The production website cannot do these things yet because this branch is intentionally unmerged and undeployed. Nothing in this package automatically publishes, places, shares, creates Journal content, changes a public profile, updates a resume, invokes AI, or writes to another surface.

## E. How this connects to PeerSlate

This package implements the Bible/Roadmap v2.3 private canonicalization boundary: Capture is immutable source evidence, AI or deterministic structure is only a proposal, and the member is the authority who confirms canonical meaning. It also preserves the Sync Standard requirement that source truth and derived structured content remain distinguishable and traceable.

The result is the prerequisite for the later PS-PLACEMENT-001 create-once/place-many model. A future placement package may deliberately project a confirmed Moment into an approved room, but PS-MOMENT-001 stops before that boundary. It keeps the Moment private and source-linked so later Journal, resume, Story, Work, Projects, Feed, or Interview Studio work can consume one approved canonical record without treating raw Capture text or a silent correction as authority.

The protected UI uses the approved Deep Navy Gold foundation with Newsreader headings, Inter product content, light-first document flow, marigold source/provenance cues, visible focus, and mobile reflow. It does not alter the shared design system or global navigation.

## F. Verification and validation

### Automated tests and repository gates

- `python -m compileall -q ...` passed for the changed Python modules and focused tests.
- Focused Moment, Moment migration, affected Capture, Capture migration, and database-service run: 73 tests passed, including the two new source-lock and rollback-refusal tests.
- Site Rules and governance pointer/guardrail run: 17 tests passed.
- Complete `python -m unittest discover` run: 313 tests passed.
- `git diff --check` and staged-diff checks passed.
- Plan-only `python scripts/apply_sql_migrations.py --migration PS-MOMENT-001` printed only the selected migration and opened no connection.
- Expected negative-path tests log fixed storage-unavailable messages; they did not produce false success.
- The first local focused attempt used system Python and stopped during import because that interpreter lacked `flask_limiter`; the first repository-virtual-environment attempt then correctly stopped at the app's required `ANTHROPIC_API_KEY` import gate. The authoritative runs used the established repository virtual environment with a non-secret test placeholder and passed completely.

### Isolated real SQL Server lifecycle evidence

- Created the short-lived empty Basic Azure SQL database `ps-moment-001-gate-20260718` on the existing PeerSlate SQL server. It contained no production/member data.
- Bootstrapped only the empty legacy `dbo.app_users` prerequisite, then applied and verified all eight foundation migrations, PS-CAPTURE-001, and PS-CAPTURE-002.
- Applied the corrected PS-MOMENT-001 migration on real SQL Server and ran the full two-owner verifier successfully on the first forward execution.
- Used independent SQL connections for the manager-required race proof. While save held its outer transaction, concurrent Capture deletion entered an `LCK_M_X` wait behind the save connection for 1.18 seconds; while confirmation held its outer transaction, deletion entered the same serialized wait for 0.98 seconds. In both cases deletion completed successfully only after the Moment transaction released the source relationship, the source deterministically became `deleted`, and no deadlock occurred.
- Proved the inverse ordering twice: deletion-first caused later save and later confirmation to return `source_deleted`. Across the concurrency proof, audit metadata/request fields contained zero occurrences of private Capture or canonical-content sentinels, and Slate entity, relation, and publication-version counts were unchanged. No publication, placement, Journal, resume, or other downstream write occurred.
- Exercised both new rollback refusals transactionally before the normal rollback. A synthetic later ledger record produced error 52235 and a later `usp_DeleteCapture` alteration produced error 52236; all three Moment tables, the PS-MOMENT-001 ledger entry, and protected procedure state remained intact, and the test-only changes were rolled back.
- Ran the guarded rollback with no Moment data or later dependency. It completed successfully.
- A separate prior-state script proved the PS-MOMENT-001 ledger row, all three Moment tables, and all five Moment procedures were absent; PS-CAPTURE-002, its Capture revision table, lifecycle procedures, ledger entry, and pre-Moment `usp_DeleteCapture` definition remained; no synthetic Capture/revision row survived. The one synthetic isolated owner intentionally committed for the multi-connection proof remained only in this temporary database until deletion.
- Reapplied PS-MOMENT-001, reran verification, then ran a separate final verification-only pass. All foundation, privacy, source pinning, two-owner, stale-token, deletion-tombstone, explicit-confirmation, and no-auto-publication/placement checks passed.
- Validated the exact temporary database resource before deletion, deleted it, and confirmed Azure returned no remaining database with that name. The temporary resource and its empty schema are not recoverable; no member data existed in it.
- No production SQL was applied, inspected, or changed.

### Responsive protected-UI evidence

- Re-ran the protected UI gate after the manager corrections using a synthetic in-memory owner and Moment preview with no persistent database connection. No UI file changed during rework.
- Native Edge/Chromium proof at 1440x900 measured viewport, document, and body widths at 1440 pixels with no horizontal overflow; the Moment panel was 980 pixels wide. Source and proposal regions were visibly separate, the source had `aria-readonly=true`, confirmation was required, and zero publication/audience controls were present.
- Touch-mobile proof at 390x844 measured viewport, document, and body widths at 390 pixels with no horizontal overflow; the panel was 350 pixels wide, source/proposal regions were 308 pixels wide, touch emulation was active, and Save/Confirm targets were exactly 44 pixels high.
- A 720x450 CSS-pixel viewport, equivalent to the layout space available at 200% zoom on a 1440x900 display, reflowed with document/body widths equal to the viewport and no horizontal overflow.
- Keyboard progression from Title to Date produced a visible solid 3-pixel navy focus outline. Browser console error lists were empty.
- The source-deleted confirmed view at 390x844 had one tombstone notice, no source-text element, no editable field, no mutation form, and no publication/audience control.
- Accepted screenshots are outside the repository at `C:\Users\peter\.codex\visualizations\2026\07\18\019f76fe-df8e-77d0-9858-53c8a0310fcf\moment-gate\moment-proposal-desktop-edge-1440x900.png`, `...\moment-proposal-mobile-edge-390x844.png`, `...\moment-confirmed-source-deleted-mobile-edge-390x844.png`, and `...\moment-proposal-200pct-equivalent-edge-720x450.png`.
- The preferred Playwright CLI could not run because npm/npx is absent. The in-app browser's DOM evidence was valid, but its full-page screenshots were visibly distorted and were rejected; the accepted images and matching measurements came from native Edge through the bundled Playwright runtime.

### Production and real-member evidence

- Production migration: not run by design; ChatGPT Work owns that release gate.
- Azure PR, merge, pipeline deployment, and live route validation: not run by design.
- Real-member validation: not run because the schema/application branch is not deployed. No claim of live Moment behavior is made.

## G. Known gaps, risks, and exclusions

- PS-MOMENT-001 is not live until ChatGPT Work approves the branch, controls any production migration, merges through Azure DevOps, waits for the exact pipeline, and verifies the protected route.
- Rollback is intentionally blocked after any Moment data exists, any later migration is recorded, a protected procedure is changed, or an unknown later dependency appears. That stop condition protects canonical member content and prevents a newer Capture delete contract from being overwritten.
- This package supports private text Capture only. It does not add AI proposal generation, voice/media Capture, placement, Journal UI, audience controls, sharing, public projections, matching, or account-wide export/deletion.
- It does not change authentication architecture, public routes, global navigation/theme, the public resume, Slate Board, or Interview Studio.
- It does not make Capture text verified evidence, and it does not claim that a confirmed Moment is public, placed, shared, or independently verified.
- The Capture entry control offers the immutable original or the current correction version exposed by the existing Capture lifecycle read contract. The SQL contract can pin any exact owned revision number; browsing all intermediate historical corrections remains outside this minimal entry slice.
- The existing global/mobile navigation remains visible around the protected page because navigation changes were explicitly forbidden. This initiative added no new permanent navigation layer.

## H. Clear next step

ChatGPT Work should review the exact pushed branch and handoff SHA, audit the migration/rollback and deletion-propagation contracts, and confirm the diff remains inside the reserved PS-MOMENT-001 files. If approved, ChatGPT Work owns the Azure PR, production-migration decision, squash merge, pipeline/deployment wait, and protected real-member validation. That sequence unlocks PS-MOMENT-001 without prematurely starting placement or another downstream surface.

## I. What Pete needs to do or decide

None. ChatGPT Work owns the documented review and release gates. Pete is needed only if review discovers a product or data conflict not resolved by the package contracts.
