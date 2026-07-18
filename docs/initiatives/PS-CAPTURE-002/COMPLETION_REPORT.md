# PeerSlate Completion and Handoff Report — PS-CAPTURE-002

## A. Status

- Package: PS-CAPTURE-002 — Controlled Private Capture Lifecycle
- Status: Ready to merge — branch implementation, manager review, responsive mobile proof, isolated SQL lifecycle gate, and the production forward migration/verification are complete; Azure PR completion, pipeline deployment, and production application validation remain
- Branch and commit: `work/2026-07-18-capture-002`; implementation commit `0b1bc01b2c8426c85045d2f8828776b9a23d7f9d`; the exact report/handoff commit is supplied with the branch handoff because a commit cannot record its own SHA
- Base: authoritative Azure DevOps `origin/main` at `6f9f22c34d791dac2466a957450dfc18e9285176`; this is the required PS-BASELINE-001 commit, and Azure pipeline run 82 succeeded for that exact SHA
- PR / pipeline / environment: Azure PR 63 is open from the exact task branch into `main`; no application deployment run has occurred yet. Implementation and manager gate fixes used the isolated worktree at `C:\Users\peter\Documents\portfolio-capture-002`.
- Production state: the backward-compatible PS-CAPTURE-002 forward migration and its full verification passed against production. The deployed application remains on the PS-CAPTURE-001 private create/list slice until PR 63 is squash-merged and its pipeline deploys.

## B. What changed technically

### Protected HTTP and template boundary

- Extended `GET/POST /app/capture` to list active or archived captures while preserving the existing private text-create path.
- Added owner-protected routes for correction, archive, restore, permanent deletion, and per-capture JSON export.
- Every lifecycle write uses the existing same-origin check, a validated opaque UUID, an eight-byte expected row-version token, and `identity.user_key` from the server identity boundary. No browser-supplied user or profile identifier is trusted.
- Foreign, missing, deleted, and stale captures return the same outward changed/not-found result. Unauthenticated requests redirect before a lifecycle or export procedure is called.
- Correction and correction-note input are trimmed and validated against the existing 8,000 UTF-16-code-unit body limit and a 1,000-unit note limit before SQL. SQL repeats the validation.
- Delete is POST-only and requires a deliberate confirmation checkbox. Archive remains the reversible option.
- Export returns deterministic UTF-8 JSON labeled `peerslate.capture.export`, schema version 1. It includes the opaque key, type, private lifecycle state, timestamps, immutable original text, ordered revisions, and current-version designation. It excludes internal numeric IDs, user keys, audit data, placement claims, and other owners' records. Responses use attachment, `private, no-store`, and `nosniff` headers.
- Added compact Capture-only controls and focus/mobile styles in the initiative's reserved template and stylesheet. No public template, global navigation, shared theme, résumé, Interview Studio, Journal, Moment, placement, or authentication architecture file changed.

### Data, procedures, and migration

- Added proposed migration `PS-CAPTURE-002_capture_lifecycle.sql` after explicit PS-AUTH-001 and PS-CAPTURE-001 ledger checks.
- Added `dbo.capture_revisions` with a surrogate key, opaque revision key, parent foreign key, capture-local monotonically increasing revision number, corrected body, optional correction note, actor provenance, timestamp, row version, constraints, and latest-revision index.
- `dbo.captures.body` remains the immutable original. A correction inserts a revision and updates only the parent's `updated_at_utc`, advancing the parent row version used for optimistic concurrency.
- Updated `dbo.usp_ListCapturesForOwner` and added owner-resolving get, correct, archive, restore, delete, and export procedures. Owner resolution and capture-key filtering occur together in SQL.
- Archive changes only `active/status/updated_at_utc`; restore reverses that state. Neither changes visibility or creates another product object.
- Delete removes the original capture row and all revision rows in one transaction after owner and concurrency checks. The retained audit event contains only the capture key, prior status, revision count, action, outcome, and timestamps—not body or correction-note content.
- Added a guarded rollback that refuses to discard revision rows, archived state, or later dependencies; otherwise it drops only PS-CAPTURE-002 objects, restores the PS-CAPTURE-001 list procedure, records a body-free rollback audit event, and removes the migration-ledger row.
- Corrected the rollback dependency guard after the real isolated run showed that SQL Server reports a table's own check constraints as expression dependencies. The guard now ignores objects owned by `dbo.capture_revisions` while continuing to block external later dependencies.
- Registered only the optional PS-CAPTURE-002 forward migration and its verification path in the existing runner. Plan-only mode does not connect to or change a database.

