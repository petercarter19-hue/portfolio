# PS-OPPORTUNITY-SLATE-001 - comprehensive Codex to Claude handoff

Date: 2026-08-04

Receiver: Claude, using the package-required Claude implementation route.

Owner objective: finish every remaining Opportunity Slate slice, release it
through the governed Azure path, and verify the completed page live.

This document supersedes `04-CODEX-TO-CLARK-HANDOFF-2026-08-04.md` as the
continuation brief. The earlier file remains useful provenance and is not
deleted.

## Copy-paste prompt for Claude

> You are taking over PS-OPPORTUNITY-SLATE-001 as the sole continuation
> writer. Read this entire handoff, `START_HERE.md`, the current control plane,
> the package README, and the package's architecture handoff before editing.
> Confirm `/model` and `/status`; this package records Claude Opus 5 Extra High
> as the implementation-writer exception and requires fresh independent review
> at its Protected gates. Start with the pushed additive-schema branch and do
> not jump directly to OS4. Preserve every dirty worktree and untracked artifact
> named below. Move the work through schema PR/apply, OS3 app release, OS4,
> OS5, OS6, and final live closeout. Keep discussed, implemented, pushed,
> merged, schema-applied, deployed, and live as separate states. Do not stop at
> a plan while an authorized, safe next action remains.

## 1. Formal transfer record

- **Package and outcome:** PS-OPPORTUNITY-SLATE-001; complete and release the
  public, unlisted Opportunity Slate journey while preserving the signed-in
  private lifecycle and the anonymous fixture/demo truth boundary.
- **Delivery path:** Protected for OS3 schema/AI/private-evidence work, OS4
  deletion/persistence, and OS6 parsing/SSRF; Bounded for OS5 shared dictation.
- **Sender:** Codex.
- **Receiver and sole continuation writer:** Claude, subject to confirming the
  package-required model and active-writer state before editing.
- **Owner:** Pete.
- **Authoritative remote:** Azure DevOps `origin`; GitHub is a backup only.
- **Authoritative main at transfer preparation:**
  `af1c6a2216bdb5cddd932fbc3d5c1d0e23ef95b3`.
- **Additive-schema branch:**
  `work/2026-08-04-oppslate-os3-additive`.
- **Additive implementation commit:**
  `8797c7fe7394f3f32893a73ab5166c2c0e3b037f`.
- **Prior pushed handoff tip:**
  `8de31f686ccedbf0275b1cbaf0d61451a2370559`.
- **Comprehensive handoff content commit:**
  `TO_BE_REPLACED_AFTER_FIRST_COMMIT`.
- **Release state:** branch pushed; no active Azure PR; OS3 schema correction
  not merged or applied; OS3/OS4 application behavior not deployed.
- **Ownership:** Codex explicitly relinquishes the Opportunity Slate
  continuation after pushing the final documentation tip. Claude may resume the
  additive worktree, then the existing OS3/OS4 worktrees sequentially. Pete
  retains product, visual-acceptance, protected-environment approval, and final
  release authority.
- **Single immediate next action:** review and open the additive-schema Azure
  PR. Do not modify application branches first.

The current control plane still contains historical wording that says the
runtime lane has no writer, while the same record names the owner-routed Claude
implementation role and OS1/OS2 are already released. Pete's current direct
instruction transfers the continuation to Claude. Record that takeover in the
package/control plane when doing so can be reconciled without colliding with an
active shared-governance writer; do not let the stale sentence justify another
architecture round.

## 2. Honest current state

As reverified during this handoff:

- `origin/main` is
  `af1c6a2216bdb5cddd932fbc3d5c1d0e23ef95b3`.
- There are **no active Azure DevOps pull requests**.
- `https://peerslate.com/healthz` returns HTTP 200 and reports live release
  marker `21a77fc14df89aa4f4397f2d`.
- `https://peerslate.com/opportunity-slate` returns HTTP 200 with
  `Cache-Control: no-store, private` and
  `X-Robots-Tag: noindex, nofollow, noarchive`.
