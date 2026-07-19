# PeerSlate Completion & Handoff Report — Owner Control Room

## A. Status
- Package: Owner Control Room, **v1 + v2 (live repository sync)** (owner-override build; **not** a manager-assigned initiative yet — proposed id `PS-CONTROL-ROOM-001`)
- Status: Technical/security/integration review passed; release readiness **Conditional**; not deployed
- Branch and commit: `work/2026-07-19-control-room`; current `origin/main @ 296711d001c7dd0d0bc66001a29c42595a938bdb` merged and review corrections committed at `b0db7708964d867922603b76f20df9ae1f3ac4d2`. The final documentation commit and pushed branch tip are reported in the handoff response.
- PR / pipeline / environment: none opened yet — awaiting owner/manager decision (section I)
- Production state: not deployed; verified locally on `http://localhost:5000`
- Visual authority and status: Not Applicable (internal owner tool; no approved visual authority exists for it). Deep Navy Gold palette reused.
- Pete / designated session manager visual acceptance: Not started
- Designated session manager: package-designated portable session manager; not yet assigned for this unregistered package
- Manager handoff status and next receiver: pending governance-path and merge-readiness decision
- Lane owner and self-managed authority: Claude Code relinquished at `904f5697e90468fb1f221364bdc7d4fc4762b458`; Codex completed the requested review
- Self-certification: **Conditional** — technical/security/integration pass; production, owner functional acceptance, visual acceptance, and governance registration remain open
- Complete-diff review: **Issues corrected** — manager-schema compatibility, mobile overflow, unsafe external-link schemes, and sequential cold Azure reads
- Acceptance requested: owner functional acceptance, designated-manager governance/merge readiness, then release verification

## B. What changed technically
- **New site-owner authorization** (`owner_authorization.py`): fail-closed check that resolves identity only via `identity.get_optional_identity()` (trusted Easy Auth boundary) and compares it to operator-configured allowlists `PEERSLATE_OWNER_EMAILS` / `PEERSLATE_OWNER_USER_KEYS`. `owner_required` decorator returns a bare `404` to any non-owner (unauthenticated, authenticated non-owner, or identity-storage failure). No prior site-owner concept existed; the existing `/app/*` routes are per-member self-ownership.
- **Read-only projection layer** (`control_room_projection.py`): deterministic providers that derive the dashboard from repo files — `CURRENT_BASELINE.yaml` (parsed by a small dependency-free YAML-subset reader), `docs/initiatives/<ID>/`, `DECISIONS.md`, and local `git log`. No DB, no secrets, no runtime AI, no request-derived file paths. Every fact carries source + timestamp + status.
- **Routes** (`control_room_routes.py`): `GET /owner/control-room` (server-rendered) and `GET /owner/control-room/data.json`, both `@owner_required`, both hardened with `X-Robots-Tag: noindex` (JSON also `Cache-Control: no-store, private`).
- **UI**: standalone `templates/control_room.html` + scoped `static/css/control-room.css` (Deep Navy Gold, light/dark/reduced-motion) + read-only `static/js/control-room.js` (table filter, refresh). Does not extend `base.html`, so no public chrome leaks in and no public page can regress.
- **Wiring**: `app.py` +1 import, +1 blueprint registration, +2 config lines. `.env.example` documents the two new owner vars.
- **Tests**: `tests/test_control_room.py` (20) — authorization, read-only, source truthfulness, non-exposure.
- **Migrations / infrastructure / rollback**: none. Rollback = revert the branch; there is no schema or data change.

### v2 — Live Repository Sync (same day, per `docs/control-room/V2_LIVE_SYNC_SPEC.md`)

Closes the "how do I know this is current?" gap identified after v1 shipped:
governance/initiative sections already refreshed on every deploy, but commit
history was unavailable in production, and pushes/PRs/pipeline runs between
deploys were invisible.

