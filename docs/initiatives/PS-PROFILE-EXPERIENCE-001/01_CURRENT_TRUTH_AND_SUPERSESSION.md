# Current Truth and Supersession

## Verified baseline

At package base `f745b39b72d2c8e5a3595f88d7f9524d8d8e41cf`:

- `GET /petec` and `GET /petec/overview` return `302` to
  `/petec/resume`.
- `GET /petec/resume` and `GET /petec/my-story` are the current public
  professional and narrative destinations.
- `GET /petec/projects`, `/petec/work`, `/projects`, and `/work` redirect to
  `/petec/resume#experience`.
- `GET /petec/about` is an existing static portfolio page whose content must be
  deliberately reconciled before Profile About replaces it.
- `/app/profile` and the six Profile destinations do not exist.
- `member_profiles`, `slate_entities`, access grants, publication-version
  scaffolding, connection/request/block/report tables, private Capture, private
  Voice, Community, Résumé, My Story, and Ask Pete foundations exist in
  different states. None proves a released Profile publication system.
- Current `entity_publication_versions.snapshot_json` is not an approved
  Profile content store. Its generic JSON and one-version sequence cannot
  safely model independent Public and Connections publication branches.

## Preserve

| Existing capability | Disposition |
|---|---|
| `member_profiles` identity and slug anchor | Reuse after server-side identity and active-profile validation |
| trusted Easy Auth identity adapter | Reuse; do not add a second session model |
| Résumé and My Story routes | Preserve as stable deeper Profile destinations |
| Ask Pete public evidence boundary | Preserve for Pete; generic Ask `[Name]` remains separately gated |
| Community canonical posts/conversations | Reference through an adapter; never copy |
| Placement exact-version/body-free principle | Reuse in the Profile publication model |
| private Capture media and Voice source lifecycles | Reuse through source adapters; never auto-publish |
| Project private-first/projection boundary | Reuse; Profile publishes exact Project projections only |
| relationship/block/report foundations | Harden additively before Connections release |
| current public routes while flag is off | Preserve exactly through dark deployment |

## Supersede

The following are historical evidence, not current product authority:

- `origin/work/2026-08-03-profile-001-architecture-v2` and its older
  Overview/My Story/Posts/Behind Story/Résumé information architecture;
- older permanent owner-rail and 1200/1440-pixel boxed Profile compositions;
- the legacy `profile_shell.html` / `profile_tabs.html` assumption that every
  `/petec` page is one Pete-specific portfolio fixture;
- content-bearing or arbitrary publication snapshots;
- automatic mapping of ambiguous legacy `shared` or `recruiter` visibility;
- Slate Board as a public Profile destination;
- Owner Home as a new standalone landing-page product;
- any generated name, date, count, portrait, photograph, project, transcript,
  or relationship in the visual boards as production data.

Preserve the Git history and evidence. Do not merge, delete, rewrite, or adopt
those branches as current implementation.

## Protect

- Résumé remains the professional evidence ledger.
- My Story remains the editorial narrative journey.
- Profile becomes the social/professional front door and command surface.
- Community remains the day-to-day social conversation room.
- Workshop/My Knowledge remains the private development and confirmed-
  information engine.
- Capture remains a reusable private-first input capability.
- Opportunity Slate and Interview Studio remain purpose-built work rooms and
  do not automatically publish results to Profile.

## Honest availability at initial dark implementation

Every depicted control must be backed by a real released dependency. Until
then, omit it or render an explicitly disabled `Coming later` state only where
the locked composition requires future orientation.

| Capability | Current truth | Profile implementation rule |
|---|---|---|
| Public Profile | Not live | Build reusable and flag off; no route cutover until enablement |
| Owner Profile | Not live | Build same body with contextual controls, authenticated and no-store |
| Connections audience | Tables exist; complete hardened service not proven | Do not expose until relationship lifecycle and two-owner tests pass |
| Connect | Not a complete member workflow | Hide until request/accept/cancel/decline/disconnect/block is real |
| Message | Not released | Hide; messaging is not part of Profile v1 |
| Profile search | Not released | Build only over pre-authorized Profile projection indexes |
| Profile posts | Community owns canonical posts | Reference exact Community projections; no second post store |
| Albums/video library | Not released | Add governed projection/derivative lifecycle before controls appear |
| Voice posts | Public retained Voice not released | Build exact audio + approved-transcript projection before appearance |
| Projects | Planned private-first foundation | Profile Projects appears only for exact released Project projections |
| Ask `[Name]` | Pete-specific Ask Pete is live | Generic control remains hidden until reusable, separately authorized |

## Owner direction recorded by this package

Pete withdrew the prior Claude Profile assignment and assigned Codex to own
Profile direction, architecture, implementation, verification, merge, and dark
deployment. Pete will review the exact deployed candidate immediately before
public enablement. That delegation permits Codex to adopt the complete
ChatGPT-created 33-board set as production direction and make only documented,
non-material truth, accessibility, responsive, and implementation adaptations.
