# PS-CAPTURE-PHOTO-LIFECYCLE-001 - Proof Mechanism and Rollout

## Decision

Implement a server-enforced and expiring production dark-launch gate on the
separately approved continuation branch.
Keep the general member release flag false. Admit exactly two synthetic owners
by the internal key that the server resolves after authentication. Use a third
synthetic identity to prove non-cohort neutrality.

The owner approved the bounded server-only implementation on 2026-07-20. On the
same date the owner replaced the earlier Defender choice B with **choice A**,
the coordinated inert production test. This document still does not authorize a
production proof window or any production configuration change; it records the
decision and the plan choice A requires.

## Access-policy contract

The later policy has two independent release axes:

1. `CAPTURE_PHOTO_ENABLED` - the ordinary-member release gate. It remains
   false for this lifecycle proof.
2. `CAPTURE_PHOTO_LIFECYCLE_PROOF_ENABLED` - an expiring synthetic-cohort gate.
   It is false by default and may be true only under an approved proof window.

The decision logic is:

```text
if ordinary release flag is true and lifecycle proof flag is true:
    fail closed as invalid configuration
elif ordinary release flag is true:
    use the existing signed-in member boundary
elif lifecycle proof flag is true:
    require a valid future UTC expiry
    resolve the signed-in identity through the trusted server boundary
    require exact identity.user_key membership in the two-key cohort
    otherwise return the flag-off-equivalent neutral denial
else:
    return the flag-off-equivalent neutral denial
```

The proof policy is evaluated independently on the Capture page and every
direct Photo endpoint. It never accepts a client-provided identity or uses an
email comparison. Configuration conflicts, invalid keys, parsing errors,
missing expiry, expired windows, and identity-storage errors all fail closed.

## Configuration contract without values

| Name | Type and default | Contract |
| --- | --- | --- |
| `CAPTURE_PHOTO_ENABLED` | Boolean; `false` | Must remain false for the complete dark-launch proof. A true value is an ordinary-member release and is forbidden by this package. |
| `CAPTURE_PHOTO_LIFECYCLE_PROOF_ENABLED` | Boolean; `false` | Master proof kill switch. True only during a separately approved, attended window. |
| `CAPTURE_PHOTO_LIFECYCLE_PROOF_USER_KEYS` | Empty string | Comma/space-separated exact internal user keys for Synthetic A and B only. Empty, malformed, duplicate, or cardinality other than two fails closed. Values are operationally sensitive and are never committed, returned, printed, or screenshot. |
| `CAPTURE_PHOTO_LIFECYCLE_PROOF_EXPIRES_AT_UTC` | Empty string | Required RFC 3339 UTC instant when proof is enabled. It must be in the future and no more than two hours after activation. Expiry fails closed without operator action. |
| `CAPTURE_PHOTO_LIFECYCLE_PROOF_RUN_ID` | Empty string | Optional nonsecret bounded correlation label. If used, it contains only the package ID plus a date/run number and no identity or record key. |

Existing nonsecret Blob account/container and Photo limit settings are not
changed or inspected by this package. No secret, setting value, identity key,
token, connection string, or credential is evidence.

## Proof-window entry gate

All conditions must pass before a later operator sets the proof flag:

1. Designated-manager approval of this architecture and the separate
   implementation branch.
2. The implementation is based on then-current `origin/main`, contains only
   reserved files, passes complete-diff review and focused/full tests, and is
   released through an Azure PR and green pipeline with both Photo flags off.
3. Production remains on the expected release SHA, `CAPTURE_PHOTO_ENABLED` is
   independently confirmed false without listing settings, and the lifecycle
   gate is confirmed false before the window.
4. Two synthetic identities A/B and one non-cohort synthetic identity C exist
   through the normal external identity flow. No real member identity is used.
5. A/B have no pre-existing live Capture Media records. C has no Photo access.
   Checks are owner-scoped and do not read other members.
6. The synthetic JPEG/PNG fixtures and synthetic notes are approved as
   nonpersonal, nonconfidential, and safe. The application-rejection fixture is
   malformed or dimension-invalid and is not evidence of malware detection.
7. Defender **choice A** is the recorded owner decision as of 2026-07-20.
   Before the window opens, security/operations has supplied and approved the
   exact inert EICAR-based fixture, the advance-notification list in
   [`04_DEFENDER_CHOICE_A_OPERATIONAL_PLAN.md`](04_DEFENDER_CHOICE_A_OPERATIONAL_PLAN.md)
   has acknowledged the window, and the expected production alert and
   remediation response are coordinated in writing. If that coordination is not
   complete on the day, the malicious row is skipped and recorded Conditional;
   the rest of the window may still proceed.
