# PS-SEC-EDGE-001 Gate Candidate Evidence - 2026-07-28

## A. Decision identity

- **Gate:** Candidate
- **Delivery mode:** Standard incident recovery
- **Materiality:** Material
- **Materiality rationale:** Authentication, authorization, private response
  caching, rate-limit identity, shared deployment packaging, and production
  runtime compatibility change.
- **Gate applicability:** Applies before this recovered runtime branch may
  merge for production deployment.
- **Initiative/release:** `PS-SEC-EDGE-001`
- **Exact assessed source branch and SHA:**
  `work/2026-07-28-sec-edge-reland-001` at
  `a5c13cdeb901d90ebca8c2ca1f835a6746aa19bd`
- **Merge target at assessment:** Azure `origin/main`
  `89a619a560f04ec3763016939361f64516aac6bf`
- **Build ID and immutable artifact:** Azure build `262`
  (`20260728.4`), `262.zip`, SHA-256
  `22aa3edfdae25290accc2fe58941804ac42d19606d1eb96f49fd2ecc68122408`
- **Exact live Candidate release:** opaque release
  `b37fa41e7a31c6a91081ae21`
- **Environment:** Azure environment and separate Linux Basic B1 Web App
  `peerslate-candidate`, `https://peerslate-candidate.azurewebsites.net`
- **Runtime:** App Service `PYTHON|3.14`; pipeline build/test Python 3.12
- **Intended audience/exposure:** Short-lived automated Candidate verification
  only; no custom DNS, discovery link, member data, provider access, or feature
  enablement.
- **Feature flags/configuration:** No production settings or credentials; no
  connection strings; no managed identity; private/database/owner features
  absent and therefore default off. The only app settings are an inert
  import-time provider value and the non-secret
  `SCM_DO_BUILD_DURING_DEPLOYMENT=true` platform build flag.
- **Date and evidence window:** 2026-07-28, 02:17:45-02:29:04 UTC
- **Designated manager / evidence owner / delegated release manager:** Current
  ChatGPT Work/Codex task, under Pete's explicit delegation of the remaining
  bounded recovery and release work.
- **Independent reviewer:** Fresh GPT-5.6 Sol High review.
- **Independent result:** Original recovery
  `3d507e7f5f32299648153abbd00ae915825219c5` failed with six findings. All were
  corrected. Exact corrected
  `a5c13cdeb901d90ebca8c2ca1f835a6746aa19bd` received `Pass`, with no
  critical, high, or medium security, privacy, authorization, or
  shared-infrastructure blocker remaining.
- **Decision:** **Pass**

## B. Evidence matrix

| Control / requirement | Applicability and exact evidence | Result | Finding / remaining risk |
|---|---|---|---|
| Exact source/artifact/environment identity | Build 262 source SHA and branch match the manifest and Candidate deployment; artifact hash and release identity are recorded above | Pass | Any later material source change requires reassessment |
| Dependency compatibility | Local and Azure `pip check` reported no broken requirements | Pass | None |
| Dependency vulnerability scan | Pinned `pip-audit` 2.10.1 reported no known vulnerabilities | Pass | Re-run on later dependency change |
| Secret scan | Checksum-verified Gitleaks 8.30.1 scanned 485 commits with redaction and reported no leaks | Pass | Existing narrow known non-secret allowlist remains unchanged |
| Application/security/privacy tests | Local full suite: 1035 passed, 3 skipped, 503 subtests; Azure: 1038 tests, 18 environment-dependent skips; independent full suite repeated the local result | Pass | No mandatory failure |
| Fresh independent review | Corrected exact SHA received `Pass`; all six original findings were rechecked in committed code/docs | Pass | One low documentation count was dispositioned below |
| Authentication issuer enforcement | Production issuer setting is present and exactly matches the reviewed expectation; missing/blank/foreign issuer claims are refused before account upsert | Pass | Newly load-bearing configuration blocker satisfied |
| Private/member response caching | `/auth/session`, private/personalized blueprints, and identity-resolved app routes default to `private, no-store`; representative session, dashboard, feed, owner, and Slate Board regressions pass | Pass | Public signed-out pages keep ordinary revalidation |
| Compression/runtime compatibility | Flask-Compress, Brotli, zstd configuration/imports, and compression-only tests are absent; Python 3.14 Candidate built and booted | Pass | Response compression remains deferred |
| Migration and rollback | No schema, data, storage, or migration change. Candidate stop is the applicable bounded recovery control | Pass | Production rollback remains Gate F/operator work |
| Production-like Candidate environment | Separate B1 Linux plan and Web App use the production runtime and deployment mechanism without sharing production compute | Pass | Temporary B1 cost remains through production verification |
| Identity/data/provider/secret separation | No connection strings, managed identity, production credential, trusted identity headers, owner allowlist, or private feature enablement | Pass | Candidate must not receive production settings later |
| Liveness/readiness and smoke | `/healthz`, `/`, `/interview-studio`, `/robots.txt`, and `/sitemap.xml` passed on the Candidate hostname with exact release identity | Pass | Cold start required six bounded retries |
| Stop/rollback control | Always-run stage stopped the app and verified Azure state `Stopped` | Pass | Named operator is the delegated release manager |
| Production isolation | Build 262 production Deploy and ProductionSmoke stages were skipped by their main-only conditions; production routes remained healthy before, during, and after Candidate | Pass | No Candidate claim is represented as production |
| Accessibility, responsive, and visual acceptance | No visual composition, hierarchy, content, interaction, or responsive change | Not Applicable | No visual acceptance is inferred |
| Legal, policy, analytics, consent, or broad launch | No audience expansion, telemetry, cookies, policy, or member capability change | Not Applicable | Gate Launch remains separately not applicable |
| Monitoring, alerts, SLO/RTO/RPO, backup/restore | No provider or persistence dependency is added; existing production operating controls remain unchanged | Not Applicable | Gate Operate begins after production Gate F |

