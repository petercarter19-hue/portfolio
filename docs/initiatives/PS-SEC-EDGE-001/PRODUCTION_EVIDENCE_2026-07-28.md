# PS-SEC-EDGE-001 Production Recovery Evidence - 2026-07-28

## Release identity

- **Azure PR:** 192, required squash workflow, no policy bypass
- **Recovery source branch tip:**
  `1cb3a61892f5641362eb2e7bbaf080c5ecbf45e3`
- **Reviewed runtime source:**
  `a5c13cdeb901d90ebca8c2ca1f835a6746aa19bd`
- **Squash merge on Azure `main`:**
  `9445d63f12067997395206a8cfb504013c247158`
- **Automatic Azure pipeline:** 263 (`20260728.5`), source exactly matched the
  squash merge
- **Immutable deployment artifact:** `263.zip`, SHA-256
  `c6049e44e30484a7a0e754380bf32537a382877d081f86fa8ee1781db470e63a`
- **Exact production release:** `524cb04dc5b5aa82a58c8b2a`
- **Pipeline result:** `Succeeded`
- **Evidence window:** 2026-07-28 02:37:32-02:45:03 UTC

## Gate F and live verification

Build 263 passed dependency compatibility, pinned vulnerability scanning,
redacted full-history secret scanning, compilation, application/security tests,
release-identity generation, packaging, artifact hashing, production deploy,
and public-boundary smoke. Candidate stages correctly skipped on `main`.

The exact-release production smoke passed after eight bounded old-release
responses during App Service restart. It verified `/healthz`, `/`,
`/interview-studio`, `/robots.txt`, and `/sitemap.xml`.

Independent post-pipeline verification then confirmed:

- `/healthz`, `/`, `/petec/resume`, `/experience`, `/interview-studio`,
  `/robots.txt`, and `/sitemap.xml` returned HTTP 200;
- `/healthz` returned exact release `524cb04dc5b5aa82a58c8b2a` with
  `Cache-Control: no-store`;
- signed-out `/auth/session` returned the expected non-member contract with
  `Cache-Control: private, no-store`;
- public HTML returned `must-revalidate, no-cache`;
- CSP, HSTS, `X-Content-Type-Options`, and `Referrer-Policy` were present;
- a cross-site `POST /api/chat` was refused with HTTP 403 before provider work;
- the homepage emitted content-hashed static references, and a representative
  current asset returned `public, max-age=31536000, immutable`; and
- production remained `Running` before and after Candidate cleanup.

The separately queued duplicate manual build 264 targeted the same exact main
SHA but was detected before start and canceled. It is not a failed release or
additional production claim.

## Candidate cleanup and rollback disposition

The stopped `peerslate-candidate` Web App and its separate
`ASP-peerslate-candidate` Basic B1 plan were identity-checked against the
production app and plan, then removed after verified production recovery as
required by `PS-OPS-001`. Azure resource enumeration returned neither
temporary resource afterward. The production app remained on its distinct
`ASP-peerslate-9377` plan, `Running`, with exact `/healthz`.

No rollback was required. The failed PR 190 release remains preserved in the
incident history, and PR 191 remains the proven rollback path.

## Decision

Production Gate F and the PS-SEC-EDGE-001 triggered audit are **Pass**. The
safe edge-security, privacy-cache, static-asset, and deployment-package subset
is implemented, squash-merged, deployed, and verified live. Response
compression remains explicitly deferred.

This evidence file and its closeout edits are documentation-only. Their own
Azure main pipeline remains mandatory after merge; that pipeline does not
change the runtime decision recorded above.
