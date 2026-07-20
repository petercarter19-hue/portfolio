# PS-CAPTURE-PHOTO-LIFECYCLE-001 - Defender Choice A Operational Plan

## Recorded decision

**2026-07-20: the owner selected Defender choice A** - a coordinated inert
production test - replacing the same-day choice B. This document is the
operational plan that choice A requires under
[`02_PROOF_MECHANISM_AND_ROLLOUT.md`](02_PROOF_MECHANISM_AND_ROLLOUT.md).

This document authorizes nothing by itself. It is the plan to be executed
inside the separately approved attended proof window described in
[`05_PROOF_WINDOW_RUN_CHECKLIST.md`](05_PROOF_WINDOW_RUN_CHECKLIST.md), while
`CAPTURE_PHOTO_ENABLED` remains false.

## What is actually being uploaded, in plain English

EICAR is a short, deliberately harmless text string published by the European
Institute for Computer Antivirus Research. It contains no executable payload,
no exploit, and no malicious behaviour. It exists for exactly one purpose: so
that an organisation can confirm its antivirus scanning is switched on and
working, without ever handling real malware.

Every mainstream scanner, including Microsoft Defender for Storage, is built to
report it as malicious on sight. **Defender will flag it, will raise an alert,
and will quarantine the Blob. That is the point.** A Defender verdict of
malicious is the success condition for this row, not an incident.

Two consequences follow, and both are handled below:

1. A real alert will land in whatever queue receives Defender for Storage
   alerts. If nobody was told in advance, a responder will reasonably treat it
   as a live malware event. Advance notification is therefore mandatory, not
   courteous.
2. The bytes are recognised by scanners everywhere. They must never enter the
   repository, a commit, a screenshot, a chat message, a ticket body, or any
   evidence artifact. Committing them would trip scanners on every clone, CI
   run, and developer laptop indefinitely.

## Fixture custody and handling

| Rule | Requirement |
| --- | --- |
| Provenance | Security/operations supplies the exact fixture. The implementation lane does not author, generate, reconstruct from memory, or download it. |
| Composition | The approved fixture is the inert EICAR-based test content presented with an image content type and filename so it reaches the normal Photo upload path. Security approves the exact composition in advance. |
| No mutation | The fixture is not disguised, re-encoded, padded, wrapped, or altered to slip past application image validation. Any such change invalidates the row. |
| Repository | The fixture never enters this repository in any form - not the bytes, not a base64 or hex form, not a fragment, not a generator that reconstructs it, not an attachment, not a screenshot of its contents. |
| Transport | The fixture travels only through the approved security channel to the attended operator workstation. It is not emailed to a wider list, pasted into chat, or stored in shared drives. |
| Local custody | It exists on the operator workstation only for the duration of the window, in one named location, and is deleted at teardown. |
| Single use | Exactly one upload, by Synthetic Owner A, once. No retries with variants. If the upload fails mechanically, stop and consult security before a second attempt. |
| Naming | Evidence refers to it only by the alias `A-defender-malicious`. |

## Advance notification - who must be told, and what they must be told

Notification is a hard precondition. If any required acknowledgement is
missing when the window opens, the malicious row is skipped and recorded
Conditional; the remainder of the window may still proceed.

| Who | Why they must be notified | Required acknowledgement |
| --- | --- | --- |
| Defender for Storage alert owner / security responder on duty | They receive the alert. Without notice they will open a live malware incident. | Written acknowledgement naming the date, window, storage scope, and that a single planned inert test fixture will trigger one malicious verdict. |
| Azure subscription / storage account owner | Remediation acts on their resource; quarantine and soft-delete state will change. | Written acknowledgement of the expected quarantine and the seven-day soft-delete retention consequence. |
| Whoever holds the on-call or paging rotation covering that alert channel | An out-of-hours page must not escalate. | Confirmation that the rotation holder for the exact window is aware. |
| Pete (owner) | Owner of the decision and the stop authority. | The recorded choice A decision plus confirmation of the scheduled window. |
| Designated session manager for the package | Sequencing and acceptance authority. | Confirmation the window is scheduled and no conflicting lane is active. |
| Any external monitoring, SIEM, or managed-detection provider, if one is connected to this subscription | They may escalate independently of internal channels. | Written acknowledgement, or an explicit written confirmation that no such provider is connected. |

