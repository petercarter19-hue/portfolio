# PS-SLATE-STUDIO-IA-001 — D3 Slate Studio information architecture

**Date:** 2026-07-23. **Author:** Codex at Pete's direction.
**Status:** **DIRECTION / ARCHITECTURE COMPLETE — activation not granted.**
This document resolves the target Studio information architecture inside this
package. It changes no route, shell, flag, application file, controlled
governance record, deployment, or live behavior.

## 1. Decision

Slate Studio is one protected experiential system with three member-facing
stations:

1. **Workshop** — the resumable command deck and protected owner entry;
2. **Build Your Future** — the private workspace in which Slate Board is the
   central canvas; and
3. **Interview Studio** — the current public, browser-local practice product
   linked truthfully until the later practice/coaching transition package
   creates an authenticated successor.

The target signed-in context remains:

`My Slate | Slate Studio | Community`

The Studio-local navigation remains:

`Workshop | Build Your Future | Interview Studio`

These are two different navigation levels. Global navigation changes rooms.
Studio navigation changes stations within the Studio experience or, for the
provisional Interview Studio entry, hands off to the existing public product
with its truth boundary disclosed.

## 2. Canonical target routes

| Member-facing destination | Target route | D3 ruling |
|---|---|---|
| Workshop | `/app` | Keep the stable protected owner entry. Owner Home is absorbed into the Workshop role rather than becoming a competing fourth destination. |
| Build Your Future | `/app/studio/build-your-future` | Canonical protected route proposed for Slice 1. It is not created by this package. |
| Interview Studio | `/interview-studio` | Keep the real current public/browser-local route and name. The Studio tab must disclose that boundary before or at handoff. |
| Future authenticated practice | `/app/interview-studio` | Preserve the already reserved future boundary. Do not create, redirect, or simulate it in Slice 1. |
| My Slate | server-resolved canonical member Slate or exact owner preview | Never hardcode Pete or a profile slug. Use the real authorized/published route supplied by the server. |
| Community | current canonical Community route | No Community IA or behavior changes in this package. |

`/app/studio` is not introduced as an empty index or redirect in Slice 1.
Workshop already supplies the protected Studio opening at `/app`, so another
intermediate route would add a chooser rather than advance the command-deck
model.

## 3. Owner Home and Workshop ruling

**Selected model: Owner Home evolves into Workshop.**

The finite `owner-home.v1` contract is useful Workshop material: review items,
one next step, recent or resurfaced context, and truthful availability can
become calm station/state lights. It does not define the full Workshop and it
does not become a metrics dashboard.

Consequences:

- `/app` remains the stable authentication return and protected entry.
- "Home" is not added to global or Studio navigation.
- Workshop resumes one useful thread; it does not present a feature chooser.
- Existing Owner Home implementation and flag behavior remain untouched until
  a separately activated runtime package owns the convergence.
- Slice 1 may link Workshop to the current `/app`; it may not rewrite Owner
  Home, expand `owner-home.v1`, or fabricate Workshop stations.
- A later Workshop slice may reuse the finite owner-home service contract only
  after exact field/state allocation and file ownership are accepted.

This absorbs the direction of `PS-SHELL-001` into Slate Studio. It avoids a
separate shell program while preserving the existing owner-shell,
authentication, no-store, and server-derived identity foundations.

## 4. Persistent shell and center-stage model

The shell persists while the center stage changes. Its bounded responsibilities
are:

- signed-in identity and account access;
- global room navigation;
- Studio-local navigation;
- current-room and current-station orientation;
- private/public truth state;
- theme parity;
- skip link, focus management, alerts, and recovery placement; and
- a single main content stage.

The shell does **not** own canonical professional data, Board data, Journal
records, Project lifecycle, practice history, AI retrieval, publication, or a
new mobile bottom bar.

The Build Your Future stage preserves the locked hierarchy:

1. page identity and sandbox explanation;
2. private workspace / published Slate status;
3. Slate Board as the dominant object;
4. selected grounded work and its Work–Story–Future lens;
5. a restrained set of creative directions; and
6. the sandbox/truth footer.

Slices may reveal this hierarchy progressively, but they may not replace it
with a dashboard, generic card grid, feature menu, Kanban board, or AI-first
chat surface.

## 5. Navigation behavior

### Global navigation

- **My Slate** opens the member's real server-resolved Slate or exact preview
  when available. It is never a hardcoded Pete route.
- **Slate Studio** is current for Workshop and Build Your Future.
- **Community** uses its current canonical route.
- Global navigation remains usable without JavaScript and exposes one
  `aria-current="page"` destination.

### Studio navigation

- Workshop and Build Your Future are protected owner destinations.
- Interview Studio links to the current public product in Slice 1.
- The Interview Studio entry includes concise visible or programmatic context:
  `Public practice · browser-local history`.
- Crossing to the public product must not imply account-backed practice,
  private Slate grounding, or cross-device history.
- On return from a public product, the protected route re-authorizes identity;
  the browser is never trusted to carry owner context.

### Context rail