8. The screenshot list, endpoint matrix, cleanup inventory, rollback command,
   expiry, evidence owner, and incident contact are prepared.
9. Defender cap/health, application health, pipeline health, and deletion
   backlog are within approved thresholds without changing Azure or Defender.
10. No active branch owns an exact reserved implementation file. The current
    `PS-HOME-FRONTEND-001` reservation does not overlap this runtime package;
    any later scope change must be rechecked before implementation starts.

## Controlled execution sequence

1. Record exact production application SHA/pipeline and a nonsecret run ID.
2. Configure the two A/B internal keys, expiry, and proof flag through the
   approved operator path without reading values back into the evidence log.
3. Confirm C sees the ordinary flag-off page and neutral direct-route denial.
4. Confirm A and B can see Photo but no real member data.
5. Run pending, clean, application image-validation rejection,
   stale/recoverable error, confirmed, export, archive, restore, original
   download, draft-delete, confirmed-delete, and both-Blob active-absence cases
   in `03_PRODUCTION_EVIDENCE_MATRIX.md`.
6. Run the Defender-malicious case under recorded choice A, following
   [`04_DEFENDER_CHOICE_A_OPERATIONAL_PLAN.md`](04_DEFENDER_CHOICE_A_OPERATIONAL_PLAN.md)
   exactly, only while every security-alert prerequisite in that plan remains
   satisfied. If any prerequisite lapses, skip the row and record it
   Conditional rather than improvising.
7. Run every B-versus-A endpoint denial immediately after the relevant A object
   exists and compare it with a random absent key.
8. Capture only the required privacy-safe viewport screenshots.
9. Teardown every synthetic draft and confirmed aggregate, prove no live
   link/source payload or active Blob remains, and record any soft-deleted
   retention without claiming permanent absence.
10. Set the proof flag false, remove the cohort/expiry values through the
   approved operator path, and confirm C, A, and B all receive flag-off behavior.
11. Record `Pass`, `Conditional`, or `Fail`. Do not change the general flag.

## Owner decision: production Defender-malicious proof

**Recorded decision, 2026-07-20: Choice A.** The owner explicitly replaced the
earlier same-day choice B with choice A, the coordinated inert production test.
One security-approved inert EICAR-based fixture will be uploaded during the
attended window so the production Defender binding is proved end to end rather
than inferred. This decision does not affect the separate application
image-validation rejection case, which remains a distinct row with distinct
evidence.

EICAR is the industry-standard harmless antivirus test string. It is not
malware and contains no executable payload; it exists specifically so scanners
can be verified. Microsoft Defender **will** report it malicious and quarantine
it. That is the intended and expected outcome of this row, not an incident.
Because the alert is real and will reach whoever watches the security queue,
choice A is authorized only with the advance notification, fixture handling,
remediation, and stop conditions specified in
[`04_DEFENDER_CHOICE_A_OPERATIONAL_PLAN.md`](04_DEFENDER_CHOICE_A_OPERATIONAL_PLAN.md).

Choice B below is retained as the superseded decision record. Reverting to it
requires a new explicit owner decision recorded in this section.

### Choice A - coordinated inert production test (recorded decision)

Use one security-approved inert EICAR-based test only after advance
coordination with the security/operations alert owner. The coordination record
must name the attended window, expected Defender alert and remediation, stop
contacts, exact approved fixture provenance, and the configured seven-day
soft-delete behavior. Security supplies the fixture; the implementation must
not disguise, mutate, or invent a payload to bypass image validation. The
fixture must reach Defender through the normal quarantine path and receive a
Defender-owned malicious result. Application rejection before that result does
not satisfy this case.

Choice A proves the production Defender binding only if the application never
delivers or confirms the bytes, the source becomes safely rejected, the Blob
is actively absent after provider remediation, and retained soft-deleted state
is recorded accurately. A post-retention check requires its own approved
follow-up if permanent absence is to be claimed.

The full operational plan this choice requires - advance notification, fixture
custody, expected `rejected` application state, required negative proofs,
remediation, cleanup, active-absence checks, retention honesty, and stop
conditions - is
[`04_DEFENDER_CHOICE_A_OPERATIONAL_PLAN.md`](04_DEFENDER_CHOICE_A_OPERATIONAL_PLAN.md).
The fixture bytes are never committed to this repository, quoted in any
package document, pasted into chat, or stored outside the approved security
channel.

### Choice B - no production malicious test (superseded 2026-07-20)