The notification message states: the exact UTC window, the storage account
scope, that one inert EICAR-based test fixture will be uploaded once, that
Defender is expected to report malicious and quarantine, the stop contact, and
the expected all-clear time. It does not contain the fixture bytes, identity
keys, or locators.

A single named person is on the notification channel throughout the window and
can be reached immediately.

## Expected application behaviour

The application must reach the documented `rejected` state through the normal
path. The expected transition is:

```text
upload accepted (bounded size/type)     -> state: scanning
Defender scans the original Blob        -> Defender-owned verdict: malicious
application reconciles the scan result  -> state: rejected, stable safe code
provider remediation acts on the Blob   -> original locator actively absent
```

Requirements for the row to count:

- The verdict is **Defender-owned**. The application must not have rejected the
  bytes earlier on its own image validation. If application image validation
  stops the fixture before Defender returns a verdict, this row is recorded
  **Conditional** - it is not relabelled as Defender evidence, and it is not
  retried with a modified fixture.
- The application state reaches `rejected`, not `failed`, `needs_review`, or
  `confirmed`.
- The member-facing surface shows a neutral rejection with no malware family
  name, no provider payload, no scanner detail, and no image preview.
- The reported safe error code is stable and identical in shape to other safe
  rejection codes.

## Required negative proofs

Every one of these must be verified and recorded for the row to pass. Each is a
separate observation, not an inference from the state name.

| # | Negative proof | How it is checked |
| --- | --- | --- |
| 1 | No preview | `GET /app/capture/photo/<source>/preview` as A returns the media-not-found response and zero bytes. |
| 2 | No original download | `GET /app/capture/photo/<source>/original` as A returns the media-not-found response and zero bytes, with no attachment header revealing type. |
| 3 | No confirmation | `POST /app/capture/photo/<source>/confirm` as A with a valid note and confirmation token is refused; no Capture is created. |
| 4 | No derivative | No safe derivative was ever produced; the status payload carries no derivative type, byte length, or dimensions. |
| 5 | No Capture | A's Capture list count is unchanged from immediately before the upload. |
| 6 | No source link | No Capture Media link row references this source. |
| 7 | No downstream write | A's Moment, Placement, audience, share, publication, and projection counts are unchanged, checked owner-scoped before and after. |
| 8 | No second-owner signal | B's requests against this source are indistinguishable from B's requests against a random absent key, at every endpoint in the second-owner matrix. |
| 9 | No non-cohort exposure | C sees no Photo surface and receives flag-off-equivalent responses throughout. |
| 10 | No leak in the rejection | The rejection response, page, and any log line contain no Blob name, container, account, SAS, digest, client filename, or provider payload. |
| 11 | No proof-audit leak | The proof-mode admission audit line contains only `access_mode` and `run_id`, as specified in [`06_PROOF_ADMISSION_AUDIT_RECORD.md`](06_PROOF_ADMISSION_AUDIT_RECORD.md). |

Proofs 1 through 4 are attempted deliberately and must fail. Do not skip them
because the state already reads `rejected`; the point of the row is that the
refusal is enforced, not merely displayed.

## Remediation and cleanup

1. Let Defender's configured remediation run its normal course. Do not
   hand-delete the Blob to make the evidence tidier, and do not change any
   Defender or Storage setting during the window.
2. Confirm with the notified security owner that the alert is closed as the
   planned test, referencing the run id, not the fixture content.
3. Delete the application-side draft through A's owner-scoped draft-delete
   endpoint, exactly as for any other synthetic draft.
4. Run the locator-specific active-absence check for the original locator. No
   derivative was created, so its retention classification is
   `soft_deleted_retention_not_applicable`.
5. Delete the fixture file from the operator workstation and empty its local
   trash. Confirm it is not in a synced folder, clipboard history, or shell
   history.
6. Confirm no fixture content reached any commit, screenshot, ticket, or chat
   message.

## Active-absence checks and the retention truth

The verifier holds the original locator transiently in process memory only. It
emits booleans and a retention classification, never the locator.

Recorded result for this row:

```text
original_active_absent=true
derivative_active_absent=true   (no derivative was ever created)
retention=soft_deleted_retention_expected
```

