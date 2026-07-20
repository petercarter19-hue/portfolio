# PS-CAPTURE-PHOTO-LIFECYCLE-001 - Proof Window Run Checklist

One document to follow start to finish on the day. Everything here is derived
from the released gate in `services/photo_lifecycle_access_service.py` and the
Photo routes in `owner_routes.py`, so the constraints are the real ones the
server enforces, not restatements of intent.

**This checklist does not authorize the window.** Scheduling it requires the
owner's approval of a specific date and the completed entry gate in
[`02_PROOF_MECHANISM_AND_ROLLOUT.md`](02_PROOF_MECHANISM_AND_ROLLOUT.md).

> `CAPTURE_PHOTO_ENABLED` is **false** before, during, and after this window.
> Nothing in this document changes it. If anyone proposes setting it true, stop.

## 0. The hard clock

The server caps a proof window at **two hours**. The gate fails closed the
moment the configured expiry passes - no operator action required, and no
warning. Plan accordingly:

- Budget the run at **90 minutes** of work inside a 2-hour expiry.
- If the run overruns, the gate simply closes and every identity drops to
  flag-off behaviour. Nothing breaks; the run is just interrupted.
- To continue after an overrun, set a **new** expiry through the operator path.
  This is a new window and produces a new admission audit line. Record both.
- Do not attempt to extend by more than two hours from the moment of
  reconfiguration. The server rejects it and fails closed.

Recommended running order puts the irreversible-feeling work early and the
Defender row where a stop is cheapest: see section 5.

## 1. Roles for the day

| Role | Responsibility |
| --- | --- |
| Operator | Sets and removes the four settings through the approved secure path. The only person who touches configuration. |
| Evidence recorder | Runs the matrix, captures screenshots, keeps the run log. Never reads or records setting values. |
| Security contact | Notified alert owner, reachable throughout, confirms the Defender alert is closed as the planned test. |
| Stop authority | Pete or the designated session manager. Can halt the window at any point. |

One person may hold more than one role, but the security contact must be a real
second person who can be reached.

## 2. Preconditions - all must be true before anything is set

Tick every line. A single unticked line means the window does not open.

**Authority and code**

- [ ] The owner has approved this specific date and window.
- [ ] `origin/main` fetched; production is on the expected release SHA.
- [ ] The released application includes the proof gate and the proof-mode
      admission audit record.
- [ ] `CAPTURE_PHOTO_ENABLED` independently confirmed **false** without listing
      or printing settings.
- [ ] `CAPTURE_PHOTO_LIFECYCLE_PROOF_ENABLED` confirmed **false**.
- [ ] No other active branch has acquired any reserved runtime file for this
      package.

**Identities**

- [ ] Synthetic A, B, and C exist through the normal external identity flow.
- [ ] No real member account is used anywhere in this window.
- [ ] A and B have zero pre-existing live Capture Media records (owner-scoped
      check only).
- [ ] C has no Photo access and no Photo records.
- [ ] The operator holds A's and B's exact internal user keys through the secure
      path. The evidence recorder does **not** have them.

**Fixtures**

- [ ] Synthetic clean JPEG/PNG images approved: generated geometric or colour
      content, no person, location, organisation, device metadata, or
      confidential text.
- [ ] Synthetic note text approved: package/run alias plus an explicit
      `synthetic proof` label only.
- [ ] `A-image-invalid` fixture approved: malformed or dimension-invalid image.
      This is application-validation evidence only and can never be Defender
      evidence.
- [ ] `A-defender-malicious` fixture supplied by security per
      [`04_DEFENDER_CHOICE_A_OPERATIONAL_PLAN.md`](04_DEFENDER_CHOICE_A_OPERATIONAL_PLAN.md),
      present on the operator workstation only, and confirmed **not** present
      anywhere in the repository or a staged change.

**Defender choice A coordination**

- [ ] Every party in the notification table of the operational plan has
      acknowledged in writing.
- [ ] The security contact is confirmed reachable for the whole window.
- [ ] The expected alert, remediation, and all-clear time are agreed.
- [ ] If any of the above is missing: the malicious row is **skipped and
      recorded Conditional**, and the rest of the window may proceed. Decide and
      record this now, not mid-run.

