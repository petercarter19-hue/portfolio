# PS-CAPTURE-PHOTO-LIFECYCLE-001 - Production Evidence Matrix

## Evidence boundary

This matrix is for a later approved run. It creates no production record now.
Every case uses synthetic owners and synthetic media only. Evidence proves the
released application, identity, SQL, Blob, Defender, UI, and deletion contracts
without reading a real member record or exposing a storage locator.

## Fixture inventory

Use one run-specific inventory maintained in transient process memory:

| Fixture alias | Owner | Purpose | Expected cleanup |
| --- | --- | --- | --- |
| `A-clean-confirmed` | A | Pending -> clean -> review -> confirm -> correction -> archive -> restore -> export/download -> confirmed delete | Capture/link content removed under existing tombstone contract; original and derivative actively absent; soft-deleted retention recorded separately |
| `A-clean-draft-delete` | A | Known-clean draft with both Blobs, deleted before confirmation | Source body-free deleted tombstone; original and derivative actively absent; soft-deleted retention recorded separately; no Capture/link |
| `A-image-invalid` | A | Safe malformed or dimension-invalid JPEG/PNG; application validation only | Application rejection/validation failure; no Defender-malicious claim; no preview/confirm/Capture/link; any accepted original actively absent after cleanup |
| `A-defender-malicious` | A | **In scope under recorded choice A.** The exact security-approved inert EICAR-based fixture reaches production Defender quarantine. Handled per [`04_DEFENDER_CHOICE_A_OPERATIONAL_PLAN.md`](04_DEFENDER_CHOICE_A_OPERATIONAL_PLAN.md); bytes are supplied through the approved security channel and never committed here | Defender-owned malicious result; application state `rejected`; no delivery/confirm; provider remediation; active absence plus seven-day soft-deleted retention evidence |
| `A-stale-error` | A | Obsolete row-version or validation failure | No mutation; recoverable error evidence; delete afterward |
| `B-owner-control` | B | Prove B can create only B-owned state while inside cohort | Fully deleted; both Blobs actively absent where created; retention recorded separately |
| `C-noncohort` | C | Gate-denial requests only | No source or Capture can be created |

Synthetic media should be generated geometric/color content with no person,
location, organization, device metadata, or confidential text. Synthetic note
copy contains only the package/run alias and an explicit `synthetic proof`
label. The repository evidence may contain the fixtures only if manager-approved
and metadata-audited; production keys and identity values never accompany them.

## Lifecycle proof matrix

