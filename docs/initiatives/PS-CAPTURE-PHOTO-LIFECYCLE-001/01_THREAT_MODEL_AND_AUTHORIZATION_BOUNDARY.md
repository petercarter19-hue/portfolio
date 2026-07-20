# PS-CAPTURE-PHOTO-LIFECYCLE-001 - Threat Model and Authorization Boundary

## Safety objective

Prove the real signed-in Photo lifecycle against the released production
application without making Photo available to an ordinary member, trusting a
client identity, exposing a Blob locator, reading real member content, or
leaving active application-addressable synthetic content behind. Azure's
configured soft-delete retention is tracked separately and is never misstated
as immediate permanent erasure.

The proof is allowed to exercise only synthetic owner records created later
under a separately approved production-proof window. This architecture package
creates none.

## Non-negotiable invariants

1. `CAPTURE_PHOTO_ENABLED` remains false throughout dark-launch proof.
2. The server resolves identity before it makes a cohort decision.
3. Only an exact server-resolved internal `user_key` may match the cohort.
4. The cohort list is empty by default, time-bounded, fail-closed, and never
   returned to the browser or committed to the repository.
5. Every Photo route enforces the gate independently. Hiding the Photo method
   in the template is not authorization.
6. After cohort admission, existing owner-resolving SQL remains the object
   authorization boundary. The dark-launch gate does not replace tenant
   isolation.
7. Source or Capture ownership is proved before any Blob tag, property, byte,
   preview, original, export, or delete operation.
8. A non-cohort request performs no Photo SQL or Blob operation after trusted
   identity resolution and receives the same neutral result as flag-off.
9. A cohort member requesting another cohort member's object receives the same
   route-specific result as a random absent key and causes no Blob operation.
10. No response, redirect, HTML, JSON, screenshot, log, audit event, or evidence
    file exposes a Blob name, account/container locator, SAS URL, credential,
    digest, client filename, external identity claim, or configured cohort
    value.
11. No original is previewed inline. No preview, original download, or
    confirmation is available before a known-clean result and safe derivative.
    Application image-validation rejection and Defender-malicious rejection
    are distinct states and require distinct evidence.
12. No proof action creates a Moment, Placement, destination, audience grant,
    share, public projection, publication, OCR, AI caption, or homepage change.

## Synthetic identity roles

| Alias | Cohort status | Purpose |
| --- | --- | --- |
| Synthetic Owner A | Approved | Owns the complete clean/confirmed lifecycle, application-validation fixture, and any separately approved Defender-malicious fixture. |
| Synthetic Owner B | Approved | Creates one owner-scoped control record and attempts every protected A endpoint to prove the real second-owner boundary. |
| Synthetic Non-cohort C | Not approved | Proves the Photo method stays absent and every direct Photo route returns the flag-off-equivalent neutral denial. |

The aliases are the only identity labels allowed in committed evidence. Email,
external subject, issuer, internal user key, account key, cookie, token, and
Easy Auth header values are not evidence and must not be printed or stored.

## Authorization sequence

```text
request
  -> validate server configuration (global flag / proof flag / expiry)
  -> resolve trusted server identity
  -> compare only resolved internal user_key with the proof cohort
  -> deny outside cohort with flag-off-equivalent neutral behavior
  -> validate same-origin requirement for writes
  -> normalize opaque source_key or capture_key
  -> call existing owner-resolving SQL with the resolved user_key
  -> only after an owner row is returned, perform any Blob operation
  -> return owner-safe application state or app-mediated bytes
```

When the global flag is false, a signed-out direct Photo request is also denied
neutrally; it must not change into a sign-in redirect merely because the proof
gate is active. The normal protected `/app/capture` route keeps its existing
signed-out sign-in behavior.

## Neutral denial contract

There are two neutral-denial layers:

### Cohort gate denial

- `/app/capture` renders the ordinary flag-off product: no Photo selector, no
  Photo asset, no Photo draft rehydration, and no Photo capability claim.
- `/app/capture?photo=<key>` and every direct `/app/capture/photo...` route
  return the exact status, body shape, headers, and redirect behavior used when
  the global Photo flag is off.
- The response contains no Photo state, cohort reason, configured identity,
  expiry, route inventory, or key validity signal.
- `Cache-Control: private, no-store` and `X-Content-Type-Options: nosniff` apply
  to any structured denial response added by the later implementation.

### Object authorization denial

After both synthetic owners pass the cohort gate, Owner B's request for Owner
A's valid key must be byte-for-byte equivalent, except for nondeterministic
headers, to B's request for a random absent key. Existing route classes may use
different absent outcomes (for example 404 for media/status and the existing
changed/stale result for state transitions), but another owner's valid object
must never be distinguishable from absence.

## Protected endpoint inventory

The future proof must cover every current protected surface that can reveal or
change Photo state:

| Surface | Authorization requirement |
| --- | --- |
| `GET /app/capture` | List only the resolved owner's Captures; expose Photo entry only to an admitted identity. |
| `GET /app/capture?photo=<source_key>` | Gate first, then owner-resolve the source before returning any draft state or app URL. |
| `POST /app/capture/photo` | Gate and same-origin check; accepts no owner, Blob, account, container, or path parameter. Creates only the resolved owner's source. |
| `GET /app/capture/photo/<source_key>` | Gate and owner-resolve; return owner-safe status without storage locators. |
| `POST /app/capture/photo/<source_key>/reconcile` | Gate, same-origin, current row version, and owner-resolve before reading Defender tags or original bytes. |
| `POST /app/capture/photo/<source_key>/confirm` | Gate, same-origin, owner-resolve, current row version, clean source, safe derivative, required note, and explicit confirmation. |
| `POST /app/capture/photo/<source_key>/delete` | Gate, same-origin, owner-resolve, current row version, and explicit draft-delete confirmation. |
| `GET /app/capture/photo/<source_key>/preview` | Gate and owner-resolve before Blob lookup; derivative only. |
| `GET /app/capture/photo/<source_key>/original` | Gate and owner-resolve before Blob lookup; attachment, private/no-store, generic name. |
| `POST /app/capture/<capture_key>/correct` | Existing same-origin, owner, and row-version boundary must deny the second owner. |
| `POST /app/capture/<capture_key>/archive` | Existing same-origin, owner, and row-version boundary must deny the second owner. |
| `POST /app/capture/<capture_key>/restore` | Existing same-origin, owner, and row-version boundary must deny the second owner. |
| `GET /app/capture/<capture_key>/export` | Existing owner boundary; schema v3 must expose only app-mediated paths and synthetic content. |
| `POST /app/capture/<capture_key>/delete` | Existing same-origin, owner, row-version, distributed-delete, and finalization boundary. |
| `POST /app/capture/<capture_key>/moment-proposal` | Negative guard: second owner denied and the lifecycle proof creates no automatic or proof-only Moment. |

## Threats, controls, and stop signals

| Threat | Required control | Immediate stop signal |
| --- | --- | --- |
| Ordinary-member feature discovery or access | Global flag false; exact internal-key cohort; selector/assets omitted; every direct route gated | Non-cohort C sees Photo UI, a Photo-specific response, or any status other than the approved neutral contract |
| Client identity spoofing | Use only `PeerSlateIdentity.user_key` from the trusted server identity boundary; ignore email/owner values in requests | Changing a header, form/query value, or source key grants cohort access |
| Cohort/configuration drift | Empty default, exactly two distinct keys, explicit UTC expiry, invalid/expired configuration fails closed | Missing/invalid expiry, unexpected cohort cardinality, both general and proof flags active, or a value printed in logs |
| Ungated endpoint | Central access policy plus route-inventory tests for every endpoint above | Any direct route behaves differently from the flag-off or nonowned baseline |
| IDOR/cross-owner access | Existing owner-resolving stored procedures before storage; B-versus-A matrix | B receives A state, media, export, mutation, or a distinguishable existence signal |
| Blob locator or credential leak | App-mediated URLs only; response/log/export/screenshot scan | Blob name/account/container/SAS/digest/auth material appears anywhere outside trusted transient process memory |
| Unscanned or unsafe delivery | Known-clean Defender result plus independent bounded decode and derivative before preview/confirm; never equate decode/dimension rejection with Defender detection | Pending, error, application-rejected, Defender-malicious, or original bytes render as a preview or can be confirmed |
| CSRF or stale/concurrent mutation | Existing same-origin checks, explicit confirmations, row-version tokens, idempotent confirmation/delete | Cross-site write succeeds, stale write wins, duplicate Capture/link appears, or delete reports success early |
| Real member content read | Synthetic identities and owner-scoped operations only; no broad member queries | Any real member name, content, source, key, Blob, Capture, or count is retrieved or displayed |
| Evidence leakage | Synthetic fixtures, alias-only records, viewport screenshots, payload-free logs | Screenshot/log/JSON committed with identity, content from a real member, URL key, cookie, token, or provider payload |
| Synthetic data left behind | Preplanned inventory, draft and confirmed delete, two-Blob active absence, link/content teardown, final zero-live-record check, and separate recording of seven-day soft-deleted retention | Any live synthetic Capture, link, source payload, active original, active derivative, or deletion backlog remains; retained soft-deleted bytes are a Conditional follow-up, not a false permanent-absence claim |
| Accidental downstream behavior | Before/after synthetic-owner counts for Moments/Placements/publication using owner-scoped checks only | Any Moment, Placement, audience, share, publication, or homepage write occurs |
| Shared-lane collision | Later file reservations and current-main synchronization | Any active branch later acquires an exact proposed runtime file; current Owner Home frontend and Interview homepage reservations do not overlap this gate |

Any security/privacy stop signal produces a **Fail**, disables the proof gate
before further investigation, and prevents Photo enablement. An evidence gap,
an owner choice of no production Defender-malicious test, or provider
soft-deleted retention still inside its recovery window produces
**Conditional** without a demonstrated safety violation and keeps both flags
off.