### Verification SQL and tests

- Added production-safe verification SQL that creates two synthetic owners inside one outer transaction and rolls all synthetic data back.
- Corrected the verifier after the real SQL run exposed prohibited nested `INSERT ... EXEC` calls. Lifecycle procedures are now called directly and their database state is asserted; read/export procedures that do not perform nested audit execution remain captured for exact result-set checks.
- The verifier proves cross-owner get/export/correct/archive/restore/delete denial, immutable original text, ordered current revision selection, stale-row-version rejection, archive filtering, reversible restore, transactional aggregate deletion, body-free audit metadata, private visibility, and no automatic placement/publication.
- Added focused route, migration-contract, runner-registration, and procedure-allowlist tests. The focused set grew to 44 passing tests, and the complete repository suite passes 281 tests.

Changed files are restricted to the package allowlist:

- `owner_routes.py`
- `templates/owner_capture.html`
- `static/css/owner-app.css` (Capture-specific selectors only)
- `services/database_service.py` (allowlist only)
- `scripts/apply_sql_migrations.py` (registration/verification only)
- the two PS-CAPTURE-002 migration files and Capture-specific verification SQL
- `tests/test_owner_capture.py`, `tests/test_capture_migration.py`, and `tests/test_database_service.py`
- this initiative completion report

## C. What this means in plain English

A private Capture can now have a safe history instead of being silently overwritten. The first words remain the permanent original. If the owner corrects them, PeerSlate records a numbered new version and shows the newest version while keeping the original available.

The owner can put a Capture aside in an archive and restore it later. Permanent deletion is intentionally harder: it is clearly described as irreversible, requires confirmation, and removes both the original and every correction. A single Capture can also be downloaded as a private, versioned JSON file. "Optimistic concurrency" means an action from an old browser tab is rejected if another action changed the Capture first, preventing silent overwrites.

## D. What the website or member can do now

On this branch, an authenticated member can create and list private text Captures; switch between active and archived lists; correct an active Capture into a new version; inspect the immutable original; archive and restore; explicitly delete the whole Capture history; and export one Capture with its version history.

Production cannot do the new lifecycle actions yet because this branch has not been reviewed, migrated, merged, or deployed. This package does not publish, place, create a Moment, add Journal UI, add audience controls, create AI structure, or provide account-wide export/deletion.

## E. How this connects to PeerSlate

Bible and Roadmap v2.3 define Capture as the private source layer before reviewed canonical Moments and deliberate placement. This work makes that source trustworthy: it preserves what the member originally said, records corrections with provenance, keeps lifecycle actions private, and makes deletion explicit. It does not cross the Capture-to-Moment boundary or imply that publication, placement, matching, or public privacy behavior exists.

The protected controls reuse the approved Deep Navy Gold owner surface and progressive disclosure. They do not change global theme/navigation or downstream experiences. The resulting private source aggregate is ready for later manager-approved Moment and placement work without pre-implementing either system.

## F. Verification and validation

### Automated repository evidence

- Baseline ancestry: `git merge-base --is-ancestor 6f9f22c34d791dac2466a957450dfc18e9285176 origin/main` — passed; `origin/main` was exactly that SHA after `git fetch --prune origin`.
- Baseline pipeline: Azure pipeline run 82 — succeeded for exact source SHA `6f9f22c34d791dac2466a957450dfc18e9285176`.
- Focused lifecycle/service/migration tests: `python -m unittest tests.test_owner_capture tests.test_capture_migration tests.test_database_service -v` — 44 passed.
- Governance/site guardrails: `python -m unittest tests.test_governance_pointers tests.test_site_rules -v` — 17 passed.
- Complete suite: `python -m unittest discover -s tests -q` — 281 passed.
- Syntax/import check: `python -m compileall owner_routes.py scripts/apply_sql_migrations.py services/database_service.py tests/test_owner_capture.py tests/test_capture_migration.py tests/test_database_service.py` — passed.
- Migration plan: `python scripts/apply_sql_migrations.py --migration PS-CAPTURE-002` — selected only `PS-CAPTURE-002_capture_lifecycle.sql` and made no database connection or change.
- Patch hygiene: `git diff --check` — passed.
- Reserved-file audit: 11 implementation files staged; zero files outside the package allowlist. This report is the twelfth allowed file.
- Secret-pattern scan of the staged diff returned no matches.

The Python commands used the existing configured virtual environment from `C:\Users\peter\Documents\portfolio-claude-review\.venv` and a test-only `ANTHROPIC_API_KEY=test-key`, matching the repository's test convention. The suite emitted only the existing Flask-Limiter in-memory warning and expected privacy-safe 503 log lines from negative tests.

