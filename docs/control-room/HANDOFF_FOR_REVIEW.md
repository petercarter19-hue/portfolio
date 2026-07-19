# PeerSlate Control Room — Review Handoff & Owner Guide

_Prepared for: **ChatGPT Codex** (technical review & sign-off) and **Pete**
(owner functional acceptance). Prepared by: Claude Code, 2026-07-19._

This one file has three audiences:

- **Part A** — the formal handoff facts (branch, SHA, state).
- **Part B — for Pete:** what it is, how to access it, how to sign in, how to use it.
- **Part C — for Codex:** how to review it, a concrete checklist, the questions I
  need aligned, and a sign-off table.

---

## Part A — Formal handoff

```
PeerSlate handoff

Source of truth:  origin (Azure DevOps)
Branch:           work/2026-07-19-control-room
Original review tip: 904f5697e90468fb1f221364bdc7d4fc4762b458
Integrated review:   b0db7708964d867922603b76f20df9ae1f3ac4d2
Feature commits:  09d3c19  v1: owner-only read-only dashboard
                  3f854df  v2 spec (design only)
                  60ac065  v2: live repository sync (Tier 0/1/2)
                  3c34e0f  v2.1: plain-language initiative detail pop-out
Original base:    origin/main @ fd27b2147b6a34019353d038331f4bde4f97d3b5
Merged main:      origin/main @ 296711d001c7dd0d0bc66001a29c42595a938bdb
Working tree:     unrelated untracked files remain preserved and are not part
                  of this package: SETUP_PS_GOV_001.sh and
                  docs/initiatives/PS-CAPTURE-MEDIA-001/CLAUDE_CODE_HANDOFF_INSTRUCTIONS.md.
Pushed to Azure:  yes
Tests/checks:     full suite 468 pass (1 pre-existing skip); focused
                  test_control_room (49) + test_azure_devops_read (13) green;
                  guardrails test_site_rules + test_governance_pointers (24) green.
Production status: NOT deployed. Verified locally in a real browser only.
Active writer:    RELINQUISHED by Claude Code at the review tip. Codex may review
                  (read-only) freely; to *edit* the branch, treat this as the
                  handoff. To hand back to Claude Code, return the branch + exact
                  full SHA.
```

> **Integration review complete:** current `origin/main` at `296711d` was merged
> in commit `b0db770`; the full suite and governance guardrails were rerun on
> that integrated tree. No PR has been opened and nothing has been deployed.

---

## Part B — Owner's guide (Pete): access, sign-in, and use

### B.1 What it is (one paragraph)

The Control Room is a **private, owner-only, read-only** dashboard that shows the
current state of PeerSlate — the authority (Bible/Roadmap versions, the manager),
every initiative and what it is, the decision log, delivery/pipeline facts, live
repository activity, and recent changes — all read straight from the repository
and (optionally) Azure DevOps. **Looking at it cannot change anything.** It is
not linked anywhere on the site; you reach it by typing its address, and only
you can see it.

### B.2 Where it lives

- **Production (after it is deployed):** `https://peerslate.com/owner/control-room`
- **Local (for trying it before deploy):** `http://localhost:5000/owner/control-room`

There is intentionally **no menu link** to it anywhere — that's part of keeping
it private. Bookmark the URL.

### B.3 How access works (the security, in plain terms)

The page is **fail-closed**: by default *nobody* can see it — not the public, not
other signed-in members, not even you — until you put yourself on an allowlist.
Anyone not on the allowlist gets a normal "not found" (404); the page doesn't
even reveal that it exists. The check happens on the server using your real
signed-in identity, so it can't be faked from the browser.

### B.4 Signing in (production)

1. **Deploy it first** (merge the branch → Azure pipeline deploys — see the
   pending decision in Part C.4).
2. **Add one setting** in the Azure Web App → Configuration → Application
   settings:
   `PEERSLATE_OWNER_EMAILS` = the email address you sign in to PeerSlate with
   (your Microsoft / Entra account email). You set this yourself; no one else,
   including any AI, needs the value.
3. **Sign in to PeerSlate normally** — the site's existing "Sign In" (Microsoft
   Entra). This is the same login the app already uses; the Control Room adds no
   new login of its own.
4. **Go to** `https://peerslate.com/owner/control-room`. Because your signed-in
   email matches the allowlist, you'll see the dashboard. Anyone else visiting
   that URL gets a 404.
5. **To revoke access later**, clear that app setting — the page instantly
   becomes 404 for everyone again.

(If you'd rather key access to the opaque account id than the email, there's a
second setting `PEERSLATE_OWNER_USER_KEYS`; email is the simplest to start.)

### B.5 Trying it locally (before deploy)

Run the app with these environment values (they enable a local test identity and
make that identity the owner) and open the local URL:

```
PORT=5000
PEERSLATE_ALLOW_DEV_IDENTITY=true
PEERSLATE_DEV_USER_KEY=test-user-1
PEERSLATE_OWNER_USER_KEYS=test-user-1
```

Then browse to `http://localhost:5000/owner/control-room`. (These dev values are
for local only — never set `PEERSLATE_ALLOW_DEV_IDENTITY=true` in production.)