**Health and readiness**

- [ ] Defender cap and health, application health, pipeline health, and the
      deletion backlog are within approved thresholds - observed only, changed
      never.
- [ ] The evidence template, screenshot list, and run log are ready.
- [ ] The rollback action is written down and understood by the operator.

## 3. The three synthetic identities

| Alias | Cohort | Role in the window | Must never |
| --- | --- | --- | --- |
| **Synthetic A** | In cohort | Owns the full lifecycle: pending, clean, review, confirm, correct, export, archive, restore, download, draft delete, confirmed delete. Also owns the application-invalid fixture and the Defender fixture. | Read any real member content. |
| **Synthetic B** | In cohort | Creates exactly one B-owned control record, then attempts every protected A endpoint to prove the second-owner boundary is real and not just a UI absence. | Obtain A's keys from any application response. |
| **Synthetic C** | **Not** in cohort | Proves ordinary-member behaviour is unchanged: no Photo surface, no Photo route difference, no disclosure that a cohort or window exists. | Be added to the cohort for convenience. |

The cohort holds **exactly two** keys. The server rejects one key, three keys,
duplicates, or a key containing `@`, and fails closed. C is never in it.

Evidence uses these aliases only. Emails, subjects, issuers, internal keys,
cookies, and headers are not evidence and are never written down.

## 4. Configuration - the four settings

The operator sets these four through the approved secure operator path. The
fifth Photo setting, `CAPTURE_PHOTO_ENABLED`, is **not touched**.

> Values are never committed, printed to a terminal that is being recorded,
> echoed into the run log, read back into evidence, or captured in a
> screenshot. The evidence recorder never sees them. If a value is accidentally
> displayed, treat the window as compromised for evidence purposes, rotate the
> synthetic identities, and restart.

| # | Setting | What the operator sets | Server rules that will fail it closed |
| --- | --- | --- | --- |
| 1 | `CAPTURE_PHOTO_LIFECYCLE_PROOF_ENABLED` | `true` | Anything not in `1/true/yes/on` (case-insensitive) is false or invalid. Both this and `CAPTURE_PHOTO_ENABLED` true is invalid. |
| 2 | `CAPTURE_PHOTO_LIFECYCLE_PROOF_USER_KEYS` | A's and B's exact internal user keys, comma or space separated | Must be exactly two distinct keys. Each must match `^[A-Za-z0-9][A-Za-z0-9._:-]{0,199}$` and must not contain `@`. One, three, duplicate, or malformed keys fail closed. |
| 3 | `CAPTURE_PHOTO_LIFECYCLE_PROOF_EXPIRES_AT_UTC` | RFC 3339 UTC instant, e.g. `2026-07-27T15:30:00Z` | Must parse, must be UTC (`Z` or `+00:00` - a naive or offset timestamp is rejected), must be in the future, and must be no more than two hours ahead. |
| 4 | `CAPTURE_PHOTO_LIFECYCLE_PROOF_RUN_ID` | A nonsecret run label, e.g. `PS-CAPTURE-PHOTO-LIFECYCLE-001-2026-07-27-run-1` | Must match `^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$`. **No colons and no spaces** - a colon is valid in a user key but not here. A malformed value fails the whole window closed. Empty is allowed but wastes the audit record. |

Set the run id. It is the only correlation label that reaches the server log,
and it is what makes the admission audit record worth having.

**Immediately after setting, before any test action:**

- [ ] A loads `/app/capture` and the Photo surface is present.
- [ ] The server log contains exactly one line matching
      `PeerSlate Photo lifecycle proof admission. access_mode=proof run_id=<your run id>`
      per application worker. Quote it verbatim into the run log. If this line
      is **absent**, proof mode is not actually admitting - stop and diagnose
      before creating any record.
- [ ] The line contains no user key, cohort value, expiry, or email. Confirm by
      reading it.

If the settings were wrong in any way, the gate fails closed and A simply sees
flag-off behaviour. That is the expected symptom of a configuration error - it
is not a bug. Recheck the four rules above.

