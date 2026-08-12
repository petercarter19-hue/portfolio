# Search, Moderation, Privacy, and Legal Readiness

## Status of this document

This is an architecture requirement, not legal advice, counsel approval, a
security assessment, or launch permission. Public and Connections Profile are
permissioned/public member-content capabilities and therefore inherit the
applicable requirements and Gate L2 from
[EARLY_LEGAL_AND_SITE_READINESS_STANDARD](../../governance/EARLY_LEGAL_AND_SITE_READINESS_STANDARD.md).

Documentation may merge while these later proofs are honestly conditional.
Public/Connections enablement may not.

## Authorized Profile search

Search is projection-first:

1. choose the current viewer context and publication revision;
2. query only index rows created from that authorized revision;
3. return only exact projection keys still present in that revision; and
4. authorize the selected result again when opened.

There is no global private index followed by audience filtering. Public and
Connections indexes are physically/logically separable and keyed by profile,
audience, publication revision, projection version, destination, and safe
search text. Withdrawal, disconnect, block, deletion, and revision advance
invalidate affected rows and cache epochs.

Searchable text is limited to member-approved Profile wording, approved Voice
transcripts, and explicitly authorized adapter fields. It excludes provider
transcript proposals, raw audio/media, private My Knowledge, Opportunity or
Interview material, private source metadata, filenames, EXIF/GPS, relationship
details, and hidden counts.

No-match and unauthorized results are indistinguishable. Queries, result
events, and logs follow a minimized retention schedule and never become public
AI sources merely because they were searched.

## Moderation and member safety

Before multi-member Profile release, the product needs operational—not merely
visual—paths for:

- report content, person, Project, media, Voice, and conversation;
- block and unblock with immediate authorization effects;
- copyright/IP and impersonation contact/takedown;
- harassment, non-consensual intimate media, threats, spam, and prohibited
  upload handling;
- evidence preservation and lawful retention when appropriate;
- owner notification, appeal, escalation, and restoration decisions;
- moderator/support authorization, audit, least privilege, and break glass;
- response targets, incident ownership, and after-hours escalation; and
- source correction or owner disablement for public Ask `[Name]`.

Profile does not ship Message in v1. Messaging requires its separate Gate L4.
Removing a Profile placement is not a substitute for moderating the canonical
Community content or source object.

## Required data inventory

The release record must enumerate actual data flows for:

- account, identity, slug, relationship, block, report, and consent;
- private source/draft and audience publication revisions;
- Posts/Community references and conversation actions;
- Projects, Résumé, Story, Workshop/My Knowledge, and public-AI references;
- photo, album, video, Voice audio, transcript attempts/versions, derivatives,
  captions, alt text, and downloads;
- search/index/cache/CDN and authorization epochs;
- AI input/output and provider processing;
- telemetry, support, moderation, incident, export, and deletion evidence; and
- test fixtures, screenshots, visual review artifacts, and backups.

For each class, record purpose, source, system, region, subprocessor, access,
retention, export, correction, deletion propagation, backup/cache/index
behavior, security control, and owner/controller role.

## Privacy and deletion truth

- Private is the default. Public and Connections require explicit exact
  preview and publication.
- UI must distinguish unpublish, remove placement, archive private source,
  revoke, delete source, moderation hold, and account deletion.
- Deletion claims include active stores, derivatives, indexes, caches,
  providers, backups, publication revisions, recipient copies, exports, and
  legal/moderation holds. Do not promise instant erasure where it is untrue.
- Privacy access/export/correction/deletion requests require safe identity
  verification and may not expose another person's Profile or relationship.
- Retention schedules and deletion jobs exist before collecting new album,
  video, Connections-event, or public Voice data.
- Public/Connections pages and media never include secrets, source credentials,
  private IDs, or third-party confidential material.

## Voice/upload/public-AI disclosures

Before use, Voice explains recording consent, retained versus transient audio,
transcription/provider processing, member correction, playback, retention,
deletion, audience, and jurisdictional constraints. Upload UI addresses
ownership/license, third-party confidential/copyrighted content, prohibited
uploads, malware/content limits, extraction, provider processing, and deletion.

Public Ask `[Name]` is a separate opt-in over exact Public projection versions.
It needs abuse/rate limits, cost ceiling, owner disable, sensitive-source
exclusion, source correction, uncertainty/citation behavior, and contact path.
It never accesses Connections or private data.

## Age, marketing, policy, and accessibility claims

- Define and enforce the age/minors position before broad registration.
- Privacy, Terms, Acceptable Use, support, accessibility/contact, copyright/IP,
  and moderation links are accurate, reachable, dated, and versioned.
- Cookie/tracking disclosures match actual geography and enforcement.
- Marketing and homepage claims match exact live audience, AI, persistence,
  deletion, verification, privacy, and security behavior.
- Claims such as private, secure, verified, encrypted, anonymous, deleted, or
  “AI will not train” require scoped technical and contractual evidence.
- WCAG intent is not a conformance claim without real testing and a remediation
  contact path.

## Privacy-safe telemetry

Allowed operational events use opaque IDs and bounded fields such as route
family, mode, publication revision, latency bucket, result count bucket,
command outcome, media state, and error taxonomy. Never record Profile body
text, search query content, transcripts, audio, photos/video, filenames, exact
URLs with private data, AI prompts/answers, relationship notes, or session
replay of member content.

## Enablement gates

The mandatory pre-enable record names actual reviewer, date, evidence, and
result for:

1. Gate L0 inventory/operations;
2. counsel review of public content, audience, indexing, revocation, copyright,
   impersonation, age, Voice/upload, and public AI;
3. repository-grounded threat model and independent payload-isolation/security
   review;
4. moderation, support, privacy request, deletion, incident, and accessibility
   exercises;
5. exact-audience member validation; and
6. Pete's final acceptance of the dark-deployed candidate.

Every item is `passed`, `conditional`, or `failed`. Repository drafting never
counts as a passed professional review.