- The public route is therefore live at the already released OS1/OS2 level.
  That does not prove OS3 or OS4 is live.
- The last successful application pipeline in the current run list is run 505
  on source `f59dd9adb8d3da3e6faaae6691ecad1f801b0c2d`.
- Run 511 is completed/failed on current main `af1c6a...`; it reached the
  production migration path and refused the reused 001 identity. It did not
  apply OS3 SQL.
- Production's schema ledger has 21 rows. It contains
  `PS-OPPSLATE-001` and does **not** contain `PS-OPPSLATE-002`.
- A live read-only governed report identifies `PS-OPPSLATE-002` as registered,
  gated, and pending. `PS-JOURNAL-001` and `PS-PLAT-008` are unrelated
  ungated/draft rows and are held back.
- `docs/governance/PRODUCTION_SCHEMA_STATE.md` does not exist yet. The first
  governed production apply/report must generate it, and a follow-up PR must
  commit the generated record.

Do not equate the route's 200 response with the requested completed page. The
visitor can use OS1/OS2 today; the alignment engine/workbench, durable save
lifecycle, shared dictation, and upload/import work remain to be released.

## 3. Remaining time

Best realistic remaining engineering/release time: **8-14 focused hours**.

Safer planning range: **12-20 hours** if Azure approvals, CI queues, merge
conflicts, the OS4 schema port, dependency/runtime checks, or owner visual
acceptance require another round.

Approximate breakdown:

- OS3 additive schema PR/apply plus OS3 app restack/release: 1.5-3 hours.
- OS4 schema port, correction preservation, visual acceptance, release: 2-4
  hours.
- OS5 dictation completion/regression: 1-2 hours.
- OS6 signed-in upload/import with security proof: 3-5 hours.
- Final end-to-end evidence and closeout: 0.5-1 hour.

## 4. Authority and non-negotiable product rules

Read in this order:

1. `START_HERE.md`.
2. `docs/governance/CURRENT_BASELINE.yaml`.
3. `docs/AI_WORKFLOW.md` and `docs/AI_MODEL_AND_ROLE_ROUTING.md`.
4. `docs/initiatives/PS-OPPORTUNITY-SLATE-001/README.md`.
5. `01_ARCHITECTURE_AND_IMPLEMENTATION_HANDOFF.md`, especially sections 8-18.
6. `OWNER_VISUAL_REVIEW_2026-08-03.md`.
7. OS2, OS3, and OS4 completion/evidence records relevant to the slice being
   released.
8. `docs/initiatives/PS-OPS-001/README.md` and
   `GOVERNED_SCHEMA_MIGRATION_PATH.md` before schema or production work.

Binding rules:

- Opportunity Slate is separate from Workshop. Do not place it under a
  Workshop header or selected Workshop destination.
- No Ask Slate AI control ships in this package. That generated-image chrome
  was explicitly rejected as an artifact.
- Anonymous v1 is a direct-link, unlisted, noindex public session. It persists
  nothing server-side, uses signed/client-held context, and grounds only on a
  clearly labeled fictional demo evidence library.
- Signed-in mode uses owner-scoped server state and authorized private
  evidence. Authorization occurs before retrieval.
- Upload/import, saved slates, saved details, response persistence, and delete
  are signed-in only.
- AI proposes; the member confirms. Voice never auto-submits, analyzes, saves,
  publishes, deletes, or navigates.
- No overall score, percentage, ranking, recommendation, fit verdict, or
  employer prediction exists in data, API, model schema, prose, or UI.
- Employer source, AI proposal, member response, authorized evidence, and
  saved snapshot remain distinct provenance classes.
- Evidence is referenced by exact key/version; Opportunity Slate never rewrites
  Workshop or Moment truth.
- One active slate per signed-in member in v1, with versioned saved results.
- Nothing is published, shared, or sent to an employer from this room.
- Image 04 controls Alignment geometry. Image 05 controls saved-state content
  and actions only; its flatter/blue-heavy/compressed geometry is prohibited.