- **Tier 0 — build-time snapshot** (`scripts/generate_control_room_snapshot.py`,
  new): captures 30 recent commits + build id/SHA/branch into
  `control_room_snapshot.json` before `azure-pipelines.yml`'s `CopyFiles` step
  strips `.git`. Dependency-free, never fails the build. New `build_identity()`
  provider reports the deployed commit in prod, the local `git HEAD` in dev —
  the two are never conflated (`environment: production_build` vs
  `local_development`). `recent_changes()` now prefers live git, falls back to
  the snapshot, and only then reports unavailable.
- **Tier 1 — read-only Azure DevOps adapter** (`services/azure_devops_read.py`,
  new): stdlib-only (`urllib`), five GET endpoints (branch refs, main commits,
  active PRs, completed PRs, pipeline runs). Configured by four optional env
  vars; any one missing ⇒ truthful `not_configured`. 60s server cache, 10-minute
  stale-serve window beyond that, then `unavailable`. One endpoint failing
  never blanks the others. A 401/403 is reported as "credential invalid" with
  no body/PAT leak anywhere (tested). New `repository_activity()` provider and
  `_compute_drift()` (deployed SHA vs. live `main` tip → up_to_date / behind
  [with pending-commit list] / unknown — never guessed).
- **UI**: new "Is this current?" status band (Production / Repository / Drift
  cards) atop Overview; new "Repository activity" section (active/completed
  PRs, branches, pipeline runs, each linked to Azure DevOps); freshness chips
  ("As of deploy · build N" / "Local development" / "Live · fetched HH:MM:SS" /
  "Stale" / "Not configured") on every section header; 90s client-side poll
  that partially re-renders only the status band + Repository activity
  (pauses when the tab is hidden, resumes + refreshes immediately when it
  isn't); client-side-only "New" markers on rows newer than the visitor's last
  visit (`localStorage`, no server state).
- **Wiring**: `app.py` +4 config lines (`PEERSLATE_ADO_ORG_URL/PROJECT/REPO/
  READ_PAT`). `.env.example` documents them. `.gitignore` +1 entry (the
  generated snapshot file, never committed). `azure-pipelines.yml` +1 step.
- **Tests**: `tests/test_control_room.py` grew from 20 → 40 (snapshot fallback,
  drift, Tier 1 wiring/overview-warning integration). New
  `tests/test_azure_devops_read.py` (11) — config, mocked fetch, per-endpoint
  isolation, caching/staleness, credential handling, PAT-never-leaks.
- **Migrations / infrastructure / rollback**: none. The pipeline step is
  additive and self-contained; reverting the branch removes it cleanly. Tier 1
  requires no infrastructure beyond the PAT Pete creates himself.

### v2.1 — Initiative detail pop-out (same day)

- **Plain-language detail on click.** Selecting any initiative's ID opens an
  accessible modal describing what that initiative *is*: its intended outcome,
  what "done" means, and what it deliberately excludes. New
  `control_room_projection.initiative_details()` + `_parse_initiative_detail()`
  parse each README into a headline summary (its Outcome/Purpose section) plus
  structured sections, skipping the pure-plumbing "Writable files" and
  "Required reading" sections. Content is the initiative's own recorded prose,
  escaped and structured — **no runtime AI paraphrase** (the dashboard's
  determinism rule). Missing README → the pop-out says so and links the folder.
- **Read-only + lean.** The detail is rendered once into a hidden server-side
  store the modal reads from — no detail endpoint, so no request input ever
  becomes a file path. It is passed to the template only, kept out of
  `build_projection()`/`data.json` so the 90s poll payload stays lean.
- **Accessible dialog.** Body-level `role="dialog"` (layers above the sticky
  topbar), focus moves in, Tab is trapped, Escape/backdrop/close all dismiss,
  focus returns to the row button, body scroll locks, reduced-motion honored.
- **Tests**: `tests/test_control_room.py` 40 → 48 (parser summary/sections/skip
  behavior, missing-README grace, page contains modal + detail store, detail
  absent from `data.json`). Integrated full suite 468 pass (1 pre-existing skip).

## C. What this means in plain English
You now have one private page that shows the current state of PeerSlate —
who the manager is, which Bible/Roadmap versions are authoritative, what's
active, what's completed, what's on hold, the decision log, and where evidence
is missing — all read straight from the repository's own governance files. **v2
adds the "is this actually current?" answer**: a status band shows what's
deployed, what's on `main` right now (if you turn on the optional live Azure
DevOps sync), and whether those two agree — plus a live feed of pushes, pull
requests, and pipeline runs that updates on its own every 90 seconds. It is
still **look-only**: opening it cannot change, approve, or deploy anything.
Only you (an allow-listed owner) can see it; everyone else gets a plain "not
found."