**Active absence is not permanent erasure, and this plan does not claim it is.**

- *Active absence* means the known locator is no longer an active Blob readable
  through the application's normal managed-identity path, and the owning SQL
  lifecycle can safely finalize and clear that locator.
- The current authority configures Blob soft delete with a **seven-day recovery
  window**. Azure may still hold recoverable bytes for that period after
  remediation and after the application-side delete.
- Therefore the correct same-window statement is: *the fixture is actively
  absent from the application, and provider-side soft-deleted retention is
  expected for up to seven days.*

No same-window screenshot, `exists=false` result, or application response may be
described as permanent absence. A permanent-absence claim requires a separately
approved, locator-specific check performed **after** the retention window
elapses. That check is explicitly out of scope for this window and is not a
condition of accepting the row. If a permanent-absence claim is later needed,
it is its own approved follow-up task.

Because this fixture is inert and carries no payload, retained soft-deleted
bytes present no residual risk beyond the ordinary soft-delete behaviour of any
other deleted synthetic Blob.

## Stop conditions specific to this row

Stop the malicious row - and, where indicated, the whole window - for any of the
following. Skipping the row and recording it Conditional is always an
acceptable outcome; improvising is not.

| Condition | Action |
| --- | --- |
| Any required advance acknowledgement is missing or unconfirmed when the window opens | Skip the row. Record Conditional. Continue the rest of the window. |
| The named security contact is unreachable at upload time | Skip the row. Record Conditional. |
| Application image validation rejects the fixture before a Defender verdict | Record the row Conditional. Do not modify the fixture. Do not relabel the application rejection as Defender evidence. |
| Defender returns clean, or no verdict arrives within the agreed wait | Record Conditional. Do not upload a second or altered fixture. |
| An alert reaches an unnotified party, or names anything beyond the single synthetic fixture | **Hard stop the window.** Disable the proof gate. Treat as a real incident until security says otherwise. |
| Any preview, download, confirmation, derivative, Capture, link, or downstream write occurs for the rejected source | **Hard stop and Fail.** This is a safety-invariant violation. |
| Any Blob locator, SAS, credential, provider payload, or identity value appears in a response, log, or screenshot | **Hard stop and Fail.** |
| The fixture is found in a commit, staged change, screenshot, or evidence artifact | **Hard stop.** Remove before any push. Report it. |
| Storage, Defender, or the application shows unrelated degradation during the window | Pause. Record Conditional. Do not manufacture recovery states. |
| Remediation does not complete, or the original remains actively present after the agreed wait | Record Conditional and escalate. Do not force-delete around the provider. |

Immediate rollback for the whole window is unchanged: set
`CAPTURE_PHOTO_LIFECYCLE_PROOF_ENABLED=false`. Because `CAPTURE_PHOTO_ENABLED`
remains false throughout, that returns every identity to flag-off behaviour, and
the configured expiry provides automatic rollback if no operator can act.

## Evidence this row produces

- The advance coordination record, identified by reference only, with no
  operational secrets.
- The Defender-owned malicious outcome, described without malware family names
  or provider payloads.
- Desktop 1440x900 and mobile 390x844 screenshots of the neutral rejection
  state, with no image preview and no scanner detail.
- The eleven negative proofs above, as booleans and route-class outcomes.
- `original_active_absent=true`, `derivative_active_absent=true`, and
  `retention=soft_deleted_retention_expected`.
- The security owner's confirmation that the alert was closed as the planned
  test.
- The proof-mode admission audit line for the run, quoted verbatim.

## Result recording

- **Pass** for this row requires the Defender-owned malicious verdict, the
  `rejected` application state, all eleven negative proofs, both active-absence
  booleans, honest retention classification, both screenshots, and the closed
  alert.
- **Conditional** for this row is the correct, expected result whenever
  coordination lapses, the verdict does not arrive, or application validation
  intercepts first. A Conditional row does not make the window a failure.
- **Fail** applies only to a safety-invariant violation, not to a skipped row.

A Pass on this row does not authorize ordinary-member Photo enablement. That
remains blocked on the full matrix, teardown, accepted and live Photo homepage
parity, and a separate explicit owner and manager decision.
