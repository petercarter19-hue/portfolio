# PeerSlate Control Room — Architecture, Data Sources, and Security

_Owner-only, read-only observational dashboard. v1 built 2026-07-19 on branch
`work/2026-07-19-control-room` from `origin/main @ fd27b21`. v2 (live
repository sync) added the same day per
[`V2_LIVE_SYNC_SPEC.md`](V2_LIVE_SYNC_SPEC.md); this document is updated in
place rather than forked so it always describes the current implementation.
Codex integrated `origin/main @ 296711d` and completed technical/security review
at `b0db770`._

> **Scope and authority note.** This surface was built under an explicit owner
> instruction to supersede the standing lane assignment for one session. It is
> **not** (yet) a manager-assigned initiative package. It deliberately does not
> modify the governance authority chain (`docs/governance/*`,
> `ACTIVE_INITIATIVES.md`, `CURRENT_BASELINE.yaml`). If it is to become a
> tracked initiative (e.g. `PS-CONTROL-ROOM-001`), that assignment is
> the designated session manager's to record. See the Completion Report, section I.

## 1. What it is

`/owner/control-room` is a single secure page that projects PeerSlate's
documented and delivered state from authoritative repository files. It is a
**projection of project truth**, not a new authority: viewing it cannot approve,
edit, assign, deploy, or change anything. There are no write endpoints.

## 2. Repository discovery (what the design is grounded in)

| Concern | Finding |
|---|---|
| Framework | Flask 3 + Jinja2, server-rendered. `app.py` registers blueprints. |
| Auth | Azure App Service "Easy Auth" (Entra). `identity.py` resolves an authenticated member to an opaque `user_key` behind `PEERSLATE_TRUST_EASYAUTH_HEADERS`; fail-closed. |
| Existing "owner" routes | `owner_routes.py` / `auth_routes.py` (`/app`, `/app/settings`, `/app/capture`) are **per-member self-ownership** — every signed-in member sees their own data. **No site-owner (Pete-only) authorization existed.** |
| Design system | Deep Navy Gold. Tokens + `body[data-theme]` in `static/css/style.css`; Inter (UI) + Newsreader (editorial). |
| Governance sources | `docs/governance/CURRENT_BASELINE.yaml` (+ `CURRENT_STATE.md`, `ACTIVE_INITIATIVES.md`, `DECISIONS.md`, `DOCUMENT_CONTROL.md`), and `docs/initiatives/<ID>/`. |
| Deployment | `azure-pipelines.yml` ships `**/*` except `.git/**` — so `docs/**` **is** present at runtime, but **git history is not**. |
| Dependencies | PyYAML is **not** a dependency. Sitemap is an explicit allowlist. An app-wide `after_request` (`prevent_stale_html`) sets `Cache-Control: no-cache, must-revalidate` on HTML. |

### Refinements made to the directive (evidence-based)

1. **404, not redirect, for non-owners.** The directive says an unauthenticated
   visitor should get "normal safe unauthenticated behavior." For a hidden
   owner surface, redirecting to sign-in would confirm the route exists. Both
   unauthenticated and authenticated-non-owner receive a bare `404`, so the
   route is indistinguishable from a non-existent path. The server-side check —
   not the obscurity — is the control.
2. **No new dependency.** Rather than add PyYAML, a small purpose-built YAML
   subset reader parses the (stable) governance baseline.
3. **Standalone template, not `base.html`.** The owner tool does not inherit the
   public nav, search, "Ask Pete AI" chatbot, or profile band, and its CSS is a
   separate file — so it cannot leak public chrome and cannot regress a public
   page. It reuses the approved Deep Navy Gold palette and fonts.
4. **Recent Changes degrades honestly.** Because production artifacts exclude
   `.git`, the commit timeline is shown where the repo is present and renders a
   truthful "unavailable" state otherwise.

## 3. Components

