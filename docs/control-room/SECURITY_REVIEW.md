# Control Room Security Review

Date: 2026-07-19

Reviewer: ChatGPT Codex

Integrated review commit: `b0db7708964d867922603b76f20df9ae1f3ac4d2`

## Outcome

**Pass for technical security review.** No open high- or medium-severity
findings remain in the reviewed Control Room implementation. This result does
not claim production authentication, a real Azure DevOps credential, pipeline
snapshot generation, or deployment has been exercised.

## Scope

- Owner authorization and identity trust boundary
- Route methods, cache/index headers, public discoverability, and snapshot URL
- Repository-file projection and absence of database mutation
- Azure DevOps read adapter, credential handling, timeouts, caching, and links
- Server-rendered and client-rendered XSS boundaries
- Integration with current `origin/main @ 296711d001c7dd0d0bc66001a29c42595a938bdb`

## Findings and corrections

1. **Resolved — portable manager schema compatibility (technical).** Current
   governance replaced the legacy `manager.tool` field. The dashboard now reads
   both schemas and renders the portable role honestly, with regression coverage.
2. **Resolved — mobile horizontal overflow (accessibility/integration).** Grid
   minimum sizing expanded the page beyond a 390px viewport. Cards and definition
   lists now shrink/reflow while wide data tables remain locally scrollable.
3. **Resolved — unsafe external-link schemes (low security hardening).** The
   Azure organization endpoint must be an absolute HTTPS URL, and non-HTTPS
   pipeline links received from the API are removed before reaching the client.
4. **Resolved — sequential cold Azure reads (availability hardening).** Five
   independent GET requests now run concurrently, bounding the cold path to one
   endpoint timeout rather than five serial timeouts.

## Controls confirmed

- Both routes are independently server-gated and register only GET/HEAD/OPTIONS.
- Empty allowlists, unauthenticated users, non-owners, and identity-storage
  failures fail closed with 404 responses.
- Identity comes from PeerSlate's trusted server-side identity resolution;
  query parameters and client-supplied owner fields cannot elevate access.
- Owner pages and JSON are `no-store`, `private`, `noindex`, `nofollow`, and
  `noarchive`; the generated snapshot is not publicly routed.
- The projection does not import or call database mutation services.
- The Azure adapter uses GET only. The PAT stays in a server-side Authorization
  header, is absent from URLs/results/log messages, and is not committed.
- Client HTML builders escape API text before `innerHTML`; initiative dialog
  markup is copied only from Jinja-autoescaped, server-rendered content.

## Operational decisions

- `/owner/control-room` is the correct prefix because it is a site-owner plane,
  separate from member-owned `/app/*` routes and absent from public navigation.
- The environment allowlist is acceptable bootstrap authorization. Prefer the
  opaque `PEERSLATE_OWNER_USER_KEYS` identifier when available. Move to a
  server-enforced database role only when a real admin model is introduced.
- An expiring Azure DevOps PAT scoped only to Code (Read) and Build (Read) is
  acceptable for optional v1 live sync. Managed identity/OAuth is a reasonable
  future replacement, not a blocker for this read-only tier.

## Evidence

- Focused: 62 passed (`test_control_room` 49 + `test_azure_devops_read` 13)
- Guardrails: 24 passed (`test_site_rules` + `test_governance_pointers`)
- Full suite: 468 passed, 1 pre-existing skip
- Browser: desktop and 390px mobile; 640px desktop-zoom-equivalent reflow;
  initiative filter; dialog open/Escape/focus return; zero console warnings or
  errors; no page-level horizontal overflow
- Route smoke: public home, Interview Studio, and résumé remain 200; protected
  Capture retains its sign-in redirect; unauthorised Control Room routes and
  the snapshot URL return 404

## Remaining release conditions

- No production deployment or live owner sign-in has been tested.
- No real PAT/API response or Azure Pipelines snapshot has been exercised.
- The package is not registered in the authoritative active-package records.
- Pete functional acceptance and designated-manager visual/product and
  merge-readiness acceptance remain blank by design.