Do not upload any malicious-test fixture in production. Retain the existing
sanctioned harmless-malware proof from a disposable, isolated Storage/Defender
account as nonproduction evidence. Run all other dark-launch production cases,
but mark the production Defender-malicious route **Conditional**. This is the
lower-production-risk choice and it cannot be promoted to Pass by a malformed,
dimension-invalid, or otherwise application-rejected image.

Choice B is superseded. It remains available as a same-day fallback: if the
security coordination in the operational plan is not complete when the window
opens, or a stop condition fires before the fixture is uploaded, the operator
skips the malicious row, cites the sanctioned isolated-account evidence, and
records that single row **Conditional** while the rest of the window proceeds.

Under recorded choice A the production Defender-malicious row is an in-scope
row that can reach **Pass**. The overall lifecycle-readiness result remains
Conditional until every production matrix row and the teardown pass.

## Blob deletion evidence vocabulary

- **Active absence** means the known original or derivative locator is no
  longer an active Blob readable through the application's normal managed-
  identity path, and the owning SQL lifecycle can safely finalize and clear
  that locator. The verifier uses the known locator transiently; it does not
  list the container or emit the locator.
- **Soft-deleted retention** means Azure has removed the Blob from normal
  application access but may retain recoverable bytes under the
  governance-recorded seven-day recovery window. This satisfies active
  absence, not permanent erasure.
- **Permanent absence** may be claimed only after the recovery period has
  elapsed and a separately authorized locator-specific verification finds no
  retained object. It is not a same-window acceptance condition and is not
  claimed by this package.

The proof records `original_active_absent=true` and
`derivative_active_absent=true`, plus a neutral retention state such as
`soft_deleted_retention_expected` or `soft_deleted_retention_not_applicable`
when no Blob was ever created. It never states that all synthetic bytes are
permanently absent while the seven-day retention window may still hold them.

## Synthetic-owner teardown

Planned teardown occurs before the cohort is removed:

1. Stop creating new sources.
2. Delete every unconfirmed A/B draft through its owner-scoped application
   endpoint. For a clean draft, verify both the derivative and original are
   actively absent before success and record soft-deleted retention separately.
3. Delete every confirmed A/B Photo Capture through the generic Capture
   deletion endpoint. Verify the source link is gone, Capture/revision content
   follows the existing tombstone contract, and both Blobs are actively absent.
4. Verify A/B have zero live Photo Captures, zero live Capture Media links, and
   zero source rows containing locators, digests, dimensions, scan detail, or
   draft payload. Body-free lifecycle/audit tombstones allowed by the released
   contract may remain.
5. Verify no synthetic Moment, Placement, audience, share, publication, or
   projection was created.
6. Disable the lifecycle gate and remove the allowlist/expiry values.
7. Confirm the global flag is still false and all three identities now receive
   flag-off behavior.

The secure verifier may hold original and derivative locators transiently in
process memory solely for locator-specific active-absence checks. It outputs
only `original_active_absent=true`, `derivative_active_absent=true`, and the
neutral retention classification defined above; locators are never logged or
committed. It uses existing owner-resolving procedures and only the two
synthetic owners. If proving active absence requires a SQL change, broad member
query, setting read, container listing, or permanent purge, stop for manager
approval.

## Rollback and incident behavior

### Immediate rollback

Set `CAPTURE_PHOTO_LIFECYCLE_PROOF_ENABLED=false`. Because
`CAPTURE_PHOTO_ENABLED` remains false, the Photo selector and direct Photo
routes return to the flag-off boundary for everyone. The configured expiry is
an independent automatic rollback if an operator cannot act.

The rollback never deletes SQL, Storage, or Azure resources and never changes
Voice or text Capture. If synthetic records remain, contain the incident first;
run teardown later only through an approved recovery action.

### Incident stop conditions

Hard-stop and disable the proof gate immediately for:

- any non-cohort Photo access or UI exposure;
- any cross-owner state, media, export, mutation, or distinguishable-existence
  result;
- any Blob locator, SAS, credential, identity, or real-member payload leak;
- any pending, application-rejected, Defender-malicious, or error source
  preview, download, or confirmation;
- any unexpected Moment, Placement, audience, share, publication, or homepage
  write;
- any mismatch between expected and deployed source/pipeline;
- both flags true, expired/invalid proof configuration, or cohort drift;
- any real member content read;
- any deletion success before both active Blob absences; or
- any high-risk security, privacy, Defender, Storage, SQL, identity, or
  application alert, **except** the single expected Defender malicious alert
  for the approved inert EICAR-based fixture under recorded choice A, which the
  notified security owner has acknowledged in advance as this planned test.

