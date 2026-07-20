# PS-CAPTURE-PHOTO-LIFECYCLE-001 - Photo Lifecycle Readiness

## Assignment and control boundary

- Package: `PS-CAPTURE-PHOTO-LIFECYCLE-001`
- Work type: package-local architecture and evidence planning only
- Branch: `work/2026-07-20-capture-photo-lifecycle-001`
- Exact base: Azure DevOps `origin/main` at
  `b7b674415f1f7c9ac2844fa0482091b62a7ec979`
- Authority verified: `origin/main` matched the expected base after
  `git fetch origin --prune` on 2026-07-20
- Architecture writer: current Codex session
- Designated session manager: the existing ChatGPT Work/Codex
  owner-delegated Capture Media manager role; acceptance of this new package is
  pending
- Later implementation writer: unassigned
- Current recommendation: **Conditional**
- Production status: the released Photo backend and experience are deployed
  with `CAPTURE_PHOTO_ENABLED=false`; Photo remains unavailable to ordinary
  members and is not claimed live

This package defines the minimum safe way to prove the real signed-in Photo
lifecycle while preserving the existing global flag-off boundary. It does not
authorize application, route, template, CSS, JavaScript, test, configuration,
SQL, Azure, Defender, production-record, or homepage changes.

## Current released manifest

The following coordinates are the current Photo authority at this package's
base:

| Release element | Authoritative record | Current meaning |
| --- | --- | --- |
| Backend writer tip | `169d0acfe78dbfe57402c76add737f48681c68c6` | Governance-recorded historical writer tip; not locally resolvable after squash merge and source-branch deletion; not a release commit |
| Backend release | Azure PR 95; squash `e4863a57f9642731073f232a973508615e116d72`; pipeline 139 passed | Verified release commit for the private Blob/Defender/SQL/application foundation deployed flag-off |
| Backend closeout | Azure PR 96; squash `67b7053fcf9ba8bf37c1bbdc5aa2d275e31dc1b7`; pipeline 140 passed | Verified release commit for backend package closeout |
| Experience writer tip | `a19a5034aa7f3b9d355f8862aa98a34eb9f3e5f6` | Governance-recorded historical writer tip; not locally resolvable after squash merge and source-branch deletion; not a release commit |
| Experience release | Azure PR 98; squash `e5912c85d95dddbaed9c565d1e599efe2c8dd0b6`; pipeline 143 passed | Verified release commit for Photo 1 assets and protected integration deployed flag-off |
| Visual authority | `PS-CAPTURE-MEDIA-001/visual-authority/photo-1-selected-authority.jpg` | Accepted only for a flag-off release |
| General release flag | `CAPTURE_PHOTO_ENABLED=false` | No ordinary-member Photo access; direct Photo mutation remains neutral 404 |
| Homepage | `PS-HOME-CAPTURE-PHOTO-PARITY-001` not released | Logged-out Capture projection still truthfully presents Photo as later work |

Released backend surfaces include the Photo-specific routes in
`owner_routes.py`, the private storage and Photo orchestration services, the
generic Capture deletion dispatcher, the Photo SQL migration/rollback/verifier,
the Azure provisioning verifier, the nonsecret configuration example, Pillow
12.3.0, and focused regression tests. Released experience surfaces include the
Capture template, Capture-scoped CSS, `owner-capture-photo.js`, Photo route
rendering context, focused UI tests, the Photo 1 authority, and the five local
synthetic visual-evidence images. This manifest records what is deployed; it is
not proof of a signed-in production lifecycle.

## Remaining unproved release states

The flag-off release did not prove the following through real signed-in
production resources:

- scan pending;
- known-clean scan and safe derivative;
- application image-validation rejection;
- Defender-malicious rejection, subject to the explicit owner decision below;
- recoverable error/stale behavior;
- explicit confirmation and idempotent replay;
- schema-v3 export;
- archive and restore with media retained;
- private original download and safe-preview delivery;
- unconfirmed draft deletion;
- confirmed aggregate deletion;
- active absence of both original and derivative Blobs after each applicable
  delete, with Azure soft-deleted retention reported separately;
- second-owner denial at every protected Photo and Photo-bearing Capture
  endpoint;
- non-cohort neutral denial while the global flag remains off;
- privacy-safe production desktop/mobile evidence; and
- homepage parity plus an ordinary-member enablement decision.

## Recommended proof mechanism

Use a **server-enforced, expiring dark-launch cohort** in the real production
application while `CAPTURE_PHOTO_ENABLED` remains false.

The cohort contains exactly two approved synthetic identities. Both identities
must pass the dark-launch gate so the second identity reaches the real
owner-resolution boundary and can prove denial against the first identity's
objects. A third signed-in synthetic identity remains outside the cohort and
proves that ordinary-member behavior stays equivalent to flag-off. No real
member account or content is used.

The access decision trusts only the `PeerSlateIdentity.user_key` produced by
the existing server authentication and internal identity mapping. Browser
owner IDs, email addresses, headers outside the trusted authentication
boundary, query values, source keys, Capture keys, Blob names, and UI state
never grant cohort access.

Before a production proof run, the owner must explicitly choose one Defender
path: (A) an approved inert EICAR-based production test with advance
security-alert coordination and documented seven-day soft-delete behavior, or
(B) no production malicious test, retaining the sanctioned isolated-account
proof and marking the production Defender-malicious path Conditional. There is
no default. A malformed or dimension-invalid image proves only application
image validation and never proves Defender malware rejection.

See:

1. [Threat model and authorization boundary](01_THREAT_MODEL_AND_AUTHORIZATION_BOUNDARY.md)
2. [Proof mechanism, configuration, rollback, and file reservations](02_PROOF_MECHANISM_AND_ROLLOUT.md)
3. [Lifecycle, two-owner, evidence, and screenshot matrix](03_PRODUCTION_EVIDENCE_MATRIX.md)
4. [Architecture completion and approval handoff](COMPLETION_REPORT.md)

## Alternatives evaluated

| Method | Decision | Reason |
| --- | --- | --- |
| Server-enforced production dark launch | **Recommended** | Proves the exact released production identity, SQL, Blob, clean-Defender, route, UI, and deletion paths while the global flag stays false and ordinary members receive neutral denial. Production Defender-malicious proof additionally requires choice A. |
| Properly isolated staging slot/environment | **Conditional supporting method** | Appropriate for rehearsal and deliberate failure injection only if identity, SQL, Storage, Defender, callbacks, telemetry, settings, managed identity, and release permissions are all isolated. Current governance does not verify that complete environment. Staging cannot by itself close production proof. |
| Temporary global flag-on production window | **Rejected now; later fallback only** | It exposes Photo to ordinary members. It requires explicit Pete and designated-manager approval, accepted and live homepage parity, an attended short window, prewritten rollback, and every dark-launch control that can still apply. |

## Package-local writable scope

This branch may add or edit only:

- `docs/initiatives/PS-CAPTURE-PHOTO-LIFECYCLE-001/`

It may not edit shared governance. It also may not edit application code,
routes, templates, CSS, JavaScript, tests, configuration, SQL, Azure scripts or
resources, Defender, production data, homepage files, or the released
`PS-CAPTURE-MEDIA-001` package.

## Approval stop

After these documents are committed and pushed, stop for designated-manager
approval. A separate assignment and fresh authorization are required before
any implementation, configuration, infrastructure, SQL, production, or
homepage action. Architecture acceptance does not authorize Photo enablement.
