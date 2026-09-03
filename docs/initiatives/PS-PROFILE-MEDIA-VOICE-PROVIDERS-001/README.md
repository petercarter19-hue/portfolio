# PS-PROFILE-MEDIA-VOICE-PROVIDERS-001

## Outcome

Deliver dark, repository-only Profile photo and retained-Voice providers over
the closed D0 projection contracts and injected canonical ports. The providers
bind one exact owner, projection key/version, audience, source key/version,
immutable digest, current source lifecycle, and audience authorization before
private bytes can be opened. They are not registered in the application.

Delivery path is **Protected**. Repository authority is `through_merge`, but
production authority is withheld. The approved deferred-registry sequence is
complete: `docs/governance/PACKAGE_REGISTRY.json` is now a claimed surface and
contains one alphabetized `current_protect` row with freshly computed counts.
The provider modules themselves remain unregistered at runtime.

## Delivered contracts

`services/profile_media_projection_provider.py` defines four injected ports:

- an exact publication-grant reader;
- an exact Public or Connections audience/block decision;
- an owner-scoped Photo source-lifecycle reader; and
- a locator-free private `open_preview` byte boundary.

Only `photo` and `preview` are eligible. The source must be confirmed, current,
not deleted, clean-scanned, metadata-stripped, and bound to the grant's exact
source version and derivative digest. The opened body, content type, byte
length, declared digest, and computed SHA-256 must agree. Album and video
providers are absent, and no original-media method exists.

`services/profile_voice_projection_provider.py` defines parallel injected
ports for the exact Voice publication grant, audience/block decision, retained
source lifecycle, and locator-free `open_audio` boundary. Voice binds the
exact retained source version and digest plus the approved Capture revision.
Only the member-approved transcript field can become canonical output; provider
transcription attempts are not represented by any port or return type.

Two partial states remain truthful:

- an approved transcript may be returned without audio and performs no byte
  open; and
- audio may be returned without a transcript, with
  `transcript_available=False` and `autoplay=False`.

## Authorization and race order

Each resolve performs this order without fallback:

1. validate the caller's exact request, including the explicit audience and a
   trusted upstream viewer key for Connections;
2. fetch and validate the exact active publication grant;
3. authorize the same owner/viewer/audience and reject either block direction;
4. fetch and validate the exact current source lifecycle;
5. open only the already-authorized preview or retained audio, when present;
6. re-read and byte-compare the complete grant, authorization epoch/block
   result, and source snapshot; and
7. validate byte length, content type, declared digest, and computed digest
   before returning a locator-free internal value.

Unpublish, revoke, where-used removal, a new authorization epoch or block,
source-version advance, Capture-revision advance, or deletion during the open
causes the same neutral not-found result. Dependency exceptions become one
stable content-free unavailable error without retaining their private cause.
Return-value representations suppress projection content, private bytes,
transcripts, source keys, viewer keys, and digests.

## Boundary and current limitation

The modules import the existing D0 `ProfileMediaProjection` and
`ProfileVoiceProjection` validators, but do not edit those closed services.
They contain no SQL procedure, database service, Blob/Speech/identity client,
provider credential, filename, ETag, provider locator, route, template, flag,
registration, migration, schema apply, deployment, or live call.

There is no current SQL-backed Media/Voice projection-grant reader. This
package therefore delivers concrete validation and authorization-order logic
over injected ports plus deterministic local fakes only. A real persistence or
runtime binding is a separate package and authority decision; it must not be
inferred from this candidate.

## Verification contract

The focused tests prove exact Public/Connections separation, two-owner and
direct-key isolation, unrelated and both-direction block refusal, malformed and
unavailable dependencies, confirmed/current/clean lifecycle requirements,
preview-only Photo access, approved-transcript provenance, both truthful Voice
partial states, digest/length/type checks, retry idempotence, and post-open
revalidation for unpublish/revoke/where-used/block/version/revision/delete
races. Existing Profile D0 and Capture/Photo/Voice suites remain mandatory.

The governed claim-only `extend-surfaces` transition added exactly
`docs/governance/PACKAGE_REGISTRY.json`, and this implementation refreshed from
that exact current main before adding the alphabetized row and recomputed
counts. Focused provider, inherited lifecycle, registry, full-repository,
preflight, compile, diff, and secret-scan validation must all pass on the final
candidate. A new independent exact-SHA review is required before evidence and
receipt binding or merge admission.