That exception is narrow. Treat a Defender alert as a real stop condition if it
names more than the one synthetic fixture, arrives outside the attended window,
reaches an owner who was not notified, or is accompanied by any exposure,
delivery, confirmation, or cross-owner signal above.

Pause new work and return **Conditional** for transient service failure,
missing screenshots, incomplete evidence, or a cleanup retry with no exposure.
Escalate to **Fail** if a safety invariant is violated or synthetic teardown
cannot be proven.

## Properly isolated staging evaluation

A staging slot/environment is useful for preflight and deliberate failure
states only when all of the following are separate from production:

- external identity registration, redirect URIs, sessions/cookies, and
  synthetic identities;
- Azure SQL database and migrations;
- Storage account/container, Defender policy/cap/remediation, and media;
- managed identity and exact role assignments;
- application settings, secrets, callbacks, host names, telemetry, alerts, and
  deployment permissions; and
- cleanup ownership and a no-swap/no-production-resource rule.

An App Service slot that shares production SQL, Storage, identity, settings,
telemetry, or managed-identity access is not an isolated staging environment.
Current governance says environment separation remains incomplete, so staging
is not the recommended closing proof today. Even a proper staging pass cannot
prove the exact production bindings, pipeline, Defender results, production
screens, or deletion path; it supplements, but does not replace, the dark
launch.

## Temporary global flag-on fallback

The global-window option is unavailable now. It may be reconsidered only if:

1. the dark-launch implementation is proven infeasible or produces an
   explicitly documented production-only blocker;
2. Pete and the designated manager approve the exact date, duration, owners,
   rollback, and risk in writing;
3. `PS-HOME-CAPTURE-PHOTO-PARITY-001` is accepted, released, and live first;
4. the full lifecycle implementation and all nonproduction evidence already
   pass;
5. the window is attended, short, automatically time-bounded, and immediately
   reversible; and
6. no ordinary-member data is read even if ordinary-member access becomes
   technically possible.

A global flag-on window is not a substitute for second-owner evidence or
homepage parity and cannot be authorized by this architecture branch.

## Approved implementation file reservations

The approved implementation may reserve only:

- `.env.example` - names/defaults for the nonsecret proof configuration only;
- `owner_routes.py` - central cohort-policy calls and neutral response behavior
  for Photo routes/rendering only;
- new `services/photo_lifecycle_access_service.py` - configuration validation,
  expiry, trusted-key matching, and fail-closed decision only;
- `tests/test_owner_photo_capture.py` - existing Photo route/rendering contract;
- new `tests/test_photo_lifecycle_access.py` - cohort, expiry, conflict,
  non-cohort, signed-out, and route-inventory tests;
- new `scripts/verify_capture_photo_lifecycle.py` - privacy-safe synthetic-only
  evidence and two-Blob active-absence/retention verifier, if it can reuse
  existing procedures without SQL or secret reads; and
- this package's implementation/evidence/completion records.

The implementation package may not reserve or edit `app.py`, `identity.py`,
templates, CSS, JavaScript, SQL, migrations, Storage/Defender provisioning,
homepage files, shared governance, Voice services/tables/UI, Moment,
Placement, Owner Home behavior, Interview Studio, or global shell/theme code.
If any excluded file becomes necessary, stop for manager scope review.

## Owner Home and Interview conflicts

- `PS-HOME-FRONTEND-001` explicitly forbids `owner_routes.py`. Its intended
  template, route-bootstrap, route-scoped CSS/JavaScript, Owner Home test, and
  package/evidence files do not overlap the proposed Photo lifecycle runtime
  files. Owner Home frontend therefore does not require serialization with the
  dark-launch gate on current reservations.
- The Photo gate must still not change `/app` Owner Home selection,
  `PEERSLATE_OWNER_HOME_ENABLED`, Owner Home SQL/service/serializer/template,
  or its dark cinematic authority. Any future reservation expansion triggers a
  fresh exact-file conflict check.
- Dark-launch lifecycle proof does not touch `/`, does not depend on homepage
  parity, and may proceed independently once its own implementation is
  approved.
- Active Interview homepage parity owns bounded homepage integration files and
  evidence. The later `PS-HOME-CAPTURE-PHOTO-PARITY-001` branch remains
  serialized after that Interview homepage work because their homepage
  partial, style/script, include, cache, or evidence integration files may
  overlap. Ordinary Photo enablement, unlike dark-launch proof, remains blocked
  until Photo homepage parity is accepted and live.
