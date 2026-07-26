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
record-linked outcomes reference eligible canonical or approved public
projection records.
The Overview may store:

- selected record/version identifiers;
- order and emphasis;
- a public-safe purpose-specific summary with lineage;
- an approved destination;
- style-specific media focal data; and
- the state last reviewed by the member.

It does not copy a new authoritative employer, degree, award, skill, or date.

### First-release proof metrics

An optional proof metric is an authored Overview claim, not a canonical fact or
a PeerSlate-verified claim. The member supplies the exact value directly or
explicitly in the current AI request. The first release has no metric
source-backing, evidence-linking, verification, or provenance-state system.

AI may preserve the exact member-supplied value and help format or shorten its
label. It may not invent, infer, calculate, round, embellish, change, or
silently substitute the value. An AI wording proposal treats the numeric token
as immutable unless the member explicitly supplies a replacement value.

Normal draft, preview, publish, version, hide, reorder, and remove behavior
still applies. A future source-backed metric system is a separate deferred
decision and may not be inferred from the record-linked contracts below.

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
- The Overview hero uses **Connect** as its primary action and **View résumé**
  as its secondary same-page action to the actual résumé below.
- Public **Download PDF** and **Ask [Name] AI** remain page-level capabilities
  in the shared contextual action area. They do not repeat in the hero. Mobile
  may place those shared controls in one compact accessible menu.
- Overview cards use visible descriptive actions to eligible sections such as
  **View full experience**, **View all 12 skills**, or **Read my full story**.
- The concepts' top navigation and footer are illustrative and do not replace
  PeerSlate's shared shell.
- After **Résumé begins here**, the canonical résumé is authoritative for its
  detailed sections and existing anchor behavior.

## 6. Wide-desktop canvas and readable measure

Physical monitor diagonal is not a layout breakpoint. A 27-inch or 32-inch
screen may expose different CSS viewport widths because of native resolution,
operating-system scaling, browser zoom, and window size. Visual evidence and
acceptance therefore use CSS pixels and record the browser viewport.

The Overview root fills 100 percent of the resolved résumé center-content
column. It must not introduce a second arbitrary narrow page stage merely to
match the 941- or 864-pixel width of a supplied concept image.

Pete approved the Studio-aligned starting geometry for ChatGPT visual creation:
a centered shell of `min(92vw, 90rem)` at 100-percent browser zoom, with the
current 140-pixel contextual ribbon and responsive gap outside the center
canvas:

| CSS viewport | Candidate shell | Candidate center canvas |
| ---: | ---: | ---: |
| 1440 px | 1324.8 px | 1156 px |
| 1920 px | 1440 px | 1268 px |
| 2560 px | 1440 px | 1268 px |
| 3840 px | 1440 px | 1268 px |

At the widest viewports, the shared shell's cap intentionally leaves outer page
margins. The requirement is not edge-to-edge stretching; it is complete use of
the resolved content column.

The current résumé applies desktop `zoom: 0.9` to its children, producing an
approximately 1092-pixel visible center canvas at a 1440-pixel viewport and
1285 pixels at wider viewports. That is present-state evidence, not the future
Overview fit method. The Overview candidate must use normal scale and may not
use CSS `zoom` or `transform` to simulate the accepted width.

Readable text measure is a separate inner-block concern. A paragraph may use an
approximately 55–70-character line while its band, media, background, rules,
and neighboring composition establish the full-width silhouette. Sparse
content must remain deliberately composed across the canvas rather than
collapsing into one skinny centered card.

If a future Context Rail or shared-shell revision changes the available column,
the Overview resolves against that new column. A materially narrower outer
silhouette is a visual-direction change and must return to ChatGPT visual
creation and Pete's exact file/hash lock; architecture and implementation may
not introduce one independently.

The planned `PS-SHELL-001` package still contains an older approximate
1120–1200-pixel stage direction. That estimate does not narrow or block the
Overview visual exercise. ChatGPT starts with the approved candidate and Pete
may redirect the exact geometry after seeing complete 2560- and 3840-pixel
frames. The exact Pete-locked Overview and shared-shell geometry must agree
before runtime implementation.

See `08_WIDE_DESKTOP_WIDTH_AMENDMENT.md` for the measured reference geometry
and evidence contract.

## 7. Public density and content hierarchy

The richest mockup is an upper-bound configuration, not the required default.
A good published Overview usually contains:

- one identity hero;
- zero or one proof band;
- four to six meaningful major content bands normally; and
- no more than eight major content bands in the first release.

The hero and optional proof band do not count toward the four-to-six target or
eight-band maximum.

The product reduces selection and wording before it reduces type size. It
never solves density by clipping sentences, hiding content in card scrollbars,
shrinking body copy below the accepted scale, or duplicating the full résumé.

## 8. Manual-first self service

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

## 9. Owner and visitor experiences

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

## 10. First-release publication model

- One private draft may evolve while one published revision remains stable.
- The first-release Overview inherits the public résumé audience and cannot be
  broader. A separately selectable Overview audience is deferred.
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

## 11. Explicit non-goals

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
- a new permanent navigation layer;
- a narrow nested page stage derived from either concept image's raster width;
  or
- the mockups' repeated Full Résumé summary.

## 12. Success criteria

The future feature is successful only when:

- a sparse early-career profile and a rich senior profile both look deliberate;
- a member with one degree and no awards sees no awkward gaps or pressure to
  invent content;
- a member can build and maintain the Overview without AI or a developer;
- every public claim is owner-approved; record-linked facts are source-traceable
  where applicable, while first-release proof metrics are clearly treated as
  authored member claims without a source or verification claim;
- AI cannot invent or alter a proof metric value;
- every action has a real eligible destination;
- the page remains readable on mobile, at 200% text/zoom, by keyboard, with
  reduced motion, and without essential JavaScript;
- changing styles never loses content or changes the published page until
  explicit publication; and
- unpublish returns the page atomically to the existing Summary without
  deleting the draft or publication history;
- corrective source supersession cannot leave a known inaccurate claim public;
  and
- the full résumé remains the detailed source beneath the concise Overview;
  and
- the Overview uses the full resolved résumé content column at wide desktop
  while body copy retains a readable inner measure.
