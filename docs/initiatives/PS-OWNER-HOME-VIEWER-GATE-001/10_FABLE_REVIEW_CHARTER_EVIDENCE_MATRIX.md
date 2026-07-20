# PS-OWNER-HOME-VIEWER-GATE-001 — Review Charter and Evidence Matrix

Recorded 2026-07-19 by the Claude/Fable architecture writer. Defines the
review, evidence, and acceptance obligations for the two implementation
packages (`PS-HOME-BACKEND-001`, then `PS-HOME-FRONTEND-001`). It refines —
and never weakens — the Codex `TEST_RELEASE_PLAN.md` in this directory.

## 1. Review model

Both packages run under the self-managed delivery model (`docs/AI_WORKFLOW.md`):
the assigned writer performs a distinct complete-diff review against its exact
`origin/main` base, finds and fixes its own issues, runs all required evidence,
and returns `Pass`, `Conditional`, or `Fail`. The designated session manager
may rely on coherent self-certification plus a focused product review. Pete and
the designated manager give final visual acceptance before release of the
frontend package; a writer never approves its own visual gate.

Backend merges first. The frontend branch starts only from the post-backend
`origin/main` and consumes the real bounded owner view model.

## 2. Focused tests

### PS-HOME-BACKEND-001 (in `tests/test_owner_home.py`, `tests/test_owner_home_migration.py`)

- `owner-home.v1` schema shape; serializer rejects unknown fields/categories.
- Limits enforced server-side: ≤3 review items, ≤9 product objects, ≤64 KiB.
- Deduplication: a record appears only in its highest-priority category;
  deterministic tie-breaks are stable across repeated identical requests.
- Owner isolation: two-owner canaries (Owner A / Owner B with distinct
  issuer/subject mappings) at SQL, service, and serialized-byte layers;
  foreign selectors return neutral 404-class results with no timing/existence
  hints.
- Authorization before retrieval: the procedure resolves the owner from
  `@UserKey` internally; no client-supplied owner/profile ID is accepted.
- Failure independence: core aggregation versus optional adapters; a failed
  optional category yields an explicit unavailable state, never a fixture.
- Availability registry: `availability.state = coming_later` carries no item
  key, count, person, or content and triggers no data query.
- Headers: `Cache-Control: private, no-store` on JSON; with the flag off the
  JSON route returns neutral 404 before retrieval; with the flag on anonymous
  JSON → `401 authentication_required`. HTML/no-store and validated sign-in
  redirect evidence belongs to the later frontend package.
- Payload privacy canaries: raw Capture bodies, transcripts, audio URLs,
  discarded proposals, emails, internal numeric IDs, and other-owner strings
  are asserted absent from SQL results, view model, serialized bytes, headers,
  and logs.
- No-N+1: query count constant (1 core + ≤2 optional adapters) regardless of
  eligible-record count.
- Migration gate: apply / structural+behavioral verify / rollback / reapply on
  an isolated database, recorded per the repository migration ledger pattern.
- Flag: `PEERSLATE_OWNER_HOME_ENABLED` defaults off; the backend package does
  not edit `/app`, and flag-off JSON is neutral 404 with zero Home data calls.

### PS-HOME-FRONTEND-001 (extend `tests/test_owner_home.py`; new `tests/test_owner_home_accessibility.py`)

- HTML contract per state: loading, empty, populated, partial failure,
  complete failure, stale, restricted, retry, session-expired, recovery.
- Exactly one `<h1>` and one `<main id="main-content">` (regression against
  the known nested-main defect in `owner_workspace.html`).
- Review list renders ≤3 `<li>` and the bounded-remainder row is not a record.
- Coming-later previews: visible label text present; native `disabled` +
  `aria-disabled="true"` where applicable; no `href`; excluded from forms; no
  event handlers; DOM contains no fabricated person/count/result strings.
- No request paths: templates and JS contain no reference to `/api/dashboard`
  and no fetch from any Coming-later element (static assertion plus JS-level
  test).
- Truthful-label copy inventory (R2): each state label appears once per
  element; no fixture pills in production templates.
- Two-owner DOM canaries: rendered page for Owner A contains no Owner B
  canary strings; sequential sign-in/sign-out produces no bleed (no-store).
- Guardrails stay green: `tests/test_site_rules.py`,
  `tests/test_governance_pointers.py`.
- Standalone shell: flag-on Owner Home contains no site sky, global
  header/profile tabs, profile band, public footer, Ask Pete AI, public search
  data, global theme bootstrap, global mobile tabbar, public-chrome scripts, or
  legacy forced-desktop tablet viewport behavior; it retains shared fonts/base
  styles, the skip link, and exactly one base main. Flag-off `/app` and every
  non-Owner-Home route retain their current DOM/chrome behavior.

## 3. Full guardrail and regression suite

At every merge candidate on both packages:

- `python -m unittest tests.test_governance_pointers tests.test_site_rules -v`
- `python -m unittest discover -s tests` (full repository suite; record pass
  count and any environment-conditional skips exactly, as prior packages did)