### Visual and accessibility evidence

- Local synthetic-owner preview returned HTTP 200 for active and archived Capture states without persistent data.
- Desktop review at 1440×900: full document width equaled viewport width; no horizontal overflow.
- Native Edge mobile emulation at 390×844 with five touch points: viewport, document, and body widths were all 390 pixels with no horizontal overflow; the Capture panel measured 350 pixels wide from x=20 to x=370, the textarea measured 300 pixels wide, Archive appeared only in the active state, and Restore appeared only in the archived state.
- The new controls have semantic labels, POST forms for mutations, visible focus styles, 44-pixel minimum targets, responsive stacking, and reduced-motion handling inherited/maintained by the protected owner surface.
- Trustworthy mobile screenshots were saved outside the repository at `C:\Users\peter\.codex\visualizations\2026\07\18\019f766c-5f37-7170-8f5f-d63834de1092\capture-gate\capture-active-lifecycle-edge-cdp-390x844.png` and `...\capture-archived-edge-cdp-390x844.png`.
- The repository's Playwright CLI could not run because `npx` is not installed in this environment. The manager rejected the in-app browser's first distorted image, then used Edge's DevTools phone-emulation protocol directly for the accepted viewport, touch, DOM-width, and screenshot evidence.

### Isolated Azure SQL evidence

- Created the short-lived Basic database `ps-capture-002-gate-20260718` on the existing PeerSlate Azure SQL server. It contained no production/member data and was deleted after the gate completed.
- Bootstrapped only the legacy pre-migration `dbo.app_users` prerequisite, then applied and verified all eight versioned foundation migrations and PS-CAPTURE-001.
- First PS-CAPTURE-002 execution applied the forward migration and exposed the verifier's nested `INSERT ... EXEC` defect. After the verifier correction, the lifecycle verification passed against real SQL Server.
- The first guarded rollback correctly stopped on its dependency check but exposed that the table's own check constraints were falsely classified as later dependencies. After narrowing that guard, rollback succeeded.
- Post-rollback inspection proved the PS-CAPTURE-002 ledger row, revision table, and six lifecycle procedures were absent; the PS-CAPTURE-001 list procedure remained and had no `@Archived` parameter.
- Reapply and final verification both succeeded, including the two-owner isolation, correction provenance, concurrency, archive/restore, aggregate deletion, private visibility, no automatic publication, and full synthetic-data rollback checks.
- The exact temporary database resource was validated before deletion, and Azure confirmed it no longer existed afterward. Production SQL was not changed during this gate.

### Production SQL evidence

- After Azure PR 63 was opened and the branch was manager-approved, `python scripts/apply_sql_migrations.py --migration PS-CAPTURE-002 --apply --verify` ran against the configured production database using cached Microsoft Entra authentication; no password, token, or connection secret was read or recorded.
- The forward migration applied successfully, all eight foundation records and platform/privacy checks passed, and the PS-CAPTURE-002 two-owner lifecycle verifier passed with no automatic publication and full synthetic-data rollback.
- No production Capture text or member record was read, printed, copied, or added to the report.

### Evidence not yet produced

- No real-member lifecycle validation has been performed because the application branch is intentionally unmerged and undeployed. The production schema is ready, but the new routes and controls will not exist until PR 63 deploys.

## G. Known gaps, risks, and exclusions

- Manager review and the isolated SQL apply → verify → guarded rollback → reapply → verify gate are complete. Any production-schema difference, unknown foreign key, or later dependency remains a stop condition; the rollback is designed to block rather than lose data.
- The production migration and verification succeeded before application deployment. The schema is backward-compatible with the currently deployed PS-CAPTURE-001 application while PR 63 awaits completion.
- Production auth, Azure deployment, and real-owner behavior remain unverified for this branch.
- This slice is text-only and per-Capture. Attachments, AI structuring, audience controls, public sharing, Journal UI, canonical Moment, placement, matching, account-wide export/deletion, and retention-policy work are excluded.
- The implementation does not claim that archived content is published, that corrected content is verified, or that any action creates a public/canonical record.

## H. Clear next step

ChatGPT Work should complete Azure PR 63 by squash merge, delete the task branch, wait for the matching pipeline Build and Deploy stages, then validate the protected Capture boundary and lifecycle behavior without exposing member data.

## I. What Pete needs to do or decide

None. ChatGPT Work can conduct the review and approved migration/release gate. Pete is needed only if the isolated database reveals one of the package's documented stop conditions or requires a product/data decision.
