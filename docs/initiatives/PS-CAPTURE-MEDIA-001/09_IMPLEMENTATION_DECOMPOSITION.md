# PS-CAPTURE-MEDIA-001 - Implementation Decomposition and Handoff

## Control-room sequence

```text
Manager architecture accepted
  -> Codex backend/security package (default off)
  -> backend manager acceptance and merge
  -> accepted Photo V1 visual-state package
  -> Claude Code protected experience package
  -> Pete/manager product acceptance
  -> release + signed-in production proof
  -> homepage Photo parity release
  -> shared-governance closeout
```

Backend and the visual-state design package may run in parallel after this
manager package is accepted. Runtime frontend implementation waits for both.

## Package 1 - PS-CAPTURE-PHOTO-BACKEND-001

- Writer: ChatGPT Codex
- Branch: `work/2026-07-19-capture-photo-backend-001`
- Base: the exact `origin/main` containing the accepted/squash-merged manager
  package
- Outcome: photo schema, storage/scan/normalization services, feature-flagged
  endpoints, lifecycle integration, infrastructure script, and complete backend
  proof; no production-visible UI
- Exit: committed, pushed, full SHA, `Pass`/`Conditional`/`Fail` completion
  report, complete diff, tests, isolated SQL/Azure evidence; no merge until
  designated-manager acceptance

### Reserved writable files

- `requirements.txt` - Pillow pin only
- `.env.example` - nonsecret Photo settings only
- `owner_routes.py` - feature-flagged Photo endpoints and generic Capture
  lifecycle dispatch only
- `services/database_service.py` - Photo procedure allowlist only
- new `services/capture_media_storage_service.py`
- new `services/photo_capture_service.py`
- optional new `services/capture_lifecycle_service.py`
- `SQL FIles/Migrations/proposed/PS-CAPTURE-MEDIA-001_photo_sources.sql`
- `SQL FIles/Migrations/proposed/PS-CAPTURE-MEDIA-001_photo_sources_rollback.sql`
- `SQL FIles/Verification/PS-CAPTURE-MEDIA-001_owner_isolation_verify.sql`
- `scripts/apply_sql_migrations.py` - exact migration registration only
- new `scripts/provision_capture_media_azure.ps1`
- new/focused Photo service, route, migration, infrastructure, database, and
  regression tests
- this initiative directory and technical completion report

No template, CSS, JavaScript, homepage, global shell, Interview Studio, Owner
Home/viewer, Story, résumé, Board, Journal, Voice table/service/UI, Moment,
Placement, publication, or shared governance edit is reserved.

### Backend entry gates

1. This manager branch is accepted and squash-merged.
2. Fetch current `origin/main`; confirm exact base and no existing remote branch.
3. Read `START_HERE.md`, `docs/AI_WORKFLOW.md`, current governance, this entire
   package, PS-CAPTURE-001/002, PS-VOICE-001, PS-MOMENT-001, and PS-PLACEMENT-001.
4. Confirm no active writer owns an overlapping shared file. If Owner Home or
   another accepted branch changed `owner_routes.py`, start from its merged main
   rather than reconciling unmerged branches.
5. Explain the Pillow and paid Azure Storage/Defender impact in the branch
   report before any production dependency install or infrastructure apply.

### Backend stop conditions

Stop for the manager on any condition listed in
`05_SECURITY_PRIVACY_LIFECYCLE.md`, any need for a UI/shared-governance file,
any change to Voice behavior, any unresolved migration conflict, any secret or
member-data requirement, or any production apply before isolated proof and
manager acceptance.

## Parallel visual package - PS-CAPTURE-PHOTO-DESIGN-001

- Manager: this package-designated ChatGPT Work/Codex manager session
- Designer/tool: manager-selected design lane; no runtime writer
- Branch: fresh `work/YYYY-MM-DD-capture-photo-design-001`
- Outcome: V1 desktop/mobile state set, copy, accessibility/truth review, and
  exact visual authority/deviation matrix under `06_EXPERIENCE_ACCESSIBILITY.md`