| Case | Signed-in production action | Required result | Required negative/cleanup proof |
| --- | --- | --- | --- |
| Pending | A uploads one supported synthetic JPEG/PNG | 201 owner-safe application response; state becomes `scanning`; status remains pending until Defender result | No preview/original URL in pending response; preview/original/confirm unavailable; no Capture/link; B denied; C neutral |
| Clean | A reconciles after Defender reports clean | State reaches `needs_review`; independently decoded metadata-free derivative has bounded type/bytes/dimensions | No Blob locator/digest/filename; exact original remains private; B denied on status/preview/original/reconcile |
| Application image-validation rejection | A submits the approved safe malformed or dimension-invalid image fixture | Initial validation rejects it or, after a clean scan, independent decode/dimension validation reaches the documented rejected/failed state with a stable safe code | Evidence names the application validator, not Defender; no preview, original product delivery, confirm, Capture, link, or downstream write; any accepted original is cleaned up without provider-detail logging |
| Defender-malicious rejection | **In scope.** A submits the exact security-approved inert EICAR-based fixture during the coordinated alert window and it reaches Defender quarantine | Defender-owned result reports malicious; application reaches `rejected` with a stable safe code; the expected Defender alert and remediation occur and are acknowledged by the notified alert owner as the planned test | No preview, download, confirm, derivative, Capture, link, or downstream write; original and derivative locator slots actively absent after remediation; seven-day retained soft-delete state documented as retention, not erasure. Application rejection before a Defender malicious result is not proof. If security coordination lapses before upload, skip the row and record it Conditional rather than substituting another fixture. |
| Error | A submits an obsolete row-version or an invalid required-note confirmation | Existing changed/validation error appears and recovery is understandable | State and both Blobs unchanged; no duplicate Capture/link; do not induce a production Storage/Defender outage merely to make an error screenshot |
| Confirmed | A supplies a nonempty synthetic note and explicit save confirmation | Exactly one private `capture_type=photo` Capture and one source link; source `confirmed`; replay returns existing result | No Moment/Placement/audience/share/publication; concurrent/replayed save does not duplicate; B denied |
| Correction | A corrects only the confirmed Capture note | One new Capture revision; immutable original note and source bytes unchanged | No Blob change or downstream write; stale token denied; B denied |
| Export | A downloads `/app/capture/<capture_key>/export` | `peerslate.capture.export`, schema version 3, synthetic original/current/revisions, safe media metadata, app-mediated download/preview paths | No Blob name/account/container/SAS/digest/identity/provider payload/binary; private/no-store/nosniff; B receives absent-equivalent denial |
| Archive | A archives the confirmed Capture with current row version | Capture moves to archived list | Original and derivative still exist; source/link retained; B denied |
| Restore | A restores the archived Capture | Capture returns active | Original and derivative still exist; source/link retained; B denied |
| Download | A downloads the private original and requests the safe preview | Original is attachment with generic name and exact synthetic bytes; preview is derivative only; both private/no-store/nosniff | No redirect to Blob/SAS; address/response does not expose locator; B denied for original and preview |
| Draft delete | A explicitly deletes `A-clean-draft-delete` | Delete is reported successful only after active storage absence and SQL finalization | `original_active_absent=true`, `derivative_active_absent=true`; soft-deleted retention classified separately; no Capture/link; content fields cleared; repeat delete is safe/neutral |
| Confirmed delete | A explicitly deletes `A-clean-confirmed` through generic Capture deletion | Distributed delete succeeds and existing Capture/Moment tombstone behavior is preserved | `original_active_absent=true`, `derivative_active_absent=true`; soft-deleted retention classified separately; link removed; Capture/revision content removed; no confirmed Moment is deleted; B denied |
| Final teardown | Owner-scoped verifier checks A and B after all deletes | Zero live synthetic Photo Captures, links, source payloads, or active Blobs | No locator/digest/dimensions/scan detail in deleted source; no synthetic downstream records; soft-deleted retention reported without claiming permanent erasure; both flags false after gate removal |

Provider/storage-outage behavior remains covered by released tests and a
properly isolated environment. Production proof may record a naturally
occurring provider error, but it must not change Azure, Defender, identity,
network, or Storage configuration to manufacture one.

## Defender decision evidence

The recorded owner decision as of 2026-07-20 is **choice A**. The production run
record must therefore identify the advance security-alert coordination record
without exposing operational secrets, and capture the Defender-owned malicious
outcome, the neutral application rejection, the expected alert and remediation,
active absence, and the seven-day soft-deleted retention classification.

Choice B remains only as the superseded record and the same-day fallback. If it
is used, the run record must state that no production malicious fixture was
uploaded, cite only the accepted disposable isolated-account proof, and mark the
production Defender-malicious row Conditional.

The `A-image-invalid` fixture cannot satisfy either choice's Defender evidence.
If choice A's fixture is stopped by application validation before Defender
returns malicious, record the Defender production row Conditional rather than
relabeling the application rejection.

## Blob absence and retention evidence

Both-Blob checks are locator-specific and use trusted locators only in
transient verifier memory. `active_absent=true` means a Blob is unavailable to
the normal application identity and may be cleared from live SQL state. It does
not mean the underlying bytes are unrecoverable.

The current authority configures malicious-Blob remediation and general Blob
soft delete with a seven-day recovery window. Evidence must therefore report
active absence separately from `soft_deleted_retention_expected` or
`soft_deleted_retention_not_applicable` when no Blob was created. No same-window
screenshot, application response, or `exists=false` result may be described as
permanent absence. A claim of permanent absence requires a separately approved
locator-specific check after retention expires; container-wide listing or
purge is outside this package.

## Second-owner denial matrix

For each A source/Capture, B sends the same request first with a random absent
key and then with A's valid key. Status, body/JSON shape, redirect target,
cache/security headers, and allowed timing variance must be equivalent. The
test harness may know A's key transiently; B never obtains it from an
application response.