### B.6 How to use each part

- **Overview → "Is this current?"** — three cards answer whether what's live
  matches the repo: **Production** (the deployed commit), **Repository** (what's
  on `main` right now, if live sync is on), and **Drift** (up to date / behind /
  unknown).
- **Overview stats + Authority + Attention** — counts, the manager and
  Bible/Roadmap versions, and a list of anything needing attention (gaps,
  unavailable sources).
- **Initiatives** — every package. **Click an initiative's ID** to open a
  plain-language pop-out describing what it is, what "done" means, and what it
  excludes. Filter box narrows the list.
- **Documentation register / Decisions / Traceability** — the governing
  documents, the manager decision log, and honest partial traceability
  (initiative → owner → closeout evidence, with gaps flagged).
- **Delivery health** — recorded release facts (not a live probe).
- **Repository activity** — *live* pushes, pull requests, branches, and pipeline
  runs from Azure DevOps. **Off until you configure it** (Part B.7); until then
  it honestly says "Not configured."
- **Recent changes** — the commit history.
- **Freshness chips** on each section tell you whether that section reflects the
  last deploy or a live poll. The page quietly refreshes the live parts every 90
  seconds; the **Refresh** button forces a full refresh.

### B.7 Optional: turning on live Azure DevOps sync

Repository activity and the live "Repository/Drift" cards need a read-only Azure
DevOps token. This is **optional** — everything else works without it.

1. In Azure DevOps → User settings → Personal Access Tokens, create a token
   scoped to **Code (Read)** and **Build (Read)** only, with an expiry.
2. Set these four app settings (you create/hold the token; no AI ever sees it):
   ```
   PEERSLATE_ADO_ORG_URL=https://dev.azure.com/peerslate19
   PEERSLATE_ADO_PROJECT=portfolio-site
   PEERSLATE_ADO_REPO=portfolio-site
   PEERSLATE_ADO_READ_PAT=<the token>
   ```
Leave any of them blank to keep the feature off.

---

## Part C — Reviewer's guide (Codex): how to review & sign off

### C.1 Get the branch (read-only review)

```bash
git fetch origin --prune
git switch --track origin/work/2026-07-19-control-room   # or: git switch work/2026-07-19-control-room; git pull --ff-only
git rev-parse HEAD          # note the review tip
git log --oneline origin/main..HEAD
```

### C.2 Run the checks

```bash
# full suite (ANTHROPIC_API_KEY is only needed so the app imports in CI)
ANTHROPIC_API_KEY=test-key-for-ci-only python -m unittest discover -s tests -q
# focused
python -m unittest tests.test_control_room tests.test_azure_devops_read -v
# guardrails
python -m unittest tests.test_site_rules tests.test_governance_pointers
```

Integrated review result: full suite 468 pass, 1 pre-existing skip; focused 62
pass; guardrails 24 pass. To see it render, use the local env in Part B.5.

### C.3 What to read, and the review checklist

**New files:** `owner_authorization.py`, `control_room_projection.py`,
`control_room_routes.py`, `services/azure_devops_read.py`,
`scripts/generate_control_room_snapshot.py`, `templates/control_room.html`,
`static/css/control-room.css`, `static/js/control-room.js`,
`tests/test_control_room.py`, `tests/test_azure_devops_read.py`,
`docs/control-room/*`.
**Modified (small, additive):** `app.py` (+1 import, +1 blueprint register, +6
config lines), `azure-pipelines.yml` (+1 step), `.env.example`, `.gitignore`.

Please confirm each — the deeper rationale is in
[`ARCHITECTURE.md`](ARCHITECTURE.md) and traceability in
[`REQUIREMENTS_TRACEABILITY.md`](REQUIREMENTS_TRACEABILITY.md):

- [x] **Integrates cleanly:** blueprint registered once; routes
  `/owner/control-room` and `/owner/control-room/data.json` only; no route
  collision; **no change to public routes, global nav, sitemap, or theme.**
- [x] **Read-only boundary:** only GET methods exist; `control_room_projection`
  never imports/uses `services.database_service`; `azure_devops_read` issues no
  POST/PUT/PATCH/DELETE; no form/mutation anywhere.
- [x] **Owner authorization:** `owner_required` fails closed; unauthenticated and
  authenticated-non-owner both get a bare 404 with no dashboard content; empty
  allowlist ⇒ nobody; identity is resolved only from the trusted Easy Auth
  boundary (never client-supplied fields).
- [x] **Secrets:** the Azure DevOps PAT is never logged, echoed in an error, or
  returned in JSON (see the PAT-leak tests); the generated
  `control_room_snapshot.json` is not publicly reachable; no secret names in
  client JS.
- [x] **Lane / boundary respect:** the feature diff does **not** touch backend
  Capture/Voice/Moment/Placement code, `dbo.*`/migrations, the résumé or
  Interview Studio templates, auth architecture, or global theme/nav. (It adds a
  *new* site-owner auth check; see governance note C.4.)
