# PS-CAPTURE-PHOTO-LIFECYCLE-001 - Photo Lifecycle Readiness

## Approved implementation continuation - 2026-07-20

- Architecture release: Azure PR 107; squash
  `531013dd8c1a05e2443becd881a226755f27ca14`
- Owner decision: architecture approved and Defender choice **B** recorded -
  no production malicious-file test
- Implementation branch:
  `work/2026-07-20-capture-photo-lifecycle-implementation-001`
- Exact implementation base: Azure DevOps `origin/main` at
  `531013dd8c1a05e2443becd881a226755f27ca14`
- Implementation source:
  `f74afcea11f74b8be1b8034d98080c0c5cc38b32`
- Released gate: Azure PR 108 squash
  `919adba534d70c4f3f30979b8d43e000912079c8`; automatic pipeline 158 passed
  Build and Deploy
- Sole implementation writer: current Codex session
- Implementation scope: only the reserved server gate, Photo route integration,
  nonsecret configuration example, focused tests, and package-local records
- Release boundary: gate released with both Photo flags false; no production
  proof window, ordinary-member enablement, homepage change, or malicious
  fixture was authorized or performed by this continuation
- Lifecycle-readiness result: **Conditional** until the signed-in production
  evidence and teardown matrix is completed; under choice B the production
  Defender-malicious row remains Conditional

The sections below preserve the accepted architecture context. The approval
above supersedes the original pending-writer and approval-stop statements for
the bounded implementation only. It does not authorize production settings,
records, Azure, Defender, SQL, homepage, or ordinary enablement changes.

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
  owner-delegated Capture Media manager role; architecture accepted by the
  owner for the bounded continuation recorded above
- Later implementation writer: current Codex session on the separate
  implementation branch recorded above
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

The owner selected Defender path **B**: no production malicious test. Retain
the sanctioned isolated-account proof and mark the production
Defender-malicious path Conditional. A malformed or dimension-invalid image
proves only application image validation and never proves Defender malware
rejection.

See:

1. [Threat model and authorization boundary](01_THREAT_MODEL_AND_AUTHORIZATION_BOUNDARY.md)
2. [Proof mechanism, configuration, rollback, and file reservations](02_PROOF_MECHANISM_AND_ROLLOUT.md)
3. [Lifecycle, two-owner, evidence, and screenshot matrix](03_PRODUCTION_EVIDENCE_MATRIX.md)
4. [Architecture completion and approval handoff](COMPLETION_REPORT.md)
5. [Gate implementation completion report](IMPLEMENTATION_COMPLETION_REPORT.md)
6. [Claude independent-review handoff](CLAUDE_HANDOFF.md)

## Alternatives evaluated

| Method | Decision | Reason |
| --- | --- | --- |
| Server-enforced production dark launch | **Recommended** | Proves the exact released production identity, SQL, Blob, clean-Defender, route, UI, and deletion paths while the global flag stays false and ordinary members receive neutral denial. Production Defender-malicious proof additionally requires choice A. |
| Properly isolated staging slot/environment | **Conditional supporting method** | Appropriate for rehearsal and deliberate failure injection only if identity, SQL, Storage, Defender, callbacks, telemetry, settings, managed identity, and release permissions are all isolated. Current governance does not verify that complete environment. Staging cannot by itself close production proof. |
| Temporary global flag-on production window | **Rejected now; later fallback only** | It exposes Photo to ordinary members. It requires explicit Pete and designated-manager approval, accepted and live homepage parity, an attended short window, prewritten rollback, and every dark-launch control that can still apply. |

## Writable-scope record

The completed architecture branch was package-local documentation only. The
approved implementation continuation may add or edit only:

- `.env.example`;
- `owner_routes.py` for Photo gate integration only;
- `services/photo_lifecycle_access_service.py`;
- `tests/test_owner_photo_capture.py`;
- `tests/test_photo_lifecycle_access.py`; and
- `docs/initiatives/PS-CAPTURE-PHOTO-LIFECYCLE-001/`.

It may not edit any other application/runtime file, shared governance,
templates, CSS, JavaScript, SQL, Azure scripts/resources, Defender, production
data, homepage files, or the released `PS-CAPTURE-MEDIA-001` package.

## Approval stop

The architecture approval stop was satisfied on 2026-07-20 for the bounded
implementation continuation recorded at the top of this document. Stop again
before any production proof configuration or record, infrastructure, SQL,
Azure/Defender, homepage, or ordinary-member enablement action. Architecture
and gate implementation acceptance do not authorize Photo enablement.