## D. What the website or member can do now
- An allow-listed owner can open `/owner/control-room` and read Overview,
  Initiatives, Documentation Register, Decisions, Traceability, Delivery Health,
  Repository Activity, and Recent Changes, each with source links and
  timestamps.
- **v2:** the Overview's status band answers "is this current?" at a glance
  (deployed commit, live `main` tip, drift between them). Every section header
  now shows which freshness tier it reflects. The page quietly refreshes the
  live sections every 90 seconds without a full reload, and marks anything
  newer than your last visit with a small "New" tag.
- Read-only interactions only: navigate, filter tables, open sources, refresh
  (manual or automatic).
- Unavailable/partial/unknown states are shown honestly (e.g. Delivery "live
  integration not configured"; completed packages lacking a closeout report
  flagged as gaps; Repository Activity says exactly which four settings are
  missing when the optional live sync isn't turned on).
- Nothing changed for members or public pages. No new nav, theme, or auth
  behavior is exposed publicly. The live Azure DevOps sync is **off by
  default** — it activates only once you set all four `PEERSLATE_ADO_*`
  settings yourself.

## E. How this connects to PeerSlate
It is an internal operations lens over the governance system (`CURRENT_BASELINE
.yaml`, `ACTIVE_INITIATIVES.md`, `DECISIONS.md`, `docs/initiatives/*`) plus,
**in v2**, the Azure DevOps repository itself (branches, PRs, pipeline runs) —
the delivery mechanics behind that same governance record. It reads the same
authority chain and the same Azure DevOps project the team already uses, so it
never duplicates or forks a fact. It touches none of the product:
Capture-to-Moment, Voice, résumé, Interview Studio, the database, and the
private/public boundary are all unchanged. It reuses the approved Deep Navy
Gold design foundation.

## F. Verification and validation
- **Automated:** `tests/test_control_room.py` — 49/49 pass.
  `tests/test_azure_devops_read.py` — 13/13 pass. Full suite:
  `python -m unittest discover -s tests -q` — 468 pass, 1 pre-existing skip. Both
  guardrail suites (`test_site_rules`, `test_governance_pointers`) green.
- **v2.1 detail pop-out (live, Playwright):** clicking an initiative ID opens
  the modal with real README-derived content (Outcome summary + Assignment /
  Owner-visible slice / Acceptance criteria sections; Writable-files skipped),
  focus moves to the close button, Escape closes and restores focus to the
  trigger, no console errors. Verified in desktop light, desktop dark, and
  mobile (375–390px) — modal is responsive and on-brand in all three.
- **Local behavior (dev server, port 5000):**
  - Owner (dev identity allow-listed): page + `data.json` return 200; JSON has
    `read_only: true`, `X-Robots-Tag: noindex`, `Cache-Control: no-store,
    private`; real data (Package-designated session manager, Bible v2.5 / Roadmap v2.4, the
    two active packages) rendered.
  - Fail-closed live check (empty allowlist): both endpoints return `404`
    with no dashboard content in the body.
  - Non-owner / unauthenticated: covered by tests (bare 404, no leak).
  - **v2 live checks:** status band renders Production (local dev commit +
    subject), Repository ("Not configured" + setup link), Drift ("Unknown" +
    explanation) — the honest default state with Tier 1 off. `data.json`
    confirmed to include `build_identity` and `repository_activity` (with
    `.drift`) with the exact shape the client JS expects. No console errors on
    load. Tier 1's mocked success/failure/cache/credential paths are covered
    by the 11 adapter tests rather than a live PAT (see Known gaps).
- **Visual evidence:** desktop-light, mobile-light, and desktop-dark full-page
  screenshots re-captured after v2 (status band, Repository activity section,
  freshness chips all visible; Deep Navy Gold preserved; no console errors).
- **Honest limits:** No production deployment or production-URL verification has
  been done. "Recent changes" prefers local `git`, falls back to the v2 build
  snapshot; the snapshot itself has only been generated and inspected manually
  (with fabricated `BUILD_*` env values), not yet produced by a real Azure
  Pipelines run. No real Azure DevOps PAT was available in this environment, so
  Tier 1's live-fetch paths are verified by mocked tests, not a real API call.
  No real-member validation (owner-only internal tool).

## G. Known gaps, risks, and exclusions
- **Governance authority not modified.** The dashboard is not registered in
  `CURRENT_BASELINE.yaml` `active_packages` or `ACTIVE_INITIATIVES.md`; that is
  the manager's decision, and the guardrail intentionally pins the active set.
- **Lane note.** This crosses the current "public experience / no auth" Claude
  Code lane; it was built under an explicit one-session owner override.
- **Delivery Health (baseline-recorded facts) is separate from Repository
  Activity (v2's live Azure DevOps feed)** — the former stays off by design
  (no credentials); the latter is real but **optional and off until Pete
  configures it**.
- **v2's live sync has not been exercised against real Azure DevOps.** No PAT
  was created or handled in this session (by design — only Pete creates it).
  The adapter's request/response handling, caching, and failure paths are
  proven with mocked HTTP responses (11 tests), not a live call. First real use
  will be the first genuine end-to-end proof of the Tier 1 wiring.
- **The build-time snapshot has not been produced by a real pipeline run.**
  The generator was exercised locally (real git history parses correctly) and
  with fabricated `BUILD_BUILDID`/`BUILD_SOURCEVERSION`/`BUILD_SOURCEBRANCH`
  values; the actual Azure Pipelines step (`azure-pipelines.yml`) has not yet
  executed in CI.
- **Recent Changes** unavailable in production until the first deploy produces
  a real snapshot (or, from then on, uses it automatically).
- **Drift detection is bounded by the fetched commit window** (30 most-recent
  `main` commits). A deployed build older than that window correctly reports
  `unknown` rather than guessing — this is intentional, not a bug, but means
  very stale deployments won't get a "behind by N" count, only "unknown."
- Do not infer production status from this page; it reflects recorded and
  polled facts, not a guarantee.
- Pete owner functional acceptance and designated-manager visual/product
  acceptance have not occurred. The internal-tool visual authority remains N/A,
  but the repository visual-integrity gate still requires those explicit
  acceptance records before merge.

## H. Clear next step
Have the designated session manager register `PS-CONTROL-ROOM-001` (or record an
explicit governance exception), then collect Pete's functional acceptance and
the required manager visual/product acceptance before opening the Azure PR.
That establishes the missing authority and acceptance evidence without changing
the technically reviewed implementation. Turning on Tier 1 (the four
`PEERSLATE_ADO_*` settings) is a separate, optional follow-up Pete can do at
any point after deploy — nothing about deployment depends on it.

## I. What Pete needs to do or decide
1. Decide governance path (H): the recommended path is to register
   `PS-CONTROL-ROOM-001`; otherwise record an explicit exception before PR.
2. To use it after deploy, set `PEERSLATE_OWNER_EMAILS` (your sign-in email) in
   the Azure Web App application settings. I never see or handle that value.
3. **Optional (v2):** to turn on live Repository Activity/Drift, create a PAT
   in Azure DevOps scoped to **Code (Read)** and **Build (Read)** only, with an
   expiry, and set `PEERSLATE_ADO_ORG_URL`, `PEERSLATE_ADO_PROJECT`,
   `PEERSLATE_ADO_REPO`, `PEERSLATE_ADO_READ_PAT` in the Web App settings. The
   dashboard is fully useful without this step.
4. No cleanup is part of this package. The unrelated untracked
   `SETUP_PS_GOV_001.sh` and
   `docs/initiatives/PS-CAPTURE-MEDIA-001/CLAUDE_CODE_HANDOFF_INSTRUCTIONS.md`
   remain preserved and uncommitted.