- The owner resolved the shared card gap to **24px**.
- The filter row belongs to OS4.
- The closing action strip stays.
- The semantic false-positive limitation is accepted only for the current
  small, unpromoted demo audience. It is not evidence of semantic entailment
  and must be revisited before broader promotion.

## 5. Why the schema correction exists

The original OS3 schema branch extended the already-ledgered migration ID
`PS-OPPSLATE-001`. Production had applied that ID for the OS1/OS2 shape.
Immutable migration IDs cannot represent different executable bytes over time.

The governed path correctly failed closed. The correction is:

1. Restore 001 byte-for-byte to the proven OS1/OS2 baseline.
2. Add OS3 as a new additive migration, `PS-OPPSLATE-002`.
3. Never update, replace, or reinterpret the production 001 ledger row.

Earlier failures were independent issues and did not apply OS3 SQL:

- Run 497: CLI argument ordering failed before connection.
- Run 501: hosted-agent credential acquisition failed closed.
- Runs 506-508: canceled, with no apply evidence.
- Run 511: reached production and refused the reused 001 identity.

Do not revive the revision-aware experiment or attempt to make a ledger ID
mutable.

## 6. Additive schema branch - completed work

Worktree:
`C:\Users\peter\Documents\portfolio\.wt\oppslate-os3-additive`

Branch:
`work/2026-08-04-oppslate-os3-additive`

The implementation commit changes exactly these technical areas:

- Restores the 001 forward migration, rollback, and verifier.
- Adds the 002 forward migration, rollback, and verifier.
- Adds 002 to `SQL FIles/Migrations/registry.json` after 001.
- Updates migration tests to apply/verify/rollback/reapply the 001 baseline and
  002 delta in sequence.
- Corrects the OS3 schema completion report and governed gate evidence.

Exact governed hashes:

- 001 executable SHA-256:
  `2406ff6eedd44939ee5148982462a66935f13dfea45fe46076cf5895883c7273`.
- 002 executable SHA-256:
  `2af25b7d4f04984d88a30b7d65bc1948bc4bba810ab048963b4cd85a8d471dd0`.

002 adds four tables:

- `opportunity_analyses`
- `opportunity_analysis_statements`
- `opportunity_analysis_citations`
- `opportunity_responses`

It adds four procedures and revises four existing owner-scoped procedures. It
labels the eight procedures it owns with the 002 definition hash. Its preflight
requires the exact 001 baseline and refuses partial/drifted OS3 shape.

The rollback refuses member rows, later migrations, or procedure drift; drops
the four new procedures; restores the four modified procedures to exact OS2
definitions; drops the four new tables; and deletes only the 002 ledger row.

### Proof already completed

Disposable Azure SQL database:
`ps-oppslate-additive-gate-20260804` on server `peerslate`.

- 001: prerequisites, apply 125 objects, no-op reapply, verifier
  `verified = 1`, rollback 125 objects, reapply: **Pass**.
- 002: prerequisites including 001, apply 61 objects, no-op reapply, verifier
  `verified = 1`, rollback 61 objects, reapply: **Pass**.
- Disposable database deleted; later lookup returned `ResourceNotFound`.
- Migration/path suite: **116 passed, 3 skipped**.
- Wider affected suite: **309 passed, 3 skipped**.
- Registry: **24 registered, 12 gated and matching**.
- `git diff --check`: Pass.

Evidence:

- `OS-3_SCHEMA_RELEASE_COMPLETION_REPORT.md`
- `evidence/os-3/sql-gate-governed.json`
- `SQL FIles/Migrations/registry.json`

## 7. Immediate release procedure for PS-OPPSLATE-002

Before any write, fetch and verify that `origin/main` and the branch have not
moved. If they moved, reconcile from current authority and rerun affected
checks.

1. Review the complete `origin/main...HEAD` diff in the additive worktree.
2. Obtain the package-required fresh independent review of the exact candidate
   SHA because this is schema/migration work.