| File | Role |
|---|---|
| `owner_authorization.py` | Fail-closed site-owner check + `owner_required` decorator. Resolves identity only from the trusted auth boundary; compares against env allowlists. |
| `control_room_projection.py` | Read-only providers that derive the projection from repo files plus Tiers 0/1. No DB, no secrets, no AI, no request-derived file paths. **(v2.1)** + `initiative_details()`: parses each README into a plain-language detail view (summary from Outcome/Purpose, structured sections, skips Writable-files/Required-reading plumbing) for the pop-out. |
| `control_room_routes.py` | `control_room` blueprint: `GET /owner/control-room` (server-rendered) and `GET /owner/control-room/data.json`. Both `@owner_required`. |
| `scripts/generate_control_room_snapshot.py` | **(v2)** Tier 0: pipeline step that captures git history + build identity into `control_room_snapshot.json` before `.git` is stripped from the deployment artifact. Dependency-free; never fails the build. |
| `services/azure_devops_read.py` | **(v2)** Tier 1: read-only Azure DevOps REST adapter (stdlib `urllib` only). Branch tips, main commits, active/completed PRs, pipeline runs. 60s in-process TTL cache; fails closed to `not_configured`/`unavailable`/`stale`. |
| `templates/control_room.html` | Standalone Deep Navy Gold, accessible, responsive UI. **(v2)** + status band, Repository activity section, freshness chips, "New" markers. **(v2.1)** + per-initiative hidden detail store and a body-level detail dialog. |
| `static/css/control-room.css` | Scoped `.cr-*` styles; light-first + dark + reduced-motion. **(v2)** + status band, freshness chip, activity-list, new-pill styles. **(v2.1)** + row-button, modal, and detail-typography styles. |
| `static/js/control-room.js` | Read-only progressive enhancement: table filter + refresh. **(v2)** + 90s auto-refresh (partial re-render of the status band and Repository activity only; pauses when the tab is hidden) and client-side "since you last looked" highlighting via `localStorage`. **(v2.1)** + accessible detail-modal controller (focus move/trap/restore, Escape/backdrop close). |
| `app.py` | +2 owner-allowlist config lines, +4 Tier 1 config lines, +1 blueprint registration, +1 import. |
| `.env.example` | Documents `PEERSLATE_OWNER_EMAILS` / `PEERSLATE_OWNER_USER_KEYS` and **(v2)** the four `PEERSLATE_ADO_*` Tier 1 variables. |
| `.gitignore` | **(v2)** Ignores the generated `control_room_snapshot.json` (never committed; regenerated every build). |
| `azure-pipelines.yml` | **(v2)** +1 step: "Generate Control Room snapshot", after tests, before `CopyFiles`. |

## 4. Data-source map

Every provider returns data plus a source path, a best-known timestamp, and a
status (`ok` / `unknown` / `unavailable` / `partial`). Missing sources degrade;
they never manufacture a favourable status.

| Section | Authoritative source | Derived fields | Failure behavior |
|---|---|---|---|
| Overview | `CURRENT_BASELINE.yaml` + initiatives scan | counts, manager, Bible/Roadmap versions, production URL, next gate, attention warnings | Baseline unreadable → whole section "unavailable" |
| Initiatives | `docs/initiatives/<ID>/` + baseline lists | id, title, lifecycle state, owner/lane, closeout-report presence, declared/mtime date | Dir missing → "unavailable"; unreadable README → per-row "unknown" |
| Initiative detail **(v2.1)** | each `docs/initiatives/<ID>/README.md` | plain-language summary (Outcome/Purpose) + structured sections (Assignment, Acceptance criteria, scope, …); Writable-files/Required-reading skipped | No README → the pop-out says so and links the folder; content is escaped source prose, never AI-generated |
| Documentation register | baseline `governing_documents` + named records + `superseded_documents` | title, type, authority, version, updated, path | Missing file → row status "unavailable" (never silent "ok") |
| Decisions | `docs/governance/DECISIONS.md` | date, title, bullets | File missing → "unavailable" |
| Traceability | initiatives + baseline | active-package links; gaps (completed-without-report, package-without-README) | Labelled **partial** by design |
| Delivery health | baseline `authority.*` | last recorded release commit/pipeline, production URL | Live Azure DevOps integration **not configured** → explicit "unavailable" + note. Never claims live green. |
| Recent changes | **(v2)** live Git → build snapshot → unavailable, in that preference order | commit, date, author, subject; `tier` (`live_git` / `build_snapshot`) | No `.git` **and** no snapshot → truthful "unavailable", naming both missing sources |
| Build identity **(v2)** | snapshot `build.*`/`commits[0]` (prod) or local `git rev-parse HEAD` (dev) | deployed/local commit, subject, build id, source branch | Neither available → "unavailable", `environment: unknown` |
| Repository activity **(v2)** | live Azure DevOps REST (branches, main commits, PRs, pipeline runs) | per-collection items + per-collection status | Any one endpoint fails → that collection empty, others unaffected. All fail → cached `stale` (≤10 min) or `unavailable`. Unconfigured → `not_configured` naming the 4 env vars. |
| Deployment drift **(v2)** | Build identity × Repository activity (`main` tip) | `up_to_date` / `behind` (+ pending commit list) / `unknown` | Either side missing, or the deployed SHA isn't in the fetched commit window → `unknown` — never guessed |