- [x] **Azure DevOps adapter correctness:** endpoint shapes, `api-version=7.1`,
  Basic-auth header, 5s timeouts, 60s cache + 10-min stale window, per-endpoint
  failure isolation, 401/403 handling. Sanity-check the org/project/repo names
  (`peerslate19` / `portfolio-site` / `portfolio-site`) against reality.
- [x] **Pipeline step:** the snapshot step runs after tests, before `CopyFiles`;
  it never fails the build; the snapshot ships in the artifact; `.git` exclusion
  is expected and handled (runtime falls back gracefully).
- [x] **Truthfulness:** unknown/unavailable/stale/partial states are honest; no
  manufactured green; drift returns `unknown` rather than guessing when data is
  missing or the deployed commit is outside the fetched window.
- [x] **Accessibility (detail pop-out & page):** dialog focus move/trap/restore,
  Escape/backdrop close, status conveyed by text+glyph (not colour alone),
  reduced-motion honored, table semantics.
- [x] **No runtime AI:** the initiative detail is parsed source prose, not a
  model-generated summary.

### C.4 Governance context & the pending decision (please weigh in)

- This was built under an **explicit one-session owner override** of the Claude
  Code "public-experience / no-auth" lane, because a genuine owner-only surface
  requires a site-owner auth check that lane normally excludes.
- The **governance authority files were intentionally NOT modified**
  (`CURRENT_BASELINE.yaml` `active_packages`, `ACTIVE_INITIATIVES.md`). Registering
  this as an initiative (proposed id `PS-CONTROL-ROOM-001`) is the designated
  session manager's call. Guardrail suites are green precisely because nothing
  in the authority chain was touched.
- **Pending owner/manager decision:** (a) merge as-is under the owner override via
  an Azure PR, or (b) have the designated session manager register
  `PS-CONTROL-ROOM-001` (lane, file reservation) first. Codex recommends (b), or
  an explicit recorded exception. Current `origin/main @ 296711d` is already
  merged in review commit `b0db770`.
- **Manager remains the formal merge-readiness/release authority.** This Codex
  review is the technical sign-off the owner asked for; it complements, not
  replaces, the manager's step.

### C.5 Questions I'd like aligned (please answer in your sign-off)

1. **Route convention:** is `/owner/control-room` the right home, or should an
   owner area settle on a different prefix before this is cemented?
2. **Owner resolution:** env-based allowlist now — acceptable long-term, or should
   it graduate to a DB `user_role` when an admin model exists?
3. **Tier 1 auth:** read-only PAT for Azure DevOps — fine, or would you prefer a
   managed-identity/OAuth approach before enabling it in production?
4. **Anything that would fight the rest of the site** at merge that these tests
   wouldn't catch?

### C.6 Sign-off record

Codex review answers:

1. `/owner/control-room` is the right convention. It keeps site-owner
   operations separate from member-owned `/app/*` routes and adds no public
   navigation contract.
2. The environment allowlist is acceptable for bootstrap. Prefer the opaque
   `user_key` in production when it is available; graduate to a server-enforced
   database role/entitlement only when PeerSlate introduces a real admin model.
3. A least-privilege, expiring PAT with Code (Read) + Build (Read) is acceptable
   for v1. Managed identity/OAuth is a desirable later replacement, not a
   pre-deployment blocker for this read-only optional tier.
4. The complete integrated diff found no collision with public/member routes.
   Two merge-time defects were corrected: portable manager-schema rendering and
   mobile horizontal overflow. HTTPS-only Azure endpoints/links and concurrent
   cold reads were also added as security/availability hardening.

| Reviewer / role | Result | Notes / conditions | Date |
|---|---|---|---|
| ChatGPT Codex — technical & integration review | **Pass** | Integrated with `origin/main @ 296711d`; two defects corrected; 468-test full suite, focused tests, guardrails, route smoke checks, and responsive browser checks pass. This is not merge-readiness or visual acceptance. | 2026-07-19 |
| ChatGPT Codex — security (auth, read-only, secrets) | **Pass** | No open high/medium findings. Keep owner allowlists server-configured; prefer opaque user key; PAT remains optional, server-side, read-only, expiring, and never committed. Live production auth/PAT remains unproved until release. See `SECURITY_REVIEW.md`. | 2026-07-19 |
| Pete — owner functional acceptance (I can access & use it) |  |  |  |
| Designated session manager — merge-readiness (governance path chosen) |  |  |  |

---

## Part D — Known limitations (don't infer past these)

- **Not deployed.** No production or production-URL verification yet.
- **Tier 1 live sync not exercised against real Azure DevOps** — its request /
  cache / failure / credential paths are proven with mocked HTTP (11 tests), not
  a live call. First real use is the first true end-to-end proof.
- **The build-time snapshot** has been generated locally with fabricated
  `BUILD_*` values, not yet produced by a real Azure Pipelines run; so
  production "Recent changes" and the deployed-commit card are unproven until the
  first deploy.
- **Drift** compares against the 30 most-recent `main` commits; a deployment
  older than that window reports `unknown` (by design, never a guess).
- Everything else (auth boundary, read-only boundary, truthfulness states,
  detail pop-out, accessibility) is covered by the 62 focused tests and local
  real-browser verification.
