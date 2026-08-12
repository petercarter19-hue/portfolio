# Purpose, Destinations, and Journeys

## The room model

Profile is one governed view of the member's continuous record. It is the
front door, not the warehouse. Each destination changes how authorized parts
of that record are explored without changing who owns the underlying truth.

```text
Private sources and purpose-built rooms
        |
        v
member-approved exact projection versions
        |
        v
Public or Connections publication revision
        |
        v
Profile Home / Posts / Projects / Media / Voice / About
```

## Dominant-purpose rule

Each destination gives the greatest combination of area, contrast, and
persistence to its real work object:

| Destination | Dominant object | Primary visitor action | Must not become |
|---|---|---|---|
| Home | Finite curated view of the person | Choose a deeper path | Résumé overview, dashboard, or infinite feed |
| Posts | Authorized authored stream | Read or open canonical conversation | News/discovery feed or duplicated Community |
| Projects | Selected work with role, outcomes, and proof | Explore a Project projection | Task manager or résumé card grid |
| Media | Album-led member-chosen visual record | Open an album or video | Private device library or masonry without context |
| Voice | Selected playable reflection + approved transcript | Listen or read | Podcast analytics dashboard or dictation tool |
| About | Profile-specific personal orientation | Understand the person and go deeper | My Story copy or second Résumé |

## Home composition

Home is a finite manifest, never “latest everything.” Recommended initial
maximums:

- identity and current chapter;
- one Featured object;
- two to four selected Posts;
- one Voice highlight;
- up to three Projects;
- one Media/album preview with an audience-correct `+N`;
- one Video highlight; and
- one About excerpt.

The owner may reorder available modules and select one Featured item. A source
appearing in a destination does not automatically appear on Home. Removing a
Home placement does not unpublish or delete its source.

## Public visitor journey

1. Open `/<slug>` without an account.
2. Receive only the current Public publication revision.
3. Understand the member through identity, current chapter, and selected
   material.
4. Browse only destinations that have Public content.
5. Search only that member's Public Profile index when search is available.
6. Open Résumé, My Story, a Project, Media, Voice, or a public-safe Community
   conversation through canonical links.
7. Sign in only when an action truly requires membership; preserve the exact
   safe return path.

## Connection journey

1. Sign in and open `/<slug>`.
2. The server proves an active connection and absence of a block before any
   Connections query runs.
3. Receive the Connections publication branch, which may include Public items
   by explicit placement but is not a client-side overlay on a Public payload.
4. See audience labels where they prevent misunderstanding.
5. Lose Connections access immediately on disconnect, block, withdrawal, or
   authorization-epoch change.

## Owner journey

1. Direct sign-in reaches stable `/app`, which routes to the member's
   canonical Profile only after the approved cutover.
2. The owner sees the same recognizable body plus one restrained Profile
   context row containing Add something, Manage, and View as public.
3. Add something begins private and distinguishes Type, Speak to type, Photo,
   Video, retained Voice, File, and Project.
4. Manage shows exact audience, placement, source version, projection version,
   where used, and stale-source truth.
5. The owner edits a draft without changing the current publication.
6. Exact Public preview runs the anonymous Public serializer, not CSS hiding.
7. Review and publish compares the draft to the current publication and
   changes exactly one audience branch after explicit confirmation.
8. On failure or conflict, the old publication remains intact.

## Sparse and scale behavior

- A sparse Profile is complete, dignified, and useful. It does not shame the
  member or fill the page with fake recommendations.
- Public navigation hides empty destinations. Direct unavailable destination
  requests use one neutral, non-enumerating response.
- Owner navigation retains empty destinations and offers one relevant first
  action.
- One item receives full reading space.
- Typical collections use calm continuation.
- Large collections use pre-authorized search/filter plus stable pagination;
  the browser never renders hundreds of players or media objects at once.

## Voice-first, text-equal entry

Voice is a platform primitive and a prominent owner entry, never mandatory.
Every voice-first prompt offers an equal Type path and a safe Skip/Cancel. The
interface always states whether audio is discarded after transcription or
retained as a private/public audio object before recording begins.
