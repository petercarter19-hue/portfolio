# Media, Albums, Video, and Voice Contract

## Private-source-first lifecycle

```text
private upload/record
-> scan/validate/process
-> private source + authorized derivatives
-> metadata/transcript proposal
-> member review and correction
-> exact audience projection proposal
-> exact preview and explicit publish
-> authorized playback/display
```

Upload, processing, transcription, or Capture confirmation never publishes or
places anything automatically.

## Media source and derivative rules

- Original bytes remain private and owner-scoped.
- Public/Connections viewers receive an authorized derivative through an
  application route, not a raw Blob URL or long-lived SAS URL.
- Before storage retrieval, the server proves viewer, subject, current
  publication revision, projection, placement, and derivative authorization.
- Strip or withhold private filenames, internal IDs, EXIF, GPS, device, and
  processing metadata from viewer responses.
- Preserve declared orientation and color safely; validate actual media type,
  dimensions, duration, size, codec, malware/active content, and decompression
  risk server-side.
- Responsive derivatives have immutable digests and exact source-version
  provenance. Regeneration does not silently change a publication.

## Photos, albums, and collections

An album/collection is a member-authored ordering of exact media projection
versions. It has cover, title, optional context, audience branch, order,
version, and current revision. It is not a folder that grants automatic access
to everything placed inside it.

For mixed-source audiences:

- album Public and Connections revisions are built independently;
- cover and `+N` count are chosen from items already authorized for that
  revision;
- removing or revoking one item creates a new revision without exposing a gap,
  filename, or inaccessible count;
- direct item routes repeat authorization rather than trusting album access;
  and
- empty revisions become unavailable without revealing a broader album.

## Video

Profile video is future target capability, not current reusable runtime truth.
Before its control appears, implementation must provide:

- validated upload/processing and safe derivatives/poster frame;
- duration, captions or transcript availability, description, and alt context;
- no autoplay; keyboard-operable play, pause, seek, volume, fullscreen, and
  captions;
- permission denied, interrupted/backgrounded, unsupported codec, processing,
  failed, retry, revoked, and deleted states;
- explicit audience and placement; and
- bounded storage, delivery, retention, abuse, and deletion rules.

Interview Studio local video rehearsal is never imported or published by this
contract.

## Four voice modes

| Mode | Audio retention | Result | Publication |
|---|---|---|---|
| Speak to type | Discarded after transcription attempt/use | Editable text | Text may later be saved/published explicitly |
| Private Voice record/log | Retained privately | Original audio + transcript proposal/review | None by default |
| Voice post/reply | Retained while published/retained | Playable audio + exact member-approved transcript | Explicit audience revision |
| Guided voice conversation | Defined before recording; private by default | Transcript and AI summaries remain proposals | Never automatic |

The interface names the consequence before microphone access. Voice is
prominent, but Type and Skip remain complete paths.

## Voice source and transcript truth

- Preserve the original private recording as source evidence when the member
  chooses a retained mode.
- Store provider transcription attempts immutably and label them proposals.
- The member can edit and approve a transcript version without rewriting the
  original provider result.
- A Voice projection pins exact audio-source and approved-transcript versions.
- Later transcript edits create a new version and do not rewrite an existing
  publication.
- Audio and transcript may fail or be revoked independently; the UI states the
  surviving truth without fabricating parity.

## Player and transcript

No autoplay. The player provides semantic controls, duration, seek, volume,
speed, clear focus, and visible state. A readable member-approved transcript is
available without requiring audio. Public prerecorded audio has transcript
parity. Download is absent by default and requires a separate member-controlled
permission.

Profile Voice search indexes only the exact approved transcript already
authorized to the current viewer. Raw provider proposals and private audio are
never broad-retrieved for search or public AI.

## Consent and prohibited inference

Recording begins only after an explicit member action and visible indicator.
No ambient/background recording. The product must provide clear guidance when
other people may be recorded and preserve jurisdiction-appropriate consent
handling before external beta.

PeerSlate does not create voiceprints or infer emotion, personality,
confidence, accent quality, protected traits, truthfulness, employability, or
candidate fit from audio. Recruiters hear Voice only when the member explicitly
publishes that exact recording and audience.

## Revocation and deletion

Unpublishing removes the projection and playback authorization immediately but
does not delete the private source. Source deletion first shows every current
use, revokes affected projections, advances authorization epochs, completes
derivative/blob deletion, and records truthful completion or retry state.
Export reports distinguish original audio, transcript versions, projections,
placements, retention state, and anything lawfully unavailable.