## 5. Ordered execution sequence

Each step records its result as Pass, Conditional, or Fail in the run log before
the next step begins.

**Phase 1 - neutrality first (do this before creating anything)**

1. [ ] C loads `/app/capture`: no Photo selector, modal, script, draft, or
       capability copy.
2. [ ] C requests `GET /app/capture?photo=<random key>`: identical to flag-off.
3. [ ] C requests all seven direct Photo routes: each identical to flag-off,
       with no cohort reason, route detail, expiry, or key-validity signal.
4. [ ] Signed-out direct Photo GET and POST: neutral flag-off 404, not a
       sign-in redirect.
5. [ ] A and B load `/app/capture`: Photo present, and **no real member data
       anywhere on the page**.

**Phase 2 - the clean lifecycle (A)**

6. [ ] A uploads `A-clean-confirmed`. Expect 201, state `scanning`. Record that
       the response carries no preview or original URL.
7. [ ] Pending state: preview, original, and confirm are all unavailable. No
       Capture, no link.
8. [ ] Screenshots: desktop 1440x900 and mobile 390x844 scan-pending.
9. [ ] A reconciles after Defender reports clean. Expect `needs_review` with a
       metadata-free derivative of bounded type, bytes, and dimensions.
10. [ ] Screenshots: desktop and mobile known-clean review with synthetic image
        and note.
11. [ ] A confirms with a nonempty synthetic note and explicit confirmation.
        Expect exactly one private `capture_type=photo` Capture and one source
        link.
12. [ ] Replay the confirm. Expect the existing result, not a duplicate.
13. [ ] Screenshots: desktop and mobile confirmed private Capture and list.

**Phase 3 - the rejection rows (A)**

14. [ ] A uploads `A-image-invalid`. Expect application validation rejection
        with a stable safe code. Record that the evidence names the
        **application validator, not Defender**. No preview, confirm, Capture,
        link, or downstream write.
15. [ ] Screenshots: desktop and mobile application-validation rejection, with
        no image preview.
16. [ ] **Defender choice A row.** Confirm the security contact is live on the
        channel right now. Then follow
        [`04_DEFENDER_CHOICE_A_OPERATIONAL_PLAN.md`](04_DEFENDER_CHOICE_A_OPERATIONAL_PLAN.md)
        end to end: single upload of `A-defender-malicious`, Defender-owned
        malicious verdict, application state `rejected`, all eleven negative
        proofs, both screenshots, remediation, alert closed as planned test,
        active absence, and `retention=soft_deleted_retention_expected`.
        Skipping this row and recording it Conditional is an acceptable
        outcome at any point.

**Phase 4 - error and recovery (A)**

17. [ ] A submits an obsolete row-version or an invalid required-note
        confirmation. Expect the existing changed/validation error and an
        understandable recovery. State and both Blobs unchanged; no duplicate
        Capture or link.
18. [ ] Screenshots: desktop and mobile stale/concurrency error plus recovery.
19. [ ] Do **not** induce a Storage or Defender outage to manufacture an error
        screenshot.

**Phase 5 - the rest of the A lifecycle**

20. [ ] Correction: one new revision; immutable original note and source bytes
        unchanged; no Blob change; no downstream write; stale token denied.
21. [ ] Export `GET /app/capture/<capture>/export`: `peerslate.capture.export`,
        schema version 3, app-mediated paths only. No Blob name, account,
        container, SAS, digest, identity, provider payload, or binary. Headers
        private/no-store/nosniff. **Do not screenshot the JSON** - it contains
        opaque keys. Text evidence only.
22. [ ] Archive, then restore. Both Blobs still exist; source and link
        retained. Screenshots at the most informative viewport.
23. [ ] Download the private original: attachment, generic name, exact
        synthetic bytes, private/no-store/nosniff, no redirect to Blob or SAS.
24. [ ] Request the safe preview: derivative only, same headers.

**Phase 6 - the second-owner boundary (B)**