## C. Diagnostic correction record

Azure build `261` assessed pre-review-correction SHA
`6151085ff3d16cd6e56dc1d27a21582faecb1958`. Its Build and CandidateDeploy
stages passed, CandidateSmoke failed because the newly recreated Web App lacked
the non-secret `SCM_DO_BUILD_DURING_DEPLOYMENT=true` platform flag, and its
always-run CandidateStop passed. No production stage ran.

The flag was added without copying any production setting or secret, and the
`PS-OPS-001` configuration record was corrected. Build 262 then performed a
zero-warning/zero-error Oryx remote build, deployed, passed the exact smoke,
and stopped cleanly. Build 261 is diagnostic evidence only and does not receive
a Gate Candidate decision.

## D. Deployment and recovery

- **Candidate build result:** Build 262 `Build` succeeded, including
  compatibility, vulnerability, secret, compile, test, release-identity,
  package, and artifact-manifest controls.
- **Candidate deployment result:** `CandidateDeploy` succeeded using an Oryx
  Python 3.14 remote build with zero reported issues.
- **Candidate smoke result:** `CandidateSmoke` succeeded against exact release
  `b37fa41e7a31c6a91081ae21` and the canonical public boundary.
- **Production isolation:** `Deploy` and `ProductionSmoke` were skipped.
  Production `/`, `/healthz`, `/petec/resume`, and `/experience` returned 200
  after the Candidate run; production remained on revert release
  `5f2e58344f1457d368abfce1`.
- **Stop exercise:** `CandidateStop` succeeded and Azure reports the Web App
  `Stopped`.
- **Production deployment status at decision time:** Not performed.
- **Production rollback owner:** Current delegated release manager.
- **Production rollback trigger:** Failed exact identity, failed mandatory
  smoke, critical/high security or privacy finding, or material live
  regression.
- **Exact recovery action:** Stop further exposure, preserve evidence, and
  revert the release through the required Azure PR workflow to the last known
  healthy main commit/release.

## E. Accepted non-blocking finding

The completion report said manual static tokens were removed across 28
templates. The exact diff contains 26 surviving templates whose only change is
token removal, plus one deleted partial; the reserved retired rollback template
is unchanged. This is a low documentation count only, with no runtime effect.
The post-Candidate closeout corrects the count. Because that correction changes
documentation only, it does not invalidate the exact assessed artifact.

## F. Final decision

Under Pete's explicit end-to-end delegation, the designated release manager
records Gate Candidate **Pass** for Azure build 262 and exact assessed source
`a5c13cdeb901d90ebca8c2ca1f835a6746aa19bd`.

This authorizes the required Azure PR, squash merge, production pipeline, and
immediate live verification. It does not represent the branch as merged,
deployed, or live; those states require their own exact evidence. It does not
enable a feature, expand an audience, approve member-data access, or waive
production smoke and rollback obligations.