| Endpoint or surface | B-versus-A proof |
| --- | --- |
| `GET /app/capture` | No A Capture, source status, thumbnail, note, action, count, or key appears in B's list. |
| `POST /app/capture/photo` | Request has no owner/path parameter; any B upload is B-owned. Supplying owner-like extra fields has no effect. |
| `GET /app/capture?photo=<A-source>` | Same neutral not-found behavior as random absent source; no draft hydration or app media URL. |
| `GET /app/capture/photo/<A-source>` | Same neutral status denial as absent source; no state/scan/dimensions/error/key validity. |
| `POST /app/capture/photo/<A-source>/reconcile` | Same absent/changed outcome; no Defender tag or Blob read and no state transition. |
| `POST /app/capture/photo/<A-source>/confirm` | Same absent/changed outcome; no Capture/link created or A state changed. |
| `POST /app/capture/photo/<A-source>/delete` | Same absent/changed outcome; neither A Blob is touched. |
| `GET /app/capture/photo/<A-source>/preview` | Same 404/media-not-found response; zero bytes returned. |
| `GET /app/capture/photo/<A-source>/original` | Same 404/media-not-found response; zero bytes returned and no attachment header revealing type. |
| `POST /app/capture/<A-capture>/correct` | Same existing absent/stale redirect; no revision added. |
| `POST /app/capture/<A-capture>/archive` | Same existing absent/stale redirect; A remains active. |
| `POST /app/capture/<A-capture>/restore` | Same existing absent/stale redirect; A remains archived/active as arranged. |
| `GET /app/capture/<A-capture>/export` | Same `Capture not found` response as absent key; no JSON fields returned. |
| `POST /app/capture/<A-capture>/delete` | Same existing absent/stale/retry-safe outcome; A Capture and both Blobs remain. |
| `POST /app/capture/<A-capture>/moment-proposal` | Same absent/changed outcome; no A or B Moment proposal is created. |

After each denial, A immediately verifies its own expected state. A final
owner-scoped check confirms B caused no A audit event that falsely claims a
successful member action.

## Non-cohort proof

Synthetic C must prove all of the following while the proof flag is active and
the general flag is false:

- `/app/capture` contains no Photo selector, Photo modal, Photo script, Photo
  draft, or Photo capability copy;
- `GET /app/capture?photo=<random-or-A-key>` is equivalent to global flag-off;
- every direct Photo GET/POST route is equivalent to global flag-off;
- no sign-in redirect, cohort reason, route detail, source existence, or
  configured expiry is disclosed by a direct Photo request; and
- no C Photo source, Capture, link, Blob, or Photo audit event is created.

After the proof gate is disabled and cohort values are removed, repeat the same
checks with A, B, and C.

## Privacy-safe evidence collection

Committed evidence may include only:

- package/run alias, UTC date, exact application SHA, Azure PR/pipeline IDs,
  viewport, browser version, test case ID, route class, HTTP outcome, state
  name, duration bucket, and Pass/Conditional/Fail;
- synthetic fixture description and synthetic note text;
- screenshot files that contain viewport pixels only;
- the server-side proof-mode admission audit line, quoted verbatim. The
  released application emits
  `PeerSlate Photo lifecycle proof admission. access_mode=proof run_id=<run id>`
  at warning level the first time each proof window actually admits a cohort
  request. It carries only the access mode and the nonsecret run label, never a
  user key, cohort value, expiry, source key, or content, so it may be quoted
  directly into evidence. It is the only positive server record that proof mode
  was live and admitted someone; without it the window rests entirely on
  operator screenshots; and
- booleans/counts such as `capture_count=1`, `link_count=1`,
  `original_active_absent=true`, `derivative_active_absent=true`, and a neutral
  soft-delete retention classification for A/B-scoped data.

Do not collect or commit:

- HAR files, cookies, tokens, Easy Auth headers, request headers, browser
  profiles, credentials, App Service settings, SQL connection material, or
  portal screenshots;
- external identity claims, email, internal user/account keys, source/Capture
  keys, Blob names, storage account/container locators, SAS values, hashes,
  ETags, provider payloads, malware detail, or exact telemetry correlation IDs;
