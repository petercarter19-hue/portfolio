# Photo Lifecycle Gate Implementation Completion Report

## Status

- Package: `PS-CAPTURE-PHOTO-LIFECYCLE-001`
- Work type: bounded server-only dark-launch gate continuation
- Branch: `work/2026-07-20-capture-photo-lifecycle-implementation-001`
- Exact base: Azure DevOps `origin/main` at
  `531013dd8c1a05e2443becd881a226755f27ca14`
- Architecture authority: Azure PR 107 squash
  `531013dd8c1a05e2443becd881a226755f27ca14`
- Owner approval: recorded 2026-07-20
- Defender decision: choice **B** - no production malicious-file test
- Current implementation result: local gate implementation complete and
  validation green; Azure release and production lifecycle proof pending
- Lifecycle-readiness result: **Conditional**
- Ordinary-member status: `CAPTURE_PHOTO_ENABLED=false`; Photo is not claimed
  live

## Technical result

The implementation replaces the former single Photo flag check with one
central server policy. It preserves ordinary-release behavior when only
`CAPTURE_PHOTO_ENABLED` is true and adds a separate proof mode that requires:

- `CAPTURE_PHOTO_ENABLED=false`;
- an explicitly true proof flag;
- exactly two distinct, syntactically bounded internal user keys;
- a future UTC expiry no more than two hours from evaluation; and
- an optional nonsecret bounded run label.

The policy trusts only the `PeerSlateIdentity.user_key` resolved by the existing
server authentication and identity mapping. It never uses browser identity,
email, source keys, or UI state as authorization. Both modes true and all
malformed, missing, conflicting, or expired proof configurations fail closed.

The Capture page computes Photo visibility from this policy. Every direct
Photo route calls the same policy before source-key parsing, same-origin
validation, Photo SQL, or Blob access for a denied request. During proof mode,
signed-out, identity-storage-failure, and non-cohort requests receive the same
neutral `Photo Capture is unavailable.` 404 as the global flag-off state.
Ordinary-release sign-in and service-unavailable behavior is preserved.

## Changed files

Runtime and test scope:

- `.env.example`
- `owner_routes.py`
- `services/photo_lifecycle_access_service.py`
- `tests/test_owner_photo_capture.py`
- `tests/test_photo_lifecycle_access.py`

Package-local records:

- `docs/initiatives/PS-CAPTURE-PHOTO-LIFECYCLE-001/README.md`
- `docs/initiatives/PS-CAPTURE-PHOTO-LIFECYCLE-001/02_PROOF_MECHANISM_AND_ROLLOUT.md`
- `docs/initiatives/PS-CAPTURE-PHOTO-LIFECYCLE-001/03_PRODUCTION_EVIDENCE_MATRIX.md`
- `docs/initiatives/PS-CAPTURE-PHOTO-LIFECYCLE-001/COMPLETION_REPORT.md`
- `docs/initiatives/PS-CAPTURE-PHOTO-LIFECYCLE-001/CLAUDE_HANDOFF.md`
- `docs/initiatives/PS-CAPTURE-PHOTO-LIFECYCLE-001/IMPLEMENTATION_COMPLETION_REPORT.md`

No application bootstrap, identity, template, CSS, JavaScript, SQL, migration,
Azure/Defender, homepage, shared-governance, Voice, Moment, Placement, or Owner
Home file changed.

## Configuration contract

The nonsecret example records names and safe empty/off defaults only:

- `CAPTURE_PHOTO_LIFECYCLE_PROOF_ENABLED=false`
- `CAPTURE_PHOTO_LIFECYCLE_PROOF_USER_KEYS=`
- `CAPTURE_PHOTO_LIFECYCLE_PROOF_EXPIRES_AT_UTC=`
- `CAPTURE_PHOTO_LIFECYCLE_PROOF_RUN_ID=`

No real identity key, setting value, token, credential, connection material, or
Blob locator was read, printed, committed, or placed in evidence.

## Validation

- startup authority/workflow review: passed
- exact branch/base verification: passed
- Python compile for all changed runtime/test modules: passed
- focused access-policy and Photo route suite: 41 passed
- full repository suite: 627 passed, 2 skipped
- direct Photo route inventory: 7/7 centrally gated
- non-cohort direct-route flag-off parity: 7/7 passed with zero Photo service
  calls
- second synthetic owner service-boundary propagation: passed for upload,
  status, reconcile, confirm, draft delete, preview, and original
- browser identity/email forgery denial: passed
- ordinary-release sign-in, cross-site-write, and malformed-source ordering:
  preserved
- configuration conflict, expiry, invalid-shape, and automatic-expiry tests:
  passed
- whitespace/error diff check: passed

The local full suite used a temporary Python 3.13 virtual environment with the
repository's exact requirements because a Python 3.12 executable was not
available locally. The Azure pipeline's Python 3.12 result remains the release
authority and is pending.

## Deliberate exclusions

The optional production evidence/Blob-absence verifier was not implemented.
The current repository has no reusable verifier that can prove both known Blob
locators absent without production dependencies and transient operator-only
data. Inventing a broad SQL query, container listing, setting read, or locator
log would violate the accepted boundary. That proof remains an attended,
owner-scoped production operation requiring separate approval.

No production configuration, synthetic identity, record, screenshot, Blob,
Azure resource, Defender setting, SQL object, or homepage state was inspected
or changed. Option B means no production EICAR or malicious fixture will be
used; the production Defender-malicious path remains Conditional.

## Release and proof boundary

The implementation may be released only with both Photo flags false. A green
release proves deployability, not the signed-in lifecycle. A later attended
proof window must still complete every row in
`03_PRODUCTION_EVIDENCE_MATRIX.md`, including pending, clean, separate
application-validation rejection, recoverable error, confirmed, correction,
export, archive, restore, download, draft delete, confirmed delete,
second-owner denial, both-Blob active absence, soft-delete retention reporting,
screenshots, teardown, automatic expiry, and rollback.

Dark-launch proof does not depend on homepage parity. Ordinary-member Photo
enablement remains blocked on accepted/live Photo homepage parity after the
active Interview homepage lane, plus a new explicit owner/manager decision.

## Recommendation

**Conditional.** The bounded gate implementation is locally ready for release
with both flags off. Lifecycle readiness cannot become Pass until the approved
production matrix and teardown are complete; choice B permanently leaves the
production Defender-malicious row Conditional unless a later owner decision
replaces it with coordinated choice A.