- No unrelated-lane file edits; complete-diff review confirms only reserved
  files changed.

## 4. Screenshot and visual-parity evidence (frontend package)

Named files under `artifacts/ps-home-frontend-001/`, each paired with its
authority export per the parity map in
`06_FABLE_VISUAL_PARITY_DEVIATION_REGISTER.md`:

| Evidence name pattern | Widths | States |
|---|---|---|
| `HOME-<STATE>_DESKTOP_1440.png` | 1440 | current-empty, populated-maximum (two-owner fixture), loading, partial-failure, complete-failure, stale, restricted, recovery-success, recovery-failure |
| `HOME-<STATE>_MOBILE_390.png` | 390 | current-empty, populated-maximum |
| `HOME-<STATE>_MOBILE_320.png` | 320 | current-empty, populated-maximum (must show the R1 correction) |
| `HOME-CURRENT_LANDSCAPE_844.png` | 844 | current |
| `HOME-FOCUS_*.png` | 1440 | visible focus on Capture and on a review row |
| `HOME-FORCEDCOLORS_*.png` | 1440 | forced-colors current |
| `HOME-REDUCEDMOTION_*.png` | 1440 | reduced-motion current |
| `HOME-ZOOM200_*.png` | 1440@200% | populated |
| `HOME-LONGCONTENT_*.png` | 1440 | long/bidi/missing-media fixture |

Authority parity matrix: one row per parity-map area (20 rows), columns
= authority export, implementation screenshot, match/exceed/deviation,
deviation ID (D1–D6 only), notes. Any new deviation requires Pete + manager
approval before merge.

## 5. Accessibility evidence (frontend package)

- Automated semantic/contrast scan with zero unresolved serious/critical
  findings (tool and version recorded).
- Keyboard-only walkthrough of every state; focus-order and visible-focus
  inspection.
- NVDA + supported Chromium on Windows: context comprehension, category
  announcements, Coming-later wording read once, retry announcements.
- 200% zoom, 320 CSS-px reflow, text-spacing overrides, Windows high
  contrast/forced colors, reduced motion, touch/orientation.
- Long, missing-media, and bidirectional sample content.

## 6. Privacy / two-owner canaries (both packages)

Canary datasets per `TEST_RELEASE_PLAN.md`: unique strings in raw Capture
bodies/revisions, transcripts/audio URLs, discarded proposals, owner
email/name, other-owner Moments, deleted/tombstone metadata, internal numeric
IDs. Assert authorized-canary presence and prohibited-canary absence in SQL
results, Python view models, serialized JSON bytes, rendered DOM/bootstrap
data, headers/redirects/cookies/URLs, logs, and browser storage/history.
Founding-alpha validation (Pete and Danielle, distinct real accounts) is
required before flag expansion; neither account stands in for the other.

## 7. Completion-report requirements (each package)

Use `docs/templates/OWNER_TECHNICAL_COMPLETION_REPORT.md` and record exactly:

- package ID, branch, full HEAD SHA, exact `origin/main` base SHA;
- PR number, squash-merge SHA, pipeline run/build, production verification
  URLs and results (or "not deployed" truthfully);
- changed files; commands run with real results; skips/failures disclosed;
- named visual authority (per `01_FABLE_AUTHORITY_MANIFEST.md`), parity matrix
  result, deviation register outcomes (D1–D6), and Pete + designated-manager
  visual acceptance status;
- homepage-impact assessment (see §8);
- self-certification `Pass`/`Conditional`/`Fail` with complete-diff review
  status; never label unresolved failures as passed;
- the explicit distinction between demonstration, implementation, deployment,
  and live production.

## 8. Homepage-impact check (required by the Owner Visual Integrity Standard)

The accepted candidate records: "No direct Owner Home homepage projection is
currently identified; implementation must reassess this before release."
Current `/` sections are Voice hero, Living Résumé, Interview walkthrough,
Story/future, invite band — none presents Owner Home today. The signed-in
entry point is the header's `My Slate` button targeting the owner workspace.
`PS-HOME-FRONTEND-001` must re-run this assessment at release: if `/` still
does not present Owner Home, record "no homepage projection; parity not
applicable"; if any homepage section begins to present or link Owner Home, a
same-wave update or an explicitly sequenced downstream parity package is
required.

## 9. Release gate summary

| Gate | Requirement |
|---|---|
| Architecture accepted | This package reviewed by ChatGPT Work/Codex |
| Backend merged first | `PS-HOME-BACKEND-001` squash-merged, pipeline green, flag off |
| Frontend implemented | From post-backend main; all §2–§6 evidence |
| Visual acceptance | Pete + designated manager against the real product |
| Azure release | PR, pipeline, live verification of `/app` (flag-off default preserved), then founding-alpha enablement |
| Closeout | Completion reports per §7; governance state updates only via reserved manager lane |

Any unresolved privacy leak, cross-owner result, simulated capability,
fabricated content, visual downgrade, or missing rollback proof is **Fail**.
