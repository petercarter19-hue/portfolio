# PS-OPS-001 - Professional delivery and operational readiness

- **Owner:** Pete
- **Owner decision:** 2026-07-26
- **Designated setup and initial-enforcement manager:** current ChatGPT
  Work/Codex task
- **Sole writer:** Codex on
  `work/2026-07-26-responsive-site-audit-001`
- **Authoritative base:** Azure `origin/main`
  `453662adc022b6ea0b1b38208c7100697d119a8b`, with prerequisite
  `PS-AUDIT-WEB-001` commit
  `f05171a2e808e419becf1b2bde5b870c8343b5e2` on the same branch
- **Independent reviewer:** runtime/pipeline, test-contract, and final
  governance rechecks passed at
  `5472b02cccc4e7f6dff34ab1a65b37047c568507`
- **Status:** Technical repository handoff complete; Gate Candidate `Pass`
  recorded for exact Azure build `256` at
  `1ca3ea6120fc8fcbfeba30137a3bfc94d5508772`; approved for the required Azure
  PR and production Gate F; Gate Launch, Gate Operate, and Gate Retire remain
  `Not Assessed`
- **Roadmap authority:** existing `PS-OPS-001` operational-maturity allocation
- **Production status:** unchanged at Candidate decision time; production
  deployment and live verification remain required after merge
- **Candidate-path owner decision:** On 2026-07-26 Pete selected the
  recommended production-like staging path and explicitly delegated its
  bounded implementation to the current manager. On 2026-07-27 Pete separately
  approved Candidate `Pass` for the exact evidence in
  `CANDIDATE_EVIDENCE_2026-07-27.md`.

## 1. Owner decision and purpose

Pete directed PeerSlate to implement the professional controls identified by
the cross-site delivery review. PeerSlate already has strong package-level
direction, architecture, implementation, verification, member validation,
visual, legal, audit, and release controls. This package fills the transition
gaps without adding a second delivery lifecycle.

It establishes four evidence gates and one bounded emergency mode:

1. **Gate Candidate - Production Candidate Readiness**
2. **Gate Launch - Public Launch and Operational Readiness**
3. **Gate Operate - Operate and Improve**
4. **Gate Retire - Safe Decommissioning**

Emergency Release Mode changes timing, not the mandatory truth, security,
privacy, artifact-identity, approval, and rollback controls.

These gates specialize the existing Roadmap A-F flow:

```text
Gate D implementation verification closes
        ->
Gate Candidate records immutable promotion evidence
        ->
Gate E member validation as applicable
        ->
Gate Launch when the release opens or materially expands an audience boundary
        ->
Gate F deployment and production verification, including post-deploy smoke
        ->
Gate Operate after Gate F closes, at 24-72 hours and recurring cadence
        ->
Gate Retire when a capability, data boundary, integration, or service closes
```

They do not repeat a page's security, accessibility, visual, responsive,
performance, legal, or member-validation work. They consume the exact accepted
evidence from those packages and answer four different business questions:

- Is this exact artifact safe enough to become a production candidate?
- Is the business ready to expose this capability to the intended audience?
- Is the released service healthy, supported, learned from, and still within
  its approved risk?
- Can this capability or dependency be removed without abandoning people,
  data, legal obligations, routes, credentials, or operating controls?

## 2. Requirements

- **PS-OPS-GATE-001:** Every material runtime release shall record whether Gate
  Candidate applies and shall not enter production while a mandatory Candidate
  blocker is unresolved.
- **PS-OPS-GATE-002:** Public beta, broad registration, or materially expanded
  public/member exposure shall pass Gate Launch in addition to the feature's
  ordinary release gate.
- **PS-OPS-GATE-003:** Every material production release shall receive an early
  Gate Operate review; recurring operational review shall occur monthly for
  active beta/production operations and quarterly for the full system.
- **PS-OPS-GATE-004:** Every material capability, audience boundary,
  integration, or service retirement shall pass Gate Retire before final
  shutdown or destructive data action.
- **PS-OPS-REL-001:** Candidate evidence shall identify one exact source SHA,
  one immutable build artifact, environment/configuration, migrations, flags,
  automated results, accepted limitations, approval, and stop/rollback action.