3. Open an Azure DevOps PR from
   `work/2026-08-04-oppslate-os3-additive` to `main`.
4. Wait for current-target blocking validation. Use the required squash merge
   without bypass. Record the exact merge SHA.
5. Wait for the automatic pipeline on that exact main SHA. Do not queue a
   same-SHA fallback while it is queued or running.
6. Queue pipeline 1 manually on `main` with:

   ```powershell
   az pipelines run --id 1 --branch main `
     --org https://dev.azure.com/peerslate19 `
     --project portfolio-site `
     --parameters schemaAction=apply `
       schemaMigrationId=PS-OPPSLATE-002 `
       forceProductionDeploy=false
   ```

7. Approve the `peerslate-database-schema` environment only when the plan
   shows migration 002 and the exact hash above. The environment permission is
   already configured for pipeline 1.
8. Verify the SchemaMigration stage, final ledger, object inventory, no-op/apply
   distinction, and `SchemaMigrationEvidence` artifact.
9. Confirm a read-only report shows 002 applied and no unexplained ledger row.
10. Commit the generated `PRODUCTION_SCHEMA_STATE.md` through a separate
    documentation PR. Do not hand-edit it.

The Azure service connection maps client ID
`8948ceff-6f5c-4f88-91cd-aefc6e99fc32` to contained database principal
`peerslate-ado-schema`. It has `db_ddladmin`, definition visibility, narrow
ledger DML, and audit-procedure execution. It is not `db_owner`,
`db_datareader`, or `db_datawriter`. Do not add a password, widen the firewall,
or broaden its standing member-data access.

## 8. OS3 application branch

Worktree:
`C:\Users\peter\Documents\portfolio\.wt\oppslate-os3`

Branch:
`work/2026-08-04-opportunity-slate-os3`

Pushed tip:
`3ac0e9d5a5fb0a20ce1c9f70b1d73ae1ea2f02a9`

Local worktree status is clean except for preserved untracked
`artifacts/2026-08-04-os3/` and `output/`. Do not clean, reset, delete, or
overwrite either directory.

What the branch contains:

- grounded Alignment analysis with structural composition templates;
- server-selected owner-scoped evidence allowlist;
- citation span/version validation and unknown/cross-owner refusal;
- derived statuses rather than model-chosen aggregate verdicts;
- analysis processing, cancel, failure, and response workflows;
- desktop, 390, 320, 200%-zoom, reduced-motion, and signed-in/public evidence;
- corrections for thirteen independent-review findings;
- owner decisions for 24px spacing, deferred filter, closing strip, and the
  accepted current-demo semantic limitation.

Prior final evidence on its then-current integration:

- affected suite: **351 passed, 2 skipped**;
- repository-wide Windows run excluding the known POSIX-only mode assertion:
  **2,391 passed, 9 skipped, 1 deselected; 3,200 subtests passed**;
- `git diff --check`: Pass.

Those results are evidence of the existing tip, not permission to skip testing
after the additive-schema integration.

### How to continue OS3 safely

Only after production 002 is verified:

1. Fetch current main and preserve the exact old tip as a backup ref.
2. Merge current `origin/main` into the existing OS3 branch or port its bounded
   net application delta into a fresh worktree. Do not reintroduce old 001
   migration bytes.
3. Resolve all migration/registry/verifier conflicts in favor of current main's
   immutable 001 plus additive 002 contract.
4. Update OS3 reports/tests that still describe schema under 001.
5. Re-run focused migration, service, route, AI, site-rule, and operational
   tests; then run the repository-wide checks justified by the integration.
6. Run a complete-diff self-review and fresh Protected exact-SHA review focused
   on private evidence grounding, no-aggregate composition, owner isolation,
   cross-version citations, response attribution, and merge-resolution drift.
7. Open the OS3 app PR, wait for blocking validation, squash merge, wait for the
   exact automatic production run, and verify the live route and release
   identity.

Do not call OS3 live merely because 002 is applied. Schema and application are
separate operations.