- original/preview binary beyond the approved synthetic fixture/evidence; or
  any real member content/count/query result.

The transient alias-to-key map is deleted after teardown and is not a
repository artifact. Logs and screenshots receive a final privacy scan before
commit. If redaction would be needed, regenerate the evidence without the
sensitive field rather than committing a redacted secret-bearing capture.

## Production screenshot requirements

Screenshots use the accepted Photo 1 real production UI through Synthetic A.
They are viewport captures only, with no browser chrome, URL/query key,
developer tools, portal, identity menu, notifications, or real content.

Required named production images for the later evidence package:

1. desktop 1440x900 and mobile 390x844 opening states;
2. desktop and mobile scan-pending states;
3. desktop and mobile known-clean safe-review states with synthetic image/note;
4. desktop and mobile application image-validation rejection with no image
   preview;
5. desktop and mobile neutral Defender-malicious rejection with no malware
   detail, no provider payload, and no image preview - required under recorded
   choice A, and omitted only if the row itself is skipped and recorded
   Conditional;
6. desktop and mobile stale/concurrency error plus recovery states;
7. desktop and mobile confirmed private Capture/list state;
8. archived and restored visible states at the most informative viewport;
9. deletion-pending/cleanup state if it occurs naturally, plus successful
   deletion-complete state; do not break production Storage to manufacture a
   retry screenshot;
10. visible keyboard focus on the dominant Photo action and the destructive
   confirmation;
11. native 200-percent zoom/reflow with zero page-level horizontal overflow;
12. mobile landscape or equivalent narrow-height proof with reachable save;
13. long synthetic note/error text and virtual-keyboard-safe mobile review;
14. reduced-motion static status behavior; and
15. no-JavaScript Type fallback with Photo unavailable as an enhanced path.

Export structure, original byte equality, headers, second-owner denial, Blob
active absence/retention, and downstream-zero checks are machine/text evidence,
not screenshots.

Do not screenshot raw export JSON because it contains opaque object keys.

Every screenshot record names the Photo 1 authority, exact production SHA,
viewport, state, synthetic fixture alias, UTC time, and comparison result. Pete
and the designated manager must accept the production visual set before an
ordinary-member release decision.

## Homepage dependency

Dark-launch proof does not change `/` and does not require homepage files. The
current `Coming later` language remains truthful because an ordinary member
still cannot use Photo.

Ordinary enablement is blocked until the separate
`PS-HOME-CAPTURE-PHOTO-PARITY-001` branch is accepted, released, and verified
live against the protected Photo product. That package owns its own desktop/
mobile comparison, truth/accessibility review, canonical protected link,
Pete/manager acceptance, Azure PR/pipeline, and live verification. A temporary
global flag-on fallback is also forbidden until homepage parity is live.

## Recommendation scale

### Pass

Use only after the later dark-launch implementation, flag-off deployment,
non-cohort checks, complete A lifecycle, every B denial, production screenshots,
privacy review, rollback/expiry proof, both-Blob active absence, accurate
soft-delete retention evidence, final teardown, and evidence review pass. Under
recorded choice A the production Defender-malicious row is in scope and a
Defender-owned malicious result plus every required negative proof is part of
the Pass condition; a skipped or uncoordinated malicious row keeps that row
Conditional. An ordinary-member enablement Pass additionally requires
accepted/live homepage parity and a separate explicit manager/owner decision.

### Conditional - current recommendation

The architecture is accepted, the cohort gate is released flag-off, and the
proof-mode admission audit record is added, but none of the signed-in production
evidence in this matrix exists yet. Keep `CAPTURE_PHOTO_ENABLED=false` and
`CAPTURE_PHOTO_LIFECYCLE_PROOF_ENABLED=false`. Defender choice A is now the
recorded decision, so the production Defender-malicious row is no longer
excluded by the owner decision; it is simply unrun, like every other row here.

### Fail

Use for any cross-owner/non-cohort exposure, Blob locator or secret leak,
unscanned delivery/confirmation, real-member read, automatic downstream write,
unsafe configuration, uncontained incident, early delete success, or inability
to remove all live synthetic records and both active Blobs. Accurately
documented seven-day soft-deleted retention alone is not a safety Fail, but it
prevents a claim of immediate permanent erasure.