Distinctions are preserved: a completed package is not shown as deployed; a
merged PR is not shown as production-verified; the presence of a test/report
file is not shown as a pass. Contradiction/gap signals surface as informational
warnings, never silently resolved.

### 4a. Freshness tiers (v2)

Every section now states which of three cadences it reflects, shown as a small
chip next to its heading:

1. **As of deploy** — Overview, Initiatives, Documents, Decisions,
   Traceability: read from whatever files this running process has, so they
   refresh whenever a new build is deployed (or, in local development,
   immediately on the next request — labelled "Local development" rather than
   "As of deploy" so the two are never confused).
2. **Live** — Repository activity: polled from Azure DevOps every 60s
   (server-side cache) and every 90s from the browser, independent of any
   deploy.
3. **Recent changes** picks whichever of live git / the build snapshot is
   available and says which one.

The Overview's **status band** ("Is this current?") is the single place that
answers the freshness question at a glance: **Production** (what's deployed,
from Tier 0), **Repository** (what's on `main` right now, from Tier 1), and
**Drift** (do those two agree).

## 5. Security model

- **Authentication** reuses `identity.get_optional_identity()` — resolved only
  from the trusted Easy Auth boundary, never from client-supplied id/email/role.
- **Authorization** is a new fail-closed site-owner check
  (`owner_authorization.is_owner`). Owner iff the server-resolved identity
  matches `PEERSLATE_OWNER_EMAILS` (case-insensitive) or
  `PEERSLATE_OWNER_USER_KEYS` (exact). **Both empty ⇒ nobody is owner.**
- **Independent endpoint protection.** `owner_required` guards the page and the
  data endpoint separately; protecting the page alone is insufficient.
- **No confirmation of existence.** Non-owners get a bare `404`; unauthorized
  responses contain no dashboard records or document excerpts.
- **No secrets.** This build reads no tokens/connection strings and adds no
  delivery-platform credentials. Owner values are operator-configured env vars.
- **No traversal / SSRF.** No request input is ever turned into a filesystem
  path; all reads target fixed, code-owned roots. Source "links" are display
  strings to the Azure repo web UI.
- **Injection.** All repo-derived content renders through Jinja autoescaping;
  no `|safe` is applied to file content.
- **Defense in depth.** `X-Robots-Tag: noindex, nofollow, noarchive` on both
  responses; `Cache-Control: no-store, private` on the JSON endpoint (the HTML
  page carries the site-wide `no-cache, must-revalidate`). The route is absent
  from the public sitemap and public navigation; `robots.txt` is **not** edited
  (listing the path there would advertise it).
- **(v2) Tier 1 credential handling.** `services/azure_devops_read.py` builds a
  Basic-auth `Authorization` header from the PAT for each request and does
  nothing else with the value: it is never logged, never included in an
  exception message, and never appears in the JSON returned to the browser
  (verified by `tests/test_azure_devops_read.py`, which asserts the PAT string
  is absent from every response). A 401/403 is reported as "credential invalid
  or expired" without echoing the response body. The PAT the operator creates
  needs only **Code (Read)** and **Build (Read)** scopes — no write access
  exists for this integration to misuse even if the token were ever
  overprivileged by mistake.
- **(v2) The generated snapshot is not a public file.** `control_room_snapshot
  .json` lives at the repository/artifact root, not under `static/`, and Flask
  serves no generic root-file route — `GET /control_room_snapshot.json`
  returns the ordinary 404 (verified by test). It contains no secrets, only
  commit metadata and a build id.

## 6. Configuration

Set at least one owner allowlist to grant yourself access (see
`.env.example`):

```
# Production (Azure App Service application settings) — easiest: your sign-in email
PEERSLATE_OWNER_EMAILS=you@example.com
# or the opaque key:
PEERSLATE_OWNER_USER_KEYS=<your identity.user_key>

# Local dev (with PEERSLATE_ALLOW_DEV_IDENTITY=true), the dev key is the owner:
PEERSLATE_OWNER_USER_KEYS=test-user-1
```

Empty/unset ⇒ the Control Room returns 404 for everyone (fail-closed).

**(v2, optional)** Set all four to turn on Tier 1 live sync — any one left
blank keeps it truthfully "Not configured" rather than partially working:

```
PEERSLATE_ADO_ORG_URL=https://dev.azure.com/peerslate19
PEERSLATE_ADO_PROJECT=portfolio-site
PEERSLATE_ADO_REPO=portfolio-site
PEERSLATE_ADO_READ_PAT=<a PAT scoped to Code: Read + Build: Read only>
```

Create the PAT yourself in Azure DevOps (User Settings → Personal Access
Tokens), scope it to exactly those two read permissions, set an expiry, and
paste it directly into the Azure Web App's application settings (or local
`.env`) — never share it in chat or a file an agent writes.