## 9. OS4 save lifecycle branch

Worktree:
`C:\Users\peter\Documents\portfolio\.wt\oppslate-os4`

Branch:
`work/2026-08-04-opportunity-slate-os4`

Pushed committed tip:
`de8735ced7673685ef7909b9d4bd72490b74f0c3`

The worktree has legitimate **uncommitted corrections** in:

- `SQL FIles/Migrations/proposed/PS-OPPSLATE-001_opportunity_slate.sql`
- `OS-4_COMPLETION_REPORT.md`
- `evidence/os-4/EVIDENCE_MANIFEST.md`
- `opportunity_slate_routes.py`
- `services/opportunity_slate_service.py`
- `_alignment.html`
- `tests/test_opportunity_slate.py`
- `tests/test_opportunity_slate_ai.py`
- `tests/test_opportunity_slate_migration.py`

Preserve these bytes. They correct:

- unknown save outcomes so the UI no longer falsely claims rollback;
- partial-snapshot refusal on both write and read paths;
- the Alignment heading outline (`h1` to `h2`, not `h3`);
- stale route/service contract documentation.

Current corrected-worktree evidence:

- focused: **385 passed, 1 skipped; 848 subtests passed**;
- repository-wide: **2,174 passed, 7 skipped; 1,854 subtests passed**;
- implementation `git diff --check`: Pass;
- changed schema bytes: **governed engine gate still pending**.

### Critical migration rule for OS4

The OS4 branch still expresses its schema additions by modifying 001. That is
historical and cannot be released.

After OS3's 002 is merged/applied, port OS4's schema delta to a new additive
migration **`PS-OPPSLATE-003`** that requires 002. Do not edit immutable 001.
Do not change production-applied 002 bytes. The 003 rollback must restore any
002-owned procedures it modifies, remove only 003-owned objects/ledger state,
and refuse member data, later migrations, or definition drift as applicable.

Gate 003 on a disposable Azure SQL database through the full chain and preserve
the current OS4 corrections/tests while updating their expected migration IDs
and shapes. Delete the gate database afterwards.

### OS4 completion gates

- Integrate onto the released OS3 application and current schema contract.
- Preserve one component for unsaved/saved/stale geometry.
- Prove versioned saves, current/stale fingerprints, evidence version changes,
  idempotent saves, partial snapshot refusal, delete atomicity, delete failure,
  and two-owner isolation.
- Recapture the real signed-in shell states after final integration.
- Pete must visually inspect the saved-details surface in particular; it has no
  exact generated-image authority and uses the approved room grammar under
  adaptation M13.
- Obtain the package-required fresh Protected review for persistence/deletion
  and migration 003.
- Merge/apply schema 003 before releasing application code that depends on it.
- Deploy and live-verify signed-in save/details/stale/delete behavior without
  exposing it anonymously.

Some late release facts in OS4 report section 12 are now stale: the governed
path and environment are built, and the correct schema plan is additive
002/003. Preserve the useful findings and tests; update the release narrative
instead of copying its old blocker forward.

## 10. OS5 shared dictation

Existing local worktree:
`C:\Users\peter\Documents\portfolio\.wt\oppslate-os5-dictation`

Local branch:
`work/2026-08-03-shared-dictation-module`

Local tip:
`e3850fd36cbaf68224420ba0e487ff320eb43e42`

The remote branch is gone. Preserve untracked
`artifacts/2026-08-03-shared-dictation-module/`.

Useful implementation commit:
`cb14fe5` (`static/js/dictation.js`, Interview Studio integration/template,
and tests). The later `e3850fd` is a merge of then-current main.

Before reuse, verify whether current main already contains equivalent work. If
not, port the useful extraction onto a fresh post-OS4 branch and resolve drift.

Known bounded cleanup: the module takes configurable `silenceMs`, but several
status/announcement strings and tests still hardcode "10 seconds". Derive the
displayed duration from the configured value so behavior and copy cannot
disagree. Then wire the same module to all four Opportunity Slate microphone
surfaces:

- role intake;
- source concern correction;
- requirement clarification/correction;
- Tell us more response.

Voice and text must edit the same field, insert at caret, dispatch `input`,
remain editable, expose accurate `aria-pressed`/live status, respect reduced
motion, and never auto-advance or persist. Run the complete Interview Studio
dictation regression plus Opportunity Slate route/JS/accessibility checks.

## 11. OS6 signed-in upload and public-link import

No OS6 implementation branch exists. Create it from current main only after
the preceding integration is stable.

This slice is signed-in only in v1. Anonymous visitors keep honest unavailable
tiles; do not expose parsing or network-fetch attack surfaces on the public
preview.

### Upload requirements

- PDF, DOCX, and TXT only.
- Route-specific request cap and bounded `MAX + 1` reads.
- Declared MIME plus magic/structure validation; extension alone is not trust.
- No macro, script, embedded-object, or external-resource execution.
- Bounded extraction output and parser time/memory behavior.
- Private original storage only after successful validation; digest recorded.
- Failed extraction discards bytes and persists no partial source.
- Original retrieval is owner-scoped and forced to a safe attachment/inline
  policy with the existing CSP pattern.
- Any new dependency must be pinned in both requirement files and proven on
  Azure App Service's Python 3.14 runtime, not only the local Python 3.13 venv.

### Public-link import SSRF requirements

- HTTPS only.
- Resolve and reject loopback, private, link-local, multicast, reserved,
  metadata, and otherwise non-public targets for IPv4 and IPv6.
- Pin the validated destination for the actual connection to prevent DNS
  rebinding.
- Revalidate every redirect; maximum three redirects.
- Tight connect/read timeout and byte cap.
- HTML-to-text only; no script execution, asset fetches, browser rendering, or
  instruction execution.
- Treat fetched role text as hostile data inside the AI prompt boundary.
- Consider a supported ATS/employer allowlist as the additional v1 restriction
  described by the architecture.
- Persist nothing on failure; preserve member inputs and offer paste/upload
  fallback.

OS6 requires a fresh security-focused independent review and production-runtime
dependency proof before release.

## 12. Visual authority and owner review

Locked visual set:
`visual-authority/2026-08-02-chatgpt-lock/`.

- Images 01-03: primary intake/review flow.
- Image 04: exact Alignment geometry and depth.
- Image 05: saved-state content/actions only.
- Images 06-09: dictation, processing, failure, and lifecycle states.
- Image 10: typography/palette reference only; it does not put the room inside
  Workshop.

Claude may implement, compare, capture evidence, and make documented
non-material accessibility/truth/reflow adaptations. Claude may not create a
new visual direction. A material composition, hierarchy, dominant action,
type-family, color-language, or responsive-interaction change returns to
ChatGPT and Pete.

Final visual acceptance is on the corrected real build, not tests or mockups.
Check desktop, 390, 320, 200% zoom, reduced motion, keyboard/focus, long
content, processing, failure, recovery, and signed-in/public truth states.

The homepage currently does not present or link Opportunity Slate, so no
homepage parity change is required unless that fact changes before release.

## 13. Review requirements

The package's routing exception is binding unless Pete changes it:

- Claude Opus 5 Extra High: sole implementation writer.
- Fresh Claude Fable 5 Extra High: mandatory independent reviewer.
- Same implementation writer corrects accepted findings.
- Pete gives final visual acceptance.

Confirm the resolved model with `/model` and `/status`; do not trust a nickname
or alias. If the named model is unavailable, record the conflict and obtain
Pete's direction rather than silently substituting.

Mandatory fresh exact-SHA review questions:

- 002 and 003 migration identity, rollback, drift refusal, and owner isolation;
- OS3 evidence allowlist, citations, composition, no aggregates, and response
  attribution;
- OS4 save idempotency, version/currency truth, unknown outcomes, deletion, and
  partial snapshot refusal;
- OS6 SSRF, parser/dependency, storage, and failure-path boundaries.