25. [ ] B creates its one `B-owner-control` record.
26. [ ] For **every** endpoint in the second-owner denial matrix of
        [`03_PRODUCTION_EVIDENCE_MATRIX.md`](03_PRODUCTION_EVIDENCE_MATRIX.md),
        B sends the request first with a random absent key and then with A's
        valid key. Status, body shape, redirect target, and cache/security
        headers must be equivalent.
27. [ ] After each denial, A immediately re-verifies its own expected state.
28. [ ] Owner-scoped check: B caused no A audit event that falsely claims a
        successful member action.

**Phase 7 - accessibility and responsive evidence (A)**

29. [ ] Visible keyboard focus on the dominant Photo action and on the
        destructive confirmation.
30. [ ] Native 200% zoom and reflow with zero page-level horizontal overflow.
31. [ ] Mobile landscape or equivalent narrow height, with save reachable.
32. [ ] Long synthetic note and long error text; virtual-keyboard-safe mobile
        review.
33. [ ] Reduced-motion static status behaviour.
34. [ ] No-JavaScript Type fallback, with Photo absent as an enhanced path.

**Phase 8 - deletion and active absence**

35. [ ] A deletes `A-clean-draft-delete`. Delete reports success **only after**
        active storage absence and SQL finalization. Record
        `original_active_absent=true`, `derivative_active_absent=true`, and the
        retention classification separately. No Capture or link. Content fields
        cleared. Repeat delete is safe and neutral.
36. [ ] A deletes `A-clean-confirmed` through the generic Capture deletion
        endpoint. Both Blobs actively absent; link removed; Capture and revision
        content removed under the existing tombstone contract; no confirmed
        Moment deleted.
37. [ ] Screenshots: deletion-complete state, plus a deletion-pending state only
        if it occurs naturally. Do not break Storage to manufacture a retry.
38. [ ] B deletes its control record. Both Blobs actively absent where created.

## 6. Evidence rows to record

Every row gets alias, UTC time, route class, HTTP outcome, state name,
Pass/Conditional/Fail, and the exact production SHA.

| Row | Evidence type |
| --- | --- |
| Non-cohort C neutrality, all surfaces | Machine/text |
| Signed-out neutral denial | Machine/text |
| Proof-mode admission audit line, verbatim | Server log line |
| Pending | Screenshots + machine |
| Clean / needs_review | Screenshots + machine |
| Application image-validation rejection | Screenshots + machine |
| Defender-malicious rejection | Screenshots + machine + alert-closed confirmation |
| Recoverable error and recovery | Screenshots + machine |
| Confirmed, and idempotent replay | Screenshots + machine |
| Correction | Machine |
| Export, schema v3 | Text only, never a screenshot |
| Archive and restore | Screenshots + machine |
| Original download and safe preview | Machine, including headers |
| Every second-owner denial endpoint | Machine |
| Draft delete, both Blobs | Machine booleans + retention |
| Confirmed delete, both Blobs | Machine booleans + retention |
| Focus, 200% zoom, landscape, long text, reduced motion, no-JS | Screenshots |
| Final teardown zero-live-record check | Machine |
| Both flags false after removal | Machine |

**Never collect:** HAR files, cookies, tokens, Easy Auth or request headers,
browser profiles, credentials, App Service settings, SQL connection material,
portal screenshots, external identity claims, email, internal user or account
keys, source or Capture keys, Blob names, storage locators, SAS values, hashes,
ETags, provider payloads, malware detail, exact telemetry correlation IDs, or
any real member content.

If redaction would be needed, regenerate the evidence without the sensitive
field. Never commit a redacted secret-bearing capture.

## 7. Teardown

Do this **before** removing the cohort, while the gate is still active.

1. [ ] Stop creating new sources.
2. [ ] Every unconfirmed A and B draft deleted through its owner-scoped
       endpoint, with both Blobs actively absent verified before success and
       retention recorded separately.
3. [ ] Every confirmed A and B Photo Capture deleted through the generic
       Capture deletion endpoint; source link gone; Capture and revision
       content follows the existing tombstone contract; both Blobs actively
       absent.
4. [ ] A and B have zero live Photo Captures, zero live Capture Media links,
       and zero source rows containing locators, digests, dimensions, scan
       detail, or draft payload. Body-free lifecycle and audit tombstones
       allowed by the released contract may remain.
