# Photo Lifecycle Gate Implementation Completion Report

> **Superseded in part, 2026-07-20.** This report records the gate
> implementation lane while Defender choice B was the recorded decision. The
> owner replaced it with **choice A** the same day, and a later proof-readiness
> continuation added the proof-mode admission audit record that this lane
> deliberately left out. The release, pipeline, and verification facts below
> remain accurate; the Defender statements are superseded by
> [`02_PROOF_MECHANISM_AND_ROLLOUT.md`](02_PROOF_MECHANISM_AND_ROLLOUT.md) and
> [`04_DEFENDER_CHOICE_A_OPERATIONAL_PLAN.md`](04_DEFENDER_CHOICE_A_OPERATIONAL_PLAN.md).

## Status

- Package: `PS-CAPTURE-PHOTO-LIFECYCLE-001`
- Work type: bounded server-only dark-launch gate continuation
- Branch: `work/2026-07-20-capture-photo-lifecycle-implementation-001`
- Exact base: Azure DevOps `origin/main` at
  `531013dd8c1a05e2443becd881a226755f27ca14`
- Architecture authority: Azure PR 107 squash
  `531013dd8c1a05e2443becd881a226755f27ca14`
- Owner approval: recorded 2026-07-20
- Defender decision at the time of this lane: choice **B**; replaced the same
  day by choice **A** - see the superseding note above
- Exact implementation source:
  `f74afcea11f74b8be1b8034d98080c0c5cc38b32`
- Azure release: PR 108 squash merge
  `919adba534d70c4f3f30979b8d43e000912079c8`
- Pipeline: automatic run 158 passed Build and Deploy for the exact merge
- Package-local closeout branch:
  `work/2026-07-20-capture-photo-lifecycle-closeout-001`, exact base
  `919adba534d70c4f3f30979b8d43e000912079c8`
- Current implementation result: gate released flag-off; production lifecycle
  proof pending
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
available locally. Azure automatic pipeline 158 supplied the authoritative
Python 3.12 result and passed Build and Deploy. A redundant manual run 159 was
canceled before its deployment job began after the hidden active automatic run
was identified.

## Release and public verification

- Azure PR 108 source commit matched the exact pushed implementation SHA.
- PR target matched exact base
  `531013dd8c1a05e2443becd881a226755f27ca14`.
- Merge status succeeded with squash strategy and source-branch deletion.
- Automatic pipeline 158 passed against exact merge
  `919adba534d70c4f3f30979b8d43e000912079c8`.
- Public `GET /` returned 200 after deployment.
- Signed-out `GET /app/capture` preserved the existing sign-in redirect.
- Direct signed-out Photo GET and same-origin POST both returned the neutral
  flag-off 404 and `Photo Capture is unavailable.`
- No setting was inspected or changed, no proof identity was configured, no
  production record was created, and no Photo mode was enabled.

## Deliberate exclusions

The optional production evidence/Blob-absence verifier was not implemented.
The current repository has no reusable verifier that can prove both known Blob
locators absent without production dependencies and transient operator-only
data. Inventing a broad SQL query, container listing, setting read, or locator
log would violate the accepted boundary. That proof remains an attended,
owner-scoped production operation requiring separate approval.

No production configuration, synthetic identity, record, screenshot, Blob,
Azure resource, Defender setting, SQL object, or homepage state was inspected
or changed. This lane used no EICAR or malicious fixture and created none;
under the later recorded choice A the fixture is supplied by security during
the attended window and is never committed to this repository.

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

**Conditional.** The bounded gate implementation is released with both flags
off. Lifecycle readiness cannot become Pass until the approved production
matrix and teardown are complete. The owner has since replaced choice B with
coordinated choice A, so the production Defender-malicious row is in scope and
can reach Pass rather than being permanently Conditional.