- **PS-OPS-REL-002:** Deployment shall use a production-like candidate
  environment or an explicitly owner-accepted temporary exception. Direct
  production deployment with post-deploy smoke may detect a defect, but it is
  not equivalent to staging or progressive exposure.
- **PS-OPS-HEALTH-001:** PeerSlate shall expose a minimal, member-data-free
  process-liveness endpoint with an opaque exact-build release identity and
  shall verify it plus the canonical public boundary after deployment.
- **PS-OPS-SEC-001:** Candidate evidence shall include dependency
  compatibility, vulnerability, secret, application-security, and
  authorization/privacy results appropriate to the change.
- **PS-OPS-QUAL-001:** Applicable accessibility, responsive, performance,
  resilience, SEO/content, migration, and rollback evidence shall use explicit
  thresholds and named results rather than a generic "tested" statement.
- **PS-OPS-LAUNCH-001:** Launch evidence shall combine—not duplicate—the
  applicable Early Legal L-gate, responsive R2 result, independent
  accessibility result, performance result, public content/indexing result,
  support/privacy/incident/backup exercises, monitoring, and owner risk
  acceptance.
- **PS-OPS-OBS-001:** Operate evidence shall review production health,
  availability/latency/error objectives, incidents and near misses, support and
  privacy requests, dependency/security posture, backup/restore status, cost
  and capacity, member outcome/guardrail signals, and required corrections.
- **PS-OPS-TRUTH-001:** Missing mandatory evidence without an explicit accepted
  bounded exception is `Not Assessed` or `Fail`, never `Pass`. `Conditional`
  requires the exception controls in section 11. Documentation, a test suite,
  a deployment, or a healthy homepage alone cannot stand in for another
  required control.

### Materiality, applicability, and decision rights

Treat a release as **material** when it changes any deployed runtime code,
dependency, schema/data behavior, production configuration, infrastructure,
identity/authorization/privacy boundary, persistence/publication behavior,
audience exposure, telemetry, deployment control, or credible member, legal,
financial, security, or availability risk. A shared deployment-pipeline change
is material. A documentation/evidence-only change with no packaged artifact,
configuration, behavior, or risk-boundary effect may be non-material.

The designated manager records the classification and rationale before release
approval. When classification is uncertain, treat the release as material. The
implementation writer may not classify their own material change as
non-material, accept their own exception, or provide the required independent
approval.

Decision rights are:

- **Candidate:** Pete or an explicitly named delegated release manager makes
  the final go/no-go decision after the evidence owner and any required
  independent reviewer sign.
- **Launch:** Pete makes the exact audience/risk decision unless he records an
  explicit named delegate for that launch.
- **Operate:** the named operations owner may `Continue` within already
  accepted limits; an incident commander may `Constrain` or
  `Rollback/Disable`; expanded exposure, a new exception, or material risk
  acceptance returns to Pete or his explicit delegate.
- **Retire:** Pete or an explicitly named delegate approves the retirement.
  Destructive data action still requires its separate authority.

Applicability is recorded per gate, not inferred from a branch label. A change
that opens or materially expands an audience also invokes Launch; an actual
production release invokes Operate after Gate F; and a decommission invokes
Retire.

## 3. Gate Candidate - Production Candidate Readiness

Run Gate Candidate after Gate D implementation verification closes and before a
material artifact is approved for production deployment. Candidate is the one
immutable promotion record for Gate D's accepted evidence; it does not rerun or
independently approve Gate D.

### Minimum evidence

- exact source branch/SHA, merge target, build ID, artifact identity/hash, and
  dependency/runtime versions;
- clean dependency compatibility plus a selected vulnerability scanner and
  secret scanner with dated results and dispositions;
- applicable unit, integration, contract, authorization/isolation,
  migration/rollback, security, AI, accessibility, responsive, performance,
  resilience, and regression results;
- production-like environment/configuration evidence, including identity,
  callback, data, storage, provider, feature-flag, and secret separation;
- liveness/readiness contract and candidate-environment smoke results;
- migration/rollback and stop controls, with a named operator;
- release notes, known limitations, support/monitoring impact, and exact
  approval decision; and
