# PS-OPS-001 Gate Candidate Evidence - 2026-07-27

## A. Decision identity

- **Gate:** Candidate
- **Delivery mode:** Standard
- **Materiality:** Material
- **Materiality rationale:** Shared deployment-pipeline, runtime identity,
  liveness, smoke, and Azure candidate-environment controls change.
- **Gate applicability:** Applies before this material branch may merge for
  production deployment.
- **Initiative/release:** `PS-AUDIT-WEB-001` and `PS-OPS-001` repository floor
- **Exact source branch and SHA:**
  `work/2026-07-26-responsive-site-audit-001` at
  `1ca3ea6120fc8fcbfeba30137a3bfc94d5508772`
- **Merge target at assessment:** Azure `origin/main`
  `f85747275b81359c0d99bd99f340e65aa58420b8`
- **Build ID and immutable artifact:** Azure build `256`
  (`20260727.9`), `256.zip`, SHA-256
  `b1e605e058aba208d6c88967ba7c7c0b5571fdf1d9ab80ce8e632a1d05e67698`
- **Exact live candidate release:** opaque release
  `20593052441e84d7211ed4ec`
- **Environment:** Azure environment and separate Linux Basic B1 Web App
  `peerslate-candidate`, `https://peerslate-candidate.azurewebsites.net`
- **Intended audience/exposure:** Short-lived automated candidate verification
  only; no custom DNS, discovery link, member data, provider access, or feature
  enablement.
- **Feature flags/configuration:** Private/database/owner/studio/journal/photo
  features explicitly off; no connection strings; no production credentials;
  system identity has no Azure role assignments.
- **Date and evidence window:** 2026-07-27, 11:39:57-11:50:06 UTC
- **Designated manager / evidence owner:** Current ChatGPT Work/Codex task
- **Release owner and final decision authority:** Pete
- **Independent separation-of-duty check:** Codex implemented and collected
  evidence but did not approve the gate. Pete reviewed the exact evidence and
  separately replied `pass` on 2026-07-27.
- **Prior independent technical reviewers:** Runtime/pipeline, test-contract,
  governance, and infrastructure-hygiene rechecks passed at
  `5472b02cccc4e7f6dff34ab1a65b37047c568507`.
- **Decision:** **Pass**

## B. Evidence matrix

| Control / requirement | Applicability and exact evidence | Result | Finding / remaining risk |
|---|---|---|---|
| Exact source/artifact/environment identity | Build 256 source SHA and branch match the manifest and candidate deployment; artifact hash above | Pass | Any later material source change requires reassessment |
| Exact live release identity | `/healthz` matched release `20593052441e84d7211ed4ec` derived from source SHA and build 256 | Pass | Production receives a new exact main-build identity after merge |
| Dependency compatibility | Local and Azure `pip check` passed | Pass | None |
| Dependency vulnerability scan | Pinned `pip-audit` 2.10.1 reported no known vulnerabilities | Pass | Re-run on later dependency change |
| Secret scan | Checksum-pinned Gitleaks 8.30.1 scanned 480 commits with redaction and reported no leaks | Pass | One exact known non-secret UUID fixture is narrowly allowlisted |
| Application/security/privacy tests | Local: 999 passed, 2 skipped; Azure: 999 passed, 18 environment-dependent skips | Pass | No mandatory failure |
| Migration and rollback | No schema, data, storage, or migration change. Candidate stop action is the applicable bounded recovery control | Pass | Production rollback remains Gate F/operator work |
| Production-like candidate environment | Separate B1 Linux plan and Web App use the production runtime/deployment mechanism; Python 3.14 and TLS 1.2 match production | Pass | Temporary B1 cost exists until post-production cleanup |
| Identity/data/provider/secret separation | No connection strings, no Azure role assignments, inert provider import value, private features off | Pass | Candidate must not receive production settings later |
| Liveness/readiness and smoke | `/healthz`, `/`, `/interview-studio`, `/robots.txt`, and `/sitemap.xml` passed on the candidate hostname | Pass | Cold start used about three minutes of the bounded retry window |
| Stop/rollback control | Always-run stage stopped the app and verified Azure state `Stopped` | Pass | Named operator is the current release manager |
| Accessibility, responsive, and visual acceptance | No presentation delta relative to current `origin/main`; prior responsive package evidence remains separate | Not Applicable | No new visual acceptance is inferred |
| Legal, policy, analytics, consent, or broad launch | No audience expansion, telemetry, cookies, policy, or member behavior change | Not Applicable | Gate Launch remains `Not Assessed` |
| Monitoring, alerts, SLO/RTO/RPO, incident/support, backup/restore | Impact assessed: this release adds no provider or persistence dependency; broader operating controls are outside this Candidate boundary | Not Applicable | Gate Operate begins after production Gate F and remains separately assessed |
| Capacity/cost/vendor posture | Candidate ran on a separate temporary Basic B1 plan; production remained responsive during the run | Pass | Remove the temporary plan after verified production release |

## C. Deployment and recovery

- **Candidate deployment result:** Azure build 256 `CandidateDeploy` succeeded.
- **Candidate smoke result:** `CandidateSmoke` succeeded against the exact live
  release and canonical public boundary.
- **Production isolation:** Build 256 production Deploy and ProductionSmoke
  stages were both skipped by branch condition. Production returned 200 during
  and after the candidate run.
- **Stop exercise:** `CandidateStop` succeeded and the Web App is `Stopped`.
- **Production deployment status at decision time:** Not yet performed.
- **Production stop/rollback owner:** Current release manager under Pete's
  authority.
- **Production rollback trigger:** Failed exact identity, failed mandatory
  public smoke, critical/high security or privacy finding, or material live
  regression.
- **Exact recovery action:** Stop further exposure, preserve evidence, and
  redeploy the previously successful main release, Azure build 255 at
  `f85747275b81359c0d99bd99f340e65aa58420b8`, or revert the release through the
  required Azure PR workflow.

## D. Final decision

Pete approved Gate Candidate `Pass` for exact build 256 and source
`1ca3ea6120fc8fcbfeba30137a3bfc94d5508772` in the current Codex task on
2026-07-27. This authorizes the Azure PR, required merge workflow, production
deployment, and immediate production verification already requested by Pete.

This evidence record and the matching governance/test-assertion updates are a
non-material closeout delta: they change no runtime code, dependency,
configuration, environment, feature, data behavior, audience, or risk
boundary. They document rather than alter the exact assessed Candidate.

Gate Launch, Gate Operate, and Gate Retire remain separately `Not Assessed`.
This Candidate decision does not enable a feature, expand an audience, approve
member data access, or waive production smoke and rollback obligations.
