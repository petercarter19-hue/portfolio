# Claude Handoff - Photo Lifecycle Readiness

## One-minute status

- Package: `PS-CAPTURE-PHOTO-LIFECYCLE-001`
- Architecture: accepted and merged through Azure PR 107 at
  `531013dd8c1a05e2443becd881a226755f27ca14`
- Owner decision: Defender choice **B** - no production malicious-file test;
  the production Defender-malicious case remains Conditional
- Implementation branch:
  `work/2026-07-20-capture-photo-lifecycle-implementation-001`
- Exact base: Azure `origin/main` at
  `531013dd8c1a05e2443becd881a226755f27ca14`
- Exact pushed implementation source:
  `f74afcea11f74b8be1b8034d98080c0c5cc38b32`
- Azure release: PR 108 squash-merged successfully at
  `919adba534d70c4f3f30979b8d43e000912079c8`; source branch deleted
- Pipeline: automatic run 158 passed Build and Deploy for exact merge
  `919adba534d70c4f3f30979b8d43e000912079c8`
- Package-local closeout branch:
  `work/2026-07-20-capture-photo-lifecycle-closeout-001`, based exactly on
  `919adba534d70c4f3f30979b8d43e000912079c8`
- Current writer: Codex remains the sole writer on that closeout branch; this
  handoff is independent review input and does not transfer branch ownership
- Current result: gate implementation is released flag-off; signed-in
  production proof is not complete; lifecycle readiness is **Conditional**
- Ordinary member status: `CAPTURE_PHOTO_ENABLED` remains false; Photo is not
  live or available to ordinary members

## What is implemented locally

The continuation adds a server-only, fail-closed Photo access policy. It has
two mutually exclusive modes:

1. the existing ordinary-member flag; or
2. an expiring proof gate for exactly two server-resolved internal user keys.

Both flags true, malformed values, missing/expired expiry, invalid cohort, or
identity-resolution failure fail closed. The proof window is limited to two
hours. Browser fields, email, route keys, and UI state cannot grant access.
Non-cohort and signed-out direct Photo requests receive the same neutral 404 as
the global flag-off state, before Photo service or Blob work. The Capture page
continues to work normally but exposes Photo only to the two admitted synthetic
owners.

Reserved runtime/test changes are limited to:

- `.env.example`
- `owner_routes.py`
- `services/photo_lifecycle_access_service.py`
- `tests/test_owner_photo_capture.py`
- `tests/test_photo_lifecycle_access.py`

Package-local documents record the approval, decision, implementation, and
handoff. No template, CSS, JavaScript, SQL, Azure/Defender, homepage, shared
governance, Voice, Moment, or Placement file is changed.

## Checks completed locally

- focused compile plus gate/Photo route tests: **41 passed**
- full repository test discovery: **627 passed, 2 skipped**
- `git diff --check`: **passed**
- route inventory: all seven direct Photo GET/POST endpoints pass through the
  central gate
- denial parity: non-cohort behavior matches global flag-off for all seven
  direct endpoints and performs no Photo service call
- second owner: the server-resolved B key reaches every protected Photo service
  boundary; forged form identity/email cannot grant access
- ordinary-release compatibility: existing sign-in, cross-site-write, and
  malformed-source denial ordering is preserved

The local validation environment is an isolated temporary Python 3.13 virtual
environment with the repository's exact requirements. Azure automatic pipeline
158 is the authoritative Python 3.12 validation and passed Build and Deploy. A
redundant manual run 159, queued while the active automatic run was hidden from
the list response, was canceled before its Deploy job began.

Public signed-out verification after pipeline 158 passed:

- `GET /` returned 200;
- `GET /app/capture` returned the existing sign-in redirect;
- direct Photo GET returned neutral 404 with `Photo Capture is unavailable.`;
  and
- direct Photo POST returned the same neutral 404 without a record or payload.

## What remains

1. Obtain a separately approved attended proof window and secure operator
   provisioning of exactly two synthetic cohort identities plus synthetic C.
2. Run the complete production evidence matrix, production screenshots,
   second-owner denial checks, owner-scoped teardown, active original/
   derivative Blob absence, soft-delete retention classification, rollback,
   and final privacy review.
3. Under choice B, do not upload EICAR or any malicious-test fixture. Do not use
   an application-invalid image as Defender proof.

Dark-launch proof does not depend on homepage parity. Ordinary-member Photo
enablement does, and Photo homepage work remains serialized after active
Interview homepage work. No PR merge or proof result authorizes ordinary
enablement.

## Review guardrails for Claude

Review this report and the released merge independently. Do not blend a
separate Claude document set into this package. Flag any safety, scope, or test
concern back to the owner. Do not inspect secret settings, create production
records, change Azure, Defender, SQL, homepage files, or enable either Photo
mode without a new explicit production-proof assignment.
