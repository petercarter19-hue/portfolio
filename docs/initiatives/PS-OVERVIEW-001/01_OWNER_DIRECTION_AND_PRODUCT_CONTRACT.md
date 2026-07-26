# Owner direction and product contract

## 1. Product purpose

The Member Overview is the public Slate's bottom line up front: a concise,
visually strong orientation that helps a visitor understand who the member is,
what they do, what evidence matters, and where to continue.

It sits above the full résumé and combines:

- fast professional orientation;
- selected evidence and outcomes;
- a curated career arc;
- selected skills and credentials;
- optional Story, values, personality, and future direction; and
- truthful deep links to the fuller public record.

It must not repeat the complete résumé, become a second Story, or turn the page
into an unbounded profile builder.

## 2. One system, two presentation styles

Both styles use the same content contracts, source references, publication
state, accessibility rules, and destination validation.

### Story & Career

The flagship and recommended starting style. It is image-capable and
narrative-forward while retaining strong professional proof. Its ideal visitor
question is:

> Who is this person, how did they become this professional, and what proof
> should I explore?

### Work & Impact

The results-forward alternate. It leads with a concise professional brief,
capabilities, scope, and outcomes. Its ideal visitor question is:

> What can this person do, at what scale, and where is the supporting evidence?

The style changes hierarchy, density, image treatment, and placement. It does
not create a new résumé, duplicate facts, or change the meaning of a record.

## 3. Member and system responsibilities

| Member controls | PeerSlate controls |
| --- | --- |
| Whether an Overview is published | Valid public rendering |
| Which style is selected | Approved style manifest |
| Which eligible records are featured | Record/source eligibility |
| Authored or accepted projection wording | Content budgets and validation |
| Block visibility and semantic order | Geometry, type scale, spacing, and reflow |
| Feature/Standard/Compact emphasis where allowed | Which emphasis options are valid for a block/style |
| Media selection, focal point, alt text, and audience | Safe media rendering and responsive crops |
| One truthful destination per actionable block | Destination existence, authorization, and focus behavior |
| Whether to accept, edit, or reject AI proposals | AI source limits, labels, provenance, and non-publication |

The member does not edit HTML, CSS, pixel coordinates, widths, font sizes,
breakpoint rules, or arbitrary columns.

## 4. Canonical truth and projection model

The Overview stores presentation decisions, not duplicate authoritative facts.

### Record-linked content

Roles, dates, education, certifications, awards, skills, projects, and factual
metrics reference eligible canonical or approved public projection records.
The Overview may store:

- selected record/version identifiers;
- order and emphasis;
- a public-safe purpose-specific summary with lineage;
- an approved destination;
- style-specific media focal data; and
- the state last reviewed by the member.

It does not copy a new authoritative employer, degree, award, skill, or date.

### Authored content

An Executive Brief, philosophy, invitation, or future-direction statement may
exist only in the Overview projection. It is member-owned presentation copy,
not automatically canonical history.

### Hybrid content

A capability, impact, or Story spotlight may combine selected source
references with member-authored or explicitly accepted presentation wording.
The public wording retains owner-visible lineage to its supporting records.

### Source changes

- A benign source evolution—such as adding a new supporting record—never
  silently republishes new Overview wording. The pinned public claim may remain
  when its exact reviewed facts are still valid, and the owner sees
  **Source changed — review Overview** before a later publication can use the
  update.
- A **corrective supersession** means the prior source/version or public claim
  is no longer accurate. The affected public claim fails closed immediately;
  the system invalidates its cached projection and omits the claim or whole
  block according to its contract. It does not silently substitute newly
  corrected wording. The owner must review and explicitly publish a replacement.
- Deletion, revocation, or audience narrowing also fails closed. The
  inaccessible item and its action are removed from public output and the
  layout reflows.
- Correction, withdrawal, and unpublish must not leave dead links, private
  labels, orphaned media, stale claims, or a gap.

## 5. Public placement and navigation

- Pete's current acceptance fixture remains the canonical `/petec/resume`
  surface and its existing redirects/download behavior. Reusable multi-user
  behavior must derive the member/profile route and may not hardcode Pete.
- The future implementation package must name the generalized route contract
  while preserving the current canonical and legacy behavior.
- A published Overview absorbs the current résumé Summary region's identity
  job: portrait, name, professional positioning, introduction, and opening
  actions. The old Summary does not render again below it.
- When no Overview is published—or after the owner successfully unpublishes
  it—the existing Summary remains the fallback opening and the detailed résumé
  continues unchanged.