Slice 1 does **not** adopt the Context Rail. The frame has no three-to-six
genuine internal views yet, and adding a rail would create an empty navigation
layer. The Work–Story–Future lens is a selected-item control in a later slice,
not a page-level route or Slice 1 rail.

## 6. Build Your Future object boundaries

| Concept | Boundary |
|---|---|
| Slate Board | A spatial planning view and future read/presentation surface. Board notes are not canonical Work or Projects. |
| Work | The broader roles/contributions/outcomes domain. One selected Work object may later be projected into the Board without copying it. |
| Project | A private-first canonical container governed by `PS-PROJECTS-001`. A Board Project note may point to or propose one but cannot create it silently. |
| Public résumé / Living Résumé | Existing product and dataset. Build Your Future may later propose governed wording or uses; it does not create a second résumé truth. |
| My Story | Existing finite public projection. Story composition remains in `PS-STORY-COMPOSER-001`; Build Your Future cannot publish or rearrange it in Slice 1. |
| Work–Story–Future | Three derived lenses over the same selected source/object, never three records, datasets, permanent columns, or destinations. |
| Board layout | Future owner-scoped presentation/relationship metadata separate from canonical content. No persistence in Slice 1. |
| Ask Slate | A contextual, optional collaborator at a selected object or action boundary. Never a mandatory doorway or permanent side rail. Not available in Slice 1. |

The unresolved member-editable professional-record contract does not block the
shell-only Slice 1 proposal because Slice 1 does not retrieve, create, or edit
professional records. It remains a hard gate before a populated Board,
selected-work detail, or editing slice.

## 7. Truth and authorization model

- Every `/app` route resolves identity from the trusted server session.
- The protected route has no user-supplied owner slug or ID.
- Authorization is resolved before private data, media, search, cache, or AI
  retrieval.
- Private and published are separate states and actions.
- `View published Slate` is a link to the exact currently published projection;
  it is not a preview, publish control, or claim that a published Slate exists.
- If no published route is available, the interface says so and provides no
  dead or fabricated link.
- AI, speech, Board, and downstream services may be absent without breaking the
  shell, navigation, status explanation, or published-Slate link.
- The sandbox promise remains visible: **Nothing you try here changes what is
  live until you decide.**

## 8. Responsive model

- **Desktop:** persistent global header, Studio navigation, and a generous
  center stage. The Board remains dominant and the selected-work region sits
  directly below it when later slices populate both.
- **Tablet:** the same semantic order with the Board using available width.
  No permanent side rail is introduced.
- **Mobile:** list/region-first composition. The spatial Board is never shrunk
  into unreadable miniature text; later populated Board slices provide a
  structured equivalent.
- **200% zoom/reflow:** equivalent to the narrow single-column composition;
  there is no horizontal page scroll.
- **Short landscape:** headers are not allowed to consume the viewport with
  stacked sticky layers; the main stage remains immediately reachable.

Responsive presentation may recompose; it may not change the route, truth
state, available action, or source meaning.

## 9. Architecture allocation

| Requirement / risk | Allocated boundary |
|---|---|
| Trusted sign-in and safe return | Existing auth blueprint and identity boundary |
| Owner-only shell | protected `/app` route family; private no-store response |
| Global / Studio navigation | server-rendered shared Studio shell component |
| Build Your Future visual hierarchy | locked files in document 04 plus Slice 0 authority in document 07 |
| Published Slate status | server-supplied canonical published route/state; no client inference |
| Board content and selection | later Slice 2 contract |
| Selected-work provenance | later Slice 3 contract |
| Editing and evidence connection | later Slice 4 contract |
| Work–Story–Future proposals | later Slice 5 contract |
| Experiments and future cards | later Slices 6–7 |
| Authenticated practice/coaching | separate Slice 8 transition package |
| Public-page alignment | separate later package |

## 10. Controlled-authority alignment

This D3 decision applies, without weakening, Bible requirements
`PS-CORE-IA-001`, `003`, `005`, `009`, `013`–`016`;
`PS-CORE-DATA-001`, `006`, `007`; `PS-CORE-SEC-001`; and
`PS-CORE-NFR-001`, `005`, `008`.

It also preserves Roadmap Gate A/B/C separation and the existing facts that:

- target route grouping remained open in Bible v2.8/Roadmap v2.7;
- the current public Interview Studio is not authenticated owner practice;
- Slate Board Project notes are not canonical Projects; and
- retained ideas do not authorize implementation.

The work-first priority and exact target routes in this document remain
package-local proposals until Pete activates the corresponding controlled
Bible/Roadmap and runtime packages.

## 11. D3 outcome

D3 is complete for direction/architecture:

- Owner Home becomes Workshop rather than a competing destination.
- the shell is absorbed into Slate Studio;
- `/app` is the protected Workshop entry;
- `/app/studio/build-your-future` is the proposed canonical Build Your Future
  route;
- the current public Interview Studio route and truth boundary remain;
- the future authenticated practice route remains reserved;
- Board / Work / Project / résumé / Story boundaries are explicit; and
- navigation, shell, responsive, authorization, and Ask Slate placement rules
  are allocated.

No implementation is activated by this outcome.