- applicability recorded separately as `Applies` or `Not Applicable`, with a
  rationale; and one gate decision: `Pass`, `Conditional`, `Fail`, or `Not
  Assessed`, with owner and correction for every non-pass item.

### Automatic blockers

Gate Candidate cannot pass with:

- an unresolved critical/high security, privacy, authorization, cross-user,
  publication, deletion, or secret finding;
- dependency incompatibility or an undispositioned known vulnerability above
  the package's accepted threshold;
- a failed mandatory test or untraced mandatory requirement;
- an unsafe or untested migration/rollback;
- an accessibility blocker on an essential flow;
- a missing exact artifact/SHA/environment relationship;
- no liveness/smoke path for a runtime deployment;
- no stop/rollback operator;
- a production configuration value that the release makes load-bearing
  without its live value having been read from the target environment and
  matched against what the code will require (see below); or
- direct-to-production deployment represented as production-like staging.

#### Newly load-bearing configuration

Added by Pete's direction on 2026-07-27 after `PS-SEC-EDGE-001` found the gap.

A setting that is currently unused, advisory, or only a fallback is not
covered by ordinary testing, because nothing reads it and nothing can prove it
wrong. A release that promotes such a setting to a required, enforced, or
identity-affecting input must read its live value in the target environment
and record the comparison as gate evidence.

The originating case: `PEERSLATE_AUTH_ISSUER` had sat in the `peerslate-pete`
App Service purely as a fallback used when a principal carried no issuer
claim. A release made it an enforced equality check on every sign-in. A
mismatch would have refused every member, and no test could have caught it,
because the test environment supplies its own value. The live value was read
and matched before merge; it was correct, but it had never been validated
against reality before that check.

This blocker is not satisfied by a test, a default, a code comment, or a
belief about how the environment is configured. It is satisfied by the value
read from the environment that will run the release, recorded with the setting
name and the exact string it was compared against.

## 4. Gate Launch - Public Launch and Operational Readiness

Gate Launch applies before public beta, broad account registration, public or
permissioned Journal, materially expanded community/publication, or another
owner-designated broad exposure. It does not rerun for every ordinary release
after the same operating boundary is accepted; later changes reassess only
affected rows unless the boundary or risk changes.

### Required combined evidence

- applicable `EARLY_LEGAL_AND_SITE_READINESS_STANDARD.md` L-gate with actual
  counsel/security reviewer and dispositions where required;
- `PS-AUDIT-WEB-001` Gate R2 for the released route/state/viewport wave;
- independent WCAG 2.2 AA accessibility review, remediation register, keyboard
  and screen-reader tasks, and accessibility contact path;
- explicit performance budgets, synthetic results, and production-field plan
  for LCP, INP, CLS, server latency, errors, payload/assets, and critical
  authenticated workflows;
- public content/SEO inventory covering purpose, title/description, canonical,
  index/noindex, robots, sitemap, redirect/404, broken links, social metadata,
  structured data where justified, and Search Console ownership/verification;
- consent-aware, privacy-safe measurement plan with owner, event definitions,
  retention/access, success measures, and guardrails;
- exercised privacy-request, deletion/export, incident, support, moderation
  where applicable, and backup/restore paths;
- monitoring/alert routing, support owner, incident owner, severity and
  escalation rules, RTO/RPO/SLO objectives, and accepted remaining risk; and
- Pete's signed launch decision tied to the exact audience, SHA, environment,
  flags, evidence, limitations, and rollback/stop action.

No internal repository statement substitutes for counsel, security assessment,
assistive-technology review, real restore exercise, Azure configuration, or
owner launch approval.

## 5. Gate Operate - Operate and Improve

Gate Operate begins only after Gate F deployment and production verification
closes. Gate F owns deployment, production smoke, exact live release identity,
and the immediate release decision. Gate Operate owns the later 24-72-hour and
recurring operating evidence; it does not duplicate Gate F.

### Early release review

For a material release, review the first credible production window, normally
24-72 hours after exposure. Record:

- exact deployed SHA/build/artifact and flags;
- liveness, availability, latency, error, provider, queue/job, and cost signals;
- authorization/privacy alerts and payload-safe logging;
- support contacts, privacy requests, incidents, regressions, and near misses;
- critical member-task completion and trust/guardrail signals where available;
- rollback/stop thresholds and whether any fired;
- open defects, owner, severity, correction, and focused recheck; and
- `Continue`, `Constrain`, `Rollback/Disable`, or `Escalate`.

