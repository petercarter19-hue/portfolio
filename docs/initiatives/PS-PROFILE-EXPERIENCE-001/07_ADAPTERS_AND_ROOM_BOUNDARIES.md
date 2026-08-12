# Adapters and Purpose-Built Room Boundaries

## Integration rule

Profile reads or publishes exact references through owned adapters. It does
not become a second persistence layer for another room's canonical truth.

| Room/capability | Canonical owner | Profile adapter output | Profile must never do |
|---|---|---|---|
| Community | Community post/conversation service | Eligible authored Post projection, exact attachment refs, canonical conversation URL | Copy a thread, silently turn all activity into Profile, or publish a comment as identity |
| Projects | Project record and Project Projection service | Exact released Project projection/version plus authorized related refs | Edit Project work, infer outcomes, or expose private workspaces |
| Capture Media | Private Capture/media source service | Approved derivative and metadata reference after explicit publication | Publish on upload, expose Blob/SAS/source filename/EXIF/GPS, or create a Profile-owned original |
| Voice | Voice source, transcript-version, and projection service | Authorized playable audio endpoint plus exact approved transcript | Treat provider transcript as truth, retain dictation, autoplay, or infer personality/emotion |
| Résumé | Living Résumé publication | Stable deeper path and deliberately selected public fact reference if separately authorized | Rebuild or edit résumé truth in Profile |
| My Story | Story/Moment publication | Stable deeper path and deliberate excerpt/image projection | Copy chapters or turn About into My Story |
| Ask `[Name]` | Public-AI source authorization | Optional action using exact Public sources only | Retrieve private/Connections material then filter it |
| Workshop/My Knowledge | Private development/confirmed information | Owner-only navigation and explicit proposal-to-projection workflow | Expose private knowledge, Goals, or AI proposals |
| Interview Studio | Interview browser/session truth | Navigation only in v1 | Publish answers, scores, coaching, camera, or history automatically |
| Opportunity Slate | Saved opportunity analysis | Navigation only in v1 | Publish qualifications, gaps, evidence judgments, or employer data automatically |
| Settings/My Data | Account/privacy/export/security | Canonical Settings doorway | Create duplicate account controls in Profile |

## Adapter contract

Every adapter exposes a narrow, purpose-specific interface:

```text
list_profile_eligible_sources(owner, source_cursor)
get_exact_source_version(owner, source_key, version)
build_projection_proposal(owner, source_version, audience)
validate_projection_reference(owner, projection_version, audience)
resolve_viewer_projection(viewer_context, projection_key)
revoke_projection_reference(owner, projection_version, reason)
```

Names are illustrative, not an implementation prescription. Required
properties are owner isolation, exact version, explicit audience, no content
copy where a reference suffices, neutral absence, and idempotent command
behavior.

## Community and Posts

Community remains the day-to-day social room. Profile Posts is the member's
authored, audience-resolved archive. A Community Post does not appear merely
because it exists. The member explicitly creates a Profile projection and
placement. `Respond`, `Comment`, and `Open conversation` operate against the
canonical Community conversation after its own authorization succeeds.

Community discovery/news/jobs/fun-content preferences remain a separate Feed
program decision and do not change the Profile Posts contract.

## Capture and owner entry

Profile `Add something` may become a prominent entrance to shared Capture
capabilities, but Capture remains the intake layer:

```text
Type or speak / add media
-> private source or draft
-> member chooses Keep private, Work on it, Share to Community,
   Add to Project, or propose a Profile projection
-> exact review and explicit destination action
```

One capture may be referenced by several destinations without duplicating its
canonical source. Broader first-sign-in guided capture and Capture/Slate global
shell prominence belong to the shared-shell/Capture program, not this runtime.

## Add-something canonical routing

`Add something` is one entry experience, not one generic Profile data store.
Before durable save, the member sees which room owns the source and what
Profile may later publish:

| Member action | Canonical source owner | Profile result |
|---|---|---|
| Edit identity, current chapter, About, or Home curation | Profile-native content/version service | Private Profile-native draft, then exact audience projection |
| Type an authored update or question | Community draft/post service | Exact Community projection reference after explicit post and Profile choices |
| Speak to type | Transient dictation feeding the selected canonical composer | Editable text only; recording discarded; no Profile Voice object |
| Add photo, video, or general file | Capture/media source service | Private source first, then an approved derivative/projection reference |
| Record retained Voice | Voice source/transcript service | Private retained source and reviewed transcript, then exact playable projection reference |
| Add or select a Project | Projects workspace/projection service | Exact Project projection reference only |
| Select an existing object | Its source-owning room through an allowlisted adapter | Private projection/placement draft referencing the exact source/version |

`POST /api/v1/profile/draft/items` may create only Profile-native identity,
current-chapter, About, and curation content, or a projection draft that
references an already-created canonical source. It cannot accept raw Community
post bodies, media bytes, audio, Project records, Story/Resume truth, Workshop
knowledge, or arbitrary files as Profile-owned canonical data.

## Dependency availability

A Profile control appears only when its adapter and downstream lifecycle are
released and healthy. Missing dependency behavior is honest and local:

- hide a destination that has no published visitor content;
- offer an Owner first-use state only for a real available workflow;
- retain the last current publication if a new adapter proposal fails;
- never replace a missing dependency with fabricated fixture data; and
- never let an adapter outage broaden visibility.

## No circular authority

Profile publication never makes its own projection canonical for the source
room. If a Profile edit could improve a Résumé fact, Story Moment, Project,
Community Post, Voice transcript, or My Knowledge item, it becomes a proposal
returned to that room. The owner approves it there before a new source version
can support a later Profile projection.