5. [ ] No synthetic Moment, Placement, audience, share, publication, or
       projection was created.
6. [ ] The Defender fixture is deleted from the operator workstation and is
       confirmed absent from the repository, any staged change, and any
       evidence artifact.
7. [ ] The transient alias-to-key map is destroyed. It is never a repository
       artifact.
8. [ ] Final privacy scan of every log line and screenshot before anything is
       committed.

## 8. Rollback triggers

**Immediate rollback action:** set
`CAPTURE_PHOTO_LIFECYCLE_PROOF_ENABLED=false`. Because
`CAPTURE_PHOTO_ENABLED` remains false, every identity returns to the flag-off
boundary at once. The configured expiry is an independent automatic rollback if
no operator can act. Rollback deletes no SQL, Storage, or Azure resource and
does not touch Voice or text Capture.

Hard-stop and roll back immediately for:

- [ ] any non-cohort Photo access or UI exposure;
- [ ] any cross-owner state, media, export, mutation, or
      distinguishable-existence result;
- [ ] any Blob locator, SAS, credential, identity, or real-member payload leak;
- [ ] any preview, download, or confirmation of a pending, application-rejected,
      Defender-malicious, or errored source;
- [ ] any unexpected Moment, Placement, audience, share, publication, or
      homepage write;
- [ ] any mismatch between expected and deployed source or pipeline;
- [ ] both flags true, expired or invalid proof configuration, or cohort drift;
- [ ] any real member content read;
- [ ] any deletion reporting success before both active Blob absences;
- [ ] a Defender alert that reaches an unnotified party or names anything
      beyond the single synthetic fixture; or
- [ ] any other high-risk security, privacy, Defender, Storage, SQL, identity,
      or application alert.

The single expected Defender malicious alert for the approved inert fixture,
acknowledged in advance by the notified security owner, is **not** a rollback
trigger. It is the planned result of step 16.

Return **Conditional** - pause, do not roll back - for transient service
failure, a missing screenshot, incomplete evidence, or a cleanup retry with no
exposure. Escalate to **Fail** if a safety invariant is violated or synthetic
teardown cannot be proven.

## 9. Final verification - both flags false

The window is not finished until every line below is ticked.

1. [ ] Operator sets `CAPTURE_PHOTO_LIFECYCLE_PROOF_ENABLED=false`.
2. [ ] Operator removes the cohort keys, expiry, and run id through the
       approved secure path.
3. [ ] `CAPTURE_PHOTO_ENABLED` confirmed still **false**. It was never changed.
4. [ ] A loads `/app/capture`: flag-off behaviour, no Photo surface.
5. [ ] B loads `/app/capture`: flag-off behaviour, no Photo surface.
6. [ ] C loads `/app/capture`: flag-off behaviour, unchanged from Phase 1.
7. [ ] All seven direct Photo routes return the neutral flag-off 404 for A, B,
       C, and signed-out.
8. [ ] No further proof-mode admission audit line is emitted after the gate is
       disabled.
9. [ ] Ordinary members are, and always were, unaffected.

## 10. Recording the result

- **Pass** requires every production row, both-Blob active absence, honest
  soft-delete retention classification, all screenshots, the full second-owner
  matrix, non-cohort neutrality before and after, complete teardown, the
  rollback and expiry proof, and the privacy review.
- **Conditional** is the correct result for a skipped Defender row, a transient
  failure, an evidence gap, or retention still inside its seven-day window. It
  is not a failure of the window.
- **Fail** is reserved for a demonstrated safety violation or an inability to
  remove every live synthetic record and both active Blobs.

Accurately documented seven-day soft-deleted retention is never a safety Fail.
It only prevents a claim of immediate permanent erasure - and that claim is not
made.

**A Pass does not enable Photo.** Ordinary-member enablement additionally
requires accepted and live Photo homepage parity via
`PS-HOME-CAPTURE-PHOTO-PARITY-001`, plus a separate explicit owner and manager
decision. `CAPTURE_PHOTO_ENABLED` stays false until then.