### Recurring review

During active beta/production operations:

- run a compact monthly operational review;
- reuse the quarterly full-site audit as the quarterly Gate Operate review when
  scope, date, reviewer, SHA/environment, evidence, and result are identical;
- exercise restore, incident, privacy-request, security-alert, and rollback
  paths at the cadence set by risk and the applicable legal gate;
- review dependency patching, vendor/subprocessor state, certificate/domain/
  callback expiry, quotas, capacity, cost, and data retention/deletion jobs; and
- turn evidence into an explicit continue, correct, retire, or invest decision.

An unchanged result does not require duplicate ceremony. Record the evidence
date and next due date.

## 6. Emergency Release Mode

Emergency Release Mode applies only when delaying a correction creates a
greater documented production risk. It may shorten sequencing, but it may not
bypass:

- exact source/build/environment identity;
- security, privacy, authorization, cross-user, publication, deletion, or
  secret blockers;
- a named release operator and a tested stop, disable, or rollback action;
- production smoke and payload-safe observation;
- explicit owner or delegated incident-commander approval; or
- honest `Conditional`/`Fail` status.

Every deferred non-blocking row requires an owner, compensating control,
blast-radius limit, expiry, and retrospective completion within two business
days. The retrospective is focused evidence completion, not a second release
review.

## 7. Gate Retire - Safe Decommissioning

Gate Retire applies before permanently disabling or removing a material member
capability, route family, data boundary, vendor integration, credential set, or
service. It records:

- affected audiences, owners, canonical data, projections, integrations,
  contracts, and regulatory/legal-hold obligations;
- member notice, support plan, export or portability path, and last-use date;
- retention, deletion, archive, legal hold, backup, and restore disposition;
- route redirects, canonical/indexing changes, broken-link checks, and
  replacement or unavailable behavior;
- traffic and dependency verification before secrets, identities, callbacks,
  webhooks, queues, storage, flags, code, and infrastructure are removed;
- monitoring/alert and support teardown only after final verification;
- rollback or restoration window, named operator, and final evidence; and
- `Pass`, `Conditional`, `Fail`, or `Not Assessed`.

Destructive data deletion remains separately authorized and is never inferred
from a Retire gate.

## 8. Repository operational floor implemented by this package

This candidate branch adds:

- `GET /healthz`, a public, member-data-free process-liveness response
  containing service/status plus an opaque build-specific release ID, with
  `Cache-Control: no-store`;
- a fail-closed build step that packages the opaque release ID derived from the
  exact Azure source SHA and build ID;
- a standard-library deployment smoke script that checks `/healthz`, `/`,
  `/interview-studio`, `/robots.txt`, and `/sitemap.xml` without signing in,
  following private data, or submitting content;
- pipeline dependency compatibility verification through `python -m pip
  check`;
- pipeline bytecode compilation for runtime and operational scripts;
- a post-deployment `ProductionSmoke` stage with a bounded deadline-based Azure
  warm-up window and normalized transport/protocol/read failures;
  and
- focused tests for the liveness contract, sitemap exclusion, smoke validation,
  HTTPS safety, and durable pipeline controls.

The liveness endpoint intentionally does not query SQL, Blob Storage, identity,
AI, or another provider. A dependency readiness endpoint can wake paid or
serverless resources, consume provider quota, and reveal infrastructure state;
it requires a separately approved contract.

## 9. Current honest readiness status