- Overview is a page region, not a new global destination or navigation layer.
- The current right-side section ribbon derives its first entry from the
  opening that actually renders: **Overview** targets `#overview` when
  published; **Summary** targets `#summary` for the fallback. Existing
  `#summary` and `#resume-overview` compatibility anchors must continue to reach
  the absorbed opening when Overview is published.
- The approved future left Context Rail is a separate deliberate résumé
  migration under `OWNER_CONTEXT_RAIL_STANDARD.md`. This package defines the
  section semantics but does not authorize moving or restyling the current
  ribbon. Either control remains outside the center canvas.
- Public Ask [Name] AI and Résumé PDF remain page-level capabilities. The
  production visual must give each retained capability one clear placement in
  the contextual action area or another inventoried treatment; the Overview
  hero must not duplicate it.
- Overview cards use visible descriptive actions to eligible sections such as
  **View full experience**, **View all 12 skills**, or **Read my full story**.
- The concepts' top navigation and footer are illustrative and do not replace
  PeerSlate's shared shell.
- After **Résumé begins here**, the canonical résumé is authoritative for its
  detailed sections and existing anchor behavior.

## 6. Public density and content hierarchy

The richest mockup is an upper-bound configuration, not the required default.
A good published Overview usually contains:

- one identity hero;
- zero or one proof band;
- four to six meaningful content bands after the hero; and
- no more than approximately eight content bands without an explicit future
  visual decision.

The product reduces selection and wording before it reduces type size. It
never solves density by clipping sentences, hiding content in card scrollbars,
shrinking body copy below the accepted scale, or duplicating the full résumé.

## 7. Manual-first self service

A member can complete every required Overview task manually:

1. start from eligible résumé records or a blank structured draft;
2. select a style;
3. add, edit, hide, and reorder supported blocks;
4. select records and write projection copy;
5. attach eligible media and provide required accessibility/privacy data;
6. select destinations;
7. resolve readiness feedback;
8. preview the exact visitor result at supported states;
9. publish explicitly; and
10. unpublish explicitly when the member wants the Summary fallback again.

AI may accelerate the same tasks, but it is never the only way to complete
them.

## 8. Owner and visitor experiences

### Owner

The authenticated owner sees a structured Overview Composer, source status,
readiness feedback, visitor preview, draft/published distinction, version
history, and explicit publish/unpublish controls.

### Visitor

The visitor receives only the authorized published projection. The public
representation contains no edit controls, draft data, private source names,
hidden block metadata, AI proposal state, or unpublished records.

When no Overview is published, the page begins with the existing résumé
experience. There is no public setup prompt or blank Overview container.

## 9. First-release publication model

- One private draft may evolve while one published revision remains stable.
- Publication pins the selected style definition/version, selected content
  versions, block order, emphasis, media focal data, destinations, and public
  audience result the member previewed.
- Publish is atomic: all validated blocks change together or nothing changes.
- The prior published revision is restorable.
- Style switching occurs only in the draft until publish.
- The owner may explicitly **Unpublish Overview**. The server-authorized,
  concurrency-checked operation atomically removes the current public Overview,
  restores the existing Summary as the opening, preserves publication history,
  invalidates public caches only after success, and leaves the private draft
  available according to the member's choice.
- A failed unpublish leaves the current public revision unchanged and provides
  a clear retry/recovery state.
- Visitors do not switch between Story & Career and Work & Impact.
- Multiple audience-specific Overviews are a possible later projection feature,
  not a side effect of the two styles.

## 10. Explicit non-goals

This package does not authorize:

- runtime implementation or changes to the current public résumé;
- a second résumé or Story fact store;
- automatic Story content from private Journal;
- a visitor-facing style toggle;
- arbitrary page layout, HTML, CSS, or user-created components;
- AI-created or AI-published facts;
- automatic publication after a source, style, or model change;
- generic or AI-generated workplace/family imagery represented as documentary
  evidence;
- public display of owner-only empty states or readiness errors;
- a new permanent navigation layer; or
- the mockups' repeated Full Résumé summary.

## 11. Success criteria

The future feature is successful only when:

- a sparse early-career profile and a rich senior profile both look deliberate;
- a member with one degree and no awards sees no awkward gaps or pressure to
  invent content;
- a member can build and maintain the Overview without AI or a developer;
- every public fact is owner-approved and source-traceable where applicable;
- every action has a real eligible destination;
- the page remains readable on mobile, at 200% text/zoom, by keyboard, with
  reduced motion, and without essential JavaScript;
- changing styles never loses content or changes the published page until
  explicit publication; and
- unpublish returns the page atomically to the existing Summary without
  deleting the draft or publication history;
- corrective source supersession cannot leave a known inaccurate claim public;
  and
- the full résumé remains the detailed source beneath the concise Overview.