Reuse old evidence only when scope, exact bytes/SHA, environment, and result
still match. Restacking or changing migration IDs invalidates affected proof.

## 14. Worktree inventory and preservation rules

- Primary checkout `C:\Users\peter\Documents\portfolio` is unrelated and
  dirty. Treat it as read-only.
- Additive schema worktree is clean at the current pushed branch before this
  handoff edit.
- OS3 app worktree has untracked evidence/output directories. Preserve them.
- OS4 worktree has nine legitimate modified files. Preserve them.
- OS5 worktree has untracked artifacts and a local branch whose remote is
  gone. Preserve it.
- `C:\Users\peter\Documents\portfolio\.wt\oppslate-os3-schema`, branch
  `work/2026-08-04-schema-revision-aware`, is a superseded dirty experiment.
  Do not merge, reset, clean, or delete it during this work.

Never use `git reset --hard`, `git clean`, or a broad checkout to make these
worktrees convenient. Create a backup ref or new clean worktree before a risky
integration.

## 15. Definition of fully finished

The page is finished only when all applicable rows below are true:

- [ ] 002 correction independently reviewed, PR-validated, squash-merged.
- [ ] Exact automatic main run verified before any fallback.
- [ ] Protected production 002 apply approved and verified.
- [ ] Generated production schema state committed.
- [ ] OS3 app reconciled to 001+002 without migration drift.
- [ ] OS3 exact-SHA review complete and accepted findings corrected.
- [ ] OS3 application merged, deployed, and live-verified.
- [ ] OS4 dirty corrections preserved and ported.
- [ ] OS4 schema expressed as additive 003 and governed-gated.
- [ ] Pete accepts final saved-details and lifecycle visuals.
- [ ] 003 applied before OS4 dependent application release.
- [ ] OS4 merged, deployed, and signed-in lifecycle live-verified.
- [ ] OS5 shared dictation wired to all four surfaces; Interview Studio
      regression green; configurable-duration copy fixed.
- [ ] OS6 upload/import passes parser, SSRF, private-storage, Python 3.14, and
      failure-state review.
- [ ] Final public and signed-in journeys pass responsive, keyboard, focus,
      reduced-motion, long-content, processing/failure/recovery checks.
- [ ] Exact deployed source, pipeline, live release marker, route headers, and
      affected capabilities recorded.
- [ ] `OWNER_TECHNICAL_COMPLETION_REPORT.md` format used for final closeout.
- [ ] Remote task branches deleted only after verified merges and preserved
      artifacts accounted for.

## 16. Communication rules

Every update should name the exact state:

- **implemented** means code exists;
- **pushed** means a remote branch contains the exact SHA;
- **reviewed** means the required reviewer assessed that exact SHA;
- **merged** means the Azure PR squash merge exists on main;
- **schema-applied** means the protected run and production ledger prove it;
- **deployed** means the exact source completed the production pipeline;
- **live** means the intended route/state was independently observed against
  that deployment.

Do not report a fixture as member data, a 200 route as the complete page, a
successful Build as deployment, or a failed/canceled schema attempt as applied
SQL.

## 17. Stop conditions

Stop and ask Pete only for a real unresolved condition:

- the authoritative main or package owner moved unexpectedly;
- another active writer owns the same mutable files;
- the protected environment plan/hash does not match 002/003;
- production ledger/object state conflicts with the report;
- an OS4 migration cannot be made additive without unsafe data movement;
- the required Claude role/model is unavailable and no exception is recorded;
- Pete requests a material visual change outside the locked authority;
- OS6 cannot meet the SSRF/parser/runtime contract with the proposed design.

Do not stop merely because the branches are old, the history is long, CI is
slow, or a separately documented limitation is already owner-accepted.

## 18. Final handoff instruction

Begin at the additive schema worktree. Fetch, verify authority, run a complete
diff review, obtain the required fresh migration review, and open the 002 PR.
That is the only correct first move. All later application work depends on it.