| Control | Current candidate status |
|---|---|
| Exact source and Azure build artifact | Azure build 256 at `1ca3ea6120fc8fcbfeba30137a3bfc94d5508772`; immutable artifact SHA-256 recorded |
| Full Python test suite | Local: 999 passed, 2 skipped; Azure: 999 passed, 18 environment-dependent skips |
| Dependency compatibility | Local and Azure `pip check` passed |
| Runtime/operations compile check | Implemented |
| Member-data-free liveness | Implemented on branch with exact build identity |
| Post-production public smoke | Implemented in YAML; production result remains Gate F work |
| Production-like staging path | Separate Basic B1 plan and candidate Web App passed exact deployment/smoke/stop |
| Azure pre-deployment approval/check | Candidate environment and pipeline permission configured and exercised |
| Dependency vulnerability scan | Pinned `pip-audit` reported no known vulnerabilities |
| Secret scan | Checksum-pinned Gitleaks scanned 480 commits with no leaks; one exact non-secret test-fixture allowlist |
| Automated accessibility/performance scan | Missing; package-level/manual evidence remains required |
| Rollback rehearsal and progressive exposure | Always-run candidate stop passed and Azure state was verified `Stopped` |
| Monitoring/alerts/SLO/RTO/RPO | Not assessed |
| Incident/privacy/support/backup exercises | Not assessed |
| Launch accessibility/performance/SEO/analytics evidence | Not assessed |

Therefore:

- **Gate Candidate:** `Pass` for build `256` and exact evidence record
- **Gate Launch:** `Not Assessed`
- **Gate Operate:** `Not Assessed`
- **Gate Retire:** `Not Assessed`

### Owner-selected Candidate implementation

The production App Service plan is Basic B1 and does not support deployment
slots. The delegated Candidate path therefore uses a separate
`peerslate-candidate` Web App on a temporary, separate Basic B1 plan. This
supplies the same Linux App Service runtime and deployment mechanism without
sharing production compute. The plan remains only through production
verification, then is removed to bound cost.

The candidate app receives an inert value required by the current application
import plus the non-secret `SCM_DO_BUILD_DURING_DEPLOYMENT=true` App Service
build flag. It receives no production Anthropic key, SQL connection, Blob
configuration, trusted identity headers, owner allowlist, Azure DevOps PAT, or
enabled private feature. The exact task branch alone can enter the candidate
stages. Those stages:

1. run compatibility, full tests, a pinned `pip-audit` advisory scan, and a
   checksum-verified Gitleaks full-history scan with redacted output;
2. package one exact build identity and SHA-256 artifact manifest;
3. deploy only to the separate candidate Web App;
4. verify the candidate hostname, build identity, and canonical public
   boundary; and
5. always stop the candidate app after the smoke stage, including when smoke
   fails.

The Web Apps do not share compute. The candidate's controls are a single smoke
workload, no member/provider access, no custom DNS/discovery link, an
always-run stop action, and production health rechecks. Exact build 256 passed
those controls; Pete made the separate gate decision recorded in
`CANDIDATE_EVIDENCE_2026-07-27.md`.

The new post-production smoke stage improves detection and proves which build
answered. It does not reduce the blast radius of a bad deployment. The exact
build-256 production-like path earned Candidate `Pass`; no production,
security, privacy, identity, or environment-bootstrap exception was requested
or inferred.

### Candidate admission-control correction required before reuse

The released pipeline still selects Candidate eligibility through one
hard-coded historical branch name. During the separately authorized
`PS-INTERVIEW-FOCUS-UI-001` overnight release, the delegated release manager
verified that a temporary remote alias at that name pointed byte-for-byte to
the already reviewed source
`da6f93946adf4f3ba3c29d39362b71b0946501a7`, ran Candidate pipeline 278, and
deleted the alias afterward. No pipeline source, runtime file, production
setting, production identity, secret, data boundary, or Candidate environment
boundary changed.

That one-time alias was a bounded procedural admission-control deviation, not
the intended reusable control. Its exact Candidate evidence remains valid, but
the workaround may not be repeated without new explicit owner approval.
Before another package uses Candidate, a separate PS-OPS correction must make
package-specific exact-SHA admission auditable without repointing a historical
branch name, receive complete-diff review, and pass focused admission-control
tests.

## 10. Evidence reuse and relationship to existing controls

- **Roadmap A-F:** Candidate is the immutable promotion record that consumes
  Gate D; Launch supplies audience/business readiness before an applicable Gate
  F release; Gate F owns deployment, live identity, and immediate smoke;
  Operate starts after F and implements the later "learn" cadence.
- **Early Legal L0-L5:** Legal review remains distinct. Launch consumes the
  applicable L-gate result and never labels internal drafting as counsel
  approval.