- Exit: Pete and designated-manager visual acceptance

It may read the accepted protected Capture implementation but does not change
runtime templates/CSS/JS/routes. It must coordinate the owner-shell outcome from
the active Owner Home/viewer gate and may not invent a second navigation layer.

## Package 2 - PS-CAPTURE-PHOTO-EXPERIENCE-001

- Writer: Claude Code
- Branch: fresh `work/YYYY-MM-DD-capture-photo-experience-001`
- Base: current `origin/main` containing the accepted backend merge
- Entry: backend merge/proof complete and Photo V1 visuals accepted
- Outcome: real protected Photo states integrated into `/app/capture`, complete
  responsive/accessibility/error evidence, flag still off until product
  acceptance

### Anticipated writable files

- `templates/owner_capture.html` - Capture-scoped Photo presentation only
- `static/css/owner-app.css` - Capture-scoped selectors only
- new `static/js/owner-capture-photo.js`
- narrowly required `owner_routes.py` rendering context only, reserved after
  rebasing from backend main
- focused Photo UI/accessibility tests
- this initiative's experience evidence and completion report

Claude must preserve real Type and Voice behavior, all disabled/future truth,
and the exact backend authorization boundary. No simulated frontend state may
substitute for server state.

## Package 3 - PS-HOME-CAPTURE-PHOTO-PARITY-001

- Writer: Claude Code after the protected product is accepted
- Branch: fresh `work/YYYY-MM-DD-home-capture-photo-parity-001`
- Outcome: update the logged-out Capture/Voice projection so Photo no longer
  appears generically `Coming later`, while keeping all upload and member data
  behind authentication
- Entry: protected Photo implementation is upstream and accepted
- Exit: visual/truth/accessibility acceptance, Azure release, and live proof

This branch is serialized with any Owner Home or Interview homepage work. It
starts from all accepted/merged upstream branches and never combines unmerged
worktrees.

## Work allowed in parallel now

- Owner Home/viewer design gate: continue independently.
- Interview Studio design/architecture gate: continue independently.
- Capture Photo backend implementation: may start after this package's manager
  acceptance/merge.
- Photo-specific visual-state design: may start after the same acceptance.

## Work that must wait

- Photo runtime frontend waits for backend merge plus visual acceptance.
- Production enablement waits for full product acceptance.
- Homepage parity waits for the accepted real protected product.
- Document and Video packages wait for Photo production closeout and a fresh
  current-state/provider/cost review.
- Shared `CURRENT_BASELINE.yaml`, `CURRENT_STATE.md`, and
  `ACTIVE_INITIATIVES.md` edits wait for an explicitly reserved governance
  closeout branch.

## Paste-ready Codex backend handoff

> You are the self-managed writer for PS-CAPTURE-PHOTO-BACKEND-001. Start only
> after PS-CAPTURE-MEDIA-001 is accepted and squash-merged. Fetch authoritative
> Azure `origin/main`, create `work/2026-07-19-capture-photo-backend-001`, and
> read every required authority/package file. Implement only the backend,
> schema, private storage/Defender, safe JPEG/PNG normalization, feature-flagged
> routes, lifecycle/export/delete integration, and evidence specified in
> `docs/initiatives/PS-CAPTURE-MEDIA-001/`. Do not edit runtime templates/CSS/JS,
> Voice internals, Home, Interview, or shared governance. Complete the full diff,
> tests, isolated SQL/Azure proof, standard completion report, commit, push, and
> return the branch plus exact full SHA with Pass/Conditional/Fail. Do not merge
> or apply production infrastructure before designated-manager acceptance.

## Manager acceptance checklist

- [x] Photo-first scope and later Document/Video order accepted (Pete,
      2026-07-19).
- [x] Separate Capture Media Storage account plus paid Defender/cost envelope
      accepted.
- [x] Backend writer/branch and file reservations accepted.
- [x] Photo V1 visual package authorized in parallel.
- [x] Runtime frontend remains blocked on backend merge and visual acceptance.
- [x] Homepage parity remains a same-wave downstream release gate.
