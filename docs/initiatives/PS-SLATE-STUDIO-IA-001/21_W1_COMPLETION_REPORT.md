# PS-WORKSHOP-001 Slice W1 — Owner technical completion report 

**Initiative:** PS-SLATE-STUDIO-IA-001 / runtime package PS-WORKSHOP-001
**Writer lanes:** Claude Sonnet 5 (implementation), Claude Fable 5 (architecture + disclosed finish/micro fixes), Claude Opus 5 (independent review + focused recheck)
**Owner:** Pete Carter

## Outcome

Workshop slice W1 is implemented, independently reviewed, corrected, and released: the private member knowledge library (My Information) with real search/filtering, direct entry (compose → review → explicit Save privately → confirmation), edit/archive/restore/delete, honest empty/unavailable/truncation states, owner-isolated storage proven at SQL, service, and route layers, and the owner-approved depth treatment. `Work on Something` (AI mode) is not in this slice; its tab renders an honest Coming later pill pending the round-3 visual lock.

## Branch and versions

- Branch: `work/2026-08-01-workshop-architecture` from `origin/main` at `2494aa73ed95bfbe97d8cf42f712b9929759e0b2`
- Final reviewed source tip: `4e0e17a3dec7e65e0940ac2e24ada1d83dca0d9a`
- Azure PR: 224, squash-merged at `174b1df6b57acac4985eb367605e5d0b97ab51fc`
- Pipeline: 20260802.1 — completed, succeeded, for exactly the merge commit

## Owner decisions honored (doc 16 + doc 20)

Approved wording canonical, original retained, no AI-attribution labels (D1, with the explicit save-consent step); AI use always on with no member-facing toggle — no permission column/procedure/UI anywhere (doc 20 §6a); PeerSlate creates no résumés — destinations render `Use this elsewhere — Coming later` (D6/A2); route `/app/workshop` with `/app` convergence deferred (A1); Workshop next to Interview Studio in nav, flag-gated, signed-in only; depth/texture finish at the owner-approved round-3 dial, chips deliberately flat.

## Verification

- Full suite: 1268 passed, 3 skipped (from 1088 at slice start; +178 Workshop tests).
- Independent Opus review: Conditional with 2 Blockers, 3 Majors, 6 Minors, 15 test gaps — all corrected; focused Conditional; both required truth fixes applied exactly as specified with pinning tests at 4e0e17a; optional SQL-side filtering deferred by design.
- Live staging rehearsal (peerslate-staging): apply → verify → rollback → reapply GREEN, 3× stable; three genuine engine defects found and fixed (nested INSERT-EXEC, INSERT-EXEC result-shape, rollback guard false positive). Owner-isolation verifier: 51 THROW assertions incl. forged-key canaries on all seven procedures.
- Production migration: applied 2026-08-02 via `scripts/apply_sql_migrations.py --apply --migration PS-WORKSHOP-001 --env-file` (ledger row present; three tables and seven procedures confirmed in sys catalogs). The 51-assertion owner-isolation verifier ran against production and returned verified=true with full synthetic rollback. Rollback file present and rehearsed on staging.
- Production smoke: `/` 200, `/interview-studio` 200, `/app/workshop` neutral 404 flag-off, then post-enablement redirect-to-sign-in verified.
- Visual: Pete accepted the first-page checkpoint (2026-08-01), the corrected set, and the round-3 depth; final ten-image evidence set in owner's records (iCloud Claude/Workshop Final Look 2026-08-01). Documented adaptations: owner-amended AI-use removals; chips wrap at 390px at readable size; disclosure panel open; title-only search (list read carries no body text by design).

## Release state

- Merged: PR 224 at `174b1df`; deployed by pipeline 20260802.1; migration applied and verified on production 2026-08-02.
- **Enablement:** `PEERSLATE_WORKSHOP_ENABLED=true` set on App Service `peerslate-pete` on 2026-08-02 per Pete's explicit decision (friends review immediately), with an explicit App Service restart. Live verification: signed-out `/app/workshop` returns 302 to `/auth/sign-in?return_to=/app/workshop`; homepage 200; `/healthz` ok on the new release identity. Pre-enable smoke: `/` 200, `/interview-studio` 200, `/app/workshop` neutral 404.

## Honest limitations / next steps

- Search matches titles only (list contract carries no body text); wording-content search is a later, deliberate contract change if wanted.
- No pagination past 200 items; truthful "Showing 200 of N" footer instead. Revisit if any member approaches the cap.
- `Work on Something`, Spark, voice capture, and destination writes are slices W2–W4; W2 gated on the ChatGPT round-3 opening lock (in progress).
- Pre-existing site issues out of scope, tracked separately: mobile platform-header crowding on /app-family pages; stale Capture verifier (chip task_88a80710); site-wide AI key boot dependency (recorded deferral).
- The dev-preview seam requires two flags and shows an unmistakable banner; never set PEERSLATE_WORKSHOP_DEV_FIXTURE in production.

## Governance updates in this release

- `CURRENT_BASELINE.yaml`: PS-SLATE-STUDIO-IA-001 status advanced (W1 released + enabled; W2 gated on round-3 visual lock); note added under active_packages.
- `docs/AI_MODEL_AND_ROLE_ROUTING.md`: Claude independent reviewer row Opus 4.8 → Opus 5 (owner decision, doc 16 §5).
- Doc 20 §6c: release + enablement record.