- **Responsive R1/R2:** R1 remains design/architecture readiness. Launch
  consumes R2 for the exact route wave.
- **Visual V0-V4 and package verification:** Keep page evidence in the page
  package. Candidate/Launch links it; they do not rerun it.
- **Checkpoint/full-site audits:** Operate may share the exact audit evidence
  when scope and evidence identity match.
- **Feature enablement readiness:** A default-off enablement may use one
  combined record when its readiness audit and Gate Candidate/Launch inspect
  the same boundary.

## 11. Evidence record and result semantics

Use `docs/templates/PROFESSIONAL_READINESS_EVIDENCE.md`. Every row names:

- requirement/control;
- applicability and rationale;
- owner and actual reviewer;
- exact SHA/artifact/environment/audience;
- evidence path/date/result;
- finding, correction, and recheck;
- remaining risk and expiry/re-review trigger; and
- final `Pass`, `Conditional`, `Fail`, or `Not Assessed`.

Applicability uses `Applies` or `Not Applicable` with a rationale; it is not a
gate result. `Pass` requires every mandatory applicable row to pass.
`Conditional` requires
an explicit bounded exception, owner, expiry, compensating control, and
stop/rollback decision. `Fail` blocks the transition. `Not Assessed` cannot be
interpreted as permission.

## 12. Setup reservation and exclusions

This task reserves:

- `.gitleaks.toml`;
- `.gitignore` for the generated release-identity exclusion only;
- `docs/initiatives/PS-OPS-001/**`;
- `docs/templates/PROFESSIONAL_READINESS_EVIDENCE.md`;
- `docs/AI_WORKFLOW.md`;
- `docs/PEERSLATE_SITE_RULES.md`;
- `docs/governance/EARLY_LEGAL_AND_SITE_READINESS_STANDARD.md`;
- `docs/governance/AI_DELIVERY_AUDIT_REGISTER.md`;
- `docs/governance/DECISIONS.md`;
- `docs/governance/DOCUMENT_CONTROL.md`;
- `docs/governance/MANAGER_SESSION_HANDOFF.md`;
- the bounded PS-OPS pointer entries in current baseline/state/initiatives;
- `app.py`;
- `azure-pipelines.yml`;
- `scripts/release_identity.py`;
- `scripts/candidate_artifact.py`;
- `scripts/verify_deployment_smoke.py`; and
- focused operational/governance tests.

Pete's 2026-07-26 follow-up delegation additionally authorizes the separate
`peerslate-candidate` Web App/environment, its non-production settings, pinned
local `pip-audit` and Gitleaks execution, immutable branch artifact, candidate
deployment/smoke, stop exercise, and exact evidence. It does not authorize
database access, migrations, feature enablement, member data, production
secrets/settings/identity, new telemetry, cookies/analytics, monitoring
providers, traffic switching, DNS, production deployment before the Candidate
decision, or another lane.

## 13. Acceptance and next action

Initial repository enforcement received a `Conditional` exact-SHA
shared-infrastructure review. Corrections and focused rechecks passed. This
material shared-pipeline/runtime release then earned Gate Candidate `Pass` for
exact Azure build 256; Pete made the decision separately from the writer. No
bootstrap exception was used.

The technical handoff may proceed after all focused/full tests, complete-diff
review, local health/smoke verification, and focused independent rechecks pass.
Before merge, a real Candidate evidence record for the exact proposed release
must then either:

- identify a branch artifact and receive a `Pass`; or
- record Pete's explicit bounded bootstrap exception with owner, expiry,
  compensating control, blast-radius limit, and stop/rollback action.

Only after that Candidate decision may the branch merge. The exact Azure
pipeline must then pass Build, Deploy, and ProductionSmoke, and the live
`/healthz` and canonical public routes must be verified before this repository
floor is called released.

The corrected runtime/pipeline, test-contract, and governance rechecks passed at
`5472b02cccc4e7f6dff34ab1a65b37047c568507`. That closes the technical review;
Pete made the later exact Candidate decision separately.

Pete selected the production-like Candidate investment, delegated the bounded
setup, and approved the completed exact record. The next action is the required
Azure PR and production Gate F. The release is not called deployed until the
exact main pipeline and live production smoke pass.