## 7. Resilience states implemented

Loading is server-rendered (no spinner window). Truthful states exist for: no
records, source not configured, source unavailable, partial source, stale/mtime
fallback dates, missing file, unauthorized (404), and unexpected identity-storage
failure (fails closed to 404). One failed provider never blanks the others.
**(v2)** Tier 1 adds: not configured (per-collection and overall), one
endpoint failing without blanking the rest, a 401/403 credential state, a
stale-cache state (serves the last good result, labelled and timestamped) when
a refresh fails within 10 minutes of a prior success, and full unavailability
beyond that window. Drift adds an explicit `unknown` rather than guessing when
either side of the comparison is missing.

## 8. Maintenance

- To catalog another document in the register, add a row to
  `_REGISTER_DOCS` in `control_room_projection.py`.
- The YAML subset reader targets the governance baseline's stable structure; if
  that file adopts richer YAML, extend `parse_yaml_subset` (it fails soft).
- Tests: `tests/test_control_room.py` (authorization, read-only, truthfulness,
  non-exposure, snapshot fallback, drift) and **(v2)**
  `tests/test_azure_devops_read.py` (Tier 1 config/fetch/cache/credential
  behavior, mocked — no real network or PAT needed to run them). Keep
  `tests/test_site_rules.py` and `tests/test_governance_pointers.py` green.
- **(v2)** To add another Azure DevOps collection (e.g. work items), add a
  normalizer + endpoint call in `services/azure_devops_read.py`'s `_fetch_all`,
  extend the `fetch_repository_activity` return shape, and add a matching
  block in `control_room.html` / `control-room.js`'s
  `renderRepositoryActivitySection`.
- **(v2)** `CACHE_TTL_SECONDS` (60) and `STALE_CACHE_MAX_AGE_SECONDS` (600) in
  `services/azure_devops_read.py`, and the 90s auto-refresh interval in
  `control-room.js`, are the tunables if polling cadence ever needs to change.
