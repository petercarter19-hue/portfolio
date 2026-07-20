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
- Current writer: Codex remains the sole writer on this branch; this handoff is
  independent review/coordination input and does not transfer branch ownership
- Current result: local implementation tests pass; release and signed-in
  production proof are not yet complete; lifecycle readiness is **Conditional**
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
environment with the repository's exact requirements. The Azure pipeline is
the authoritative Python 3.12 validation and remains pending until release.

## What remains

1. Complete the final diff/privacy/scope review, commit, and push.
2. Release only through an Azure PR and green pipeline with both Photo flags
   false.
3. Obtain a separately approved attended proof window and secure operator
   provisioning of exactly two synthetic cohort identities plus synthetic C.
4. Run the complete production evidence matrix, production screenshots,
   second-owner denial checks, owner-scoped teardown, active original/
   derivative Blob absence, soft-delete retention classification, rollback,
   and final privacy review.
5. Under choice B, do not upload EICAR or any malicious-test fixture. Do not use
   an application-invalid image as Defender proof.

Dark-launch proof does not depend on homepage parity. Ordinary-member Photo
enablement does, and Photo homepage work remains serialized after active
Interview homepage work. No PR merge or proof result authorizes ordinary
enablement.

## Review guardrails for Claude

Review this report and the branch independently. Do not edit this branch or
blend a separate Claude document set into the package while Codex remains the
sole writer. Flag any safety, scope, or test concern back to the owner/Codex.
Do not inspect secret settings, create production records, change Azure,
Defender, SQL, homepage files, or enable either Photo mode.
